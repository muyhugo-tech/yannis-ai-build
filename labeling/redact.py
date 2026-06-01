"""
redact.py — redaction-first gate for the labeling pipeline.

Two layers:
  1. deterministic_redact(): regex. Kills emails, phones, payment-like digit
     runs, URLs. This is also the VERIFICATION GATE — verify() re-scans output
     and any structured-PII survivor flags the thread (no label allowed).
  2. model_redact(): optional Claude pass for names / companies / addresses,
     which regex cannot do. Off unless a redactor callable is supplied.

Honest limit: names and companies have residual leak risk. The human reading
the redacted thread to label it is the backstop. Nothing is marked 'verified'
on the strength of the model pass alone — only the deterministic gate verifies.
"""
import re

TOKENS = {
    "email":   "{email}",
    "phone":   "{phone}",
    "payment": "{payment}",
    "url":     "{url}",
}

# Order matters: emails before phones (an email can contain digit runs).
_EMAIL_RE   = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE     = re.compile(r"\bhttps?://[^\s)>\]]+", re.IGNORECASE)
# Phone: NA-style with optional country code, separators . - space ( ).
_PHONE_RE   = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
# Payment: 13-16 digit runs, optionally grouped in 4s (card-like).
_PAYMENT_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")


def deterministic_redact(text: str) -> str:
    """Regex layer. Applied to every thread, always."""
    text = _EMAIL_RE.sub(TOKENS["email"], text)
    text = _URL_RE.sub(TOKENS["url"], text)
    text = _PAYMENT_RE.sub(TOKENS["payment"], text)
    text = _PHONE_RE.sub(TOKENS["phone"], text)
    return text


def verify(text: str) -> list[dict]:
    """Re-scan redacted text for surviving structured PII.
    Returns a list of findings; empty list == passes the gate.
    Does NOT check names/companies — those are not regex-verifiable."""
    findings = []
    for kind, rx in (("email", _EMAIL_RE), ("phone", _PHONE_RE),
                     ("payment", _PAYMENT_RE), ("url", _URL_RE)):
        for m in rx.finditer(text):
            findings.append({"kind": kind, "match_span": [m.start(), m.end()]})
    return findings


def model_redact(text: str, redactor=None) -> str:
    """Optional name/company/address pass.
    `redactor` is a callable(str)->str (e.g. an Anthropic API wrapper) supplied
    by the caller. If None, returns text unchanged — the deterministic gate and
    the human backstop are then the only defenses for names/companies."""
    if redactor is None:
        return text
    return redactor(text)


def redact_thread(raw: str, redactor=None) -> tuple[str, str, list[dict]]:
    """Full pipeline. Returns (redacted_text, status, findings).

    status:
      'flagged'           structured PII survived the deterministic gate,
                          OR the redactor produced output much larger than
                          input (hallucination signal).
      'names_unredacted'  gate passed but NO name/company pass ran. The text
                          may still contain names. NOT labelable — the label
                          command refuses anything that is not 'verified'.
      'verified'          gate passed AND a name/company redactor was applied
                          AND the output passed the length sanity check.
                          Residual name risk is still non-zero; the human
                          labeling pass is the final backstop."""
    name_pass = redactor is not None
    stage1 = model_redact(raw, redactor=redactor)   # names/companies (optional)

    # Hallucination guard: model output should never be substantially longer
    # than the input. Redacting and cleaning shrinks or preserves length;
    # significant growth means the model invented content.
    if name_pass and len(stage1) > max(len(raw) * 1.2, len(raw) + 200):
        return raw, "flagged", [{"kind": "hallucination",
                                  "input_len": len(raw),
                                  "output_len": len(stage1)}]

    stage2 = deterministic_redact(stage1)            # structured PII (always)
    findings = verify(stage2)
    if findings:
        status = "flagged"
    elif not name_pass:
        status = "names_unredacted"
    else:
        status = "verified"
    return stage2, status, findings
