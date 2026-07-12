r"""
verify_replacements.py -- Session T2 Step 3 gate. READ-ONLY.

Validates labeling/pii_replacements_local.txt WITHOUT printing a single
real term. Per rule:

  [derived]   the left-side term (lowercased) exists in the scanner's
              runtime-derived term set. A typo'd or wrong name will not.
  [hits]      the term matches >= 1 reachable blob in history (unguarded,
              case-insensitive -- same semantics filter-repo will apply).
              A wrong name hits zero. Also reports dangling hits FYI.
  [order]     every multi-word rule appears BEFORE any single-word rule
              whose term is one of its words.

Structural: exactly 13 regex rules, zero FILL_ placeholders, well-formed
'==>' split, token side matches {name-N} or {name}.

stdout: rule index, token, verdicts, counts. Terms never printed.

Run from repo root:
    python labeling\verify_replacements.py
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scan_pii_history as sp   # noqa: E402
import scan_pii_aux as aux      # noqa: E402

REPL_REL = "labeling/pii_replacements_local.txt"


def main():
    repo = pathlib.Path(__file__).resolve().parents[1]
    repl = repo / REPL_REL

    print("=" * 74)
    print("verify_replacements.py -- Step 3 gate (READ-ONLY, terms never printed)")
    print("=" * 74)

    if not repl.exists():
        print(f"FAIL: {REPL_REL} does not exist.")
        sys.exit(1)
    if not sp.is_gitignored(repo, REPL_REL):
        print(f"FAIL: {REPL_REL} is NOT gitignored. Stop.")
        sys.exit(1)

    text = repl.read_text(encoding="utf-8", errors="replace")
    if "FILL_" in text:
        n = text.count("FILL_")
        print(f"FAIL: {n} FILL_ placeholder(s) remain. Not filled.")
        sys.exit(1)

    rules = []   # (lineno, term_raw, token)
    ok = True
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not s.startswith("regex:(?i)"):
            print(f"FAIL line {i}: rule does not start with 'regex:(?i)'")
            ok = False
            continue
        body = s[len("regex:(?i)"):]
        if "==>" not in body:
            print(f"FAIL line {i}: no '==>' separator")
            ok = False
            continue
        term, token = body.split("==>", 1)
        term, token = term.strip(), token.strip()
        if not term:
            print(f"FAIL line {i}: empty term")
            ok = False
            continue
        if not re.fullmatch(r"\{name(-\d+)?\}", token):
            print(f"FAIL line {i}: token side '{token}' not {{name-N}} / {{name}}")
            ok = False
            continue
        rules.append((i, term, token))

    print(f"\n[structure] rules parsed: {len(rules)} (expected 13)")
    if len(rules) != 13:
        ok = False

    # duplicate-term check
    lowered = [re.sub(r"\\(.)", r"\1", t).lower() for _, t, _ in rules]
    if len(set(lowered)) != len(lowered):
        print("FAIL: duplicate terms across rules")
        ok = False

    # ordering: multiword before any single that is one of its words
    for i, (ln_m, term_m, tok_m) in enumerate(rules):
        words_m = re.sub(r"\\(.)", r"\1", term_m).lower().split()
        if len(words_m) < 2:
            continue
        for j, (ln_s, term_s, tok_s) in enumerate(rules):
            if j >= i:
                break
            w_s = re.sub(r"\\(.)", r"\1", term_s).lower()
            if " " not in w_s and w_s in words_m:
                print(f"FAIL [order]: single rule {tok_s} (line {ln_s}) appears "
                      f"BEFORE multiword rule {tok_m} (line {ln_m}) that "
                      f"contains it. Move the multiword rule up.")
                ok = False

    # derived-set check
    print("\n[derived] deriving scanner term set (counts only):")
    terms_by_kind = aux.derive_terms(repo)
    derived = terms_by_kind["name"]

    # names-file coverage: all 7 lines must appear among the rule terms
    names_file = repo / sp.NAMES_FILE
    u_terms = []
    for line in names_file.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            u_terms.append(sp._norm_ws(s).lower())
    covered = sum(1 for u in u_terms if u in set(lowered))
    print(f"\n[names-file] {covered} of {len(u_terms)} names-file terms present "
          f"as rule terms {'-- PASS' if covered == len(u_terms) else '-- FAIL'}")
    if covered != len(u_terms):
        ok = False

    # history-hit check: unguarded (?i), reachable vs dangling
    reach = aux.reachable_shas(repo)
    blobs = aux.all_blobs(repo)
    blob_text = {}
    for sha, size in blobs:
        if size > aux.MAX_BLOB_BYTES:
            continue
        data = sp.git(repo, "cat-file", "blob", sha)
        if b"\x00" in data[:1024]:
            continue
        blob_text[sha] = data.decode("utf-8", "replace")

    print("\n[hits] unguarded (?i) matches per rule (filter-repo semantics):")
    print(f"    {'rule':4s} {'token':12s} {'derived':8s} {'reach':>6s} {'dangl':>6s}  verdict")
    for idx, (ln, term, token) in enumerate(rules, 1):
        try:
            rx = re.compile(term, re.IGNORECASE)
        except re.error as e:
            print(f"    {idx:<4d} {token:12s} regex error: {e} -- FAIL")
            ok = False
            continue
        plain = sp._norm_ws(re.sub(r"\\(.)", r"\1", term)).lower()
        in_derived = plain in derived
        r = d = 0
        for sha, txt in blob_text.items():
            n = len(rx.findall(txt))
            if not n:
                continue
            if sha in reach:
                r += n
            else:
                d += n
        verdict = "PASS" if (in_derived and r >= 1) else "FAIL"
        if verdict == "FAIL":
            ok = False
        print(f"    {idx:<4d} {token:12s} {'yes' if in_derived else 'NO':8s} "
              f"{r:>6d} {d:>6d}  {verdict}")

    print("\n[result] " + ("ALL CHECKS PASS -- file is rewrite-ready."
                           if ok else
                           "FAILURES above. Fix the flagged rules, re-run."))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
