"""
service_options.py — first grounding tool for the Yanni's lead-triage agent.

Purpose: make service-mode availability deterministic instead of sampled.
The v1 agent invented plated service for an 80-guest inquiry. The business
does not sell plated above 25 guests (foundation rule 2.4a). This tool
returns the service modes the agent is permitted to present at a given
guest count. Plated is simply absent from the list above 25, so the model
cannot offer what it is not handed.

Canonical source: foundation rule 2.4 (space/menu bands) + 2.4a (plated cap).
Do not re-derive the rule here; this encodes it.

Bands (option 2 — tool knows nothing about the 30-guest one-off):
  guest_count < 15   -> regular dining, standard service
  15 <= count <= 25  -> plated available (incl. $55 prix-fixe) OR buffet
  count >= 26        -> buffet only

The 30-guest case-by-case one-off (2.4a) lives entirely outside this tool.
It is an operator-manual decision on a specific thread. The agent has no
representation of it and therefore cannot volunteer it.
"""

from typing import TypedDict


PLATED_CAP = 25  # foundation rule 2.4a: plated offered up to 25 guests max


class ServiceOptions(TypedDict):
    guest_count: int
    band: str
    service_modes: list[str]      # the modes the agent MAY present
    plated_available: bool
    requires_operator_escalation: bool  # plated requested above the cap


def resolve_service_options(
    guest_count: int,
    plated_requested: bool = False,
) -> ServiceOptions:
    """Return the service modes permitted at this guest count.

    Args:
        guest_count: number of guests for the event. Must be a positive int.
        plated_requested: whether the customer explicitly asked for plated
            service. Only affects escalation: a plated request above the cap
            sets requires_operator_escalation, it never adds plated to the
            agent-visible modes.

    Returns:
        ServiceOptions. service_modes is the authoritative list the agent
        may present. plated never appears in it above PLATED_CAP.

    Raises:
        ValueError: if guest_count is not a positive integer.
    """
    if not isinstance(guest_count, int) or guest_count < 1:
        raise ValueError(f"guest_count must be a positive integer, got {guest_count!r}")

    if guest_count < 15:
        return ServiceOptions(
            guest_count=guest_count,
            band="under_15",
            service_modes=["regular_dining"],
            plated_available=False,
            requires_operator_escalation=False,
        )

    if guest_count <= PLATED_CAP:  # 15..25 inclusive
        return ServiceOptions(
            guest_count=guest_count,
            band="15_to_25",
            service_modes=["plated", "buffet"],
            plated_available=True,
            requires_operator_escalation=False,
        )

    # guest_count >= 26: buffet only. Plated request escalates, never offered.
    return ServiceOptions(
        guest_count=guest_count,
        band="26_plus",
        service_modes=["buffet"],
        plated_available=False,
        requires_operator_escalation=plated_requested,
    )
