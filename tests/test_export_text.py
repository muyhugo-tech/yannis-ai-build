"""test_export_text.py -- F2/F3 fixes proven against the real defect formats.

Fixture strings are sanitized reconstructions of thread 18da9f17eb7c769d
(2026-06-12): structure and formats byte-faithful, customer names replaced
with 'Jane Stand-In' / 'Jane'. Staff names (Yanni's Catering) kept -- they
are public operator identity, not customer PII, and allowlist behavior
elsewhere depends on them.

Run from repo root in venv (the Anthropic one, where pytest lives):
    python -m pytest tests\\test_export_text.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_text import (  # noqa: E402
    clean_body,
    html_to_text,
    strip_inline_quotes,
    strip_quoted_replies,
)


# ---------------------------------------------------------------------------
# F2 -- inline quote markers (the collapsed single-line defect)
# ---------------------------------------------------------------------------

# The literal failing shape: customer text, glued signature, device sig,
# Apple-style quote header, then the whole prior chain on ONE line.
COLLAPSED_APPLE = (
    "Thank you Hugo.\xa0Last year we had numbers in the 70\u2019s. "
    "We are hoping for 100 but\u2026 you never know as that\u2019s a big jump. "
    "We know you are busy.\xa0Thanks for your help with this!Jane"
    "Sent from my iPhoneOn Feb 15, 2024, at 8:52 AM, Yanni's Catering "
    "<ybgcatering@gmail.com> wrote:\ufeffHi Jane, we have not yet put together "
    "a floor plan as I would like to be accurate with the numbers"
)

# Gmail-style inline header deeper in the same chain.
COLLAPSED_GMAIL = (
    "some reply textOn Wed, Feb 14, 2024 at 15:26 Jane Stand-In "
    "<jane@example.com> wrote:HI Denise and Hugo,Things are really coming "
    "together for our event"
)


def test_apple_style_chain_cut_at_device_signature():
    out = strip_inline_quotes(COLLAPSED_APPLE)
    # Everything from the device signature onward is gone...
    assert "Sent from my iPhone" not in out
    assert "wrote:" not in out
    assert "floor plan" not in out
    # ...and the customer's own message survives intact, including the glued
    # signature name (names die at INGEST, not export -- by design).
    assert out.endswith("Thanks for your help with this!Jane")
    assert "hoping for 100" in out


def test_gmail_style_inline_header_cut():
    out = strip_inline_quotes(COLLAPSED_GMAIL)
    assert out == "some reply text"
    assert "Jane Stand-In" not in out


def test_forwarded_ruler_cut_inline():
    body = "real content here---------- Forwarded message ---------From: x"
    assert strip_inline_quotes(body) == "real content here"


def test_prose_with_wrote_not_cut():
    # No date shape -> never cut, even with 'wrote:' present.
    body = "She wrote: the menu looks great. On Friday we wrote the plan."
    assert strip_inline_quotes(body) == body


def test_date_shape_without_wrote_not_cut():
    # Date shape but no 'wrote:' within range -> a real sentence, keep it.
    body = "On Feb 15, 2024, at 8:52 AM we will arrive for setup."
    assert strip_inline_quotes(body) == body


def test_24h_time_gmail_variant():
    body = "okOn Wed, Feb 14, 2024 at 15:26 Jane <j@x.com> wrote:old text"
    assert strip_inline_quotes(body) == "ok"


# ---------------------------------------------------------------------------
# F2 regression -- the line-based pass still works where it always did
# ---------------------------------------------------------------------------

def test_linewise_quote_still_cut():
    body = "Sounds great, see you then.\n\nOn Feb 15, 2024 Hugo wrote:\n> hi"
    assert strip_quoted_replies(body) == "Sounds great, see you then."


def test_forwarded_ruler_cut_linewise():
    body = "keep this\n---------- Forwarded message ---------\nFrom: x"
    assert strip_quoted_replies(body) == "keep this"


# ---------------------------------------------------------------------------
# F3 -- HTML to text
# ---------------------------------------------------------------------------

def test_block_tags_become_newlines_uncollapsing_body():
    html = "<div>Thank you Hugo.</div><div>On Feb 15, 2024, at 8:52 AM, X wrote:</div><div>old</div>"
    text = html_to_text(html)
    assert text.splitlines()[0] == "Thank you Hugo."
    # Un-collapsed: the line-based pass can now see the marker.
    assert strip_quoted_replies(text) == "Thank you Hugo."


def test_br_becomes_newline():
    assert html_to_text("line one<br>line two") == "line one\nline two"


def test_entities_decoded_and_nbsp_normalized():
    assert html_to_text("Thank&nbsp;you &lt;3 &amp; more") == "Thank you <3 & more"


def test_unescape_after_tagstrip_keeps_escaped_markup_literal():
    # '&lt;div&gt;' is genuine text, not markup: must survive as '<div>'.
    assert html_to_text("see the &lt;div&gt; element") == "see the <div> element"


def test_bom_and_zero_width_stripped():
    assert html_to_text("\ufeffHi\u200b there") == "Hi there"


# ---------------------------------------------------------------------------
# End to end: the real defect shape through the full cleanup
# ---------------------------------------------------------------------------

def test_collapsed_html_body_end_to_end():
    # The whole message-3 failure: HTML with no block structure for the
    # chain, entities, BOM, device sig, Apple header -- one line.
    html = (
        "<div>Thank you Hugo.&nbsp;Last year we had numbers in the "
        "70&#8217;s. Thanks for your help with this!Jane"
        "Sent from my iPhoneOn Feb 15, 2024, at 8:52 AM, Yanni's Catering "
        "&lt;ybgcatering@gmail.com&gt; wrote:&#65279;Hi Jane, old chain text"
        "On Wed, Feb 14, 2024 at 15:26 Jane Stand-In &lt;jane@example.com&gt; "
        "wrote:HI Denise and Hugo, oldest text</div>"
    )
    out = clean_body(html_to_text(html))
    assert "wrote:" not in out
    assert "old chain text" not in out
    assert "oldest text" not in out
    assert "Jane Stand-In" not in out
    assert "Sent from my iPhone" not in out
    assert "Thank you Hugo." in out
    assert "Thanks for your help with this!Jane" in out
