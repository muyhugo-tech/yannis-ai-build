"""One-shot patch: replace first_message_date/last_message_date with date_range.

Idempotent: skips files that already have date_range and no first_message_date.
Run once after the export_threads.py format change; safe to re-run.
"""
import sys
from pathlib import Path

DIR = Path("threads_batch2")


def patch(text: str) -> tuple[str, bool]:
    if "date_range:" in text and "first_message_date:" not in text:
        return text, False
    lines = text.split("\n")
    first = last = None
    out = []
    inserted = False
    for line in lines:
        if line.startswith("first_message_date:"):
            first = line.split(":", 1)[1].strip()
            continue
        if line.startswith("last_message_date:"):
            last = line.split(":", 1)[1].strip()
            continue
        if not inserted and first is not None and last is not None:
            out.append(f"date_range: {first} / {last}")
            inserted = True
        out.append(line)
    if not inserted and first is not None and last is not None:
        out.append(f"date_range: {first} / {last}")
        inserted = True
    if not inserted:
        return text, False
    return "\n".join(out), True


def main():
    files = sorted(DIR.glob("*.md"))
    if not files:
        print(f"no .md files in {DIR}")
        sys.exit(1)
    patched = skipped = 0
    for p in files:
        old = p.read_text(encoding="utf-8")
        new, changed = patch(old)
        if changed:
            p.write_text(new, encoding="utf-8")
            patched += 1
        else:
            skipped += 1
    print(f"patched {patched}, skipped {skipped}")


if __name__ == "__main__":
    main()
