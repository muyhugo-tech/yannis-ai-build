"""
probe_body_artifacts.py  --  F5 body-artifact verification gate.  READ-ONLY.

WHY THIS EXISTS
  The From-line probe (check_batch3_redaction.py) scans **From:** slots only.
  It ran GREEN while "{name-8}" sat unredacted in a SIGNATURE BLOCK and
  "Hi {name-3}" / "{name-5}" sat in body prose -- because those are not header
  slots. Bodies were a structural blind spot. F5 closes it.

  This is the gate that must pass before any new ingest. Its bar:
      ZERO un-quarantined CUSTOMER-name hits, on BOTH surfaces.
  Carrier artifacts and cosmetic residue (staff surnames, menu nouns, vendor
  org tokens) are reported but do NOT fail the bar -- they are not customer
  PII. See PASS-BAR below.

WHAT IT IS NOT
  Not the publication gate. F5 is the INGEST gate. It deliberately tolerates
  staff surnames and known vendor/menu tokens in stored text because those are
  not customer PII. A stricter "no real-person name anywhere" scan for the
  public git-history audit is a SEPARATE, stricter tool. Do not conflate them.

DESIGN COMMITMENTS (these are the F6/{name-17} lessons, applied)
  1. NO ALLOWLIST IMPORT. redact.py's allowlist is how {name-17} hid (a staff
     first-name token waved a customer surname through). This probe builds its
     own known-token set from scratch. If redact.py's allowlist is wrong, this
     probe must still be able to catch it -- shared code means shared blind
     spots. They are kept independent ON PURPOSE.
  2. TWO-TIER triage, not aggressive filtering. A hit is either CLEARED
     (every token is provably non-PII: staff/org/menu/role known token) or it
     lands in REVIEW. We never silently suppress a maybe. The filter grows by
     explicit, filename-visible edits -- brittle by design, visible when it
     grows, same discipline as the allowlist itself.
  3. OVER-REPORT, never under-report. The name heuristic flags more than it
     should and a human clears each REVIEW hit. A probe that under-reports
     lies; a probe that over-reports merely costs eyeball time.
  4. SCAN STORED BYTES. DB surface reads thread_text_redacted (what actually
     ships to eval), not source. File surface reads the .md on disk. They can
     disagree (Session F: committed != applied); reporting both is the point.

PASS-BAR (exit code)
  exit 0  -> PASS: zero un-quarantined customer-name hits. (REVIEW bucket may
            be non-empty but every REVIEW hit traces to a quarantined row or
            was human-cleared in a prior session and recorded as non-customer.)
  exit 1  -> FAIL: at least one REVIEW name hit on a row that is NOT
            quarantined (redaction_status != 'model_failed'). Ingest is
            blocked until that row is re-redacted in place or quarantined.
  Carrier artifacts NEVER set the fail code on their own (they are a
  data-quality signal, not a PII leak) but are surfaced loudly.

  NOTE on the file surface: .md exports carry signature names BY DESIGN -- they
  die at ingest and are never committed (threads*/ is gitignored). So the file
  surface is reported for drift-detection but does NOT gate (a raw name in an
  uncommitted, gitignored .md is not a leak). Only the DB surface gates.

Run from labeling\\ :  python probe_body_artifacts.py
Optional: python probe_body_artifacts.py --db labels.db --threads-glob "..\\threads*"
"""

import argparse
import glob
import os
import re
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# KNOWN NON-PII TOKENS  (built from scratch; NOT imported from redact.py)
#
# Two sets with different jobs:
#   STAFF_ORG  -- Yanni's own people + the business itself. A signature from
#                 the operator side is expected and is not customer PII.
#   NOISE      -- menu nouns, role/title words, and KNOWN vendor names that
#                 the two-cap-word signature heuristic trips on. These are not
#                 names of customers. Grows by explicit edit when a new menu
#                 item or role surfaces in REVIEW.
#
# A hit is CLEARED iff EVERY token in it is in (STAFF_ORG | NOISE | stopwords).
# Anything with even one unknown token goes to REVIEW. That asymmetry is the
# whole safety property: unknown token -> human looks.
# ---------------------------------------------------------------------------

