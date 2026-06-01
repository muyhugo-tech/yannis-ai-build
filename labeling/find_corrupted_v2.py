"""find_corrupted_v2.py — narrower scan: only flag threads where the model
clearly REPLIED instead of redacting (output starts with talkback phrasing,
or contains no '## Message' header at all)."""
import sqlite3

cx = sqlite3.connect("labels.db")
rows = cx.execute("SELECT inquiry_id, length(thread_text_redacted), thread_text_redacted FROM inquiries").fetchall()

# A real redacted thread should contain '## Message' (the per-message header).
# If it doesn't, the redactor did something weird.
NO_HEADER = []
TALKBACK_START = []
TALKBACK_PHRASES = (
    "i need the", "i'm ready", "i am ready", "i cannot process",
    "please provide", "the input you provided", "the text you provided",
    "i'll process", "according to my instructions",
)

for inquiry_id, length, body in rows:
    if "## Message" not in body:
        NO_HEADER.append((inquiry_id, length, body[:200]))
        continue
    # Look at the first ~150 chars before the first ## Message header.
    head_end = body.find("## Message")
    head = body[:head_end].strip().lower()
    if head and any(p in head for p in TALKBACK_PHRASES):
        TALKBACK_START.append((inquiry_id, length, body[:300]))

print(f"total threads scanned: {len(rows)}")
print(f"missing ## Message header (very suspicious): {len(NO_HEADER)}")
print(f"talkback before first ## Message (corrupted): {len(TALKBACK_START)}")
print()

if NO_HEADER:
    print("=== NO HEADER (likely corrupted or one-message thread without ## structure) ===")
    for inquiry_id, length, preview in NO_HEADER:
        print(f"  {inquiry_id}  ({length} chars)")
        print(f"    preview: {preview!r}")
        print()

if TALKBACK_START:
    print("=== TALKBACK PREFIX (definitely corrupted) ===")
    for inquiry_id, length, preview in TALKBACK_START:
        print(f"  {inquiry_id}  ({length} chars)")
        print(f"    preview: {preview!r}")
        print()
