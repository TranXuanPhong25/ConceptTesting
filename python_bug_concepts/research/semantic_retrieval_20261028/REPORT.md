# Concept quality and semantic retrieval: design review

Review started2026-10-28, completed2026-10-29. User requested independent agents to assess concept-base quality,
retrieval and the lack of embeddings. Three Codex agents reviewed corpus quality,
retrieval architecture, and experimental evidence separately. Main agent inspected
the cited source and aggregated saved v6 JSON. No new inference, embedding model,
target execution, benchmark, dependency installation or paper reproduction.
This is a proposal, not an implemented retrieval version.

## 2026-10-29 correction after checking integration from another machine

The initial review missed tracked `trickcatcher_linefacts/pipelines/v85_retrievalhybrid`.
After fetch, local main and origin/main both937f498. V85 already places v2 compact
cards plus a source-bound mechanical target inside the v11 two-round/10-spec-oracle
workflow. Thus the omitted-bindings observation below applies to standalone
retrieval_v3 utility only, not to all existing downstream integrations.

V85's adapter selects the first unused ranked v11 fact in the first retrieval
evidence span; otherwise it uses STMT line reachability. This binds a location but
does not establish that the executable gate realizes the card's semantic trigger.
The hybrid controller requests round2 only for missed gates, so a satisfied weak
gate may suppress a useful follow-up; this is a code-supported risk, not yet an
observed failure frequency. V85 uses v2, not v6. Its ignored out/ is absent here,
and latest committed status is a historical54-pair/694-response continuation
launch, without final scoring. No current-process or efficacy conclusion follows.

Revise next-step priority: get latest v85 artifacts; audit retrieval selection,
gate binding and round2 delivery; then isolate v2→v6 vs open-BM25/dense retrieval
under one unchanged integration. Keep existing frozen runs untouched. Concept-base
quality and independent dense recall remain plausible; don't rebuild an integration
that already exists. Initial v7 copy/environment/draft overlay is paused.

## Assessment

Add an independent dense candidate channel, alongside a better evidenced concept
base and source-bound output. The supported diagnosis is limited semantic
generalization, not absence of semantics: v6 already encodes scope, provenance,
operation roles, public-contract heuristics and exclusions. Similarity, conditional
applicability and actual fault confirmation must remain distinct.

### Concrete implementation findings

- `retrieval_v6/engine.py:249`: search ranks only `evidence.items()`, populated by
  structural recognizers/supplemental rules. A dense bonus after this stage cannot
  rescue a concept absent from that pool.
- `engine.py:259`: score is `1000*tier + min(priority,300) + lexical<=15`.
  Precise retains tier>=2; balanced does too when any supported pair exists.
  Existing tiers are heuristic support, not calibrated probabilities or proofs.
- `retrieval_v6/roles.py`: public-contract interpretation uses finite phrase/API
  rules. Paraphrases and alternative realizations are a plausible dense-retrieval
  use case, requiring measurement rather than an assumed improvement.
- `retrieval_v6/applicability.py:9`: nine families have explicit condition lists;
  `:201` supplies a generic contract/operation condition for other families.
  Other semantic rules exist elsewhere, so this is not a count of all supported
  families. Merely adding more prose condition fields would repeat v5.
- `retrieval_v6/engine.py:185`: bound how/what still reuse generic mechanism and
  failure/trigger text; expected output is deliberately unset. The public contract
  is source text, not a verified clause-to-mechanism alignment.
- `retrieval_v3/prompts.py:103`: utility passes only compact card definitions.
  Retrieved source lines and instantiated bindings are not transmitted. V6's
  improved site selection therefore has no demonstrated downstream benefit in
  the existing utility interface.

### Saved-result provenance cross-tab

Computed from `retrieval_v6/evaluation_v6/iter06/RESULTS.json`, joining each
`records[].systems[policy].selected[].concept_id` to original `data/concepts.json`
or v6 `data/extra_concepts.json`; matches use the saved `label_match` flag.
Counts below are cards, not tasks; no outcome was rerun or relabeled.

| Policy | Original132 returned/matched | Extra30 returned/matched |
| --- | ---: | ---: |
| coverage | 61 / 6 | 209 / 92 |
| balanced | 12 / 5 | 114 / 89 |
| precise | 6 / 4 | 76 / 62 |

Most measured frozen-label agreement comes from the semantic extension. This is
not evidence that the original lint concepts are inherently poor: cohort, incomplete
labels and development-informed corpus/rules all affect the distribution. It does
mean that current aggregate hit rates cannot validate all 162 cards equally.

V6 balanced hits all91 labeled families and90 first sites;22 unlabelled tasks are
unknown, not established missing mechanisms. The previous v2 diagnosis that site
binding dominates should not be presented as an unchanged v6 finding.

## Proposed changes

### 1. Evidence-backed mechanism cards

