# STATE — Yanni's catering qualifier (code state of record)

Update this at the END of every build session. It records what is TRUE on
disk now, not what was decided in conversation. Next session: read this,
attach the files it names, then start. Do not rediscover.

Last updated: 2026-06-10 (end of Session 9).

---

## One-paragraph state

v3 agent ships structured qualification output. Session 9 changed ONE
variable — the status definitions inside SUBMIT_QUALIFICATION_SCHEMA's
description, rewritten from completeness-based to intent-based wording —
and the change was KEPT: clean-inbound status accuracy moved 0.787 → 0.934
with zero hard lead-loss errors before and after. The classify-wording
lever is now considered spent; remaining misses trace to data problems,
not prompt wording. Pipeline runs end to end with zero errors.

---

## File inventory (all in `eval/` unless noted)

- `agent_output_schema.py` — the AgentOutput contract. UNCHANGED.
- `agent_v2.py` — voice baseline + service-options tool. UNCHANGED.
- `agent_v3.py` — EDITED (the single variable). The four status definitions
  in SUBMIT_QUALIFICATION_SCHEMA's description rewritten intent-based:
  qualified = real person with active intent (missing details do not
  downgrade; small groups / regular dining with clear intent still
  qualified); needs_info = intent tentative or unclear (exploring/comparing,
  or cannot tell what they want); declined = no booking intent (spam,
  vendor, internal, empty/broken content, or not something Yanni's does);
  human_review unchanged. NOTHING else in the file touched — prompt_v2.txt,
  service tool, both qualify() stages, contract all byte-identical to
  Session 8. File-top docstring still describes Session 8; it is one
  session stale by deliberate minimal-edit choice.
- `eval_loader.py`, `grade_agent.py`, `grader.py`, `stubs.py` — UNCHANGED.
- `probe_misses.py` — NEW read-only diagnostic. Dumps inquiry texts of the
  Session 8 miss rows by deterministic loader index. Session-9-specific
  (indices hardcoded to the 61-row set, guarded by an n==61 assert).
  Joins the keep-pile of one-off diagnostics; not part of the harness.

## DB shape — UNCHANGED (see Session 8 entry; labels.db untouched this session)

## Dataset counts — UNCHANGED (61 clean inbounds; re-run check_counts.py if grown)

---

## Session 9 result — v3 status axis, CLEAN INBOUNDS (n=61)

DIAGNOSTIC, NOT GATING (n<100). Floor = 61% (always-declined).

overall accuracy: 0.934   (Session 8 baseline: 0.787; delta +0.147, +9 rows)

  class         support   prec   recall    f1
  declined         37    0.947   0.973   0.960
  needs_info        4    0.667   1.000   0.800
  qualified        20    1.000   0.850   0.919

confusion (rows=true, cols=pred):
  true\pred      declined  needs_info  qualified
  declined          36         1          0
  needs_info         0         4          0
  qualified          2         1         17

### Keep/kill: KEPT. All pre-registered criteria cleared:
- declined→qualified cell 0 before and after (zero hard lead-loss errors)
- qualified recall 0.650 → 0.850, above the ≥0.80 signal threshold
- declined recall 0.892 → 0.973 (junk rows 51/58/60 recovered to declined)
- qualified precision 1.000 — the loosened definition leaked nowhere
- Typeform "just exploring" rows (10, 24) flipped to CORRECT needs_info

### Method note (Session 9 process)
The edit was evidence-based: probe_misses.py dumped the 7 miss rows before
any wording was chosen. The original missing-fields hypothesis was KILLED
by row 32 (all fields present, still downgraded); the operator's labeling
boundary is intent-based, not completeness-based. The kept wording encodes
foundation 2.2's engagement floor (no ignore bucket; every group size served).

### Residual misses (4), diagnosed — none fixable by further wording edits:
- Row 1 (id 199bba0feb1dda0d) qualified→declined: OPERATOR-INITIATED thread
  mislabeled as clean inbound. Data artifact. Needs edge_case_flag=1 in a
  future labeling pass. Confidence: high.
- Row 11 (id 19a7b4a7eef7f026) qualified→declined: 8-person reservation
  request. The explicit small-groups clause did not catch it. Cause unknown
  (reads as already-booked vs. run noise). Single row; not chased.
- Row 22 (id 19a9e3565e6b65ba) qualified→needs_info: "what do you offer for
  15+ people." Possible LABEL softness — the new needs_info definition
  arguably fits this inquiry better than its qualified label. Candidate for
  relabel review, not agent change.
- Row 61 (id 19e607f611173ffd) declined→needs_info: internal one-liner.
  The internal-messages clause should have caught it; one-row anomaly, logged.

### Caveats (carry these forward verbatim)
- EVAL-SET LEAKAGE: the kept wording was partly fitted to these 61 rows'
  misses and re-measured on the same 61 rows. The +0.147 delta is an
  OPTIMISTIC estimate. The honest test is the future n>100 set with rows
  the wording never saw. Do not quote 0.934 without this caveat.
- Single run per condition; run-to-run variance never measured. The delta
  (+9 rows) is far outside plausible noise; the residual misses (1-2 rows
  each) are NOT — do not over-interpret them.
- Row 2 (mid-thread inquiry, a known data artifact) recovered anyway;
  treated as a bonus, not evidence the artifact problem is gone.
- needs_info support is still 4. human_review still 0 examples, unmeasured.

---

## Open items

- **CLASSIFY-WORDING LEVER IS SPENT.** Residual misses are data problems.
  Next accuracy work is DATASET work: (a) relabel pass for rows 1 and 2
  (operator-initiated / mid-thread → edge_case_flag=1) and a relabel REVIEW
  of row 22; (b) grow clean inbounds past n=100 so the metric gates. Do NOT
  run another wording variant against this same 61-row set — it would fit
  noise and leaked rows.
- **REDACTION LEAK (Session C, exporter):** unchanged from Session 8 —
  real names in sender slots. Still the top gate before any public release.
- **EXPORTER BODY DROPS:** rows 51/58/60 confirmed the attachment-only /
  empty-body defect inside the eval set itself. Same Session C bucket.
- **human_review unmeasured:** unchanged; needs edge-case rows or more data.
- **Non-graded AgentOutput fields** (fit_score, confidence, edge_flags):
  still placeholders; each becomes real only with its own grader + baseline.
- **agent_outputs table** still unused; persisting runs remains a later step.
- Commit note: agent_v3.py edit + this STATE.md update commit together;
  probe_misses.py can ride along or join the untracked diagnostics pile —
  operator's call, consistent with the untracked-throwaways precedent.

## Standing rules (unchanged)

Direct Anthropic SDK, no frameworks. Prompt caching from first commit. One
variable per eval cycle. Hugo runs all terminal commands; Claude edits files
only. Confidence labels on every claim. Push back on scope creep by default.
