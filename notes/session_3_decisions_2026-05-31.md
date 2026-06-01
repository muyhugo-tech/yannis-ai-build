# Session 3 decision record — 2026-05-31

Written at end of session. Captures decisions made today that change how
the pipeline works going forward. Save under `C:\dev\yannis-ai-build\notes\`.

## Decisions made

### 1. No export-time filtering of mixed-signal senders

Removed Jonathan, Denise, and Chris from `internal_addresses.txt` (or
emptied the file entirely — depends on what was finalized).

**Reasoning.** During batch 1 labeling, all three sometimes send real
forwarded catering leads and sometimes send pure operational noise
(schedules, wine lists, HR docs). Filtering at export drops the real
leads invisibly — you never know what you missed.

**The principle.** Filter at export only when sender is *always* noise.
Filter at label/agent time when sender is *sometimes* noise, sometimes
signal. The agent reads the full thread and decides; the exporter cannot
make that call from sender address alone.

**The cost.** ~6 extra `not_an_inquiry` labels per ~50-thread batch.
Negligible. The benefit is zero invisible loss of real forwarded leads.

### 2. `internal_addresses.txt` lives in the project root, not in labeling/

The exporter reads it with a relative path and runs from the project
root. If it ends up in labeling/, the WARNING fires and filtering
silently doesn't apply.

### 3. Exporter rework deprioritized in favor of eval harness

Started today as the planned next big work block. Stopped after
discovering that the biggest "bug" (internal staff leakage) wasn't a bug
at all — those threads SHOULD have come through. Remaining real exporter
issues are smaller than originally scoped:

- Stitched threads (2 of 50 in batch 1, ~4% — real bug, but bounded)
- Newsletter cruft (already handled downstream by the redactor at small
  per-call cost)
- Tighter query exclusions for Typeform/Toast vendor marketing (small
  query-syntax wins)

**Decision.** Defer all of the above. Move next to the eval harness
(weeks 3-4 of the milestone plan). The harness is what turns the 50
labels into a measurement instrument; without it, labels are just
opinions. The exporter is "good enough" — the data feeding labels is
already real ground truth.

## Current state at end of session

- 50 threads exported, ingested, labeled. 5 fix-pass relabels applied
  via `relabel_fixes.py` in batch `b1_relabel`.
- Labels DB at `C:\dev\yannis-ai-build\labeling\labels.db`.
- Dataset shape: 64% not_an_inquiry, 26% private_event, 6% catering,
  4% unknown. 20% qualified, 16% booked.
- `internal_addresses.txt` decision pending: empty file, or just Chris,
  or omit entirely. (See decisions section above.)

## Open items carrying forward

### Relabel/exclude queue from batch 1 (already applied via relabel_fixes.py)

These are documented for traceability — the fix script already ran and
inserted corrected rows. Use `MAX(labeled_at) per inquiry_id` to read
the latest label.

- `19df97c26d3467f8` — relabeled with proper language_patterns and
  edge_case_reason (prior had typo'd values).
- `19e32408d592d128` — relabeled with proper edge_case_reason.
- `19e32e093576d648` — marked EXCLUDE_FROM_EVAL, stitched Typeform
  threads. Needs split after exporter rework.
- `19e37739e85c19db` — relabeled to qualified/booked with
  cross_thread_continuation tag (paired with 19e3cdfd754257d3).
- `19e4be5fea76755d` — marked EXCLUDE_FROM_EVAL, stitched Toast form
  threads. Needs split after exporter rework.

### Known issues to handle in future sessions

- **Stitched threads.** Two confirmed cases where Gmail bundled unrelated
  messages from same-sender notification addresses (Typeform, Toast) into
  one thread. Fix at export time, not at label time. Defer to a focused
  exporter session.
- **Newsletter cruft in quoted replies.** The redactor handles it but
  burns tokens. Stripping at export time would be more efficient. Defer.
- **Empty-body internal threads.** Bodies that are image-only or HTML-only
  come through as `_(no body extracted)_` or with `[image: x.png]` tags
  and nothing else. The downstream pipeline correctly labels these as
  `not_an_inquiry` but it's wasted ingestion work. Defer.

### One thing to keep watching in batch 2

The conversion-rate hypothesis (foundation Section 4): batch 1 was a
recent-month export and produced 80% outcome=unknown because most
threads were mid-flight. Batch 2 (or batch 3) should include older
threads where outcomes are actually observable, otherwise the loss
hypotheses stay frozen.

## Next session

Goal: build the eval harness against the 50 existing labels.

Per the milestone plan (weeks 3-4) and `08_engineering_commitments.md`
(stub-first sequencing): the harness must produce sensible metrics
against a stub agent returning random or fixed outputs *before* a real
agent exists. That's the proof that the eval system itself is correct.

Approach when we get there:
1. Pytest-based harness reading from `labels.db`.
2. Deterministic voice checks first (em-dash count = 0, emoji count = 0,
   pricing-in-initial-response = 0, language match).
3. Stub agent that returns fixed/random outputs.
4. Confirm metrics are sane on garbage outputs before building the
   real agent.

Realistic time budget: 8-12 hours, probably across 2 sessions.
