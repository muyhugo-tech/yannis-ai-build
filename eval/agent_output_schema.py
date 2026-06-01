"""
Agent output contract  --  Step 0 of the eval harness.

This file defines the SHAPE of an agent's answer to a single inquiry.
It is the one place where the agent (or a stub standing in for it) and
the eval harness agree on what an output looks like. Nothing downstream
gets built until this is fixed, because the harness reads this shape and
the stubs emit it.

Why a code file and not a doc: prose can describe a shape but cannot
reject a wrong one. This file validates -- hand it a bad output and it
raises an error naming the problem. That is the difference between a
shape we agreed on and a shape that is enforced.

Canonical vocabulary decision (session 4): the qualification status uses
the LABEL vocabulary from 07_label_schema_canonical.md, because 50 labels
are already stored using it and no agent code exists yet. The cheap side
conforms to the expensive side.
"""

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# The status enum: the four allowed qualification decisions.
#
# An Enum is a fixed menu of allowed values. Using anything not on this
# menu is an error -- an invalid decision becomes unrepresentable, the
# same principle the TypeScript submit_qualification tool proved.
#
# These four strings MUST match the qualification_decision enum in
# 07_label_schema_canonical.md exactly, because the harness compares an
# agent's status against a stored label's qualification_decision. If the
# strings differ, every comparison silently fails as a mismatch.
# ---------------------------------------------------------------------------
class QualificationStatus(str, Enum):
    QUALIFIED = "qualified"
    NEEDS_INFO = "needs_info"
    DECLINED = "declined"
    HUMAN_REVIEW = "human_review"


# ---------------------------------------------------------------------------
# The mapping layer.
#
# An agent might phrase a status differently than the label vocabulary
# (e.g. "decline-recommended" from the project overview, or hyphenated
# variants). Rather than forcing the agent to use the exact label words,
# we translate agent-side wording into the canonical status here, before
# any comparison. This is where "two names for one concept" gets
# reconciled -- NOT in the stored labels.
#
# Keys are lowercased agent-side strings. Values are canonical statuses.
# The canonical strings map to themselves so the table is the single
# source of truth for "what counts as a valid incoming status".
# ---------------------------------------------------------------------------
STATUS_ALIASES: dict[str, QualificationStatus] = {
    "qualified": QualificationStatus.QUALIFIED,
    "needs_info": QualificationStatus.NEEDS_INFO,
    "needs-info": QualificationStatus.NEEDS_INFO,
    "declined": QualificationStatus.DECLINED,
    "decline-recommended": QualificationStatus.DECLINED,
    "decline_recommended": QualificationStatus.DECLINED,
    "human_review": QualificationStatus.HUMAN_REVIEW,
    "human-review": QualificationStatus.HUMAN_REVIEW,
}


def normalize_status(raw: str) -> QualificationStatus:
    """Translate any agent-side status string into the canonical status.

    Raises ValueError if the string is not a recognized alias. We raise
    rather than guess: an unrecognized status is a real defect we want
    surfaced loudly, not silently bucketed.
    """
    key = raw.strip().lower()
    if key not in STATUS_ALIASES:
        raise ValueError(
            f"Unrecognized qualification status: {raw!r}. "
            f"Known values: {sorted(STATUS_ALIASES)}"
        )
    return STATUS_ALIASES[key]


# ---------------------------------------------------------------------------
# One flagged edge case in the agent's output.
#
# The overview calls for "flagged edge cases with reasons". The smallest
# honest shape is a short tag plus a human-readable reason. A list of
# these hangs off the main output; an empty list means "no edge cases",
# which is different from "the field is missing".
# ---------------------------------------------------------------------------
@dataclass
class EdgeFlag:
    tag: str       # short machine-ish label, e.g. "allergy_complexity"
    reason: str    # one sentence a human can read


# ---------------------------------------------------------------------------
# The full agent output for ONE inquiry.
#
# Five fields, from 00_project_overview.md:
#   1. fit_score        -- 0 to 100
#   2. status           -- one of the four canonical QualificationStatus
#   3. draft_response   -- the operator-voice reply text
#   4. edge_flags       -- list of EdgeFlag (may be empty)
#   5. confidence       -- per-decision confidence (see note below)
#
# Note on confidence: the overview says "confidence per decision" but
# does not pin the shape. For now confidence is a single float 0.0-1.0
# attached to the status decision -- the decision that actually gets
# graded against labels. If later we grade more sub-decisions, this
# becomes a dict keyed by decision name. Flagged as the one underspecified
# field; this is the minimal honest version, not the final one.
#
# __post_init__ runs automatically right after an AgentOutput is created.
# We use it to validate -- this is the "contract bites" part. A bad output
# fails at creation time with a clear message, not deep in the harness.
# ---------------------------------------------------------------------------
@dataclass
class AgentOutput:
    fit_score: int
    status: QualificationStatus
    draft_response: str
    confidence: float
    edge_flags: list[EdgeFlag] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.status, QualificationStatus):
            raise TypeError(
                f"status must be a QualificationStatus, got {type(self.status).__name__}. "
                f"Use normalize_status() on raw strings first."
            )
        if not (0 <= self.fit_score <= 100):
            raise ValueError(f"fit_score must be 0-100, got {self.fit_score}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if not isinstance(self.draft_response, str):
            raise TypeError("draft_response must be a string")


# ---------------------------------------------------------------------------
# Convenience: build an AgentOutput from a plain dict (e.g. JSON the real
# agent or a stub produced). Runs the raw status through normalize_status
# so callers do not have to know about the alias table. This is the door
# the harness and the stubs both walk through.
# ---------------------------------------------------------------------------
def agent_output_from_dict(d: dict) -> AgentOutput:
    return AgentOutput(
        fit_score=int(d["fit_score"]),
        status=normalize_status(d["status"]),
        draft_response=str(d["draft_response"]),
        confidence=float(d["confidence"]),
        edge_flags=[
            EdgeFlag(tag=str(e["tag"]), reason=str(e["reason"]))
            for e in d.get("edge_flags", [])
        ],
    )


if __name__ == "__main__":
    # A tiny self-check so running this file directly proves it works.
    # Not a real test suite -- that comes later. Just a sanity ping.
    ok = AgentOutput(
        fit_score=80,
        status=normalize_status("decline-recommended"),  # alias -> DECLINED
        draft_response="Thanks for reaching out. Happy to help with your event.",
        confidence=0.7,
    )
    assert ok.status is QualificationStatus.DECLINED
    print("contract OK:", ok.status.value, "| fit", ok.fit_score, "| conf", ok.confidence)
