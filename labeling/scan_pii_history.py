r"""
scan_pii_history.py -- full git-history customer-PII hit inventory. READ-ONLY.

THE GATE THIS SERVES
  Companion to audit_pii.py, specialized for the pre-publication history
  audit: every commit from `git rev-list --all`, every tracked path at every
  revision -- INCLUDING paths deleted in later commits. Deletion does not
  scrub history; deleted-then-forgotten files are exactly what this finds.

WHERE THE TERMS COME FROM (never from this file)
  This file contains ZERO customer names, emails, phones, or companies.
  Hardcoding them would create the exact defect it audits for. All terms are
  derived AT RUNTIME from gitignored local surfaces, each verified with
  `git check-ignore` before it is read:

    1. The five gitignored PII-bearing remediation scripts (see .gitignore).
       Their bytes are ast.parse'd -- string constants inside assignment
       nodes are collected (never imported/executed) -- AND their comment/
       docstring prose is mined with the greeting / Cap-Cap bigram
       heuristics, because the current bytes of those five scripts carry
       the names in COMMENTS, not in list literals.
    2. The gitignored labeling DBs (labels*.db*), including pre-fix backups:
       **From:**/**To:** display slots, greeting lines ("Hi X"), and
       signature lines (one/two cap words alone on a line) in the stored
       thread text, plus raw email/phone matches. This is the mechanism
       proven by audit_pii.py's derive_customer_names(), extended to body
       prose so names that only ever leaked in signatures/greetings
       (the F5 lesson) are still derived.
    3. labeling/audit_names_local.txt (one term per line, # comments ok).
    4. Supplemental: the gitignored _archive/**/*.py spent diagnostics,
       mined the same way as (1).

  Union across all sources. Run output prints COUNTS ONLY, never terms.

ALLOWLIST (same discipline as probe_body_artifacts' CLEARED set)
  Staff first names/surnames, the business' own org tokens, known vendor/
  platform orgs, menu/role noise, and staff emails are excluded from the
  term set. These identify staff and the business, not customers, so they
  may appear in this file. Unknown tokens are NEVER silently suppressed:
  anything not provably non-customer becomes a scan term (over-report,
  never under-report).

REPORT (labeling/pii_history_report.txt -- must be gitignored FIRST)
  The report path is verified with `git check-ignore` before a single hit
  is written; the scan aborts if it is trackable. Every matched term is
  redacted AT WRITE TIME to a stable {name-N} / {email-N} / {phone-N}
  token (index per unique term, deterministic across runs); context is
  +/-20 chars with every known term and any residual email/phone redacted.
  The raw string never reaches the report.

ACCEPTANCE SELF-TEST
  notes/STATE.md is CONFIRMED-POSITIVE for customer names across many
  commits. If this scanner finds zero name hits in any historical
  notes/STATE.md, the scanner is broken (exit 2) -- that result must never
  be presented as a clean history.

READ-ONLY against git: rev-list / ls-tree / cat-file / check-ignore only.

Run from repo root or labeling\ :
    python labeling\scan_pii_history.py
    python labeling\scan_pii_history.py --repo <path>
"""

import ast
import glob
import pathlib
import re
import sqlite3
import subprocess
import sys
import warnings
from collections import Counter

# ---------------------------------------------------------------------------
# Allowlist: staff / org / vendor / noise. NOT customer PII, safe to embed.
# Mirrors probe_body_artifacts.py's STAFF_ORG | NOISE | STOPWORDS discipline
# (built by explicit edit, never imported -- shared code means shared blind
# spots) plus audit_pii.py's email/vendor allowlists.
# ---------------------------------------------------------------------------

