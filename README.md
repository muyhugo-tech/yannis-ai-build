# yannis-ai-build

An AI-powered catering inquiry triage agent for a real, operating
restaurant: Yanni's Bar & Grill, a 20+ year family-owned Mediterranean
restaurant in San Diego. Built by the operator (3 years running the
catering side) as both a production tool and a working demonstration of
eval-first agent engineering.

This is an active build. The agent runs in daily pilot use with a human
reviewing every draft before anything is sent.

## What it does

Takes an inbound catering or private-event inquiry (email body or form
text) and produces:

- a qualification decision (qualified / needs-info / declined / human-review)
- a draft reply in the operator's voice
- flagged edge cases with reasons

The operator reviews, edits, or rejects every draft. Human-in-the-loop is
the design, not a fallback.

## Architecture in one paragraph

Python, direct Anthropic SDK, no orchestration frameworks. The agent loop
is a plain while-loop on stop_reason. Every fact the business depends on
is computed by a deterministic tool, never sampled from the model:
delivery-fee tiers, the plated-service guest cap, quote-gate rules. The
final answer is a terminal tool call whose schema is the contract, so an
invalid decision is unrepresentable. Classification and draft-writing use
decoupled system prompts so voice edits cannot contaminate qualification
decisions. Prompt caching from the first commit.

## Eval discipline

The eval harness shipped before the agent did, validated against a stub
returning garbage to prove the metrics were sensible independent of any
agent. The labeled dataset is built from 3 years of real inquiry
history: currently 168 ingested threads, 166 labeled, 160 gradeable eval
rows, 73 clean cold inbounds. Labels encode the operator's actual
historical decisions, not idealized ones.

Iteration rules, enforced as standing commitments: one variable per eval
cycle, one fix per commit, acceptance gates written before results exist.
A set of danger cells act as hard kill criteria regardless of aggregate
score; the canonical example is declined-to-qualified misclassifications,
which must be zero. A run that improves the average while touching a
danger cell is a failed run.

Operator hypotheses about the business (why leads are lost, conversion
rates) are treated as unverified until measured against the corpus. They
are documented as questions and are not encoded in the agent.

## PII discipline

The training corpus is real customer email. Nothing customer-identifying
is committed: tracked files carry stable redaction tokens, the labeling
database and every PII-bearing artifact are gitignored, and the PII
scanners derive their search terms at runtime from gitignored local
sources so the scanners themselves contain no names.

Before this repository went public, the full git history was audited and
rewritten: every blob at every revision, commit messages, ref names, and
unreachable objects were scanned with two independent instruments
(a boundary-guarded scanner and a boundary-agnostic substring pass),
rewritten with git filter-repo against a byte-verified replacements map,
and re-scanned to zero non-allowlisted hits. The session-by-session
record of that work is in notes/STATE.md.

## Repo layout

- `eval/` -- eval loader, grader, pilot loop, voice checks
- `labeling/` -- labeling pipeline, schema migrations, PII scanners
- `notes/` -- session-by-session state records (the raw build log,
  published deliberately: the process is part of what this repo
  demonstrates)
- `_archive/` -- spent diagnostic scripts, kept for the record

## Status and roadmap

Running: daily pilot on live inquiries, human-reviewed.
In progress: growing the labeled dataset past 100 clean cold inbounds
for an honest held-out accuracy number; a documentation pass.
Planned: CRM integration for lead and draft records; loss-hypothesis
analysis against dead threads.

No conversion or accuracy numbers are quoted here yet, on purpose: the
honest held-out run has not happened, and this project does not publish
numbers before they exist.
