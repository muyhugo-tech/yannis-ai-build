"""
agent_v2.py  --  Week-5 baseline + ONE change: the service-mode tool.

This is agent_v1.py with exactly one capability added: the agent now calls
the deterministic resolve_service_options tool before describing any service
format. Everything else is held constant against the v1 baseline so the
eval delta is attributable to the tool alone.

What is IDENTICAL to v1 (do not change without a new baseline):
  - the held-out inquiry
  - EXPECTED_LANGUAGE
  - MODEL
  - the voice-check tail (run_voice_checks on the returned draft string)
  - generate_draft still returns a single str; the voice gate is byte-for-byte
    the same code path as v1

What CHANGED from v1 (the single variable this session):
  - reads prompt_v2.txt instead of prompt_v1.txt (v1 prompt + the minimal
    instruction telling the model the tool exists and to use it)
  - imports resolve_service_options
  - generate_draft is now a stop_reason-keyed tool-use loop instead of a
    single messages.create call

HONEST DELTA NOTE for the eval record: the v1 -> v2 change is "tool + the
minimum prompt instruction that makes the tool fire", not "tool alone". A
tool with no prompt instruction gets called erratically. It is still one
conceptual change. Voice rules, exemplars, and pricing-gate language are
untouched.

PROOF NOTE: this run confirms the 80-guest fix by EYEBALL -- read the draft
and confirm no plated service is offered. A machine-checkable assertion
(fail if 'plated' appears in the 80-guest draft) was deliberately deferred
to next session. Until that assertion exists, "plated is gone" is a manual
confirmation, not a gate.

Standing rules honored here:
  - Direct Anthropic SDK, no framework.
  - Prompt caching enabled on the system block (unchanged from v1).
  - One variable changed off the v1 baseline.

Run:  python agent_v2.py
Needs: ANTHROPIC_API_KEY in the environment (or a .env loaded your usual way).
"""

from anthropic import Anthropic
from voice_checks import run_voice_checks
from tools.service_options import resolve_service_options

# --- the v2 system prompt: v1 verbatim plus the use-the-tool instruction ---
with open("prompt_v2.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# --- IDENTICAL to v1: same held-out inquiry. "up to 80 people" forces the
#     model to resolve a single integer (80) from a range, then the tool
#     makes plated structurally absent at that size. ---
HELD_OUT_INQUIRY = (
    "Subject: Birthday Party\n\n"
    "Hi,\n\n"
    "I'm planning a 50th birthday party and would like to know if you have "
    "availability on 7/11/2026. I believe we may have up to 80 people.\n\n"
    "If you have availability that weekend, please let me know your pricing options.\n\n"
    "Thank you,"
)

EXPECTED_LANGUAGE = "en"  # IDENTICAL to v1

MODEL = "claude-sonnet-4-5"  # IDENTICAL to v1; change deliberately, one var at a time

MAX_TURNS = 5  # hard cap so a misbehaving model cannot spin forever

# --- the tool schema the model sees. The description is load-bearing: the
#     model decides WHEN to call based on it. It names plated as capped and
#     this tool as the only authority on availability. ---
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


def _dispatch_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run a tool call. Return (result_text, is_error).

    The only tool wired this session is resolve_service_options. A bad guest
    count raises ValueError inside the tool; we catch it and return an error
    tool_result so the loop survives a bad extraction instead of crashing and
    lying about why the eval failed.
    """
    if name != "resolve_service_options":
        return (f"Unknown tool: {name}", True)
    try:
        result = resolve_service_options(
            guest_count=tool_input["guest_count"],
            plated_requested=tool_input.get("plated_requested", False),
        )
        # TypedDict is a plain dict at runtime; str() gives the model a clear
        # readable mapping. No need for json here, the model parses it fine.
        return (str(dict(result)), False)
    except (ValueError, KeyError, TypeError) as e:
        return (f"tool error: {e}", True)


def generate_draft(client: Anthropic) -> str:
    """Run the inquiry through a stop_reason-keyed tool-use loop.

    Same -> str contract as v1: returns the final reply text. The voice gate
    downstream does not know or care that a tool was involved.
    """
    messages = [{"role": "user", "content": HELD_OUT_INQUIRY}]

    for _ in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # caching, unchanged
                }
            ],
            tools=[SERVICE_OPTIONS_SCHEMA],
            messages=messages,
        )

        if resp.stop_reason == "tool_use":
            # Record the assistant turn verbatim (it may mix text + tool_use).
            messages.append({"role": "assistant", "content": resp.content})

            # Build one tool_result per tool_use block, keyed by its id.
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
            continue  # loop: feed results back, let the model write the reply

        # end_turn (or any non-tool stop): collect the text and return.
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    # Loud failure beats a silent hang: if we never reached end_turn, say so.
    raise RuntimeError(
        f"agent did not finish within {MAX_TURNS} turns (last stop_reason: "
        f"{resp.stop_reason!r}). Inspect the tool loop."
    )


def main() -> None:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from env

    print("=" * 70)
    print("HELD-OUT INQUIRY (agent input):")
    print("=" * 70)
    print(HELD_OUT_INQUIRY)
    print()

    draft = generate_draft(client)

    print("=" * 70)
    print("AGENT DRAFT (output):")
    print("=" * 70)
    print(draft)
    print()

    # EYEBALL PROOF for this run: read the draft above. Confirm it offers
    # buffet (or asks a qualifying question) and does NOT offer plated service.
    # 80 guests -> band 26_plus -> service_modes ["buffet"]. Plated must be
    # absent. If you see "plated" anywhere, the fix did NOT hold.
    print("(EYEBALL CHECK: confirm the draft above offers no plated service.)")
    print()

    print("=" * 70)
    print("VOICE GATE  --  deterministic checks")
    print("=" * 70)
    results = run_voice_checks(draft, expected_language=EXPECTED_LANGUAGE)

    real_checks = [r for r in results if r.name != "language_match"]
    lang = next(r for r in results if r.name == "language_match")

    real_failed = 0
    for r in real_checks:
        mark = "PASS" if r.passed else "FAIL"
        if not r.passed:
            real_failed += 1
        print(f"  [{mark}] {r.name:32s} | {r.detail}")

    # language_match is an explicit stub. Report it as ABSTAINED, never as a
    # pass, so the count is not read as a clean sweep.
    print(f"  [ABSTAINED] {lang.name:28s} | {lang.detail}")

    print()
    print("-" * 70)
    print(f"REAL CHECKS: {len(real_checks) - real_failed}/{len(real_checks)} passed"
          f"   (language_match abstained, not counted)")
    print("-" * 70)


if __name__ == "__main__":
    main()
