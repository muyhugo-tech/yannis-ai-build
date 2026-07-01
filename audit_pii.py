r"""
audit_pii.py -- scan tracked files AND full git history for customer PII.

THE GATE THIS SERVES
The repo cannot go public until committed content (tree and history) is
confirmed clean of customer PII. Thread .md files were never committed
(verified: initial commit 3e157e0 contains only code/notes), so the live
risk is PII that leaked into code, prompts, fixtures, logs, and notes.

WHAT IT SCANS
  Surface 1: every file in `git ls-files` (the tracked working tree)
  Surface 2: every blob in `git rev-list --objects --all` (ALL history,
             including deleted files -- deletion does not scrub history)

WHAT IT LOOKS FOR
  1. KNOWN CUSTOMER NAMES -- derived AT RUNTIME from a pre-fix backup DB
     (its header lines still contain the leaked display names). The names
     are never hardcoded here; hardcoding them would create the exact
     problem this script audits for. Matching is case-insensitive
     substring on the full display string (e.g. '{name} Faries'), which
     keeps false positives near zero. Single-word display names (e.g.
     'jamie') are matched as whole words to avoid noise.
  2. RAW EMAIL ADDRESSES -- anything matching the email pattern that is
     not an allowlisted business/own address.
  3. PHONE-LIKE and PAYMENT-LIKE digit runs (same regexes as redact.py).

ALLOWLIST
  ybgcatering@gmail.com (published business inbox) and the git author
  address are expected in a public repo; staff first names are expected
  in code (the redaction allowlist itself names them). Flagging those
  would bury real findings in noise.

OUTPUT
  Findings grouped by surface with location (path, or commit+path for
  history blobs), kind, line number, and the matched text. Terminal
  output stays LOCAL -- same convention as probe_from_lines.py. When
  sharing results, describe locations and kinds, not the matched PII.

READ-ONLY. Runs git plumbing queries only; writes nothing, changes nothing.

Usage (from repo root, any venv -- stdlib only):
    python audit_pii.py labeling\labels_backup_2026-06-05.db
    python audit_pii.py <backup-db> --repo <path>     # default: cwd
    python audit_pii.py <backup-db> --names-file labeling\audit_names_local.txt

--names-file: supplemental name list, one display-name string per line,
blank lines and # comments allowed. EXISTS BECAUSE OF A COVERAGE GAP: the
backup DB only contains names that leaked in DB rows; names that leaked
ONLY in the .md files (most of batch 1) were never in any DB and the file
fix overwrote them in place. Build this file LOCALLY from the first
probe_from_lines.py run's terminal output. It must be gitignored -- it is
itself a PII file. Verify with: git check-ignore labeling/audit_names_local.txt
"""
import pathlib
import re
import sqlite3
import subprocess
import sys
from collections import Counter

# --- patterns (mirror redact.py) -------------------------------------------
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
PAYMENT_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")

# Emails that are EXPECTED in a public repo. Lowercase, exact match.
EMAIL_ALLOWLIST = {
    "ybgcatering@gmail.com",     # published business inbox
    "muyhuguso5@gmail.com",      # git author (operator's own)
}

# Sender slots that are staff/vendor, not customers -- mirror redact.py's
# judgment so derived "customer names" exclude them. Lowercase substring.
SENDER_ALLOWLIST = (
    "yannis catering", "yanni's", "yannis bar", "ybg",
    "hugo", "brenna", "jonathan", "jonah", "denise", "yanni",
    "typeform", "toast sites", "truereview", "unifirst",
    "hospitality headline", "new york times", "weddingpro",
    "office us", "business manager",
)

FROM_LINE_RE = re.compile(r"^\*\*(?:From|To):\*\*(.*)$", re.MULTILINE)

# Binary-ish extensions to skip when scanning blobs.
SKIP_EXT = {".db", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pyc",
            ".lock", ".zip", ".ico", ".woff", ".woff2"}


def derive_customer_names(backup_db: pathlib.Path) -> list[str]:
    """Pull leaked customer display-names from the PRE-FIX backup DB.

    These are the names that survived redaction in header slots before the
    Session C fix. They are the highest-confidence 'known PII' strings to
    grep the repo for."""
    conn = sqlite3.connect(backup_db)
    try:
        rows = conn.execute(
            "SELECT thread_text_redacted FROM inquiries").fetchall()
    finally:
        conn.close()

    names = set()
    for (text,) in rows:
        if not text:
            continue
        for m in FROM_LINE_RE.finditer(text):
            slot = m.group(1).strip()
            slot = re.sub(r"\s*<[^>]*>\s*$", "", slot).strip()
            slot = slot.strip('"').strip("'").strip()
            if not slot:
                continue
            bare = slot.strip("{}")
            if bare in ("name", "email", "url", "phone", "payment"):
                continue
            low = slot.lower()
            if any(a in low for a in SENDER_ALLOWLIST):
                continue
            names.add(slot)
            # Outlook 'Last, First' also leaks as 'First Last' in prose;
            # add the flipped form.
            if "," in slot:
                parts = [p.strip() for p in slot.split(",", 1)]
                if len(parts) == 2 and all(parts):
                    names.add(f"{parts[1]} {parts[0]}")
    return sorted(names)


