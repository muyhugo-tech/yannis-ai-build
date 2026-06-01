"""
Eval data loader  --  Step 2 of the eval harness.

This is the highest bug-risk component. Every metric the grader produces
is computed on whatever rows this loader returns. If it returns the wrong
rows, every downstream number is wrong AND looks plausible -- nothing
crashes. So this file does three jobs, in a specific order, and each is a
place to get it silently wrong.

JOB 1 -- latest label per inquiry.
  labels.db stores one row per labeling EVENT. Relabels were inserted as
  new rows, not updates. So an inquiry can have several rows: the original
  plus corrections. We must keep only the most recent. Confirmed in the
  data: 55 total rows, 50 distinct inquiries -> 5 relabels.
  Sort key: labeled_at (ISO text, sorts correctly), tie-broken by label_id
  (higher = inserted later). The tiebreak matters because relabel_fixes.py
  inserted all 5 corrections at the SAME timestamp; within one inquiry that
  is currently fine, but the tiebreak removes a future silent bug.

JOB 2 -- drop EXCLUDE_FROM_EVAL rows.
  Two stitched threads are marked for exclusion. The marker lives as the
  literal prefix 'EXCLUDE_FROM_EVAL:' in edge_case_reason. CRITICAL ORDER:
  we pick the latest label FIRST, then check exclude on that latest row.
  The exclude marker exists on the relabel rows, and checking before
  picking-latest would mis-handle the original rows.

JOB 3 -- expose both decision fields.
  The grader grades two axes: qualification_decision (status) and
  inquiry_type (where the 64% not_an_inquiry majority lives). Both are
  returned per row.

Target: 50 distinct inquiries -> 50 latest rows -> drop 2 excluded -> 48
gradeable rows. That 48 is the proof-of-correctness number.
"""

import sqlite3
from dataclasses import dataclass


# The marker that flags a row as not-gradeable, as it actually appears in
# edge_case_reason. We match on this prefix.
EXCLUDE_MARKER = "EXCLUDE_FROM_EVAL"


@dataclass
class EvalRow:
    """One gradeable inquiry: just the fields the grader needs.

    We deliberately do NOT carry the whole 27-column label row around.
    The grader needs the id (to join against agent outputs), the two
    decision axes, and the response text + language for the voice checks.
    Keeping this narrow means a change to some unrelated label column
    cannot accidentally affect grading.
    """
    inquiry_id: str
    qualification_decision: str
    inquiry_type: str
    language: str
    response_sent: str | None


# ---------------------------------------------------------------------------
# The SQL that does Job 1 and Job 2 together.
#
# Read it inside-out:
#
#   The inner query (the "latest" subquery) finds, for each inquiry_id,
#   the label_id of its most recent row. It sorts every row by
#   (labeled_at, label_id) descending and, per inquiry_id, keeps the top
#   one. SQLite's window function row_number() does this: it numbers rows
#   1, 2, 3... within each inquiry_id group, ordered newest-first, so the
#   newest row always gets number 1.
#
#   The outer query keeps only the rows whose number is 1 (the latest per
#   inquiry), then drops any whose edge_case_reason starts with the
#   exclude marker. Exclude is checked on the LATEST row, after latest has
#   been chosen -- the correct order.
#
# COALESCE(edge_case_reason, '') turns a NULL reason into an empty string
# so the LIKE comparison never trips over NULL.
# ---------------------------------------------------------------------------
_LATEST_GRADEABLE_SQL = """
WITH ranked AS (
    SELECT
        inquiry_id,
        qualification_decision,
        inquiry_type,
        language,
        response_sent,
        edge_case_reason,
        ROW_NUMBER() OVER (
            PARTITION BY inquiry_id
            ORDER BY labeled_at DESC, label_id DESC
        ) AS rn
    FROM labels
)
SELECT
    inquiry_id,
    qualification_decision,
    inquiry_type,
    language,
    response_sent
FROM ranked
WHERE rn = 1
  AND COALESCE(edge_case_reason, '') NOT LIKE ?
ORDER BY inquiry_id
"""


def load_eval_rows(db_path: str) -> list[EvalRow]:
    """Return the gradeable rows: latest label per inquiry, exclusions dropped.

    Read-only. Opens the DB, runs one query, closes it.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(_LATEST_GRADEABLE_SQL, (f"{EXCLUDE_MARKER}%",))
        rows = [
            EvalRow(
                inquiry_id=r[0],
                qualification_decision=r[1],
                inquiry_type=r[2],
                language=r[3],
                response_sent=r[4],
            )
            for r in cursor.fetchall()
        ]
    finally:
        conn.close()
    return rows


def summarize(rows: list[EvalRow]) -> dict:
    """A small diagnostic summary -- counts per axis. Lets us eyeball that
    the loaded data matches the known dataset shape (64% not_an_inquiry,
    etc.) without trusting a single total."""
    from collections import Counter
    return {
        "n_rows": len(rows),
        "by_inquiry_type": dict(Counter(r.inquiry_type for r in rows)),
        "by_qualification": dict(Counter(r.qualification_decision for r in rows)),
    }


if __name__ == "__main__":
    import sys
    # Default to the known path; allow override as a command-line argument.
    db = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\yannis-ai-build\labeling\labels.db"
    rows = load_eval_rows(db)
    s = summarize(rows)
    print(f"gradeable rows: {s['n_rows']}  (expected 48)")
    print("by inquiry_type:", s["by_inquiry_type"])
    print("by qualification:", s["by_qualification"])
    # Hard check: the proof-of-correctness number.
    assert s["n_rows"] == 48, f"EXPECTED 48 gradeable rows, got {s['n_rows']}"
    print("PASS: loader returned the expected 48 gradeable rows")
