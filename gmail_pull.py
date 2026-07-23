"""gmail_pull.py -- GP-v1 read-only Gmail fetch for Typeform notification intake.

Finds the latest Typeform notification email in the catering inbox, shows a
preview (sender / subject / date / snippet) on stderr, asks for a y/N confirm,
then writes the email body to stdout as UTF-8 bytes.

Designed to be the left side of a pipe into pilot_v0.py --stdin. All preview
and prompt output goes to stderr so stdout carries ONLY the email body.

Usage (pipe runs from eval\\ so pilot keeps its required cwd; both
interpreters explicit -- .venv for this script, venv for pilot):

  ..\\.venv\\Scripts\\python.exe ..\\gmail_pull.py | ..\\venv\\Scripts\\python.exe pilot_v0.py --stdin

Modes:
  (no args)   fetch newest match, preview, confirm, emit body
  --list N    print the last N matches with indices to stderr, emit nothing
  --pick I    fetch match at index I (same ordering --list shows; 0 = newest)

Hard constraints (GP-v1):
  - READ-ONLY Gmail scope. No send, no label-write, no delete, no archive.
  - Raw email text is never written to any file. Body goes to stdout only;
    preview goes to the terminal (stderr). No logging.
  - credentials.json / token.json live next to this script (repo root),
    both gitignored. Paths resolve from the script's own location, not cwd.
"""

import argparse
import base64
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only. Changing this scope is out of contract for this tool.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Fixed Typeform notification anchor. Subject template is stable per form.
QUERY = 'subject:"New response for YBG Event QuoteBot"'

ROOT = Path(__file__).resolve().parent
CREDS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"


def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                sys.exit(
                    f"credentials.json not found at {CREDS_PATH} -- "
                    "copy the OAuth client file from the exporter setup"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def _walk_parts(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            yield from _walk_parts(part)
    else:
        yield payload


def extract_body(msg):
    """Prefer text/plain; fall back to a crude tag-strip of text/html."""
    plain = None
    html = None
    for part in _walk_parts(msg["payload"]):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if not data:
            continue
        text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        if mime == "text/plain" and plain is None:
            plain = text
        elif mime == "text/html" and html is None:
            html = text
    if plain and plain.strip():
        return plain
    if html and html.strip():
        import html as htmllib
        import re

        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</p>", "\n\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        return htmllib.unescape(text)
    return None


def _headers(msg):
    return {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}


def _err(line=""):
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def confirm(prompt):
    sys.stderr.write(prompt)
    sys.stderr.flush()
    try:
        answer = input().strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def main():
    ap = argparse.ArgumentParser(
        description="Read-only fetch of the latest Typeform notification body to stdout."
    )
    ap.add_argument("--list", type=int, metavar="N", dest="list_n",
                    help="list the last N matches with indices, emit nothing")
    ap.add_argument("--pick", type=int, metavar="I", default=None,
                    help="fetch match at index I (0 = newest, same order as --list)")
    args = ap.parse_args()

    if args.list_n is not None and args.list_n < 1:
        ap.error("--list N must be >= 1")
    if args.pick is not None and args.pick < 0:
        ap.error("--pick I must be >= 0")

    service = get_service()

    want = args.list_n if args.list_n is not None else (args.pick or 0) + 1
    resp = service.users().messages().list(
        userId="me", q=QUERY, maxResults=want
    ).execute()
    msgs = resp.get("messages", [])
    if not msgs:
        sys.exit("no messages matched the Typeform notification query -- nothing fetched")

    if args.list_n is not None:
        for i, m in enumerate(msgs):
            meta = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            h = _headers(meta)
            _err(f"[{i}] {h.get('Date', '?')}")
            _err(f"    From: {h.get('From', '?')}")
            _err(f"    Subj: {h.get('Subject', '?')}")
            _err(f"    {meta.get('snippet', '')[:100]}")
        return

    idx = args.pick or 0
    if idx >= len(msgs):
        sys.exit(f"--pick {idx} out of range -- only {len(msgs)} match(es) returned")

    msg = service.users().messages().get(
        userId="me", id=msgs[idx]["id"], format="full"
    ).execute()
    h = _headers(msg)

    _err("-" * 68)
    _err(f"From: {h.get('From', '?')}")
    _err(f"Subj: {h.get('Subject', '?')}")
    _err(f"Date: {h.get('Date', '?')}")
    _err(f"Snip: {msg.get('snippet', '')[:120]}")
    _err("-" * 68)
    if not confirm("Pipe this email body to pilot? [y/N] "):
        sys.exit("aborted by operator -- nothing written to stdout")

    body = extract_body(msg)
    if not body or not body.strip():
        sys.exit("matched message has no extractable text body -- aborting, nothing written")

    sys.stdout.buffer.write(body.encode("utf-8"))


if __name__ == "__main__":
    main()
