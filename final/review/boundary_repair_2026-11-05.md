# BVA repair — implemented

User authorized implementation of the mechanism proposal. Changes are in the
existing modules;no new version folder or benchmark generation was created.

## Changes

1. Shared `CallBuilder` for modern plain and BVA. LLM returns named JSON values;
   code handles signature binding,defaults,positional-only/keyword-only fields,
   tuple/set tags and safe literal serialization. It never evaluates model code.
2. `TargetCompiler` computes exact integer/float neighborhoods (`math.nextafter`)
   and instantiates supported scalar,length,element,sum,extrema,range and run-length
   targets. LLM supplies contexts rather than writing target arithmetic or arrays.
3. Typed `run_length` measures the longest consecutive run,not whole-string length.
   `range` measures max-min. Domain roles require matching necessary public clauses;
   behavior guards cannot be converted to preconditions merely by labeling them.
4. Bounded public hints expose constants/relations for cases such as positive
   filtering,elements>10 and max(sequence)<threshold. No global finite min/max is
   required. Unsupported characteristics and uncertain bindings have distinct states.
5. Context quotas are allocated before outputs,round-robin across boundaries.
   Single-scalar targets are built directly and exact base duplicates removed;
   covered scalar calls do not consume a context-model call. List/length classes
   are not skipped merely because one base input has the same feature value.

## Validation and limits

**165 combined checks pass**:modular pipeline plus development selection,including
34new mechanism checks. Cases include float0/3.7,run context inside text,role8,
extrema/range,relational thresholds,nested grid shape,budget/duplicate handling,
unknown predicates,conditional shape requirements and zero-model replay.

Offline recheck of49saved proposals:43pass supported structural checks;4domain
roles are unverified,one extrema binding and one consecutive-run binding rejected.
These are not semantic precision labels. All1,336original benchmark artifact files
match their pre-repair hashes. No new model calls or real-cohort evaluation.

Known-domain checking recognizes necessary conjunctions and supported all() clauses.
OR,opaque predicates and mutated inputs remain unknown. Behavior bindings may
still be LLM semantic hypotheses;quote/target checks do not prove entailment.
Full trusted domain/reference evaluation remains after generation freeze.

Constructor limits:1000items/container,16000characters/literal. Unrepresentable,
unsupported and resource-limited targets retain reasons;none becomes an invented
semantic endpoint. Inverse construction is bounded,not a general solver.

Default `construction_mode="compiled"`;strict literal mode remains for compatibility.
Literal fallbacks in compiled mode are tagged and still face target/quota checks.
Changed code/schema requires a fresh run directory. Native cache fingerprint now
includes its shared signature parser dependency. Historical results remain intact.

## Files / reproduction

- `final/modular/call_builder.py`, `input_prompts.py`.
- `boundary_value_analysis/characteristics.py`, `binding.py`, `construction.py`.
- Updated selection/context prompts,stages,settings and BoundaryArm.
- `final/modular/tests/test_bva_compiled.py`.
- [Offline audit JSON](boundary_repair_offline_2026-11-05.json).

```bash
final/.venv/bin/python -m pytest final/modular/tests final/tests/test_development_groups.py -q
final/.venv/bin/python -m final.review.audit_bva_repair
```

The corrected HumanEval+ rescore remains0vs0on the earlier saved inputs. There
is no new live result for this repaired generator and no claim of efficacy gain.
