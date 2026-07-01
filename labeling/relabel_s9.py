"""relabel_s9.py -- apply the Session 9 residual-miss relabels (Session D, Goal 1).

Three rows, decided 2026-06-12:

  199bba0feb1dda0d (S9 row 1)  -> edge_case_flag=1: operator-initiated thread,
                                  not a clean cold inbound. Label values
                                  otherwise correct; thread leaves the clean set.
  19a557d555deff9c (S9 row 2)  -> edge_case_flag=1: mid-thread inquiry, message 1
                                  opens 'Thank you for getting back to me' --
                                  prior context never exported. Data artifact.
  19a9e3565e6b65ba (S9 row 22) -> qualification_decision qualified -> needs_info.
                                  Operator review decision. Stays in the clean
                                  set: edge_case_flag remains 0, reason None.

MECHANICS (relabel_fixes.py precedent, one deliberate change):
  - INSERT new label rows, never UPDATE. Latest-wins downstream via
    (labeled_at DESC, label_id DESC). Audit trail intact.
  - Deviation from precedent: instead of hand-transcribing full replacement
    rows, each fix COPIES the current latest row and overrides only the
    target fields. Same insert mechanics, zero transcription risk.
  - batch_id 's9_relabel', labeled_by 'hugo'.

GUARDS:
  - Refuses to run if any target already has an 's9_relabel' row (no double-run).
  - Asserts each target's current latest row matches the expected pre-state
    (the probe output of 2026-06-12). Any mismatch aborts before any write.
  - All three inserts in one transaction: all land or none do.
  - Post-checks: clean-inbound count 61 -> 59; gradeable count stays 122;
    each target's new latest row shows the override.

Run from labeling\\ (any venv, stdlib only):
    python relabel_s9.py
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

DB = sys.argv[1] if len(sys.argv) > 1 else "labels.db"
BATCH_ID = "s9_relabel"
LABELED_BY = "hugo"

# The label-table columns we copy forward, in insert order. label_id is
# excluded (autoincrement); labeled_at/labeled_by/batch_id are stamped fresh.
COPY_COLS = (
    "inquiry_id", "received_at", "channel", "inquiry_type", "language",
    "group_size", "lead_time_days", "date_specificity", "budget_signal",
    "budget_amount", "budget_basis", "menu_tier_fit",
    "qualification_decision", "decision_reasoning", "response_sent",
    "response_latency_hours", "outcome", "friction_points",
    "language_patterns", "edge_case_flag", "edge_case_reason",
    "unresolved_fields",
)

# Each fix: target id, expected pre-state on the CURRENT latest row (guard),
# and the field overrides to apply on the copied row.
FIXES = [
    {
        "inquiry_id": "199bba0feb1dda0d",
        "expect": {"edge_case_flag": 0, "qualification_decision": "qualified",
                   "label_id": 60},
        "override": {
            "edge_case_flag": 1,
            "edge_case_reason": (
                "RELABEL: operator-initiated thread. Message 1 is the operator's "
                "own outreach (holiday-party date follow-up); the customer's first "
                "message is message 2. Not a clean cold inbound -- the agent's "
                "message-1 input is the operator, not a customer. Identified as "
                "Session 9 residual miss row 1; flagged Session D. Label values "
                "otherwise unchanged."
            ),
        },
    },
    {
        "inquiry_id": "19a557d555deff9c",
        "expect": {"edge_case_flag": 0, "qualification_decision": "qualified",
                   "label_id": 61},
        "override": {
            "edge_case_flag": 1,
            "edge_case_reason": (
                "RELABEL: mid-thread inquiry, known data artifact. Message 1 "
                "opens 'Thank you for getting back to me!' -- the true first "
                "contact predates the exported thread, so message 1 is not a "
                "cold open. Identified as Session 9 residual miss row 2 (recovered "
                "in the S9 run by luck, still bad eval data); flagged Session D. "
                "Label values otherwise unchanged."
            ),
        },
    },
    {
        "inquiry_id": "19a9e3565e6b65ba",
        "expect": {"edge_case_flag": 0, "qualification_decision": "qualified",
                   "label_id": 111},
        "override": {
            "qualification_decision": "needs_info",
            "decision_reasoning": (
                "RELABEL (S9 row 22, operator review 2026-06-12): qualified -> "
                "needs_info. Message 1 is a capability question ('what do you "
                "offer for groups that exceed 15 people') -- no event asserted, "
                "no date, no occasion; those arrive in message 3. Boundary rule "
                "set by this decision: qualified requires message 1 to ASSERT an "
                "event exists (missing details still do not downgrade); a "
                "capability question with no asserted event is needs_info. "
                "Operator's own first reply was the needs_info playbook (ask "
                "date/size/budget, attach menus, act on nothing). Original "
                "reasoning preserved: cold inbound birthday gathering, 15-20 "
                "guests, firm Dec 13 date once details arrived; in-restaurant "
                "large group; reservation confirmed; outcome unknown."
            ),
            # edge_case_flag stays 0, edge_case_reason stays None: this is a
            # label correction on a legitimate clean inbound, and the
            # flag=0 <-> empty-reason alignment must hold.
        },
    },
]

CLEAN_COUNT_SQL = """
WITH ranked AS (
    SELECT l.edge_case_flag,
           ROW_NUMBER() OVER (PARTITION BY l.inquiry_id
                              ORDER BY l.labeled_at DESC, l.label_id DESC) AS rn
    FROM labels l
)
SELECT COUNT(*) FROM ranked WHERE rn = 1 AND edge_case_flag = 0
"""

GRADEABLE_COUNT_SQL = """
WITH ranked AS (
    SELECT l.edge_case_reason,
           ROW_NUMBER() OVER (PARTITION BY l.inquiry_id
                              ORDER BY l.labeled_at DESC, l.label_id DESC) AS rn
    FROM labels l
)
SELECT COUNT(*) FROM ranked
WHERE rn = 1 AND COALESCE(edge_case_reason,'') NOT LIKE 'EXCLUDE_FROM_EVAL%'
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def latest_row(cx, inquiry_id: str) -> sqlite3.Row:
    row = cx.execute(
        "SELECT * FROM labels WHERE inquiry_id = ? "
        "ORDER BY labeled_at DESC, label_id DESC LIMIT 1",
        (inquiry_id,),
    ).fetchone()
    if row is None:
        print(f"ABORT: no label rows found for {inquiry_id}")
        sys.exit(1)
    return row


