# OPTION C WORK ORDER — Redaction Pipeline Repair

Written 2026-06-12 (Session D), after the batch-3 Q1 export surfaced four
pipeline defects on first real use. Growth (batch 3 Q2–Q4 export, ingest,
labeling) is BLOCKED until the verification gates at the bottom pass.

## STATUS (updated end of Session E, 2026-06-17)
- **F1 — DONE and COMMITTED** (commit 7561fe1). Migration 002 applied to
  labels.db; schema.sql + label.py status edit committed.
- **F2/F3 — DONE, TESTED, COMMITTED** (commit 1fa648b, Session E).
  export_text.py (new) + export_threads.py rewired + tests/test_export_text.py
  (14 pass). Proven end-to-end in Session D: Q1 re-exported clean, ingested
  40 (0 flagged), originating leak thread 18da9f17eb7c769d verified clean
  in the DB. Held uncommitted through Session D because coupled to the
  redact.py F6 diff; committed Session E once F6 landed.
- **F4 — DONE** (the 14 tests are F4).
- **F5 — NOT DONE.** Body-artifact probe still unwritten. Sessions D and E
  used a manual eyeball as the gate instead. Build it before relying on
  automated body-leak detection; it must NOT reuse the allowlist.
- **F6 — DONE and COMMITTED** (commit 0547c76, Session E). _ALLOWLIST's
  substring match replaced with two-tier is_allowlisted full-coverage rule.
  Staff full names (brenna fineman, jonathan gutierrez, yannis pihas,
  denise pihas) and exact org slot strings (typeform notifications, toast
  sites forms, the new york times) added as explicit phrases (Option A,
  explicit-phrase over noise-word-tolerance, chosen for a PII gate's
  visible-failure property). probe_from_lines.py rewired to import the
  shared is_allowlisted (it had carried the same blind spot). Re-run across
  all surfaces: 113 -> 2 From-line flags, the 2 being one customer slot
  ("{name-22}, Jonah") correctly redacting. tests/test_redact_allowlist.py,
  11 cases.
- Verification gates 1–4, 6, 7: PASSED. Gate 5 (F5 probe) still pending F5.
- Ingest left **3 model_failed** batch-3 threads (F1 working as designed —
  recorded, not crashed). Diagnose/defer next session.

NOTE on the bare-name limitation surfaced in Session E: `_HEADER_RE`
requires a trailing `<` after the slot, so a From line with a display name
and NO angle-bracket address is not matched by the header pass at all. Not
hit in the current corpus (the 113 flags were all `name <...>` shaped), but
it is a real gap separate from F6. Scope it if a bracket-less customer slot
ever appears.

---

## Rules of engagement (non-negotiable, same as every session)

- **Claude Code edits files only. Hugo runs ALL terminal commands.** No
  background processes, no long-running jobs, no parallel DB access. This
  rule exists because of real past failures (phantom background waits,
  DB-lock collisions).
- **No Anthropic API calls in loops.** The model redaction pass is only
  ever run by Hugo, watched, via `label.py ingest`. Do not script retries
  or batch API calls.
- **PII:** never print, log, commit, or embed a real customer name. Test
  fixtures use placeholder names (e.g. `Jane Stand-In`). All `threads*/`
  folders are gitignored (glob rule added 2026-06-12) and stay local-only.
- **One fix per commit**, each with its own test, committed in the order
  F1 → F2 → F3 → F4. Grader/agent files are NOT touched in this work.
- **Confidence labels** on any claim about expected behavior.

---

## Defect inventory (all evidenced on real data, 2026-06-12)

### D1 — Schema CHECK constraint rejects `model_failed` (BLOCKS INGEST)
`labeling/redact.py` line ~195 returns `status = "model_failed"` when the
model name-pass fails. The `inquiries` table CHECK constraint allows only
`('pending','verified','flagged','names_unredacted')`. First batch-3
ingest crashed with `sqlite3.IntegrityError: CHECK constraint failed` on
the first file (`18da9f17eb7c769d.md`, sorted-first). Session C added the
status; the schema was never widened. Nothing landed: DB confirmed at 128
rows, all `verified`, zero batch-3 rows (`check_batch3_landed.py`,
2026-06-12).

### D2 — `strip_quoted_replies` misses single-line HTML-collapsed chains
`export_threads.py`'s quote stripper is line-based: it cuts at the first
LINE matching a quote marker (`^On .* wrote:` etc.). Gmail collapses some
HTML replies into ONE physical line, so markers appear mid-line and never
match. Evidence: thread `18da9f17eb7c769d` message 3 — the entire quoted
chain survived, including `On Feb 15, 2024, at 8:52 AM, ... wrote:` and
`On Wed, Feb 14, 2024 at 15:26 [customer full name] <{email}> wrote:`.
Quoted chains are where customer names concentrate; this is the primary
name-leak vector in export-stage files.

### D3 — HTML entities never decoded
Same message: `&nbsp;`, `&lt;`, `&gt;` literals throughout, plus a BOM-ish
`\ufeff`. `extract_plain_text`'s HTML fallback does a crude
`re.sub(r"<[^>]+>", "", html)` tag-strip and never calls `html.unescape`.
Garbled text degrades labeling and the agent's eval input.

