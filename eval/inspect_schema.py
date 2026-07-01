"""
inspect_schema.py  --  read-only schema probe.

PURPOSE
The loader returns labels but no inquiry body. The agent needs the body.
Before joining anything we confirm, from the db itself, exactly which table
and column holds the inquiry text -- so we do not guess a column name and
burn another run on an AttributeError.

This file only READS. It prints:
  1. every table name,
  2. each table's columns (name + type),
  3. for the inquiries table specifically, ONE sample row with long text
     fields truncated, so we can see the shape without dumping a full email.

PII NOTE: a sample row may contain a real (already-redacted) inquiry body.
We truncate every text field to 200 chars. This is for your eyes in the
terminal only; nothing is written to disk. If a field still shows a raw
name/email, that is a redaction-pipeline finding to note separately, not
something to copy out of the terminal.

Run:  python inspect_schema.py
      python inspect_schema.py <path-to-labels.db>
"""

import sqlite3
import sys


def _truncate(value, limit: int = 200):
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"... [+{len(value) - limit} chars]"
    return value


def main() -> None:
    db = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\yannis-ai-build\labeling\labels.db"
    conn = sqlite3.connect(db)
    try:
        # 1. all tables
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        print("=" * 60)
        print("TABLES:", tables)
        print("=" * 60)

        # 2. columns per table
        for t in tables:
            print(f"\n--- {t} ---")
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
            for c in cols:
                # PRAGMA table_info: (cid, name, type, notnull, dflt, pk)
                print(f"  {c[1]:<28} {c[2] or '(no type)':<10} "
                      f"{'PK' if c[5] else ''}")

        # 3. sample row from the inquiries table, if it exists
        target = next((t for t in tables if t.lower() == "inquiries"), None)
        if target is None:
            print("\n[!] No table named 'inquiries' found. The inquiry body lives "
                  "elsewhere -- inspect the columns above to locate it.")
        else:
            print(f"\n{'=' * 60}")
            print(f"SAMPLE ROW from '{target}' (text truncated to 200 chars):")
            print("=" * 60)
            cur = conn.execute(f"SELECT * FROM {target} LIMIT 1")
            colnames = [d[0] for d in cur.description]
            row = cur.fetchone()
            if row is None:
                print("  (table is empty)")
            else:
                for name, val in zip(colnames, row):
                    print(f"  {name:<28} = {_truncate(val)!r}")

        # 4. count rows in inquiries so we know it is populated
        if target is not None:
            n = conn.execute(f"SELECT COUNT(*) FROM {target}").fetchone()[0]
            print(f"\n  rows in '{target}': {n}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
