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
## Session I (2026-06-21) — pilot delivery defined + decision axis verified on live runs

### Goal 0 — state verified against the DB (passed)
label.py status: 168 ingested / 166 labeled / 2 model_failed / 0 verified_unlabeled. MATCH.
eval_loader.py: PASS 160 gradeable / 73 clean inbounds (asserts fired vs live DB). MATCH.
probe_body_artifacts (F5): PASS, [B-FAIL]=0; 19 [B-OK] all on the 2 quarantined rows. No stored-byte disagreement.
GIT FINDING (resolved): the Session-H STATE.md amendment was WRITTEN but never committed — found via
`git status --short notes/STATE.md` (` M`) after `git log -1 -- notes/STATE.md` returned empty (the empty
result was a pathspec artifact of running from labeling/, not a missing file). Committed this session as
47fd59c. So the Session-H pilot decision is now persisted, not working-tree-only. Same governing lesson:
the record disagreed with git until the bytes were checked.

### Goal 1 — pilot delivery DEFINED (decided live, in writing)
v0 pilot delivery = **local script, draft emitted as TEXT, operator copies approved drafts by hand.**
NO Gmail write scope, NO deployed service, NO new credential. The inbox is never touched by a program;
the copy-paste IS the review act (human-in-the-loop enforced structurally, not aspirationally).
PATH NOT TAKEN and why: (a) unsent-Gmail-draft delivery was rejected — puts a finished-looking draft one
click from send, erodes the review step the gate revision rests on, and needs gmail.compose scope on the
live inbox. (b) "separate deployed toolset" (operator's mid-session swerve, "don't want to plug into my
machine") was NAMED as scope creep — that is the Week 8-9 MCP/hosted path, gated on autonomous-readiness
this pilot does not claim. The real worry behind the swerve was "program writes to my live inbox," which
the text-output design removes entirely. Lightest thing that works won.

### Goal 1.5 — pilot_v0.py BUILT (uncommitted, operator deferred commit decision)
eval/pilot_v0.py (NEW, on disk, NOT staged this session by operator choice). Single-inquiry harness that
MIRRORS grade_agent.pairs_for_real_agent exactly: load_gradeable_inbounds -> qualify(client, inquiry_text)
-> print decision + draft + checks. Reuses the graded call path so the pilot cannot silently diverge from
what the eval measured. --id (repeatable, pulls clean inbound from DB), --stdin (paste), --list. Prints:
DECISION, DRAFT, the 3 REAL voice checks (run_voice_checks), an email/phone leak scan (new, narrow regex,
strips {curly_tokens} first so echoed placeholders never flag), and an EYEBALL note for names+language.
GATES NOTHING, WITHHOLDS NOTHING this session — it is a reading instrument to answer "is a draft edit-and-
send quality." Quarantine guard: refuses 18da9fc1 / 18e15f53 if ever passed (belt-and-suspenders; they are
not in the clean set anyway).

### Goal 2 — safety-rail TRUTH established (the rails attach to what is real, not assumed)
- DANGER-CELL CHECKER: run_voice_checks IS callable and wired. But it covers 3 of 5 cells. no_em_dash /
  no_emoji / no_pricing are REAL. **language_match is an explicit always-passing STUB (verifies nothing).
  No PII check exists in voice_checks.py at all.** Wiring run_voice_checks as "the gate" without naming
  these two gaps would be the F/G/H trap (green check that tests nothing). For v0: added a narrow email/
  phone leak scan in pilot_v0 (the one PII class with a clean deterministic test); names + language are
  printed as "NOT VERIFIED — eyeball" rather than faked. Real-name detection has no clean deterministic
  test (same wall as language) — deferred, not stubbed-as-passing.
- CONFIDENCE SIGNAL DOES NOT EXIST: agent_v3 PLACEHOLDER_CONFIDENCE = 0.5, hardcoded on every inquiry
  (confirmed in source). The "withhold draft on low-confidence" rail is UNBUILDABLE — it would read a
  constant and fire never. The only real branch signal is `status`. Do not design a confidence gate until
  the agent emits real confidence (its own baseline-resetting step).

### Goal 2 evidence — TWO pilot runs (18 hand-picked rows, single run each, MODERATE confidence)
RUN 1 (9 real event inquiries): all 9 DECISION=qualified, all matched labels. Redaction held everywhere
({email}/{phone}/{address} in agent input, leak scan quiet). Parsing clean incl. carrier-line noise
("Sent from my Verizon..." read past correctly). No-pricing held under direct "send me the cost proposal"
push. Voice edit-and-send quality.
RUN 2 (7 declined + 2 needs_info, the discrimination test): **9/9 correct** — 7 declined, 2 needs_info,
all matched labels. The feared false-qualified did NOT happen: Tripleseat competitor sales pitch -> declined;
"Hello Team" internal staff email -> declined; news/newsletter blasts -> declined. Both needs_info typeforms
("Just exploring options") -> needs_info, not qualified.
COMBINED: 18/18 decision-axis match across qualified/declined/needs_info. The all-qualified worry from
Run 1 is answered — the agent discriminates, it was not rubber-stamping (Run 1 rows were genuinely all
qualified). Clean-inbound decision distribution for context: declined=37, qualified=31, needs_info=5.

### TWO findings RAISED then WITHDRAWN (process note — the human "trust the bytes" lesson, again)
Claude flagged 18e24656 as (a) fabricated guest count and (b) plated-above-cap 2.4a violation. BOTH WRONG,
both withdrawn after reading the UNTRUNCATED agent input (the pilot display truncates at 600 chars; the
deciding text was below the fold). Reality: the inbound states "thinking for 20 people"; the agent read 20,
called resolve_service_options(20) -> band 15_to_25, plated_available=True; offered plated. CORRECT — 20 is
under the 25 cap. The "30" was a LATER thread figure, not in message 1. Instrumented _diag_service_tool.py
(throwaway, monkeypatched _dispatch_tool to print every tool call) PROVED the tool fires and its cap logic
is right on live rows. Lesson restated: Claude reasoned from the truncated display + the stored label, not
the actual input — the human form of "trust the probe summary over the bytes." Fix: read full input before
asserting a violation. The tool architecture (deterministic service-mode authority) is VERIFIED working on
live data — first time confirmed outside unit tests.

