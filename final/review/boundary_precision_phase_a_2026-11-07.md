# Soft precision tool — Phase A

User-authorized offline diagnostic completed, with no new model calls.
Artifacts: `final/out/boundary_precision_phase_a_20261107_152738`.
Source seeds: `final/out/boundary_prompt_style10_20261107_120909`.
Policy was appended to PREREG before executing new inputs: first10soft seeds,
up to10adjacent float expansions in fixed seed/parameter/direction order, then
remaining seeds fill unused slots. Numeric strings need a direct float(parameter)
conversion cue. No task-specific target insertion or post-outcome policy tuning.

| Policy | Novel valid inputs | Detected PUTs/tasks |
|---|---:|---:|
| Saved direct | 199 | 6 |
| Saved soft | 192 | 7 |
| Fixed20precision expansion | 193 | 8 |
| Full pool ceiling, outside20budget | 318 | 8 |

Gate PASSED: new stable value-mismatch task99, no previously soft-detected task
lost. Pool ceiling alone was not used for the decision. All fixed/pool batches
froze before any new reference evaluation; both evaluations have matching
immutable read-only replay.354modular/development tests passed before launch.
Source files and original saved artifacts were hash-verified through completion.

## Causal mechanism supported by the trace

Soft's first99seed is value='0.5'. The tool uses that existing value as its
anchor, reads a direct float(value)conversion cue, and constructs its immediate
lower binary64neighbor: '0.49999999999999994'. The fixed policy selects it.
Reference returns0, PUT returns1in both native repeats. Thus soft already supplied
the relevant transition location; mechanical value construction repaired the
missing precision. This result requires no new LLM concept proposal or feedback.

The generic policy also retains task2by generating adjacent neighbors below
integer-valued float seeds. It replaces some original exposing seeds but retains
the PUT detection. Preservation here is an observed result of this policy, not
a general guarantee for arbitrary tasks or smaller budgets.

There are126distinct expansions across four tasks:2has38,72has4,99has38,157has46.
The primary fixed20batch uses34expansions total; other slots remain original
seeds.11/16/23/76/124/140have no eligible scalar-float/numeric-string anchor under
the declared scope, so they keep their original seed batches.

## What remains weak

-11still has no empty binary-string pair. A float constructor cannot supply
  missing joint empty coverage. Historical naive produced('', '')and PUT raised
  ValueError instead of returning''.
-16still has only ASCII seeds. No chosen quantity points to ord(char)after
  lowercasing, so this precision tool cannot reach the excluded Unicode partition.
  Historical naive also missed16; this is not evidence naive solved that case.
-76still detects through thex0timeout. Historical naive additionally exercised
  negative/zero-base cases that produced wrong returned values. Precision is not
  the missing capability on integer branch/context cases.
-The fixed allocation drops some seeds; full per-seed replacement and candidate
  trace is preserved in report.json. Additional precision does not prove better
  exploration, quantity selection or semantic interpretation.

Naive's historical wins over typed BVA v5on2/11/157were lost upstream: explicit
abstention gates on2/11and a wrong scalar/domain target on157. Current soft has
already removed those gates and recovers2/157. The remaining11miss is missing
concrete coverage, not a compiler failure. Different historical PUT visibility
also prevents attributing all differences to prompt wording or length.

Next conditional question: with the same seed batch and matched expansion-slot
counts, does LLM direction outperform generic expansion? Phase A supports float
construction; it supplies no evidence that a concept selector is useful.

All10tasks were known-bug, outcome-selected development cases and informed this
diagnostic.8vs7is a mechanism result, not general efficacy or a default promotion.