def main() -> None:
    cx = sqlite3.connect(DB)
    cx.execute("PRAGMA foreign_keys = ON")
    cx.row_factory = sqlite3.Row

    # Guard 0: no double-run.
    already = cx.execute(
        "SELECT COUNT(*) FROM labels WHERE batch_id = ?", (BATCH_ID,)
    ).fetchone()[0]
    if already:
        print(f"ABORT: {already} row(s) with batch_id='{BATCH_ID}' already "
              "exist. This script already ran. Nothing written.")
        sys.exit(1)

    # Guard 1: pre-state of every target verified BEFORE any write.
    sources = {}
    for fix in FIXES:
        row = latest_row(cx, fix["inquiry_id"])
        for field, expected in fix["expect"].items():
            actual = row[field]
            if actual != expected:
                print(f"ABORT: {fix['inquiry_id']} pre-state mismatch on "
                      f"{field}: expected {expected!r}, found {actual!r}. "
                      "Nothing written.")
                sys.exit(1)
        sources[fix["inquiry_id"]] = row
    print("pre-state guard PASS: all 3 targets match the 2026-06-12 probe")

    pre_clean = cx.execute(CLEAN_COUNT_SQL).fetchone()[0]
    print(f"clean inbounds before: {pre_clean} (expected 61)")

    # All three inserts, one transaction.
    stamp = now_iso()
    placeholders = ",".join("?" for _ in range(len(COPY_COLS) + 3))
    insert_sql = (
        f"INSERT INTO labels ({', '.join(COPY_COLS)}, labeled_at, labeled_by, "
        f"batch_id) VALUES ({placeholders})"
    )
    try:
        for fix in FIXES:
            src = sources[fix["inquiry_id"]]
            values = []
            for col in COPY_COLS:
                values.append(fix["override"].get(col, src[col]))
            values += [stamp, LABELED_BY, BATCH_ID]
            cx.execute(insert_sql, values)
            changed = ", ".join(f"{k}" for k in fix["override"])
            print(f"  inserted relabel for {fix['inquiry_id']}  "
                  f"(overrode: {changed})")
        cx.commit()
    except Exception as e:
        cx.rollback()
        print(f"ABORT: {type(e).__name__}: {e} -- rolled back, nothing written.")
        sys.exit(1)

    # Post-checks.
    print("\n--- post-checks ---")
    post_clean = cx.execute(CLEAN_COUNT_SQL).fetchone()[0]
    post_gradeable = cx.execute(GRADEABLE_COUNT_SQL).fetchone()[0]
    print(f"clean inbounds after:  {post_clean} (expected 59)")
    print(f"gradeable rows after:  {post_gradeable} (expected 122, unchanged)")

    ok = post_clean == 59 and post_gradeable == 122
    for fix in FIXES:
        new = latest_row(cx, fix["inquiry_id"])
        if new["batch_id"] != BATCH_ID:
            print(f"  FAIL: latest row for {fix['inquiry_id']} is not the "
                  f"s9_relabel insert (batch_id={new['batch_id']!r})")
            ok = False
            continue
        for col, val in fix["override"].items():
            if new[col] != val:
                print(f"  FAIL: {fix['inquiry_id']}.{col} = {new[col]!r}, "
                      f"expected {val!r}")
                ok = False
        print(f"  latest for {fix['inquiry_id']}: "
              f"decision={new['qualification_decision']!r} "
              f"flag={new['edge_case_flag']} batch={new['batch_id']!r}")

    cx.close()
    if ok:
        print("\nPASS: 3 relabels applied. Clean-inbound n is now 59.")
        print("Next: update the n=61 assert in eval_loader __main__ at end of "
              "session (after batch 3 lands), and record n=59 + the row-22 "
              "boundary rule in STATE.md.")
    else:
        print("\nFAIL: post-checks did not all pass. Inserts ARE committed -- "
              "investigate before labeling anything else.")
        sys.exit(1)


if __name__ == "__main__":
    main()
