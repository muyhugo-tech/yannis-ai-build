"""test_redact_allowlist.py -- F6: two-tier allowlist coverage.

Proves the surname-leak fix: a staff first name alone survives, but the same
first name plus a customer surname redacts the surname. Org phrases survive
whole; a customer full name redacts. Fixtures use placeholder names only
(no real customer PII). 'Pihas' here is a stand-in surname, not real data.

Run from repo root in venv (Anthropic, where pytest lives):
    python -m pytest tests\\test_redact_allowlist.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "labeling"))

from redact import deterministic_redact, is_allowlisted  # noqa: E402


# ---------------------------------------------------------------------------
# is_allowlisted -- the coverage rule directly
# ---------------------------------------------------------------------------

def test_staff_first_name_only_survives():
    assert is_allowlisted("Hugo") is True
    assert is_allowlisted("Brenna") is True
    assert is_allowlisted("Denise") is True


def test_staff_first_name_plus_surname_not_covered():
    # The F6 case: 'denise' must not wave through a CUSTOMER surname.
    assert is_allowlisted("Denise Romero") is False
    assert is_allowlisted("Hugo Stand-In") is False


def test_staff_full_names_survive():
    # Full staff names are explicit allowlist phrases so the staff SURNAME
    # survives (operator-vs-customer channel signal in the From line).
    assert is_allowlisted("Brenna Fineman") is True
    assert is_allowlisted("Jonathan Gutierrez") is True
    assert is_allowlisted("Yannis Pihas") is True
    assert is_allowlisted("Denise Pihas") is True


def test_comma_reversed_staff_full_name_survives():
    # Quoted "Lastname, First" format (the probe found "{name-17}, Jonah").
    # Phrase matching is order-independent so the staff full name still
    # covers when reversed.
    assert is_allowlisted("Pihas, Denise") is True


def test_org_noise_phrases_survive():
    # Real org slots carry leading/trailing noise words; the exact strings
    # are explicit allowlist phrases (Option A).
    assert is_allowlisted("Typeform Notifications") is True
    assert is_allowlisted("Toast Sites Forms") is True
    assert is_allowlisted("The New York Times") is True
    assert is_allowlisted("Typeform") is True  # bare stem still works


def test_org_phrase_survives_whole():
    assert is_allowlisted("New York Times") is True
    assert is_allowlisted("Toast Sites") is True
    assert is_allowlisted("Hospitality Headline") is True


def test_customer_full_name_redacts():
    assert is_allowlisted("Jane Stand-In") is False


# ---------------------------------------------------------------------------
# Normalization edges
# ---------------------------------------------------------------------------

def test_apostrophe_normalized_for_yannis():
    # Slot reads "Yanni's Catering"; allowlist has "yannis catering".
    assert is_allowlisted("Yanni's Catering") is True
    # And the bare possessive staff token.
    assert is_allowlisted("Yanni's") is True


def test_single_org_token_not_loosely_allowlisted():
    # Org phrases must match whole. A standalone 'us' / 'manager' / 'office'
    # token from a multi-word entry must NOT allowlist a customer slot.
    assert is_allowlisted("Office Manager Smith") is False
    assert is_allowlisted("Times Square") is False


# ---------------------------------------------------------------------------
# End to end through the header pass
# ---------------------------------------------------------------------------

def test_header_redacts_surname_keeps_staff():
    text = (
        "**From:** Denise Romero <{email}>\n"
        "**From:** Hugo <{email}>\n"
        "**From:** Brenna Fineman <{email}>\n"
        "**From:** New York Times <{email}>\n"
        "**From:** Jane Stand-In <{email}>\n"
    )
    out = deterministic_redact(text)
    # Customer slots: surname-bearing 'Romero' (shares staff first name) and
    # the pure customer 'Jane Stand-In' both redact.
    assert "Romero" not in out
    assert "Stand-In" not in out
    # Staff (first-name-only and full-name) and org survive.
    assert "**From:** Hugo <{email}>" in out
    assert "**From:** Brenna Fineman <{email}>" in out
    assert "**From:** New York Times <{email}>" in out
    # The two customer slots collapse to {name}.
    assert out.count("**From:** {name} <{email}>") == 2


def test_idempotent_on_already_redacted():
    text = "**From:** {name} <{email}>\n"
    assert deterministic_redact(text) == text