STAFF_ORG = {
    # staff first names
    "hugo", "brenna", "jonathan", "jonah", "denise", "yanni", "yannis",
    "jona",  # corpus OCR/typo variant of "Jonah" (Session G; staff, not customer)
    # staff surnames
    "pihas", "fineman", "gutierrez",
    # business identity
    "ybg", "yannis", "bar", "grill", "catering", "scripps", "highlands",
    "san", "diego", "ca",
}

# Menu nouns, role/title words, and KNOWN vendor names. These are the things
# the signature heuristic flags that are provably not a customer's name.
# ADD HERE EXPLICITLY when a new one shows up in REVIEW and is confirmed noise.
# Every addition is a filename-visible decision (the F6 discipline).
NOISE = {
    # menu nouns seen in pasted menu blocks / quote chains
    "neapolitan", "spartan", "bruschetta", "bruschettas", "dip", "trio",
    "grilled", "chicken", "loukaniko", "caesar", "spinach", "salad", "salads",
    "penne", "bolognese", "beef", "skewers", "cobb", "mediterranean",
    "chicken", "piccata", "lamb", "cannelloni", "salmon", "lemoni",
    "mini", "budino", "bakery", "app", "barber", "massage", "botanica",
    "spa", "therapy", "salon", "skincare", "first", "look", "front", "patio",
    # menu nouns -- added from Session G [B-FAIL] triage (confirmed non-names)
    "spanakopita", "dessert", "tzatziki", "arancini", "appetizers", "appetizer",
    # section/label words from structured-form bodies (Typeform field labels,
    # menu section headers) -- not names
    "timing", "setup", "overview", "inside", "perfect", "blog", "community",
    # role / title words (job titles in signatures, not names)
    "facility", "manager", "events", "event", "coordinator", "executive",
    "assistant", "general", "quality", "assurance", "guest", "count",
    "dietary", "notes", "business", "principal",
    # role / title words -- added Session G [B-FAIL] triage
    "paralegal", "partner",
    # sign-off abbreviations the signature regex catches as a lone cap-word
    "thx",
    # known vendor / platform org tokens seen in corpus signatures
    "typeform", "team", "epic", "coordination", "wedding", "grantify",
}

# Sign-off / greeting stopwords -- not names, frequently adjacent to names.
STOPWORDS = {
    "best", "thanks", "thank", "cheers", "hi", "hello", "regards", "kind",
    "sincerely", "the", "warm", "warmest", "later", "dear", "all", "good",
    "morning", "afternoon", "evening", "and", "or", "to", "of", "for",
    "sweet",  # "Sweet Brenna" sign-off (Session G)
}

KNOWN = STAFF_ORG | NOISE | STOPWORDS


# ---------------------------------------------------------------------------
# PATTERNS
# ---------------------------------------------------------------------------

# Carrier artifacts: quote-chain / forwarded-message / mobile-signature /
# HTML-entity leak carriers. A body with these has un-stripped quote chain or
# encoding residue -- a data-quality flag, and a place names love to hide.
ARTIFACT_PATTERNS = {
    "On...wrote:":   re.compile(r"\bOn\b.{0,80}\bwrote:", re.DOTALL),
    "html_entity":   re.compile(r"&(nbsp|lt|gt|amp|#\d+|quot|apos);"),
    "angle_entity":  re.compile(r"&lt;|&gt;"),
    "Sent from iP":  re.compile(r"Sent from my iP"),
    "Forwarded msg": re.compile(r"Forwarded message"),
}

# Greeting:  "Hi Firstname" / "Hello Firstname" / "Dear Firstname"
# [ \t]+ not \s+ : \s crosses newlines, so "Hi\nAs soon as" wrongly captured
# "As". A greeting and its name are on the same line. (Session G fix.)
GREETING_RE = re.compile(r"\b(?:Hi|Hello|Dear)[ \t]+([A-Z][a-z]+)\b")
# Signature: a line that is ONLY one or two capitalized words (a name block).
SIG_NAME_RE = re.compile(r"^\s*([A-Z][a-z]+)(?:\s+([A-Z][a-z]+))?\s*$", re.MULTILINE)


