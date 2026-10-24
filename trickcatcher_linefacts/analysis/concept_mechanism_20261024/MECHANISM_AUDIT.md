# Concept mechanism audit — execution report, 2026-10-24

**P0/P1 complete; P2 contract documented and reviewed. No positive gate for a new generic concept-guided generator.** This is the execution of `PLAN_CONCEPT_MECHANISM_20261024.md` after the user said “làm đi”. Existing v50/v53 work is now reconciled/evaluated; conditional P3–P5 were not activated because the required mechanism signal is absent.

**What was done**

- Verified local v50 source/dependency/prepared/rubric/approval and v43/v40 parent integrity using the exact pinned interpreter; independently matched generation inventory.
- Independently reviewed all8initial+16final v50 raw responses, including rejected/unknown items and prose, under the frozen rubric. Audited all24 completion attempts and25 metadata requests.
- Reviewed v53 source/protocol, all72original answer transcripts and prompt/answer hashes. Ran the original CPU scorer on the existing answers with reviewed provenance guards, then independently verified totals, gates and full acceptance masks from cached outputs.
- Independently checked all32,311reference rows for completeness, source/input mapping, parseability and unresolved execution failures.
- Reproduced all54 v34 concept confirmed labels and the10 detection-discordant task pairs using saved caches; reviewed every v49 defn/brute detection discordant and all-task v47 results. Read v7/v11/v35/v52/v54 reports with explicit scope limits.
- Produced331structured rows:43v34 task/arm summaries,66v47selector rows,66v49oracle rows,24v50reply-stage rows and132v53filter rows. Candidate-level semantic obligation coverage is unknown when not logged; these summaries are not331independent experiments.
- Wrote an operational concept contract and reviewed it independently. This is an evaluation definition, not a new implemented method or efficacy result.

All new work uses local source, saved transcripts/caches and CPU execution of existing checks. No new model/HTTP calls, paid API use, paper reimplementation, endpoint activity or held-out evaluation was initiated. Original frozen source/answers and old scientific gates are unchanged.

**Decisive results**

| Question | Evidence | Decision |
|---|---|---|
| Does repaired v50 feedback add semantic episode successes? |0tool-onlywins/0raw-onlylosses; E8failsboth. Strict2/8each; label-neutral3/8each | Registered NO-GO |
| Does v53 typed validity concept beat open extraction? | Both catch12,842/12,842invalid, reject0valid/0exposing; margin0 vs+.10 | Registered not promising |
| Does taxonomy beat untyped line-by-line extraction? | Concept/lines/open full masks exactly identical on32,311rows | Report-only null |
| Does validity extraction improve saved tests? | Sonnet FA56→0, Qwen145→108,0confirmedtasks lost/gained in all3model-filterarms | Useful engineering, no concept-specific advantage |
| Are v34 wins only witness replay? |16confirmed tests in8wins,0reuse selected concept inputs | No; semantic causal use remains unknown and evidence is unequal |
| Does v49 show literally no possible treatment effect? | Two extra tasks through usable-program yield; registered gate fails | Keep NO-GO; yield remains a plausible mediator, not proof of taxonomy |

V53's extra9Qwen/36Sonnet confirmed assertions result from cap20refill, not new task detection or generated inputs. Perfect validator agreement applies only to the fixed decisive universe. No universal soundness claim is justified. The numeric-only baseline catches1,854invalid inputs (14.44%); it already calls repaired v48 code, so old v44 parser counterexamples are not an explanation of this result.

**What the old criticism gets right, and what it misses**

The criticism of narrow vocabularies, shallow mutation abstractions, missing joint constraints and uneven evidence is supported in the named implementations. However, tool-computed facts can satisfy the user's concept definition. Round-robin hint selection is a weak policy, not proof that the facts lack semantic meaning. V47 has task semantics in its context, so random-like selection is not logically inevitable. Strong-writer pilot ceilings do not establish universal redundancy of concepts.

The most concrete v50 failure is normative-status confusion: a spec-required relation may be marked rejected/unknown because the buggy code violates it, while agreement on an undefined rule in E8 is treated as justification. The frozen prompt already explicitly instructs the opposite. Repeating the same instruction, changing labels or repairing the old all-or-nothing admission again is not a new mechanism.

