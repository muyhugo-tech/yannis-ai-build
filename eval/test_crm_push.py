"""
test_crm_push.py -- contract-shape tests for crm_push. SYNTHETIC DATA ONLY.

No network: _post is monkeypatched. Live-contract verification is the
smoke test (see STATE Session-CRMv0), not pytest. No real inquiry text,
name, or thread URL may ever appear in this file.
"""

import pytest

import crm_push


SYNTH_URL = "https://mail.google.com/mail/u/0/#inbox/SYNTHETIC-PYTEST"


# --- build_lead_payload: the field mapping ---

def test_whitelist_drops_unknown_none_empty():
    payload = crm_push.build_lead_payload({
        "contact_name": "Test Synthetic",
        "guest_count": None,
        "company": "",
        "bogus_field": "must be dropped",
        "shadow": True,
        "source": "forged",
    })
    assert payload == {"contact_name": "Test Synthetic"}


def test_known_fields_pass_through():
    fields = {
        "contact_name": "Test Synthetic",
        "contact_email": "synthetic@example.com",
        "guest_count": 30,
        "requested_date": "2026-09-01",
        "message": "synthetic inquiry body",
        "gmail_thread_url": SYNTH_URL,
    }
    assert crm_push.build_lead_payload(fields) == fields


def test_missing_contact_name_exits():
    with pytest.raises(SystemExit):
        crm_push.build_lead_payload({"message": "no name present"})


# --- push_lead: response handling ---

def _patch_post(monkeypatch, status, body):
    calls = []

    def fake_post(url, key, payload):
        calls.append((url, payload))
        return status, body

    monkeypatch.setattr(crm_push, "_post", fake_post)
    monkeypatch.setattr(crm_push, "_config",
                        lambda: ("https://synthetic.invalid", "synthetic-key"))
    return calls


def test_push_lead_201_returns_event_id(monkeypatch):
    calls = _patch_post(monkeypatch, 201,
                        {"event": {"id": "synthetic-event-id"}})
    eid = crm_push.push_lead({"contact_name": "Test Synthetic",
                              "gmail_thread_url": SYNTH_URL})
    assert eid == "synthetic-event-id"
    assert calls[0][0].endswith("/api/agent/leads")


def test_push_lead_409_returns_existing_id(monkeypatch):
    _patch_post(monkeypatch, 409,
                {"error": "duplicate_thread",
                 "event_id": "existing-id", "status": "lead"})
    assert crm_push.push_lead({"contact_name": "Test Synthetic",
                               "gmail_thread_url": SYNTH_URL}) == "existing-id"


def test_push_lead_400_exits(monkeypatch):
    _patch_post(monkeypatch, 400, {"error": "validation"})
    with pytest.raises(SystemExit):
        crm_push.push_lead({"contact_name": "Test Synthetic"})


# --- push_draft ---

def test_push_draft_201_returns_draft_id(monkeypatch):
    calls = _patch_post(monkeypatch, 201,
                        {"draft": {"id": "synthetic-draft-id"}})
    did = crm_push.push_draft("synthetic-event-id", "Synthetic draft body.")
    assert did == "synthetic-draft-id"
    assert calls[0][0].endswith("/api/agent/events/synthetic-event-id/drafts")
    assert calls[0][1] == {"body": "Synthetic draft body."}


def test_push_draft_404_exits(monkeypatch):
    _patch_post(monkeypatch, 404, {"error": "not_found"})
    with pytest.raises(SystemExit):
        crm_push.push_draft("nonexistent-id", "Synthetic draft body.")


def test_push_draft_empty_body_exits():
    with pytest.raises(SystemExit):
        crm_push.push_draft("synthetic-event-id", "")


def test_push_draft_over_20000_exits():
    with pytest.raises(SystemExit):
        crm_push.push_draft("synthetic-event-id", "x" * 20001)
