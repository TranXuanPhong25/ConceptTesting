# v57_pathfault — explicit hypotheses and path-aware input construction

New engineering implementation, 2026-10-24. Not promoted; no model or benchmark effectiveness run.
Parent is best v7; v31 fixed-transform functions are preserved in `legacy_templates.py`.

## What changes from v31

V31 labels a mutation site, applies fixed single-position edits to public examples, and injects selected inputs plus alternatives into a prompt. Its final 18-vs-15 result remains valid as a directional package result.

V57 implements a different construction mechanism:

1. Extract exact AST-bound alternatives, or import explicit writer hypotheses grounded by a spec quote. Writer fields separate `required_relation`, `observed_relation` and `trigger_reason`. A matching quote verifies location of evidence, not the correctness of interpretation.
2. Build symbolic inputs shared by PUT and alternative. Symbolically follow assignments, branches and bounded loops. Build constraints for reaching the exact target expression, changing its local value, and changing the returned value.
3. Solve jointly with Z3. Arguments and list elements can change together; search is not limited to a fixed list of seed edits.
4. Replay each candidate on both programs in an isolated networkless worker. Require normal returns, the exact AST event, matching branch trace and predicted output, and final typed output disagreement. Timeouts/errors are not successes.
5. Rank unresolved public-example hypotheses with verified witnesses. This ranks behavioral uncertainty, not likelihood of a spec bug.
6. Export prompts. `concept` names the reach/infection/propagation obligation; `equal_evidence_raw` receives the exact same evidence object/order. `inputs_only`, `plain` and public `witness_only` are separate baselines. No LLM transport runs here.

## Fault families and executable facets

The five v31 families remain in the vocabulary; new facets are not mutually exclusive defect labels.

| Family/facet | Binding / actual executable construction |
|---|---|
| BOUNDARY + ORDER_TIE | Strict/inclusive comparison alternative; solve equal operands plus enclosing guards and return disagreement |
| OPERATOR | Arithmetic/Boolean operator alternative; solve local and final distinction |
| VALUE | `abs(x)` versus identity, or an imported source-bound value expression |
| CALL | `min` versus `max` on supported integer values; not arbitrary API behavior |
| MISSING_CASE | Legacy low-cardinality transformations and shape enumeration only; **no synthesized missing branch** |
| LOOP_CARDINALITY | `range` endpoint ±1; solve loop paths with changed returned value |
| INDEX_SELECTION | Adjacent index alternative, negative-index normalization, bounds valid for both paths, selected-value/output distinction |
| STATE_ACCUMULATION | `+=`/other accumulator update versus overwrite; require at least two exact target visits and output distinction |
| MULTIPLICITY | `sum/len(sequence)` versus `sum/len(set(sequence))` in either direction; enforce duplicate values and output distinction |

Each reported input includes path predicates, local infection predicates, before/after outputs, exact-site events, replay status and domain bounds. Aliasing/mutation, external API effects, recursion and arbitrary missing algorithms are not claimed supported families.

## Supported Python envelope

Entry must be a top-level ordinary function with fixed positional arguments (no defaults), or the normalized repository wrapper of a simple stateless Solution method. `bindings.py` preserves the original module/AST coordinates and analyzes the matching method body; replay still calls the original wrapper. Init/dunder methods, inheritance, metaclasses, decorators and executable class-body state are excluded. This is not general class/helper support. Input profiles: homogeneous int/bool/string scalars and homogeneous flat int/bool/string lists/tuples; only-empty public sequences have unknown element type and are rejected explicitly. Shape enumeration includes every length from zero through the configured maximum; Cartesian shape-cap truncation is reported explicitly. Example sign/minimum length is never a validity rule.

Supported: assignments/unpacking, arithmetic `+ - * // %`, comparisons, scalar short-circuit Boolean operators with compatible result types, conditional expressions, if/else, bounded for/range, break/continue/for-else, returns, asserts, len/sum/min/max/abs, enumerate, sequence concat/constant slices/reversed, bounded indexing, string length/equality/concat/index, pure `set` inside supported sum/len.

Unsupported: while, comprehensions, helpers/nested functions, arbitrary methods/imported call semantics, sequence element writes/mutating calls, nested/heterogeneous input containers, symbolic-size slices, floating point, generators, recursion, and general exception or object semantics. Symbolic sequence AugAssign (including `+=`) is explicitly unsupported; concrete replay preserves its actual in-place/alias semantics when recording public observations. `min/max` are modeled as integer-valued; combinations such as type-preserving bool extrema can replay-reject. Support for an input type does not imply every listed builtin works on it. Symbolic shape/loop/path caps, Z3 unknown and replay mismatches are logged distinctly. A verified witness remains useful when other paths are unsupported; absence of a witness is never a full-program equivalence claim. The current objective requires both programs to return normally; exception-only discrepancies are excluded.

The input profile and search bounds are observational, not the normative spec domain. All inputs still need spec-validity checks and an independent oracle before counting bug discoveries. No hidden evaluator/reference is accepted by the preparation schema. Callers must attest that supplied examples/spec are public.

## Run locally

