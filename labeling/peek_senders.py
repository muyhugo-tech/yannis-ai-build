import sqlite3, re
cx = sqlite3.connect("labels.db")
internal_ids = ["19e3782421ede870", "19e42a8328b68fcf", "19e4645f2e19e420",
                "19e464e455095802", "19e50ef36921c4ac", "19e5cffc1f49a729"]
for iid in internal_ids:
    r = cx.execute("SELECT subject_redacted, substr(thread_text_redacted, 1, 250) FROM inquiries WHERE inquiry_id = ?", (iid,)).fetchone()
    if r:
        # Pull the From line from the first message
        m = re.search(r"\*\*From:\*\*\s*(.+)", r[1])
        sender = m.group(1).strip() if m else "(no From line found)"
        print(f"{iid}  subject={r[0]!r}")
        print(f"  sender: {sender}")