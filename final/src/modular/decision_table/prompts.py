"""Eight steps; detailed validation belongs to the checker."""
GUIDANCE = """Use Decision Table Testing. (1) Find the conditions and the actions the
specification requires. (2) List each condition's values. (3) Form the
combinations and drop the ones that cannot happen. (4) One rule per
combination. (5) Merge rules whose actions are the same, using "-" for a
condition that does not matter. (6) Check for missing or overlapping rules.
(7) Fill in the actions of each rule. (8) Write one input per rule not already
exercised by the existing calls. List the rules in the catalogue."""

COMBINED_GUIDANCE = """Use Equivalence Partitioning, Decision Table Testing and normal BVA together.
Split inputs into classes handled alike, including by kind of result. Build
conditions from those classes and rules from their feasible combinations;
merge only rules with the same ordered actions. Pick typical inputs for rules,
then min, min+1, max-1 and max of class edges, changing one quantity at a time.
You may also add other useful tests. List classes, boundaries and rules in the catalogue."""
