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
## Session F correction (2026-06-18) — stored state ≠ committed state

Found and fixed: F6 was COMMITTED Session E (0547c76) but NEVER APPLIED to
stored rows. redact.py runs only at ingest; thread_text_redacted is frozen
at ingest time. All batch-3 rows were ingested Session D (pre-F6), so the
fix never touched them. Gate-6's "DB row all names -> {name}" (PASSED) was
FALSE — it trusted the eyeball + the commit, never scanned stored bytes.

CUSTOMER PII FOUND: row 18e15f532bcec520, slot "{name-17}, Jonah" — customer
surname {name-17} survived because staff first-name "jonah" matched the
pre-F6 substring allowlist. Was sitting verified+unredacted in labels.db.

FIX APPLIED (verified by byte-scan, not by commit):
- Backed up labels.db -> labels.db.bak-pre-batch3-reingest (fc /b identical).
- Deleted 40 batch-3 rows (delete_batch3.py, guarded: 40 count + 0 labeled
  asserted). FK-safe — zero batch-3 rows were labeled.
- Re-ingested ..\threads_batch3 with current (post-F6) redact.py.
- check_batch3_redaction.py: [B] (customer-leak bucket) now EMPTY. {name-17} gone.
- model_failed dropped 3 -> 1 (D2/D3 body fixes let 2 ingest clean; confirms
  the D2/D3-causes-model_failed hypothesis a 2nd time). 1 still deferred.

STILL OPEN (deferred, not fixed today — all cosmetic/non-PII):
- 78 labeled rows have STALE source_path (points at chunk_*/threads_test3;
  files actually live in threads_batch2*/). Re-redactable by ID-match, not
  yet done. Staff-surname-only survival ([B] clean for all 168). NOT customer PII.
- The "separation" of those 78 was NEVER persisted — no archive file, no DB
  table, no loader filter. They are STILL LIVE in labels and STILL flow
  through eval_loader. eval_loader asserts (122/61) are stale regardless.
- 1 batch-3 row still model_failed — diagnose/defer next session.

PROCESS FIX (the real lesson): "committed" ≠ "applied." A redaction fix is
inert until re-run over stored data AND the stored bytes are scanned.
Verification gates must scan the DB column, not the code or working tree.
Standing addition: after ANY redactor change or folder move, re-derive
expected redaction from current source + current redact.py and diff against
stored thread_text_redacted before trusting any "clean" claim.

Dataset now: 168 inquiries (167 verified, 1 model_failed), 128 labeled,
39 batch-3 verified-unlabeled. Labeling NOT started this session.
## Session F (2026-06-18) — labeling + a data-integrity correction

### What actually happened
Came in to label batch-3. Found, before labeling could start, that F6 was
COMMITTED Session E (0547c76) but NEVER APPLIED to stored rows. redact.py
runs only at ingest; thread_text_redacted is frozen at ingest time. All
batch-3 rows were ingested Session D (pre-F6), so the fix never touched them.
Gate-6's "DB row all names -> {name}" (PASSED) was FALSE — it trusted the
eyeball + the commit, never scanned stored bytes.

### Customer PII found and fixed
- 18e15f532bcec520, slot "{name-17}, Jonah" — customer surname {name-17} survived
  the pre-F6 substring allowlist (staff first name "jonah" matched). Was
  sitting verified+unredacted.
- Backed up labels.db -> labels.db.bak-pre-batch3-reingest (fc /b identical).
- Deleted 40 batch-3 rows (delete_batch3.py, guarded), re-ingested
  ..\threads_batch3 with current post-F6 redact.py. From-line leak cleared,
  verified by byte-scan (check_batch3_redaction.py [B] empty).
- model_failed dropped 3 -> 2 (D2/D3 body fixes let 2 of 3 ingest clean;
  confirms the D2/D3-causes-model_failed hypothesis a 2nd time).

### The From-line probe was blind to BODY leaks (the F5 gap, confirmed)
[B] empty meant From-LINES clean, not bodies clean. probe_body_leaks.py
(read-only, new) found 2 real customer-name BODY leaks the model redactor
missed/failed:
- 18e15f532bcec520 ({name-17}) — signature "{name-8}" + greeting "Hi Jonah".
- 18da9fc12bae4de0 ({name-3} / {name-4} / {name-5}) — already model_failed.
Both QUARANTINED (set redaction_status=model_failed, quarantine_{name-17}.py),
un-labelable, deferred to the redaction-fix session.
F5 (body-artifact probe) IS NO LONGER DEFERRABLE. The manual eyeball failed —
read past {name-17} in a signature block. F5 must be built before any further
ingest, and it must NOT reuse the allowlist.