### D4 — Customer names sit cleartext in export-stage `.md` bodies
Evidence: same thread, message 1 signature (customer full name) and the
D2 chain. DESIGN NOTE, read carefully: body names are killed at INGEST by
the model pass (`redactor_claude.py`), not at export — the exporter's
deterministic layer cannot do names, and the exporter runs in the Google
`.venv` with no Anthropic client. That design STANDS. The fix for D4 is
therefore: (a) D2+D3, which remove the chain text where names concentrate;
(b) containment — `threads*/` gitignore (done 2026-06-12) and local-only
handling; (c) the verification gate confirming names die at ingest. Do
NOT move the model pass into the exporter.

### Hypothesis (moderate confidence, verify cheaply): D1's `model_failed`
on `18da9f17eb7c769d` was CAUSED by the D2/D3 blob — an enormous
single-line HTML mess plausibly times out or confuses the model pass.
If true, fixing D2/D3 at export and re-exporting may make the
`model_failed` disappear on re-ingest. The D1 schema fix is still
required regardless: `model_failed` is a legitimate status and must be
storable, not crash-inducing.

---

## Fix specifications

### F1 — Migration 002: widen the `redaction_status` CHECK (do FIRST)
Write `labeling/migrations/002_add_model_failed_status.py` (the
`migrations/` convention: every schema change traceable, v1 never edited
in place). SQLite cannot ALTER a CHECK constraint; rebuild the table:

1. `PRAGMA foreign_keys=OFF`; begin transaction.
2. Create `inquiries_new`, identical to `inquiries` but with CHECK
   `IN ('pending','verified','flagged','names_unredacted','model_failed')`.
   Read the live schema with `sqlite3 labels.db` / schema.sql first —
   reproduce ALL columns and constraints exactly; do not work from memory.
3. `INSERT INTO inquiries_new SELECT * FROM inquiries;`
4. Drop `inquiries`, rename `inquiries_new` → `inquiries`.
5. Re-create any indexes; `PRAGMA foreign_key_check`; commit;
   `PRAGMA foreign_keys=ON`.
6. Built-in post-checks, hard asserts: 128 rows; status breakdown
   unchanged (128 verified); `labels` FK intact (count of labels rows
   joining to inquiries unchanged, expect 145 label rows total —
   142 pre-Session-D + 3 s9_relabel).
7. Also update `labeling/schema.sql` so a fresh `init` matches the
   migrated DB. Same constraint text in both places.

Execution protocol (Hugo, watched): file-copy `labels.db` →
`labels.db.bak-pre-002` FIRST (rollback is "copy it back"), then
`python migrations\002_add_model_failed_status.py`, then re-run
`check_batch3_landed.py` expecting unchanged counts.

Companion edit in `label.py`: `cmd_status` should count `model_failed`
rows (it currently surfaces only flagged/names_unredacted). The `label`
command already filters to `redaction_status='verified'`, so
`model_failed` rows are correctly un-labelable with no change there.
Verify that claim by reading the code, then state it in the commit.

### F2 — Inline quote-chain stripping (exporter)
In `export_threads.py`, after the existing line-based pass, add an
inline pass that truncates the body at the FIRST occurrence of any of:
- `On <date-ish>, at <time>, <anything> wrote:`  (Apple/iPhone style)
- `On <Weekday>, <Mon> <d>, <yyyy> at <h>:<mm> <anything> wrote:` (Gmail)
- `Sent from my iPhone` / `Sent from my iPad` (when followed by `On ` or
  end-of-text — signature-then-quote pattern)
- `---------- Forwarded message ---------`
Build the regexes against the LITERAL fixture text from
`18da9f17eb7c769d` message 3 (placeholder-swapped), not imagined formats.
Conservative bias: a too-eager cut loses real body text silently —
require the marker to include `wrote:` or the literal forwarded-message
ruler before cutting. Every regex gets a fixture test (F4).

### F3 — HTML decoding (exporter)
In `extract_plain_text`'s HTML fallback: convert block-level tags
(`<br>`, `</p>`, `</div>`) to newlines BEFORE the tag-strip (this also
un-collapses the single-line blobs, making the line-based quote pass
effective again), then strip tags, then `html.unescape()` (stdlib), then
strip zero-width/BOM chars (`\ufeff`). Order matters: unescape LAST so
`&lt;div&gt;` in genuine text doesn't become a strippable tag.

### F4 — Tests (pytest, in `eval/tests/` or `labeling/tests/` — match
whatever the repo already uses; check before creating a new folder)
- Fixture: a sanitized reconstruction of `18da9f17eb7c769d` (structure
  and formats byte-faithful, names/emails replaced with placeholders).
- D2 tests: each inline marker format gets cut; plain bodies with the
  word "wrote" in normal prose do NOT get cut.
- D3 tests: entities decoded, block tags become newlines, BOM stripped.
- F1 test: insert a row with `redaction_status='model_failed'` into a
  temp DB built from the updated schema.sql — must not raise.

