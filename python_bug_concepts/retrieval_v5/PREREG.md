# Scoped-fact retrieval v5 — 2026-10-27

User explicitly requests implementation by copying the old version and committing
it first. Parent baseline committed/pushed as163b58a; COPY_MANIFEST records the
actual copy of retrieval_v2. No paper algorithm is reproduced. V2/default/corpus
and previous outcomes remain frozen. V5's inherited evaluation directory is a
historical baseline copy, not new results; new scores go under `evaluation_v5/`.

Before new scores: add LibCST metadata for source spans/scope/qualified names;
AST value-origin chains with ambiguity recorded unknown; explicit benign guards
and semantic API facts. Match concept/site pairs, preserving unknown candidates.
Candidate representation includes public-contract clause, requires/excludes,
evidence facts, and conditional where/how/what. No invented expected outputs.
No gold/reference/old witness/model judge is available inside retrieval.

Generic rules selected from the preceding research, not new outcome tuning:
- bind fixed extremum initialization to its definition in the same scope;
- prioritize direct API operation sites for normalization, bytes/count domain,
  integer coercion, value/first-position lookup, and positional-domain concepts;
- recognize nonempty guards only for stable builtin-sequence domains, respecting
  branch polarity, assignment/mutation invalidation and lexical scope;
- recognize range(len(sequence)-constant) safe indexing only without mutation;
- a builtin min/max tie preserves first occurrence; do not claim that operation
  violates an explicit first-tie contract;
- public positive examples with equal distinct members/different counts refute a
  requirement that both strings must have equal multiplicities;
- missing/ambiguous scope/type/flow evidence stays unknown, never safe/bug proof.
Do not add per-task IDs/names/constants after observing new scores.

Verification before outcome computation: regressions for scope isolation,
shadowing, Unicode byte columns, branch polarity/mutation, API semantics, flow
ambiguity, unsupported source, provenance and no PUT execution. Pairwise benign/
faulty engineering fixtures are design cases, not independent accuracy evidence.

Then freeze source/config hashes and run existing113 PUT source-only retrieval
with unchanged v2 labels joined afterwards. Report family/site/returned-card label
precision and per-task wins/losses. Old corpus and labels saw these tasks: this is
engineering evaluation, not fresh holdout. Preserve regressions, do not retune
from new score misses. Quality fixture results do not prove all returned cards
true. No new Qwen completion/paid calls/native utility run authorized by this
protocol; old40 utility does not score v5. Public default stays v2 pending review.
