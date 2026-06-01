import sqlite3
cx = sqlite3.connect("labels.db")
total = cx.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
by_type = cx.execute("""
    SELECT inquiry_type, COUNT(*) FROM labels l
    WHERE labeled_at = (SELECT MAX(labeled_at) FROM labels WHERE inquiry_id = l.inquiry_id)
    GROUP BY inquiry_type
""").fetchall()
print(f"total: {total}")
for t, c in by_type: print(f"  {t}: {c}")