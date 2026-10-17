# v23 diagnostic registration — 2026-10-17, before model outputs

User requests copying the best version, code first, then clean-context audit; prefers
libraries and optionally authorizes gpt-6-luna/low concept-use probe. This increment
does not launch Qwen. Source parent v7; ports/provenance explicit. Never edit a frozen run.

Exact16 cases from ported pilot_fixtures.cases(), already seen in v21/v22 diagnostic;
seven buggy, eight correct, one ambiguous. No claims of unseen validation. Fixture
oracles and known witness labels excluded from all prompts and execution feedback.

Stages/arm matrix/execution boundaries/caps are specified in README.md and config.json.
Five-stage families concept, behavior, hypothesis, inputs, revision. At most160 logical
completions:32 common preparation +32 hypotheses +96 input/revision calls. Retry only
transport failures, cumulative3 per logical slot; no semantic/format retry or repair.
Temperature0, fixed seed20261017, model Qwen2.5-Coder-7B-Instruct and context16384 pinned.
Stage output caps768/768/1024/768/768; source/template hashes freeze before requests.

Interpretation: first measure parseability, independent semantic review of concepts,
behavior, hypothesis verdict/trigger and ambiguity handling, then feasibility of novel
admissible discriminators. Review correct/ambiguous/masked examples as well as bugs.
Report all16 cases and blocked/invalid slots. Schema checks never confer semantic truth.
Input discovery and correctly specified failing assertions are distinct outcomes.
No automatic real20, held-out run or promotion to best pipeline. Any later benchmark
comparison needs independent review/frozen protocol and full mandatory controls.

Separate optional Luna probe: fixed f02/f06/f12/f13/f14; two independent clean-context
gpt-6-luna low agents receive the same original context and public-base tool evidence.
One receives a manually authored normative concept, one does not. No fault hypothesis,
bug labels, distinguishing inputs, expected outputs or evaluator code are supplied.
Each produces one hypothesis and up to3 literal tests/case, no execution revision.
Batch context per arm is disclosed; no API call/token parity or stage-isolation claim.
Save all raw agent responses before evaluator scoring; report efficacy as exploratory,
never combine with Qwen results. Equal results imply no observed concept benefit in
this tiny probe. Artifact-only independent reviewer checks practical correctness.