def _norm(tok: str) -> str:
    return tok.lower().strip(".,;:\"'()<>[]")


def classify(tokens: list[str]) -> str:
    """CLEARED if every token is known non-PII; else REVIEW.
    Empty -> CLEARED (nothing to look at)."""
    toks = [_norm(t) for t in tokens if _norm(t)]
    if not toks:
        return "CLEARED"
    return "CLEARED" if all(t in KNOWN for t in toks) else "REVIEW"


def scan_text(text: str):
    """Return (artifact_kinds, review_name_samples, cleared_name_samples)."""
    artifacts = []
    review = []
    cleared = []
    if not text:
        return artifacts, review, cleared

    for kind, rx in ARTIFACT_PATTERNS.items():
        if rx.search(text):
            artifacts.append(kind)

    for m in GREETING_RE.finditer(text):
        verdict = classify([m.group(1)])
        (review if verdict == "REVIEW" else cleared).append(("greeting", m.group(0)))

    for m in SIG_NAME_RE.finditer(text):
        parts = [g for g in (m.group(1), m.group(2)) if g]
        verdict = classify(parts)
        sample = m.group(0).strip()
        (review if verdict == "REVIEW" else cleared).append(("signature", sample))

    return artifacts, review, cleared


# ---------------------------------------------------------------------------
# SURFACE 1: DB rows (the gating surface)
# ---------------------------------------------------------------------------

def scan_db(db_path: str):
    cx = sqlite3.connect(db_path)
    try:
        rows = cx.execute(
            "SELECT inquiry_id, redaction_status, thread_text_redacted "
            "FROM inquiries ORDER BY ingested_at"
        ).fetchall()
        labeled = {r[0] for r in cx.execute("SELECT DISTINCT inquiry_id FROM labels")}
    finally:
        cx.close()

    findings = []  # (iid, status, labeled, artifacts, review, cleared)
    for iid, status, text in rows:
        artifacts, review, cleared = scan_text(text)
        if artifacts or review or cleared:
            findings.append((iid, status, iid in labeled, artifacts, review, cleared))
    return findings, len(rows)


# ---------------------------------------------------------------------------
# SURFACE 2: .md files (reported, does NOT gate -- exports carry names by
# design and are gitignored/local-only)
# ---------------------------------------------------------------------------

