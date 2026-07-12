r"""
scan_pii_aux.py -- Session T2 auxiliary coverage passes. READ-ONLY.

PASS A (Step 2a): commit messages, tag names + tag messages, branch/ref
  names. walk_history reads trees, never commit objects -- these surfaces
  have never been scanned. Matched with the main scanner's own compiled
  matcher. Terms are IMPORTED from scan_pii_history (one term list, no
  divergence -- the T1 Finding-3 lesson).

PASS B (Step 2b): boundary-agnostic substring pass over EVERY blob in the
  object database (git cat-file --batch-all-objects), dangling/unreachable
  blobs included. The main scanner's matcher guards with
  (?<![A-Za-z0-9]) ... (?![A-Za-z0-9]) and therefore misses a term flush
  against an alphanumeric byte (T1 Finding 4: name against a literal \n
  escape -- the 'n' blocks the lookbehind). This pass drops the guards:
  same escaped terms, whitespace-flexible, case-insensitive, no boundary
  assertions. Per-token output splits guarded hits (main scanner would
  see) from substring-only hits (main-scanner-blind: the Finding-4 class
  plus innocent containing-word false positives -- triage from report).
  Reachable vs dangling is attributed per blob (rev-list --objects --all).

MATCHER SELF-TEST (runs always): a synthetic in-memory line is built from
  one actually-derived term and asserted to match BEFORE any scan. This is
  the liveness proof that replaces the STATE.md positive control after the
  history rewrite zeroes it (post-rewrite, the main scanner's exit-2 is
  by-design-inverted; this self-test is the cross-check).

MODES
  default          pre-rewrite: reachable guarded hits must be > 0
                   (dirty history is the positive control) else exit 2.
  --post-rewrite   acceptance: reachable guarded hits must be == 0
                   else exit 2. Substring-only and dangling hits are
                   reported for triage, not auto-failed.

This file contains ZERO customer PII. Terms derive at runtime from the
gitignored sources via scan_pii_history's miners. stdout prints counts
and tokens only; contexts go to the gitignored report (check-ignore
gated before a byte is written, same discipline as the main scanner).

Run from repo root:
    python labeling\scan_pii_aux.py
    python labeling\scan_pii_aux.py --post-rewrite
    python labeling\scan_pii_aux.py --repo <path>
"""

import glob
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scan_pii_history as sp  # noqa: E402  (term derivation + matching machinery)

REPORT_REL = "labeling/pii_aux_report.txt"
MAX_BLOB_BYTES = 2_000_000


# ---------------------------------------------------------------------------
# term derivation -- orchestrates sp's miners, identically to sp.main()
# ---------------------------------------------------------------------------

def derive_terms(repo: pathlib.Path):
    names, weak, emails, phones = set(), set(), set(), set()

    def use(rel, miner):
        nonlocal names, weak, emails, phones
        p = repo / rel
        if not p.exists():
            print(f"    {rel:55s} MISSING (skipped)")
            return
        if not sp.is_gitignored(repo, rel):
            print(f"    {rel:55s} NOT GITIGNORED (refused as source)")
            return
        n, w, e, ph = miner(p)
        names |= n
        weak |= w
        emails |= e
        phones |= ph

    for rel in sp.FIVE_SCRIPTS:
        use(rel, sp.mine_python_file)
    for db in sorted(glob.glob(str(repo / sp.DB_GLOB))):
        use(pathlib.Path(db).relative_to(repo).as_posix(), sp.mine_db)
    use(sp.NAMES_FILE, sp.mine_names_file)
    for py in sorted(glob.glob(str(repo / sp.ARCHIVE_GLOB), recursive=True)):
        use(pathlib.Path(py).relative_to(repo).as_posix(), sp.mine_python_file)

    terms_by_kind, dropped, uncorrob = sp.build_variants(names, weak, emails, phones)
    print(f"    union names={len(names)} weak={len(weak)} "
          f"emails={len(emails)} phones={len(phones)}")
    print(f"    scan terms: name={len(terms_by_kind['name'])} "
          f"email={len(terms_by_kind['email'])} "
          f"phone={len(terms_by_kind['phone'])} "
          f"(dropped={dropped} uncorroborated={uncorrob})")
    if not terms_by_kind["name"]:
        print("\nREFUSING: zero customer-name terms derived. Sources missing")
        print("or empty; a scan with no terms is a vacuous 'clean'.")
        sys.exit(1)
    return terms_by_kind


