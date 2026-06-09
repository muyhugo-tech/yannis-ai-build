"""
test_plated_absence.py -- the regression guard for the v1 plated bug.

What broke in v1: the agent invented plated dinner service for an 80-guest
inquiry. The business does not sell plated above 25 guests. The service_options
tool now makes plated structurally absent above 25, but the tool being correct
does not prove the AGENT honors it -- the model could still ignore the tool and
say "plated" anyway. This test proves the agent does not.

It calls the real agent (live API call), so it is marked slow. Run it on
purpose before committing, not on every save:

    pytest eval/test_plated_absence.py -m slow

The tool is already covered by its own 18/18 eval. This test covers the one
thing that bug was really about: the model presenting what the tool returns.
"""

import pytest
from anthropic import Anthropic

import agent_v2


@pytest.mark.slow
def test_agent_does_not_offer_plated_at_80_guests():
    """The 80-guest held-out inquiry must produce a draft with no plated service.

    80 guests -> tool band 26_plus -> service_modes ["buffet"]. Plated must be
    absent from the agent's reply. If "plated" appears, the agent ignored the
    tool and the v1 bug is back.
    """
    client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    draft = agent_v2.generate_draft(client)

    assert "plated" not in draft.lower(), (
        "REGRESSION: agent offered plated service for an 80-guest inquiry. "
        "Plated is capped at 25 guests. The agent ignored resolve_service_options.\n\n"
        f"Draft was:\n{draft}"
    )
