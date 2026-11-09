"""Fixed short guidance from PLAN_TESTING_ARMS.md."""
GUIDANCE = """Equivalence Partitioning is a useful source of test ideas here. Split the
inputs into classes that the specification handles the same way (per parameter,
or for parameters that work together), and also by the kinds of result the
specification describes. Pick one typical input from each class; one input can
cover classes of several parameters. You may also add other useful tests.
List the classes in the catalogue."""

STRONG_GUIDANCE = """Use strong Equivalence Partitioning: split the inputs into classes the
specification handles the same way, including by kind of result. Pick a typical
input for every feasible combination of input classes across partitions.
You may also add other useful tests. List the classes in the catalogue."""
