# show_next.py -- READ-ONLY. Prints the oldest verified, unlabeled inquiry
# so it can be reviewed before labeling. No writes, no API.
#
# Run from labeling\ :  python show_next.py
# (Pass an inquiry_id to show a specific one: python show_next.py <id>)

import sqlite3
import sys

DB = "labels.db"

cx = sqlite3.connect(DB)
cx.row_factory = sqlite3.Row

if len(sys.argv) > 1:
    r = cx.execute(
        "SELECT inquiry_id, subject_redacted, message_count, date_range_start, "
        "thread_text_redacted FROM inquiries WHERE inquiry_id=?",
        (sys.argv[1],),
    ).fetchone()
else:
    r = cx.execute(
        "SELECT i.inquiry_id, i.subject_redacted, i.message_count, "
        "i.date_range_start, i.thread_text_redacted "
        "FROM inquiries i LEFT JOIN labels l ON l.inquiry_id = i.inquiry_id "
        "WHERE l.label_id IS NULL AND i.redaction_status='verified' "
        "ORDER BY i.ingested_at LIMIT 1"
    ).fetchone()
cx.close()

if r is None:
    print("nothing to show (no verified, unlabeled inquiries)")
    raise SystemExit

print("=" * 70)
print(f"INQUIRY {r['inquiry_id']}  ({r['message_count']} msgs, {r['date_range_start']})")
print(f"subject: {r['subject_redacted']}")
print("=" * 70)
print(r["thread_text_redacted"])
print("=" * 70)