Keep where/how/what, but represent the causal prerequisites explicitly:
required public behavior → transformation/effect → affected output/decision →
distinguishing input class. Attach evidence and supported/contradicted/unknown
status to each bound prerequisite. A generic phrase such as “violates the spec”
does not establish the target-specific connection.

For prioritized mechanisms, curate external real bug/fix exemplars and benign
counterexamples with pinned provenance, separate from benchmark references. Keep
author code unchanged. Examples establish possible applicability, not automatic
applicability to a new target. No such collection or reproduction was run here.

Normalize family versus realization: loss of required multiplicity can occur via
set conversion, boolean presence or one-entry dictionaries. Record specialization
relations instead of treating overlapping cards as independent hypotheses. Loss
of order is a different effect even if it also uses `set`.

### 2. Independent hybrid retrieval

Candidate generation should be the union of structural v6, full-corpus BM25 and
full-corpus dense retrieval. Dense must be able to propose a card even when the
old recognizer has no evidence row. With162 cards, exact vector similarity is
sufficient; a vector database is not needed initially.

Use separate aligned views rather than embedding an entire function/card once:

| Query evidence | Card view |
| --- | --- |
| Public behavior, units, domain, order/count/tie requirements | Required invariant/applicability |
| Local code slice, definitions, guards and consumers | Mechanism/effect and realizations |
| Publicly admissible input classes | Trigger class and observable failure |

Rank fusion is a starting design, not an efficacy claim. Generated query summaries
must preserve their source and uncertainty; do not treat a guessed bug summary as
observed fact. Embeddings can nominate plausible mechanisms; they cannot establish
that a particular semantic requirement is normative.

### 3. Grounded binding after recall

Bind candidate `(concept, site)` pairs to public clauses, code facts and output
dependencies. Keep unsupported mappings unknown; reject a binding only for an
evidenced contradiction under stated assumptions. Do not reuse the old recognizer
as a mandatory eligibility gate for all dense candidates.

Example: `len(set(xs))` is compatible with a lost-multiplicity mechanism, but is
correct when the contract requests the number of distinct values. The observable
requirement distinguishes the cases. Cosine proximity alone cannot do so.

### 4. Transmit the useful evidence to test generation

An optional new packet should contain selected source span, cited requirement,
causal effect, guards/unknowns and distinguishing input class. Keep oracle claims
separate and validate them using the established evaluation protocol. Compare
this packet against generic cards at matched evidence/budget; more text by itself
is not evidence of mechanism value. Retrieval and packet changes need separate
ablations.

## Prior trials and discriminating evaluation

- Python v3 already tried Qwen catalog selection (all titles, details for a small
  structural shortlist): site67 vs v2 74; utility15 vs18 bug tasks. This was not a
  dense embedding experiment. Repeating generic LLM selection is not the new idea.
- Python v5 already added scoped facts/conditions without retrieval gain; v6
  operationalized role/ranking changes and improved site hits. Retain both facts.
- Linefacts v31/v34/v35 tested fault concepts and input templates; the proposed
  causal binding is not justified by simply renaming those templates.
- Linefacts v36 raw CFG and v47/v78 selectors did not establish gains; v50/v63
  show that tool evidence/gates do not automatically resolve normative semantics.

First classify saved failures: missing mechanism / candidate omission / ranking
or gate loss / wrong binding / input failure / oracle failure. An unlabeled task
stays unknown until reviewed. Then use a small, separately frozen mechanism audit
with same-operation/different-contract pairs and different-realization/same-effect
pairs. These test semantic discrimination, not larger sample-size rescue.

Separate corpus and retrieval effects with a2×2 design if implemented:

| | Current retrieval | Independent hybrid retrieval |
| --- | --- | --- |
| Current cards | baseline | embedding/channel effect |
| Revised evidenced cards | corpus effect | interaction |

Freeze candidate budget and use the same binding stage for comparable arms; also
report dense-only and sparse-only candidate coverage as diagnostics. Record
recall-before-binding, evidence-correct top3 bindings, benign confusion/abstention,
and semantic stability under paraphrase. Separate returned risk suggestions from
actual fault assertions; canonical retrieval is not itself bug-report FP rate.

Within the retrieval comparison, **open-corpus BM25+v6 is a required control**
against dense+v6. If dense beats the closed v6 pool but not the open lexical pool,
the gain may come from removing the structural gate rather than embedding
semantics. Test both before attributing an improvement to dense representations.
For the downstream packet, compare generic cards, grounded concept packets and
the same grounded evidence as plain factual hints. This separates concept
organization from the effect of supplying additional information.

Continuation requires dense-only, independently supported recovered mechanisms
or improved semantic discrimination at comparable coverage/budget. More relevant
words, more returned cards, or higher cosine alone do not qualify. If candidates
were already correct and generation/oracle failed, address that downstream loss.
No full benchmark, fine-tuning or paid run is proposed merely to salvage an
unchanged method.
