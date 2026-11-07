# Legacy BVA — archived selection/context/compiler flow

Archived on2026-11-07. The active `boundary` arm uses [soft BVA](../README.md).
This folder preserves typed-selection, constructor/literal and checked-grounding
implementations for explicit diagnostics and historical input accounting. The
protocol descriptions/results below are historical; they do not define the current
CLI default. Saved artifacts are unchanged; strict historical replay still needs
the original source/environment. New-source frozen-input rescore uses a fresh output.

## Opt-in checked grounding experiment

`BoundarySettings(grounding_mode="checked")` or
`BoundaryArm(grounding_mode="checked")` enables bounded AST quantity/polarity
receipts, recognized-contract float widening, raw code-point templates, early
domain-side pruning and checked context goals. Off remains the default and its
selection messages/menus match all10saved v5requests byte-for-byte.

Receipts are source facts under stated assumptions, not NL intent or correctness
proofs. Raw code points differ from transformed `ord` and encoded byte length.
`non_ascii` and `prefix_exceeds_limit` properties can be checked on final calls;
goal coverage remains a context metric, not a bug verdict. Unknown syntax does
not reject all task inputs. This experiment changes candidate pool and guidance
together and requires fresh artifacts (`boundary-value-analysis-grounded-1`).

278modular tests pass, including44grounding cases. After endpoint replacement,
the registered6miss diagnostic completed:8calls,23valid inputs, bug task16.
72states the prefix condition but supplies5invalid contexts;23omits boundaries;
157corrects polarity but selects an excluded domain side. Full replay/hash audit
passes. Trial changes remain uncommitted after v5checkpoint; no default promotion.
See the [live report](../../../../review/boundary_checked_grounding_2026-11-06.md)
and [offline trial](../../../../review/boundary_grounding_offline_2026-11-06.md).

## Historical default: restored protocol5

The user selected protocol5 as the stable default after the compact diagnostic.
Selection and context instruction bytes match the saved protocol5 prompts.
The shorter protocol6 candidate tested on23/72/157is archived under
final/review/prompts/boundary_selection_compact_v6.txt; historical run artifacts
remain unchanged.
Three fresh long controls on the current runtime reproduce the v5response texts.
The compact prompt adds partial semantic recognition on23but no new useful
inputs there;72/157retain their semantic mistakes, and157also emits an invalid
origin. Short pipeline:11valid inputs/0detected,8total paired-diagnostic calls.
The compact candidate is not the active default; the diagnostic supports no broader promotion.
See the [paired report](../../../../review/boundary_compact_selection_2026-11-06.md).

## Selection/context repair (protocol5)

Public spec/contract quotes establish the input domain or quantity. Code and
natural-edge candidates do not require an explicit spec threshold or different
spec rules on each side. Selection defaults to4096 completion tokens; generation
keeps2048. `selection_truncated` records an output-budget failure, with applicability
unknown, independently of invalid JSON or `no_applicable_boundary`.

Context families can use valid negative/mixed-sign inputs, empty/token-only text
and supported endpoint placement. Each family reuses its seed/non-target values
across sides, subject to compiled context budgets. This is prompt guidance, not a
guarantee that the model covers every family or executes the desired path.

Named-context records may include `context_requirements`, for example:

```json
{"obligation_id":"b1:at","arguments":{"xs":[-2,-1,-2],"limit":-6},
 "context_requirements":[{"parameter":"xs","property":"palindrome"},
                         {"parameter":"xs","property":"all_negative"}]}
```

Supported properties: `palindrome` (str/list/tuple), `all_negative`,
`all_nonpositive`, `all_positive`, `all_nonnegative` (nonempty numeric list/tuple),
and `token_only` (str plus a one-character `token`; empty text is allowed).
These are context choices, not inferred domain preconditions. They are checked
on final calls, including literal fallbacks. A requested palindrome sum changes
the center element or equal center pair rather than the last element, preserving
integer element types for integer targets. Odd integer totals on even integer
seeds are rejected as `context_shape_cannot_realize_target`; a different shape
may still work. Unmet properties give `context_requirement_not_met`.