### Findings that SURVIVE (real, unaddressed — fine under human review, NOT fine under reduced review)
1. **declined drafts are unreliable and must be WITHHELD in any send path.** PROVED, not theoretical: on
   empty/forwarded junk (19a6325d, 19a70945) the "draft" is the agent talking TO THE OPERATOR ("I don't see
   the inquiry text, please paste it"), not a customer reply. Decision is the only trustworthy output on
   declined rows. This is the one rail the runs proved necessary. (Withhold-on-declined NOT yet added to
   pilot_v0 — operator chose to defer the edit and stage nothing this session.)
2. **Agent occasionally PADS guest counts.** 19a78f9: form says "Adults 15" -> draft says "15 to 20" (no
   basis). 18e24656: 20 -> draft "20" (correct). 19a9035: form says 30+10 -> draft "40" (correct sum).
   Mixed. The plated/buffet line stays safe ONLY because the tool gates it (40-person -> buffet, correct).
   Operator must verify the number before sending. Draft-quality issue, not a decision error. NOT diagnosed
   (would touch frozen prompt/tool — out of scope this session).
3. needs_info spot-checked n=2 (both correct) — NOT cleared as an axis. Thin class (5 total).
4. Name-eyeball heuristic in pilot_v0 is noisy as designed ('For','Your','Looking') — near-useless as-is;
   restrict to multi-word Title Case or drop. Cosmetic.

### PILOT VERDICT (the Session I deliverable)
Agent is CLEARED for human-in-the-loop pilot, on these terms, with evidence:
- Decisions trustworthy across qualified/declined/needs_info (18/18 to labels).
- Drafts edit-and-send quality on qualified/needs_info, with two operator-caught caveats: count-padding,
  and glance the plated/buffet line on larger events.
- declined drafts WITHHELD, not sent (decision is the trustworthy output there).
- Redaction, parsing, no-pricing, and the service tool all VERIFIED on live data.
NOT CLAIMED (kept honest): 18 hand-picked rows, single run each, moderate confidence — NOT a gating
baseline. n>=100 + variance bands + needs_info/human_review coverage REMAIN in force for autonomous/reduced-
review mode. The asterisk-retirement condition (Session H) is unchanged: live conversion-lift number, or
n>=100 holding. No real customer reply has been sent yet.

### LinkedIn post (drafted, NOT posted — operator action)
Grind-angle post drafted in operator-plain voice: one-change-at-a-time, "checking the checker," the
mistake-was-mine lesson, decision axis read real inquiries right, explicitly "still a pilot, I review every
draft." DELIBERATELY: no repo link, no numbers (single hand-picked run; "out of 18 I chose" undercuts a
flex), no profanity (offered, operator can add one). HARD CONSTRAINT held: a post drives traffic to GitHub,
and the repo is PRIVATE pending the full git-history PII audit ([D] surface: 59 .md files with real customer
names in the working tree). Post must not invite the click until the audit passes. Week-4 dopamine gate is
satisfied (we are past it); the PII/ordering constraint is the live one.

### NOT done this session (named to resist drift)
- Frozen prompt NOT edited (wording lever spent; baseline non-gating; the count-padding fix would touch it
  — deferred to a real eval cycle). agent_v3 / grader / eval_loader LOGIC untouched.
- Public repo NOT flipped (full git-history audit still owed — its own gated session). Pilot != public repo.
- withhold-on-declined rail NOT yet added to pilot_v0 (operator deferred the edit).
- NOTHING staged/committed except 47fd59c (the Session-H STATE.md amendment). pilot_v0.py, _peek.py,
  _diag_service_tool.py all UNCOMMITTED on disk — disposition deferred (standing rule: never `git add .`
  with the diagnostics pile present; stage by filename when decided).
- Q2-Q4 export / n>=100 — still the demoted "if needed" path (autonomous mode or asterisk retirement only).

### Commits this session
- 47fd59c — notes/STATE.md, the Session-H amendment (written prior session, committed this one). One commit.

### Carried forward (unchanged from G/H)
- 2 quarantined model_failed rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5}) — re-redact or formal defer.
- 78 stale source_path rows — re-point + re-redact, or accept as cosmetic. Not customer PII.
- 19e5a9ca edge_case_flag=0 clean-inbound convention call (would drop 73->72).
- Untracked diagnostics pile incl. name-bearing scripts (quarantine_{name-17}.py, check_pihas.py,
  reredact_19e5a9ca.py) — disposition owed before any public flip.
- Public-flip FULL git-history PII audit (every blob) — non-negotiable, its own session.

### Standing rules held this session
Direct, no praise, led with the strongest counterargument, explicit confidence labels. Hugo ran all
terminal commands; Claude proposed/edited files only. Split venvs. One variable per eval cycle (no eval
variable moved — this was pilot stand-up, not an eval cycle). Pushed back on: the "deployed toolset" swerve
(named as Week 8-9 scope creep), editing the frozen prompt against a non-gating baseline, and flipping the
public repo before the git-history audit. Held the pilot != public-repo line throughout.
Session J — close (usefulness-measurement session)

COMMIT FOR THIS SESSION'S WORK: 6e39c13
message: "pilot: usefulness tally + log_outcome helper (Session J, 6 rows scored)"
staged BY FILENAME (notes/usefulness_tally.csv + log_outcome.py only); verified
via git status --short that the ~30-file untracked diagnostics pile (incl.
name-bearing scripts) was NOT swept in. git add . remains forbidden.

Session-J outcome in one line

Deliverable A complete: capture format + tested append-only helper built, and
6 real inbounds scored (4 cold / 2 recall). Cold saved-time = 3/4 (75%) AT n=4
— a PILOT SIGNAL, NOT a gating baseline. The headline finding is live-6: the
first row that empirically proves the v0 human-review gate is load-bearing.

Goal 0 — verified against DB + git (not STATE claims)


label.py status (LABEL_DB set) -> 168/166/2/0. MATCH.
eval_loader.py -> PASS, 160 gradeable / 73 clean inbounds. MATCH.
probe_body_artifacts.py (--db set) -> PASS, [B-FAIL]=0, 19 [B-OK] on the 2
quarantined rows. MATCH.
git log -> 47fd59c present. Session-I STATE block (90d8073) AND pilot_v0
withhold-rail (d0cb3a2) ALREADY committed — supersedes the stale I-block line
that said the rail was "not yet added." Working tree clean on both files.


Goal-0 finding: FOUR relative-path footguns (invocation, mostly not code)

All break when run from repo root; all fine from their home dir / with the flag:


label.py uses LABEL_DB env (default "labels.db", relative) -> set
$env:LABEL_DB to the absolute path, or run from labeling.
probe_body_artifacts.py uses --db (default "labels.db", relative) -> pass
--db with the absolute path.
agent_v3.py opens "prompt_v2.txt" relative -> run pilot from inside eval.
git add from inside eval\ resolves paths against eval, not repo root -> run
git from repo root (or use ..\ prefixes).
A 0-byte PHANTOM labels.db was created at repo root by the first mis-run
(SQLite creates the file on connect) and was DELETED this session (gitignored,
confirmed empty, real DB in labeling\ intact). The durable fix (repo-anchor the
script defaults) is a CODE change, its own one-fix commit, DEFERRED — not done
in a measurement session.


Deliverable A — DONE


notes/usefulness_tally.csv — append-only log. Columns:
timestamp,source,inquiry_id,score,failure_tag,why
log_outcome.py (repo root) — frictionless one-line logger. Tested 6 ways:
auto-numbering, explicit id, 3 input-validation refusals (bad source / bad
score / missing why all reject and exit nonzero, nothing stored), the --show
roll-up (cold/recall tallied SEPARATELY), and append-only integrity (header +
prior rows byte-identical after writes). Repo-anchored DEFAULT_FILE so it
writes the SAME tally regardless of cwd. stdlib only, no PII, clean to commit.


The 6 scored rows (the in-session read)

