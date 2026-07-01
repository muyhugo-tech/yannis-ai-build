"""
agent_v3.py  --  v2 baseline + ONE change: structured qualification output.

This is agent_v2.py with exactly one new capability: the agent now emits a
STRUCTURED DECISION (qualification status) via a terminal submit_qualification
tool, in addition to the operator-voice draft it already wrote. Until now the
agent produced prose only and its qualification accuracy had never been
measured. This file makes the decision measurable.

THE SINGLE VARIABLE THIS SESSION:
  - a second tool, submit_qualification, whose schema is the contract.
    Its `status` enum is the four canonical QualificationStatus values, so
    an invalid decision is structurally unrepresentable (the Step-3 pattern
    from the foundation doc). The status comes OUT of the tool/contract;
    the reply text stays prose. The two never mix.

WHAT IS HELD CONSTANT vs v2 (do not touch without a new baseline):
  - SYSTEM_PROMPT source (prompt_v2.txt) -- NOT edited here. The instruction
    telling the model to submit a qualification is added by FORCING the tool
    (tool_choice), not by editing the prompt. This keeps the prompt variable
    out of this cycle.
  - the resolve_service_options tool, its schema, and the tool loop
  - MODEL, MAX_TURNS, prompt caching on the system block
  - the voice gate and the v2 held-out 80-guest demo (preserved in main())

STATUS-ONLY SCOPE (operator decision, session 8):
  Of the five AgentOutput fields only `status` is graded. fit_score,
  confidence, and edge_flags are filled with explicit placeholders here and
  are NOT real model judgments yet. They get their own baseline-resetting
  step if/when a grader scores them. draft_response carries the real reply.

DECISION/PROSE SEPARATION (forced-tool consequence):
  When a tool is forced via tool_choice the model stops to call it and does
  not also free-write in the same turn. So qualify() runs in two stages:
    stage 1 -- normal tool loop (service tool available, no forcing): the
               model writes the operator-voice reply exactly as in v2.
    stage 2 -- a single forced submit_qualification call over the same
               conversation: the model classifies, emitting only the
               structured decision.
  Prose is produced free; the decision is extracted under contract. Clean
  separation, by construction.

Standing rules honored:
  - Direct Anthropic SDK, no framework.
  - Prompt caching on the system block (unchanged from v2).
  - One variable changed off the v2 baseline (the structured-output tool).

Run the v2-style single-inquiry demo:  cd eval; python agent_v3.py
Grade over the dataset:                cd eval; python grade_agent.py
Needs: ANTHROPIC_API_KEY in the environment.
"""

# --- TLS: trust the OS certificate store (Windows/corporate root CAs) ---
# The Anthropic API is reached through a TLS-intercepting root CA present in
# the OS cert store but absent from certifi's bundle, so plain requests fail
# with CERTIFICATE_VERIFY_FAILED. truststore routes verification through the
# OS store. Guarded: a no-op if truststore is not installed, so this never
# hard-breaks an environment that does not need it. Must run before the
# anthropic client opens a connection.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
# -----------------------------------------------------------------------

from anthropic import Anthropic

from agent_output_schema import (
    AgentOutput,
    QualificationStatus,
    normalize_status,
)
from voice_checks import run_voice_checks
from tools.service_options import resolve_service_options

# --- v2 system prompt, read verbatim. NOT edited this session. ---
with open("prompt_v2.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# --- v2 held-out demo inquiry, preserved so the v2 voice/plated demo still
#     runs unchanged from this file. ---
HELD_OUT_INQUIRY = (
    "Subject: Birthday Party\n\n"
    "Hi,\n\n"
    "I'm planning a 50th birthday party and would like to know if you have "
    "availability on 7/11/2026. I believe we may have up to 80 people.\n\n"
    "If you have availability that weekend, please let me know your pricing options.\n\n"
    "Thank you,"
)

EXPECTED_LANGUAGE = "en"            # IDENTICAL to v2
MODEL = "claude-sonnet-4-5"        # IDENTICAL to v2
MAX_TURNS = 5                      # IDENTICAL to v2

# --- placeholders for the four non-graded fields (status-only scope) ---
PLACEHOLDER_FIT_SCORE = 50
PLACEHOLDER_CONFIDENCE = 0.5

# --- service-options tool: IDENTICAL to v2 ---
SERVICE_OPTIONS_SCHEMA = {
    "name": "resolve_service_options",
    "description": (
        "Resolve which service modes (plated, buffet, regular dining) Yanni's "
        "offers for a given guest count. Call this before describing any service "
        "format. Plated service is capped; this tool is the only authority on "
        "whether plated is available at a given size."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "guest_count": {
                "type": "integer",
                "description": "Number of guests for the event.",
            },
            "plated_requested": {
                "type": "boolean",
                "description": (
                    "True only if the customer explicitly asked for plated / "
                    "individually-served service."
                ),
                "default": False,
            },
        },
        "required": ["guest_count"],
    },
}

