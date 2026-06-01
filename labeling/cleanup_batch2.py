import sqlite3
c = sqlite3.connect("labels.db")
n = c.execute("DELETE FROM inquiries WHERE redaction_status='names_unredacted'").rowcount
c.commit()
print(f"deleted {n}")
c.close()
