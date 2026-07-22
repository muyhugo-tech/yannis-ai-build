"""
pilot_v0.py  --  the lightest useful pilot: read ONE inbound, print ONE draft,
and surface enough checks to judge whether the draft is edit-and-send quality.

This is NOT the send-safety gate and NOT a delivery mechanism. It exists to
answer one question with evidence before we build anything further:

    Is an agent draft good enough that EDITING it beats WRITING from scratch?

Everything we argued about (Gmail-draft delivery, three-tier name gating,
review banners) is downstream of that answer. So this file deliberately does
the minimum: it runs the SAME qualify() the graded path runs, prints the
decision and the draft, runs the THREE real voice checks, scans for the one
class of PII leak that has a clean deterministic test (emails / phone numbers),
and prints an explicit EYEBALL note for the two things we cannot check
deterministically yet (real names, language). It gates NOTHING. It withholds
NOTHING. It is a reading instrument.

WHY IT MIRRORS grade_agent.py:
  grade_agent.pairs_for_real_agent already established how to run the real
  agent over a loaded inbound: load_gradeable_inbounds(db) -> qualify(client,
  row.inquiry_text). This file is a single-row version of that loop with the
  DRAFT printed instead of scored. Reusing the exact call path means the
  pilot cannot silently behave differently from the thing the eval measured.

WHAT IS HONEST ABOUT THE CHECKS HERE (read before trusting the output):
  - no_em_dash / no_emoji / no_pricing: REAL deterministic booleans from
    voice_checks.run_voice_checks. Trustworthy on output #1.
  - email / phone leak scan: a small REAL regex scan added here. It catches
    the structured-PII class that has no false-positive problem. It does NOT
    attempt to detect real human NAMES -- that has no clean deterministic
    test (see the redactor work), so attempting it here would either
    false-positive constantly or false-negative silently. Instead we PRINT a
    one-line eyeball reminder.
  - language: voice_checks.check_language_match is an explicit STUB that always
    abstains (returns passed=True, verifies nothing). We do NOT count it as a
    pass. We print 'NOT VERIFIED' so a reader knows language was not checked.
    (On the v2 prompt the agent is instructed to reply in English regardless,
    so a wrong-language draft is unlikely in this run -- but unlikely is not
    checked, and we say so.)

NORMAL-INPUT NOTE  --  PLACEHOLDER TOKENS ARE EXPECTED, NOT LEAKS:
  Redacted inbounds carry {name} {company} {phone} {address} {email} by
  design, and a correct draft will ECHO some of them ("Hi {name},"). The leak
  scan below is built to PASS those tokens and only flag UN-tokenized
  structured PII. A draft containing '{name}' is the redaction working; a
  draft containing 'john@acme.com' is a leak.

QUARANTINE GUARD:
  Two rows are quarantined model_failed and carry live un-redacted names
  (18da9fc1, 18e15f53). They are not in the clean-inbound set this pilot pulls
  from, so --id cannot normally reach them -- but we refuse them explicitly
  anyway, belt-and-suspenders, so a future change to the loader cannot route
  a name-bearing row into a printed draft.

USAGE (run from inside eval/, venv with ANTHROPIC_API_KEY set):
  cd eval
  python pilot_v0.py --id 19xxxxxxxxxxxxxx        # pull a clean inbound from the DB
  python pilot_v0.py --id 19aaa --id 19bbb ...    # several in one run
  echo "Hi, can you cater 20 people Friday?" | python pilot_v0.py --stdin
  python pilot_v0.py --list                       # list available clean-inbound IDs

This file is read-only against the DB. It makes 2 API calls per inquiry
(reply + forced classify), exactly as qualify() does in the graded path.
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

import argparse
import re
import sys

from anthropic import Anthropic

from eval_loader import load_gradeable_inbounds, InboundRow
from voice_checks import run_voice_checks
from agent_v3 import qualify


# Rows quarantined model_failed that carry live names. Never print a draft
# built from these, regardless of how they were reached.
QUARANTINED_IDS = {
    "18da9fc12bae4de0",
    "18e15f532bcec520",
}

# Statuses whose DRAFT must be WITHHELD (decision shown, draft suppressed).
# PROVED in the Session-I runs, not theoretical: on declined rows the draft
# field is frequently the agent talking TO THE OPERATOR ("I don't see the
# inquiry text, please paste it"), not a sendable customer reply. The DECISION
# is the trustworthy output on these rows; the draft is not. human_review is
# included on the same logic: if the operator must judge it directly, the
# agent should not hand over a confident-looking draft to send. For these
# statuses the draft is never surfaced as sendable and the draft-based checks
# (which only matter for something you'd send) are skipped.
WITHHELD_STATUSES = {"declined", "human_review"}

DEFAULT_DB = r"C:\dev\yannis-ai-build\labeling\labels.db"


# ---------------------------------------------------------------------------
# Email / phone leak scan  --  the ONE PII class with a clean deterministic
# test. This is intentionally narrow. It flags structured identifiers that
# should never survive redaction. It does NOT touch names (no clean test).
#
# Placeholder tokens like {name} {email} {phone} are EXPECTED and must not
# trip this. We strip {curly_tokens} before scanning so an echoed placeholder
# can never be mistaken for a leak.
# ---------------------------------------------------------------------------
_CURLY_TOKEN = re.compile(r"\{[a-z_]+\}", re.IGNORECASE)

# An email: something@something.tld. Conservative; real emails, not every @.
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# A phone number: 10+ digits allowing common separators. Requires enough
# structure that prices/dates/guest-counts do not trip it. Matches
# 619-555-0123, (619) 555 0123, 6195550123, +1 619 555 0123.
_PHONE = re.compile(
    r"(?:\+?1[\s.\-]?)?"          # optional country code
    r"(?:\(\d{3}\)|\d{3})"        # area code, parenthesized or not
    r"[\s.\-]?\d{3}[\s.\-]?\d{4}" # prefix + line
)


def scan_pii_leak(text: str) -> list[str]:
    """Return a list of structured-PII leak descriptions found in `text`.
    Curly placeholder tokens are stripped first so they are never flagged.
    Empty list means no structured leak found (names NOT checked here)."""
    scrubbed = _CURLY_TOKEN.sub("", text)
    hits = []
    emails = _EMAIL.findall(scrubbed)
    if emails:
        hits.append(f"email-like: {emails}")
    phones = _PHONE.findall(scrubbed)
    # findall with groups returns tuples for some patterns; normalize to the
    # actual matched spans via finditer for a readable report.
    phone_spans = [m.group(0) for m in _PHONE.finditer(scrubbed)]
    if phone_spans:
        hits.append(f"phone-like: {phone_spans}")
    return hits


# ---------------------------------------------------------------------------
# Name eyeball heuristic  --  NOT a gate. Surfaces capitalized name-shaped
# tokens for a human glance. This will false-positive on ordinary words
# (sentence starts, 'Yanni', 'Mediterranean', weekday names). That is fine:
# its only job is to give the reader a short "glance at these" list, never to
# block or pass anything. We do not try to be precise; we try to be honest
# that names are unchecked and offer a cheap prompt to look.
# ---------------------------------------------------------------------------
# Words that are EXPECTED to be capitalized in a correct draft and are not
# customer names. Keeping this small and obvious; it only declutters the
# eyeball list, it does not make the list authoritative.
_EXPECTED_CAPS = {
    "Yanni", "Yannis", "Hi", "Hello", "Dear", "Best", "Thanks", "Thank",
    "Hugo", "Brenna",  # operator signatures, expected
    "Mediterranean", "Scripps", "Ranch", "San", "Diego",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
}
_CAP_TOKEN = re.compile(r"\b[A-Z][a-z]{2,}\b")


def eyeball_name_tokens(text: str) -> list[str]:
    """Capitalized name-shaped tokens minus an obvious expected set and minus
    curly placeholders. For HUMAN GLANCE only. Deliberately imprecise."""
    scrubbed = _CURLY_TOKEN.sub("", text)
    toks = _CAP_TOKEN.findall(scrubbed)
    # de-dupe, drop expected, preserve order
    seen = set()
    out = []
    for t in toks:
        if t in _EXPECTED_CAPS or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# Rendering one inquiry's result.
# ---------------------------------------------------------------------------
def render(inquiry_id: str | None, inquiry_text: str, output) -> None:
    bar = "=" * 72
    print(bar)
    label = f"INQUIRY {inquiry_id}" if inquiry_id else "INQUIRY (pasted)"
    print(label)
    print("-" * 72)
    # Show what the agent actually read, so a parsing miss is visible.
    # NOTE: limit raised 600 -> 2000 after Session I — the 600-char cut hid the
    # deciding text on two rows and led to two wrongly-flagged findings. Show
    # the reviewer what the agent actually read.
    preview = inquiry_text.strip()
    if len(preview) > 2000:
        preview = preview[:2000] + " […truncated for display]"
    print("AGENT INPUT (what qualify() read):")
    print(preview if preview else "(empty — parsing returned no body)")
    print()

    print(f"DECISION: {output.status.value}")
    print()

    # --- WITHHOLD branch (Session I) ---------------------------------------
    # On declined / human_review the draft is NOT a sendable customer reply
    # (proved: it is often the agent addressing the operator). Suppress it and
    # the draft-based checks entirely, and tell the operator to handle the row.
    # The decision above is the trustworthy output here.
    if output.status.value in WITHHELD_STATUSES:
        print("DRAFT: [WITHHELD]")
        if output.status.value == "declined":
            print("  Status is 'declined' — no customer reply is needed, and the")
            print("  agent's draft on declined rows is unreliable (often addressed")
            print("  to the operator, not the customer). Nothing to send here.")
        else:  # human_review
            print("  Status is 'human_review' — the operator should judge this one")
            print("  directly. No draft is surfaced for sending.")
        print()
        print("SUMMARY: draft withheld by design. If you disagree with the")
        print("         DECISION above, handle this inquiry by hand.")
        print(bar)
        print()
        return
    # -----------------------------------------------------------------------

    print("DRAFT:")
    print(output.draft_response.strip())
    print()

    # --- the three REAL voice checks ---
    results = run_voice_checks(output.draft_response)
    real = [r for r in results if r.name != "language_match"]
    real_fail = [r for r in real if not r.passed]
    print("VOICE CHECKS (deterministic, real):")
    for r in real:
        mark = "PASS" if r.passed else "FAIL"
        print(f"  [{mark}] {r.name:32s} {r.detail}")

    # --- the one real PII class we can check cleanly ---
    leaks = scan_pii_leak(output.draft_response)
    if leaks:
        print(f"  [FAIL] pii_email_phone_scan            {leaks}")
    else:
        print(f"  [PASS] pii_email_phone_scan            no email/phone leak (names NOT checked)")

    # --- the two things we do NOT check: print, do not gate ---
    names = eyeball_name_tokens(output.draft_response)
    print()
    print("EYEBALL THESE YOURSELF (not checked, not gated):")
    print(f"  names: language is NOT verified on this draft — read it for wrong-language.")
    if names:
        print(f"  name-shaped tokens to glance at (expect false positives): {names}")
    else:
        print(f"  name-shaped tokens: none beyond the expected set")

    # --- bottom line for THIS draft (advisory only) ---
    print()
    hard = list(real_fail)
    if leaks:
        hard.append("pii_email_phone_scan")
    if hard:
        names_failed = ", ".join(r.name if hasattr(r, "name") else str(r) for r in hard)
        print(f"SUMMARY: {len(hard)} hard check(s) FAILED ({names_failed}). "
              f"This draft would be WITHHELD in a send path. Read why above.")
    else:
        print("SUMMARY: all hard checks passed. Judge the DRAFT itself: "
              "would editing this beat writing from scratch?")
    print(bar)
    print()


def run_one_from_db(client: Anthropic, rows_by_id: dict[str, InboundRow],
                    inquiry_id: str) -> None:
    if inquiry_id in QUARANTINED_IDS:
        print(f"REFUSED {inquiry_id}: quarantined model_failed row "
              f"(carries live names). Not running.\n")
        return
    row = rows_by_id.get(inquiry_id)
    if row is None:
        print(f"NOT FOUND {inquiry_id}: not in the clean-inbound set. "
              f"Run with --list to see available IDs.\n")
        return
    output = qualify(client, row.inquiry_text)
    render(inquiry_id, row.inquiry_text, output)


def run_one_from_text(client: Anthropic, text: str, push: bool = False,
                      attach_id: str | None = None) -> None:
    output = qualify(client, text)
    render(None, text, output)
    if push:
        _push_to_crm(text, output)
    if attach_id:
        _attach_to_crm(attach_id, output)



def _prompt_console(label: str) -> str:
    """Prompt on the console device. --stdin runs exhaust sys.stdin, so
    input() would EOFError; read from CON (Windows console) instead."""
    print(label, end="", flush=True)
    try:
        with open("CON", "r", encoding="utf-8") as con:
            return con.readline().strip()
    except OSError:
        try:
            return input().strip()
        except EOFError:
            return ""


def _push_to_crm(inquiry_text: str, output) -> None:
    """Opt-in push of this run into the CRM. Operator supplies the two
    fields the model must not extract (deterministic source: Gmail).
    Empty answer at either prompt aborts; the run is unaffected."""
    if output.status.value in ("declined", "human_review"):
        print("PUSH skipped: draft withheld for this status; no CRM row by design.")
        print()
        return
    import crm_push
    print("PUSH: copy both fields from Gmail. Empty answer aborts.")
    name = _prompt_console("  contact_name: ")
    if not name:
        print("PUSH aborted: no contact_name.")
        print()
        return
    url = _prompt_console("  gmail_thread_url: ")
    if not url:
        print("PUSH aborted: no gmail_thread_url.")
        print()
        return
    if not url.startswith("https://mail.google.com/"):
        print("PUSH aborted: thread URL must start with https://mail.google.com/")
        print()
        return
    event_id = crm_push.push_lead({
        "contact_name": name,
        "gmail_thread_url": url,
        "message": inquiry_text.strip(),
    })
    draft_id = crm_push.push_draft(event_id, output.draft_response.strip())
    print(f"PUSHED: event {event_id}  draft {draft_id}")
    print()


def _attach_to_crm(event_id: str, output) -> None:
    """Opt-in draft-attach to an EXISTING CRM event (Typeform leads arrive
    via webhook; push_lead would duplicate them). push_draft only, ever."""
    if output.status.value in ("declined", "human_review"):
        print("ATTACH skipped: draft withheld for this status; no CRM write by design.")
        print()
        return
    import crm_push
    answer = _prompt_console(f"attach draft to event {event_id}? (y/N): ")
    if answer.lower() != "y":
        print("ATTACH aborted: not confirmed.")
        print()
        return
    draft_id = crm_push.push_draft(event_id, output.draft_response.strip())
    print(f"ATTACHED: event {event_id}  draft {draft_id}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="v0 pilot: print one draft + checks for one inbound.")
    ap.add_argument("--id", action="append", default=[],
                    help="inquiry_id from the clean-inbound set (repeatable)")
    ap.add_argument("--stdin", action="store_true",
                    help="read one raw inquiry body from stdin instead of the DB")
    ap.add_argument("--list", action="store_true",
                    help="list available clean-inbound IDs and exit")
    ap.add_argument("--db", default=DEFAULT_DB, help="path to labels.db")
    ap.add_argument("--push", action="store_true",
                    help="after the draft, offer to push lead+draft to the CRM (stdin runs only)")
    ap.add_argument("--attach", metavar="EVENT_ID", default=None,
                    help="after the draft, offer to attach it to an EXISTING CRM event "
                         "(Typeform leads; stdin runs only; never creates a lead)")
    args = ap.parse_args()
    if args.push and not args.stdin:
        ap.error("--push works only with --stdin (corpus rows are historical, not live leads)")
    if args.attach and args.push:
        ap.error("--attach and --push are mutually exclusive (attach never creates a lead)")
    if args.attach and not args.stdin:
        ap.error("--attach works only with --stdin (corpus rows are historical, not live leads)")
    if args.attach and not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
            r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", args.attach):
        ap.error(f"--attach id does not look like a UUID: {args.attach!r}")

    rows = load_gradeable_inbounds(args.db)
    rows_by_id = {r.inquiry_id: r for r in rows}

    if args.list:
        print(f"{len(rows)} clean cold inbounds available:")
        for r in rows:
            preview = r.inquiry_text.strip().replace("\n", " ")[:70]
            print(f"  {r.inquiry_id}  {preview!r}")
        return

    client = Anthropic()

    if args.stdin:
        text = sys.stdin.buffer.read().decode('utf-8')
        if not text.strip():
            print("stdin was empty — nothing to run.")
            return
        run_one_from_text(client, text, push=args.push, attach_id=args.attach)
        return

    if not args.id:
        ap.error("give at least one --id, or --stdin, or --list")

    for iid in args.id:
        run_one_from_db(client, rows_by_id, iid)


if __name__ == "__main__":
    main()