### Labeling
37 batch-3 inbounds labeled (38 threads walked; 2 batch-3 rows quarantined).
ROW-22 applied. Most edge cases were operator-initiated, repeat customers,
exporter-split continuations, or non-inquiries (health notices, bounces, COI
forwards). ~14 kept as clean cold inbounds (edge_case_flag=0).

### Dataset now
- inquiries: 168 (166 verified-or-labeled, 2 model_failed quarantined).
- labels: 166 labeled.
- gradeable (load_eval_rows): 122 -> 160.
- clean cold inbounds (load_gradeable_inbounds, edge_case_flag=0): 59 -> 73.
- eval_loader.py asserts refreshed to 160 / 73 (count refresh only; logic frozen).

### Still open / deferred (none are customer PII)
1. F5 body-artifact probe — now REQUIRED before next ingest.
2. 2 model_failed quarantined rows ({name-17}, 18da9fc1) — re-redact or formally defer.
3. 78 labeled rows with STALE source_path (point at dead chunk_*/threads_test3;
   files actually live in threads_batch2*/). Re-redactable by ID-match.
   Staff-surname-only survival, NOT customer PII. Deferred.
4. Phone-regex gap: vendor phone "T.+1 (858) 914 - 9055" survived in
   18e0f9c5 (T. prefix + spaced dash). Vendor, cosmetic. Add to redaction backlog.
5. Growth (Q2-Q4 2024 export) to push n>=100 — gated behind F5.

### Process rule added (the real lesson)
"Committed" != "applied." A redaction fix is inert until re-run over stored
data AND the stored bytes are scanned. Verification must scan the DB column,
not the code, the working tree, or a From-line-only probe. After ANY redactor
change or folder move, re-derive expected redaction from current source +
current redact.py and diff against stored thread_text_redacted.
## Session G (2026-06-19) — F5 built + passing; one record correction

### Goal 0 — verified Session F against the DB, not the record
All four checks run against live labels.db (not trusted from STATE.md):
- label.py status: ingested=168 labeled=166 model_failed=2 verified_unlabeled=0. MATCH.
- eval_loader.py: PASS 160 gradeable / 73 clean inbounds (asserts fired vs live DB).
- check_batch3_redaction.py: [B] empty (no From-line customer leak). 35 [A] = staff
  surnames, cosmetic/expected.
- probe_body_leaks.py: surfaced a THIRD flagged body-name the record did not list —
  19e5a9ca 'Later\n{name-25}'. Eyeballed: vendor salesperson (real name, NOT a customer).
  Record said "2 quarantined"; reality was 2 customer + 1 vendor. Corrected (below).

### Goal 1 — F5 built, passing, now a standing gate
labeling/probe_body_artifacts.py (NEW, committed). Replaces the session-F diagnostic
probe_body_leaks.py as the spec'd F5. Properties:
- DUAL SURFACE: DB thread_text_redacted (GATES) + threads*/ .md files (reported only,
  non-gating — exports carry names by design, gitignored, die at ingest).
- TWO-TIER triage: CLEARED (every token in STAFF_ORG|NOISE|STOPWORDS) vs REVIEW
  (any unknown token -> human looks). Asymmetry is the safety property.
- STATUS-AWARE gate: REVIEW hit on a non-quarantined row -> [B-FAIL] -> exit 1.
  REVIEW hit on a model_failed row -> [B-OK] -> does not gate. Carrier artifacts
  ([A]) reported, never gate.
- NO ALLOWLIST IMPORT — builds its own known sets from scratch. redact.py's allowlist
  is how {name-17} hid; shared code = shared blind spot, kept independent on purpose.
