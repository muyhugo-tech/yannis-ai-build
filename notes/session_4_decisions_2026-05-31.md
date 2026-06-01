Session 4 decision record -- 2026-05-31

Built the eval harness (weeks 3-4 milestone). Five files in eval/.
Stub-first sequencing honored: the measuring instrument is proven correct
before any real agent exists.

## Files built (all in C:\dev\yannis-ai-build\eval\)
- agent_output_schema.py  -- Step 0, the output contract
- stubs.py                -- Step 1, three fake agents (oracle/fixed/random)
- eval_loader.py          -- Step 2, latest-label-per-inquiry + exclude filter
- voice_checks.py         -- Step 3, deterministic voice checks
- grader.py               -- Step 4, precision/recall/F1 + confusion matrix

## Decisions made

### 1. Canonical status vocabulary = the LABEL vocabulary
qualified / needs_info / declined / human_review. Chosen because 50 labels
are already stored using it; the agent does not exist yet. Cheap side
conforms to expensive side. Agent-side synonyms (decline-recommended, etc.)
are reconciled in a mapping table (STATUS_ALIASES), not by touching labels.

### 2. EXCLUDE_FROM_EVAL marker lives in edge_case_reason
Stored as the literal prefix "EXCLUDE_FROM_EVAL:" in the edge_case_reason
column (also echoed in decision_reasoning). NOT a dedicated column. The
loader filters on this prefix.

### 3. Loader operation order: latest-label FIRST, then exclude-filter
Relabels were inserted as new rows (55 total rows, 50 distinct inquiries =
5 relabels). The exclude marker sits only on the latest (relabel) row; the
original row says different text. So we pick MAX(labeled_at) per inquiry,
tie-broken by label_id (relabel_fixes.py inserted all 5 at the same
timestamp), THEN check exclude on the surviving row. Wrong order could
mis-handle excluded inquiries. Proof number: 50 distinct -> 48 gradeable.

### 4. Both axes have a dominant class (corrects an earlier assumption)
Measured, not guessed:
  - qualification_decision: declined = 29/48 (~60%)
  - inquiry_type: not_an_inquiry = 32/48 (~67%)
The fixed stub demonstrates the majority-class trap on BOTH axes.

### 5. Metrics math hand-written, not scikit-learn
Portfolio piece is about understanding evals; importing the math outsources
the competence. Definitions match scikit-learn so numbers cross-check later.
Proven correct by the oracle stub scoring 1.000 + a synthetic hand-checked
case.

### 6. Language-match voice check is an explicit STUB
Deferred. Deterministic detection on short text needs either a dependency
or a model call (non-deterministic). And there are no real drafts to check
yet. Abstains (does not fail the suite). Revisit when the real agent emits
Spanish/English drafts.

## Verified results (DIAGNOSTIC, n=48, NOT gating)
- Oracle: 1.000 accuracy both axes -- grader math proven.
- Fixed (status, always declined): 0.604 acc, 0.000 recall on the 3
  minority classes -- trap exposed.
- Fixed (type, always not_an_inquiry): 0.667 acc, 0.000 recall on catering
  and private_event.
- Random: ~0.25 (status) / ~0.23 (type), messy non-degenerate spread.

## Open / carrying forward
- All metrics stay DIAGNOSTIC until n>=100. Do NOT set ship thresholds yet.
- Threshold SHAPE can be drafted (e.g. "recall on qualified >= X, X TBD at
  n>=100") but no numbers filled in -- 10 qualified examples is too few.
- Voice suite is trustworthy NOW (per-output booleans); classification
  metrics are not yet trustworthy as signal.
- internal_addresses.txt decision still pending (empty / Chris / omit) --
  affects batch 2 composition, not the harness.
- Batch 2/3 should include older threads with observable outcomes, or the
  loss hypotheses (foundation Section 4) stay frozen.

## Next session
NOT the real agent yet, unless deliberately chosen. Candidate next steps:
  - Wrap the harness as a pytest suite (currently __main__ self-checks).
  - OR start batch 2 labeling to push toward n>=100 (unlocks gating).
  - The real agent (weeks 5-7) should be a NEW chat -- different phase,
    eval-harness context stops being load-bearing.
