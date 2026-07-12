"""
crm_push.py -- v0: push one pilot decision + draft into the yannis-events CRM.

Contract (verified live 2026-07-12, smoke 201/409/201/401):
  POST {base}/api/agent/leads                 -> 201 {event} | 409 {error, event_id, status}
  POST {base}/api/agent/events/{id}/drafts    -> 201 {draft}
Auth header x-agent-key. Bodies are zod .strict(): unknown fields 400.

PII rules (binding):
  - never print a request payload
  - never print a response body (the 201 echo returns the full row, PII included)
  - never print the key
  - errors print HTTP status + short error code only, then exit nonzero
"""

import json
import os
import sys
import urllib.error
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_LEAD_FIELDS = (
    "contact_name", "company", "contact_email", "contact_phone",
    "event_type", "guest_count", "requested_date", "message",
    "gmail_thread_url",
)


def _load_env() -> dict:
    vals = {}
    try:
        with open(_ENV_PATH, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip()
    except FileNotFoundError:
        print("crm_push: .env not found at repo root", file=sys.stderr)
        raise SystemExit(1)
    return vals


def _config() -> tuple[str, str]:
    env = _load_env()
    base = env.get("CRM_BASE_URL", "").rstrip("/")
    key = env.get("AGENT_API_KEY", "")
    if not base or not key:
        print("crm_push: CRM_BASE_URL or AGENT_API_KEY missing from .env",
              file=sys.stderr)
        raise SystemExit(1)
    return base, key


def _post(url: str, key: str, payload: dict) -> tuple[int, dict]:
    """POST JSON. Returns (status, parsed body). Never prints either."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"x-agent-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {}
        return e.code, body
    except urllib.error.URLError as e:
        print(f"crm_push: transport failure ({e.reason})", file=sys.stderr)
        raise SystemExit(1)


def _fail(context: str, status: int, body: dict) -> None:
    code = body.get("error", "") if isinstance(body.get("error", ""), str) else ""
    print(f"crm_push: {context} failed, HTTP {status} {code}".rstrip(),
          file=sys.stderr)
    raise SystemExit(1)


def build_lead_payload(fields: dict) -> dict:
    """Whitelist to the zod schema; drop None/empty; contact_name required."""
    payload = {k: fields[k] for k in _LEAD_FIELDS
               if k in fields and fields[k] not in (None, "")}
    if not payload.get("contact_name"):
        print("crm_push: contact_name is required", file=sys.stderr)
        raise SystemExit(1)
    return payload


def push_lead(fields: dict) -> str:
    """Create the lead. On 409 duplicate_thread, return the existing event_id."""
    base, key = _config()
    status, body = _post(f"{base}/api/agent/leads", key,
                         build_lead_payload(fields))
    if status == 201:
        return body["event"]["id"]
    if status == 409 and body.get("error") == "duplicate_thread":
        print(f"crm_push: duplicate thread, reusing event {body['event_id']}")
        return body["event_id"]
    _fail("push_lead", status, body)


def push_draft(event_id: str, draft_body: str) -> str:
    """Attach the draft text to an event. Returns the draft id."""
    if not draft_body or len(draft_body) > 20000:
        print("crm_push: draft body empty or over 20000 chars", file=sys.stderr)
        raise SystemExit(1)
    base, key = _config()
    status, body = _post(f"{base}/api/agent/events/{event_id}/drafts", key,
                         {"body": draft_body})
    if status == 201:
        return body["draft"]["id"]
    _fail("push_draft", status, body)
