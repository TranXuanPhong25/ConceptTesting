# Boundary protocol5: known-bug10 diagnostic rerun

Protocol5 detects the known bugs in tasks76,99,124,140, compared with task124
alone in v4. It produces64valid novel inputs with16received model calls;
v4 produced10with14calls. This is an outcome-selected, post-hoc mechanism
diagnostic, not a detection rate or efficacy comparison. No plain/random control
was run and the effective call/token/input counts differ.

## Fixed scope and prelaunch review

- Same10PUTs/cohort as v4, cohort hash
  `274e5251c97682d2d0c43d53fb936a859822737ec3d33f54e05e09aac3eb48c1`.
- Same `qwen3.5-27b-awq`, context8192, input budget20/task, generation2048tokens,
  seeds/temperatures, contract and corrected HumanEval+v0.1.10 oracle.
- Selection budget4096instead of2048; repaired selection/context prompts and
  optional bounded context requirements. No character-code projection added and
  numeric-string binding safeguards remain intact.
- Independent prelaunch review removed residual spec-threshold requirements
  from candidate metadata and the side-rule-change requirement from context.
  All223modular tests passed before launch. All10selection prompts fit context;
  their token counts range2069–3148.
- All generation froze before the first reference/PUT evaluation. No semantic
  retry, witness injection, prompt edit or cohort expansion during the run.
- Output: `final/out/boundary_known_bug10_prompt_v5_20261105`.

## Per-task result

| Task | v5 valid inputs | Bug observed | Mechanism / remaining loss |
|---|---:|---|---|
| 2 | 0 | No | Selection still abstains; calls fractional-part behavior continuous/uniform and requires stated thresholds despite the repaired instructions. |
| 11 | 0 | No | Selection still abstains; treats equal string lengths as insufficient to justify the empty edge. |
| 16 | 0 | No | Selection recognizes character-code256but binds it to string length256; generation then reaches2048tokens and truncates while padding contexts/materializing long text. Character-code characteristic remains unsupported. |
| 23 | 0 | No | Selection abstains; required character-code characteristic remains unsupported. |
| 72 | 7 | No | Correct relational sum boundary, with palindrome requirements preserved, but accepted contexts still contain only nonnegative/positive values; negative case absent. |
| 76 | 14 | Yes | Adds `x == 1` neighborhood, which includes `x == 0`; `(0,2)` times out twice against referenceFalse. Also exposes a separate `(1,0)` value disagreement. |
| 99 | 6 | Yes | Selection finishes without truncation; compiled parsed-float neighbors of±0.5include the exposing near-half values. No context model call needed. |
| 124 | 19 | Yes | Length10neighborhood exposes malformed year width, as in v4. Three parsed-field proposals remain rejected with `unverified_numeric_string_binding`. |
| 140 | 12 | Yes | Same run-length2boundary now includes token-only, leading-space and trailing-space context families. One/two-space strings expose the bug. |
| 157 | 6 | No | Selection replaces abstention with `a > 0`, not the known hypotenuse boundary. Fourteen context proposals target excluded sides and are rejected by recognized-domain checks. |

Observed examples, each with identical outcomes in two native repeat slots:

| Task | Input args | Corrected reference | PUT |
|---|---|---|---|
| 76 | `(0, 2)` | `False` | timeout |
| 99 | `('0.49999999999999994',)` | `0` | `1` |
| 124 | `('01-01-200',)` | `False` | `True` |
| 140 | `(' ',)` | `'_'` | `'-'` |
| 140 | `('  ',)` | `'__'` | `'-'` |

The repair bundle exercises three previously missing paths: task76selection,
task99complete selection/compiled targets and task140special contexts. It does
not resolve selection abstention on2/11or negative context choice on72. Lower
abstention counts do not themselves establish better semantic selection:16has
a wrong characteristic and157chooses an unrelated edge. Quote presence remains
provenance evidence, not proof of a valid semantic binding.

## Accounting and artifact audit

-16task invocations,16responses,0unknown;42,587prompt +11,749completion
  =54,336known tokens. No missing usage footers.
- User-requested keepalive ping before launch:13prompt +1completion tokens,
  separately recorded in prelaunch_readiness.json. No periodic keepalive was
  needed before terminal completion.
- Generation rejections:1invalid/truncated generation,8duplicates,
  14recognized-domain violations. Oracle rejects0inputs.
-256native input records,24cache hits and232executions. Six timeout results
  were not cached; repeat slots remain separate.
-10/10input-freeze hashes and the generation-before-oracle barrier verified.
  All291prior v4output files retain their prelaunch hashes.

There was concurrent working-tree source drift after launch. The launch manifest
matches the prelaunch hashes of `runtime/model.py` and `modular/pipeline.py`;
the long-lived controller imported those modules before their on-disk edits.
The drift is a transport migration and package-accounting edit from another
session. Two audit/test files also changed. All BVA source, dataset, contract,
reference and native-execution worker files retain their prelaunch hashes.

Full read-only replay on the current working tree is blocked by the source-hash
guard at `modular/pipeline.py`; the guard was not bypassed. The two exact launch
source files were recovered, hash-checked and saved as `.py.txt` evidence under
the run's `source_evidence/`, without modifying the working tree or manifest.
This is a reproducibility limitation for the current tree; the frozen inputs and
stable native failure evidence were independently checked from artifacts.

See the run's `prelaunch_snapshot.json`, `prelaunch_readiness.json`,
`modular_manifest.json`, `generation_frozen.json` and `postrun_audit.json` for
hashes, scope, per-task outcomes and every stable failure input.

## Follow-up failure trace

User-requested [six-task trace](boundary_prompt_v5_failure_trace_2026-11-05.md)
records exact raw contexts, constructor changes, early exits and native outcomes.
Pure constructor replay for72/157matches saved inputs. Additional findings:
72confuses prefix sum with total sum;157calls complementary domain predicates
an operator mismatch and its observed-int templates exclude controlled float
neighbors despite the float-permitting contract;23describes PUT byte-length
semantics as intended behavior. Analysis only, no new model/PUT/reference runs.
