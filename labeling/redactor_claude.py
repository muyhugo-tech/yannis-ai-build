"""
redactor_claude.py — name / company / address stripper using the Anthropic API.

Sits in front of the deterministic gate in redact.py. Takes raw thread text,
returns the same text with personal-name spans replaced by {name}, company
names by {company}, and street addresses by {address}.

Honest limit: this is a model call. Recall on unusual names or company names
that look like ordinary words is imperfect. Two backstops behind it:
  1. The deterministic gate in redact.py re-scans for structured PII.
  2. You read the redacted thread when labeling — flag and re-redact anything
     that slipped through.
"""
import os
import ssl
import httpx
import truststore
from anthropic import Anthropic
from dotenv import load_dotenv

# Load .env from project root (one level up from labeling/).
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_MODEL = "claude-sonnet-4-5"   # recall over speed at this volume
_CLIENT = None

def _client():
    global _CLIENT
    if _CLIENT is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set. Check .env in project root.")
        # Use the OS trust store. Python 3.14 ships OpenSSL 3.0 which rejects
        # the Anthropic/Cloudflare chain certifi presents with "Basic
        # Constraints of CA cert not marked critical". Windows schannel
        # accepts the same chain, so route through truststore.
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        _CLIENT = Anthropic(
            http_client=httpx.Client(verify=ctx, timeout=httpx.Timeout(60.0)),
            max_retries=3,
        )
    return _CLIENT

_SYSTEM = """You clean and redact email thread text for a labeling pipeline. You do two jobs in one pass: remove personal identifiers, and strip noise the exporter left behind.

JOB 1 — REDACT personal identifiers. Replace these spans with the exact placeholder tokens shown:
- Personal names of customers, contacts, or signers (first names, last names, full names, nicknames, initials used as names) → {name}
- Company, organization, or business names that identify a customer entity → {company}
- Customer street addresses (street number + street name, suite numbers, full mailing addresses) → {address}

Do NOT redact:
- The restaurant's own name (Yanni's, Yanni's Bar & Grill, Yanni's Bar and Grill, YBG, YBG Catering, Yanni's Catering)
- The restaurant's own street address (12015 Scripps Highlands Drive / Dr, San Diego, CA 92131) — leave it alone, it's a published business address
- Staff/operator names: Hugo, Brenna, Jonathan, Jonah, Denise, Yanni — leave these alone
- Generic words ("the manager", "the office", "the team")
- City names, neighborhood names, region names (Scripps Ranch, Sorrento Valley, San Diego, etc.) — operational context
- Dates, times, dollar amounts, guest counts
- Email addresses, phone numbers, URLs — already tokenized as {email}/{phone}/{url} by a separate pass; leave existing tokens alone

JOB 2 — STRIP exporter noise:
- Remove quoted newsletter/marketing content. If a message contains a quoted Yanni's newsletter (signs: marketing copy about menu items, wine features, MJML/CSS class names like .mj-column-per-100, "View online version", "Unsubscribe here", multi-paragraph promotional content quoted under the customer's reply), drop the entire quoted newsletter block. Keep the customer's actual reply text above it.
- Remove quoted reply-chain headers like "On [date], [name] <[email]> wrote:" — these add no signal once the prior message is dropped.
- Decode HTML entities to their characters: &amp; → &, &nbsp; → space, &lt; → <, &gt; → >, &#39; → ', etc.
- Fix common mojibake from misencoded UTF-8: â€™ → ', â€œ → ", â€ → ", â€" → —, â€" → –, â€¦ → ..., Ã© → é, etc. Use judgment — if a string of garbage characters obviously represents a known punctuation mark or accented letter, fix it.
- Collapse runs of 3+ consecutive non-breaking-space or whitespace-only lines into a single blank line.
- Leave the structural ## Message N / **From:** / **Date:** headers intact.

OUTPUT RULES:
- Return ONLY the cleaned, redacted text. No preamble, no explanation, no markdown fencing.
- Preserve the ## Message N structure and the From/Date headers for each message.
- If the input has no PII and no noise to strip, return it unchanged.
- When uncertain whether a token is a name, prefer to redact. When uncertain whether content is newsletter cruft vs. the customer's actual message, prefer to keep it — false-positive {name} is safe, but accidentally dropping a customer's message is not.

CRITICAL — DO NOT INVENT CONTENT:
- NEVER add content that was not in the input. Do not write example emails. Do not generate plausible threads. Do not improvise.
- If the input does not look like an email thread (no ## Message header, just a short string, a fragment, or a subject line), return the input UNCHANGED.
- If you genuinely have no thread to redact, return the input verbatim. Returning a short string unchanged is correct; making one up is forbidden.
- Your output should never be substantially longer than the input. The job is to clean and redact, not to expand."""

def redactor(text: str) -> str:
    """Single-call redaction. Returns redacted text or raises on API failure."""
    if not text.strip():
        return text
    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=8000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    # Concatenate text blocks (usually one).
    out = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    return out if out else text