STAFF_FIRST = {"hugo", "brenna", "jonathan", "jonah", "denise", "yanni", "jona"}
STAFF_SURNAMES = {"pihas", "fineman", "gutierrez"}
ORG_TOKENS = {
    "yannis", "ybg", "bar", "grill", "catering", "scripps", "highlands",
    "san", "diego", "ca",
}
VENDOR_TOKENS = {
    "typeform", "toast", "truereview", "unifirst", "weddingpro", "grantify",
    "epic", "events", "team", "wedding", "coordination", "notifications",
}
MENU_ROLE_NOISE = {
    "neapolitan", "spartan", "bruschetta", "bruschettas", "dip", "trio",
    "grilled", "chicken", "loukaniko", "caesar", "spinach", "salad", "salads",
    "penne", "bolognese", "beef", "skewers", "cobb", "mediterranean",
    "piccata", "lamb", "cannelloni", "salmon", "lemoni", "mini", "budino",
    "bakery", "app", "barber", "massage", "botanica", "spa", "therapy",
    "salon", "skincare", "first", "look", "front", "patio", "spanakopita",
    "dessert", "tzatziki", "arancini", "appetizers", "appetizer", "timing",
    "setup", "overview", "inside", "perfect", "blog", "community",
    "facility", "manager", "event", "coordinator", "executive", "assistant",
    "general", "quality", "assurance", "guest", "count", "dietary", "notes",
    "business", "principal", "paralegal", "partner", "thx",
}
STOPWORDS = {
    "best", "thanks", "thank", "cheers", "hi", "hello", "regards", "kind",
    "sincerely", "the", "warm", "warmest", "later", "dear", "all", "good",
    "morning", "afternoon", "evening", "and", "or", "to", "of", "for",
    "sweet",
}
# Business-correspondence words: a candidate "name" carrying one of these
# tokens is a subject-ish line ('Change Request', 'Reservation Request'),
# not a person. Catches the signature heuristic's structural blind spot
# (two cap words alone on a line is also the shape of a subject header).
CORRESPONDENCE_WORDS = {
    "request", "requests", "change", "changes", "reservation",
    "reservations", "quote", "quotes", "invoice", "invoices", "update",
    "updates", "confirmation", "reminder", "inquiry", "enquiry", "booking",
    "estimate", "proposal", "order", "tasting", "question", "questions",
    "availability", "follow", "info", "information", "details", "pricing",
    "payment", "deposit", "receipt", "hold", "cancellation", "cancel",
    "confirmed", "pending", "approved",
}

# Words that make a Cap-Cap bigram mined from code comments a non-name.
FUNCTION_WORDS = {
    "this", "that", "these", "those", "from", "note", "run", "type", "gate",
    "backup", "rollback", "delete", "abort", "aborted", "print", "status",
    "session", "option", "batch", "row", "rows", "table", "label", "labels",
    "labeled", "source", "fix", "fixes", "read", "only", "see", "why",
    "what", "which", "not", "are", "was", "has", "have", "will", "must",
    "may", "can", "its", "one", "two", "three", "any", "each", "per",
    "into", "over", "after", "before", "next", "new", "old", "same",
    "known", "real", "body", "name", "names", "customer", "staff", "file",
    "files", "script", "scripts", "message", "messages", "thread", "gates",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun", "jan", "feb", "mar",
    "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday",
}
# Documentation placeholders: literal format-example words mined from term
# sources ('Lastname, First' in comments/docstrings). Not people.
DOC_PLACEHOLDERS = {"lastname", "firstname"}
KNOWN_NON_PII = (DOC_PLACEHOLDERS | STAFF_FIRST | STAFF_SURNAMES | ORG_TOKENS | VENDOR_TOKENS
                 | MENU_ROLE_NOISE | STOPWORDS | FUNCTION_WORDS)

