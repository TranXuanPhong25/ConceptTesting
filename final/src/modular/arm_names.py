"""Dependency-free identifiers shared with the isolated Prefect environment."""
VF3_HYBRID_ARM_NAMES = (
    "ep_bva_vf3_hybrid",
    "decision_table_vf3_hybrid",
)
CATALOGUE_ARM_NAMES = VF3_HYBRID_ARM_NAMES
VF3_STRUCTURED_ARM_NAMES = VF3_HYBRID_ARM_NAMES
CATALOGUE_CALL_CAPS = {name: 2 for name in VF3_HYBRID_ARM_NAMES}
ANALYSIS_FAMILY_COUNTS = {"control_flow": 1, "control_flow_4tool": 1}


def generation_call_cap(arm):
    if arm in ANALYSIS_FAMILY_COUNTS:
        return "pending"
    return CATALOGUE_CALL_CAPS.get(arm, 0 if arm == "pynguin" else 1)


def retained_input_budget(name, initial_budget):
    if name in ANALYSIS_FAMILY_COUNTS:
        return "pending"
    if name in VF3_HYBRID_ARM_NAMES:
        return initial_budget + 20
    return initial_budget
