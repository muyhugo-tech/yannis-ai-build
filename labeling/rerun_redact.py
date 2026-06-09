r"""
rerun_redact.py — re-run the redaction pipeline over an existing batch of
exported thread .md files, in place.

Why standalone: re-redaction should not route through label.py ingest (which
commits at end and discards on error) and must never touch labels.db. This
reads each file, runs the corrected redact_thread, writes it back, and prints
a per-file status. Idempotent: safe to re-run; already-clean files pass through
the deterministic gate unchanged.

Resilience: a failure on one file (e.g. an API read timeout on a large thread)
is caught, logged as ERROR, and the batch continues. Re-run the script to
retry the failed files — successful files re-redact to the same output, so
re-running is safe. Failed files are listed at the end so you can target them.

Usage (from labeling\, venv with anthropic active):
    python rerun_redact.py ..\threads_batch2

Add --dry-run to print statuses without writing anything.
"""
import sys
import pathlib

from redact import redact_thread
from redactor_claude import redactor   # the model name/company/address pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if not args:
        print("usage: python rerun_redact.py <dir> [--dry-run]")
        sys.exit(1)

    target = pathlib.Path(args[0])
    if not target.is_dir():
        print(f"not a directory: {target}")
        sys.exit(1)

    files = sorted(target.glob("*.md"))
    if not files:
        print(f"no .md files in {target}")
        sys.exit(1)

    counts = {"verified": 0, "names_unredacted": 0, "flagged": 0,
              "model_failed": 0, "unchanged": 0, "error": 0}
    errored = []

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8")
            redacted, status, findings = redact_thread(raw, redactor=redactor)
        except Exception as e:
            # One bad file (timeout, API error, decode error) must not abort
            # the batch. Log it, remember it, move on. Re-run to retry.
            counts["error"] += 1
            errored.append(f.name)
            print(f"{'ERROR':18} {f.name}  <-- {type(e).__name__}: {e}")
            continue

        changed = redacted != raw
        counts[status] = counts.get(status, 0) + 1
        if not changed:
            counts["unchanged"] += 1
        if status == "model_failed":
            errored.append(f.name)

        flag = ""
        if status == "flagged":
            kinds = ", ".join(sorted({x.get("kind", "?") for x in findings}))
            flag = f"  <-- FLAGGED: {kinds}"
        elif status == "model_failed":
            flag = "  <-- model pass failed; deterministic gate ran, prose names NOT redacted; retry"
        marker = "" if changed else "  (no change)"

        print(f"{status:18} {f.name}{marker}{flag}")

        if changed and not dry_run:
            f.write_text(redacted, encoding="utf-8")

    print("\nsummary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")
    if errored:
        print("\nfailed files (re-run to retry):")
        for name in errored:
            print(f"  {name}")
    if dry_run:
        print("\n(dry run — no files written)")


if __name__ == "__main__":
    main()