# Multi-word staff/org/vendor phrases: a whole slot/term equal to one of
# these (or containing a vendor-org phrase) is not a customer.
ALLOW_PHRASES = {
    "yannis catering", "yanni's", "yannis bar", "yannis bar & grill",
    "yanni's bar & grill", "yanni's catering", "ybg catering",
    "toast sites", "hospitality headline", "new york times", "weddingpro",
    "office us", "business manager", "epic events", "san diego",
    "scripps highlands", "epic events wedding coordination",
}
STAFF_EMAILS = {
    "ybgcatering@gmail.com",   # published business inbox
    "muyhuguso5@gmail.com",    # git author (operator's own)
    "mailer-daemon@googlemail.com",  # google bounce daemon (vendor infra, not a person)
}
PLACEHOLDER_DOMAINS = ("example.com", "example.org", "example.net",
                       "acme.com", "x.com")
PLACEHOLDER_TLDS = (".tld", ".test", ".invalid", ".example", ".localhost")
PLACEHOLDER_SLOTS = {"name", "email", "url", "phone", "payment"}


def is_placeholder_email(email_lc: str) -> bool:
    return (email_lc in STAFF_EMAILS
            or email_lc.endswith(PLACEHOLDER_DOMAINS)
            or email_lc.endswith(PLACEHOLDER_TLDS))


def is_dummy_phone(raw: str) -> bool:
    """NANP 555 exchange is reserved for fictional numbers."""
    digits = re.sub(r"\D", "", raw)
    return len(digits) < 10 or digits[-7:-4] == "555"

# ---------------------------------------------------------------------------
# Patterns (regex bodies mirror redact.py / audit_pii.py / probe_body_artifacts)
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
FROM_LINE_RE = re.compile(r"^\*\*(?:From|To):\*\*(.*)$", re.MULTILINE)
GREETING_RE = re.compile(r"\b(?:Hi|Hello|Dear)[ \t]+([A-Z][a-z]+)\b")
SIG_NAME_RE = re.compile(
    r"^\s*([A-Z][a-z]+)(?:\s+([A-Z][a-z]+))?\s*$", re.MULTILINE)
NAME_BIGRAM_RE = re.compile(r"\b([A-Z][a-z]+)[ \t]+([A-Z][a-z]+)\b")
PERSON_SHAPE_RE = re.compile(
    r"^[A-Z][a-z]+(?:[-'][A-Za-z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Za-z][a-z]+)?){0,2}$")

SKIP_EXT = {".db", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pyc",
            ".lock", ".zip", ".ico", ".woff", ".woff2"}

# The five gitignored PII-bearing remediation scripts (see .gitignore).
FIVE_SCRIPTS = (
    "labeling/quarantine_c1.py",
    "labeling/check_sources.py",
    "labeling/delete_batch3.py",
    "labeling/probe_body_leaks.py",
    "labeling/verify_ingest_redaction.py",
)
NAMES_FILE = "labeling/audit_names_local.txt"
DB_GLOB = "labeling/labels*.db*"
ARCHIVE_GLOB = "_archive/**/*.py"
REPORT_REL = "labeling/pii_history_report.txt"
POSITIVE_CONTROL_PATH = "notes/STATE.md"   # confirmed-positive acceptance gate


def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, check=True).stdout


def is_gitignored(repo: pathlib.Path, rel: str) -> bool:
    out = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", rel],
        capture_output=True)
    return out.returncode == 0


# ---------------------------------------------------------------------------
# Term derivation
# ---------------------------------------------------------------------------

def _norm_ws(s: str) -> str:
    return " ".join(s.split())


def classify_tokens_all_known(tokens) -> bool:
    """True iff every token is provably non-customer (CLEARED)."""
    toks = [t.lower().strip(".,;:\"'()<>[]") for t in tokens]
    toks = [t for t in toks if t]
    return bool(toks) and all(t in KNOWN_NON_PII for t in toks)


def allowlisted_phrase(term_lc: str) -> bool:
    if term_lc in ALLOW_PHRASES:
        return True
    return any(p in term_lc for p in ALLOW_PHRASES if " " in p or "'" in p)


