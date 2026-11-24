"""Dependency-free identifiers shared with the isolated Prefect environment."""
CATALOGUE_ARM_NAMES = (
    "ep_bva_v2", "decision_table_v2",
)
VF3_MEASURED_ARM_NAMES = (
    "ep_bva_vf3_measured", "decision_table_vf3_measured",
)
CATALOGUE_CALL_CAPS = {name: 2 for name in VF3_MEASURED_ARM_NAMES}
ANALYSIS_FAMILY_COUNTS = {'control_flow': 1}


def generation_call_cap(arm):
    if arm in ANALYSIS_FAMILY_COUNTS:
        return 'pending'
    return CATALOGUE_CALL_CAPS.get(arm, 0 if arm == 'pynguin' else 1)


def retained_input_budget(name, initial_budget):
    return initial_budget + 10 if name in VF3_MEASURED_ARM_NAMES else initial_budget