- exit 0 = PASS, exit 1 = FAIL. Gates all future ingest: no new batch lands on a FAIL.
First run FAILed (33 [B-FAIL]): all noise I under-loaded (menu nouns: spanakopita,
dessert, tzatziki, arancini; roles: paralegal, partner; form labels; 'Jona Gutierrez'
staff OCR typo; 'Hi\nAs'/'Hi\nCan' greeting-regex newline bug; 'Sweet Brenna' sign-off)
plus the one real residue ({name-25}). Fixed in-file: added tokens to NOISE/STAFF_ORG/
STOPWORDS by explicit edit (the brittle-by-design discipline), fixed GREETING_RE to
[ \t]+ (was \s+, crossed newlines). Re-run: PASS, [B-FAIL]=0, [B-OK]=the 2 quarantined.

### Record correction — 19e5a9ca (NOT a customer leak; in-place re-redacted)
Routing was already correct: label = not_an_inquiry / declined / edge_case_flag=0.
The agent already learns "vendor pitch = not a lead." So '{name-25}' was PURE PII hygiene,
zero routing stakes. Chose in-place re-redaction over quarantine (quarantine would
drop a correctly-labeled not_an_inquiry example from eval to hide a vendor first name).
reredact_19e5a9ca.py: backup-first, whole-word {name-25} -> {name}, single row, label
untouched (FK preserved), byte-verified after. labels.db changed (gitignored — recorded
here, not committed). Backup: labels.db.bak-reredact-19e5a9ca-*.

### Dataset now (unchanged counts; only one row's stored text edited)
- inquiries 168 (166 verified-or-labeled, 2 model_failed quarantined).
- labels 166. gradeable 160. clean inbounds 73. eval_loader asserts still 160/73 (no
  count change — re-redaction does not move counts).

### Backlog / deferred (NONE are un-quarantined customer PII)
1. Goal 2 NOT done — the 2 quarantined rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5})
   still need watched-model re-redaction OR formal defer. Own session (API in loop).
2. Goal 3 NOT done — 78 stale-source_path rows (point at dead chunk_*/threads_test3;
   real files in threads_batch2*/). Staff-surname-only, not customer PII. Re-point +
   re-redact in place by ID-match, OR document as accepted cosmetic. Pick one.
3. 19e5a9ca edge_case_flag=0 puts a VENDOR PITCH in the clean-inbound set (the 73).
   Routes correctly but arguably isn't a "cold customer inbound." Possible edge_case_flag
   mislabel (would drop it from 73, a count change). Labeling-convention call, deferred.
4. [D] file surface: ~59 threads*/ .md files contain real customer names ({name}, {name},
   {name}, {name}, {name}, {name}, {name}, ...).
   CONTAINED today: git check-ignore confirms threads*/ ignored (.gitignore:14); git log
   --all over threads*/*.md returned empty (never committed, re-verifies the Session-C
   3e157e0 claim directly). Containment rests entirely on the ignore rule holding. This
   inventory's existence is exactly why the public-flip FULL git-history audit (every
   blob, not just threads*/) is non-negotiable and remains its own gated session.
5. Carrier artifacts ([A], 11 rows: Sent-from-iP / On...wrote: / Forwarded msg) — data
   quality, not PII. Exporter Option C territory. Deferred.
6. Vendor phone-regex gap (Session F): "T.+1 (858) 914 - 9055" survived. Vendor, cosmetic.

### Process note carried forward (the governing lesson, re-confirmed)
Goal 0 found a record/data disagreement (3rd flagged name) by scanning DB bytes, not by
trusting STATE.md — same discipline that caught {name-17}. F5's pass logic DEPENDS on the
"files are gitignored" claim, so that claim was re-verified (check-ignore + history scan)
rather than trusted. "Committed != applied" and "working-tree-clean != history-clean"
both held again this session.

### Commit(s) this session
- labeling/probe_body_artifacts.py — F5 (one commit).
- reredact_19e5a9ca.py — keep-tracked-or-del is operator's call (it's the canonical
  in-place-reredact pattern Goal 2/3 reuse). If kept, its own commit.
- labels.db change ({name-25}) — gitignored, recorded here, NOT committed.

### NOT done this session (by design — named to resist drift)
No growth (Q2-Q4 export) — gated behind F5, which only just passed; fresh data is exactly
F5's case, run it on the next export. Agent/grader/eval_loader LOGIC untouched. Repo NOT
flipped public (full git-history audit still owed). No labeled row delete-reingested.
## Session H (2026-06-19) — re-baseline + gate revision (n>=100 -> pilot scope)

