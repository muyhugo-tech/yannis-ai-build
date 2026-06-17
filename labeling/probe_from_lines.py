r"""
probe_from_lines.py -- read-only probe for the display-name redaction leak.

PURPOSE
Dump the LITERAL bytes (repr) of every **From:** line whose display-name slot
is not already {name} and not allowlisted staff, across BOTH surfaces:

  1. the on-disk .md exports (threads\, threads_batch2\, threads_batch2_deferred\,
     threads_batch3\, threads_batch3_deferred\)
  2. labels.db's inquiries.thread_text_redacted (what the agent actually reads)

The fix to redact.py's _HEADER_RE must be built against these real formats
(bare name with no angle bracket, quoted "Lastname, First", {email}-only,
token-after-name, whatever else is out there) -- not against assumed ones.

Scans ALL messages in each thread, not just message 1: quoted-chain or
mid-thread From lines can leak the same way.

WRITES NOTHING. No API calls. Safe to run repeatedly.

PII NOTE: this probe prints raw leaked names to YOUR terminal so you can see
the failing formats. That output stays local. Do not paste it anywhere public;
when sharing findings, describe the FORMAT (e.g. 'bare name, no brackets')
rather than the name itself, or substitute {name} manually.

Run from labeling\ (any venv, stdlib only):
    python probe_from_lines.py
    python probe_from_lines.py <repo-root>      # default C:\dev\yannis-ai-build

2026-06-12 (Session D): threads_batch3 / threads_batch3_deferred added to
THREAD_DIRS. Findings are tagged with their source path, so fresh-export
leaks (the Session C verification ride-along) are distinguishable from any
legacy-folder noise by the FILE prefix.
"""
import pathlib
import re
import sqlite3
import sys
from collections import Counter

# Single source of truth: the probe judges leaks with the SAME coverage rule
# the redactor uses. If they drift, the probe lies. (v1 carried its own copy;
# pre-F6 it imported _ALLOWLIST and re-ran the same broken substring test, so
# it shared the blind spot and reported 0 leaks while surnames sat in bodies.)
from redact import is_allowlisted

THREAD_DIRS = (
    "threads",
    "threads_batch2",
    "threads_batch2_deferred",
    "threads_batch3",
    "threads_batch3_deferred",
)

FROM_LINE_RE = re.compile(r"^\*\*From:\*\*.*$", re.MULTILINE)


def slot_of(line: str) -> str:
    """Best-effort extraction of the display-name slot from a From line.
    Everything after '**From:**', minus a trailing <...> part if present."""
    rest = line.split("**From:**", 1)[1].strip()
    # strip a trailing angle-bracket section (real address or {email} token)
    rest = re.sub(r"\s*<[^>]*>\s*$", "", rest).strip()
    return rest


def is_leak(slot: str) -> bool:
    """True if the slot looks like an unredacted customer display-name."""
    if not slot:
        return False                      # empty slot: nothing leaked
    # v2: treat quoted tokens as redacted too. The model pass redacts the
    # name INSIDE Outlook-style quotes, leaving '"{name}"' / '"{email}"'.
    # v1 flagged these as leaks; they are not -- no name survives. (They DO
    # indicate the deterministic header pass never ran on that surface,
    # which redact_headers fixes by collapsing the slot to bare {name}.)
    bare = slot.strip().strip('"').strip("'").strip()
    if bare in ("{name}", "{email}", "{url}", "{phone}"):
        return False                      # already redacted / token-only
    # Shared F6 coverage rule — identical to what the redactor enforces.
    if is_allowlisted(slot):
        return False                      # staff / vendor / org allowlist
    return True


def classify(line: str) -> str:
    """Coarse structural classification of the From line, for the format
    inventory. The repr output is the ground truth; this is just grouping."""
    rest = line.split("**From:**", 1)[1].strip()
    has_bracket = "<" in rest
    quoted = rest.startswith('"')
    has_email_token = "{email}" in rest
    if quoted and has_bracket:
        return "quoted name + <...>"
    if quoted:
        return "quoted name, NO brackets"
    if has_bracket:
        return "bare name + <...>"
    if has_email_token:
        return "bare name + {email} token, NO brackets"
    return "bare name only, NO brackets"


def scan_text(text: str, source: str, findings: list) -> None:
    for m in FROM_LINE_RE.finditer(text):
        line = m.group(0)
        slot = slot_of(line)
        if is_leak(slot):
            findings.append((source, classify(line), line))


def main() -> None:
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(
        r"C:\dev\yannis-ai-build")

    findings: list[tuple[str, str, str]] = []

    # Surface 1: .md exports
    md_count = 0
    per_dir: Counter = Counter()
    for d in THREAD_DIRS:
        folder = root / d
        if not folder.is_dir():
            print(f"(skipping missing folder: {folder})")
            continue
        for f in sorted(folder.glob("*.md")):
            md_count += 1
            per_dir[d] += 1
            scan_text(f.read_text(encoding="utf-8"),
                      f"FILE {d}\\{f.name}", findings)

    # Surface 2: labels.db thread_text_redacted
    db = root / "labeling" / "labels.db"
    db_count = 0
    if db.exists():
        conn = sqlite3.connect(db)
        try:
            rows = conn.execute(
                "SELECT inquiry_id, thread_text_redacted FROM inquiries"
            ).fetchall()
        finally:
            conn.close()
        db_count = len(rows)
        for inquiry_id, text in rows:
            if text:
                scan_text(text, f"DB   {inquiry_id}", findings)
    else:
        print(f"(labels.db not found at {db})")

    # Report
    print("=" * 72)
    print(f"SCANNED  {md_count} .md files  +  {db_count} DB rows")
    for d in THREAD_DIRS:
        if per_dir[d]:
            print(f"         {per_dir[d]:>4} files in {d}\\")
    print(f"LEAKED From-lines found: {len(findings)}")
    print("=" * 72)

    fmt_counts = Counter(fmt for _, fmt, _ in findings)
    print("\nFORMAT INVENTORY (drives the regex fix):")
    for fmt, n in fmt_counts.most_common():
        print(f"  {n:>4}  {fmt}")

    print("\nLITERAL LINES (repr -- exact bytes the fix must handle):")
    print("-" * 72)
    for source, fmt, line in findings:
        print(f"[{fmt}]")
        print(f"  {source}")
        print(f"  {line!r}")
        print()

    if not findings:
        print("  (none -- both surfaces clean under the current allowlist)")


if __name__ == "__main__":
    main()
