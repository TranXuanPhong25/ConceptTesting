# v20_groundedflow_bounded — cpu_v3, 2026-10-15

Parent cpu_v2 preserved:28 fixture checks pass, but independent static audit found analyzer recursion for sources already rejected for reassignment/unbound definitions. No parent inventory/GPU.
Only behavioral change from checked: return unsupported before slice traversal on any validation reason; defensively bound name-definition recursion. Four regression fixtures + one static regression added. Same narrow multiplicity evidence contract, no scope expansion.
