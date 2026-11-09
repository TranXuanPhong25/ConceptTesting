"""Classical variants alongside the unchanged soft BVA module."""
NORMAL_GUIDANCE = """Boundary Value Analysis is a useful source of test ideas here. For each bounded
quantity (a parameter, or a length, count, position, or parsed value), take
min, min+1, max-1 and max from the specification. Vary one quantity at a time
while the others stay at typical values, plus one all-typical input. When a
limit depends on other parameters, fix them first. You may also add other
useful tests. List the boundaries in the catalogue."""

COMBINED_GUIDANCE = """Use Equivalence Partitioning together with Boundary Value Analysis. First split
the inputs into classes the specification handles the same way, including by
kind of result, and pick one typical input per class. Then test the edges of
those classes: min, min+1, max-1, max, varying one quantity at a time. A value
just past an edge belongs to the neighbouring class; that is fine. You may also
add other useful tests. List classes and boundaries in the catalogue."""

ROBUST_GUIDANCE = """Use robust Boundary Value Analysis for specified out-of-domain behavior.
For each bounded quantity take min-1, min, min+1, max-1, max and max+1;
vary one quantity at a time with the others typical, plus one all-typical input.
Fix dependent context first. For floats use a specification-defined step or
adjacent representable values. You may also add other useful tests.
List the boundaries in the catalogue."""

WORST_CASE_GUIDANCE = """Use worst-case Boundary Value Analysis. For each bounded quantity choose
min, min+1, a typical value, max-1 and max, then combine those choices across
quantities within the input budget. Fix dependent contexts first. For floats use
a specification-defined step or adjacent representable values. You may also add
other useful tests. List the boundaries in the catalogue."""