The strongest new engineering evidence is validity extraction: all three prompt styles handle the sampled domain well and remove invalid-input Sonnet alarms. Because open and untyped extraction already do so, the taxonomy itself carries no demonstrated extra information or useful decision change in this study.

**Gate decisions and work stopped**

| Candidate direction | Gate / action |
|---|---|
| More v34/v35 template/ranking runs | STOP: existing ceiling and attribution limits; no changed mechanism |
| Same v47 menu selector with new labels | STOP: no new discriminatory evidence identified |
| Repeat “spec truth differs from observed code” in v50 | STOP: already in frozen prompt; no tool-only semantic gain |
| RANGE/RELATION/STRUCTURE validity taxonomy | STOP current treatment under registered v53 rule; keep extraction engineering result |
| New generic semantic-contract input generator | G1 not met: no supported mechanism yet links correct task binding to better obligation realization and new discoveries vs equal raw evidence |
| Joint construction respecting verified constraints | Concrete engineering hypothesis, not yet tested as concept contribution; requires a separate prospective protocol and relation/coverage controls |
| Feasible oracle enumeration suggested by v52task65 | Concrete oracle-side mechanism only; cannot substitute for input-generation evidence |
| Fresh-cohort confirmation or54-call diagnostic | Not activated; prerequisite concept mechanism gate failed |

This is a research decision supported by the gates, not a missing endpoint, quota or user permission. No larger N/K/model sweep was launched to rescue the null treatments. V53's original fallback favors open extraction over the numeric tool on this universe; Stage2 remains a separate unregistered experiment. A later changed hypothesis needs evidence and a prospective design rather than relabeling these results.

**What a future implementation must demonstrate**

The reviewed `CONCEPT_CONTRACT.md` requires a reusable relation, correct typed task binding, justified preconditions, measured test gap and executable obligation. Spec grounding, finite observations and fault hypotheses have separate statuses. PUT disagreement does not reject a justified requirement; PUT agreement does not justify an invented requirement.

An implementation must show valid generated inputs realize the obligation, and that this change yields confirmed discoveries at a matched budget with an independent oracle. Raw evidence, equivalent semantic prose, structured concepts, direct generation and witness-only need their appropriate controls. Typed labels need not outperform equivalent semantic prose to show semantic-content benefit, but unchanged behavior vs raw evidence does not establish incremental concept utility.

These are admissibility/evaluation requirements shared with earlier v7/v26/v40/v43 work, not claimed novelty. No general-purpose engine or per-task answer vocabulary was built in this audit.

**Reproducibility and limits**

Entry points: `inventory.py`, `HISTORICAL_build.py`, `audit_references.py`, `run_v53_score.py`, `verify_v53_postscore.py`, `build_matrix.py`. Analysis scripts read cached artifacts; only the reviewed scoring wrapper executes existing generated checks through the original sandbox. Exclusive output files intentionally refuse overwriting earlier verification snapshots. Reuse existing reports when repeating an audit instead of launching another scorer.

Primary evidence: `ARTIFACT_INVENTORY.json`, `REFERENCE_INTEGRITY.json`, `V50_SEMANTIC_REVIEW.{md,json}`, `V50_TRANSPORT_AUDIT.json`, `V53_PROTOCOL_INVENTORY.json`, `V53_SCORING_REVIEW.md`, `V53_POSTSCORE_VERIFICATION.json`, `V53_POSTSCORE_REVIEW.md`, `HISTORICAL_MECHANISM_ROWS.json`, `MECHANISM_MATRIX.jsonl`. All references are relative to this folder unless an original run path is given.

Not every historical source/freeze was independently reverified; those limits are explicit in the historical report. V34 causal semantic use cannot be reconstructed from missing obligation logs. V50 uses seen authored fixtures and one independent primary semantic pass, with partial masking and label-neutral sensitivity; it is not statistical generalization evidence. V53 has24problems/33PUTs on a fixed dev input distribution, with12PUTtasks containing no invalid candidate. Hidden-reference data were used only for evaluation; they were not exposed to the original checker writers.

The durable outcome is a verified negative result for the current extra concept treatments, a useful validity baseline, and a precise contract for what remains unproven. No positive concept efficacy claim is made.
