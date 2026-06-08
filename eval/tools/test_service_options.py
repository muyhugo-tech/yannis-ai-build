"""
test_service_options.py — eval-first check for the service-mode tool.

The tool's correctness gets a check before it is trusted (eval-first holds
even for tools). The anchor case is the 80-guest plated regression that the
v1 agent eval exposed: the tool must never put "plated" in front of the
agent above 25 guests.

Run: pytest eval/tools/test_service_options.py -v
"""

import pytest

from service_options import resolve_service_options, PLATED_CAP


# --- The regression that put this tool in scope -------------------------

def test_80_guest_plated_regression():
    """The v1 agent offered plated to an 80-guest inquiry. The tool must
    make that impossible: plated absent from service_modes, plated_available
    False. This is the case the whole session exists to fix."""
    result = resolve_service_options(80)
    assert "plated" not in result["service_modes"]
    assert result["service_modes"] == ["buffet"]
    assert result["plated_available"] is False


def test_80_guest_plated_request_escalates_not_offered():
    """Even when the customer explicitly asks for plated at 80, the tool
    escalates to the operator and still does not offer plated."""
    result = resolve_service_options(80, plated_requested=True)
    assert "plated" not in result["service_modes"]
    assert result["requires_operator_escalation"] is True


# --- Band boundaries (rule 2.4 / 2.4a) ----------------------------------

def test_under_15_regular_dining():
    result = resolve_service_options(14)
    assert result["band"] == "under_15"
    assert result["service_modes"] == ["regular_dining"]
    assert result["plated_available"] is False


def test_15_lower_plated_boundary():
    """15 is the lower edge of the plated band."""
    result = resolve_service_options(15)
    assert result["band"] == "15_to_25"
    assert "plated" in result["service_modes"]
    assert result["plated_available"] is True


def test_25_is_last_plated_guest():
    """25 is the cap: plated still available."""
    result = resolve_service_options(PLATED_CAP)  # 25
    assert "plated" in result["service_modes"]
    assert result["plated_available"] is True


def test_26_is_first_buffet_only():
    """26 is the first count above the cap: buffet only, no plated."""
    result = resolve_service_options(26)
    assert result["band"] == "26_plus"
    assert result["service_modes"] == ["buffet"]
    assert result["plated_available"] is False
    assert result["requires_operator_escalation"] is False  # no request made


def test_30_one_off_invisible_to_tool():
    """Option 2: the tool knows nothing about the 30-guest one-off. At 30 it
    behaves exactly like any other 26+ count — buffet only. The one-off is an
    operator-manual decision the agent cannot see and therefore cannot offer."""
    result = resolve_service_options(30)
    assert result["band"] == "26_plus"
    assert "plated" not in result["service_modes"]
    assert result["plated_available"] is False


# --- Input validation ---------------------------------------------------

@pytest.mark.parametrize("bad", [0, -1, 3.5, "20", None])
def test_invalid_guest_count_raises(bad):
    with pytest.raises(ValueError):
        resolve_service_options(bad)


# --- Property: plated never appears above the cap, at any count ----------

@pytest.mark.parametrize("count", [26, 30, 50, 80, 100, 150])
def test_plated_never_offered_above_cap(count):
    result = resolve_service_options(count)
    assert "plated" not in result["service_modes"]
    assert result["plated_available"] is False
