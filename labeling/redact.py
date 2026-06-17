"""
redact.py — redaction-first gate for the labeling pipeline.

Two layers:
  1. deterministic_redact(): regex. Kills emails, phones, payment-like digit
     runs, URLs, AND From/To header display-names. This is also the
     VERIFICATION GATE — verify() re-scans output and any structured-PII
     survivor flags the thread (no label allowed).
  2. model_redact(): optional Claude pass for names / companies / addresses
     in free prose and signatures, which regex cannot do. Off unless a
     redactor callable is supplied.

Honest limit: names and companies in free prose / signatures have residual
leak risk. The deterministic gate now closes the structured header positions
(From/To display-names) where the model pass was under-redacting. The human
reading the redacted thread to label it remains the backstop for prose and
signature-block names/companies.
"""
import re

TOKENS = {
    "email":   "{email}",
    "phone":   "{phone}",
    "payment": "{payment}",
    "url":     "{url}",
    "name":    "{name}",
}

# Order matters: emails before phones (an email can contain digit runs).
_EMAIL_RE   = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE     = re.compile(r"\bhttps?://[^\s)>\]]+", re.IGNORECASE)
# Phone: NA-style with optional country code, separators . - space ( ).
_PHONE_RE   = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
# Payment: 13-16 digit runs, optionally grouped in 4s (card-like).
_PAYMENT_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")

# --- Header display-name redaction -----------------------------------------
# The exporter emits one structural line per message:
#     **From:** <displayname> <{email}>
#     **To:**   <displayname> <{email}>
# The email is already tokenized to {email} by the time this runs (or will be,
# but we match either a real address or the token to be order-independent).
# The display-name slot is everything between the header label and the angle
# bracket. We clear it to {name} UNLESS it is the restaurant's own outbound or
# a staff member — those are not customer PII and must survive.
#
# Idempotent: if the slot is already {name}, the allowlist check passes it
# through unchanged and the regex re-substitutes {name} -> {name} (no-op).

# Self / staff senders that must NOT be redacted.
#
# 2026-06-11: extended with non-personal PLATFORM/VENDOR senders found by
# probe_from_lines.py. These are not customer PII, and the sender slot is
# channel signal the agent uses (Typeform notification vs. {name} cold open).
# Rule for additions: the slot must identify an ORGANIZATION or system, never
# a person. A vendor slot containing a personal name (e.g. a first name +
# company) stays OUT and gets redacted to {name}.
#
# 2026-06-16 (F6): matching is NO LONGER a raw substring test. The old
# `any(allowed in slot.lower())` passed the WHOLE slot whenever any entry
# appeared anywhere in it, so a staff first-name token ("denise") waved
# through a customer surname ("Denise Pihas" -> "Pihas" survived). See
# is_allowlisted() below for the two-tier coverage rule that replaced it.
_ALLOWLIST = (
    # self / staff -- single first-name tokens (survive alone; a surname
    # residue redacts unless the FULL staff name is also listed below)
    "ybg",
    "hugo",
    "brenna",
    "jonathan",
    "jonah",
    "denise",
    "yanni",
    # self / staff -- full names. Listed explicitly so the staff SURNAME
    # survives (channel signal: operator-vs-customer in the From line).
    # Without these, "Brenna Fineman" -> residue "fineman" -> redacts.
    # A CUSTOMER who shares a staff first name ("Denise <other-surname>")
    # still redacts, because only these exact full names are covered.
    "yannis catering",
    "yanni's",
    "yannis bar",
    "brenna fineman",
    "jonathan gutierrez",
    "yannis pihas",
    "denise pihas",
    # platforms / vendors / newsletters -- exact org slot strings as they
    # appear in real From lines (Option A: explicit phrases, not a noise-word
    # tolerance rule). Brittle by design: a new variant leaks, the probe
    # catches it, you add one line. That visibility is the point for a PII
    # gate. Stems alone ("typeform") are kept for bare-slot variants.
    "typeform",
    "typeform notifications",
    "toast sites",
    "toast sites forms",
    "truereview",
    "unifirst",
    "hospitality headline",
    "new york times",
    "the new york times",
    "weddingpro",
    "office us",
    "business manager",
)

