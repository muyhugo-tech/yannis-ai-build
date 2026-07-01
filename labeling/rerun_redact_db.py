r"""
rerun_redact_db.py -- apply the deterministic HEADER pass to labels.db rows.

WHAT THIS FIXES
probe_from_lines.py proved the leak is a COVERAGE gap, not a regex defect:
redact_headers() was never run over inquiries.thread_text_redacted (the DB
was ingested before the header pass existed and never re-touched). This
script closes that surface.

WHAT IT RUNS
redact.redact_headers() ONLY -- the pure-regex From/To display-name closer,
with the allowlist (staff + vendor platforms) deciding what survives.
NO model call, NO API cost, NO other redaction layers. The model name pass
already ran on these rows at ingest; emails/phones/URLs were tokenized at
export. The header slot is the one thing that was never closed here.

It deliberately does NOT run the full deterministic_redact(): the other
regexes are idempotent in theory, but the smallest change that fixes the
defect is the header pass alone, and that is what gets run.

SAFETY
- Refuses to write unless a backup file matching labels_backup_*.db newer
  than the last write to labels.db exists in the same folder. Make one first:
      Copy-Item labels.db labels_backup_2026-06-11.db
- --dry-run prints what WOULD change (row ids + changed line counts) and
  writes nothing. Run it first.
- Only rows whose text actually changes are written. Rerunning is a no-op
  (redact_headers is idempotent; allowlisted slots pass through).

AFTER RUNNING
1. Re-run probe_from_lines.py -- pass bar: zero personal names in headers
   on the DB surface.
2. Re-run the eval (grade_agent) to re-baseline: rows whose text changed
   can move the metric. That is a DATA change, documented as such; do not
   compare the new number to 0.934 without saying the input text changed.

Usage (from labeling\, any venv -- stdlib + local redact.py only):
    python rerun_redact_db.py --dry-run
    python rerun_redact_db.py
    python rerun_redact_db.py <path-to-labels.db> [--dry-run]
"""
import pathlib
import sqlite3
import sys

from redact import redact_headers


def find_db(args: list[str]) -> pathlib.Path:
    positional = [a for a in args if not a.startswith("--")]
    if positional:
        return pathlib.Path(positional[0])
    return pathlib.Path(__file__).resolve().parent / "labels.db"


def backup_ok(db: pathlib.Path) -> bool:
    """A labels_backup_*.db at least as new as labels.db must exist."""
    db_mtime = db.stat().st_mtime
    for candidate in db.parent.glob("labels_backup_*.db"):
        if candidate.stat().st_mtime >= db_mtime:
            return True
    return False


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    db = find_db(sys.argv[1:])

    if not db.exists():
        print(f"labels.db not found: {db}")
        sys.exit(1)

    if not dry_run and not backup_ok(db):
        print("REFUSING to write: no labels_backup_*.db found that is at")
        print("least as new as labels.db. Make one first:")
        print("    Copy-Item labels.db labels_backup_2026-06-11.db")
        print("Or run with --dry-run to preview without writing.")
        sys.exit(1)

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT inquiry_id, thread_text_redacted FROM inquiries"
        ).fetchall()

        changed = []
        for inquiry_id, text in rows:
            if not text:
                continue
            fixed = redact_headers(text)
            if fixed != text:
                n_lines = sum(
                    1 for a, b in zip(text.splitlines(), fixed.splitlines())
                    if a != b
                )
                changed.append((inquiry_id, fixed, n_lines))

        print(f"rows scanned: {len(rows)}")
        print(f"rows changed: {len(changed)}")
        for inquiry_id, _, n_lines in changed:
            print(f"  {inquiry_id}  ({n_lines} header line(s) redacted)")

        if dry_run:
            print("\n(dry run -- nothing written)")
            return

        if not changed:
            print("\nnothing to write.")
            return

        conn.executemany(
            "UPDATE inquiries SET thread_text_redacted = ? WHERE inquiry_id = ?",
            [(fixed, inquiry_id) for inquiry_id, fixed, _ in changed],
        )
        conn.commit()
        print(f"\nwrote {len(changed)} rows. Re-run probe_from_lines.py to verify.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