def build_tokens(terms_by_kind):
    tokens = {}
    next_idx = {}
    for kind in ("name", "email", "phone"):
        for i, key in enumerate(sorted(terms_by_kind[kind]), 1):
            tokens[(kind, key)] = f"{{{kind}-{i}}}"
        next_idx[kind] = len(terms_by_kind[kind]) + 1
    return tokens, next_idx


def tok_for(kind, key, tokens, next_idx):
    if (kind, key) not in tokens:
        tokens[(kind, key)] = f"{{{kind}-{next_idx[kind]}}}"
        next_idx[kind] += 1
    return tokens[(kind, key)]


# ---------------------------------------------------------------------------
# matchers: guarded (sp's own) + unguarded (same branches, no lookarounds)
# ---------------------------------------------------------------------------

def compile_unguarded(terms_by_kind):
    entries = []
    for kind, terms in terms_by_kind.items():
        for t in terms:
            entries.append((kind, t))
    entries.sort(key=lambda e: (-len(e[1]), e[1]))
    if not entries:
        return None, {}
    branches = [re.escape(t).replace(r"\ ", r"\s+") for _, t in entries]
    rx = re.compile("(?:" + "|".join(branches) + ")", re.IGNORECASE)
    lookup = {t: k for k, t in entries}
    return rx, lookup


def term_spans(line, rx, lookup):
    out = []
    if rx is None:
        return out
    for m in rx.finditer(line):
        key = sp.term_key_of(m.group(0))
        kind = lookup.get(key) or lookup.get(sp._norm_ws(key))
        if kind:
            out.append((m.start(), m.end(), kind, key))
    return out


def generic_spans(line, taken):
    """Residual emails/phones not overlapping already-taken spans."""
    def overlaps(a, b):
        return not (a[1] <= b[0] or b[1] <= a[0])
    out = []
    for m in sp.EMAIL_RE.finditer(line):
        lo = m.group(0).lower()
        if sp.is_placeholder_email(lo):
            continue
        span = (m.start(), m.end())
        if any(overlaps(span, t) for t in taken):
            continue
        out.append((m.start(), m.end(), "email", lo))
        taken.append(span)
    for m in sp.PHONE_RE.finditer(line):
        if sp.is_dummy_phone(m.group(0)):
            continue
        span = (m.start(), m.end())
        if any(overlaps(span, t) for t in taken):
            continue
        out.append((m.start(), m.end(), "phone", re.sub(r"\D", "", m.group(0))))
        taken.append(span)
    return out


def merge_spans(*span_lists):
    """Union of spans, earliest-start-longest-first, overlaps dropped."""
    allsp = sorted(set(s for lst in span_lists for s in lst),
                   key=lambda s: (s[0], -(s[1] - s[0])))
    taken, out = [], []
    for s in allsp:
        if any(not (s[1] <= a or b <= s[0]) for a, b in taken):
            continue
        taken.append((s[0], s[1]))
        out.append(s)
    out.sort()
    return out


def self_test_matcher(g_rx, g_lookup, terms_by_kind):
    """Liveness proof: one real derived term embedded in a synthetic line
    must match. In-memory only; nothing written."""
    probe_term = sorted(terms_by_kind["name"])[0]
    line = f"self-test: {probe_term} :end"
    found = term_spans(line, g_rx, g_lookup)
    if not any(k == "name" for _, _, k, _ in found):
        print("\nMATCHER SELF-TEST FAILED: a derived term did not match a")
        print("synthetic line. The matcher is broken; no scan result from")
        print("this run can be trusted.")
        sys.exit(2)
    print("[self-test] matcher alive: synthetic line with derived term matched")


# ---------------------------------------------------------------------------
# corpora
# ---------------------------------------------------------------------------

