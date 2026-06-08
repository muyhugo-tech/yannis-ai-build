"""
agent_v1.py  --  Week-5 "simplest possible" agent.

Single prompt. No tools. No state. No multi-turn. One inquiry in, one
operator-voice first-reply draft out. This is the baseline; capability gets
added ONLY when an eval failure demands it.

Standing rules honored here:
  - Direct Anthropic SDK, no framework.
  - Prompt caching enabled on the system block from the first commit.
  - One thing measured this run: voice compliance, via voice_checks.py,
    deterministic checks only. No qualification scoring yet.

Run:  python agent_v1.py
Needs: ANTHROPIC_API_KEY in the environment (or a .env loaded your usual way).
"""

from anthropic import Anthropic
from voice_checks import run_voice_checks

# --- the system prompt lives in its own file so it is versionable and
#     cacheable independent of this runner ---
with open("prompt_v1.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# --- the held-out test inquiry: a cold inbound NOT among the exemplars.
#     It explicitly asks for pricing, which is the hardest test of the
#     no-pricing gate: will the agent quote because it was asked? ---
HELD_OUT_INQUIRY = (
    "Subject: Birthday Party\n\n"
    "Hi,\n\n"
    "I'm planning a 50th birthday party and would like to know if you have "
    "availability on 7/11/2026. I believe we may have up to 80 people.\n\n"
    "If you have availability that weekend, please let me know your pricing options.\n\n"
    "Thank you,"
)

EXPECTED_LANGUAGE = "en"

MODEL = "claude-sonnet-4-5"  # change deliberately, one variable at a time


def generate_draft(client: Anthropic) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # caching from commit 1
            }
        ],
        messages=[{"role": "user", "content": HELD_OUT_INQUIRY}],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


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