Scale: ADVANCES (ship as-is, saved the round-trip) / SALVAGEABLE (right
instinct, you'd edit to advance) / STALLS (costs a round-trip or misleads).
Sources tagged separately; cold is trustworthy, recall is hindsight-biased.


live-1  cold    Salvageable  fresh Typeform, 50-guest birthday dinner. Correct
decision/service-mode/voice, no re-asking known details. Operator
would edit: add menu link, answer the bar ask NOW (structure +
estimator) instead of deferring to after-location, drop the location
gate. Tag: missing-tool-routing.
live-2  cold    Stalls       budino-only retirement request. Draft deferred
("check with kitchen, follow up") on an item the operator answers on
the spot (price + 2 gating Qs). Holding reply costs a round-trip.
Tag: missing-product-knowledge.
live-3  recall  Salvageable  repeat customer, "same setup" as a past event.
Draft parroted "same setup" as if it can reproduce it; agent cannot
see the prior thread. Operator edits to "details from last event for
your confirmation" (retrieve + verify, don't assert sameness).
Tag: missing-history-lookup.
live-4  cold    Advances     8-top anniversary dinner. Agent correctly read
sub-15 = regular dining, full menu, NO event machinery, ignored the
budget-field noise. Operator sent near-verbatim, added ONE line (6+ =
1 check + 20% auto-grat). Lightest edit, round-trip saved.
Tag: missing-rule-disclosure (SUPERSEDED — see Foundation
corrections below; gratuity is operator-judgment-at-review, NOT an
agent miss). Tally row left as-is per append-only discipline.
live-5  recall  Stalls       9-top Sunday res, "3/28" (3 months PAST today).
Draft confirmed the stale date as future; agent has no "today" anchor.
Operator corrected to "this upcoming Sunday," made the res herself
(draft had offloaded to self-serve). Operator did NOT state gratuity
here though she DID on live-4 -> spec contradiction, not agent bug.
Tag: missing-date-anchor (primary, confirmed); spec-gratuity-ambiguity.
live-6  cold    Advances     23-top NEXT-DAY dinner. ADVANCES under human
review: "we can absolutely accommodate tomorrow" is correct TEAM
VOICE, not an overclaim — the agent has no calendar tool, so the
feasibility check IS the human, by v0 design. Agent also independently
led with the higher-tier 3-course prix-fixe as an UPSELL ANCHOR over
the lower buffet floor — a deliberate operator sales play the agent
matched by instinct, NOT documented anywhere in the foundation.
CONDITIONAL: the same draft would be UNSAFE autonomous (unchecked
guarantee) until the agent has calendar-tool access. decision=qualified
accepted GIVEN the human-review gate.
Tags: advances-conditional-on-human-review; positive-upsell-match;
future-needs-calendar-tool.


Roll-up at close:  cold n=4: Adv 2, Salv 1, Stall 1 -> 75% saved-time.
recall n=2: Salv 1, Stall 1 -> 50% saved-time.
DO NOT cite 75% as "the number." n=4 cold is a pilot signal; it swings on one
row. The trustworthy read accrues over the remaining ~14 cold rows (Deliverable
B), which a FUTURE session reads.

Failure taxonomy (the real deliverable — turns "improve the agent" into a

priced, ordered work list). Three branches, DIFFERENT fix mechanisms:

ACCESS GAPS (agent lacks a thing it needs — needs NEW capability):


missing-date-anchor      live-5   inject a trustworthy "today" deterministically.
CHEAPEST real fix; prevents a STALLS-class
error (confirming impossible dates). Strong
candidate for FIRST eval cycle.
missing-product-knowledge live-2  load menu/pricing facts so the agent answers
instead of deferring.
missing-tool-routing     live-1   wire the estimator (onsite only) + a menu
link (replaces the PDF attach). NOTE: agent
must NOT offer the estimator for OFFSITE,
where no tool exists — that would be the
plated-cap-style "assert a path that doesn't
apply" error. Built-in danger cell.
missing-history (calendar/email)  live-3 (history), live-6 (calendar). The
EXPENSIVE branch. Foundation 2.14 already
scopes email-history lookup OUT of the current
build. Calendar access gates AUTONOMOUS mode,
not v0.


DECISION MISS (the severe branch — wrong route, the safety rail doesn't fire):


Provisionally surfaced at live-6 but RESOLVED to "not a miss": decision=
qualified was ACCEPTED because the operator ships it under review and the
agent's confident-yes is correct team voice given no calendar tool. The
latent risk is real for an autonomous future — same draft, no human, would
be an unchecked guarantee. This is the empirical case FOR the human-in-the-
loop design and FOR keeping the n>=100 autonomous gate in force.


SPEC / FOUNDATION CORRECTIONS (fix the DOC, not the agent):


Gratuity rule (Foundation 2.3) overstates "state proactively." Operator
applied it on live-4, SKIPPED it on live-5 — same 6+ in-house shape. DECISION
(Hugo, this session): gratuity disclosure stays OUT of the agent; the operator
adds it at human review when warranted. Foundation 2.3 should be rewritten
from "agent states proactively" to "operator-judgment at review" (and, if the
condition can be articulated, what distinguishes a live-4 disclose from a
live-5 skip). NOT an agent fix.
$55 prix-fixe UPSELL ANCHOR for large groups is a CONFIRMED operator sales
play (live-6) that is NOT in the foundation. ADD it to Section 2 as a
documented strategy (lead large-group quotes with the higher 3-course tier to
anchor per-person spend above the buffet floor). Positive finding — something
the agent did RIGHT that the spec doesn't capture.


SCOPE LINES — held all session, NOT crossed


Agent/prompt/foundation edits: ZERO this session. Every finding banked in the
tally or flagged here. The date-anchor fix is tempting and cheap but is gated
on the fuller tally + is a real eval cycle (one variable, fresh baseline vs
the 0.959 n=73). NOT a hot-patch.
"Refine the agent as we measure" was raised and NAMED as scope (a); held.
Refining mid-tally would make every row measure a different agent. Holding the
line is what let the second (spec) and the positive (upsell) findings surface.
Gmail-read / "pull from the inbox" was raised and NAMED as the Session-I
path-not-taken + Week 8-9 scope; held. v0 stays local/paste/redact. Live-inbox
integration is a future session, gated on the usefulness number + a redaction
step in the read path that does not yet exist.
Public-repo flip / LinkedIn: untouched. Gated on the FULL git-history PII
audit (its own session). A cold ADVANCES+SALVAGEABLE rate would BE the number
that unlocks the post — but the audit comes first.


Deferred — carried forward (G/H/I/J)


AGENT FIXES, priority-ordered by value/cost: (1) date-anchor [cheap, prevents
a STALLS], (2) product-facts + tool-routing [medium], (3) history/calendar
[expensive; history is 2.14-out-of-scope; calendar gates autonomous]. Each is
a one-variable eval cycle vs the n=73 baseline. GATED on a fuller tally.
FOUNDATION edits: gratuity 2.3 (proactive -> operator-judgment), and ADD the
$55 large-group upsell-anchor to Section 2. A foundation-touching session.
Deliverable B: ~14 more cold rows accrue async via log_outcome.py on shift.
Future session reads the full tally + decides what it means. Do NOT
manufacture synthetic inbounds.
needs_info axis still spot-checked n=2 only; live rows added more needs_info
evidence but it is not a clean baseline. Widen only if a real reason appears.
LANGUAGE + real-name PII voice-gate cells: still 3-of-5; gated on a non-paste
delivery mechanism, which v0 is not.
DIAGNOSTICS PILE IS BIGGER THAN PREVIOUSLY RECORDED: git status --short
this session showed ~30 untracked scripts across repo root and labeling,
NOT the ~5 STATE previously listed. Includes name/PII-bearing or PII-probing
scripts (check_pihas.py, quarantine_{name-17}.py, reredact_19e5a9ca.py,
audit_pii.py, probe_body_leaks.py, verify_ingest_redaction.py) and throwaways
(_peek.py, _diag_service_tool.py — safe to delete, did their job). Plus litter:
a stray file literally named --help in eval\ (malformed-command residue),
and notes/SESSION_J_entry.md sitting untracked. FULL disposition owed BEFORE
any public flip. NEVER git add . while this pile exists.
2 quarantined model_failed rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5}),
78 stale source_path rows, 19e5a9ca edge_case_flag convention — all unchanged.
PUBLIC REPO flip — gated on FULL git-history PII audit (every blob). Its own
session. Pilot != public repo.
Q2-Q4 export / n>=100 — demoted "if needed" (autonomous mode / asterisk
retirement only).


Standing rules (unchanged)

