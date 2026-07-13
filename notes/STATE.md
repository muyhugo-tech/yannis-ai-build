> **HASH INVALIDATION (Session T2, 2026-07-12).** The git history was
> rewritten with git filter-repo. EVERY commit hash recorded below this
> line is historical-reference-only and no longer resolves in this
> repository. Post-rewrite hashes begin at e3398c6. The pre-rewrite
> history survives only in the frozen local mirror (see T2 close block).

# STATE — Yanni's catering qualifier (code state of record)

Update this at the END of every build session. It records what is TRUE on
disk now, not what was decided in conversation. Next session: read this,
attach the files it names, then start. Do not rediscover.

Last updated: 2026-07-12 (end of Session T2 -- history rewritten, repo public).

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
Both QUARANTINED (set redaction_status=model_failed, quarantine_c1.py),
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
4. [D] file surface: ~59 threads*/ .md files contain real customer names (7 distinct; list held in labeling/audit_names_local.txt, gitignored).
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
- Untracked diagnostics pile incl. name-bearing scripts (quarantine_c1.py, check_pihas.py,
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
scripts (check_pihas.py, quarantine_c1.py, reredact_19e5a9ca.py,
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
  scripts (check_pihas.py, quarantine_c1.py, reredact_19e5a9ca.py,
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
  check_pihas.py, quarantine_c1.py, audit_pii.py) is NOT swept in.
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
## Session N — close block (FIRST WIRE-IN ATTEMPT: §2.3 — KILLED on danger-cell breach)

OUTCOME: §2.3 (6+ auto-gratuity) attempted as the first foundation-rule wire-in.
KILLED. Not a no-op — it moved the primary danger cell. The session's real
deliverable is a STRUCTURAL FINDING that reframes the entire N track: the agent's
draft prompt and its qualification classifier share context, so ANY draft-voice
prompt edit can move the decision. "Additive low-risk content variable" is not a
real category under the current agent_v3 architecture.

### Goal 0 — passed, state matched STATE (with one correction)
- label.py: 168/166/2/0. PASS.
- eval_loader: 160 gradeable / 73 clean. PASS.
- probe_body_artifacts: [B-FAIL]=0, 19 [B-OK] on the 2 quarantined rows. PASS.
- log_outcome: 11 rows, COLD n=8 (Adv2/Salv2/Stall4), RECALL n=3 (Salv1/Stall2). PASS.
- git status: ~33-file diagnostics pile, not swept. PASS.
- git log CORRECTION: entry prompt expected M's STATE commit atop c188336. It was
  NOT committed — M's STATE block was dirty in the working tree (J-pattern repeat,
  3rd occurrence). Committed this session as 7d81e71 BEFORE any prompt work.
  c188336 was HEAD; it is no longer.

### prompt caching / standing rules: honored. agent_v3 reads prompt_v2.txt (line 64).

### The variable: §2.3 wire-in (prompt_v3.txt = prompt_v2.txt + 1 BILLING STRUCTURE block)
- Diff: clean, +4 lines after SERVICE FORMAT, nothing else touched. Single variable.
- Block: state single-check + 20% auto-grat for in-restaurant group events of 6+,
  category-gated (NOT plain reservations), "when in doubt do not state it."
- Pointed agent_v3 at prompt_v3.txt (1-token swap line 64). Tested via pilot_v0
  --stdin (reconstructed live-4 / live-5 inquiry shapes, not the real DB rows —
  live-N → thread-id crosswalk not available; --stdin tests the rule on the shape).

### THE KILL — v2/v3 comparison on the live-5 shape (9-top plain Sunday reservation)
- v3: DECISION=declined. v2 (same inquiry, same qualify() path, prompt reverted):
  DECISION=qualified. The §2.3 block is the only changed variable. It flipped a
  real booking from qualified to declined.
- qualified→declined is the primary danger cell's other face: a thrown-away lead.
  pilot_v0's withhold logic then HIDES the draft — in a live pilot the booking
  vanishes silently. Hard kill. Keep-or-kill criterion ("danger cells hold")
  failed. No gratuity-wording fix is worth a prompt that drops leads.
- Mechanism (confirmed, high confidence): agent_v3._classify (stage 2) forces
  submit_qualification over the conversation AND PASSES THE FULL DRAFT SYSTEM_PROMPT.
  The block's "a plain table reservation is not a large-group event" language gave
  the classifier a new salient frame → read 9-top as mere reservation → declined.
  Draft-voice instruction leaked into the decision. This was flagged as a risk
  pre-run and underweighted ("almost certainly harmless"); the run disproved it.

### Secondary result (subordinate to the kill)
- §2.3 ALSO did not fire on the live-4 shape (in-restaurant 8-top "nothing fancy"
  anniversary): draft routed regular dining correctly but stated NO gratuity line.
  A-no. Cause: either over-timid boundary wording (the "when in doubt / nothing
  fancy" escape hatch triggered silence on a case that should fire) or example-
  absence — no EXAMPLE in prompt_v2.txt models a gratuity line, so the agent
  pattern-matches the 3 concrete examples over the 1 abstract rule. Same failure
  family as live-6 (concrete example beats abstract instruction) and EXAMPLE 3
  teaching deferral. Moderate confidence on example-absence as primary.

### THE STRUCTURAL FINDING (the real N reframe — write this down)
agent_v3._classify passes the full draft-authoring SYSTEM_PROMPT into the
qualification call. There is NO separation between draft-voice instruction and
decision context. Therefore EVERY foundation-rule wire-in (§2.3, §2.8a, indoor,
all ~12) enters classifier context and carries decision-contamination risk. The
N premise — "wire confirmed rules in as low-risk content variables" — is built on
a crack. No content variable is genuinely additive under this architecture.
COROLLARY: the 73-row grader set may not contain a 9-top-style row, so a full
grade_agent.py run might have MISSED this contamination. Eyeball-on-shape caught
what the grader might not. The grader set likely needs the 9-top case added before
it can guard this class of regression.

### Repo state at close
- prompt_v3.txt: DELETED (never staged; kill = delete untracked file). 
- agent_v3.py: confirmed reading prompt_v2.txt (findstr verified). Back to pre-
  session state. NO repo mutation from the killed variable.
- 7d81e71 (M STATE close + N entry) is the only commit this session. This N close
  block is the second.
- §2.3 wording is NOT locked/saved — it was a tested-and-killed candidate. If
  revisited, it must be re-derived against the decoupled architecture, not reused.

### NEXT SESSION — recommended top (decouple, then resume wire-in)
DECOUPLE _classify FROM THE DRAFT PROMPT. Give stage-2 classification its own
minimal prompt (intent definitions only — effectively the submit_qualification
schema's own descriptions), NOT the full draft-authoring SYSTEM_PROMPT. This cuts
the contamination channel and makes the N wire-in track actually low-risk. It is
an agent_v3.py change → OWN fresh baseline (re-run grade_agent.py, confirm 0.959 /
declined→qualified=0 reproduces on the decoupled agent BEFORE it becomes the new
baseline). Reproduction of the defect for the next session: v2 prompt qualifies
the 9-top "Can I make a reservation for 9 people this Sunday at 6pm?"; the §2.3
block made it decline. After decoupling, that same block should NOT move the
decision — that is the decoupling's acceptance test.

Other tracks unchanged/unbraided: §2.8a+§2.8b (now KNOWN to be 2 layers AND to
carry the contamination risk above — gated on decouple), date-anchor/merge-field
code fixes, git-history PII audit, foundation→repo migration. Add to backlog:
grader set needs a small-plain-reservation row to guard qualified→declined.
## Session O — close block (DECOUPLE _classify FROM DRAFT PROMPT — SHIPPED, clean)

OUTCOME: The contamination channel N found is CUT. _classify no longer reads the
draft-authoring SYSTEM_PROMPT; it gets CLASSIFY_SYSTEM_PROMPT (minimal intent-only,
sourced from SUBMIT_QUALIFICATION_SCHEMA.description + one "ignore tone/wording"
sentence). _write_reply unchanged. Acceptance test PASSED: the §2.3 billing block
that flipped the 9-top qualified→declined under the coupled build no longer moves
the decision (stays qualified) — the draft block reaches _write_reply but the
classifier never sees it. Commit 801ce96, eval/agent_v3.py by filename only.

### Goal 0 — all six passed, state matched STATE exactly
- label.py: 168/166/2/0. eval_loader: 160/73. probe: [B-FAIL]=0, 19 [B-OK].
- git log: 2e53799 HEAD. log_outcome: COLD n=8, RECALL n=3. git status: pile clean,
  STATE.md committed (J-pattern NOT repeated — N committed it). All PASS.

### Pre-decouple baseline (re-measured live, not trusted from STATE)
- overall 0.959 | declined→qualified=0 | qualified→declined=2 (rows 23, 56).

### The edit (one change, agent_v3.py only)
- EDIT 1: module-level CLASSIFY_SYSTEM_PROMPT after SUBMIT_QUALIFICATION_SCHEMA,
  = "ignore tone/wording, decide what the sender wants" + the schema's own four
  intent definitions. One source of truth with the grader's contract.
- EDIT 2: _classify system block SYSTEM_PROMPT → CLASSIFY_SYSTEM_PROMPT. Nothing
  else touched (tool_choice, messages+[nudge], max_tokens=200, cache_control stay).
- findstr verified: SYSTEM_PROMPT used once (_write_reply); CLASSIFY_SYSTEM_PROMPT
  defined once, used once (_classify). Option A: conversation history preserved,
  only the system block changed.

### Acceptance test (the pass condition — fail-fast, run before the grade)
- Recreated §2.3 prompt_v3.txt (TEST ARTIFACT), pointed agent at it, ran 9-top
  "Can I make a reservation for 9 people this Sunday at 6pm?" via pilot_v0 --stdin.
- Decision = qualified → PASS. Coupled build declined the same input. Channel cut.
- Reverted agent to prompt_v2.txt, deleted prompt_v3.txt. O ships NO §2.3 wire-in.

### Post-decouple grade run (required — decision-path code change, own baseline)
- loaded 73 clean cold inbounds. overall 0.959 (unchanged).
- declined→qualified = 0 (primary danger cell — HOLDS).
- qualified→declined = 1, row 56 only. Row 23 flipped to CORRECT. Set {23,56}→{56}:
  subset of allowed, no third, no shifted row. Consistent with "more stable
  classifier" prediction (moderate confidence on mechanism; do NOT claim the
  decouple "improved accuracy" — overall held flat, row 23 is n=1).
- Off-cell misses (non-guarded): [34] needs_info→qualified, [73] declined→needs_info.
  3/73 total, no regression.

### Repo state at close
- Commit 801ce96 (agent_v3.py decouple). prompt_v3.txt deleted (test artifact, never
  staged). ~33 diagnostics pile untouched. agent_v3.py confirmed back on prompt_v2.txt.

### ENV NOTE (not a repo change — a lever if wanted)
- Both venvs hit CERTIFICATE_VERIFY_FAILED on the Anthropic API: TLS-intercepting
  root CA in the Windows cert store, absent from certifi's bundle. Worked around
  out-of-band via temp sitecustomize.py calling truststore.inject_into_ssl() on
  PYTHONPATH (deleted, no repo file touched). truststore already installed in both
  venvs. Permanent fix without the env hack = wire truststore.inject_into_ssl() at
  process start. Its own decision; NOT done this session.

### THE UNBLOCK (what O buys)
The wire-in track is now low-risk. §2.3, §2.8, indoor, and every other foundation
rule can be re-attempted as GENUINELY draft-only variables — a prompt edit reaches
_write_reply, not _classify. Each still gets its own eval cycle, one variable, fresh
baseline vs 0.959. §2.3 must be RE-DERIVED against the decoupled architecture, not
reused from the killed N block. BACKLOG unchanged: grader set still needs a 9-top-
class row (the acceptance test caught what the 73 rows can't); date-anchor/merge-field
code fixes; git-history PII audit (gates public flip); foundation→repo migration;
diagnostics-pile disposition; repo-anchor path defaults.
## Session P — close block (§2.8a + 2.6a WIRE-IN — SHIPPED, clean, best grade to date)

OUTCOME: The tier1-underdisclosure failure class (4 of 8 cold Stalls) is addressed
at the prompt layer. prompt_v3.txt replaces the flat no-pricing rule with the §2.8
three-tier policy + the 2.6a past-15mi never-quote rule; EXAMPLE 3 (which TAUGHT
the deferral failure — it was the Poway/live-7 shape) replaced with an operator-
authored Tier-1 disclosure example. Two commits this cycle:
  - 1315ebb: voice_checks.py check_no_pricing rewritten to three-tier logic
    (Tier-1 attributed figures pass; Tier-2/3/unattributed fail). Instrumented
    FIRST as a verified no-op on baseline drafts, so the prompt change landed
    against a gate that could score it.
  - <this commit>: prompt_v3.txt + agent_v3.py pointer v2->v3.

### Pilot shapes (fail-fast, run before the grade — 5/5 clean)
- live-11 shape (40-guest offsite, budget, quote ask): deferral GONE, buffet routed,
  Tier-3 lock line held. Residual: Tier-1 under-surfaced (no equipment/staff offer)
  — improvement not perfection, logged below.
- live-7 shape (23p Menu #3, Mira Mesa ~8mi, direct fee ask): quoted $50 correctly,
  offered equipment $150 + staff $200, total withheld. Near-verbatim EXAMPLE 3 —
  the example teaches, as expected; watch for over-parroting on non-matching shapes.
- past-15mi shape (Oceanside): NO fee stated, no tier extrapolated, "depends on the
  exact address" + did not say "we don't deliver there". NEW DANGER CELL HELD.
- total-ask (100 people): no total, EXAMPLE-1 qualifying-question route. Tier-3 held.
- bonus Typeform low-quality lead: needs_info (correct on "just exploring"), no PII
  slot leakage from empty form fields, nothing quoted.

### Grade run (73 clean cold inbounds)
- overall 0.986 (prior baseline 0.959).
- declined→qualified = 0 (primary danger cell HOLDS).
- qualified→declined = {} — row 56 flipped CORRECT. qualified now 1.000/1.000.
- Sole miss: row 73 declined→needs_info (same off-cell miss as both prior runs).
- CLAIM DISCIPLINE: the load-bearing result is tier policy in drafts + both danger
  cells held + zero regression. The 0.986 and row-56 flip are n=73/n=1 — plausible
  mechanism (classifier reads richer draft content; prompt itself is invisible to
  it post-O) but recorded as side effect, NOT as "wire-in improved classification."

### BACKLOG (adds/updates)
- Tier-1 under-surfacing residual on no-distance offsite shapes (pilot #1): agent
  quotes when asked/distance known, but does not volunteer the full Brenna block
  unprompted. Candidate next prompt variable; own cycle vs the new 0.986 baseline.
- VERIFY 1315ebb scope: pilot output shows a pii_email_phone_scan voice check not
  present in the pre-rewrite voice_checks.py read; either pilot-side or the step-1
  commit exceeded spec. Diff 1315ebb + paste voice_checks __main__ output (still
  outstanding from step 1). Cheap check, do at next session open.
- EXAMPLE-3 parroting watch: pilot reads should flag verbatim EXAMPLE 3 pasted onto
  shapes it doesn't fit.
- Unchanged: grader 9-top row; holdout from Q2–Q4 export; git-history PII audit
  (confirmed-positive, gates public flip); foundation→repo migration; 02 stale line;
  agent_v3 prompt-load path anchor (deferred from path-anchor session); stale line-18
  comment in agent_v3.py mentions prompt_v2 (cosmetic).
  ## Session Q — close block (TIER-1 VOLUNTEERING ON OFFSITE SHAPES — SHIPPED, prompt_v4)

OUTCOME: The Tier-1 under-surfacing residual (P's pilot #1) is addressed. prompt_v4.txt
adds ONE bullet after the Tier-1 bullet: on offsite/delivery inquiries, volunteer
equipment + staff unprompted and address the delivery fee (one tier if distance known
<=15mi; depends-on-exact-location with NO tier list if unknown). Agent pointer v3->v4.
Commit 42daf83 (prompt_v4.txt + agent_v3.py, by filename).

### Goal 0 — all six passed, no env var / no --db flag needed (a00d3ef confirmed honest)
label 168/166/2/0; loader 160/73; probe [B-FAIL]=0, 19 [B-OK]; log bdbb5a8 HEAD;
tally 11 rows COLD n=8 RECALL n=3; tree clean.

### PRE-WORK: 1315ebb scope check RESOLVED — verdict (a), no scope violation
- --stat: eval/voice_checks.py ONLY. Hunk map: @@ -92,41 +92,105 @@ (check rewrite)
  + @@ -171,8 +235,19 @@ (__main__ cases). 64+11=+75 net, reconciles with stat.
- pii_email_phone_scan lives in pilot_v0.py (lines 254/256/272), added in d0cb3a2
  (the withhold-on-declined / display-limit commit). Pre-existing pilot-side scan.
- voice_checks __main__ pasted IN FULL: 14/14 OK. P's step-1 debt cleared.

### THE VARIABLE — Option 1 (rule bullet), TWO iterations before pilots passed
- v4 draft 1: "quote the tier when known; otherwise say depends" — FAILED pilot 1.
  Draft said depends AND enumerated the full tier table ($25/$50/$75) as conditionals;
  checker caught '$25' unattributed and would have withheld. The "otherwise" branch
  was not exclusive enough to override the Tier-1 bullet's open invitation.
- v4 draft 2 (shipped): fee branch made exclusive — "quote that ONE tier" /
  "do not list the tier amounts". Also: an edit tangle mid-session left a duplicated
  fragment + literal "new:" line in the file; caught by findstr region check before
  any run. Lesson reconfirmed: verify edited bytes before running, every time.

### Pilots 5/5 (fail-fast, before grade)
1. P's pilot-#1 shape (reconstructed — P's exact bytes not saved; logged): PASS.
   Depends-line present, ZERO tier amounts, equipment $150 + staff $200 volunteered,
   Tier-3 held, qualified, 4/4 checks. The target behavior moved.
2. Mira Mesa fee ask: $50 and ONLY that tier. Near-verbatim EXAMPLE 3 (shape matches;
   parroting watch unchanged).
3. Oceanside past-15mi: NO fee, depends-on-address, did not refuse. DANGER CELL HELD.
   Read-note: draft said "outside our standard delivery radius" — softer than refusal
   but faintly frames past-15mi as exception vs 2.6a's normal-inquiry stance. Operator
   would likely cut the line. Logged, not gated.
4. 100p total ask: no total, EXAMPLE-1 route, Tier-3 held.
5. Onsite 12-16 patio (overcorrection guard): CLEAN — no delivery/equipment/staff
   block on the onsite shape. The bullet's offsite scoping held.

### Grade runs (73 clean) — TWO runs, rules pre-committed before run 2
- Run 1 (clean): overall 0.973 vs 0.986 baseline. dq=0 HOLDS. qd={} HOLDS (row 56
  stayed correct, qualified recall 1.000). Misses: [34] needs_info->qualified,
  [73] declined->needs_info (permanent).
- Run 2 (INVALID headline — rows 24-29 APIConnectionError, 6 rows; 0.904 measures
  the network): row 34 graded clean OUTSIDE the error block and flipped CORRECT.
  Per pre-committed rule: row 34 is NOISE (wrong in O, right in P, wrong run-1,
  right run-2). No third roll taken.
- RECORDED NUMBER: 0.973 (run 1), with row-34-unstable note. Honest claim: overall
  within noise of baseline, both danger cells held across both runs, target behavior
  confirmed. Do NOT claim v4 "cost" or "gained" accuracy.
- API errors: transient connection drops, self-recovered, signature differs from the
  cdb7c77 TLS failure. Watch item; if next grade run errors, add retry logic to
  grade_agent.py (its own change).

### BACKLOG (adds/updates)
- checker phrasing-sensitivity gap: check_no_pricing recognizes "delivery would be
  $50" as attributed but flagged "the fee is $25" in equivalent context (run-1 draft-1
  evidence). Backlog, own cycle if it bites again.
- FROM-PRICE OPEN QUESTION (parked, corpus item, NOT a gate): live-11's operator
  reply gave "delivery from $X local" — a from-price anchor on a no-distance shape.
  If that is the real house behavior, v4's say-depends-quote-nothing branch encodes
  the wrong rule. Test against corpus in a future batch before any prompt change.
- pilot-3 "standard radius" framing (above) — candidate wording watch, not a change.
- Project instructions STILL stale ("unanswered delivery rule" — answered in P);
  fired 4+ times this session. Swap at next settings visit.
- Unchanged: git-history PII audit (confirmed-positive, gates public flip); holdout
  from Q2-Q4 export; foundation->repo migration + file-02 stale line; agent_v3
  prompt-load path anchor (still deferred, prompt cycles active); stale line-18
  comment (now says prompt_v2, doubly stale — batch with next agent_v3 code change);
  grader 9-top row; EXAMPLE-3 parroting watch.

### NEXT SESSION — candidates (pick one, do not braid)
- git-history PII audit (human-eyes; the longest-standing gate)
- checker phrasing-sensitivity fix (small, self-contained)
- foundation->repo migration (+ 02 line fix rides along; PII-scan before staging)
Baseline for any future prompt work: 0.973/run-1 with row-34-noise note; constraints
unchanged: dq=0, qd={}, Tier-3 withhold, no past-15mi fee, no tier-list on unknown
distance (NEW, this session's addition to the danger-cell family).
## Session R — checker phrasing-sensitivity fix (one variable: voice_checks.py)

### Goal 0 — all seven passed incl. out-of-session 5e40764 at HEAD
label 168/166/2/0; loader 160/73; probe [B-FAIL]=0, 19 [B-OK]; log 5e40764 HEAD;
tally 11 rows COLD n=8 RECALL n=3; tree clean; agent_v3 line 78 prompt_v4
(line-18 comment still stale, still batched for next agent_v3 change).

### DIAGNOSIS (reframed the entry prompt's model)
The gap is NOT phrasing-shape ("would be" vs "is"). Attribution is purely
keyword-in-window; _TIER1_KEYWORDS lacked the token "fee". "delivery would be
$50" passed because "delivery" was in the 60-char window, not because of its
verb. Smallest correct surface = one token, not new phrasing patterns.

### THE VARIABLE — Option 1 collapsed to a single keyword
fees? added to _TIER1_KEYWORDS. Explicitly EXCLUDED: charge/price/cost (each
would flip a Tier-2 fail to pass — the forbidden false-negative direction).
- Cases FIRST: 6 added (2 gap-encoding, 1 regression pin, 3 guards:
  "charge $46/person" stays Tier-2 fail; "fee comes to $1,840 in total" stays
  Tier-3 fail with 'fee' in-window, proving precedence protects the danger
  cell; "$2,500 minimum" stays unattributed fail — patio-minimum withhold).
- Step-1 run: 18 OK / 2 XX, exactly the gap cases. Step-2 run: 20/20 PASS.
  No pre-existing fail flipped. Built in Claude sandbox against uploaded
  copy, re-verified on repo bytes (20/20 on machine). CRLF warning benign
  (LF-source file, autocrlf normalized; diff shows 2 clean hunks, +11/-0).
- Commit 55c2884: eval/voice_checks.py only, by filename.

### Insurance grade run — 0.973, dq=0. ROW 56 FLIPPED WRONG (noise verdict)
- Misses: [56] qualified->declined, [73] declined->needs_info. Row 34 flipped
  correct (consistent with its noise designation).
- Row 56 history: wrong <=O, right P, right Q-run-1, wrong R — the row-34
  signature. NO RERUN taken (rerolling to confirm = choosing when to stop
  sampling, the multiple-comparisons trap the row-34 rule exists to prevent).
- Causality verified in bytes, not assumed: run_voice_checks fires only in
  agent_v3.py's __main__ demo path (line 352), results printed, no branch on
  passed, no regenerate, no decision feedback. grade_agent.py does not import
  it. A checker edit CANNOT move classifications.
- BASELINE LANGUAGE REVISED: 0.973 with rows 34/56 sampling-unstable, row 73
  the sole stable miss. qd={} is NOT a per-run absolute a sampled classifier
  can promise; dq=0 IS the absolute and has held in every run ever. At n=73,
  identical 0.973 headlines with different miss composition => run-to-run
  deltas finer than ~+/-0.014 are noise.
- OPERATOR DECISION OPEN: qd downgraded from hard constraint to watch-item on
  Claude's read; operator may restore it as a kill-trigger (revenue-cost
  argument). Unresolved at close; next prompt session must resolve before
  its keep/kill rules are pre-committed.
- Zero retry lines: network clean, 5e40764 landed but UNEXERCISED in anger.

### BACKLOG (adds/updates)
- Path footgun EXTENDED: git pathspecs from inside eval\ double-stack the
  prefix same as script paths (bit twice in R: findstr, then git add — add
  failed fatal, nothing staged, no damage). Rule is now: ALL commands run
  from repo root unless the tool itself requires eval\ (pilot_v0.py,
  grade_agent.py only).
- NEW: usefulness_tally why-text eats dollar figures (live-11 shows "\-3K",
  "\/4hr" — escaping bug somewhere in the log_outcome pipeline). Cosmetic.
- Project instructions stale line fired again (5th+ occurrence): still says
  "unanswered delivery rule" — answered in P, extended in Q. Settings fix,
  not a commit.
- Unchanged: git-history PII audit (longest-standing gate, human-eyes, next
  operator decision = scanner name-list source); FROM-PRICE corpus question;
  pilot-3 radius framing; holdout Q2-Q4; foundation->repo migration + file-02
  line; agent_v3 path anchor; line-18 comment (batch with next agent_v3
  change); grader 9-top row; Section 4 loss hypotheses (highest-value next
  batch); EXAMPLE-3 parroting watch.

### NEXT SESSION — candidates (pick one, do not braid)
- git-history PII audit (the gate that blocks the public flip; queued next
  step is the scanner name-list-source operator decision)
- foundation->repo migration (+ 02 line rides along; PII-scan before staging)
- Section 4 dead-thread batch (not a code session)
Baseline for any future prompt work: 0.973, rows 34/56 unstable, row 73
stable miss. Constraints: dq=0 absolute; qd watched pending operator ruling
(above); Tier-3 withhold; no past-15mi fee; no tier-list on unknown-distance
offsite; no PII.
- Shell footsgun family, full diagnosis after two failed attempts: (1) PS
  double-quoted -m strings expand $25 to empty (e665067's original mangle; amended to 55c2884);
  (2) PS 5.1 single-quoted -m strings with EMBEDDED double quotes split at
  the inner quotes and git reads fragments as pathspecs (amend attempt 1
  errored harmlessly). RULE: any commit message containing $ or quotes goes
  through a here-string + git commit -F msg.txt. Same family as the tally
  why-text dollar losses.
  ## Session S — git-history PII audit: scanner + full hit inventory + remediation design

### Goal 0 — 6/7 clean; e665067 residual HIT as predicted from bytes
label 168/166/2/0; loader 160/73; probe [B-FAIL]=0, 19 [B-OK]; HEAD 2614a69;
tally 11 rows COLD n=8; tree clean. findstr e665067 -> 1 hit line 1709
(shell-footgun bullet cites the dead pre-amend hash) — fixed this session's
STATE touch, alongside the R-block "Commit <hash>" placeholder (never filled
at R close; resolved to 55c2884 from git log) and the stale file header
(said Session E). All three are STATE-integrity defects, not code.

### Deliverable 1 — scanner (Claude Code brief, full-bytes discipline held)
labeling/scan_pii_history.py committed 77c245e. Read-only history walk:
rev-list --all x ls-tree per revision x cat-file per unique blob — deleted
paths covered by construction. Report gitignored BEFORE existence
(check-ignore gate wired, exit 1 if trackable), every term redacted at
write time to stable {kind-N} tokens.
- DEVIATION ACCEPTED: brief premise wrong — the five gitignored scripts
  carry names in COMMENTS, not list literals; pure AST extraction would
  have zeroed and tripped the gate. Claude Code named it before building
  and extended derivation: AST assignment strings + comment/docstring
  prose mining + DB backups (From/To slots, greetings, signatures) +
  archive scripts. Union across all sources, counts-only stdout.
- ACCEPTANCE GATE DID ITS JOB: STATE.md confirmed-positive control wired
  as exit-2 hard failure. Zero-hits-on-STATE = broken scanner, never a
  clean history. Passed every run (1105 -> 1151 as new commits added
  historical STATE revisions — scanner counting its own session, correct).

### Deliverable 2 — two rejections on human-eyes pass, fixed (77c245e)
Claude Code's proposed staging REJECTED against its own pasted bytes:
(1) scanner FIVE_SCRIPTS constant embedded a customer surname via a
gitignored script's FILENAME; (2) .gitignore carried the same filename
plus a comment naming three customers. Root cause identical: a filename
is PII and propagates into every file referencing it. Fix: script renamed
to labeling/quarantine_c1.py, .gitignore line + comment scrubbed, scanner
constant updated, re-run identical (same union/terms/hits), THEN staged.
Lesson (new instance of trust-the-bytes): a deliverable's claim of "zero
PII in this file" is checked against the file's bytes including every
embedded PATH, not against the claim.

### Deliverable 3 — inventory (final, post-allowlist-refinement)
Two review items ruled vendor infra, not people: the redact-allowlist org
slot token is the form vendor's notification display name; the email in
export_threads' exclusion list is google's bounce daemon. Both added to
scanner allowlists (commit after 77c245e). 136 hits reclassified false
positive; export_threads.py exits the inventory entirely (never dirty).
FINAL NUMBERS: 1697 hits / 33 of 44 commits / 7 paths / 10 unique terms.
By path: STATE.md ~1151 (dominant surface — session narratives quoted
real names to document PII lessons), probe_body_artifacts.py 224 (docstring
narrates F5/F6 with real names), redact.py ~35 genuine (slot-format
comments), tests/test_redact_allowlist.py comments, OPTION_C_WORKORDER.md,
probe_from_lines.py, .gitignore (now history-only post-77c245e).
IRONY, RECORDED: the leaks are overwhelmingly the PII tooling and its
documentation quoting the names they caught. Every one rewordable to
tokens; none needs the real string to do its job.

### HEAD-live finding (reshapes remediation)
findstr 2614a69 on the report: 70 hits live at audit-time HEAD across ALL
8 then-paths — there was NO history-only bucket. Rewriting history while
HEAD bytes are dirty fixes nothing. Post-77c245e: .gitignore hits are the
first history-only entries; ~62 genuine hits remain HEAD-live across 6
paths (46 of them STATE.md narratives).

### REMEDIATION DESIGN (design only — execution is Session T)
PHASE 1 — HEAD byte-fix session: reword the ~62 HEAD-live hits to
{name-N} tokens / initials across the 6 paths (docstrings, comments,
STATE narratives). One session, commits by filename, re-run scanner
after: acceptance = zero non-allowlisted hits at NEW HEAD. STATE.md
convention from this block forward: session narratives NEVER quote a
real name — tokens only. Phase 1 gates Phase 2.
PHASE 2 — history rewrite: git filter-repo --replace-text with a
GITIGNORED replacements file (real-term -> token map; the map itself is
PII, same discipline as the report). CHOSEN over fresh-repo cutover:
the 44-commit history is a documented portfolio asset (repo conventions:
meaningful commit history for senior-engineer review); cutover destroys
the artifact the repo exists to demonstrate. Fresh-cutover stays the
documented fallback if filter-repo misbehaves on Windows.
BACKUP PROTOCOL (gate, non-negotiable): git clone --mirror to a path
outside the repo, verified restorable (clone from the mirror, Goal 0
passes on the restore) BEFORE filter-repo touches anything. Rewrite
invalidates all commit hashes — every hash recorded in STATE becomes
historical-reference-only; note this at the top of STATE in T.
COVERAGE GAP TO CLOSE IN T BEFORE REWRITE: scanner walks blobs only.
Commit messages, tag names, branch names unscanned. One-shot pass
(scanner extension or manual git log --all review) required; risk low
(commit style is technical), but low is not verified.
PUBLIC FLIP CRITERIA: Phase 1 clean + Phase 2 executed + full re-scan
zero non-allowlisted + commit-message pass clean + mirror backup
retained. Then and only then.

### BACKLOG (adds/updates)
- NEW: Session T = remediation (Phase 1 byte-fix, then Phase 2 rewrite;
  can split into two sessions if Phase 1 runs long — Phase 1 alone is
  committable value).
- NEW: intake plumbing (gmail -> pilot, kills copy-paste friction) —
  named as a drift risk twice this session, held out of S. Candidate
  AFTER T; two weeks of manual daily pilot use first would prove or kill
  friction-as-bottleneck (B-before-C logic). Manual loop grows the cold
  tally toward the conversion number regardless.
- LinkedIn Projects entry drafted (two variants, no repo link, no
  metrics, privacy-audit status stated plainly) — operator may post;
  the build-announcement POST still gates on a conversion number.
- Project instructions stale line FIXED (settings swap done mid-session;
  5+ sessions on the backlog, cleared).
- qd-constraint ruling still OPEN — unchanged: next PROMPT session opens
  with it before pre-committing keep/kill rules.
- Unchanged: foundation->repo migration (+ file-02 line) — T candidate
  rider; FROM-PRICE corpus question; pilot-3 radius framing; holdout
  Q2-Q4; agent_v3 path anchor + line-18 comment; grader 9-top row;
  Section 4 loss hypotheses (highest-value next batch); EXAMPLE-3
  parroting watch; 5e40764 retry still unexercised; tally why-text
  dollar-figure escaping.

### NEXT SESSION — candidates (pick one, do not braid)
- Session T Phase 1: HEAD byte-fix (~62 hits, 6 paths, reword to tokens)
  — smallest step on the public-flip critical path.
- Section 4 dead-thread batch (not a code session).
- qd ruling (operator decision, ~15 min, unblocks future prompt work).
Baseline for prompt work unchanged: 0.973, rows 34/56 unstable, row 73
stable miss; dq=0 absolute; Tier-3 withhold; no past-15mi fee; no
tier-list on unknown-distance offsite; no PII.

## Session T Phase 1 — HEAD byte-fix: zero customer names in tracked bytes at HEAD

### Goal 0 — clean, brief matched exactly
label 168/166/2/0; loader 160/73 PASS; HEAD 6c84b97; tree clean; scanner
1821 / 35 of 46 / 7 paths / 10 terms, gate PASS 1243; findstr 6c84b97 ->
62 hits / 6 paths, .gitignore absent (history-only as designed).

### Finding 1 — two placeholder false-positive terms (8 of 62 hits, 3 paths)
Byte-inspection of flagged lines showed "Lastname" and "Firstname" —
literal documentation-placeholder words in format-example comments — were
mined as name terms. Fixed via DOC_PLACEHOLDERS set prepended to
KNOWN_NON_PII: 99bdea9 (lastname), 904bb65 (firstname; also fixed a
one-string set-literal typo from the first attempt that silently matched
nothing — caught because the re-run regressed to baseline and was
diagnosed from bytes). probe_from_lines.py and redact.py exit the
inventory ENTIRELY — never carried a real name in any commit; they leave
Phase 2 scope too. Corrected genuine inventory at 6c84b97: 56 hits, 4 paths.
LESSON (cost two detours): verify the term against file bytes BEFORE
designing the edit. Report snippets identify lines; only bytes identify terms.

### Finding 2 — token numbering is run-stable, NOT cross-run-stable
Any term-list change renumbers report tokens. File tokens are FROZEN to
the committed numbering and the report is not chased: {name-17} = the F6
customer surname, {name-8} = that customer's full-name form, {name-3}/
{name-4}/{name-5} = the 18da9fc1 trio (first/first/full), {name-25} = the
19e5a9ca vendor first name. Report-vs-file token mismatch is cosmetic; the
acceptance gate greps real terms, not tokens.

### Finding 3 — scanner term-coverage gap (gate was necessary, not sufficient)
Scanner terms come only from gitignored scripts/DBs. Seven customer names
sat at HEAD in STATE.md's [D]-surface inventory that no term source
contained — invisible to every prior scan. Fixed twice over: (a) the name
list in STATE.md replaced with a count + pointer; (b) audit_names_local.txt
(already a wired [names-file] source, was empty) populated with the 7
names (one per line; parser silently yields 0 on comma-separated input).
The populated source immediately caught a 5th dirty path no scan had ever
seen: audit_pii.py:20 carried a customer full name in a comment (365ea6d).
Independent full-file name sweep of STATE.md found nothing beyond the 6
flagged terms + these 7.

### Finding 4 — one boundary-blocked hit the scanner misses by design
STATE.md old line 268 held the vendor name flush against a literal \n
escape (no word boundary); the scanner's word-boundary matching never
flagged it in any run. Fixed in this commit's byte pass. Phase 2 note:
scanner matching should be re-checked for boundary-adjacent hits before
the post-rewrite final scan is trusted.

### Byte-fix commits (by filename)
- 99bdea9 scanner: lastname placeholder dropped
- b6a7425 OPTION_C_WORKORDER.md + test_redact_allowlist.py
- 904bb65 scanner: firstname placeholder + set-literal typo fix
- 6489c32 probe_body_artifacts.py (4 docstring/comment lines; probe
  re-run [B-FAIL]=0 after edit)
- ffa3a36 token renumber to frozen numbering (OPTION_C + tests)
- 365ea6d audit_pii.py comment (names-file coverage catch)
- this commit: STATE.md ~48 hits tokenized via deterministic script
  (manual find-replace misfired and was reverted; replacement done
  programmatically from the pristine HEAD copy, counts verified:
  5 filename / 2 full / 8 trio-full / 18 surname / 8+1 firsts / 5 vendor /
  1 [D]-list), quarantine filename refs -> quarantine_c1.py, [D] list ->
  count + pointer, this close block.

### ACCEPTANCE (record result at close)
Scanner re-run post-commit with populated names file (13 terms), findstr
new HEAD -> required ZERO non-allowlisted hits. Result: zero non-allowlisted hits at then-HEAD 660a0b9 (historical hash). Verified 2026-07-11 at T2 Goal 0: scanner re-run 2073 hits all history-only, findstr on the HEAD hash returned 0 lines. Backfilled at T2 close; the placeholder itself was a repeat of the unfilled-acceptance defect class.
Gate PASS required; gate count grows with each new STATE.md revision in
history (correct, per-commit counting).

### CONVENTION (standing, from S, now enforced)
STATE narratives never quote a real customer name — tokens only. This
block complies; every block after it must.

### NEXT — Phase 2 is the sole remaining pre-flip work
filter-repo --replace-text (replacements file gitignored; now must cover
all 13 terms incl. the names-file 7), commit-message/tag/branch coverage
pass, mirror backup verified-restorable BEFORE rewrite, boundary-adjacency
scanner check (Finding 4), full re-scan, then public flip. Hash
invalidation warning: rewrite makes every hash in this file
historical-reference-only.

### Backlog unchanged
qd ruling (operator, before next prompt session); Section 4 dead threads;
intake plumbing (after 2 weeks manual pilot); foundation migration;
holdout Q2-Q4; agent_v3 path anchor + line-18 comment; grader 9-top row;
EXAMPLE-3 watch; tally dollar-escaping; 5e40764 retry unexercised.
Baseline for prompt work: 0.973, rows 34/56 unstable, row 73 stable miss;
dq=0 absolute; Tier-3 withhold; no past-15mi fee; no tier-list on
unknown-distance offsite; no PII.


## Session T2 close -- history rewrite executed, repo PUBLIC

Flip timestamp: 2026-07-12 08:59 local (operator flipped visibility after push verification).

### What happened, in order
- Goal 0 matched the brief exactly. T1 acceptance backfilled (see above);
  stale header fixed.
- Step 1: mirror at C:/dev/_mirrors/yannis-ai-build-pre-T2.git,
  restore-verified GIT-ONLY (ruling: the DB never lived in git; verifying
  it in a restore proves the copy, not the mirror). Scratch restore
  deleted after verification. FINDING: ~85 dangling blobs + 2 dangling
  commits -- an unscanned surface (rev-list --all never sees them),
  though unreachable objects cannot be pushed, so flip-risk was nil.
- Step 2: scan_pii_aux.py shipped (committed). Pass A (commit msgs, refs,
  tags) found 2 name hits in one commit message -- the F6 close-block
  narrative quoted the customer slot; "commit style is technical" was
  wrong once. Pass B (boundary-agnostic substring over ALL blobs incl.
  danglers) found Finding-4 LIVE: 11 reachable hits of the vendor name
  flush against a literal \n at STATE.md old line 268, invisible to the
  guarded scanner in every prior run. Noise floor established: one short
  derived term ({name-44}) substring-matches inside common words
  (total/stale/accidentally), ~1258 innocent hits; EXCLUDED from
  replacement by ruling. 14 name terms + 2 phone numbers existed ONLY in
  dangling blobs -- different dirt than reachable, destroyed at rewrite gc.
- Step 3: replacements file built (13 rules, gitignored-first).
  verify_replacements.py shipped as the gate: derived-set membership,
  reachable-history hit count, full-before-single ordering, per rule.
  The gate caught one dead rule ({name-8} typed first-last; history
  carries the Outlook "Last, First" form) before it could ride in as a
  silent no-op.
- Step 4 attempt 1: POISONED. The replacements template carried '#'
  comment lines; filter-repo's format has NO comment syntax -- every line
  without '==>' becomes a replace-with-***REMOVED*** rule. Every '#' in
  every tracked file in history was destroyed. Detected immediately
  (acceptance scripts refused to parse), mirror-restored to c65431d in
  ~4 minutes, zero data loss. The recovery design carried the session.
- Step 4 attempt 2: file stripped to 13 rule-lines-only (BOM-free .NET
  write), re-verified ALL PASS, rewrite clean. 55 commits in, 54 out:
  the T1 probe_body_artifacts tokenize commit became empty (its parent
  received the same replacements) and was pruned -- safe by construction,
  a pruned-empty commit's tree equals its parent's. filter-repo also
  rewrote abbreviated hashes quoted inside commit MESSAGES to their
  post-rewrite values (messages only; file contents keep stale hashes,
  hence the note at top).
- Step 5 acceptance, all green: main scanner 48 terms derived, 0 hits
  across 54 commits, exit-2 = INVERTED CONTROL BY DESIGN (pre-answered
  ruling: exit 2 + nonzero derived terms + 0 hits = PASS; the positive
  control was legitimately erased). Aux --post-rewrite: reachable
  B-GUARD 0, A-TERM 0, {name-38} flush-form 0, residue = {name-44}
  noise floor only. fsck: ZERO dangling objects. label 168/166/2/0,
  loader PASS 160/73 (DB untouched, as it must be).
- Step 6 flip: msg.txt gitignore gap closed (was in the checklist, had
  no rule). FINDING: no README existed -- the checklist item presumed a
  file that was never written. Minimal honest README drafted and
  committed (no metrics quoted by design; the honest n>100 run has not
  happened). notes/ ruled PUBLIC deliberately -- the process is part of
  what the repo demonstrates. FINDING: no GitHub remote had ever been
  created; "REMOTE IS PRIVATE" described an intention, not a repo. The
  dirty history never left this machine. Repo created fresh, clean
  history pushed (284 objects), flipped public.

### Standing rules added/changed
- THE MIRROR IS FROZEN FOREVER. It is the sole copy of pre-rewrite
  history; a remote update would clobber it with rewritten refs. Never
  update it. Custody = labels.db discipline.
- Replacements files contain RULE LINES ONLY. The filter-repo format has
  no comments; any non-rule line is a live replace-with-***REMOVED***
  rule. verify_replacements.py must be extended to fail on non-rule
  lines before it is ever reused.
- Any commit made after a mirror gate re-runs the mirror update BEFORE
  the destructive step (obeyed twice this session) -- now moot for this
  mirror (frozen), binding for any future backup gate.
- Code blocks in session chats contain commands only, zero prose (both
  directions of the paste-accident happened this session).
- PROCESS RULE reaffirmed the hard way: multi-line file changes are
  produced by script, never by manual find-replace. The replacements
  fill was directed manually in violation and cost four confused
  round-trips; the verifier gate is what saved it.

### Post-rewrite reference hashes (live)
e3398c6 rewrite base (gitignore replacements path, rewritten)
d8fa846 verify_replacements.py
5e90526 msg.txt gitignore
b37660f README
(close-block commit hash: the commit containing this block)

### Backlog (unchanged unless noted)
qd ruling (operator, before next prompt session); Section 4 dead-thread
batch; intake plumbing (after 2 weeks manual pilot); foundation->repo
migration + file-02 stale line; holdout Q2-Q4; agent_v3 path anchor +
line-18 comment; grader 9-top row; EXAMPLE-3 watch; tally
dollar-escaping; retry commit unexercised (hash now historical); README
quality pass is its own later session ("not embarrassing" bar was the
only bar applied today); eval_loader assert refresh after batch-3
labeling settles.
Baseline for prompt work unchanged: 0.973, rows 34/56 unstable, row 73
stable miss; dq=0 absolute; Tier-3 withhold; no past-15mi fee; no
tier-list on unknown-distance offsite; no PII.

## Session CRM-v0 close — 2026-07-12
### What happened
- Goal 0 PASS at 458e7f9; .env gitignore-verified before key added.
- Smoke test vs live CRM: 201/409/201/401 all exact per handoff. First
  live posts the agent surface ever received. Synthetic event
  7e413ef6-ec40-4cb9-bd31-4aa978d8efb0 / draft
  2fb7e9c5-5c0b-4003-bd3a-a1abfd316b40, cleaned up CRM-side at close.
- curl.exe cannot TLS to Vercel from this machine (exit 35);
  Invoke-WebRequest and Python urllib fine. curl not used by any
  tracked code; noted only in case Python ever shows TLS trouble.
- c440523: eval/crm_push.py + eval/test_crm_push.py (10 synthetic
  contract tests, pytest green, no network in tests).
- d988bd2: pilot --push hook, stdin-only (corpus rows are historical,
  not live leads — argparse-enforced), CON-device prompts (stdin is
  EOF after --stdin), empty-answer veto, declined/human_review skip.
- Live run attempted on a real inquiry: decision needs_info, draft
  passed all hard checks, danger cells held (no fee on unknown
  distance, Tier-1 quoted, Tier-3 withheld). Push aborted at prompt
  (operator reflex Ctrl+Z — veto worked as designed), then correctly
  NOT retried: inquiry was Typeform-sourced.
### FINDING (session's main output)
Typeform leads auto-create CRM rows via webhook (source=typeform) and
have NO gmail_thread_url. push_lead on one would DUPLICATE the lead
with no dedupe key. v0 push path is direct-email-only by construction.
Current live volume is mostly Typeform. What Typeform leads need is
draft-attach-only to the EXISTING event id — endpoint exists, pilot
has no path to it. This reorders the backlog.
### Shadow week clock: NOT STARTED
No direct-email inquiry live in the inbox today. Clock starts on the
first real email inquiry pushed end-to-end. Recorded honestly rather
than forcing a stale thread through.
### Observation for tally
needs_info decision produced a draft that asks for nothing (no date/
location question). Decision-draft mismatch, watch item.
### Backlog (reordered)
1. draft-attach-only path for Typeform leads (operator supplies
   event_id from CRM; push_draft already supports it) — likely v0.1,
   ahead of gmail-pull v1 given live volume mix.
2. gmail-pull intake v1 (shadow week = friction evidence).
3. qd ruling (operator, before next prompt session); Section 4 dead
   threads; foundation migration; remainder per T2 block unchanged.

### Amendment (same sitting)
- PROCESS ERROR this session: push executed BEFORE the scanner re-run.
  Scans came back clean so nothing escaped, but the ordering violated
  the last-wall principle. BINDING RULE: scanners run before git push,
  every session, no exceptions.
- Main scanner inverted-control verdict on clean history confirmed
  expected per T2 ruling (not broken, not to be fixed).
- Aux triage: name-44 B-SUB 1521 reachable hits = benign substring
  (eyeballed, hits inside ordinary tokens, no standalone occurrence).
- Synthetic CRM row (7e413ef6) dismissed, Lost, archived CRM-side.
