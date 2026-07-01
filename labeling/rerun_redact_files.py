r"""
rerun_redact_files.py -- apply the deterministic HEADER pass to thread .md files.

Companion to rerun_redact_db.py, same defect, second surface. The DB rows are
already fixed; this closes the on-disk exports (threads\, threads_batch2_deferred\
-- batch 2 already had the pass run and should report no changes, which is
itself a useful idempotency check if you point this at it).

WHAT IT RUNS
redact.redact_headers() ONLY. Pure regex, no model call, no API cost, no other
redaction layers. It deliberately does NOT use rerun_redact.py's full pipeline:
that would re-run the model prose pass over every file (slow, costs tokens,
perturbs body text) to fix a defect that lives only in header lines.

WHY NO BACKUP GUARD (unlike the DB script)
These files are gitignored, untracked, reproducible from Gmail, and no longer
the canonical surface (the DB is). The change is also surgical: only **From:**
/ **To:** lines can be touched, and only their display-name slot. If you want
a belt anyway:  Copy-Item -Recurse ..\threads ..\threads_backup_2026-06-11

KNOWN LIMIT (log, don't fix here)
Batch-1 file BODIES may never have had the model prose pass (the DB got it at
ingest). This script does not address prose/signature names in bodies. That
only matters if these files are ever re-ingested; note it in STATE.md.

Usage (from labeling\, any venv -- stdlib + local redact.py only):
    python rerun_redact_files.py ..\threads ..\threads_batch2_deferred --dry-run
    python rerun_redact_files.py ..\threads ..\threads_batch2_deferred
"""
import pathlib
import sys

from redact import redact_headers


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    dirs = [pathlib.Path(a) for a in sys.argv[1:] if not a.startswith("--")]

    if not dirs:
        print("usage: python rerun_redact_files.py <dir> [<dir> ...] [--dry-run]")
        sys.exit(1)

    bad = [d for d in dirs if not d.is_dir()]
    if bad:
        for d in bad:
            print(f"not a directory: {d}")
        sys.exit(1)

    total_files = 0
    total_changed = 0

    for d in dirs:
        files = sorted(d.glob("*.md"))
        print(f"\n{d}  ({len(files)} files)")
        print("-" * 60)
        for f in files:
            total_files += 1
            raw = f.read_text(encoding="utf-8")
            fixed = redact_headers(raw)
            if fixed == raw:
                continue
            total_changed += 1
            n_lines = sum(
                1 for a, b in zip(raw.splitlines(), fixed.splitlines())
                if a != b
            )
            print(f"  {f.name}  ({n_lines} header line(s) redacted)")
            if not dry_run:
                f.write_text(fixed, encoding="utf-8")

    print(f"\nfiles scanned: {total_files}")
    print(f"files changed: {total_changed}")
    if dry_run:
        print("(dry run -- nothing written)")
    else:
        print("Re-run probe_from_lines.py to verify. Pass bar: zero findings.")


if __name__ == "__main__":
    main()
