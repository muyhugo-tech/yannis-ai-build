import sqlite3, sys
cx = sqlite3.connect("labels.db")
r = cx.execute("SELECT subject_redacted, thread_text_redacted FROM inquiries WHERE inquiry_id = ?", (sys.argv[1],)).fetchone()
print("=== SUBJECT ===")
print(repr(r[0]))
print()
print("=== BODY (first 800 chars) ===")
print(r[1][:800])