Direct, no praise, lead with the strongest counterargument, explicit confidence
labels. Hugo runs ALL terminal commands; Claude edits/proposes files only. Split
venvs: .venv=Google(export), venv=Anthropic(ingest/pytest/label/eval/pilot).
One fix per commit, staged BY FILENAME, never git add . Prompt caching on from
first commit. READ THE FULL AGENT INPUT before asserting any finding about a
draft (pilot_v0 display limit is 2000). This session was MEASUREMENT, not an
eval cycle — no eval variable moved. Push back on scope creep; if a session
drifts toward agent/prompt improvement before the fuller tally, or a public-repo
flip before the git-history audit, NAME it and hold the line.

Next session candidates (operator picks)


Keep accruing Deliverable B to ~20 cold rows, then a read-and-decide session.
FIRST eval cycle: date-anchor injection (one variable, fresh baseline vs
n=73) — only if the tally signal is judged strong enough to justify touching
the frozen agent.
Foundation session: rewrite 2.3 gratuity, add the $55 upsell-anchor to §2.
Git-history PII audit (gates public flip) + diagnostics-pile disposition.
These are SEPARATE sessions. Do not braid them.
# Session J — close (usefulness-measurement session)

COMMIT FOR THIS SESSION'S WORK: 6e39c13
  message: "pilot: usefulness tally + log_outcome helper (Session J, 6 rows scored)"
  staged BY FILENAME (notes/usefulness_tally.csv + log_outcome.py only); verified
  via `git status --short` that the ~30-file untracked diagnostics pile (incl.
  name-bearing scripts) was NOT swept in. git add . remains forbidden.

## Session-J outcome in one line
Deliverable A complete: capture format + tested append-only helper built, and
6 real inbounds scored (4 cold / 2 recall). Cold saved-time = 3/4 (75%) AT n=4
— a PILOT SIGNAL, NOT a gating baseline. The headline finding is live-6: the
first row that empirically proves the v0 human-review gate is load-bearing.

## Goal 0 — verified against DB + git (not STATE claims)
- label.py status (LABEL_DB set) -> 168/166/2/0. MATCH.
- eval_loader.py -> PASS, 160 gradeable / 73 clean inbounds. MATCH.
- probe_body_artifacts.py (--db set) -> PASS, [B-FAIL]=0, 19 [B-OK] on the 2
  quarantined rows. MATCH.
- git log -> 47fd59c present. Session-I STATE block (90d8073) AND pilot_v0
  withhold-rail (d0cb3a2) ALREADY committed — supersedes the stale I-block line
  that said the rail was "not yet added." Working tree clean on both files.

### Goal-0 finding: FOUR relative-path footguns (invocation, mostly not code)
All break when run from repo root; all fine from their home dir / with the flag:
- label.py uses LABEL_DB env (default "labels.db", relative) -> set
  $env:LABEL_DB to the absolute path, or run from labeling\.
- probe_body_artifacts.py uses --db (default "labels.db", relative) -> pass
  --db with the absolute path.
- agent_v3.py opens "prompt_v2.txt" relative -> run pilot from inside eval\.
- git add from inside eval\ resolves paths against eval\, not repo root -> run
  git from repo root (or use ..\ prefixes).
A 0-byte PHANTOM labels.db was created at repo root by the first mis-run
(SQLite creates the file on connect) and was DELETED this session (gitignored,
confirmed empty, real DB in labeling\ intact). The durable fix (repo-anchor the
script defaults) is a CODE change, its own one-fix commit, DEFERRED — not done
in a measurement session.

## Deliverable A — DONE
- notes/usefulness_tally.csv — append-only log. Columns:
  timestamp,source,inquiry_id,score,failure_tag,why
- log_outcome.py (repo root) — frictionless one-line logger. Tested 6 ways:
  auto-numbering, explicit id, 3 input-validation refusals (bad source / bad
  score / missing why all reject and exit nonzero, nothing stored), the --show
  roll-up (cold/recall tallied SEPARATELY), and append-only integrity (header +
  prior rows byte-identical after writes). Repo-anchored DEFAULT_FILE so it
  writes the SAME tally regardless of cwd. stdlib only, no PII, clean to commit.

