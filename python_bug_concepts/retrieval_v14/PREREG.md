# VR14 concept-template query prototype — 2026-10-30

User approved the proposed three-family prototype: filtering/preservation,
multiplicity, search-result/indexing. This is our experimental representation,
not a ConceptCoder reproduction, trained bottleneck, or public-default promotion.

Prior work: vr10dense added no reviewed supported bindings; vr11/13 pruned
operation mismatches but lost one known site. vr8/9/12 changed gates/retention,
not the upstream query representation; no demonstrated applicability benefit.
OBS/REQ/TEST labels were already proposed. The concrete change here is an
extracted neutral concept instance with source-bound roles/relations BEFORE
retrieval, used to query and bind partitions from a small template KB.

Scope: nine neutral templates across three families and neighboring operations.
All arms use identical KB, copied vr13 SQLite FTS5 BM25/tokenizer, candidate cap3,
same bounded extractor and binder, max2048 query characters, one query/function.
No new embedding/model/API call; no claim versus pretrained dense encoders.
Arms: raw(source+docstring); concepts(names/properties without relation text);
relations(the same concepts plus explicit producer/consumer role relations).
Candidate retrieval precedes binding; unbindable candidates remain reported,
not silently replaced. An empty structured query abstains, never falls back raw.

OBS is code structure/conditional local semantics, not proof of a defect or a
whole-program guarantee. Concepts also occur in correct programs. Slot evidence
must include source spans; source identity is stable by source hash+span. Unknown
receiver domains/alias flow/unsupported control flow stay explicitly unknown.
Support is restricted to identity comprehensions, simple set/len/Counter calls,
text replacement/search with recorded receiver assumptions, and bounded lexical
assignment flow to subscript. No target program is executed.

REQ extraction is deliberately narrow: only explicitly recognized standalone
public-docstring directives carry a quoted requirement cue; all other requirements
remain unknown. Cues are unverified interpretations, never oracle values or
hard filters. Input partitions describe both predicate outcomes and mixed/repeated
inputs; coverage is not defined as making a suspected bug predicate true.

Validate parser/flow/binding/shadowing/unknown boundaries with authored engineering
fixtures. Freeze implementation/templates/fixtures and obtain independent read-only
review before diagnostic outcomes. The same authored cases are development checks,
not an unbiased retrieval benchmark. Include benign and unsupported cases; score
concept presence and exact slot relations separately from fault truth.

After freeze: run raw/concepts/relations on fixed fixtures; report candidate recall,
correct-template presence after binding, false bindings, unknowns, relation matches,
partition output and query truncation. Also run a source-only census over the113
saved v85 prepared PUTs, selecting none by old scores. This is unlabeled extraction
coverage and paired output comparison, not bug detection or supported-binding
precision. Save task51 as an exposed illustrative walkthrough, never a heldout win.
No canonical/reference decoding, generation, PUT execution, or oracle scoring.

Success at this stage means usable evidence-backed instances/partitions and faithful
uncertainty, not a chosen retrieval percentage. Report null/negative arms as-is.
No automatic Qwen/full113testgen, dense comparison, vr15, or default promotion.

Implementation clarification before freeze/outcomes: the concepts arm excludes
the composite search-position-indexing instance from query text (the binder still
sees all instances in every arm). Relations arm adds composite concept text and
edge text. This contrasts primitive versus relational representation, not an
isolated effect of punctuation/JSON serialization. Both use exactly one capped
query, not extra query votes. Fixed fixtures have at most one instance per kind;
labels name all expected kinds and exact role expressions. Predictions are sealed
before joining fixture labels; labels are not inputs to extract/search.

## Amendment 1 — independent review, before freeze/outcomes (2026-10-30)

Six correctness issues were found using extract-only adversarial snippets, not
diagnostic outcomes. Resolver now abstains inside loop/try/with/match contexts;
parameter recognition requires its qualified symbol (not a comprehension shadow).
Only subscript loads with a known literal/annotated sequence domain are bound.
Text replacement requires a string domain; Counter occurrence aggregation requires
a known non-mapping sequence domain. Unknowns remain explicit. These restrictions
can reduce census coverage and are not relaxed based on task51 or other outcomes.

Two positive development fixtures now state their necessary domains explicitly:
Counter's argument `xs: list`, direct indexing's receiver `s: str`. No case was
removed. Relation labels now include producer/consumer kind and source expression,
predicate and evidence expressions; exact binding requires both slots and relations.
Expected/exact/missing-or-incorrect edges and relation errors are reported separately.
Seven adversarial engineering tests cover the review fixes and relation scoring.
The diagnostic reserves its output directory atomically and never overwrites it.
Inherited BM25 query tokenization keeps at most 128 unique terms, equally in all arms;
the 2,048-character limit alone does not describe the full query budget.

Amendment 2 (2026-10-30, still before outcomes): final review caught Python 3.11
exception groups (`TryStar`) outside the control-flow boundary. Both use and
chosen definition now reject unsupported contexts; one regression test added.
Counter instances also record their non-mapping iterable domain assumption.
First candidate freeze was rejected and retained in `review/INITIAL_FREEZE.json`.
