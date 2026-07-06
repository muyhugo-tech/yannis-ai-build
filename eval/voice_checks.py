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
# Check 3: no pricing in the initial response  --  §2.8 three-tier disclosure.
#
# Not every dollar figure is forbidden. The operator may quote concrete
# ADD-ON line items in a first reply (delivery, rentals, linen, staff, a
# beverage package) -- those are Tier-1 and ALLOWED. What must never appear
# is a menu/per-head price (Tier-2) or a total/estimate/quote (Tier-3, the
# danger cell: it reads as a committed number). So we do not ask "is there a
# number" -- we ask, for each dollar figure, "what is it attached to?":
#   "delivery is $50"            -> Tier-1, attributed   (pass)
#   "the menu is $46 per person" -> Tier-2, per-head     (fail)
#   "your total comes to $1,840" -> Tier-3, a total      (fail)
#   "it would be $75"            -> unattributed         (fail, conservative)
#   "we can seat up to 50"       -> not money at all      (pass)
#
# Mechanics: find each money figure (_MONEY), take a ~60-char window around
# it, and classify by what shares that window. Tier-3 phrasing fails no
# matter what else is there. A Tier-1 keyword within the window attributes
# the figure and clears it. Per-person phrasing WITHOUT a Tier-1 keyword is
# Tier-2 and fails. Anything left over -- a bare figure with no attribution
# -- fails by conservative default. Bare numbers (guest counts, dates,
# times) are never money and never flagged.
#
# This is GOOD, not PERFECT: attribution is proximity, not parsing, so a
# Tier-1 keyword that happens to sit near an unrelated menu price would
# wave it through. That is the deliberate bias -- it errs toward matching
# the operator's real add-on quoting, and the danger cell (Tier-3 totals)
# fails unconditionally regardless of any nearby keyword.
#
# This is the one check that earns its own test cases (see __main__).
# ---------------------------------------------------------------------------
_CONTEXT = 60  # chars on each side of a money figure that count as "near"

# A money figure: a $-amount, or "<number> dollars/USD".
_MONEY = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"                       # $50  $3  $1,840  $46.50
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:dollars?|usd)\b",   # 46 dollars  46 USD
    re.IGNORECASE,
)

# Tier-1 add-on line items. A figure attributed to one of these is allowed.
_TIER1_KEYWORDS = re.compile(
    r"\b(?:"
    r"deliver(?:y|ies|ed|ing)?"            # delivery
    r"|equipment|chafing|platter"          # rental hardware
    r"|rental|rent(?:ed|ing|s)?"           # rental
    r"|linen|napkin"                       # linen / napkin
    r"|cutlery|disposable"                 # cutlery / disposable
    r"|service staff|staff|server"         # service staff / server
    r"|soft[\s-]?drinks?|beverages?|drinks?"  # beverage terms
    r"|na"                                 # NA (non-alcoholic)
    r")\b",
    re.IGNORECASE,
)

# Tier-3 danger cell: a committed total/estimate/quote. Fails regardless of
# any nearby Tier-1 attribution.
_TIER3_TOTAL = re.compile(
    r"\b(?:total|comes to|estimate of|quote of|all[\s-]?in|altogether)\b",
    re.IGNORECASE,
)

# Tier-2 signal: per-head / menu pricing. Fails only when NOT Tier-1 attributed.
_PER_UNIT = re.compile(
    r"(?:per\s+(?:person|guest|head)|/\s?(?:person|guest|head))",
    re.IGNORECASE,
)


def check_no_pricing(text: str) -> CheckResult:
    for m in _MONEY.finditer(text):
        lo = max(0, m.start() - _CONTEXT)
        hi = min(len(text), m.end() + _CONTEXT)
        window = text[lo:hi]
        figure = m.group(0).strip()

        # Tier 3 -- total/estimate/quote: fails regardless of attribution.
        if _TIER3_TOTAL.search(window):
            return CheckResult(
                "no_pricing_in_initial_response", False,
                f"Tier-3 total/estimate/quote disclosure near {figure!r}",
            )
        # Tier 1 -- attributed to an add-on line item: allowed, keep scanning.
        if _TIER1_KEYWORDS.search(window):
            continue
        # Tier 2 -- per-head/menu price with no Tier-1 attribution: fails.
        if _PER_UNIT.search(window):
            return CheckResult(
                "no_pricing_in_initial_response", False,
                f"Tier-2 per-person/menu pricing without Tier-1 attribution near {figure!r}",
            )
        # Conservative default -- an unattributed figure fails.
        return CheckResult(
            "no_pricing_in_initial_response", False,
            f"unattributed pricing figure {figure!r}",
        )
    return CheckResult(
        "no_pricing_in_initial_response", True,
        "no disclosed pricing (Tier-1 attributed add-on figures allowed)",
    )


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
        # --- §2.8 three-tier disclosure ---
        # Tier-1: figure attributed to an add-on line item -> ALLOWED.
        ("Delivery to your office is $50.", "no_pricing_in_initial_response", True),
        ("Equipment rental is $150 and our NA package is $3 per guest.", "no_pricing_in_initial_response", True),
        ("Service staff are $200 per staff member.", "no_pricing_in_initial_response", True),
        ("We can seat up to 50 guests.", "no_pricing_in_initial_response", True),  # bare number, not money
        # Tier-2: per-head/menu price, no Tier-1 attribution -> FAIL.
        ("The reception menu is $46 per person.", "no_pricing_in_initial_response", False),
        ("It runs 46 dollars per guest.", "no_pricing_in_initial_response", False),
        # Tier-3: total/estimate/quote -> FAIL regardless of attribution.
        ("Your total comes to $1,840.", "no_pricing_in_initial_response", False),
        # Unattributed figure -> FAIL (conservative default).
        ("It would be $75.", "no_pricing_in_initial_response", False),
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