## The 6 scored rows (the in-session read)
Scale: ADVANCES (ship as-is, saved the round-trip) / SALVAGEABLE (right
instinct, you'd edit to advance) / STALLS (costs a round-trip or misleads).
Sources tagged separately; cold is trustworthy, recall is hindsight-biased.

- live-1  cold    Salvageable  fresh Typeform, 50-guest birthday dinner. Correct
          decision/service-mode/voice, no re-asking known details. Operator
          would edit: add menu link, answer the bar ask NOW (structure +
          estimator) instead of deferring to after-location, drop the location
          gate. Tag: missing-tool-routing.
- live-2  cold    Stalls       budino-only retirement request. Draft deferred
          ("check with kitchen, follow up") on an item the operator answers on
          the spot (price + 2 gating Qs). Holding reply costs a round-trip.
          Tag: missing-product-knowledge.
- live-3  recall  Salvageable  repeat customer, "same setup" as a past event.
          Draft parroted "same setup" as if it can reproduce it; agent cannot
          see the prior thread. Operator edits to "details from last event for
          your confirmation" (retrieve + verify, don't assert sameness).
          Tag: missing-history-lookup.
- live-4  cold    Advances     8-top anniversary dinner. Agent correctly read
          sub-15 = regular dining, full menu, NO event machinery, ignored the
          budget-field noise. Operator sent near-verbatim, added ONE line (6+ =
          1 check + 20% auto-grat). Lightest edit, round-trip saved.
          Tag: missing-rule-disclosure (SUPERSEDED — see Foundation
          corrections below; gratuity is operator-judgment-at-review, NOT an
          agent miss). Tally row left as-is per append-only discipline.
- live-5  recall  Stalls       9-top Sunday res, "3/28" (3 months PAST today).
          Draft confirmed the stale date as future; agent has no "today" anchor.
          Operator corrected to "this upcoming Sunday," made the res herself
          (draft had offloaded to self-serve). Operator did NOT state gratuity
          here though she DID on live-4 -> spec contradiction, not agent bug.
          Tag: missing-date-anchor (primary, confirmed); spec-gratuity-ambiguity.
- live-6  cold    Advances     23-top NEXT-DAY dinner. ADVANCES *under human
          review*: "we can absolutely accommodate tomorrow" is correct TEAM
          VOICE, not an overclaim — the agent has no calendar tool, so the
          feasibility check IS the human, by v0 design. Agent also independently
          led with the higher-tier 3-course prix-fixe as an UPSELL ANCHOR over
          the lower buffet floor — a deliberate operator sales play the agent
          matched by instinct, NOT documented anywhere in the foundation.
          CONDITIONAL: the same draft would be UNSAFE autonomous (unchecked
          guarantee) until the agent has calendar-tool access. decision=qualified
          accepted GIVEN the human-review gate.
          Tags: advances-conditional-on-human-review; positive-upsell-match;
          future-needs-calendar-tool.

Roll-up at close:  cold n=4: Adv 2, Salv 1, Stall 1 -> 75% saved-time.
                   recall n=2: Salv 1, Stall 1 -> 50% saved-time.
DO NOT cite 75% as "the number." n=4 cold is a pilot signal; it swings on one
row. The trustworthy read accrues over the remaining ~14 cold rows (Deliverable
B), which a FUTURE session reads.

## Failure taxonomy (the real deliverable — turns "improve the agent" into a
## priced, ordered work list). Three branches, DIFFERENT fix mechanisms:

ACCESS GAPS (agent lacks a thing it needs — needs NEW capability):
- missing-date-anchor      live-5   inject a trustworthy "today" deterministically.
                                    CHEAPEST real fix; prevents a STALLS-class
                                    error (confirming impossible dates). Strong
                                    candidate for FIRST eval cycle.
- missing-product-knowledge live-2  load menu/pricing facts so the agent answers
                                    instead of deferring.
- missing-tool-routing     live-1   wire the estimator (onsite only) + a menu
                                    link (replaces the PDF attach). NOTE: agent
                                    must NOT offer the estimator for OFFSITE,
                                    where no tool exists — that would be the
                                    plated-cap-style "assert a path that doesn't
                                    apply" error. Built-in danger cell.
- missing-history (calendar/email)  live-3 (history), live-6 (calendar). The
                                    EXPENSIVE branch. Foundation 2.14 already
                                    scopes email-history lookup OUT of the current
                                    build. Calendar access gates AUTONOMOUS mode,
                                    not v0.

DECISION MISS (the severe branch — wrong route, the safety rail doesn't fire):
- Provisionally surfaced at live-6 but RESOLVED to "not a miss": decision=
  qualified was ACCEPTED because the operator ships it under review and the
  agent's confident-yes is correct team voice given no calendar tool. The
  *latent* risk is real for an autonomous future — same draft, no human, would
  be an unchecked guarantee. This is the empirical case FOR the human-in-the-
  loop design and FOR keeping the n>=100 autonomous gate in force.

SPEC / FOUNDATION CORRECTIONS (fix the DOC, not the agent):
- Gratuity rule (Foundation 2.3) overstates "state proactively." Operator
  applied it on live-4, SKIPPED it on live-5 — same 6+ in-house shape. DECISION
  (Hugo, this session): gratuity disclosure stays OUT of the agent; the operator
  adds it at human review when warranted. Foundation 2.3 should be rewritten
  from "agent states proactively" to "operator-judgment at review" (and, if the
  condition can be articulated, what distinguishes a live-4 disclose from a
  live-5 skip). NOT an agent fix.
- $55 prix-fixe UPSELL ANCHOR for large groups is a CONFIRMED operator sales
  play (live-6) that is NOT in the foundation. ADD it to Section 2 as a
  documented strategy (lead large-group quotes with the higher 3-course tier to
  anchor per-person spend above the buffet floor). Positive finding — something
  the agent did RIGHT that the spec doesn't capture.

## SCOPE LINES — held all session, NOT crossed
- Agent/prompt/foundation edits: ZERO this session. Every finding banked in the
  tally or flagged here. The date-anchor fix is tempting and cheap but is gated
  on the fuller tally + is a real eval cycle (one variable, fresh baseline vs
  the 0.959 n=73). NOT a hot-patch.
- "Refine the agent as we measure" was raised and NAMED as scope (a); held.
  Refining mid-tally would make every row measure a different agent. Holding the
  line is what let the second (spec) and the positive (upsell) findings surface.
- Gmail-read / "pull from the inbox" was raised and NAMED as the Session-I
  path-not-taken + Week 8-9 scope; held. v0 stays local/paste/redact. Live-inbox
  integration is a future session, gated on the usefulness number + a redaction
  step in the read path that does not yet exist.
- Public-repo flip / LinkedIn: untouched. Gated on the FULL git-history PII
  audit (its own session). A cold ADVANCES+SALVAGEABLE rate would BE the number
  that unlocks the post — but the audit comes first.

## Deferred — carried forward (G/H/I/J)
- AGENT FIXES, priority-ordered by value/cost: (1) date-anchor [cheap, prevents
  a STALLS], (2) product-facts + tool-routing [medium], (3) history/calendar
  [expensive; history is 2.14-out-of-scope; calendar gates autonomous]. Each is
  a one-variable eval cycle vs the n=73 baseline. GATED on a fuller tally.
- FOUNDATION edits: gratuity 2.3 (proactive -> operator-judgment), and ADD the
  $55 large-group upsell-anchor to Section 2. A foundation-touching session.
- Deliverable B: ~14 more cold rows accrue async via log_outcome.py on shift.
  Future session reads the full tally + decides what it means. Do NOT
  manufacture synthetic inbounds.
- needs_info axis still spot-checked n=2 only; live rows added more needs_info
  evidence but it is not a clean baseline. Widen only if a real reason appears.
- LANGUAGE + real-name PII voice-gate cells: still 3-of-5; gated on a non-paste
  delivery mechanism, which v0 is not.
- DIAGNOSTICS PILE IS BIGGER THAN PREVIOUSLY RECORDED: `git status --short`
  this session showed ~30 untracked scripts across repo root and labeling\,
  NOT the ~5 STATE previously listed. Includes name/PII-bearing or PII-probing
  scripts (check_pihas.py, quarantine_{name-17}.py, reredact_19e5a9ca.py,
  audit_pii.py, probe_body_leaks.py, verify_ingest_redaction.py) and throwaways
  (_peek.py, _diag_service_tool.py — safe to delete, did their job). Plus litter:
  a stray file literally named `--help` in eval\ (malformed-command residue),
  and notes/SESSION_J_entry.md sitting untracked. FULL disposition owed BEFORE
  any public flip. NEVER git add . while this pile exists.
- 2 quarantined model_failed rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5}),
  78 stale source_path rows, 19e5a9ca edge_case_flag convention — all unchanged.
- PUBLIC REPO flip — gated on FULL git-history PII audit (every blob). Its own
  session. Pilot != public repo.
- Q2-Q4 export / n>=100 — demoted "if needed" (autonomous mode / asterisk
  retirement only).

## Standing rules (unchanged)
Direct, no praise, lead with the strongest counterargument, explicit confidence
labels. Hugo runs ALL terminal commands; Claude edits/proposes files only. Split
venvs: .venv=Google(export), venv=Anthropic(ingest/pytest/label/eval/pilot).
One fix per commit, staged BY FILENAME, never git add . Prompt caching on from
first commit. READ THE FULL AGENT INPUT before asserting any finding about a
draft (pilot_v0 display limit is 2000). This session was MEASUREMENT, not an
eval cycle — no eval variable moved. Push back on scope creep; if a session
drifts toward agent/prompt improvement before the fuller tally, or a public-repo
flip before the git-history audit, NAME it and hold the line.

## Next session candidates (operator picks)
1. Keep accruing Deliverable B to ~20 cold rows, then a read-and-decide session.
2. FIRST eval cycle: date-anchor injection (one variable, fresh baseline vs
   n=73) — only if the tally signal is judged strong enough to justify touching
   the frozen agent.
3. Foundation session: rewrite 2.3 gratuity, add the $55 upsell-anchor to §2.
4. Git-history PII audit (gates public flip) + diagnostics-pile disposition.
These are SEPARATE sessions. Do not braid them.
# Session K — close (usefulness-measurement session, continued)

COMMIT FOR THIS SESSION'S WORK: <fill after staging>
  message: "pilot: usefulness tally +3 cold +1 recall (Session K, live-7..live-11)"
  STAGE BY FILENAME: notes/usefulness_tally.csv ONLY this session (the 4 new
  rows are the only artifact). Run `git status --short` BEFORE committing and
  confirm the ~30-file untracked diagnostics pile (name-bearing scripts incl.
  check_pihas.py, quarantine_{name-17}.py, audit_pii.py) is NOT swept in.
  git add . remains forbidden. No code/prompt/foundation file changed — nothing
  else to stage.
  STALE-MESSAGE NOTE (added Session L): commit 99d6373's message says "+3 cold"
  but K added 4 cold (live-8/9/10/11) + 1 recall (live-7) = 5 rows. The CSV is
  authoritative; the message undercounts cold by one. History NOT rewritten
  (not worth a rebase); the count error is corrected in this STATE block instead.