### F5 — Body-leak probe (new, deterministic proxies)
`probe_from_lines.py` scans `**From:**` lines only — it was green while
bodies leaked. Names can't be detected deterministically, but their
carriers can. New read-only probe `labeling/probe_body_artifacts.py`
scanning BOTH surfaces (all `threads*/` .md files + DB
`thread_text_redacted`) for: `wrote:` preceded by `On ` in the same line,
`&nbsp;`/`&lt;`/`&gt;`/`&amp;` literals, `Sent from my iP`, and
`Forwarded message`. Report hits per source like probe_from_lines does.
Pass bar on FRESH exports after F2/F3: zero hits. (Legacy folders will
show hits — expected; they are gitignored history, report but don't fail
on them.)

### F6 — Allowlist surname leak (substring match eats full names) [NEW]
`labeling/redact.py`'s `_ALLOWLIST` is a lowercased SUBSTRING match. A
staff/vendor token like `denise` matches anywhere in a display-name slot,
so the deterministic header pass suppresses redaction of the WHOLE slot —
surname included. Evidence (Session D): thread 18da9f17eb7c769d messages
4–5 emitted `**From:** Denise Pihas <{email}>` — the surname `Pihas`
survived because `denise` matched. Harmless for staff (not customer PII),
but the same mechanism leaks any CUSTOMER named Denise / Jonah / Yanni /
Brenna etc.: a cold inbound from a person named e.g. "Denise <lastname>"
would pass through unredacted.

Fix direction (decide at implementation): match the allowlist against the
PARSED display-name token(s), not a raw substring — e.g. allowlist applies
only when the slot, minus the `<...>` address, equals or is fully covered
by allowlisted tokens; a slot with an extra non-allowlisted token (a
surname) does NOT get a free pass and the non-allowlisted token redacts to
{name}. Build against real slot formats via probe_from_lines (the format
inventory it prints). This is a redaction-correctness fix; it gates the
F2/F3 + redact.py commit and the public flip. Add a fixture test: staff
first-name-only slot survives; staff-first-name + surname redacts the
surname; pure org slot (Typeform) survives; customer full name redacts.

This also explains why probe_from_lines reported 0 leaks while a name sat
in the body: the probe shares the allowlist, so it inherits the same
blind spot for allowlisted-token slots. F5's body probe must NOT reuse the
allowlist for the carrier-artifact checks.

---

## Verification gates — growth resumes only when ALL pass

1. Migration 002 applied; `check_batch3_landed.py` shows 128/verified
   unchanged; backup file exists. — **PASSED** (counts held, .bak-pre-002 exists).
2. `pytest` green on the new tests. — **PASSED** (14/14).
3. Hugo deletes the old `threads_batch3\` contents and re-exports Q1 with
   the fixed exporter (same command, `--after 2024/01/01 --before
   2024/04/01 --out threads_batch3 --max 40`). — **PASSED** (40 exported).
4. `probe_from_lines.py`: zero From-line leaks in threads_batch3 (regression
   check on the Session C fix). — **PASSED** (0 leaks, 40 files scanned).
   NOTE: see F6 — this gate is partially blind (shares the allowlist).
5. `probe_body_artifacts.py`: zero hits in threads_batch3. — **PENDING F5**
   (probe not built; manual eyeball used instead this session).
6. Manual eyeball of `18da9f17eb7c769d.md`: message 3 readable, chain
   gone, entities decoded; message 1 signature name still present in the
   .md (EXPECTED — names die at ingest) — then ingest batch 3 and confirm
   the DB row's `thread_text_redacted` contains NO customer names.
   — **PASSED** (message 3 clean; DB row all names -> {name}).
7. `label.py status` runs and reports any `model_failed` rows; if
   `18da9f17eb7c769d` still model-fails after the D2/D3 cleanup, it goes
   to the deferred bucket per the batch-2 precedent, not inline retry.
   — **PARTIAL**: 18da9f17eb7c769d now ingests as `verified` (no longer
   model_fails — confirms the D2/D3-causes-model_failed hypothesis). 3
   OTHER batch-3 threads recorded model_failed; diagnose/defer next session.

BEFORE GROWTH RESUMES, still required: F5 (body probe). F6 and the
F2/F3+redact.py commit are DONE (Session E, commits 0547c76 / 1fa648b).
After F5: diagnose the 3 model_failed threads, then label.

After gates: Session D's growth plan resumes exactly where it stopped —
Q2–Q4 export at `--max 80`, slice-probe-eyeball each, chunked watched
ingest, labeling with the row-22 boundary rule (qualified requires
message 1 to ASSERT an event; capability question with no asserted event
is needs_info).

## Out of scope — do not let the session absorb these
- Typeform/Toast stitched-thread splitting (known exporter defect,
  separately tracked, its own session).
- Any change to `redactor_claude.py` model behavior, prompts, timeouts.
- Anything in `eval/` — agent, grader, loader logic all frozen.
- Public-repo flip (separate decision, separate audit).