def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, check=True).stdout


def scan_text(text: str, names: list[str], findings: list, where: str) -> None:
    lines = text.splitlines()
    for ln, line in enumerate(lines, start=1):
        low = line.lower()
        for name in names:
            if len(name.split()) == 1:
                # single-word display name: whole-word match to cut noise
                if re.search(rf"\b{re.escape(name.lower())}\b", low):
                    findings.append((where, ln, "customer_name", name, line.strip()[:90]))
            elif name.lower() in low:
                findings.append((where, ln, "customer_name", name, line.strip()[:90]))
        for m in EMAIL_RE.finditer(line):
            if m.group(0).lower() not in EMAIL_ALLOWLIST:
                findings.append((where, ln, "email", m.group(0), line.strip()[:90]))
        for m in PHONE_RE.finditer(line):
            findings.append((where, ln, "phone", m.group(0), line.strip()[:90]))
        for m in PAYMENT_RE.finditer(line):
            findings.append((where, ln, "payment_run", m.group(0), line.strip()[:90]))


def load_names_file(path: pathlib.Path) -> list[str]:
    """Supplemental names, one per line, # comments and blanks allowed."""
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repo = pathlib.Path.cwd()
    if "--repo" in sys.argv:
        repo = pathlib.Path(sys.argv[sys.argv.index("--repo") + 1])
        args = [a for a in args if a != str(repo)]
    names_file = None
    if "--names-file" in sys.argv:
        names_file = pathlib.Path(sys.argv[sys.argv.index("--names-file") + 1])
        args = [a for a in args if a != str(names_file)]
    if not args:
        print("usage: python audit_pii.py <pre-fix-backup-db> "
              "[--repo <path>] [--names-file <path>]")
        sys.exit(1)
    backup = pathlib.Path(args[0])
    if not backup.exists():
        print(f"backup DB not found: {backup}")
        sys.exit(1)

    names = derive_customer_names(backup)
    print(f"derived {len(names)} customer name strings from {backup.name}")
    if names_file is not None:
        if not names_file.exists():
            print(f"names file not found: {names_file}")
            sys.exit(1)
        extra = load_names_file(names_file)
        # safety: refuse to run if the names file is not gitignored --
        # a trackable names file would itself be a committed-PII defect.
        try:
            rel = names_file.resolve().relative_to(repo.resolve())
            out = subprocess.run(
                ["git", "-C", str(repo), "check-ignore", str(rel)],
                capture_output=True)
            if out.returncode != 0:
                print(f"REFUSING: {rel} is NOT gitignored. The names file is")
                print("itself PII and must never be trackable. Add it to")
                print(".gitignore first.")
                sys.exit(1)
        except ValueError:
            pass  # names file lives outside the repo: fine, can't be tracked
        merged = sorted(set(names) | set(extra))
        print(f"merged {len(extra)} supplemental names from {names_file.name}"
              f" -> {len(merged)} total")
        names = merged
    print("(names print in findings below; terminal output stays local)\n")

    findings: list[tuple] = []

    # --- Surface 1: tracked working tree -----------------------------------
    tracked = git(repo, "ls-files").decode().splitlines()
    print(f"surface 1: scanning {len(tracked)} tracked files...")
    for path in tracked:
        p = repo / path
        if p.suffix.lower() in SKIP_EXT or not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scan_text(text, names, findings, f"TREE {path}")

    # --- Surface 2: every blob in history -----------------------------------
    raw = git(repo, "rev-list", "--objects", "--all").decode().splitlines()
    blobs = []
    seen = set()
    for line in raw:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue                      # commits/trees have no path here
        sha, path = parts
        if sha in seen:
            continue
        seen.add(sha)
        if pathlib.Path(path).suffix.lower() in SKIP_EXT:
            continue
        blobs.append((sha, path))
    print(f"surface 2: scanning {len(blobs)} unique historical blobs...")
    for sha, path in blobs:
        try:
            data = git(repo, "cat-file", "blob", sha)
        except subprocess.CalledProcessError:
            continue
        if b"\x00" in data[:1024]:
            continue                      # binary
        scan_text(data.decode("utf-8", errors="replace"),
                  names, findings, f"HIST {sha[:10]} {path}")

    # --- report --------------------------------------------------------------
    print("\n" + "=" * 72)
    print(f"FINDINGS: {len(findings)}")
    print("=" * 72)
    kinds = Counter(k for _, _, k, _, _ in findings)
    for kind, n in kinds.most_common():
        print(f"  {n:>4}  {kind}")
    print("-" * 72)
    for where, ln, kind, match, context in findings:
        print(f"[{kind}] {where}  line {ln}")
        print(f"    match:   {match}")
        print(f"    context: {context}")
        print()
    if not findings:
        print("  (none -- tree and history clean for derived names + structured PII)")
    else:
        print("NOTE: review each finding; some may be expected (e.g. example")
        print("emails in docstrings). The pass bar is zero CUSTOMER findings,")
        print("not zero lines printed.")


if __name__ == "__main__":
    main()
