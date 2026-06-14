"""002_add_model_failed_status.py -- widen inquiries.redaction_status CHECK.

WHY
labeling/redact.py (Session C rewrite) returns status='model_failed' when the
model name-pass fails. The inquiries CHECK constraint allows only
('pending','verified','flagged','names_unredacted'), so the first batch-3
ingest crashed with sqlite3.IntegrityError on its first file
(18da9f17eb7c769d.md). model_failed is a legitimate blocked state -- like
'flagged' and 'names_unredacted', a model_failed row must be storable and
un-labelable (label.py already filters labeling to redaction_status =
'verified', so no change needed there for labelability).

WHAT
SQLite cannot ALTER a CHECK constraint; the table is rebuilt:
  create inquiries_new (identical, widened CHECK) -> copy all rows ->
  drop inquiries -> rename. labels' FK references 'inquiries' by name, so
  the rename restores the relationship; foreign_key_check verifies it.

GUARDS
  - refuses to run unless labels.db.bak-pre-002 exists (rollback = copy back)
  - refuses to run if the live CHECK already contains model_failed (no
    double-run)
  - pre/post counts captured dynamically and asserted equal (inquiries rows,
    status breakdown, labels rows, labels-joinable-to-inquiries rows)
  - live constraint test: inserts a model_failed dummy row inside a
    transaction and rolls it back -- proves the widened CHECK without residue

RUN (Hugo, watched, from labeling\\ in venv -- stdlib only, either venv works):
    python migrations\\002_add_model_failed_status.py

Expected: all pre/post pairs equal (128 inquiries, all verified; 145 label
rows), constraint test PASS, foreign_key_check clean.
"""
import os
import sqlite3
import sys

DB = "labels.db"
BACKUP = "labels.db.bak-pre-002"

NEW_INQUIRIES_DDL = """
CREATE TABLE inquiries_new (
    inquiry_id           TEXT PRIMARY KEY,
    thread_id            TEXT NOT NULL,
    source_path          TEXT NOT NULL,
    subject_redacted     TEXT,
    message_count        INTEGER,
    date_range_start     TEXT,
    date_range_end       TEXT,
    thread_text_redacted TEXT NOT NULL,
    redaction_status     TEXT NOT NULL DEFAULT 'pending'
        CHECK (redaction_status IN ('pending','verified','flagged','names_unredacted','model_failed')),
    redaction_findings   TEXT,
    ingested_at          TEXT NOT NULL
)
"""

COLS = ("inquiry_id, thread_id, source_path, subject_redacted, message_count, "
        "date_range_start, date_range_end, thread_text_redacted, "
        "redaction_status, redaction_findings, ingested_at")


def counts(cx) -> dict:
    return {
        "inquiries": cx.execute("SELECT COUNT(1) FROM inquiries").fetchone()[0],
        "statuses": dict(cx.execute(
            "SELECT redaction_status, COUNT(1) FROM inquiries "
            "GROUP BY redaction_status").fetchall()),
        "labels": cx.execute("SELECT COUNT(1) FROM labels").fetchone()[0],
        "labels_joined": cx.execute(
            "SELECT COUNT(1) FROM labels l "
            "JOIN inquiries i ON i.inquiry_id = l.inquiry_id").fetchone()[0],
    }


def main() -> None:
    if not os.path.exists(DB):
        print(f"ABORT: {DB} not found. Run from labeling\\.")
        sys.exit(1)
    if not os.path.exists(BACKUP):
        print(f"ABORT: backup {BACKUP} not found. Make it first:")
        print(f"  copy {DB} {BACKUP}")
        sys.exit(1)

    cx = sqlite3.connect(DB)

    # Guard: no double-run. Read the live DDL from sqlite_master.
    live_ddl = cx.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='inquiries'"
    ).fetchone()[0]
    if "model_failed" in live_ddl:
        print("ABORT: live inquiries CHECK already contains model_failed. "
              "Migration already applied. Nothing changed.")
        sys.exit(1)

    pre = counts(cx)
    print("pre-migration:")
    print(f"  inquiries: {pre['inquiries']}   statuses: {pre['statuses']}")
    print(f"  labels: {pre['labels']}   joinable to inquiries: {pre['labels_joined']}")

    # Rebuild. foreign_keys must be set OUTSIDE a transaction.
    cx.execute("PRAGMA foreign_keys = OFF")
    try:
        cx.execute("BEGIN")
        cx.execute(NEW_INQUIRIES_DDL)
        cx.execute(f"INSERT INTO inquiries_new ({COLS}) "
                   f"SELECT {COLS} FROM inquiries")
        copied = cx.execute("SELECT COUNT(1) FROM inquiries_new").fetchone()[0]
        if copied != pre["inquiries"]:
            raise RuntimeError(f"copy count {copied} != {pre['inquiries']}")
        cx.execute("DROP TABLE inquiries")
        cx.execute("ALTER TABLE inquiries_new RENAME TO inquiries")
        cx.execute("COMMIT")
    except Exception as e:
        cx.execute("ROLLBACK")
        cx.close()
        print(f"ABORT: {type(e).__name__}: {e} -- rolled back, DB unchanged.")
        sys.exit(1)

    fk_violations = cx.execute("PRAGMA foreign_key_check").fetchall()
    cx.execute("PRAGMA foreign_keys = ON")

    post = counts(cx)
    print("post-migration:")
    print(f"  inquiries: {post['inquiries']}   statuses: {post['statuses']}")
    print(f"  labels: {post['labels']}   joinable to inquiries: {post['labels_joined']}")

    ok = (pre == post and not fk_violations)
    if fk_violations:
        print(f"  FAIL: foreign_key_check reported {len(fk_violations)} violation(s)")
    if pre != post:
        print("  FAIL: pre/post counts differ")

    # Live constraint test: model_failed insert must now succeed. Rolled back.
    try:
        cx.execute("BEGIN")
        cx.execute(
            "INSERT INTO inquiries (inquiry_id, thread_id, source_path, "
            "thread_text_redacted, redaction_status, ingested_at) "
            "VALUES ('__mig002_test__','__t__','__p__','x','model_failed','now')")
        cx.execute("ROLLBACK")
        print("  constraint test: model_failed insert accepted (rolled back) -- PASS")
    except sqlite3.IntegrityError as e:
        cx.execute("ROLLBACK")
        print(f"  constraint test FAIL: model_failed still rejected: {e}")
        ok = False

    cx.close()
    if ok:
        print("\nPASS: migration 002 applied. redaction_status now accepts "
              "model_failed. Rollback if ever needed: copy the .bak-pre-002 "
              "file back over labels.db.")
    else:
        print(f"\nFAIL: post-checks did not pass. Rollback: "
              f"copy {BACKUP} {DB}  (then investigate before re-running)")
        sys.exit(1)


if __name__ == "__main__":
    main()
