import sqlite3, sys
cx = sqlite3.connect("labels.db")
r = cx.execute("SELECT thread_text_redacted FROM inquiries WHERE inquiry_id = ?", (sys.argv[1],)).fetchone()
print(r[0] if r else "not found")