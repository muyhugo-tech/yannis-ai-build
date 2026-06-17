# STATE.md — Session C entry (append after the Session 9 block; update "Last updated" line to 2026-06-11)

---

## Session C result — redaction leak CLOSED (all three surfaces) + body-drop fix

Session C was exporter/redaction work only. The agent repo's eval code,
prompts, and agent_v3.py were NOT touched. labels.db text WAS touched
(15 rows) — see re-baseline note below.

### Root cause (overturns the Session 8 framing)
The leak was a COVERAGE gap, not a regex defect. redact.py's header pass
(redact_headers) was correct all along; it had simply never been run over
batch-1 files, the deferred folder, or the DB rows (ingested pre-fix).
threads_batch2 had the pass and was already clean. Proven by
probe_from_lines.py: all 182 flagged lines were `name <...>` shape the
existing regex handles; zero no-bracket cases existed. Confidence: high.

### What changed on disk
- `labeling/redact.py` — _ALLOWLIST extended with nine ORG-ONLY vendor
  senders (typeform, toast sites, truereview, unifirst, hospitality
  headline, new york times, weddingpro, office us, business manager).
  Rule documented in-file: slot must identify an organization, never a
  person. Grantify excluded (personal name in slot). Vendor senders stay
  visible by design — they are channel signal (Typeform notification vs.
  {name} cold open) and not customer PII.
- `labeling/rerun_redact_db.py` — NEW one-off. Header pass only (pure
  regex, no model call) over inquiries.thread_text_redacted. Backup-guard:
  refuses to write without a fresh labels_backup_*.db. Ran 2026-06-11:
  15 rows changed. Backup: labels_backup_2026-06-11.db.
- `labeling/rerun_redact_files.py` — NEW one-off. Same pass over .md
  thread files. Ran 2026-06-11: 32 files changed (31 in threads\, 1 in
  threads_batch2_deferred\ — the 26-header-line 19a802598e6895a5 thread).
- `export_threads.py` — TWO changes (committed separately or flagged as
  two concerns in one commit, operator's call):
  1. PREVENTION: private redaction regex copy deleted; now imports
     deterministic_redact from labeling/redact.py and runs it ONCE over
     the assembled message block (header pass needs the assembled
     '**From:** name <email>' line shape). Frontmatter excluded from the
     pass — thread_id is the join key and the payment-run regex eats
     digit-heavy ids (caught in testing). Subject redacted separately.
  2. BODY-DROP FIX: attachment-only/image-only messages now emit
     '_(no text body; N attachment(s): .pdf, .png)_' instead of silently
     reading as empty. EXTENSIONS ONLY, never filenames — customer file
     names are a PII channel the deterministic layer cannot close.
- `labeling/probe_from_lines.py` — NEW diagnostic, keep-pile. v2 imports
  _ALLOWLIST from redact.py (single source of truth) and treats quoted
  tokens ('"{name}"') as redacted, not leaks. Scans BOTH surfaces (.md
  files + DB rows), all messages per thread, prints format inventory +
  literal repr of leaked lines.

### Verification (the pass bar was met)
probe_from_lines.py after both reruns: 131 .md files + 128 DB rows,
ZERO leaked From-lines. Dry-runs matched live runs exactly on both
surfaces. Exporter fix verified by simulated assembly only — first real
export should be spot-checked with the probe. Confidence corpus header
surfaces are clean under current allowlist: high.

### EVAL RE-BASELINE (required — 0.934 is no longer directly comparable)
15 DB rows changed text (header lines only: real names → {name}, quoted
tokens normalized). Re-ran grade_agent 2026-06-__:

    clean-inbound status accuracy: 0.___   (prior: 0.934 on pre-fix text)
    declined→qualified cell: ___            (must stay 0)
    [paste full class table]

Record as DATA-CHANGE re-baseline, not an agent change. Watch row 11
(19e456f941c171f2, the 8-person reservation miss): its sender changed
from a raw personal name to {name}; if the miss flips, weak evidence the
raw name was noise. Single run; do not over-interpret 1–2 row moves.

### Open items (Session C deltas only — others carry forward unchanged)
- REDACTION LEAK: CLOSED on corpus (DB + files) and at source (exporter).
  Was the top gate; no longer blocks.
- EXPORTER BODY DROPS: CLOSED at source. Existing rows 51/58/60 keep
  their empty bodies (correctly labeled declined; agent handles them).
  They self-heal only on a future re-export.
- PUBLIC RELEASE GATE: NOT CLEARED. Committed .py/.md content still owes
  its own PII audit (separate decision, separate session). Prose/signature
  names in bodies remain model-pass-recall territory with the human
  backstop — unchanged honest limit.
- Batch-1 file BODIES may never have had the model prose pass (DB rows
  got it at ingest). Matters only if those files are re-ingested. Logged.
- NEXT SESSION (unchanged from Session 9): dataset work. Relabel pass for
  rows 1/2 (edge_case_flag=1), relabel review of row 22, grow clean
  inbounds past n=100. The exporter fixes make new exports cleaner than
  the old corpus — note the consistency seam when mixing old and new rows.

### Commit guidance (consistent with grader/agent-separate precedent)
1. redact.py allowlist + rerun_redact_db.py + rerun_redact_files.py —
   the corpus fix.
2. export_threads.py — the prevention + body-drop fix (source change,
   different blast radius).
3. probe_from_lines.py — diagnostics pile or ride-along, operator's call.
labels.db stays gitignored; its change is recorded here, not in git.
clean-inbound status accuracy: 0.934   (prior: 0.934 on pre-fix text)
    declined→qualified cell: 0             (gate holds)
    Confusion matrix IDENTICAL to Session 9: same 4 misses
    (rows 1, 11, 22, 61), same cells.

Row 11 (19e456f941c171f2) did NOT flip after its sender changed to
{name} — the raw-name-as-noise hypothesis is dead; the miss is
content-driven. Single run, one row: confidence low, but the negative
result narrows the diagnosis.

The 0.934 now stands on post-fix text. The eval-set-leakage caveat from
Session 9 (wording fitted to these 61 rows) carries forward unchanged;
the data-change caveat is RESOLVED — no perturbation observed.
## PII audit (same day, follow-on to Session C) — PASSED

audit_pii.py (NEW, tracked — no PII hardcoded; derives names from backup
DB at runtime): scanned 41 tracked files + 71 historical blobs. Zero
customer findings. Two benign hits (mailer-daemon in Gmail query filter).
Thread .md files confirmed never committed (3e157e0 stat). Both tracked
internal_addresses.txt copies confirmed empty placeholders. Prose files
(test_output.txt, session_3/4 notes) inspected by operator: no customer
names. Names-file grep abandoned (scrollback lost); manual inspection
substituted — adequate at this tree size.

PUBLIC-RELEASE GATE: CLEARED. Both blockers (redaction leak, committed-
content audit) resolved. Flip is now a deliberate decision, not blocked.
labeling/audit_names_local.txt gitignore entry is vestigial — harmless.