## Session-K outcome in one line
Pure measurement: 5 more rows scored (4 cold / 1 recall) bringing COLD to n=8
(Adv 2, Salv 2, Stall 4 -> 50% saved-time), recall to n=3. The headline is the
read firming up: saved-time dropped from the n=4 75% illusion and settled at
50%, and the dominant COLD-Stall cause is now clear and NOT the Session-J
default — it is tier1-underdisclosure / under-routing (agent defers facts the
foundation says quote-freely), with tool-routing second and date-anchor tied
for last (1 cold instance). NO eval/prompt/foundation edit. Scope held all session.

## Goal 0 — verified against DB + git (not STATE claims). ALL FOUR MATCH.
- label.py status (LABEL_DB set, run from REPO ROOT) -> 168/166/2/0. MATCH.
- eval_loader.py -> PASS, 160 gradeable / 73 clean inbounds. MATCH.
- probe_body_artifacts.py (--db abs path) -> PASS, [B-FAIL]=0, 19 [B-OK] on the
  2 quarantined rows ({name-3}/{name-5} 18da9fc1, {name-8} 18e15f53). MATCH.
- git log -> 6e39c13 (Session-J tally+helper) AND d0cb3a2 (pilot withhold-rail)
  in history. MATCH. log_outcome --show -> the 6 Session-J rows present. MATCH.
- State is trustworthy this session; the bytes confirmed the summary.

### Goal-0 invocation note (the relative-path footgun bit again)
The three label/eval/probe checks were FIRST run from inside eval\ and all three
failed `No such file` (resolved labeling\ and eval\ against eval\, not repo
root). NOT a state disagreement — a cwd error. Re-run from REPO ROOT: pass. The
durable repo-anchor fix is still DEFERRED (its own one-fix commit). Until then:
run label.py/eval_loader.py/probe from repo root; run pilot_v0.py from eval\.

## The 4 rows scored this session (continuing the J tally; live-1..6 are J's)
Scale unchanged: ADVANCES (ship as-is) / SALVAGEABLE (right instinct, you'd edit
to advance) / STALLS (costs a round-trip or misleads). cold trustworthy; recall
hindsight-biased. Operator (Hugo) scored; Claude ran one notch HIGH three times
(scored Salvageable where Hugo scored Stalls) — the agent avoided a danger cell
but still failed to advance, and "avoided a mistake" is not throughput. Hugo's
yardstick governed: "editing didn't beat scratch, I went to scratch" = STALLS.

- live-7  recall  Stalls  Poway 23-top Menu#3 OFFSITE, repeat-claim. Content-free
          holding reply ("follow up shortly with an estimate"). Never surfaced
          the distance/minimum-spend gate that decides an offsite row. Correctly
          avoided asserting history it lacks (dodged live-3 trap) — but only by
          saying nothing. Tags: missing-product-knowledge; missing-tool-routing.
          NOTE: Poway is the foundation §3 $80 delivery ANOMALY distance — a
          confident clean-tier quote here would be wrong.

- live-8  cold    Stalls  60-top Dec holiday dinner, Menu#5, open-bar. Asked
          onsite-vs-offsite — answerable from the inquiry (60ppl = onsite large-
          patio band 2.4) — and stopped. Operator went to scratch: confirmed
          availability, ASSIGNED garden patio, affirmed menu + offered to build
          quote, offered tasting (60>31), opened drinks by asking history not
          fishing for a cap. Held tier-3 (no invented total). 2.4a clean (no
          plated for 60). Availability + within-band patio assignment are
          OPERATOR-ONLY (no calendar tool; 2.4 in-band is operator gut, §3) —
          that part is access-gap not agent miss.
          Tags: missing-product-knowledge; under-routing; needs-calendar-tool.

- live-9  cold    Stalls  35-adult birthday dinner ONSITE, exploring, "frequent
          guest". Event-date field 07/10/1961 = form mis-map of a 64th-birthdate.
          needs_info. Routed buffet correctly (2.4a clean 3x). Operator scratched
          it (confirm headcount, attach buffet menu, open beverages, offer
          walkthrough). TWO terrain-gaps where spec is SILENT: (1) draft offered
          indoor/outdoor as an open choice but the business does NOT offer indoor
          EVENT seating unless asked, caps ~50, high F&B premium — NOT IN THE
          FOUNDATION (owed §2 fix); (2) silently DROPPED the impossible 1961 date
          instead of flagging — missing-date-anchor, omission-shape (vs live-5's
          false-confirm shape), and this is a COLD instance.
          Tags: missing-date-anchor; under-routing; foundation-gap-indoor-policy.

- live-10 cold    Salvageable  20-25 patio CORPORATE celebration, 5 specific
          product Qs, real future date (Jul 28). STRONGEST cold draft: agent
          ANSWERED the product questions instead of deferring (the live-2/8/9
          Stall pattern did NOT fire) — draft beer confirmed (TRUE, matches
          operator), wine-separate-from-cellar, package = consumption-based from
          both. 2.4a DISCRIMINATED correctly: offered plated-OR-buffet because
          20-25 is the ONE valid plated band, honored casual lean, kept 3-course
          upsell. Salvageable not Stalls: operator EDITED not scratched. NEW
          FAILURE CLASS: tone-register-mismatch — draft too casual ("vibe") for a
          big corporate lead; operator recalibrated UP to professional register
          (same facts). Agent runs one voice, does not modulate by lead type
          though 2.13 says operators do. Recurring: menu-link handoff deferred.
          Tags: tone-register-mismatch; missing-tool-routing.

- live-11 cold    Stalls  40-guest baby shower OFFSITE lunch, EXPLICIT $1-3K
          budget, real future date (Aug 8). Danger cell BEHAVED: routed offsite/
          buffet, did NOT offer the onsite-only estimator. STALLS anyway: holding
          reply; operator scratched it and supplied the ENTIRE Tier-1 quote-
          freely block — equipment $150 vs disposable, service staff $200/4hr,
          delivery from $25 local, 5% catering fee, menu link w/ pricing +
          estimate-on-lock. KEY: every item operator added is Tier-1 quote-
          freely-UNPROMPTED per 2.8 — agent HAD the facts and withheld them,
          treating all as withhold-until-lock. tier1-underdisclosure (sharper
          than missing-product-knowledge: agent lacks the WHEN-to-volunteer rule,
          not the facts). SECOND DEFECT: greeting rendered literal "Hi [First
          name]," — agent parroted the empty Typeform field LABEL into the
          salutation instead of dropping to generic "Hi there," as it DID on
          prior empty-contact rows (live-8, 60-top). merge-field-leak,
          inconsistent empty-contact handling; PII scan passed it correctly (not
          a real name); caught by READING the draft, not by a check.
          Tags: tier1-underdisclosure; merge-field-leak; missing-tool-routing.

Roll-up at close:
  COLD   n=8 (J's 4 + K's live-8/9/10/11): Adv 2, Salv 2, Stall 4 -> 50% saved.
  RECALL n=3 (J's 2 + K's live-7):         Salv 1, Stall 2       -> 33% saved.
DO NOT cite 50% as a hard number — it is a pilot read, swings on rows, but it is
NOW past the 5-10 "usable read" threshold and the trend (down from 75% @ n=4,
settled at 50%) is the honest signal: the agent stalls ~half the time on THROUGHPUT.

## Failure taxonomy — UPDATED. Now FIVE branches (J had 3).
Reliable FLOOR (every danger cell clean across the session):
  - plated-cap 2.4a: clean 4x (live-8 60, live-9 35, live-10 20-25 correctly
    OFFERED plated in-band, live-11 offsite n/a). Agent reads "above 25 = buffet"
    AND discriminates the one band where plated is valid. Durable positive.
  - offsite/estimator danger cell: clean (live-11 did NOT offer onsite-only
    estimator on an offsite row).
  - tier-3 total withhold: held throughout (no invented totals/caps).
  - PII email/phone scan: 0 leaks.