# Capture: (1) the header label + trailing space, (2) the display-name slot,
# (3) the opening angle bracket onward. Slot is non-greedy up to " <".
_HEADER_RE = re.compile(
    r"(\*\*(?:From|To):\*\*\s*)(.+?)(\s*<)",
)


# --- F6: two-tier allowlist coverage ----------------------------------------
# The allowlist mixes two kinds of entry that need OPPOSITE matching:
#
#   single-token staff first names  ("hugo", "denise", "yanni", ...)
#       -> match only as a STANDALONE slot token. "denise pihas" must NOT be
#          covered by "denise"; the residue "pihas" forces redaction.
#
#   multi-word org phrases  ("new york times", "toast sites", "office us", ...)
#       -> match as a WHOLE PHRASE. Shattering them into loose tokens would
#          allowlist standalone "us" / "manager" / "office", a real hole.
#
# A slot is allowlisted iff it is FULLY consumed with ZERO residue by some
# combination of (whole org-phrase matches) + (single-token matches). Any
# leftover token (a customer surname) means the slot is NOT allowlisted.
#
# Normalization (_norm_token): lowercase, drop apostrophes, strip surrounding
# punctuation. This is why "Yanni's" in a slot resolves against the entry
# "yannis" / "yanni's" -- the apostrophe is normalized away on both sides.

def _norm_token(tok: str) -> str:
    """Lowercase, remove apostrophes, strip surrounding punctuation."""
    tok = tok.lower().replace("'", "").replace("\u2019", "")
    return tok.strip(".,;:\"'()<>[]")


def _norm_slot_tokens(slot: str) -> list[str]:
    """Split a slot into normalized, non-empty tokens.
    Commas are treated as separators so quoted 'Lastname, First' slots
    tokenize the same as 'First Lastname'."""
    raw = re.split(r"[\s,]+", slot.strip())
    return [t for t in (_norm_token(r) for r in raw) if t]


# Derive the two tiers from _ALLOWLIST once, at import.
_ALLOWLIST_SINGLE = frozenset(
    _norm_token(entry) for entry in _ALLOWLIST if " " not in entry
)
_ALLOWLIST_PHRASES = tuple(
    tuple(_norm_token(t) for t in entry.split())
    for entry in _ALLOWLIST if " " in entry
)


def is_allowlisted(slot: str) -> bool:
    """True iff the display-name slot is FULLY covered (zero residue) by
    allowlisted org phrases and/or single staff tokens.

    A bare staff first name ("Denise") is covered and survives. The same
    name with a surname ("Denise Pihas") leaves a residue token ("pihas")
    and is NOT covered, so the slot redacts to {name}. This is the F6 fix:
    the old substring test waved the whole slot through on a first-name hit.

    SHARED: probe_from_lines.py imports this so the probe judges leaks with
    the exact same rule the redactor enforces. If they ever diverge, the
    probe lies (which is how F6 hid: the probe shared the old blind spot)."""
    tokens = _norm_slot_tokens(slot)
    if not tokens:
        return False
    # Consume whole org/full-name phrases, longest first so a longer phrase
    # wins over a shorter overlapping one. Matching is ORDER-INDEPENDENT
    # (multiset subset), not sequential: real slots appear both as
    # "Denise Pihas" and comma-reversed "Pihas, Denise" (the quoted
    # Lastname,First format the probe found). A phrase is consumed if every
    # one of its tokens is present in the remaining slot tokens, regardless
    # of position; those token occurrences are then removed.
    remaining = list(tokens)
    for phrase in sorted(_ALLOWLIST_PHRASES, key=len, reverse=True):
        if all(remaining.count(t) >= phrase.count(t) for t in set(phrase)):
            for t in phrase:
                remaining.remove(t)
    # Whatever's left must each be a single-token allowlist entry.
    return all(t in _ALLOWLIST_SINGLE for t in remaining)


def _redact_header_match(m: re.Match) -> str:
    label, slot, bracket = m.group(1), m.group(2), m.group(3)
    slot_clean = slot.strip()
    # Already redacted — leave it (idempotency).
    if slot_clean == "{name}":
        return m.group(0)
    # Allowlisted self/staff/org sender — leave it (F6 two-tier coverage).
    if is_allowlisted(slot_clean):
        return m.group(0)
    # Otherwise it's a customer display-name — redact the slot.
    return f"{label}{TOKENS['name']}{bracket}"