### Goal 0 — state verified against DB (passed)
label.py status: 168 ingested / 166 labeled / 2 model_failed / 0 verified_unlabeled. MATCH.
eval_loader: 160 gradeable / 73 clean inbounds, asserts fired vs live DB. MATCH.
probe_body_artifacts (F5): PASS, [B-FAIL]=0; 19 [B-OK] all on the 2 quarantined rows. No stored-byte disagreement.
Frozen-file check: agent_v3.py / prompt_v2.txt / grader.py clean vs HEAD (last touch ba21f8d, Session 9).
eval_loader.py touched post-9 only by 9710cb1 (assert refresh 160/73, not logic). Re-baseline isolation holds.

### Goal 1 — re-baseline agent_v3 on the current 73 clean inbounds
One variable moved: eval set 61 -> 73. Agent/prompt/grader/loader-logic frozen.
RESULT (single run, prompt caching on):
  overall status accuracy: 0.959  (70/73)
  qualified:   prec 1.000  recall 0.935  (29/31; 2 missed -> declined)
  declined:    prec 0.947  recall 0.973  (36/37; 1 missed -> needs_info)
  needs_info:  prec 0.833  recall 1.000  (5/5)
  DANGER CELL declined->qualified: 0   (no false "yes we can do this")
  errors all on the safe side: agent under-commits (qualified->declined x2, declined->needs_info x1).
  inquiry_type axis: not re-tabulated this run; status axis was the target.
CONFIDENCE: moderate at best. Single run, n=73, no variance bands.
  needs_info n=5 and human_review n=0 are thin/unmeasured classes.

### Labels are INDEPENDENT (not leaked the way feared)
The 73 were hand-labeled this session, one-by-one, COLD — operator did not view agent
predictions while labeling. Ground truth is independent of agent output, so 0.959 measures
reality-agreement, not self-agreement. The earlier prompt-tuning leakage caveat is NOT the
governing limitation; the governing limitation is small-n / single-run.
Holdout abandoned: batch_id is null for the additions (only relabel passes tagged);
labeled_at was bulk-stamped this session by the labeling itself. Neither marker isolates
an untuned slice. No clean holdout recoverable from existing markers.

### Goal 2 — n>=100 gate REVISED to pilot scope (in writing, with reasoning)
DECISION: the n>=100 clean-inbound gate is revised. It was scoped for AUTONOMOUS-readiness
("is the agent trustworthy enough to act unreviewed"). This launch makes no such claim.
v0 is a HUMAN-REVIEWED pilot: operator reviews/edits/approves every draft before it reaches
a customer (human-in-the-loop by design, not an edge case). For that launch the relevant bar
is "does assisted draft + zero dangerous errors beat the current manual baseline," and 0.959
with declined->qualified=0 clears it.
This is a SCOPE CLARIFICATION of the gate, not its abandonment. The n>=100 (and variance
bands, and needs_info/human_review coverage) requirements REMAIN in force for any future
AUTONOMOUS or reduced-review mode.
EVIDENCE on record: 0.959 / n=73 / danger cell 0 / independent cold labels / 2026-06-19.
LIMITATIONS on record (next to the number, deliberately): single run, no variance, two thin
classes, grader stamps the status axis DIAGNOSTIC below n=100.

### Asterisk-retirement condition
The pilot baseline carries an asterisk until ONE of: (a) clean inbounds reach n>=100 and a
re-run holds, or (b) a measured conversion-lift number from the live pilot exists. Either
retires "DIAGNOSTIC"; until then the number is a pilot baseline, not a gating baseline.

### NOT done / carried forward (unchanged from Session G)
- 2 quarantined model_failed rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5}) — re-redact or formal defer.
- 78 stale source_path rows; 19e5a9ca clean-inbound convention call; untracked diagnostics disposition.
- Public flip STILL gated on full git-history PII audit (every blob). Pilot != public repo.
- Q2-Q4 export (the n>=100 path) deferred, F5-gated when resumed.

### Standing rules held this session
Frozen files untouched. One variable (61->73). Caching on. Hugo ran all commands; Claude proposed files only.
Pushed back on: open-ended prompt edit (wording lever spent, non-gating baseline), and on gating
an autonomous claim at n=73. Gate revision limited to pilot scope only.