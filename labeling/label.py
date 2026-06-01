#!/usr/bin/env python3
"""
label.py — terminal labeling workflow for Yanni's lead-triage dataset.

Commands:
  init                          create the DB from schema.sql
  ingest  --dir D [--batch B]   redact every .md in D, write to inquiries
  label   [--inquiry-id ID]     label unlabeled, redaction-verified inquiries
  status                        counts: ingested / labeled / flagged / unlabeled

Disciplines enforced here:
  - Redaction-first: a thread that fails the deterministic gate is stored
    'flagged' and CANNOT be labeled until re-redacted.
  - Unknown-default: every prompt's default is the ignorant value. Pressing
    Enter keeps it. You type only when the thread gives positive evidence.
  - Manual judgment: no model proposes labels. The eval's ground truth is yours.
"""
import argparse, json, os, re, sqlite3, sys, uuid
from datetime import datetime, timezone

import redact

DB_PATH     = os.environ.get("LABEL_DB", "labels.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

ENUMS = {
    "channel":           ["direct_email","typeform","web_form","phone_followup","referral","other","unknown"],
    "inquiry_type":      ["catering","private_event","general","not_an_inquiry","unknown"],
    "language":          ["en","es","mixed"],
    "date_specificity":  ["firm_date","flexible","no_date"],
    "budget_signal":     ["explicit","implied","absent"],
    "budget_basis":      ["per_person","total","unspecified"],  # nullable
    "menu_tier_fit":     ["entry","mid","premium","mixed","unknown"],
    "qualification_decision": ["qualified","needs_info","declined","human_review"],
    "outcome":           ["booked","no_response","declined_by_lead","cancelled","unknown"],
}
# Ignorant defaults (the unknown-default discipline, per-field).
DEFAULTS = {
    "channel":"unknown","inquiry_type":"unknown","language":"en",
    "date_specificity":"no_date","budget_signal":"absent","budget_basis":None,
    "menu_tier_fit":"unknown","qualification_decision":"human_review","outcome":"unknown",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("PRAGMA foreign_keys = ON")
    cx.row_factory = sqlite3.Row
    return cx

# ---------------------------------------------------------------- init
def cmd_init(_):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    cx = connect(); cx.executescript(sql); cx.commit(); cx.close()
    print(f"initialized {DB_PATH}")

# ---------------------------------------------------------------- ingest
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

def parse_thread(text: str) -> tuple[dict, str]:
    """Split frontmatter (simple key: value) from body. Tolerant of no frontmatter."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, m.group(2)

def get_redactor():
    """Return a callable(str)->str that strips names/companies/addresses, or None.
    Wired to the Anthropic-backed name pass in redactor_claude.py.
    Returning None forces every thread to 'names_unredacted' (un-labelable)."""
    try:
        from redactor_claude import redactor
        return redactor
    except Exception as e:
        print(f"WARNING: could not load redactor_claude ({e}). Falling back to None.")
        return None

def cmd_ingest(args):
    redactor = get_redactor()
    if redactor is None:
        print("WARNING: no name/company redactor configured. Threads will be stored")
        print("         'names_unredacted' and CANNOT be labeled until names are removed.")
        print("         Wire a redactor in get_redactor() before running on the real corpus.\n")
    cx = connect()
    files = sorted(f for f in os.listdir(args.dir) if f.endswith(".md"))
    if not files:
        print(f"no .md files in {args.dir}"); return
    ingested = flagged = skipped = 0
    for fn in files:
        path = os.path.join(args.dir, fn)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        fm, body = parse_thread(raw)
        thread_id = fm.get("thread_id") or os.path.splitext(fn)[0]
        inquiry_id = thread_id  # thread-id derived
        if cx.execute("SELECT 1 FROM inquiries WHERE inquiry_id=?", (inquiry_id,)).fetchone():
            skipped += 1; continue

        red_body, status, findings = redact.redact_thread(body, redactor=redactor)
        # Subject lines do NOT go through the model redactor. The model expects
        # full thread structure; a bare subject like "Quote request" gives it
        # nothing to redact and prompts it to invent a plausible thread. Use the
        # deterministic gate only — subjects rarely contain emails/phones anyway.
        red_subject = redact.deterministic_redact(fm.get("subject", ""))
        date_range = fm.get("date_range","")
        dr_start = date_range.split("/")[0].strip() if date_range else None

        cx.execute("""INSERT INTO inquiries
            (inquiry_id, thread_id, source_path, subject_redacted, message_count,
             date_range_start, date_range_end, thread_text_redacted,
             redaction_status, redaction_findings, ingested_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (inquiry_id, thread_id, path, red_subject,
             int(fm["message_count"]) if fm.get("message_count","").isdigit() else None,
             dr_start,
             (date_range.split("/")[1].strip() if "/" in date_range else None),
             red_body, status,
             json.dumps(findings) if findings else None, now_iso()))
        ingested += 1
        if status == "flagged":
            flagged += 1
            print(f"  FLAGGED {inquiry_id}: {len(findings)} structured-PII survivor(s) — re-redact before labeling")
    cx.commit(); cx.close()
    print(f"ingested {ingested} ({flagged} flagged, {skipped} already present)")

# ---------------------------------------------------------------- label
def ask_enum(field, default):
    opts = ENUMS[field]
    while True:
        raw = input(f"  {field} {opts}\n    [{default}] > ").strip()
        if raw == "":
            return default, False
        if raw == "?":   # mark unresolved, keep default
            return default, True
        if raw in opts:
            return raw, False
        print(f"    not in enum. type one of {opts}, Enter for default, or ? to mark unresolved")

def ask_int(field):
    raw = input(f"  {field} [null] (Enter=unknown) > ").strip()
    if raw == "": return None, False
    if raw == "?": return None, True
    try: return int(raw), False
    except ValueError:
        print("    not an int; kept null"); return None, True

def ask_text(field, optional=True):
    raw = input(f"  {field} > ").strip()
    return (raw or None) if optional else raw

def ask_tags(field):
    raw = input(f"  {field} (comma-separated, Enter=none) > ").strip()
    return [t.strip() for t in raw.split(",") if t.strip()]

def cmd_label(args):
    cx = connect()
    if args.inquiry_id:
        rows = cx.execute("SELECT * FROM inquiries WHERE inquiry_id=?", (args.inquiry_id,)).fetchall()
    else:
        rows = cx.execute("""
            SELECT i.* FROM inquiries i
            LEFT JOIN labels l ON l.inquiry_id = i.inquiry_id
            WHERE l.label_id IS NULL AND i.redaction_status = 'verified'
            ORDER BY i.ingested_at""").fetchall()
    if not rows:
        print("nothing to label (no verified, unlabeled inquiries)"); return

    for r in rows:
        if r["redaction_status"] != "verified":
            print(f"\n{r['inquiry_id']}: redaction_status={r['redaction_status']} — skipping, re-redact first")
            continue
        print("\n" + "="*70)
        print(f"INQUIRY {r['inquiry_id']}  ({r['message_count']} msgs, {r['date_range_start']})")
        print(f"subject: {r['subject_redacted']}")
        print("-"*70)
        print(r["thread_text_redacted"])
        print("="*70)
        print("Enter = keep ignorant default. '?' = mark field unresolved.")

        unresolved = []
        vals = {}
        for f in ("channel","inquiry_type","language","date_specificity",
                  "budget_signal","menu_tier_fit","qualification_decision","outcome"):
            v, unk = ask_enum(f, DEFAULTS[f]); vals[f] = v
            if unk: unresolved.append(f)

        for f in ("group_size","lead_time_days","budget_amount","response_latency_hours"):
            v, unk = ask_int(f); vals[f] = v
            if unk: unresolved.append(f)

        vals["budget_basis"] = None
        if vals["budget_signal"] != "absent":
            bb, unk = ask_enum("budget_basis", "unspecified"); vals["budget_basis"] = bb
            if unk: unresolved.append("budget_basis")

        vals["decision_reasoning"] = ask_text("decision_reasoning (1-3 sentences)")
        vals["response_sent"]      = ask_text("response_sent (redacted summary)")
        vals["friction_points"]    = ask_tags("friction_points")
        vals["language_patterns"]  = ask_tags("language_patterns")

        ec = input("  edge_case? [n] (y/N) > ").strip().lower() == "y"
        ec_reason = ask_text("edge_case_reason (required)", optional=False) if ec else None
        while ec and not ec_reason:
            ec_reason = ask_text("edge_case_reason (required)", optional=False)

        cx.execute("""INSERT INTO labels
            (inquiry_id, received_at, channel, inquiry_type, language, group_size,
             lead_time_days, date_specificity, budget_signal, budget_amount, budget_basis,
             menu_tier_fit, qualification_decision, decision_reasoning, response_sent,
             response_latency_hours, outcome, friction_points, language_patterns,
             edge_case_flag, edge_case_reason, unresolved_fields, labeled_at, batch_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["inquiry_id"], r["date_range_start"], vals["channel"], vals["inquiry_type"],
             vals["language"], vals["group_size"], vals["lead_time_days"], vals["date_specificity"],
             vals["budget_signal"], vals["budget_amount"], vals["budget_basis"], vals["menu_tier_fit"],
             vals["qualification_decision"], vals["decision_reasoning"], vals["response_sent"],
             vals["response_latency_hours"], vals["outcome"], json.dumps(vals["friction_points"]),
             json.dumps(vals["language_patterns"]), 1 if ec else 0, ec_reason,
             json.dumps(unresolved), now_iso(), args.batch))
        cx.commit()
        print(f"  saved. unresolved: {unresolved or 'none'}")
    cx.close()

# ---------------------------------------------------------------- status
def cmd_status(_):
    cx = connect()
    ing  = cx.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
    flag = cx.execute("SELECT COUNT(*) FROM inquiries WHERE redaction_status='flagged'").fetchone()[0]
    names = cx.execute("SELECT COUNT(*) FROM inquiries WHERE redaction_status='names_unredacted'").fetchone()[0]
    lab  = cx.execute("SELECT COUNT(DISTINCT inquiry_id) FROM labels").fetchone()[0]
    unl  = cx.execute("""SELECT COUNT(*) FROM inquiries i LEFT JOIN labels l
                         ON l.inquiry_id=i.inquiry_id
                         WHERE l.label_id IS NULL AND i.redaction_status='verified'""").fetchone()[0]
    print(f"ingested={ing}  labeled={lab}  flagged_redaction={flag}  names_unredacted={names}  verified_unlabeled={unl}")
    cx.close()

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    pi = sub.add_parser("ingest"); pi.add_argument("--dir", required=True); pi.add_argument("--batch", default=None); pi.set_defaults(func=cmd_ingest)
    pl = sub.add_parser("label"); pl.add_argument("--inquiry-id", default=None); pl.add_argument("--batch", default=None); pl.set_defaults(func=cmd_label)
    sub.add_parser("status").set_defaults(func=cmd_status)
    args = p.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
