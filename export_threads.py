"""
Gmail thread exporter for Yanni's catering inquiry research.

Pulls inquiry threads from ybgcatering@gmail.com, strips quoted reply chains,
applies light PII redaction (emails, phones, URLs), and writes each thread
to a single markdown file under the chosen output folder.

Read-only Gmail access. Cannot modify, delete, or send mail.

2026-06-12 (Session D): date window, output folder, and max-results moved
from hardcoded constants to CLI args (--after/--before/--out/--max).

2026-06-12 (option C, F2+F3): text processing moved to export_text.py
(stdlib-only, testable from the Anthropic venv). Fixes proven on thread
18da9f17eb7c769d: inline quote-chain stripping for single-line HTML-collapsed
bodies, block-tag newline restoration, entity decoding, BOM/zero-width
stripping. The redaction path (labeling/redact.py import) is UNTOUCHED.

Usage (run from repo root, .venv -- the Google one):
    python export_threads.py --after 2024/01/01 --before 2024/04/01 \
        --out threads_batch3 --max 40
"""

import argparse
import base64
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Text processing: ONE implementation, in export_text.py (F2/F3 fixes live
# there with their tests). This module only composes it.
from export_text import clean_body, html_to_text

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
INTERNAL_ADDRESSES_FILE = "internal_addresses.txt"

# Gmail date format for after:/before: query parts. before: is EXCLUSIVE.
GMAIL_DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")

# Base Gmail query. Filters at the server side for inbound traffic to the
# catering inbox, excluding clear-noise sources. Internal staff addresses
# are appended dynamically from internal_addresses.txt. Date window is
# appended from --after/--before.
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


def build_query(after: str, before: str) -> str:
    """Build the full Gmail query: base parts + date window + internal
    address exclusions."""
    parts = list(BASE_QUERY_PARTS)
    parts.append(f"after:{after}")
    parts.append(f"before:{before}")
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
# 2026-06-11: the exporter's private regex copy is GONE. It silently diverged
# from labeling/redact.py (no header display-name pass) and caused the
# customer-name leak fixed in Session C. One redaction pipeline, one file:
# labeling/redact.py. This module only imports it.
#
# deterministic_redact() runs over the FULLY ASSEMBLED markdown (not per
# fragment) because redact_headers() matches the '**From:** name <email>'
# line shape, which only exists after assembly.
#
# redact.py is stdlib-only (re), so importing it from the Google-API .venv
# is safe. Path assumption: labeling/ is a sibling of this script.

sys.path.insert(0, str(Path(__file__).resolve().parent / "labeling"))
from redact import deterministic_redact  # noqa: E402


# ---------------------------------------------------------------------------
# Email parsing
# ---------------------------------------------------------------------------

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

    # Fallback: HTML body through the F3 pipeline (block tags -> newlines,
    # tag strip, entity decode, BOM/zero-width cleanup). Replaces the old
    # crude tag-strip that collapsed bodies onto one line and left &nbsp;
    # literals in exports.
    if payload.get("mimeType") == "text/html":
        return html_to_text(decode_body(payload))

    return ""


def header_value(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def collect_attachment_exts(payload) -> list[str]:
    """Walk a Gmail payload tree, return extensions of attachment parts.

    A part is an attachment if it carries a filename. We emit EXTENSIONS
    ONLY, never filenames: customer file names are a PII channel ('{name}
    Wedding Contract.pdf') that the deterministic redaction layer cannot
    close. Count + extension preserves the 'something was here' signal
    (fixing the silent body-drop defect) with zero new PII surface.
    """
    exts = []
    filename = payload.get("filename", "")
    if filename:
        dot = filename.rfind(".")
        exts.append(filename[dot:].lower() if dot != -1 else "(no extension)")
    for part in payload.get("parts", []) or []:
        exts.extend(collect_attachment_exts(part))
    return exts


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

    # Frontmatter is STRUCTURAL and stays out of the redaction pass:
    # thread_id is the filename and join key; a digit-heavy id would get
    # eaten by the payment-run regex (caught in testing). Only the subject
    # is customer-supplied text, so it alone gets redacted here.
    frontmatter = [
        "---",
        f"thread_id: {thread_id}",
        f"subject: {deterministic_redact(first_subject)}",
        f"message_count: {len(messages)}",
        f"date_range: {first_date} / {last_date}",
        f"labels: {labels}",
        f"operator_replied: {operator_replied}",
        "---",
        "",
    ]

    msg_lines = []
    for i, msg in enumerate(messages, start=1):
        headers = msg["payload"]["headers"]
        sender = header_value(headers, "From")
        date = header_value(headers, "Date")
        body = extract_plain_text(msg["payload"])
        # F2: line-based quote pass + inline backstop for collapsed bodies.
        body = clean_body(body)
        att_exts = collect_attachment_exts(msg["payload"])

        msg_lines.append(f"## Message {i}")
        msg_lines.append(f"**From:** {sender}")
        msg_lines.append(f"**Date:** {date}")
        msg_lines.append("")
        if body:
            msg_lines.append(body)
        elif att_exts:
            # Body-drop fix: attachment-only / image-only messages used to
            # read as '_(no body extracted)_' with no hint anything existed.
            msg_lines.append(
                f"_(no text body; {len(att_exts)} attachment(s): "
                f"{', '.join(att_exts)})_"
            )
        else:
            msg_lines.append("_(no body extracted)_")
        if body and att_exts:
            msg_lines.append(
                f"_({len(att_exts)} attachment(s): {', '.join(att_exts)})_"
            )
        msg_lines.append("")

    # ONE redaction pass over the assembled MESSAGE block. Deliberate:
    # redact_headers() needs the '**From:** name <email>' line shape, which
    # only exists post-assembly. Covers senders and bodies in the same pass:
    # emails, phones, payment-like runs, URLs, and From/To display-names
    # (staff/vendor allowlist survives).
    full_text = "\n".join(frontmatter) + "\n" + deterministic_redact("\n".join(msg_lines))

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{thread_id}.md"
    out_path.write_text(full_text, encoding="utf-8")

    return {
        "thread_id": thread_id,
        "skipped": False,
        "message_count": len(messages),
        "operator_replied": operator_replied,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Export Gmail catering threads to redacted .md files."
    )
    p.add_argument("--after", required=True,
                   help="Gmail after: date, YYYY/MM/DD (inclusive)")
    p.add_argument("--before", required=True,
                   help="Gmail before: date, YYYY/MM/DD (EXCLUSIVE)")
    p.add_argument("--out", required=True,
                   help="Output folder for .md files, e.g. threads_batch3")
    p.add_argument("--max", type=int, default=40,
                   help="Max threads to pull this run (default 40)")
    args = p.parse_args()
    for label, val in (("--after", args.after), ("--before", args.before)):
        if not GMAIL_DATE_RE.match(val):
            p.error(f"{label} must be YYYY/MM/DD, got {val!r}")
    return args


def main():
    args = parse_args()
    output_dir = Path(args.out)

    print(f"Starting export at {datetime.now().isoformat()}")
    print(f"Window: after {args.after} / before {args.before} (exclusive)  "
          f"-> {output_dir}  (max {args.max})")
    service = get_gmail_service()
    print("Authenticated. Running Gmail query...")

    query = build_query(args.after, args.before)
    print(f"Query: {query}")
    results = service.users().threads().list(
        userId="me",
        q=query,
        maxResults=args.max,
    ).execute()

    threads = results.get("threads", [])
    print(f"Found {len(threads)} threads matching query.")

    stats = []
    for i, t in enumerate(threads, start=1):
        print(f"[{i}/{len(threads)}] exporting {t['id']}...")
        stats.append(export_thread(service, t["id"], output_dir))

    exported = [s for s in stats if not s.get("skipped")]
    with_reply = sum(1 for s in exported if s.get("operator_replied"))
    without_reply = len(exported) - with_reply

    print("")
    print("=" * 50)
    print(f"Exported: {len(exported)} threads")
    print(f"  Operator replied: {with_reply}")
    print(f"  No operator reply: {without_reply}")
    print(f"Output folder: {output_dir.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