def redact_headers(text: str) -> str:
    """Clear customer display-names in **From:**/**To:** header lines.
    Self/staff senders are allowlisted and survive. Idempotent."""
    return _HEADER_RE.sub(_redact_header_match, text)


def deterministic_redact(text: str) -> str:
    """Regex layer. Applied to every thread, always."""
    text = _EMAIL_RE.sub(TOKENS["email"], text)
    text = _URL_RE.sub(TOKENS["url"], text)
    text = _PAYMENT_RE.sub(TOKENS["payment"], text)
    text = _PHONE_RE.sub(TOKENS["phone"], text)
    text = redact_headers(text)
    return text


def verify(text: str) -> list[dict]:
    """Re-scan redacted text for surviving structured PII.
    Returns a list of findings; empty list == passes the gate.
    Does NOT check names/companies in prose/signatures — those are not
    regex-verifiable. Does check that no real email address survives, which
    indirectly catches a header that kept a real address beside a name."""
    findings = []
    for kind, rx in (("email", _EMAIL_RE), ("phone", _PHONE_RE),
                     ("payment", _PAYMENT_RE), ("url", _URL_RE)):
        for m in rx.finditer(text):
            findings.append({"kind": kind, "match_span": [m.start(), m.end()]})
    return findings


def model_redact(text: str, redactor=None) -> str:
    """Optional name/company/address pass for prose and signatures.
    `redactor` is a callable(str)->str (e.g. an Anthropic API wrapper) supplied
    by the caller. If None, returns text unchanged — the deterministic gate and
    the human backstop are then the only defenses for prose names/companies."""
    if redactor is None:
        return text
    return redactor(text)


def redact_thread(raw: str, redactor=None) -> tuple[str, str, list[dict]]:
    """Full pipeline. Returns (redacted_text, status, findings).

    status:
      'flagged'           structured PII survived the deterministic gate,
                          OR the redactor produced output much larger than
                          input (hallucination signal).
      'names_unredacted'  gate passed but NO name/company prose pass ran. The
                          text may still contain prose/signature names. NOT
                          labelable — the label command refuses anything that
                          is not 'verified'.
      'verified'          gate passed AND a name/company redactor was applied
                          AND the output passed the length sanity check.
                          Residual prose/signature name risk is still non-zero;
                          the human labeling pass is the final backstop.
      'model_failed'      the model pass raised (e.g. API timeout). The
                          deterministic gate STILL RAN on the raw text, so
                          emails, phones, and From/To header names are redacted.
                          Prose/signature names are NOT — retry the model pass.
                          Structurally protected, not fully clean.

    Note: From/To header display-names are now closed deterministically inside
    deterministic_redact(), independent of the model pass. A model-pass failure
    no longer leaves a file fully raw — the deterministic gate runs regardless."""
    name_pass = redactor is not None

    model_failed = False
    if name_pass:
        try:
            stage1 = model_redact(raw, redactor=redactor)   # prose names/companies
        except Exception:
            # Model pass failed (timeout, API error). Do NOT leave the file
            # raw — fall through to the deterministic gate on the original
            # text so structured PII and header names are still redacted.
            stage1 = raw
            model_failed = True
    else:
        stage1 = raw

    # Hallucination guard: model output should never be substantially longer
    # than the input. Redacting and cleaning shrinks or preserves length;
    # significant growth means the model invented content.
    if name_pass and not model_failed and len(stage1) > max(len(raw) * 1.2, len(raw) + 200):
        return raw, "flagged", [{"kind": "hallucination",
                                  "input_len": len(raw),
                                  "output_len": len(stage1)}]

    stage2 = deterministic_redact(stage1)            # structured PII + headers (always)
    findings = verify(stage2)
    if findings:
        status = "flagged"
    elif model_failed:
        status = "model_failed"
    elif not name_pass:
        status = "names_unredacted"
    else:
        status = "verified"
    return stage2, status, findings