def mine_prose(text: str):
    """Greeting + Cap-Cap-bigram name mining over arbitrary prose/code text.
    Returns a set of candidate person-name strings (original case)."""
    found = set()
    for m in GREETING_RE.finditer(text):
        tok = m.group(1)
        if tok.lower() not in KNOWN_NON_PII:
            found.add(tok)
    for m in NAME_BIGRAM_RE.finditer(text):
        t1, t2 = m.group(1), m.group(2)
        lo1, lo2 = t1.lower(), t2.lower()
        if lo1 in FUNCTION_WORDS or lo2 in FUNCTION_WORDS:
            continue
        if classify_tokens_all_known([t1, t2]):
            continue
        found.add(f"{t1} {t2}")
    return found


def mine_python_file(path: pathlib.Path):
    """AST assignment-literal strings + comment/docstring prose mining.
    Never imports or executes the file.
    Returns (strong_names, weak_names, emails, phones)."""
    names, emails, phones = set(), set(), set()
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return names, set(), emails, phones

    # (a) string constants inside assignment nodes (the briefed mechanism)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value:
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        s = _norm_ws(sub.value)
                        if PERSON_SHAPE_RE.match(s) and not classify_tokens_all_known(s.split()):
                            names.add(s)
                        for em in EMAIL_RE.findall(sub.value):
                            emails.add(em)
                        for ph in PHONE_RE.findall(sub.value):
                            phones.add(ph)

    # (b) whole-file prose (comments + docstrings carry the names here)
    names |= mine_prose(text)
    for em in EMAIL_RE.findall(text):
        emails.add(em)
    return names, set(), emails, phones


def mine_db(path: pathlib.Path):
    """From/To display slots + greeting/signature prose + raw emails/phones
    from the stored (model-redacted, possibly pre-fix) thread text.

    Signature-heuristic SINGLE words come back as WEAK candidates: a lone
    capitalized word on its own line is as often a subject-ish word
    ('Change', 'Request') as a name, so it only becomes a scan term if
    corroborated by a From-slot / greeting / multi-word name token
    (build_variants does that). Never silently dropped -- the drop count is
    reported. Returns (strong_names, weak_names, emails, phones)."""
    names, weak, emails, phones = set(), set(), set(), set()
    try:
        cx = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        cols = [r[1] for r in cx.execute("PRAGMA table_info(inquiries)")]
        text_cols = [c for c in cols if "redacted" in c.lower()]
        if not text_cols:
            cx.close()
            return names, weak, emails, phones
        rows = cx.execute(
            "SELECT " + ", ".join(text_cols) + " FROM inquiries").fetchall()
        cx.close()
    except sqlite3.Error:
        return names, weak, emails, phones

    for row in rows:
        for text in row:
            if not text:
                continue
            # From/To display slots (audit_pii.py's derive mechanism)
            for m in FROM_LINE_RE.finditer(text):
                slot = m.group(1).strip()
                slot = re.sub(r"\s*<[^>]*>\s*$", "", slot).strip()
                slot = slot.strip('"').strip("'").strip()
                if not slot or slot.strip("{}") in PLACEHOLDER_SLOTS:
                    continue
                slot = _norm_ws(slot)
                lo = slot.lower()
                if allowlisted_phrase(lo) or classify_tokens_all_known(slot.split()):
                    continue
                if EMAIL_RE.fullmatch(slot):
                    emails.add(slot)
                    continue
                names.add(slot)
                # Outlook 'Last, First' also leaks flipped in prose.
                if "," in slot:
                    parts = [p.strip() for p in slot.split(",", 1)]
                    if len(parts) == 2 and all(parts):
                        names.add(_norm_ws(f"{parts[1]} {parts[0]}"))
            # greeting names in body prose
            for m in GREETING_RE.finditer(text):
                tok = m.group(1)
                if tok.lower() not in KNOWN_NON_PII:
                    names.add(tok)
            # signature lines: one/two cap words alone on a line
            for m in SIG_NAME_RE.finditer(text):
                parts = [g for g in (m.group(1), m.group(2)) if g]
                if classify_tokens_all_known(parts):
                    continue
                if len(parts) == 1:
                    weak.add(parts[0])          # needs corroboration
                else:
                    names.add(_norm_ws(" ".join(parts)))
            # raw structured PII that survived (pre-fix backups especially)
            for em in EMAIL_RE.findall(text):
                emails.add(em)
            for ph in PHONE_RE.findall(text):
                phones.add(ph)
    return names, weak, emails, phones


