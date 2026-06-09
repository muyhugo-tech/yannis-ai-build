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

# Self / staff senders that must NOT be redacted. Lowercased, substring match.
_ALLOWLIST = (
    "yannis catering",
    "yanni's",
    "yannis bar",
    "ybg",
    "hugo",
    "brenna",
    "jonathan",
    "jonah",
    "denise",
    "yanni",
)

# Capture: (1) the header label + trailing space, (2) the display-name slot,
# (3) the opening angle bracket onward. Slot is non-greedy up to " <".
_HEADER_RE = re.compile(
    r"(\*\*(?:From|To):\*\*\s*)(.+?)(\s*<)",
)


def _redact_header_match(m: re.Match) -> str:
    label, slot, bracket = m.group(1), m.group(2), m.group(3)
    slot_clean = slot.strip()
    # Already redacted — leave it (idempotency).
    if slot_clean == "{name}":
        return m.group(0)
    # Allowlisted self/staff sender — leave it.
    low = slot_clean.lower()
    if any(allowed in low for allowed in _ALLOWLIST):
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