# --- THE SINGLE NEW THING: the terminal decision contract as a tool. The
#     status enum mirrors QualificationStatus exactly. The model literally
#     cannot return a fifth value: an invalid decision is unrepresentable.
#     We pull the allowed strings FROM the enum so this can never drift out
#     of sync with the contract the grader reads. ---
SUBMIT_QUALIFICATION_SCHEMA = {
    "name": "submit_qualification",
    "description": (
        "Submit the final qualification decision for this inquiry. Call this "
        "exactly once, after you have read the inquiry. Choose the single "
        "status that best fits:\n"
        "  - qualified: a real person with active intent to book or arrange "
        "an event, meal, or catering at Yanni's. Missing details (date, exact "
        "headcount, time of day) do not downgrade this; the reply asks for "
        "them. Small groups and regular dining requests with clear intent are "
        "still qualified. Yanni's serves every group size.\n"
        "  - needs_info: the sender's intent is tentative or unclear: they "
        "are exploring or comparing options, or you cannot tell what they "
        "actually want. Use this when the reply must first establish whether "
        "there is a real booking intent at all, not merely fill in details.\n"
        "  - declined: no booking intent: spam, vendor or marketing outreach, "
        "internal or administrative messages, empty or broken content, or a "
        "request for something Yanni's does not do.\n"
        "  - human_review: genuinely ambiguous, or a case the operator should "
        "judge directly."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [s.value for s in QualificationStatus],
                "description": "The single qualification decision for this inquiry.",
            },
        },
        "required": ["status"],
    },
}


# Session O decouple: the classifier gets its OWN minimal prompt, sourced from
# the intent definitions (the submit_qualification schema description) rather
# than the draft-authoring SYSTEM_PROMPT. This cuts the channel by which
# draft-voice prompt edits (e.g. a billing block) leaked into the qualification
# decision. _write_reply is unchanged and still uses SYSTEM_PROMPT verbatim.
CLASSIFY_SYSTEM_PROMPT = (
    "You are classifying an inbound inquiry to Yanni's Bar & Grill into "
    "exactly one qualification status. Decide based only on the inquiry and "
    "the conversation so far. Do not consider tone, wording, or how a reply "
    "should be written -- only what the sender wants.\n\n"
    + SUBMIT_QUALIFICATION_SCHEMA["description"]
)