def scan_files(threads_glob: str):
    findings = []  # (path, artifacts, review, cleared)
    paths = []
    for d in glob.glob(threads_glob):
        if os.path.isdir(d):
            paths.extend(glob.glob(os.path.join(d, "**", "*.md"), recursive=True))
    for p in sorted(set(paths)):
        try:
            with open(p, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        artifacts, review, cleared = scan_text(text)
        if artifacts or review:
            findings.append((p, artifacts, review, cleared))
    return findings, len(paths)


# ---------------------------------------------------------------------------
# REPORT + GATE
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=Path(__file__).resolve().parent / "labels.db")
    ap.add_argument("--threads-glob", default=os.path.join("..", "threads*"))
    ap.add_argument("--quiet-cleared", action="store_true",
                    help="suppress the CLEARED name list (noise) in output")
    args = ap.parse_args()

    print("=" * 74)
    print("F5 body-artifact probe (probe_body_artifacts.py) -- READ-ONLY")
    print("=" * 74)

    # ---- DB surface (gating) ----
    db_findings, n_rows = scan_db(args.db)
    print(f"\nSURFACE 1: DB (thread_text_redacted)  --  {n_rows} rows scanned")
    print("-" * 74)

    db_artifacts = [(i, s, l, a) for (i, s, l, a, r, c) in db_findings if a]
    db_review_gating = []     # REVIEW on a NON-quarantined row -> FAILS the bar
    db_review_quarantined = []  # REVIEW on a quarantined row -> known, no fail

    for iid, status, lab, artifacts, review, cleared in db_findings:
        for kind, sample in review:
            rec = (iid, status, lab, kind, sample)
            if status == "model_failed":
                db_review_quarantined.append(rec)
            else:
                db_review_gating.append(rec)

    print(f"\n[A] CARRIER ARTIFACTS (quote-chain / entity / forward residue): "
          f"{sum(len(a) for _,_,_,a in db_artifacts)} across {len(db_artifacts)} rows")
    for iid, status, lab, artifacts in db_artifacts:
        L = "labeled" if lab else "unlabeled"
        print(f"    {iid}  [{status}, {L}]  {', '.join(artifacts)}")

    print(f"\n[B-FAIL] REVIEW name hits on NON-quarantined rows "
          f"(these GATE -- must be zero): {len(db_review_gating)}")
    for iid, status, lab, kind, sample in db_review_gating:
        L = "labeled" if lab else "unlabeled"
        print(f"    {iid}  [{status}, {L}]  {kind}: {sample!r}")

    print(f"\n[B-OK] REVIEW name hits on QUARANTINED (model_failed) rows "
          f"(known, do not gate): {len(db_review_quarantined)}")
    for iid, status, lab, kind, sample in db_review_quarantined:
        L = "labeled" if lab else "unlabeled"
        print(f"    {iid}  [{status}, {L}]  {kind}: {sample!r}")

    if not args.quiet_cleared:
        cleared_count = sum(len(c) for _,_,_,_,_,c in db_findings)
        print(f"\n[C] CLEARED hits (known staff/org/menu/role noise): {cleared_count}")
        print("    (suppressed list; pass --quiet-cleared off to inspect. These are")
        print("     provably non-customer tokens. If a REAL name is here, a token in")
        print("     NOISE/STAFF_ORG is wrong -- fix the set, do not ignore.)")

    # ---- File surface (reported, non-gating) ----
    file_findings, n_files = scan_files(args.threads_glob)
    print(f"\nSURFACE 2: .md files ({args.threads_glob})  --  {n_files} files scanned")
    print("-" * 74)
    print("(REPORTED ONLY -- exports carry names by design, are gitignored, die at")
    print(" ingest. Does NOT gate. Drift between this and SURFACE 1 is the signal.)")
    file_review = [(p, r) for (p, a, r, c) in file_findings if r]
    print(f"\n[D] files with REVIEW name hits: {len(file_review)}")
    for p, review in file_review[:40]:
        names = ", ".join(f"{k}:{s!r}" for k, s in review[:4])
        more = "" if len(review) <= 4 else f"  (+{len(review)-4} more)"
        print(f"    {os.path.basename(p)}  {names}{more}")
    if len(file_review) > 40:
        print(f"    ... (+{len(file_review)-40} more files)")

    # ---- VERDICT ----
    print("\n" + "=" * 74)
    fail = len(db_review_gating) > 0
    if fail:
        print("RESULT: FAIL")
        print(f"  {len(db_review_gating)} REVIEW name hit(s) on non-quarantined DB rows.")
        print("  Each is a candidate customer-name leak in shipping eval text.")
        print("  Per row: eyeball it. If customer PII -> re-redact IN PLACE (labeled,")
        print("  FK to labels -- never delete-reingest) OR quarantine (model_failed).")
        print("  If it is provably non-customer (vendor/menu/role) -> add the token to")
        print("  NOISE/STAFF_ORG in THIS file, by explicit edit, and re-run.")
        print("  Ingest is BLOCKED until this is zero.")
    else:
        print("RESULT: PASS")
        print("  Zero un-quarantined customer-name hits on the DB surface.")
        print(f"  ({len(db_review_quarantined)} REVIEW hit(s) sit on quarantined rows --")
        print("   known, excluded from eval, not shipping.)")
        print("  Carrier artifacts and CLEARED/file-surface hits are reported above")
        print("  for data-quality awareness; they do not block ingest.")
    print("=" * 74)

    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