def refs_corpus(repo):
    """(label, text) items: commit messages, ref names, tag messages.
    Labels for refnames are generic indices -- the refname itself could be
    the PII, so it appears only inside the redacted context, never raw."""
    items = []
    raw = sp.git(repo, "log", "--all", "--format=%H%x00%B%x1e").decode(
        "utf-8", "replace")
    n_msgs = 0
    for rec in raw.split("\x1e"):
        rec = rec.strip("\r\n ")
        if not rec:
            continue
        h, _, body = rec.partition("\x00")
        items.append((f"msg {h[:7]}", body))
        n_msgs += 1
    refnames = [r for r in sp.git(repo, "for-each-ref", "--format=%(refname)")
                .decode("utf-8", "replace").splitlines() if r.strip()]
    for i, r in enumerate(refnames, 1):
        items.append((f"refname #{i}", r))
    tags = [t for t in sp.git(repo, "tag", "-l").decode("utf-8", "replace")
            .splitlines() if t.strip()]
    for i, t in enumerate(tags, 1):
        contents = sp.git(repo, "tag", "-l", t, "--format=%(contents)").decode(
            "utf-8", "replace")
        if contents.strip():
            items.append((f"tagmsg #{i}", contents))
    return items, n_msgs, len(refnames), len(tags)


def all_blobs(repo):
    out = sp.git(repo, "cat-file", "--batch-all-objects",
                 "--batch-check=%(objectname) %(objecttype) %(objectsize)"
                 ).decode("utf-8", "replace")
    blobs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "blob":
            blobs.append((parts[0], int(parts[2])))
    return blobs