def _dispatch_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run a service tool call. Return (result_text, is_error).

    IDENTICAL to v2. submit_qualification is NOT dispatched here -- it is a
    terminal contract handled directly in qualify(), not a side-effect tool.
    """
    if name != "resolve_service_options":
        return (f"Unknown tool: {name}", True)
    try:
        result = resolve_service_options(
            guest_count=tool_input["guest_count"],
            plated_requested=tool_input.get("plated_requested", False),
        )
        return (str(dict(result)), False)
    except (ValueError, KeyError, TypeError) as e:
        return (f"tool error: {e}", True)


def _write_reply(client: Anthropic, inquiry_text: str) -> tuple[str, list]:
    """Stage 1: the v2 reply path. Returns (reply_text, message_history).

    This is v2's generate_draft loop, generalized to take an inquiry instead
    of the hardcoded one, and additionally returning the message history so
    stage 2 can classify over the same conversation. The service tool is
    available and NOT forced -- the model uses it exactly as in v2.
    """
    messages = [{"role": "user", "content": inquiry_text}]

    for _ in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[SERVICE_OPTIONS_SCHEMA],
            messages=messages,
        )

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result_text, is_error = _dispatch_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                            "is_error": is_error,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        reply = "".join(b.text for b in resp.content if b.type == "text").strip()
        # record the final assistant reply so stage 2 sees it
        messages.append({"role": "assistant", "content": resp.content})
        return reply, messages

    raise RuntimeError(
        f"agent did not finish writing a reply within {MAX_TURNS} turns "
        f"(last stop_reason: {resp.stop_reason!r}). Inspect the tool loop."
    )


def _classify(client: Anthropic, messages: list) -> QualificationStatus:
    """Stage 2: force exactly one submit_qualification call over the existing
    conversation and read the status back through the contract.

    tool_choice forces the call, so the model cannot decline to decide and
    cannot smuggle the decision into prose. We run the raw status through
    normalize_status so the contract -- not this function -- is the authority
    on what counts as a valid status. An unrecognized value raises loudly
    rather than being silently bucketed.
    """
    resp = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=[
            {
                "type": "text",
                "text": CLASSIFY_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[SUBMIT_QUALIFICATION_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_qualification"},
        messages=messages + [
            {
                "role": "user",
                "content": (
                    "Now submit your qualification decision for this inquiry "
                    "using the submit_qualification tool."
                ),
            }
        ],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "submit_qualification":
            return normalize_status(block.input["status"])

    # tool_choice guarantees a forced call; reaching here means the API
    # contract changed underneath us. Fail loud, do not guess a status.
    raise RuntimeError(
        "submit_qualification was forced but no tool_use block was returned. "
        f"stop_reason={resp.stop_reason!r}. Inspect the classify call."
    )


def qualify(client: Anthropic, inquiry_text: str) -> AgentOutput:
    """Run one inquiry end to end and return the full AgentOutput.

    status        -- the real model decision (graded).
    draft_response-- the real operator-voice reply.
    fit_score / confidence / edge_flags -- explicit placeholders this session
                     (status-only scope). Not model judgments yet.
    """
    reply, messages = _write_reply(client, inquiry_text)
    status = _classify(client, messages)
    return AgentOutput(
        fit_score=PLACEHOLDER_FIT_SCORE,
        status=status,
        draft_response=reply,
        confidence=PLACEHOLDER_CONFIDENCE,
    )


def main() -> None:
    """v2-style single-inquiry demo, now also printing the structured status.

    The voice gate and the 80-guest eyeball proof are preserved exactly so
    this file still confirms the v2 behavior, plus it now shows the decision.
    """
    client = Anthropic()

    print("=" * 70)
    print("HELD-OUT INQUIRY (agent input):")
    print("=" * 70)
    print(HELD_OUT_INQUIRY)
    print()

    output = qualify(client, HELD_OUT_INQUIRY)

    print("=" * 70)
    print("AGENT DRAFT (output):")
    print("=" * 70)
    print(output.draft_response)
    print()
    print("(EYEBALL CHECK: confirm the draft above offers no plated service.)")
    print()

    print("=" * 70)
    print("STRUCTURED DECISION (the new output this session):")
    print("=" * 70)
    print(f"  status: {output.status.value}")
    print(f"  (fit_score={output.fit_score}, confidence={output.confidence} "
          f"-- placeholders, not graded this session)")
    print()

    print("=" * 70)
    print("VOICE GATE  --  deterministic checks")
    print("=" * 70)
    results = run_voice_checks(output.draft_response, expected_language=EXPECTED_LANGUAGE)

    real_checks = [r for r in results if r.name != "language_match"]
    lang = next(r for r in results if r.name == "language_match")

    real_failed = 0
    for r in real_checks:
        mark = "PASS" if r.passed else "FAIL"
        if not r.passed:
            real_failed += 1
        print(f"  [{mark}] {r.name:32s} | {r.detail}")
    print(f"  [ABSTAINED] {lang.name:28s} | {lang.detail}")

    print()
    print("-" * 70)
    print(f"REAL CHECKS: {len(real_checks) - real_failed}/{len(real_checks)} passed"
          f"   (language_match abstained, not counted)")
    print("-" * 70)


if __name__ == "__main__":
    main()
