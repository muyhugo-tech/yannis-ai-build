"""
Gmail thread exporter for Yanni's catering inquiry research.

Pulls inquiry threads from ybgcatering@gmail.com, strips quoted reply chains,
applies light PII redaction (emails, phones, URLs), and writes each thread
to a single markdown file under threads/.

Read-only Gmail access. Cannot modify, delete, or send mail.
"""

import base64
import os
import re
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
INTERNAL_ADDRESSES_FILE = "internal_addresses.txt"
OUTPUT_DIR = Path("threads_batch2")  # batch 2 -- separate folder from batch 1
MAX_THREADS = 80  # batch 2: pull a surplus, drop noise, keep ~50 labelable

# Base Gmail query. Filters at the server side for inbound traffic to the
# catering inbox, excluding clear-noise sources. Internal staff addresses
# are appended dynamically from internal_addresses.txt.
#
# Date window for batch 2: 2025-01-01 through 2025-11-30 (Gmail before: is
# exclusive). December excluded -- it is the documented seasonal outlier
# (elevated patio minimums, holiday-party mix). Pull it as its own batch if
# wanted.
BASE_QUERY_PARTS = [
    "in:anywhere",
    "to:ybgcatering@gmail.com",
    "-from:ybgcatering@gmail.com",
    "-from:mailer-daemon@googlemail.com",
    "-from:noreply -from:no-reply",
    'subject:-"out of office"',
    'subject:-"automatic reply"',
    # Vendor platforms that send transactional mail, not catering inquiries.
    "-from:(opentable.com OR square.com OR stripe.com "
    "OR resy.com OR yelp.com OR mailchimp.com)",
    # Social platforms -- pure notification noise, never customer inquiries.
    "-from:(tiktok.com OR tiktokv.com OR facebookmail.com OR linkedin.com)",
    "after:2025/01/01",
    "before:2025/12/01",
]


def load_internal_addresses() -> list[str]:
    """Read internal staff email addresses from a local file.

    File format: one email per line, blank lines and # comments allowed.
    File is gitignored and never leaves the local machine.
    """
    if not os.path.exists(INTERNAL_ADDRESSES_FILE):
        print(f"WARNING: {INTERNAL_ADDRESSES_FILE} not found. "
              "Internal staff filtering disabled.")
        return []

    addresses = []
    with open(INTERNAL_ADDRESSES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                addresses.append(line)
    return addresses


def build_query() -> str:
    """Build the full Gmail query, appending internal-address exclusions."""
    parts = list(BASE_QUERY_PARTS)
    internal = load_internal_addresses()
    if internal:
        internal_filter = " OR ".join(internal)
        parts.append(f"-from:({internal_filter})")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_gmail_service():
    """Authenticate and return a Gmail API client.

    First run opens a browser for OAuth consent and writes token.json.
    Subsequent runs reuse token.json and refresh it silently when expired.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
)
URL_RE = re.compile(r"https?://\S+|www\.\S+")


def redact(text: str) -> str:
    """Replace emails, phones, and URLs with placeholders. Names not handled."""
    text = EMAIL_RE.sub("{email}", text)
    text = PHONE_RE.sub("{phone}", text)
    text = URL_RE.sub("{url}", text)
    return text


# ---------------------------------------------------------------------------
# Email parsing
# ---------------------------------------------------------------------------

QUOTED_LINE_RE = re.compile(
    r"^(>+|On .* wrote:|From: .*|Sent: .*|To: .*|Subject: .*)",
    re.MULTILINE,
)


def strip_quoted_replies(body: str) -> str:
    """Cut everything from the first quoted-reply marker onward.

    Heuristic and imperfect, but catches the most common Gmail/Outlook patterns.
    """
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        if QUOTED_LINE_RE.match(line.strip()):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def decode_body(part) -> str:
    """Extract a text/plain or text/html body from a Gmail message part."""
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")


def extract_plain_text(payload) -> str:
    """Walk a Gmail payload tree and return the best plain-text body found."""
    if payload.get("mimeType") == "text/plain":
        return decode_body(payload)

    for part in payload.get("parts", []) or []:
        text = extract_plain_text(part)
        if text:
            return text

    # Fallback: take HTML and strip tags crudely.
    if payload.get("mimeType") == "text/html":
        html = decode_body(payload)
        return re.sub(r"<[^>]+>", "", html)

    return ""


def header_value(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ---------------------------------------------------------------------------
# Thread export
# ---------------------------------------------------------------------------

def export_thread(service, thread_id: str, output_dir: Path) -> dict:
    """Pull a single thread, write a .md file, return summary stats."""
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="full"
    ).execute()
    messages = thread.get("messages", [])

    if not messages:
        return {"thread_id": thread_id, "skipped": True, "reason": "no messages"}

    first_subject = header_value(messages[0]["payload"]["headers"], "Subject")
    first_date = header_value(messages[0]["payload"]["headers"], "Date")
    last_date = header_value(messages[-1]["payload"]["headers"], "Date")
    labels = thread.get("messages", [{}])[0].get("labelIds", [])

    # Detect whether the operator (the catering inbox) ever sent in this thread.
    operator_replied = any(
        "ybgcatering@gmail.com" in header_value(m["payload"]["headers"], "From").lower()
        for m in messages
    )

    out_lines = [
        "---",
        f"thread_id: {thread_id}",
        f"subject: {redact(first_subject)}",
        f"message_count: {len(messages)}",
        f"date_range: {first_date} / {last_date}",
        f"labels: {labels}",
        f"operator_replied: {operator_replied}",
        "---",
        "",
    ]

    for i, msg in enumerate(messages, start=1):
        headers = msg["payload"]["headers"]
        sender = header_value(headers, "From")
        date = header_value(headers, "Date")
        body = extract_plain_text(msg["payload"])
        body = strip_quoted_replies(body)
        body = redact(body)
        sender_redacted = redact(sender)

        out_lines.append(f"## Message {i}")
        out_lines.append(f"**From:** {sender_redacted}")
        out_lines.append(f"**Date:** {date}")
        out_lines.append("")
        out_lines.append(body if body else "_(no body extracted)_")
        out_lines.append("")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{thread_id}.md"
    out_path.write_text("\n".join(out_lines), encoding="utf-8")

    return {
        "thread_id": thread_id,
        "skipped": False,
        "message_count": len(messages),
        "operator_replied": operator_replied,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Starting export at {datetime.now().isoformat()}")
    service = get_gmail_service()
    print("Authenticated. Running Gmail query...")

    query = build_query()
    print(f"Query: {query}")
    results = service.users().threads().list(
        userId="me",
        q=query,
        maxResults=MAX_THREADS,
    ).execute()

    threads = results.get("threads", [])
    print(f"Found {len(threads)} threads matching query.")

    stats = []
    for i, t in enumerate(threads, start=1):
        print(f"[{i}/{len(threads)}] exporting {t['id']}...")
        stats.append(export_thread(service, t["id"], OUTPUT_DIR))

    exported = [s for s in stats if not s.get("skipped")]
    with_reply = sum(1 for s in exported if s.get("operator_replied"))
    without_reply = len(exported) - with_reply

    print("")
    print("=" * 50)
    print(f"Exported: {len(exported)} threads")
    print(f"  Operator replied: {with_reply}")
    print(f"  No operator reply: {without_reply}")
    print(f"Output folder: {OUTPUT_DIR.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