Only these declared properties are checked. Prose reach/propagation stays
unverified, and full domain validation still requires the external contract.
The numeric-string binding guard and characteristic coverage are unchanged.
Protocol5 requires a fresh output directory; historical checkpoints are preserved.
Prelaunch validation passed223modular engineering tests. The subsequent
user-requested known-bug10 diagnostic produced64valid inputs/16calls and exposed
tasks76/99/124/140, compared with124alone in v4. This is post-hoc mechanism
evidence, not efficacy. See the [diagnostic report](../../../../review/boundary_prompt_v5_diagnostic_2026-11-05.md)
for remaining losses and the concurrent runtime-source drift that blocks full
replay on the current working tree. Dated scope is recorded in CHANGELOG/PREREG.

## String characteristics and format derivations

After the 44-PUT feasibility audit, protocol3 introduced the following changes.
String candidates include `parsed_float`: a finite Python float read from a
numeric string. Public numeric-string declarations are required to bind this
projection; numeric observations or a PUT-side conversion alone are insufficient.
Code round-trips exact targets through `repr(float(target))`, including adjacent
floats and signed zero. A single controlled numeric string needs no context call.

Bounded public-spec rules expose half-integer midpoint representatives for nearest
integer behavior and length inferred from a declared fixed-width format mask.
For example `mm-dd-yyyy` gives length10 with recorded field widths2/2/4. These
are behavior hints, never new preconditions: malformed date strings can remain
valid function inputs whose correct result is False. Examples, negation, optional
suffixes, variable formats and ambiguous parameter bindings do not establish a
fixed width. The selector may still decline; there is no automatic fallback.

205 engineering checks pass (196 modular+9 development-selection),including40 new
string cases. Scripted selections on two saved PUT fixtures demonstrate the full
injected-generator/freeze/corrected-oracle path; they do not measure fresh LLM
selection quality. Old artifacts remain unchanged; new generation needs a fresh
output directory. See [follow-up report](../../../../review/boundary_string_repair_2026-11-05.md).

## Historical compiled repair

`construction_mode="compiled"` now uses:types/templates/public guards → LLM
selection → role/operator checks → TargetCompiler → optional LLM named contexts
→ shared CallBuilder → target/domain/duplicate checks. Plain uses the same encoder.
The context response is `{"inputs":[{"obligation_id":"b1:at","arguments":{...}}]}`.
Code computes nextafter/integer targets and constructs supported shapes;scalar
targets with no free context can finish after selection alone. Context budgets
are fixed per obligation;exact scalar/base duplicates are removed before querying.

New evaluators include maximum consecutive run length,range,min and max. Domain
roles require necessary public constraints;behavior conditions remain separate.
Statuses distinguish no-applicable,unsupported,uncertain,covered and construction
limits. Recognized domain checks are partial,not complete contract/spec proofs.
Strict literal mode remains for compatibility;compiled literal fallbacks are tagged.
New source/schema requires fresh artifacts,not migration of old result checkpoints.

The initial compiled repair passed165checks,including34new mechanism checks.
See [repair report](../../../../review/boundary_repair_2026-11-05.md) for scope and limits.

## Original literal protocol history

Module riêng trong code hiện có, theo flow user yêu cầu ngày 2026-11-04:

```text
saved input calls + PUT/task signature
  → InputTypeExtraction
  → BoundaryTemplates
  → BoundarySelection (LLM lần 1)
  → BoundaryInputGeneration (LLM lần 2)
  → literal inputs + boundary evidence
```

Mỗi bước là một class với `run(context)`. `BoundaryValueAnalysis` điều phối,
lưu checkpoint và thực hiện skip. Public API: `extract`, `run`, `run_for_program`.
Module hoạt động độc lập theo từng PUT và đã có adapter `BoundaryArm` trong
pipeline qua explicit legacy import. CLI `--arms boundary` hiện dùng soft BVA.
Không cần CFG/DFG, mutation, fuzzing hoặc chạy PUT để trích type.
Core mới nhận injected generator; `MethodInputGenerator([BoundaryArm()])` nối
module vào cùng contract sinh input như mọi phương pháp khác, không có concept
mining/witness stages ban đầu. Xem [injection API](../../generators/README.md).