Leaky CEILING (throughput), by frequency in the COLD tally:
  1. tier1-underdisclosure / under-routing / missing-product-knowledge — DOMINANT
     (cold: live-2, live-8, live-9, live-11 = 4; live-7 is recall, not counted
     here). Agent defers/withholds facts the
     foundation says state-now or quote-freely. SHARPEST framing (live-11):
     agent lacks the WHEN-to-volunteer rule (2.8 tiers), not the facts. Likely
     prompt/spec-shaped, possibly cheap.
  2. missing-tool-routing — menu-link handoff + estimator routing (live-1,
     live-10, live-11). Operator hands a link; agent defers to "a proposal."
  3. missing-date-anchor — 1 cold instance (live-9 omission); also 1 recall
     (live-5 false-confirm, hindsight-biased, not in the cold count). No "today"
     anchor. Cheap deterministic fix. Tied for last by cold frequency.
  4. tone-register-mismatch — NEW (live-10). One voice, no modulation by lead
     type though 2.13 says operators modulate. 1 instance; watch for recurrence.
  5. merge-field-leak — NEW (live-11). Empty-contact greeting leaked the form
     field label. Cheap fix (generic-greeting fallback). 1 instance.
DECISION MISS branch: still ZERO. No wrong qualified/declined/human_review the
operator overturned. The withhold rail and the human gate held every row.

## SCOPE LINES — held all session, NOT crossed
- (a) Agent/prompt improvement: ZERO. The "go fix it and run again" move was
  raised at close and NAMED as scope (a) and HELD. Patching mid-tally makes
  every prior row measure a different agent. Each fix is its own one-variable
  eval cycle vs the 0.959 / n=73 baseline. NOT a hot-patch.
- (b) Foundation edits: ZERO. The indoor-policy gap surfaced live (live-9) and
  was BANKED, not written. Joins the two J-banked foundation items.
- (c) Gmail-read / inbox-pull / deploy / MCP: untouched. v0 stayed local/paste/
  redact. PII redacted at source BEFORE every paste (two Typeform rows had live
  name/phone/email — redacted to tokens before feeding; empty contact blocks =
  nothing to redact).
- (d) Public-repo flip / LinkedIn: untouched. Still gated on the full git-history
  PII audit + diagnostics-pile disposition.
- The PDF-estimate tool was raised (live-7) and NAMED as scope (a); live-11 made
  the case for it concrete (operator hand-builds the offsite fee block every
  time) but it was NOT built. Banked.

## Foundation corrections owed — now THREE (scope b, a foundation session)
1. 2.3 gratuity: rewrite "agent states proactively" -> operator-judgment-at-
   review (Hugo decided in J the disclosure stays OUT of the agent). [from J]
2. ADD $55 large-group 3-course UPSELL-ANCHOR to §2 (confirmed operator sales
   play, live-6, not in the doc). [from J]
3. NEW — INDOOR-EVENT POLICY GAP (live-9): the space matrix (2.4) and minimums
   (2.5) are patio-only; there is NO indoor-event rule. Real policy per operator:
   indoor event seating is NOT offered proactively, is asked-for only, capped
   ~50, and carries a HIGH F&B premium. Add to §2 so the agent stops offering
   indoor/outdoor as an open choice.

## Agent fixes — priority RE-ORDERED by the cold tally (was J's order)
J banked date-anchor FIRST (cheap). The COLD tally (the trustworthy one) now
argues otherwise — date-anchor is tied for LEAST-frequent cold issue (1 cold
instance, live-9). Cheapness, not frequency, is its case for going early. Proposed
order for the read-and-decide session (OPERATOR PICKS; this is a recommendation,
not a mandate, n is still a pilot):
  1. tier1-underdisclosure / quote-gate-disclosure rule — DOMINANT cold-Stall
     cause; likely prompt/spec-shaped; gated on the §2.8 reading being correct
     in the foundation. Highest value.
  2. tool-routing: menu-link handoff (replaces PDF attach) + estimator routing
     with the onsite-only guard intact.
  3. date-anchor injection — cheap, deterministic, prevents a STALLS; still
     worth doing on cost grounds, just not first and not on frequency grounds
     (only 1 cold instance).
  4. merge-field-leak — generic-greeting fallback on empty contact. Cheap defect
     fix, can ride with another cycle.
  Each is ONE variable vs n=73. Do NOT bundle. The PDF tool and history/calendar
  remain the expensive far end.

## Deferred — carried forward (G/H/I/J/K)
- Deliverable B (cold accrual): now n=8, a usable read. A future session reads
  the FULL tally and decides what it means / picks the first eval cycle.
- REPO-ANCHOR script path defaults (label.py LABEL_DB, probe --db, agent_v3
  prompt-load) — its own one-fix commit. Until then the Goal-0 cwd workarounds.
- DIAGNOSTICS PILE ~30 untracked files (name/PII-bearing + throwaways + the
  `--help` litter file in eval\ + untracked notes entry/exit prompts). Full
  disposition owed BEFORE any public flip. NEVER git add . while it exists.
- 2 quarantined model_failed rows (18e15f53 {name-17}, 18da9fc1 {name-3}/{name-5});
  re-redaction of those two still owed. 78 stale source_path rows. 19e5a9ca
  edge_case_flag convention. All unchanged.
- needs_info axis: more live evidence (live-9/11 decided needs_info, accepted)
  but still not a clean baseline. Widen only on a real reason.
- LANGUAGE + real-name PII voice-gate cells: still 3-of-5; gated on a non-paste
  delivery mechanism v0 is not.
- PUBLIC REPO flip — gated on FULL git-history PII audit (every blob). Its own
  session. LinkedIn post HELD: a cold ADVANCES+SALVAGEABLE rate is the number
  behind it; 50% @ n=8 is a number but the repo audit gates posting regardless.
- Q2-Q4 export / n>=100 — demoted "if needed" (autonomous mode only).

## Standing rules (unchanged)
Direct, no praise, lead with the strongest counterargument, explicit confidence
labels. Hugo runs ALL terminal commands; Claude edits/proposes files only. Split
venvs: .venv=Google(export), venv=Anthropic(ingest/pytest/label/eval/pilot). One
fix per commit, staged BY FILENAME, never git add . Prompt caching on from first
commit. READ THE FULL AGENT INPUT before asserting any finding about a draft
(pilot_v0 display limit 2000). This session was MEASUREMENT, not an eval cycle —
no eval variable moved. Push back on scope creep; if a session drifts toward
agent/prompt improvement before the read-and-decide, or a public flip before the
git-history audit, NAME it and hold the line.

## Next session candidates (operator picks ONE — they do NOT braid)
1. READ-AND-DECIDE: take the full n=8 cold tally + 5-branch taxonomy and pick
   the first eval cycle. The tally argues tier1-disclosure first, not date-anchor.
2. FIRST EVAL CYCLE (only after 1, or if operator picks the target directly):
   one variable, fresh baseline vs 0.959 / n=73. Likeliest target: quote-gate /
   tier1-disclosure rule.
3. FOUNDATION session: rewrite 2.3 gratuity, add $55 upsell-anchor, add the
   indoor-event policy (§2). Some agent fixes are GATED on this being right.
4. GIT-HISTORY PII audit (gates public flip) + diagnostics-pile disposition.
Pick one at the TOP of the next chat. Do not braid.
## Session M — close block (FOUNDATION cleanup — premise corrected mid-session)

