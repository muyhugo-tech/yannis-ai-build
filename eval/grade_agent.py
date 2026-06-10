"""
grade_agent.py  --  run the REAL agent over the dataset and score it.

This is the payoff. The grader math is already proven correct on stubs
(grader.py's oracle hits 1.000, fixed shows the majority-class trap). This
file swaps the stub for the real agent_v3 and reports the same per-class
metrics, reusing grader.py's score() and print_report() verbatim. Nothing
about the math changes -- only the source of the predictions.

SCOPE: status axis only this session. inquiry_type is graded separately by
the inline predictor in grader.py and is NOT touched here -- the agent does
not emit a type yet, and adding one would be a second variable.

COST/TIME NOTE: this makes 2 API calls per row (reply + forced classify)
over 122 rows = ~244 calls. Real money and real minutes. The status comes
from the SECOND call; the reply call is run because the classifier decides
over the full conversation, exactly as the agent does in production. If you
want a cheaper classify-only pass later, that is a deliberate variable
change with its own baseline, not a quiet optimization.

Run:  cd eval
      python grade_agent.py
      python grade_agent.py  (pass a db path as argv[1] to override default)
Needs: ANTHROPIC_API_KEY in the environment.
"""

import sys

from anthropic import Anthropic

from agent_output_schema import normalize_status
from eval_loader import load_gradeable_inbounds, InboundRow
from grader import score, print_report

# agent_v3, grader, eval_loader, and the schema all live in eval/ alongside
# this file. Run from inside eval/ (cd eval; python grade_agent.py), the same
# way agent_v2.py is run. Flat same-folder imports, no sys.path juggling.
from agent_v3 import qualify


def pairs_for_real_agent(client: Anthropic, rows: list[InboundRow],
                         verbose: bool = True) -> list[tuple[str, str]]:
    """Run the real agent over each row, returning (true, predicted) status
    pairs in the exact shape grader.score() consumes.

    The true label is normalized the same way grader.pairs_for_status does,
    so the comparison is identical to the stub path -- the ONLY difference
    is that the prediction comes from qualify() instead of a stub.
    """
    pairs = []
    for i, row in enumerate(rows, 1):
        true_status = normalize_status(row.qualification_decision).value
        try:
            pred = qualify(client, row.inquiry_text).status.value
        except Exception as e:
            # One bad row must not sink the whole run. Record it as a
            # distinct 'ERROR' prediction so it shows up in the confusion
            # matrix as a visible miss rather than being silently dropped
            # (which would shrink the denominator and inflate accuracy).
            pred = "ERROR"
            if verbose:
                print(f"  row {i}: ERROR -- {type(e).__name__}: {e}")
        pairs.append((true_status, pred))
        if verbose:
            print(f"  [{i:3d}/{len(rows)}] true={true_status:13s} pred={pred}")
    return pairs


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\yannis-ai-build\labeling\labels.db"  # raw string: backslashes are literal
    rows = load_gradeable_inbounds(db)
    print(f"loaded {len(rows)} clean cold inbounds (edge_case_flag=0)")
    print("running the REAL agent (2 API calls per row) -- this takes a few minutes\n")

    client = Anthropic()
    pairs = pairs_for_real_agent(client, rows)
    result = score(pairs)

    print_report("REAL AGENT v3 -- status axis (qualification_decision)", result)

    # Read the per-class table, not just the headline. In the CLEAN-INBOUND
    # set 'declined' is ~61% (37/61), so the majority-class trap pulls toward
    # 'declined': an agent that mostly guesses declined posts ~61% accuracy
    # with poor recall on qualified/needs_info -- the leads it must actually
    # find. human_review has ZERO examples in this set, so its accuracy is
    # UNMEASURED here, not passing. The per-class breakdown is the real read.
    print("\nREMINDER: clean-inbound status baseline for v3. ~61% is the "
          "majority-class FLOOR (always-declined), not a win. Read recall on "
          "qualified and needs_info. human_review is unmeasured (0 examples). "
          "Any 'ERROR' row is a real failure, not rounding.")