## Type và templates

- Đọc concrete types từ `base_inputs`: `args`/`kwargs` là Python literal strings,
  hoặc `bound` là mapping parameter→literal string như cached base calls hiện tại.
  Nếu có cả hai thì bind args/kwargs vào PUT signature; tránh sai tên khi PUT đổi
  parameter name so với task signature.
- Bổ sung annotations từ PUT và task specification, giữ provenance riêng.
  Không import PUT, không evaluate annotations/default expressions bằng `eval`.
  Unknown type giữ unknown. Observed values không được biến thành semantic range.
- V1 có scalar numeric value, collection/string length, numeric list/tuple elements
  và numeric list/tuple sum. Model có thể chọn threshold là constant hoặc scalar/
  length/sum của parameter khác, ví dụ `sum(xs)=limit` hoặc `index=len(xs)`.
- Boolean-only, unknown/custom types không tạo numeric boundary candidate.
  Nested element paths, custom arithmetic, date objects và enum-specific order
  chưa hỗ trợ. Collection chứa type chưa hỗ trợ vẫn có length candidate.

## Hai bước LLM

Selection nhận specification, contract, PUT, type evidence và candidate templates.
Nó chọn characteristic, threshold, comparison, boundary kind, neighborhood,
target sides và constraints có source quotes. Có thể trả `no_boundary` với reason.

Schema validation kiểm template/parameter references, nonempty quotes thực sự
có trong spec/contract, numeric thresholds/steps, allowed sides và literal shape.
Quote tồn tại **không chứng minh semantic entailment**; selection được ghi rõ là
`llm_proposed_with_verified_quote_not_entailment_proof`.

Generation chỉ nhận selected boundaries và domains cùng templates. Model trả
`args`, `kwargs`, `boundary_id`, `side`; không sinh expected outputs/assertions.
Validator bind signature, kiểm finite supported literals, tính characteristic và
threshold trên chính input đó, kiểm đúng declared neighbor/side và loại duplicates.
`elements` cần ít nhất một element đạt target; `sum` dùng Python arithmetic.

`step` được tính theo Python arithmetic; `float_adjacent` dùng `math.nextafter`.
Nếu rounding làm neighbor trùng threshold hoặc nonfinite thì reject. Không dùng
tolerance tùy tiện để nhận một input không thực sự chạm target.

Constraints bằng prose vẫn là LLM proposals, **chưa được execute/verify**. Output
ghi `domain_constraints: unverified`, `oracle: not_run`. Cần external contract/
reference validation trước khi gọi input là valid test hoặc chấm bug detection.
V1 chỉ cho normal domain-boundary sides; input ngoài precondition không được đưa
vào chỉ vì muốn thêm robustness case. Behavior boundaries có thể xét hai phía.

## Skip, budget và cache

| Status | Ý nghĩa / số LLM calls |
|---|---|
| `unsupported_signature` | Signature chưa hỗ trợ; 0 calls |
| `no_templates` | Không có family hỗ trợ từ type evidence; 0 calls |
| `no_boundary` | LLM không chọn được boundary; 1 call, không sinh input |
| `invalid_selection` | JSON/schema/provenance invalid; 1 call, không giả làm no-boundary |
| `prompt_too_large` | Dừng trước request không vừa context; 0 hoặc 1 call trước đó |
| `invalid_generation` | Response sinh input malformed/truncated; 2 calls |
| `no_inputs` | Không sinh/không giữ được input; 2 calls, không claim infeasible |
| `generated` | Có input đã qua signature/target checks; 2 calls |

