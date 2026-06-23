"""
log_outcome.py  --  frictionless one-line logger for the usefulness tally.

This is the capture helper for Deliverable B (the cold/recall usefulness
tally). It does ONE thing: append a single scored row to the tally CSV. It
does NOT run the agent -- you run pilot_v0.py, READ the draft, form your
judgment, THEN log it here. The score is your judgment after reading the
draft; it cannot be captured in the same step that generates the draft.

WHY APPEND-ONLY, CONSTRAINED, REPO-ANCHORED (read before trusting it):
  - APPEND-ONLY: it never edits or deletes a prior row. The failure mode of a
    logging tool is clobbering history; this tool cannot. If you mis-log, fix
    the CSV by hand -- the tool is not given delete power on purpose. Same
    command twice = two visible rows (honest), never a silent overwrite.
  - CONSTRAINED INPUTS: source must be cold|recall and score must be
    Advances|Salvageable|Stalls (case-insensitive in, canonical out). A tally
    full of "pretty good" does not tally. Bad values are REFUSED with a reason,
    not stored. why + failure_tag are free text.
  - REPO-ANCHORED PATH: it always writes the SAME file regardless of the
    directory you run it from. This session hit the relative-path-vs-cwd bug
    three times (label.py, probe, agent_v3's prompt load); a logger with a
    relative path would scatter tally fragments across directories and you'd
    trust an incomplete one. The path is hardcoded to the repo, like
    pilot_v0's DEFAULT_DB. Override with --file only if you mean to.

THE TWO TAGS THAT MATTER:
  - source: cold = a genuinely never-seen inbound you judge in real time (the
    TRUSTWORTHY signal). recall = a thread you have prior knowledge of (fast,
    but HINDSIGHT-BIASED -- score what the draft SAYS, not what you KNOW). The
    two are tallied separately on read; if they diverge, trust cold.
  - score: ADVANCES (send as-is, saved the round-trip) / SALVAGEABLE (right
    instinct, you'd edit to advance properly) / STALLS (sending costs a
    round-trip or misleads -- you'd rewrite).

ID HANDLING:
  Pass --id for a DB row (e.g. 19abc... ) or a recall thread's own id. Omit it
  and the tool auto-assigns the next live-N by scanning existing live-* rows in
  the file, so mid-shift you type the minimum.

USAGE (run from anywhere; venv not required -- stdlib only):
  python log_outcome.py --source cold --score Salvageable \
      --why "missed the bar ask; deferred to after location" \
      --tag missing-tool-routing
  # -> appends live-2 (auto-numbered)

  python log_outcome.py --source recall --id 19a78f9... --score Stalls \
      --why "padded 15 -> 15 to 20, forced a re-ask" --tag count-padding

  python log_outcome.py --show         # print the current tally and the
                                       # running cold / recall roll-up
"""

import argparse
import csv
import os
import sys
from datetime import date

# Repo-anchored, like pilot_v0's DEFAULT_DB. Always the one true tally,
# regardless of cwd. Override with --file only deliberately.
DEFAULT_FILE = r"C:\dev\yannis-ai-build\notes\usefulness_tally.csv"

HEADER = ["timestamp", "source", "inquiry_id", "score", "failure_tag", "why"]

VALID_SOURCE = {"cold", "recall"}
# canonical-case map; we accept any case in, store canonical out.
VALID_SCORE = {
    "advances": "Advances",
    "salvageable": "Salvageable",
    "stalls": "Stalls",
}


def _ensure_file(path: str) -> None:
    """Create the file with a header if it does not exist. Does not touch an
    existing file."""
    if os.path.exists(path):
        return
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADER)


def _read_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _next_live_id(path: str) -> str:
    """Scan existing live-N ids and return the next one. Robust to gaps and to
    non-live ids (DB/recall ids are ignored for numbering)."""
    rows = _read_rows(path)
    n = 0
    for r in rows:
        iid = (r.get("inquiry_id") or "").strip()
        if iid.startswith("live-"):
            tail = iid[len("live-"):]
            if tail.isdigit():
                n = max(n, int(tail))
    return f"live-{n + 1}"


