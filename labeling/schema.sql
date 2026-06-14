-- Yanni's Lead Triage — labeling store
-- Schema v1. Mirrors 07_label_schema_canonical.md.
-- Three tables per 04_data_pipeline.md: inquiries (source), labels (truth), agent_outputs (predictions).
-- Enum CHECK constraints make an invalid label unrepresentable at the DB layer
-- (same principle as Step 3: contract underneath, prose on top).
--
-- PROPOSED v1 AMENDMENT, pending operator sign-off:
--   'unknown' added to channel and inquiry_type so the unknown-default discipline
--   has a representable value. If rejected, drop 'unknown' from those two CHECKs
--   and decide how a labeler records "could not determine channel/type".
--
-- AMENDMENT 2026-06-12 (migration 002): 'model_failed' added to the
-- redaction_status CHECK. labeling/redact.py (Session C) returns this status
-- when the model name-pass fails; the constraint was never widened to match,
-- crashing the first batch-3 ingest. model_failed rows are blocked states
-- like 'flagged' / 'names_unredacted': stored, surfaced by `label.py status`,
-- un-labelable until re-redacted. Existing DBs: run
-- migrations/002_add_model_failed_status.py. Fresh init from this file
-- matches the migrated shape.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. inquiries: immutable, redacted source. One row per exported thread.
--    Raw .md stays on disk (gitignored). Only redacted text lands here.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inquiries (
    inquiry_id           TEXT PRIMARY KEY,           -- thread-id derived
    thread_id            TEXT NOT NULL,
    source_path          TEXT NOT NULL,              -- path to raw .md, for re-redaction
    subject_redacted     TEXT,
    message_count        INTEGER,
    date_range_start     TEXT,                       -- ISO 8601, from frontmatter
    date_range_end       TEXT,
    thread_text_redacted TEXT NOT NULL,              -- what the labeler reads
    redaction_status     TEXT NOT NULL DEFAULT 'pending'
        CHECK (redaction_status IN ('pending','verified','flagged','names_unredacted','model_failed')),
    redaction_findings   TEXT,                       -- JSON: residual structured-PII hits if flagged
    ingested_at          TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 2. labels: the canonical schema. Ground truth for the eval harness.
--    Versioned (schema_version). FK to inquiries. Multiple labels per inquiry
--    allowed (relabels), most recent labeled_at wins downstream.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS labels (
    label_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inquiry_id            TEXT NOT NULL REFERENCES inquiries(inquiry_id),
    schema_version        TEXT NOT NULL DEFAULT 'v1',

    received_at           TEXT,                       -- ISO 8601; computed from frontmatter at ingest
    channel               TEXT NOT NULL DEFAULT 'unknown'
        CHECK (channel IN ('direct_email','typeform','web_form','phone_followup','referral','other','unknown')),
    inquiry_type          TEXT NOT NULL DEFAULT 'unknown'
        CHECK (inquiry_type IN ('catering','private_event','general','not_an_inquiry','unknown')),
    language              TEXT NOT NULL DEFAULT 'en'
        CHECK (language IN ('en','es','mixed')),
    group_size            INTEGER,                    -- null = not stated (unknown-default)
    lead_time_days        INTEGER,                    -- null = not derivable
    date_specificity      TEXT NOT NULL DEFAULT 'no_date'
        CHECK (date_specificity IN ('firm_date','flexible','no_date')),
    budget_signal         TEXT NOT NULL DEFAULT 'absent'
        CHECK (budget_signal IN ('explicit','implied','absent')),
    budget_amount         INTEGER,                    -- null unless budget_signal != absent
    budget_basis          TEXT
        CHECK (budget_basis IS NULL OR budget_basis IN ('per_person','total','unspecified')),
    menu_tier_fit         TEXT NOT NULL DEFAULT 'unknown'
        CHECK (menu_tier_fit IN ('entry','mid','premium','mixed','unknown')),

    qualification_decision TEXT NOT NULL DEFAULT 'human_review'
        CHECK (qualification_decision IN ('qualified','needs_info','declined','human_review')),
    decision_reasoning    TEXT,                       -- 1-3 sentences, operator-written
    response_sent         TEXT,                       -- redacted full text or summary
    response_latency_hours INTEGER,                   -- null = not derivable

    outcome               TEXT NOT NULL DEFAULT 'unknown'
        CHECK (outcome IN ('booked','no_response','declined_by_lead','cancelled','unknown')),

    friction_points       TEXT NOT NULL DEFAULT '[]', -- JSON array of tags
    language_patterns     TEXT NOT NULL DEFAULT '[]', -- JSON array of tags
    edge_case_flag        INTEGER NOT NULL DEFAULT 0 CHECK (edge_case_flag IN (0,1)),
    edge_case_reason      TEXT,                       -- required if edge_case_flag = 1 (enforced in app)

    unresolved_fields     TEXT NOT NULL DEFAULT '[]', -- JSON array: fields the labeler could not determine
    labeled_at            TEXT NOT NULL,
    labeled_by            TEXT NOT NULL DEFAULT 'hugo',
    batch_id              TEXT,

    -- edge_case_reason must exist when flagged
    CHECK (edge_case_flag = 0 OR edge_case_reason IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_labels_inquiry ON labels(inquiry_id);
CREATE INDEX IF NOT EXISTS idx_labels_batch   ON labels(batch_id);

-- ---------------------------------------------------------------------------
-- 3. agent_outputs: eval-run predictions. Defined per 04; UNUSED until the
--    eval harness exists. Here so the labels-vs-predictions comparison has a
--    home and the schema is not retrofitted later.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_outputs (
    output_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inquiry_id             TEXT NOT NULL REFERENCES inquiries(inquiry_id),
    run_id                 TEXT NOT NULL,
    agent_version          TEXT NOT NULL,
    qualification_decision TEXT
        CHECK (qualification_decision IS NULL OR qualification_decision IN ('qualified','needs_info','declined','human_review')),
    decision_reasoning     TEXT,
    response_draft         TEXT,
    confidence             TEXT
        CHECK (confidence IS NULL OR confidence IN ('high','moderate','low','unknown')),
    created_at             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outputs_run ON agent_outputs(run_id);
