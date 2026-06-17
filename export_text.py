"""export_text.py -- pure text processing for the Gmail exporter.

Extracted from export_threads.py (Session D, option-C fixes F2+F3) so the
quote-stripping and HTML handling are stdlib-only and testable from the
Anthropic venv (where pytest lives) without importing the Google client
stack. export_threads.py imports from here. One implementation, no copies
-- the same discipline that killed the exporter's private redaction regex
in Session C.

The two defects these functions close (evidence: thread 18da9f17eb7c769d,
2026-06-12):

F3 -- html_to_text: Gmail HTML bodies went through a crude tag-strip that
  (a) inserted no newlines at block boundaries, collapsing whole replies
  onto one physical line, and (b) never decoded entities, leaving &nbsp;
  / &lt; / &gt; literals in exports. The collapse is what blinded the
  line-based quote stripper (defect F2's trigger).

F2 -- strip_inline_quotes: the line-based stripper cuts at the first LINE
  matching a quote marker. Collapsed bodies carry the markers mid-line
  ('...help with this!LauraSent from my iPhoneOn Feb 15, 2024, at 8:52
  AM, ... wrote:'), so nothing matched and entire quoted chains -- the
  densest customer-name surface -- survived into exports. This pass cuts
  at the first INLINE marker. Conservative by design: the On-pattern
  requires a date shape AND 'wrote:' within close range, so prose like
  'On Friday we wrote the plan' is never cut.
"""
import re
from html import unescape

# ---------------------------------------------------------------------------
# Line-based pass (pre-existing behavior, plus the forwarded-message ruler,
# which starts with '-' and matched nothing in the old pattern).
# ---------------------------------------------------------------------------

QUOTED_LINE_RE = re.compile(
    r"^(>+|On .* wrote:|From: .*|Sent: .*|To: .*|Subject: .*"
    r"|-{5,}\s*Forwarded message\s*-{3,})"
)


def strip_quoted_replies(body: str) -> str:
    """Cut everything from the first quoted-reply LINE onward.

    Heuristic and imperfect, but catches the most common Gmail/Outlook
    patterns when the body has real line structure. Collapsed single-line
    bodies are handled by strip_inline_quotes below.
    """
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        if QUOTED_LINE_RE.match(line.strip()):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# Inline pass (F2). Markers built against the literal failing formats from
# thread 18da9f17eb7c769d, not imagined ones:
#   Apple:  'On Feb 15, 2024, at 8:52 AM, Yanni's Catering <...> wrote:'
#   Gmail:  'On Wed, Feb 14, 2024 at 15:26 [name] <...> wrote:'
#   Device: '...help with this![name]Sent from my iPhoneOn Feb 15...'
#   Ruler:  '---------- Forwarded message ---------'
# ---------------------------------------------------------------------------

INLINE_QUOTE_MARKERS = (
    # Date-shaped 'On <Mon> <d>, <yyyy> ... wrote:' (optional weekday, optional
    # comma before 'at', 12h or 24h time). 'wrote:' REQUIRED within 120 chars
    # of the timestamp -- the conservative gate against cutting real prose.
    re.compile(
        r"On (?:[A-Z][a-z]{2}, )?[A-Z][a-z]{2} \d{1,2}, \d{4},? at "
        r"\d{1,2}:\d{2}[^\n]{0,120}?wrote:"
    ),
    # Device signatures. Nothing legitimate follows these; in collapsed
    # bodies the quoted chain is glued directly after.
    re.compile(r"Sent from my iP(?:hone|ad)"),
    # Forwarded-message ruler, mid-line.
    re.compile(r"-{5,}\s*Forwarded message\s*-{3,}"),
)


def strip_inline_quotes(body: str) -> str:
    """Cut the body at the earliest inline quote marker, if any."""
    cut = len(body)
    for rx in INLINE_QUOTE_MARKERS:
        m = rx.search(body)
        if m:
            cut = min(cut, m.start())
    return body[:cut].rstrip()


# ---------------------------------------------------------------------------
# HTML handling (F3).
# ---------------------------------------------------------------------------

_BR_RE = re.compile(r"(?i)<\s*br\s*/?\s*>")
_BLOCK_CLOSE_RE = re.compile(r"(?i)</\s*(?:p|div|tr|li|h[1-6]|blockquote)\s*>")
_TAG_RE = re.compile(r"<[^>]+>")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


def html_to_text(html_str: str) -> str:
    """Convert an HTML body to plain text, preserving line structure.

    Order is deliberate:
      1. block-level boundaries (<br>, </p>, </div>, ...) become newlines
         BEFORE tags are stripped -- this is what un-collapses single-line
         bodies and lets the line-based quote pass see its markers again;
      2. strip remaining tags;
      3. unescape entities LAST, so '&lt;div&gt;' in genuine text decodes
         to literal '<div>' without ever being treated as a strippable tag;
      4. normalize the residue: NBSP -> space, BOM / zero-width chars out,
         3+ blank lines collapsed.
    """
    text = _BR_RE.sub("\n", html_str)
    text = _BLOCK_CLOSE_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    for zw in ("\ufeff", "\u200b", "\u200c", "\u200d"):
        text = text.replace(zw, "")
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def clean_body(body: str) -> str:
    """Full body cleanup: line-based quote pass, then the inline backstop.

    The exporter calls this on every extracted body (plain or HTML-derived).
    """
    body = strip_quoted_replies(body)
    body = strip_inline_quotes(body)
    return body
