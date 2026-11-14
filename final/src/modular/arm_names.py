"""Dependency-free identifiers shared with the isolated Prefect environment."""
CATALOGUE_ARM_NAMES = (
    "equivalence", "bva_normal", "ep_bva", "decision_table",
    "ep_strong", "bva_robust", "bva_worst_case", "ep_dt_bva",
    "ep_bva_v2", "decision_table_v2",
)

OBLIGATION_ARM_NAMES = ('spec_obligation', 'control_flow_obligation')
ANALYSIS_CALL_CAPS = {'control_flow': 2, **dict.fromkeys(OBLIGATION_ARM_NAMES, 2)}