Default tối đa4boundaries,20input records,4096selection/2048generation completion tokens,
context8192, selection temperature0 và generation temperature0.7. Không có model
retry/fallback ở module này; transport adapter giữ retry policy riêng của nó.
Prompt generation hiển thị tối đa12base calls đầu tiên; duplicate validation vẫn
so với toàn bộ base calls. Type evidence được gộp theo type, giữ observation count
và tối đa8example indices. Không dùng observed extrema làm threshold.

Artifact ở `tasks/<task_number>/boundary/<program_id>/`: identity, input_types,
templates, select/inputs prompts, selection, generation, result. Identity ràng buộc
source/spec/contract/base inputs/settings/model và module source hashes; mismatch
fail trước inference. Calls dùng keys `bva_<program_id>_select` và
`bva_<program_id>_inputs`, tương thích `RecordedModelCalls` và token accounting.
Lock riêng cho từng PUT ngăn hai controller chạy cùng checkpoint.

Transport failure propagate, giữ selection đã hoàn thành để resume ở generation;
không chuyển API failure thành skip. Read-only replay cần đầy đủ stage artifacts,
không tokenize/gọi model/chạy PUT. Dùng output directory riêng cho protocol này;
không ghi vào completed runs hoặc checkpoint của arm khác.

## Sử dụng

Chỉ inspect candidates offline:

```python
from final.src.modular.boundary_value_analysis.legacy import BoundaryValueAnalysis

analysis = BoundaryValueAnalysis()
candidates = analysis.extract(
    specification=task["prompt"],
    entry_point=task["entry_point"],
    program_source=program["code"],
    base_inputs=program["base"]["calls"],
    contract=metadata["contract"],
)
```

Chạy hai bước LLM khi backend/run đã được cấu hình:

```python
from pathlib import Path
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.boundary_value_analysis.legacy import BoundarySettings, BoundaryValueAnalysis

artifacts = ArtifactStore(Path("final/out/boundary_development"))
calls = RecordedModelCalls(model, artifacts)  # model dùng backend/env hiện có
analysis = BoundaryValueAnalysis(BoundarySettings(input_budget=12))
result = analysis.run_for_program(
    task, program, contract=metadata["contract"], artifacts=artifacts, calls=calls,
)
```

Adapter chỉ lấy prompt/entry point, PUT source và saved base inputs; không đọc
canonical solution/plus inputs/base expected outputs. Nó không tự tạo PUT,
không chạy reference và không tự launch benchmark. Inputs có thể đưa vào bước
reference validation hiện có sau khi freeze toàn bộ generation của run.
Budget của API này là **per PUT**. Adapter `BoundaryArm` đã chia total task budget
cho các visible PUT có template, gộp/deduplicate inputs rồi dùng reference oracle
và PUT evaluation của pipeline chính. Mỗi allocated PUT có tối đa2logical calls;
không gọi đây là one-call/task arm. Xem [pipeline usage](../../README.md)
cho CLI chạy smoke subset và cách giữ các arm khác trong cùng run.

## Verification

Engineering fixtures dùng scripted model responses, không phải mô phỏng paper.
Kiểm early exits, source provenance, malformed/truncated responses, relational/
float targets, literal safety, duplicates, transport resume và immutable replay.
Chạy: `final/.venv/bin/python -m pytest final/src/modular/tests/test_boundary_value_analysis.py -q`.

Module41checks + integration11checks; toàn bộ modular regression suite85checks
pass. Integration dùng scripted responses và tiny synthetic programs để kiểm
generation freeze, real sandbox reference/evaluation, checkpoint resume/replay,
task budget và báo cáo skip. Chưa chạy live model hoặc benchmark cohort.

Sau refactor dependency inversion: full suite93checks pass. Các validation được
tách thành `validate_response`, `validate_input`, `validate_task_input` và shared
`validate_generated_inputs`/`validate_input_literal`; chỗ gọi có comment blocks
`VALIDATION START`/`VALIDATION END`. API/cache/budget/reference checks có markers.

Xem [research basis](../../../../review/boundary_applicability_2026-11-04.md).
