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

--- TWO LOADER PATHS (added session 8) ---
  load_eval_rows         -> ALL gradeable rows (122). Feeds the STUB-based
                            grader; needs no inquiry body. UNCHANGED.
  load_gradeable_inbounds-> CLEAN cold inbounds only (edge_case_flag=0, 61
                            rows), each carrying message-1 body. Feeds the
                            REAL agent, which must read an inquiry and decide.
  The two are separate on purpose: the stub proof and the real-agent baseline
  ask different questions and must not interfere.
"""

import re
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


# ===========================================================================
# CLEAN-INBOUND PATH (session 8) -- the REAL-AGENT eval set.
#
# load_eval_rows above is untouched and still feeds the stub grader over all
# 122 rows. The functions below are a SEPARATE path: clean cold inbounds only
# (edge_case_flag = 0), each carrying the message-1 body the agent reads.
#
# Why a separate dataclass and query rather than extending EvalRow: a body-
# parsing change must not be able to affect the stub path. Isolation is the
# same discipline the original file applied by keeping EvalRow narrow.
# ===========================================================================


@dataclass
class InboundRow:
    """One gradeable COLD INBOUND: label fields PLUS the inquiry body.

    inquiry_text is message 1's body -- the customer's cold-open email, the
    exact thing the agent must triage. We do NOT include later messages
    (Yanni's replies, the outcome) so the agent is graded on triaging the
    inquiry, not on reading a resolved conversation.
    """
    inquiry_id: str
    qualification_decision: str
    inquiry_type: str
    language: str
    inquiry_text: str
    response_sent: str | None


# Latest label per inquiry (same JOB-1 ranking), joined to the inquiry body,
# filtered to clean inbounds. edge_case_flag = 0 was proven in
# check_edge_flag.py to align exactly with empty edge_case_reason (61 flag=0,
# all empty; 67 flag=1, all with a reason; zero mismatches). Since every
# EXCLUDE_FROM_EVAL row carries a reason, it is flag=1 and already dropped by
# the flag=0 filter -- no separate exclude clause needed here.
_CLEAN_INBOUNDS_SQL = """
WITH ranked AS (
    SELECT
        l.inquiry_id,
        l.qualification_decision,
        l.inquiry_type,
        l.language,
        l.response_sent,
        l.edge_case_flag,
        i.thread_text_redacted,
        ROW_NUMBER() OVER (
            PARTITION BY l.inquiry_id
            ORDER BY l.labeled_at DESC, l.label_id DESC
        ) AS rn
    FROM labels l
    JOIN inquiries i ON i.inquiry_id = l.inquiry_id
)
SELECT
    inquiry_id,
    qualification_decision,
    inquiry_type,
    language,
    response_sent,
    thread_text_redacted
FROM ranked
WHERE rn = 1
  AND edge_case_flag = 0
ORDER BY inquiry_id
"""


def _first_message_body(thread_text: str) -> str:
    """Extract message 1's BODY from a thread.

    Threads are delimited by '## Message N' and each block has a header of
    '**From:** ...' / '**Date:** ...' lines, then a blank line, then the body.
    We take the first block and return everything after its header.

    If the structure is unexpected we return the block with only the
    '## Message N' line stripped, rather than silently emptying it, so a
    parsing miss shows up in the agent's input instead of hiding.
    """
    if not thread_text:
        return ""
    blocks = [p for p in re.split(r"(?=## Message)", thread_text) if p.strip()]
    if not blocks:
        return thread_text.strip()
    first = blocks[0]

    lines = first.splitlines()
    body_start = None
    seen_from = False
    for idx, ln in enumerate(lines):
        if ln.strip().startswith("**From:**"):
            seen_from = True
        if seen_from and ln.strip() == "":
            body_start = idx + 1
            break
    if body_start is None:
        body_lines = [ln for ln in lines if not ln.strip().startswith("## Message")]
        return "\n".join(body_lines).strip()
    return "\n".join(lines[body_start:]).strip()


def load_gradeable_inbounds(db_path: str) -> list[InboundRow]:
    """Return clean cold inbounds (edge_case_flag=0) with message-1 body.

    This is the REAL-AGENT eval set: the agent reads inquiry_text and we grade
    its decision against the stored label. Distinct from load_eval_rows, which
    feeds the stub-based grader over all 122 rows and needs no body.
    Read-only.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(_CLEAN_INBOUNDS_SQL)
        rows = [
            InboundRow(
                inquiry_id=r[0],
                qualification_decision=r[1],
                inquiry_type=r[2],
                language=r[3],
                response_sent=r[4],
                inquiry_text=_first_message_body(r[5]),
            )
            for r in cursor.fetchall()
        ]
    finally:
        conn.close()
    return rows


if __name__ == "__main__":
    import sys
    # Default to the known path; allow override as a command-line argument.
    db = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\yannis-ai-build\labeling\labels.db"
    rows = load_eval_rows(db)
    s = summarize(rows)
    print(f"gradeable rows: {s['n_rows']}  (expected 160)")
    print("by inquiry_type:", s["by_inquiry_type"])
    print("by qualification:", s["by_qualification"])
    # Hard check: the proof-of-correctness number.
    # Derived 2026-06-09: 142 label rows, 128 distinct inquiries (14 relabels
    # collapsed), drop 6 EXCLUDE_FROM_EVAL rows -> 122 gradeable.
    # Updated 2026-06-18 (Session F): 37 batch-3 inbounds labeled (2 batch-3
    # rows quarantined model_failed, un-labelable) -> 160 gradeable.
    # Re-run check_counts.py to re-derive if the dataset grows again.
    assert s["n_rows"] == 160, f"EXPECTED 160 gradeable rows, got {s['n_rows']}"
    print("PASS: loader returned the expected 160 gradeable rows")

    # Clean-inbound path sanity: count + one sample body (truncated).
    inbounds = load_gradeable_inbounds(db)
    print(f"\nclean cold inbounds (edge_case_flag=0): {len(inbounds)}  (expected 73)")
    assert len(inbounds) == 73, f"EXPECTED 73 clean inbounds, got {len(inbounds)}"
    sample = inbounds[0]
    preview = sample.inquiry_text[:200].replace("\n", " ")
    print(f"  sample inquiry_text[:200]: {preview!r}")
    print("PASS: clean-inbound loader returned 73 rows with bodies")