def mine_names_file(path: pathlib.Path):
    """Operator-curated list: everything is a strong term."""
    names, emails, phones = set(), set(), set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return names, set(), emails, phones
    for line in lines:
        line = _norm_ws(line.strip())
        if not line or line.startswith("#"):
            continue
        if EMAIL_RE.fullmatch(line):
            emails.add(line)
        elif PHONE_RE.fullmatch(line):
            phones.add(line)
        else:
            names.add(line)
    return names, set(), emails, phones


def build_variants(names, weak_names, emails, phones):
    """Full / first-only / last-only variants, allowlist-filtered.
    Weak (uncorroborated signature-single) candidates only become terms if
    their token also occurs in a strong name. Returns (terms_by_kind,
    dropped_by_allowlist, dropped_uncorroborated)."""
    name_terms, dropped = set(), 0

    strong_tokens = set()
    for name in names:
        for w in name.lower().replace(",", " ").split():
            strong_tokens.add(w)
    corroborated = {w for w in weak_names if w.lower() in strong_tokens}
    uncorroborated = len(weak_names) - len(corroborated)
    names = set(names) | corroborated

    def try_add(term_lc: str):
        nonlocal dropped
        term_lc = _norm_ws(term_lc)
        if (len(term_lc) < 3 or term_lc in KNOWN_NON_PII
                or allowlisted_phrase(term_lc)
                or classify_tokens_all_known(term_lc.split())
                or any(w in CORRESPONDENCE_WORDS for w in term_lc.split())):
            dropped += 1
            return
        name_terms.add(term_lc)

    for name in names:
        lo = _norm_ws(name.lower().replace(",", " "))
        words = lo.split()
        try_add(lo)
        if 2 <= len(words) <= 3 and PERSON_SHAPE_RE.match(_norm_ws(name)):
            try_add(words[0])    # first-only
            try_add(words[-1])   # last-only

    email_terms = set()
    for em in emails:
        lo = em.lower()
        if is_placeholder_email(lo):
            dropped += 1
            continue
        email_terms.add(lo)

    phone_terms = set()
    for ph in phones:
        if is_dummy_phone(ph):
            dropped += 1
        else:
            phone_terms.add(ph.strip())

    return ({"name": name_terms, "email": email_terms, "phone": phone_terms},
            dropped, uncorroborated)


# ---------------------------------------------------------------------------
# Matching machinery
# ---------------------------------------------------------------------------

def compile_matcher(terms_by_kind):
    """One combined case-insensitive regex; longest alternatives first so a
    full name outranks its first/last variants at the same position."""
    entries = []   # (kind, term_lc)
    for kind, terms in terms_by_kind.items():
        for t in terms:
            entries.append((kind, t))
    entries.sort(key=lambda e: (-len(e[1]), e[1]))
    if not entries:
        return None, {}
    branches = []
    for _, term in entries:
        esc = re.escape(term).replace(r"\ ", r"\s+")
        branches.append(esc)
    rx = re.compile(
        r"(?<![A-Za-z0-9])(?:" + "|".join(branches) + r")(?![A-Za-z0-9])",
        re.IGNORECASE)
    lookup = {t: k for k, t in entries}
    return rx, lookup


def term_key_of(matched_text: str) -> str:
    return _norm_ws(matched_text.lower())


