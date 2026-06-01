"""find_corrupted.py — scan inquiries for redactor outputs that aren't real threads."""
import sqlite3

# Phrases that the model emits when it doesn't understand the input.
# If any of these appear in a stored thread, the redactor talked back
# instead of doing its job.
TELLS = [
    "I need the",
    "I'm ready to",
    "I am ready to",
    "Please provide",
    "appears to be just",
    "appears to be a subject",
    "not a complete email",
    "I cannot",
    "I'll process it",
    "according to my instructions",
    "according to the rules",
]

cx = sqlite3.connect("labels.db")
rows = cx.execute("SELECT inquiry_id, length(thread_text_redacted), thread_text_redacted FROM inquiries").fetchall()

corrupted = []
for inquiry_id, length, body in rows:
    body_lower = body.lower()
    hits = [t for t in TELLS if t.lower() in body_lower]
    if hits:
        corrupted.append((inquiry_id, length, hits, body[:200]))

print(f"total threads scanned: {len(rows)}")
print(f"corrupted (model talked back): {len(corrupted)}")
print()
for inquiry_id, length, hits, preview in corrupted:
    print(f"  {inquiry_id}  ({length} chars)  hits={hits}")
    print(f"    preview: {preview!r}")
    print()