```bash
uv venv /tmp/concepttester-v57-venv
uv pip install --python /tmp/concepttester-v57-venv/bin/python -r trickcatcher_linefacts/pipelines/v57_pathfault/requirements-pathfault.txt
/tmp/concepttester-v57-venv/bin/python -m pytest -q trickcatcher_linefacts/pipelines/v57_pathfault/test_pathfault.py
```

The new entrypoint is `deep_run`; copied v7 commands still describe the inherited baseline, not this new method.

```bash
# Adapt only explicitly public material; simple assert candidate(args) == literal is supported.
/tmp/concepttester-v57-venv/bin/python -m trickcatcher_linefacts.pipelines.v57_pathfault.public_adapter \
  --source put.py --public-asserts public_tests.py --spec spec.txt --entry f --case-id example --out /tmp/v57-request.json

# Optional explicit semantic-writer stage: export, then put its JSON list in request.proposals.
/tmp/concepttester-v57-venv/bin/python -m trickcatcher_linefacts.pipelines.v57_pathfault.deep_run \
  export-hypotheses --request /tmp/v57-request.json --out /tmp/v57-hypothesis-prompt.json

# CPU construction, concrete replay and equal-evidence prompt export. No model/API call.
/tmp/concepttester-v57-venv/bin/python -m trickcatcher_linefacts.pipelines.v57_pathfault.deep_run \
  prepare --request /tmp/v57-request.json --out /tmp/v57-prepared.json
```

Output is immutable. Reusing a path with changed request/proposals/config/source/Python/Z3 version fails instead of silently using an old artifact. Config is in `config.json:pathfault`. The adapter records unsupported asserts; it never executes public tests to extract values, imports an evaluator, or silently chooses a subset above six examples.

The adapter accepts direct module assertions or direct assertion-only `check(candidate)` wrappers. Wrappers containing returns, rebinding or other executable statements are marked unsupported as a whole. General module statements fail closed; literal `if False` bodies can be skipped with a recorded limitation. This intentionally excludes arbitrary test harnesses.

The repository's normalized `_heldout_same` comparator is recognized only by exact known AST. It is never executed to extract examples; the original comparator remains the evaluation policy. Unknown helpers are rejected.

Case deadlines propagate through symbolic evaluation, each solver check and concrete/base replay waits. These are orchestration limits, not a hard CPU/memory sandbox for the parent process; AST size, expression/path/query/sequence caps bound parent work. Worker processes have explicit CPU/memory/wall limits. Imported replacements pass a pure AST/builtin allowlist before any replay.

## Validation and limits of the claim

Authored regression fixtures cover joint guards/assignment dependencies, multi-argument construction, tie/multiplicity, repeated accumulator updates, loop endpoint effects, safe negative indexing, dead/short-circuit sites, masked local effects, Python negative-divisor semantics, partial unsupported paths, input-profile limits, proposal binding/priority, evidence parity and manifest drift. These are engineering checks, not a benchmark or concept efficacy estimate.

Independent plan/code review and amendments are recorded in `REVIEW.md` and `PREREG_V57.md`. Future model comparison must freeze its own cohort/budgets and retain original v31 plus equal-evidence controls. Prompt formatting alone is not an isolated semantic-content ablation when raw receives the same concept descriptions. The current deliverable proves runnable construction/integration, not research novelty or improved bug detection.

## Ngrok transport and frozen pilot

User explicitly requested ngrok, with no OpenRouter fallback. `ngrok_client.py` accepts only HTTPS ngrok domains, refuses redirects, reads URL/key from environment and never includes them in artifacts or errors. `/models` selects the actual served model; server `/tokenize` preflight checks exact prompt+completion context before a chat dispatch. Metadata/tokenization requests do not generate model completions.

`ngrok_run.py` performs one shared explicit semantic-writer slot, CPU construction, and two probes plus final for each of plain/concept/equal-evidence-raw/inputs-only. The input control sees exactly the same displayed witness pool as concept/raw. Public witnesses are replayed separately without a model. Expected outputs remain model predictions; this runner never opens the private evaluator or claims confirmed bugs.

The six dev cases (61,66,124,58,131,85) were selected by outcome-blind hash from the frozen v31 cohort; public requests are already prepared with zero skipped assertions. At most78completed slots/156chat transport attempts. Attempts and exact requests persist before dispatch, including unknown interrupted completions; responses/artifacts publish atomically without overwrite. Received responses survive interrupted final publication. A run-output lock prevents duplicate clients in the same output folder. Exhausting a slot's two attempts stops the run. Full code/protocol review passed;49engineeringtests pass independently. No live model request yet; user's notebook restart/new endpoint pending.

```bash
bash trickcatcher_linefacts/pipelines/v57_pathfault/run_ngrok.sh --env-file /private/runtime-env.sh metadata
bash trickcatcher_linefacts/pipelines/v57_pathfault/run_ngrok.sh --env-file /private/runtime-env.sh run \
  --requests trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json \
  --out trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/generation
```

Use a private env file outside the repo with `QWEN_BASE_URL` and optional `QWEN_MODEL`/`QWEN_API_KEY`. No paid provider or silent model substitution. `examples/prepared.json` is the earlier CPU snapshot at commit`eb2b17c`; later transport/integration source changes intentionally invalidate its reuse under the current manifest. Preserve it and choose a fresh output path for a new preparation.
