# STATE — Yanni's catering qualifier (code state of record)

Update this at the END of every build session. It records what is TRUE on
disk now, not what was decided in conversation. Next session: read this,
attach the files it names, then start. Do not rediscover.

Last updated: 2026-06-17 (end of Session E).

---

## One-paragraph state

Session E cleared the F2/F3 commit blocker. F6 (the allowlist surname
leak) is fixed and committed: _ALLOWLIST's substring match was replaced
with a two-tier full-coverage rule (is_allowlisted), staff full names and
exact org slot strings added as explicit phrases so staff identity and
channel signal survive, and probe_from_lines.py rewired to share the
helper (it had carried the same blind spot). Re-run probe across all
surfaces went 113 -> 2, the 2 being one customer slot ("{name-17}, Jonah" —
customer {name-17}, staff first name Jonah) correctly redacting. The F2/F3
exporter fixes and the .gitignore changes are now committed too. Three
commits this session: 0547c76 (F6), 1fa648b (F2/F3), bf150e8 (.gitignore).
Still BLOCKED before growth: nothing on the commit side; remaining option-C
item is F5 (body probe). Then the 3 model_failed threads, then labeling.
Two PII surfaces earlier audits missed surfaced this session (F6's surname
leak; labels.db.bak-pre-002 was untracked but NOT gitignored — now covered
by *.db.bak*). The agent, grader, loader logic, and prompts were untouched
all session.

---

## What got committed this session (Session E)

- **F6** (commit 0547c76): `labeling/redact.py` (two-tier is_allowlisted
  replacing the substring match; staff full names + exact org slot phrases
  added), `labeling/probe_from_lines.py` (rewired to import is_allowlisted),
  `tests/test_redact_allowlist.py` (NEW, 11 tests incl. over-match guards
  and the customer/staff first-name collision).
- **F2/F3** (commit 1fa648b): `export_text.py` (NEW), `export_threads.py`
  (rewired), `tests/test_export_text.py` (NEW, 14 tests).
- **.gitignore** (commit bf150e8): `threads*/` glob + `*.db.bak*`. The
  latter closes a real gap — labels.db.bak-pre-002 was untracked but NOT
  ignored (the `*.db` rule misses the .bak suffix); a `git add .` would
  have committed the whole DB.

Full suite green at commit time: 25 passed (14 F2/F3 + 11 F6).

## Committed prior session (Session D)

- **F1** (commit 7561fe1): `labeling/migrations/002_add_model_failed_status.py`
  (new), `labeling/schema.sql` (model_failed added to redaction_status
  CHECK), `labeling/label.py` (cmd_status now counts model_failed).
  Migration applied to labels.db; counts held (128 inquiries, 145 labels).
  Backup at `labeling/labels.db.bak-pre-002` (untracked AND now gitignored;
  rollback = copy it back over labels.db).

## Working tree after Session E commits

Clean of the option-C commit set. Remaining uncommitted/untracked items are
the long-standing diagnostics pile (see bottom) and notes/, committed as the
session record. No leak-bearing state remains in the working tree.

---

## Dataset state

- Clean cold inbounds (edge_case_flag=0): **59** (was 61; Session D
  relabels moved 2 to edge_case, 1 stayed clean as needs_info).
  s9_relabel batch, 3 rows:
  - 199bba0feb1dda0d -> edge_case_flag=1 (operator-initiated)
  - 19a557d555deff9c -> edge_case_flag=1 (mid-thread artifact)
  - 19a9e3565e6b65ba -> qualified -> needs_info (boundary call, see below)
- inquiries table: **168** rows (128 + 40 batch-3). Status breakdown:
  165 verified, **3 model_failed**.
- labels table: 145 rows (142 + 3 s9_relabel).
- The 40 batch-3 rows are ingested but **not yet labeled**. 37 are
  verified/labelable; 3 are model_failed (un-labelable until re-redacted).