def scan_line(line: str, matcher, lookup):
    """Yield (start, end, kind, term_key) for known terms, then residual
    generic emails/phones that do not overlap a known-term span."""
    spans = []
    if matcher is not None:
        for m in matcher.finditer(line):
            key = term_key_of(m.group(0))
            kind = lookup.get(key)
            if kind is None:
                # whitespace-normalized multiword form
                kind = lookup.get(_norm_ws(key))
            if kind is None:
                continue
            spans.append((m.start(), m.end(), kind, key))
    taken = [(s, e) for s, e, _, _ in spans]

    def overlaps(a, b):
        return not (a[1] <= b[0] or b[1] <= a[0])

    for m in EMAIL_RE.finditer(line):
        lo = m.group(0).lower()
        if is_placeholder_email(lo):
            continue
        if any(overlaps((m.start(), m.end()), t) for t in taken):
            continue
        spans.append((m.start(), m.end(), "email", lo))
        taken.append((m.start(), m.end()))
    for m in PHONE_RE.finditer(line):
        if is_dummy_phone(m.group(0)):
            continue
        if any(overlaps((m.start(), m.end()), t) for t in taken):
            continue
        spans.append((m.start(), m.end(), "phone",
                      re.sub(r"\D", "", m.group(0))))
        taken.append((m.start(), m.end()))
    spans.sort()
    return spans


def redact_line(line: str, spans, tokens):
    """Replace every span with its token. Returns (redacted_line,
    list of (out_start, out_end, span_index))."""
    out, out_spans, cursor = [], [], 0
    pos = 0
    for i, (s, e, kind, key) in enumerate(spans):
        out.append(line[pos:s])
        cursor += s - pos
        tok = tokens[(kind, key)]
        out_spans.append((cursor, cursor + len(tok), i))
        out.append(tok)
        cursor += len(tok)
        pos = e
    out.append(line[pos:])
    return "".join(out), out_spans


def context_window(red_line: str, out_spans, target_idx: int, pad: int = 20):
    """+/-pad chars around the target token, never slicing another token."""
    t0, t1 = None, None
    for a, b, i in out_spans:
        if i == target_idx:
            t0, t1 = a, b
            break
    w0, w1 = max(0, t0 - pad), min(len(red_line), t1 + pad)
    for a, b, _ in out_spans:
        if a < w0 < b:
            w0 = a
        if a < w1 < b:
            w1 = b
    prefix = "..." if w0 > 0 else ""
    suffix = "..." if w1 < len(red_line) else ""
    return prefix + red_line[w0:w1] + suffix


# ---------------------------------------------------------------------------
# History walk
# ---------------------------------------------------------------------------