def reachable_shas(repo):
    out = sp.git(repo, "rev-list", "--objects", "--all").decode("utf-8", "replace")
    return {line.split()[0] for line in out.splitlines() if line.strip()}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[1:]
    repo = pathlib.Path(__file__).resolve().parents[1]
    if "--repo" in argv:
        repo = pathlib.Path(argv[argv.index("--repo") + 1]).resolve()
    post_rewrite = "--post-rewrite" in argv
    report_path = repo / REPORT_REL

    print("=" * 74)
    print("scan_pii_aux.py -- refs pass + boundary-agnostic blob pass (READ-ONLY)")
    print(f"repo: {repo}   mode: {'POST-REWRITE acceptance' if post_rewrite else 'pre-rewrite inventory'}")
    print("=" * 74)

    if not sp.is_gitignored(repo, REPORT_REL):
        print(f"\nREFUSING: {REPORT_REL} is NOT gitignored. Add it to")
        print(".gitignore, verify with git check-ignore, then re-run.")
        sys.exit(1)
    print(f"\n[gate] git check-ignore {REPORT_REL}: PASS (report stays local)")

    print("\n[1] term derivation (gitignored sources via scan_pii_history):")
    terms_by_kind = derive_terms(repo)
    tokens, next_idx = build_tokens(terms_by_kind)
    g_rx, g_lookup = sp.compile_matcher(terms_by_kind)
    u_rx, u_lookup = compile_unguarded(terms_by_kind)
    self_test_matcher(g_rx, g_lookup, terms_by_kind)

    report_lines = []

    # ---- PASS A: refs ----
    items, n_msgs, n_refs, n_tags = refs_corpus(repo)
    a_counts = Counter()
    for label, text in items:
        for ln, line in enumerate(text.splitlines() or [""], 1):
            guard = term_spans(line, g_rx, g_lookup)
            taken = [(s, e) for s, e, _, _ in guard]
            gen = generic_spans(line, taken)
            merged = merge_spans(guard, gen)
            if not merged:
                continue
            red, out_spans = sp.redact_line(line, merged, {
                (k, key): tok_for(k, key, tokens, next_idx)
                for _, _, k, key in merged})
            for i, (s, e, kind, key) in enumerate(merged):
                tag = "A-TERM" if (s, e, kind, key) in guard else "A-GENERIC"
                tok = tok_for(kind, key, tokens, next_idx)
                ctx = sp.context_window(red, out_spans, i)
                report_lines.append(f"{tag:9s} {label}:{ln}  {tok}  | {ctx}")
                a_counts[tag] += 1
    print(f"\n[A] refs corpus: {n_msgs} commit messages, {n_refs} ref names, "
          f"{n_tags} tags")
    print(f"    term hits:    {a_counts['A-TERM']}")
    print(f"    generic hits: {a_counts['A-GENERIC']} (email/phone)")

    # ---- PASS B: all blobs, guarded vs unguarded ----
    reach = reachable_shas(repo)
    blobs = all_blobs(repo)
    b_counts = Counter()
    token_table = Counter()   # (token, category) -> n
    n_text = n_binary = n_oversize = 0
    for sha, size in blobs:
        if size > MAX_BLOB_BYTES:
            n_oversize += 1
            continue
        data = sp.git(repo, "cat-file", "blob", sha)
        if b"\x00" in data[:1024]:
            n_binary += 1
            continue
        n_text += 1
        where = "reach" if sha in reach else "DANGLING"
        for ln, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            guard = term_spans(line, g_rx, g_lookup)
            unguard = term_spans(line, u_rx, u_lookup)
            gset = {(s, e) for s, e, _, _ in guard}
            sub_only = [s for s in unguard if (s[0], s[1]) not in gset]
            taken = [(s, e) for s, e, _, _ in guard + sub_only]
            gen = generic_spans(line, taken)
            merged = merge_spans(guard, sub_only, gen)
            if not merged:
                continue
            red, out_spans = sp.redact_line(line, merged, {
                (k, key): tok_for(k, key, tokens, next_idx)
                for _, _, k, key in merged})
            gset_full = set(guard)
            sset_full = set(sub_only)
            for i, span in enumerate(merged):
                s, e, kind, key = span
                if span in gset_full:
                    cat = "B-GUARD"
                elif span in sset_full:
                    cat = "B-SUB"
                else:
                    cat = "B-GENERIC"
                tok = tok_for(kind, key, tokens, next_idx)
                ctx = sp.context_window(red, out_spans, i)
                report_lines.append(
                    f"{cat:9s} {where:8s} {sha[:7]}:{ln}  {tok}  | {ctx}")
                b_counts[(cat, where)] += 1
                token_table[(tok, cat, where)] += 1

    print(f"\n[B] blobs: {len(blobs)} in object db "
          f"({n_text} text scanned, {n_binary} binary, {n_oversize} oversize skipped)"
          f"; reachable shas: {len(reach & {s for s, _ in blobs})}, "
          f"dangling text/binary included")
    for cat in ("B-GUARD", "B-SUB", "B-GENERIC"):
        r = b_counts[(cat, "reach")]
        d = b_counts[(cat, "DANGLING")]
        print(f"    {cat:9s} reachable={r:<6d} dangling={d}")
    if token_table:
        print("    per-token (token, category, where -> hits):")
        for (tok, cat, where), n in sorted(token_table.items()):
            print(f"      {tok:12s} {cat:9s} {where:8s} {n}")

    # ---- report ----
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# aux PII coverage report -- REDACTED AT WRITE TIME\n")
        f.write("# generated by labeling/scan_pii_aux.py (read-only scan)\n")
        f.write("# A-TERM/A-GENERIC: refs corpus (commit msgs, refnames, tags)\n")
        f.write("# B-GUARD: main scanner's matcher would find this\n")
        f.write("# B-SUB:   substring-only -- main-scanner-blind (Finding-4\n")
        f.write("#          class OR innocent containing word; triage by eye)\n")
        f.write("# B-GENERIC: residual email/phone\n")
        f.write("#\n")
        for line in report_lines:
            f.write(line + "\n")
    print(f"\n[report] {report_path}  ({len(report_lines)} hit lines)")

    # ---- acceptance ----
    reach_guard = b_counts[("B-GUARD", "reach")]
    a_term = a_counts["A-TERM"]
    print("\n[acceptance]")
    if post_rewrite:
        ok = (reach_guard == 0 and a_term == 0)
        print(f"    reachable B-GUARD == 0: {'PASS' if reach_guard == 0 else f'FAIL ({reach_guard})'}")
        print(f"    A-TERM (refs)   == 0: {'PASS' if a_term == 0 else f'FAIL ({a_term})'}")
        print("    B-SUB / dangling hits: triage from report (not auto-failed)")
        if not ok:
            print("    RESULT: FAIL -- rewrite left guarded-matchable PII.")
            sys.exit(2)
        print("    RESULT: PASS -- no guarded-matchable PII in reachable blobs or refs.")
    else:
        if reach_guard == 0:
            print("    RESULT: BROKEN -- pre-rewrite run found zero reachable")
            print("    guarded hits on a known-dirty history. Do not trust.")
            sys.exit(2)
        print(f"    pre-rewrite positive control: reachable B-GUARD = {reach_guard} > 0 -- inventory live.")


if __name__ == "__main__":
    main()
