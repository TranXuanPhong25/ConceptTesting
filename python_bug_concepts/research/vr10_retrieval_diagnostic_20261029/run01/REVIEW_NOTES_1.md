# Independent semantic review, queue 1

Reviewed only REVIEW_QUEUE_1.json and SEMANTIC_REVIEW_RUBRIC.md. The prior engineering
review exposed the prospective sample and public source construction, but no arm,
rank, score, known-label match or result attribution. No RESULTS, RETRIEVAL,
REVIEW_KEY, sibling grades or target execution was used. Judgments are source
reasoning by a Codex reviewer, not human annotation or formal verification.

All 59 assigned review IDs are graded. Most contradicted nominations lack the
operation or required context altogether: print redirection at ordinary calls,
mutable defaults on signatures without defaults, byte-domain cards on Unicode
operations, and min/max empty-domain cards on joins or set insertion. These are
proposal-confusion judgments, not emitted false bug reports.

Supported judgments require the proposed card's causal mechanism plus a public
contract-valid input class. Empty filtered min without a default, occurrence-count
via set cardinality, byte-count via UTF-8 encoding, case-folded character-set
comparison, and reuse of an earlier occurrence in the zero-sum triple check meet
that requirement. The two triple cards describe the same underlying occurrence
identity mechanism; they must not be counted as two independent mechanisms.

Conservative decisions: the modulo unit-digit proposal is useful to inspect,
but its canonical card describes division-by-ten/leading-prefix confusion, so it
is unknown rather than a supported fault under that exact card. Aggregation-scope
and text-normalization labels are likewise not promoted merely because their
bound expressions participate in a different proven bug. The decoder's isalpha
check is contradicted as a proposed Unicode-domain fault because its stated input
comes from the visible encoder, whose output is confined to a-z.

The occurrence/Unicode/minimum fixtures were inspected in earlier engineering
work and remain exploratory, regardless of these judgments. Root must separate
them from real-task GO evidence and preserve canonical useful-test opportunities
instead of treating every conditional warning as a false alarm.