def walk_history(repo, matcher, lookup):
    """Every commit x every tracked path at that revision. Blob contents are
    scanned once per unique sha and attributed to every (commit, path) that
    carries the sha -- deleted-in-later-commits paths included by
    construction, since ls-tree is per historical revision."""
    commits = git(repo, "rev-list", "--reverse", "--all").decode().split()
    blob_hits = {}          # sha -> list of (line_no, spans, line_text)
    binary_shas = set()
    hits = []               # (commit, path, line_no, spans, line_text)
    n_blob_scans = 0

    for commit in commits:
        tree = git(repo, "ls-tree", "-r", commit).decode("utf-8", "replace")
        for entry in tree.splitlines():
            try:
                meta, path = entry.split("\t", 1)
                mode, otype, sha = meta.split()
            except ValueError:
                continue
            if otype != "blob":
                continue
            if pathlib.PurePosixPath(path).suffix.lower() in SKIP_EXT:
                continue
            if sha in binary_shas:
                continue
            if sha not in blob_hits:
                data = git(repo, "cat-file", "blob", sha)
                if b"\x00" in data[:1024]:
                    binary_shas.add(sha)
                    continue
                n_blob_scans += 1
                found = []
                for ln, line in enumerate(
                        data.decode("utf-8", "replace").splitlines(), 1):
                    spans = scan_line(line, matcher, lookup)
                    if spans:
                        found.append((ln, spans, line))
                blob_hits[sha] = found
            for ln, spans, line in blob_hits[sha]:
                for i in range(len(spans)):
                    hits.append((commit, path, ln, spans, line, i))
    return commits, hits, n_blob_scans, len(binary_shas)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[1:]
    repo = pathlib.Path(__file__).resolve().parents[1]
    if "--repo" in argv:
        repo = pathlib.Path(argv[argv.index("--repo") + 1]).resolve()
    report_path = repo / REPORT_REL

    print("=" * 74)
    print("scan_pii_history.py -- git-history PII hit inventory (READ-ONLY)")
    print(f"repo: {repo}")
    print("=" * 74)

    # GATE 0: the report path must be gitignored BEFORE it exists.
    if not is_gitignored(repo, REPORT_REL):
        print(f"\nREFUSING: {REPORT_REL} is NOT gitignored. The report is a")
        print("PII map even redacted. Add it to .gitignore, then re-run.")
        sys.exit(1)
    print(f"\n[gate] git check-ignore {REPORT_REL}: PASS (report stays local)")

    # ---- derive terms from gitignored sources only ----
    names, weak, emails, phones = set(), set(), set(), set()
    print("\n[1] term sources (gitignored, read at runtime; counts only):")

    def use_source(rel, miner, tag):
        nonlocal names, weak, emails, phones
        p = repo / rel
        if not p.exists():
            print(f"    {rel:55s} MISSING (skipped)")
            return
        if not is_gitignored(repo, rel):
            print(f"    {rel:55s} NOT GITIGNORED (refused as source)")
            return
        n, w, e, ph = miner(p)
        names |= n
        weak |= w
        emails |= e
        phones |= ph
        print(f"    {rel:55s} [{tag}] names={len(n)} weak={len(w)} "
              f"emails={len(e)} phones={len(ph)}")

    for rel in FIVE_SCRIPTS:
        use_source(rel, mine_python_file, "script")
    for db in sorted(glob.glob(str(repo / DB_GLOB))):
        rel = pathlib.Path(db).relative_to(repo).as_posix()
        use_source(rel, mine_db, "db")
    use_source(NAMES_FILE, mine_names_file, "names-file")
    for py in sorted(glob.glob(str(repo / ARCHIVE_GLOB), recursive=True)):
        rel = pathlib.Path(py).relative_to(repo).as_posix()
        use_source(rel, mine_python_file, "archive")

    print(f"\n    UNION: names={len(names)} weak-singles={len(weak)} "
          f"emails={len(emails)} phones={len(phones)}")

    terms_by_kind, dropped, uncorrob = build_variants(names, weak, emails, phones)
    n_terms = {k: len(v) for k, v in terms_by_kind.items()}
    print(f"\n[2] scan terms after variant expansion + staff/org allowlist:")
    print(f"    name variants (full/first/last): {n_terms['name']}")
    print(f"    email terms:                     {n_terms['email']}")
    print(f"    phone terms:                     {n_terms['phone']}")
    print(f"    dropped by allowlist/shape/dummy:      {dropped}")
    print(f"    sig-singles dropped (uncorroborated):  {uncorrob}")
    if n_terms["name"] == 0:
        print("\nREFUSING: zero customer-name terms derived. The gitignored")
        print("sources are missing or empty; scanning history with no terms")
        print("would produce a vacuous 'clean' result.")
        sys.exit(1)

    # stable token indices: sorted per kind over the full derived term set
    tokens = {}
    for kind in ("name", "email", "phone"):
        for i, key in enumerate(sorted(terms_by_kind[kind]), 1):
            tokens[(kind, key)] = f"{{{kind}-{i}}}"

    matcher, lookup = compile_matcher(terms_by_kind)

    # ---- walk history ----
    print("\n[3] walking history (rev-list --all; every path at every rev)...")
    commits, hits, n_scanned, n_binary = walk_history(repo, matcher, lookup)
    print(f"    commits: {len(commits)}   unique text blobs scanned: {n_scanned}"
          f"   binary blobs skipped: {n_binary}")

    # generic-hit tokens discovered during the walk (emails/phones not in
    # the derived set): extend the index space deterministically.
    next_idx = {k: len(terms_by_kind[k]) + 1 for k in ("name", "email", "phone")}
    discovered = sorted({(s[2], s[3]) for _, _, _, spans, _, _ in hits
                         for s in spans if (s[2], s[3]) not in tokens})
    for kind, key in discovered:
        tokens[(kind, key)] = f"{{{kind}-{next_idx[kind]}}}"
        next_idx[kind] += 1

    # ---- write redacted report ----
    path_counter = Counter()
    token_counter = Counter()
    commit_counter = Counter()
    kind_counter = Counter()
    lines_out = []
    for commit, path, ln, spans, line, i in hits:
        red, out_spans = redact_line(line, spans, tokens)
        s, e, kind, key = spans[i]
        tok = tokens[(kind, key)]
        ctx = context_window(red, out_spans, i)
        lines_out.append(f"{commit[:7]}  {path}:{ln}  {tok}  | {ctx}")
        path_counter[path] += 1
        token_counter[tok] += 1
        commit_counter[commit[:7]] += 1
        kind_counter[kind] += 1

    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# git-history PII hit inventory -- REDACTED AT WRITE TIME\n")
        f.write("# generated by labeling/scan_pii_history.py (read-only scan)\n")
        f.write("# one line per hit: <commit> <path>:<line> <token> | context\n")
        f.write("# tokens are stable per unique term; raw terms never appear\n")
        f.write("#\n")
        for line in lines_out:
            f.write(line + "\n")
        f.write("\n")
        f.write("=" * 70 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"total hits:        {len(lines_out)}\n")
        f.write(f"commits scanned:   {len(commits)}\n")
        f.write(f"commits touched:   {len(commit_counter)}\n")
        f.write(f"paths touched:     {len(path_counter)}\n")
        f.write(f"unique terms hit:  {len(token_counter)}\n")
        f.write("\nhits per file path:\n")
        for p, n in path_counter.most_common():
            f.write(f"  {n:>6}  {p}\n")
        f.write("\nhits per unique term index:\n")
        for t, n in token_counter.most_common():
            f.write(f"  {n:>6}  {t}\n")
        f.write("\nhits per commit:\n")
        for c, n in sorted(commit_counter.items()):
            f.write(f"  {n:>6}  {c}\n")

    # ---- stdout summary: counts only ----
    print(f"\n[4] results (counts only; terms live redacted in the report):")
    print(f"    total hits:                 {len(lines_out)}")
    print(f"    by kind:                    "
          + "  ".join(f"{k}={kind_counter.get(k, 0)}"
                      for k in ("name", "email", "phone")))
    print(f"    distinct paths touched:     {len(path_counter)}")
    print(f"    distinct commits touched:   {len(commit_counter)} / {len(commits)}")
    print(f"    distinct terms with hits:   {len(token_counter)}")
    print(f"    report: {report_path}  ({len(lines_out)} hit lines)")

    # ---- ACCEPTANCE SELF-TEST: notes/STATE.md is confirmed-positive ----
    control_hits = sum(
        1 for commit, path, ln, spans, line, i in hits
        if path == POSITIVE_CONTROL_PATH and spans[i][2] == "name")
    print(f"\n[5] acceptance gate ({POSITIVE_CONTROL_PATH} is confirmed-positive):")
    print(f"    name hits in {POSITIVE_CONTROL_PATH} across history: {control_hits}")
    if control_hits == 0:
        print("    RESULT: SCANNER BROKEN -- zero hits on a confirmed-positive")
        print("    file. Do NOT read this run as a clean history. Fix the")
        print("    term derivation and re-run.")
        sys.exit(2)
    print("    RESULT: PASS -- positive control detected; inventory is live.")


if __name__ == "__main__":
    main()
