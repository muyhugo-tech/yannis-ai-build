"""
Stub agents  --  Step 1 of the eval harness.

A stub is a FAKE agent: it returns outputs in the correct shape (the
AgentOutput contract from Step 0) but does not actually reason. Stubs
exist to test the GRADER, not the agent. We point the grader at fakes
whose behavior we already know; if the grader reports what we predicted,
the grader is trustworthy. Only then do we believe what it says about a
real agent. This is the stub-first commitment.

Three stubs, each testing a different property the grader must have:

  OracleStub  -- cheats: returns the correct answer every time.
                 Grader MUST score it perfect. If not, the grader or the
                 label-comparison is broken.

  FixedStub   -- always says "not_an_inquiry" (the 64% majority class).
                 Grader should show ~64% accuracy BUT near-zero recall on
                 every other class. This exposes the majority-class trap:
                 a lazy agent must NOT look good.

  RandomStub  -- picks a valid status at random.
                 Grader should produce a messy, non-degenerate result that
                 moves when output changes. Proves nothing is hardcoded.

Each stub takes a labeled inquiry and returns an AgentOutput. The "inquiry"
here is just the stored label row (a dict) -- the stubs only need the
fields they pretend to predict. The oracle peeks at the true answer; the
others ignore it.
"""

import random

from agent_output_schema import (
    AgentOutput,
    QualificationStatus,
    normalize_status,
)


# The four statuses as a plain list, for the random stub to choose from.
ALL_STATUSES = list(QualificationStatus)


# ---------------------------------------------------------------------------
# A stub takes one labeled row (a dict from labels.db) and returns an
# AgentOutput. We keep a tiny shared helper to build a valid output so the
# three stubs differ only in the ONE thing each is testing -- the status
# they choose -- and are otherwise identical valid outputs.
# ---------------------------------------------------------------------------
def _make_output(status: QualificationStatus, *, fit_score: int, confidence: float) -> AgentOutput:
    return AgentOutput(
        fit_score=fit_score,
        status=status,
        draft_response="(stub response -- not real text)",
        confidence=confidence,
    )


class OracleStub:
    """Returns the label's true qualification_decision verbatim.

    This is a cheater. The grader MUST score it perfect. It is the
    strongest test: known-correct input must yield a perfect score, or
    the comparison machinery is wrong.
    """

    name = "oracle"

    def predict(self, label_row: dict) -> AgentOutput:
        true_status = normalize_status(label_row["qualification_decision"])
        # high score / high confidence: it "knows" it is right
        return _make_output(true_status, fit_score=90, confidence=1.0)


class FixedStub:
    """Always predicts the same status, regardless of input.

    Default is the dataset's majority class. The grader should show high
    accuracy but near-zero recall on the other classes -- the proof that
    the grader does not reward a lazy majority-guesser.
    """

    name = "fixed"

    def __init__(self, always: QualificationStatus = QualificationStatus.HUMAN_REVIEW):
        # NOTE: the 64% majority is in inquiry_type (not_an_inquiry), a
        # DIFFERENT field from qualification_decision. For the STATUS axis
        # there is no single dominant class, so the "always" default here
        # is just a fixed pick. The majority-class trap is demonstrated on
        # the inquiry_type axis in the harness, where not_an_inquiry IS 64%.
        # Flagged so this is not mistaken for "status is 64% one value".
        self.always = always

    def predict(self, label_row: dict) -> AgentOutput:
        return _make_output(self.always, fit_score=50, confidence=0.5)


class RandomStub:
    """Picks a valid status uniformly at random.

    Seeded so runs are reproducible -- an eval that changes answer every
    run is useless for proving the grader is stable. Same seed, same
    outputs, every time.
    """

    name = "random"

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)

    def predict(self, label_row: dict) -> AgentOutput:
        status = self._rng.choice(ALL_STATUSES)
        return _make_output(
            status,
            fit_score=self._rng.randint(0, 100),
            confidence=round(self._rng.random(), 2),
        )


if __name__ == "__main__":
    # Sanity ping: feed each stub one fake labeled row and print what it
    # returns. Proves all three emit valid AgentOutputs. Not a real test.
    fake_row = {"qualification_decision": "qualified", "inquiry_type": "private_event"}

    for stub in (OracleStub(), FixedStub(), RandomStub(seed=42)):
        out = stub.predict(fake_row)
        print(f"{stub.name:7s} -> status={out.status.value:13s} fit={out.fit_score:3d} conf={out.confidence}")
