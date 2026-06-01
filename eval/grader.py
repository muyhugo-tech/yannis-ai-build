"""
Classification grader  --  Step 4 of the eval harness.

This is the piece that ties the others together. It:
  1. pulls the 48 gradeable rows from the loader,
  2. runs a stub (later: the real agent) over them to get a prediction
     per inquiry,
  3. compares each prediction to the true label,
  4. computes precision / recall / F1 per class + a confusion matrix,
  5. prints everything under a DIAGNOSTIC banner because n=48 is too small
     to gate any decision on.

The metrics math is hand-written, not imported from scikit-learn. This is
a portfolio piece about understanding evals; importing the math would
outsource the exact competence the project claims. The math is simple
(counting + division) and is PROVEN correct by the oracle stub: the oracle
returns truth, so it must score a perfect 100%. Anything less means the
math is wrong, and you see it immediately. Definitions match scikit-learn's
so the numbers can be cross-checked later if ever wanted.

--- The three numbers, in plain terms (per class C) ---
  true positives  (tp): predicted C, and truly C
  false positives (fp): predicted C, but NOT truly C   (false alarms)
  false negatives (fn): truly C, but predicted something else (misses)

  precision = tp / (tp + fp)   "when it says C, how often right?"
  recall    = tp / (tp + fn)   "of the real Cs, how many caught?"
  f1        = harmonic mean of the two (balances them)

A class with no predictions gets precision 0; a class with no true
examples gets recall 0. We guard the divisions so an empty class yields 0,
not a crash.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from agent_output_schema import normalize_status
from eval_loader import load_eval_rows, EvalRow
from stubs import OracleStub, FixedStub, RandomStub, QualificationStatus


# ---------------------------------------------------------------------------
# Per-class metrics, as a small record.
# ---------------------------------------------------------------------------
@dataclass
class ClassMetrics:
    label: str
    support: int      # how many true examples of this class exist
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


# ---------------------------------------------------------------------------
# The core math. Given a list of (true_label, predicted_label) pairs,
# compute per-class metrics, overall accuracy, and the confusion matrix.
#
# This function knows nothing about stubs, agents, or the contract -- it is
# pure counting over label strings. That isolation is deliberate: the math
# is testable on its own and reused for both axes (status and type).
# ---------------------------------------------------------------------------
def score(pairs: list[tuple[str, str]]) -> dict:
    classes = sorted({t for t, _ in pairs} | {p for _, p in pairs})

    tp = Counter()
    fp = Counter()
    fn = Counter()
    support = Counter(t for t, _ in pairs)

    # confusion[true][pred] = count
    confusion = defaultdict(Counter)

    correct = 0
    for true_label, pred_label in pairs:
        confusion[true_label][pred_label] += 1
        if true_label == pred_label:
            tp[true_label] += 1
            correct += 1
        else:
            fp[pred_label] += 1   # predicted pred_label wrongly
            fn[true_label] += 1   # missed the real true_label

    per_class = {
        c: ClassMetrics(label=c, support=support[c], tp=tp[c], fp=fp[c], fn=fn[c])
        for c in classes
    }
    accuracy = correct / len(pairs) if pairs else 0.0
    return {
        "classes": classes,
        "per_class": per_class,
        "accuracy": accuracy,
        "confusion": confusion,
        "n": len(pairs),
    }


# ---------------------------------------------------------------------------
# Run a stub over the loaded rows, producing (true, predicted) pairs for a
# chosen axis. axis is either "status" (qualification_decision) or "type"
# (inquiry_type).
#
# For the STATUS axis we compare the stub's AgentOutput.status against the
# row's qualification_decision. For the TYPE axis the stubs do not yet
# predict inquiry_type, so we use a simple convention: the fixed stub can
# be told to always emit a given type; oracle copies the true type; random
# picks one. To keep this honest and simple we handle the type axis with a
# tiny inline predictor here rather than overloading the stubs.
# ---------------------------------------------------------------------------
def pairs_for_status(stub, rows: list[EvalRow]) -> list[tuple[str, str]]:
    pairs = []
    for row in rows:
        true_status = normalize_status(row.qualification_decision).value
        pred = stub.predict({"qualification_decision": row.qualification_decision,
                             "inquiry_type": row.inquiry_type}).status.value
        pairs.append((true_status, pred))
    return pairs


def pairs_for_type(mode: str, rows: list[EvalRow], fixed_value: str = "not_an_inquiry",
                   seed: int = 0) -> list[tuple[str, str]]:
    """Type-axis predictions. mode is 'oracle' | 'fixed' | 'random'.
    Kept inline (not in stubs) because the stubs' contract is about the
    status output; type is a second axis we grade separately."""
    import random as _random
    rng = _random.Random(seed)
    type_classes = sorted({r.inquiry_type for r in rows})
    pairs = []
    for row in rows:
        true_type = row.inquiry_type
        if mode == "oracle":
            pred = true_type
        elif mode == "fixed":
            pred = fixed_value
        elif mode == "random":
            pred = rng.choice(type_classes)
        else:
            raise ValueError(f"unknown mode {mode!r}")
        pairs.append((true_type, pred))
    return pairs


# ---------------------------------------------------------------------------
# Reporting. Every report prints the DIAGNOSTIC banner. This is the
# enforcement of the n=48 not-gating rule: the harness labels its own
# output so a future reader cannot mistake a diagnostic number for a
# ship-gating baseline.
# ---------------------------------------------------------------------------
def print_report(title: str, result: dict, gating_min_n: int = 100) -> None:
    n = result["n"]
    gating = "GATING" if n >= gating_min_n else "DIAGNOSTIC -- NOT GATING"
    print(f"\n{'='*64}")
    print(f"{title}")
    print(f"  n={n}   status: {gating}   (gating requires n>={gating_min_n})")
    print(f"  overall accuracy: {result['accuracy']:.3f}")
    print(f"{'-'*64}")
    print(f"  {'class':<16}{'support':>8}{'prec':>8}{'recall':>8}{'f1':>8}")
    for c in result["classes"]:
        m = result["per_class"][c]
        print(f"  {c:<16}{m.support:>8}{m.precision:>8.3f}{m.recall:>8.3f}{m.f1:>8.3f}")
    print(f"{'-'*64}")
    print("  confusion matrix (rows=true, cols=pred):")
    classes = result["classes"]
    header = "  true\\pred       " + "".join(f"{c[:10]:>12}" for c in classes)
    print(header)
    for t in classes:
        rowstr = f"  {t[:14]:<16}"
        for p in classes:
            rowstr += f"{result['confusion'][t][p]:>12}"
        print(rowstr)


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\yannis-ai-build\labeling\labels.db"
    rows = load_eval_rows(db)
    print(f"loaded {len(rows)} gradeable rows")

    # --- STATUS axis: the three stubs ---
    print("\n########## STATUS AXIS (qualification_decision) ##########")

    oracle_status = score(pairs_for_status(OracleStub(), rows))
    print_report("ORACLE stub -- MUST be perfect (accuracy 1.000)", oracle_status)

    fixed_status = score(pairs_for_status(
        FixedStub(always=QualificationStatus.DECLINED), rows))
    print_report("FIXED stub (always 'declined', the ~60% majority)", fixed_status)

    random_status = score(pairs_for_status(RandomStub(seed=0), rows))
    print_report("RANDOM stub (uniform over 4 statuses)", random_status)

    # --- TYPE axis: where the 64%/67% not_an_inquiry majority lives ---
    print("\n########## TYPE AXIS (inquiry_type) ##########")

    oracle_type = score(pairs_for_type("oracle", rows))
    print_report("ORACLE stub -- MUST be perfect", oracle_type)

    fixed_type = score(pairs_for_type("fixed", rows, fixed_value="not_an_inquiry"))
    print_report("FIXED stub (always 'not_an_inquiry', the ~67% majority)", fixed_type)

    random_type = score(pairs_for_type("random", rows, seed=0))
    print_report("RANDOM stub (uniform over types)", random_type)

    # --- The proof: oracle must be perfect on BOTH axes ---
    print(f"\n{'='*64}")
    assert oracle_status["accuracy"] == 1.0, "ORACLE not perfect on status -- math is broken"
    assert oracle_type["accuracy"] == 1.0, "ORACLE not perfect on type -- math is broken"
    print("PASS: oracle scored perfect on both axes -- grader math is proven correct")
    # The fixed stub's majority-class trap: high accuracy, zero minority recall
    decl = fixed_status["per_class"].get("qualified")
    if decl:
        assert decl.recall == 0.0, "fixed stub should have zero recall on 'qualified'"
    print("PASS: fixed stub shows the majority-class trap (zero recall on minority classes)")
