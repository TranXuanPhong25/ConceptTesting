"""Dependency-free identifiers shared with the isolated Prefect environment."""
CATALOGUE_ARM_NAMES = (
    "equivalence", "bva_normal", "ep_bva", "decision_table",
    "ep_strong", "bva_robust", "bva_worst_case", "ep_dt_bva",
    "ep_bva_v2", "decision_table_v2",
)
CATALOGUE_CALL_CAPS = {}
ANALYSIS_CALL_CAPS = {'control_flow': 'pending'}


def retained_input_budget(name, initial_budget):
    return initial_budget