### ROW-22 BOUNDARY RULE (carry forward — labeling convention for batch 3+)
Set by the 19a9e3565e6b65ba relabel and written into its decision_reasoning:
**qualified requires message 1 to ASSERT an event exists** (missing details
do NOT downgrade); **a capability question with no asserted event is
needs_info** (e.g. "what do you offer for groups over 15?" with no date /
occasion / statement that a gathering is being planned). Apply consistently
when labeling the batch-3 inbounds.

---

## eval_loader assert drift (KNOWN, deferred)

`eval/eval_loader.py` `__main__` still asserts 122 gradeable / 61 clean
inbounds. Clean inbounds are now 59, and gradeable will change once batch-3
labels land. These asserts are a count-check refresh, not loader logic —
update them once the batch-3 labeling settles and the true counts are
known. Do not update piecemeal mid-growth.

---

## Open items (ordered)

1. **F5 — body-artifact probe** (`probe_body_artifacts.py`). Not built;
   Session D used manual eyeball. Build it so body-leak detection is
   automated and does NOT reuse the allowlist (it must not inherit the
   blind spot F6 just exposed in probe_from_lines).
2. **3 model_failed batch-3 threads** — diagnose why the model pass failed
   (likely oversized/odd content), then re-redact or formally defer per
   batch-2 precedent. They are un-labelable meanwhile. Do not retry inline
   in a loop.
3. **Label the 37 verified batch-3 inbounds**, applying the row-22
   boundary rule. This is the actual growth toward n>100 clean inbounds.
4. **Resume growth Q2–Q4 2024** at --max 80, slice-probe-eyeball-ingest
   per the Session D handoff discipline. Q1 returned 40 at the cap, so
   2024 alone plausibly clears n>100; 2023 H2 fallback likely unneeded.
5. Update eval_loader asserts (still say 122/61; clean inbounds are 59
   pre-batch-3 and will grow) once batch-3 labeling settles. Count refresh,
   not loader logic. Do not update piecemeal mid-growth.

DONE this session: F6 (0547c76), F2/F3 commit (1fa648b), .gitignore
(bf150e8).

## What stayed frozen (do not rediscover as "missing")

- agent_v3.py, prompts, grader.py, stubs.py, eval_loader logic,
  agent_output_schema.py — ALL untouched in Sessions D and E. Session 9's
  0.934 (leaked, optimistic) is still the last status number; the honest
  n>100 test has NOT been run and waits on growth.
- Non-graded AgentOutput fields (fit_score, confidence, edge_flags) still
  placeholders.
- agent_outputs table still unused.

## Standing rules (unchanged)

Direct Anthropic SDK, no frameworks. Prompt caching from first commit. One
variable per eval cycle. Hugo runs all terminal commands; Claude edits
files only. Confidence labels on every claim. Push back on scope creep.
Split venvs: `.venv` = Google (export), `venv` = Anthropic (ingest, pytest).
REMOTE IS PRIVATE — do not flip public until: (a) the redaction work is
fixed AND committed (F6 done 0547c76; F5 body probe still open), AND (b) a
FULL GIT-HISTORY PII audit passes — every blob in history, not just the
working tree. `git check-ignore` and a clean `git status` only describe
going-forward state; they say nothing about what earlier commits already
contain. This session found TWO PII surfaces earlier audits missed (F6's
surname leak; labels.db.bak-pre-002 untracked-but-not-ignored), which is
direct evidence that working-tree-clean != history-clean. The history scan
is its own gated session. Thread folders are gitignored (`threads*/`) and
local-only; .md exports carry signature names by design (they die at
ingest) and must never be committed.

## Untracked diagnostics pile (decision still pending, not this session)

eval/check_counts.py, check_edge_flag.py, inspect_*.py, probe_misses.py;
labeling/b2_relabel.py, check_b2.py, dump_b2_rows.py, find_holdout.py,
rerun_redact_*.py, probe_relabel_targets.py, check_batch3_landed.py,
verify_ingest_redaction.py, relabel_s9.py; audit_pii.py. relabel_s9.py
documents a ground-truth change and is the strongest candidate to actually
track. (probe_from_lines.py left this pile — committed in 0547c76 as F6's
shared-helper consumer; STATE_session_C_entry.md committed with the notes.)
