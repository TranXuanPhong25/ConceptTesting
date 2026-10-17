# v23 concept/hypothesis diagnostic — CPU and clean-context review

2026-10-17. User requested a direct copy of the best pipeline, a small mechanism
diagnostic, clean-context audit, standard libraries where suitable, and an optional
small-model concept-use probe. Later explicitly authorized the Qwen endpoint run.

`pipelines/v23_concepthyp` copies all51 v7 source/resource files; PARENT.json records
hashes and parent commit. Parent hashes rechecked unchanged. Six interface/resource
ports from frozen v22 are recorded separately. No outputs/caches or v21_flowtools
work imported. Uses jsonschema, httpx, Jinja2 and existing isolated execution workers.

26 CPU tests pass; full16 preflight passes, with native/traced agreement on public
base seeds and seven evaluator-only witnesses confirming the declared fixture bugs.
These are interface/execution checks, not model/concept efficacy evidence. Source
freeze includes62 files; preflight is bound to exact source/fixture hashes. Repeated
prelaunch CPU attempts are archived by source hash, not overwritten as old evidence.

One independent clean-context code reviewer, `v23_clean_audit`, performed initial
audit plus re-audits. No model/endpoint calls or edits by that reviewer. Findings
and resolutions before online source freeze:

| Finding | Resolution and regression coverage |
| --- | --- |
| Terminal transport failure blocked every later case/report | SlotFailure persists failed artifact; other arms/cases continue; protocol failures stop globally with an incomplete full-denominator status |
| Legacy online entrypoints could bypass diagnostic limits | Legacy Client online construction and experiment/mining CLI paths disabled; CPU workers retained |
| Invalid stages looked like valid abstention | Separate stage states/counts, failed input stages, blocked revision and valid abstentions |
| HTTP tokenizer body accidentally limited to64KiB |16MiB HTTP-body parser limit separate from64KiB model-text limit; long token-list regression |
| CPU pass could outlive source changes | Exact source/fixture binding checked before online and frozen protocol |
| Tokenizer malformed metadata could lose global failure on resume | Persistent prompt-hash quarantine, shape/negative/context checks; [], null and wrong context regressions |
| Legitimate overlong prompt treated as protocol drift | Nonnegative count accepted; completion classifies overflow as per-slot context failure |

Spec-only concepts and code-only behavior claims remain separated. Tools return
syntax/line observations; no complete CFG, symbolic path proof or semantic matcher.
Three downstream arms distinguish complete concept-guidance, upstream hypothesis
guidance and explicit concept presentation conditional on the same hypothesis.
Fixture expected-output evaluators run only after generation is frozen; native
observations alone never set expected outputs. Raw malformed artifacts remain available.

Separate Luna probe: [report](v23_luna_probe/report.json). Two gpt-6-luna/low agents,
one fresh context per arm. Five seen fixtures: three buggy, one correct with an
unused suspicious operation, one ambiguous spec. Supplied authored concepts contain
no fault, trigger or witness. Both arms produce valid artifacts for5/5 cases, detect
all3 buggy cases with correct assertions and no observed false alarms. Independent
review verified all19 submitted input predictions/expectations and sufficient triggers,
correct ambiguity abstention and unused-operation handling. Both find the same four
bug-revealing inputs; concept adds only passing contrasts. **No incremental concept
benefit observed.** This tests supplied-concept use, not Qwen extraction reliability,
API-stage isolation, unseen validation or token-matched benchmark gain.

Online diagnostic is separately registered in central PREREG and local PREREG.
Maximum160 logical requests/480 physical completion attempts, no content repair,
same16 seen fixtures and full denominator. Frozen run status/results are under
`out/pipelines/v23_concepthyp/humaneval/concept_hypothesis_diagnostic/`.
No automatic benchmark/held-out expansion; semantic review remains required.
