"""
Deterministic voice checks  --  Step 3 of the eval harness.

These differ from the classification metrics in one crucial way: each is a
per-output BOOLEAN, not a statistic. "Does this draft contain an em-dash?"
is true or false for one response, no sample size needed. That is why the
voice doc runs them BEFORE any similarity scoring and calls them
deterministic -- they are trustworthy on output number one and catch real
regressions the day the real agent exists.

Three checks are real deterministic booleans, built fully here:
  - no_em_dash
  - no_emoji
  - no_pricing_in_initial_response

The fourth, language_match, is an explicit STUB. Language detection on
short text is unreliable; making it "deterministic" would require either a
new dependency or a model call (non-deterministic -- the very thing voice
checks exist to avoid). And there is nothing to run it against yet: no real
agent, no real drafts. Building it now is capability ahead of need. It is
written as an honest not-implemented check that says what it needs.

Each check returns a CheckResult: passed (bool) + detail (str). The detail
explains a failure so a human reading eval output knows WHAT was wrong, not
just that something was.
"""

import re
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Check 1: no em-dash.
#
# The rule forbids the em-dash (—, U+2014). We check for it strictly.
# But a model often emits near-misses that LOOK like an em-dash to a
# reader: the en-dash (–, U+2013) and the double-hyphen (--). The rule is
# only about the true em-dash, so those do not FAIL the check -- but we
# surface them in the detail so they are visible, not silently passed.
# ---------------------------------------------------------------------------
EM_DASH = "\u2014"
EN_DASH = "\u2013"


def check_no_em_dash(text: str) -> CheckResult:
    if EM_DASH in text:
        count = text.count(EM_DASH)
        return CheckResult("no_em_dash", False, f"found {count} em-dash(es)")
    # passed, but note look-alikes if present
    notes = []
    if EN_DASH in text:
        notes.append(f"{text.count(EN_DASH)} en-dash(es)")
    if "--" in text:
        notes.append(f"{text.count('--')} double-hyphen(s)")
    detail = "no em-dash" + (f"; note look-alikes: {', '.join(notes)}" if notes else "")
    return CheckResult("no_em_dash", True, detail)


# ---------------------------------------------------------------------------
# Check 2: no emoji.
#
# There is no single "is this an emoji" flag in text. Emojis are ranges of
# Unicode code points, and the ranges are large and occasionally
# surprising. We check a defined set of the common ranges. This is GOOD,
# not PERFECT -- an exotic symbol could slip through, or a non-emoji
# pictograph could trip it. The check is honest about that rather than
# claiming a certainty it does not have.
# ---------------------------------------------------------------------------
_EMOJI_PATTERN = re.compile(
    "[" 
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoji, extended
    "\U00002600-\U000027BF"   # misc symbols + dingbats
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U00002190-\U000021FF"   # arrows (some render as emoji)
    "\U0000FE00-\U0000FE0F"   # variation selectors (emoji-style)
    "]"
)


def check_no_emoji(text: str) -> CheckResult:
    found = _EMOJI_PATTERN.findall(text)
    if found:
        return CheckResult("no_emoji", False, f"found {len(found)} emoji-like char(s): {found}")
    return CheckResult("no_emoji", True, "no emoji detected (good, not perfect)")


# ---------------------------------------------------------------------------
# Check 3: no pricing in the initial response.
#
# The operator never reveals pricing in a first reply; the agent directs to
# a call or follow-up. This is the only check with real false-positive
# risk: a reply with a number is not necessarily a reply with a price.
#   "we can seat up to 50"        -> a number, NOT a price  (must pass)
#   "the menu is $46 per person"  -> a price                (must fail)
#
# We look for two signals: a dollar amount ($ followed by digits), or
# price-phrasing ("per person", "per guest", "/person", "/guest") near a
# number. We deliberately do NOT flag bare numbers, to avoid failing on
# guest counts, dates, or times.
#
# This is the one check that earns its own test cases (see __main__).
# ---------------------------------------------------------------------------
_DOLLAR = re.compile(r"\$\s?\d")
_PER_PERSON = re.compile(r"(per\s+(person|guest|head)|/\s?(person|guest))", re.IGNORECASE)
_NUMBER_NEAR_PER = re.compile(
    r"\d+\s*(dollars?|usd)?\s*(per\s+(person|guest|head)|/\s?(person|guest))",
    re.IGNORECASE,
)


def check_no_pricing(text: str) -> CheckResult:
    signals = []
    if _DOLLAR.search(text):
        signals.append("dollar amount")
    if _NUMBER_NEAR_PER.search(text):
        signals.append("number + per-person phrasing")
    if signals:
        return CheckResult(
            "no_pricing_in_initial_response", False,
            f"pricing detected: {', '.join(signals)}",
        )
    return CheckResult("no_pricing_in_initial_response", True, "no pricing detected")


# ---------------------------------------------------------------------------
# Check 4: language match  --  EXPLICIT STUB.
#
# Not implemented, on purpose. To do this honestly we need:
#   (a) a real agent producing real Spanish/English drafts (stubs emit
#       placeholder text with no meaningful language), and
#   (b) a decision on HOW to detect language deterministically without a
#       new dependency or a model call, including the `mixed` rule
#       (default Spanish unless the inquiry's last message was English).
# Until both exist, this returns a not-implemented result so the harness is
# honest about what it can and cannot verify.
# ---------------------------------------------------------------------------
def check_language_match(draft_text: str, expected_language: str) -> CheckResult:
    return CheckResult(
        "language_match",
        passed=True,  # does not fail the suite; it abstains
        detail="NOT IMPLEMENTED -- needs real drafts + a deterministic detection decision",
    )


def run_voice_checks(draft_text: str, expected_language: str = "en") -> list[CheckResult]:
    """Run all voice checks on one draft. Returns a list of CheckResults.
    The three real checks run first; language abstains for now."""
    return [
        check_no_em_dash(draft_text),
        check_no_emoji(draft_text),
        check_no_pricing(draft_text),
        check_language_match(draft_text, expected_language),
    ]


if __name__ == "__main__":
    # Test cases. The pricing check especially earns these: we assert that
    # numbers-that-are-not-prices PASS and real prices FAIL.
    cases = [
        # (text, which check, should_pass)
        ("Thanks for reaching out, happy to help.", "no_em_dash", True),
        ("Happy to help \u2014 let's chat.", "no_em_dash", False),
        ("Looking forward to it!", "no_emoji", True),
        ("Looking forward to it \U0001F389", "no_emoji", False),
        ("We can seat up to 50 guests on the patio.", "no_pricing_in_initial_response", True),
        ("Your event is on 6/12 at 2pm.", "no_pricing_in_initial_response", True),
        ("The reception menu is $46 per person.", "no_pricing_in_initial_response", False),
        ("It runs 46 dollars per guest.", "no_pricing_in_initial_response", False),
    ]
    failed = 0
    for text, check_name, should_pass in cases:
        results = {r.name: r for r in run_voice_checks(text)}
        got = results[check_name].passed
        ok = (got == should_pass)
        if not ok:
            failed += 1
        mark = "OK " if ok else "XX "
        print(f"{mark}[{check_name}] expected_pass={should_pass} got_pass={got}  | {results[check_name].detail}")
    print()
    if failed:
        print(f"FAIL: {failed} voice-check case(s) behaved wrong")
    else:
        print("PASS: all voice-check cases behaved as expected")
