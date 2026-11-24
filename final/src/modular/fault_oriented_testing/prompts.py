"""Fixed short V2 instruction plus separately sourced, non-prescriptive examples."""
import json
from pathlib import Path

EP_BVA_GUIDANCE = (
    "Use Equivalence Partitioning (EP) with normal Boundary Value Analysis (BVA). "
    "Start from specification behaviors and input dependencies.\n"

    """Partition by meaningful rules, result categories and jointly valid combinations,
    rather than numeric ranges alone. Use plausible specification-supported fault
    hypotheses to refine classes; split or merge when a different fault could be hidden.
    """

    """Choose typical representatives that satisfy their class, keeping unrelated values ordinary;
    then add useful class-edge min/min+, max-/max tests, varying one quantity at a time.
    """

    """Check membership and remove redundancy unless tests distinguish different plausible faults.
    Other useful tests are welcome. List classes and boundaries in the catalogue."""
)

DECISION_TABLE_GUIDANCE = (
    "Use Decision Table Testing for behaviors determined by interacting conditions.\n"

    """Derive conditions and ordered actions from the specification; a condition may be
    an input predicate or relation, even when the function has only one parameter.
    Form combinations; distinguish feasible, infeasible and unresolved cases.
    """

    "Use plausible fault hypotheses to notice missing conditions, combinations or priorities.\n"
    "Merge only when ordered actions agree and omitted conditions do not change behavior. "
    'If a PUT may depend on a merged "-" condition, vary just that condition across two feasible '
    "calls in the same rule. Use existing calls for either side and add only missing contrasts.\n"

    """Check gaps, overlaps and representative membership; keep tests for distinct faults.
    Other useful tests are welcome. List the rules in the catalogue."""
)

FAULT_HYPOTHESIS_OUTPUT_NOTE = """Optional class/rule field "fault_hypothesis" is a short plausible implementation mistake \
supported by the specification; use it where it motivates a distinct class or rule. \
Use the existing "covers" labels to connect inputs. This is a hypothesis, not a confirmed bug."""


def soft_example_for(technique):
    path = Path(__file__).with_name('soft_examples.json')
    examples = json.loads(path.read_text())
    return examples[technique]