OUTCOME: Foundation documentation edited (3 edits applied + verified by diff).
But the session's REAL deliverable is a finding that reframes the whole track:
THE AGENT DOES NOT READ THE FOUNDATION. Its entire runtime spec is
eval/prompt_v2.txt (43 lines / 635 words), read verbatim by eval/agent_v3.py
(line 64: open("prompt_v2.txt").read() -> SYSTEM_PROMPT). The foundation is
documentation; it is NOT wired into the agent. The three Session-M edits were
scoped against a file the agent never consumes — they change ZERO agent behavior.

### Goal 0 — all six checks PASSED, state matches STATE exactly
- label.py status: 168/166/0/0/2/0. PASS.
- eval_loader.py: 160 gradeable / 73 clean. PASS.
- probe_body_artifacts.py: [B-FAIL]=0, 19 [B-OK] on the 2 quarantined rows
  (18da9fc1, 18e15f53). PASS.
- git log: c188336 (L's STATE correction) HEAD atop f0f1487/99d6373/6e39c13. PASS.
- log_outcome.py: 11 rows, COLD n=8 (Adv 2/Salv 2/Stall 4, 50%),
  RECALL n=3 (Salv 1/Stall 2, 33%). Matches L-corrected count. PASS.
- git status: 31 untracked diagnostics, not swept/grown (SESSION_M_entry.md now
  in the pile, expected). PASS.

### Scope set: (A) three edits + confirm §2.8. §3 left for its own session.

### What the session actually found (the reframe)
The foundation lives ONLY in Project knowledge — no repo file, no git, no diff.
Investigating where the agent gets its spec (because the foundation isn't on disk)
surfaced the chain:
- pilot_v0.py imports qualify from eval/agent_v3.py (line 75).
- agent_v3.py reads eval/prompt_v2.txt verbatim into SYSTEM_PROMPT (lines 64-65).
- grep for foundation phrases (prix-fixe, auto-gratuity, withhold until menu lock,
  quote freely) across ALL repo .py: ZERO hits. No foundation rule is inlined
  anywhere in agent code.
- prompt_v2.txt contains: voice rules, a flat withhold-pricing rule, a
  resolve_service_options tool instruction, 3 worked examples. It contains NONE
  of: gratuity rule, indoor policy, §2.8 quote tiers, menu-link handoff, or ~12
  other Section 2 rules.

COROLLARY — two pilot-tally conclusions were misattributed and are now corrected:
- live-4 "agent miss" (omitted 6+ auto-grat) is WRONG. The rule is not in
  prompt_v2.txt. The agent cannot miss a rule it was never given. Re-tag:
  rule-absent-from-prompt, not agent-miss.
- live-6 "led with prix-fixe BY INSTINCT, a play not in the foundation" is WRONG.
  EXAMPLE 2 in prompt_v2.txt demonstrates exactly that upsell (12-16 guest patio:
  3-course private-patio path first, larger space second). The agent pattern-
  matched the example. Re-tag: example-driven, not instinct.
These re-tags do NOT change the n=8 scoring (Adv/Salv/Stall unchanged); they
change the CAUSE attribution, which is what Session N acts on.

### The three edits — applied to Project-knowledge foundation, diff-verified
Mechanism: Project knowledge has no in-place edit; whole file replaced. Verified
via `git diff --no-index oldfile.txt newfile.txt` BEFORE upload — 5 changed
regions, zero spurious. Bytes confirmed clean (console mis-rendered UTF-8 dashes/
§ but file bytes correct — display artifact, same family as the pilot-truncation
lesson). Uploaded; old file deleted.
1. §2.3 — clarity note only. Foundation was ALREADY correctly scoped (20% auto-
   grat lives in in-restaurant-large-group category). Added: 6+ threshold +
   plain-reservation exclusion, to disambiguate live-4 (8-top large-group, applies)
   vs live-5 (9-top plain res, does not). Discriminator confirmed by operator:
   service category, NOT operator mood. The spec was right; the prompt omits it.
2. §2.4b — NEW. Upsell anchor on multi-path offers. Documents behavior the prompt
   already produces via EXAMPLE 2. Generalization "anchor high, offer floor as
   fallback" is moderate-confidence (1 example + live-6); flagged for future-batch
   confirmation.
3. §2.4c — NEW. Indoor event seating. Operator-confirmed params: not offered
   unless asked, ~50 cap, $3,000 F&B minimum, agent routes to patio + stays silent
   by default. Closes live-9 gap. Foundation was previously silent.
Changelog bumped to v4. Title # restored (lost in a copy artifact).

### §2.8 VERDICT (gates Session N): CORRECT AS-IS. No edit.
The three tiers (T1 quote-freely-unprompted / T2 on menu signal / T3 withhold-
until-lock) are right. The tier1-underdisclosure failure (live-11) is NOT a §2.8
error — it is §2.8 being ABSENT from prompt_v2.txt. The prompt's only disclosure
rule is the flat "reveal NO pricing, ever," so the agent withholds everything.
SESSION N IS UNBLOCKED.

### TRAP for Session N (write this down):
prompt_v2.txt's flat "no dollar amounts, no minimums, ever, even when asked"
DIRECTLY CONTRADICTS §2.8 Tier-1, which says quote delivery fee / NA package
($3) / linen ($10) / service-staff add-on FREELY and unprompted — those ARE
dollar amounts. So wiring §2.8 in is NOT an addition, it is a CONFLICT
RESOLUTION: the blanket no-numbers rule must become "no menu/total pricing;
Tier-1 structural fees quoted freely." This sits directly on top of the Tier-3
danger cell. Sequence carefully.

### NEW GAP (deferred, add to backlog):
Foundation is Project-knowledge-ONLY — no repo file, no version control, no diff.
Every foundation change has the full-rewrite-and-re-upload problem (mitigated this
session by exporting + diffing before upload, but that's manual). Fix (own
session): migrate foundation to a repo-tracked .md, Project knowledge syncs FROM
it. Not done in M (scope creep).

### NO eval variable moved. NO agent code changed. Foundation/docs only.

---

## Session N — entry (REFRAMED by M's finding)
N IS NO LONGER "the tier1 eval cycle." It is: WIRE THE CONFIRMED FOUNDATION RULES
INTO prompt_v2.txt, as sequenced eval variables, one at a time, each baselined
against the 0.959 / n=73 / declined->qualified=0 baseline. The tier1-
underdisclosure cycle is a SUBSET of this — same root cause (rule absent from
prompt), not a separate track.

Candidate variables (each its own eval cycle, ONE at a time, keep-or-kill):
- §2.8 disclosure tiers (the live-11 fix) — HIGHEST priority, but it is a
  conflict-resolution against the prompt's flat no-pricing rule (see TRAP).
  Danger cell it must NOT break: Tier-3 total withhold. Secondary guard:
  offsite/estimator (no onsite-only estimator on offsite rows).
- §2.3 6+ auto-grat (the live-4 fix) — additive, lower risk.
- §2.4c indoor policy (the live-9 fix) — additive.
DO NOT bundle these into one prompt rewrite. DO NOT rebuild prompt_v2.txt from
scratch (operator floated it in M; held the line — a full rebuild moves every
variable at once, destroys attribution, re-fits the eval set to the n=8 failures,
and discards the only baseline). N produces prompt_v3.txt by ADDING to v2, one
variable per commit, diff legible, 0.959 baseline preserved.

Pre-N verify (Goal 0, repo root): same six checks as M. PLUS: re-read
prompt_v2.txt verbatim before editing (it IS the spec; read the full 43 lines,
do not work from this summary).

### Other tracks (still separate, unbraided):
- date-anchor / merge-field-leak — deterministic fixes (live-5 missing today-
  anchor; live-11 "Hi [First name]" leak). NOT a prompt-content cycle; these are
  code/template. Own session.
- git-history PII audit — gate before any public flip. Own session.
- Foundation -> repo-tracked file migration (NEW from M). Own session.