def cmd_show(path: str) -> None:
    rows = _read_rows(path)
    if not rows:
        print(f"(no tally yet at {path})")
        return
    # print rows
    print(f"TALLY ({path}) -- {len(rows)} row(s)")
    print("-" * 72)
    for r in rows:
        print(f"  {r['timestamp']}  {r['source']:6s}  {r['inquiry_id']:16s}  "
              f"{r['score']:11s}  [{r.get('failure_tag','')}]")
        why = (r.get("why") or "").strip()
        if why:
            print(f"      why: {why}")
    print("-" * 72)
    # roll-up, the two sources tallied SEPARATELY (trust cold on divergence)
    for src in ("cold", "recall"):
        sub = [r for r in rows if r.get("source") == src]
        if not sub:
            print(f"  {src}: 0 rows")
            continue
        adv = sum(1 for r in sub if r["score"] == "Advances")
        sal = sum(1 for r in sub if r["score"] == "Salvageable")
        sta = sum(1 for r in sub if r["score"] == "Stalls")
        saved = adv + sal
        total = len(sub)
        pct = (100.0 * saved / total) if total else 0.0
        print(f"  {src}: n={total}  Advances={adv}  Salvageable={sal}  "
              f"Stalls={sta}  |  saved-time (Adv+Salv) = {saved}/{total} "
              f"({pct:.0f}%)")
    print("  NOTE: cold is the trustworthy signal; if cold and recall diverge,")
    print("        trust cold (recall carries hindsight bias).")


def cmd_log(args, path: str) -> None:
    source = args.source.strip().lower()
    if source not in VALID_SOURCE:
        sys.exit(f"REFUSED: --source must be one of {sorted(VALID_SOURCE)}, "
                 f"got {args.source!r}. Nothing logged.")

    score_key = args.score.strip().lower()
    if score_key not in VALID_SCORE:
        sys.exit(f"REFUSED: --score must be one of "
                 f"{[v for v in VALID_SCORE.values()]} (any case), "
                 f"got {args.score!r}. Nothing logged.")
    score = VALID_SCORE[score_key]

    if not (args.why or "").strip():
        sys.exit("REFUSED: --why is required (one line on why this score). "
                 "Nothing logged.")

    _ensure_file(path)
    iid = (args.id or "").strip() or _next_live_id(path)
    tag = (args.tag or "").strip()  # free text; may be empty or ';'-joined
    why = args.why.strip()
    ts = args.date or date.today().isoformat()

    row = [ts, source, iid, score, tag, why]
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

    print(f"LOGGED: {ts}  {source}  {iid}  {score}  [{tag}]")
    print(f"  why: {why}")
    print(f"  -> appended to {path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Append one scored row to the usefulness tally. "
                    "Run pilot_v0 and READ the draft first; this logs your "
                    "judgment, it does not run the agent.")
    ap.add_argument("--source", help="cold | recall")
    ap.add_argument("--score", help="Advances | Salvageable | Stalls (any case)")
    ap.add_argument("--why", help="one line: why this score")
    ap.add_argument("--tag", default="",
                    help="failure-mode tag(s), free text, ';'-join multiples "
                         "(e.g. count-padding;wrong-gating-question). May be empty.")
    ap.add_argument("--id", default="",
                    help="DB inquiry_id or recall thread id. Omit to "
                         "auto-assign the next live-N.")
    ap.add_argument("--date", default="",
                    help="override the timestamp (ISO date). Default: today.")
    ap.add_argument("--file", default=DEFAULT_FILE,
                    help="tally path. Default is repo-anchored; override "
                         "only deliberately.")
    ap.add_argument("--show", action="store_true",
                    help="print the current tally + cold/recall roll-up and exit")
    args = ap.parse_args()

    path = args.file

    if args.show:
        cmd_show(path)
        return

    # logging requires the three core fields; give a clear error if missing
    missing = [n for n in ("source", "score", "why") if not getattr(args, n)]
    if missing:
        ap.error(f"to log a row, provide: {', '.join('--' + m for m in missing)} "
                 f"(or use --show to view the tally).")

    cmd_log(args, path)


if __name__ == "__main__":
    main()
