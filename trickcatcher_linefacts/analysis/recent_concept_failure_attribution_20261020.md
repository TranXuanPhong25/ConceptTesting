# Recent concept experiments: where does useful reasoning get lost?

2026-10-20, retrospective synthesis requested by user. Read existing frozen reports
and v33 saved attribution JSON only; no new model/API/worker executions, output repairs,
recovered scores, source changes or new experiment. Different cohorts/model/harnesses
are not pooled into a global rate or a cross-version causal comparison.

**Assessment:** current evidence does not establish concept-to-input translation as
the dominant missing skill. There are clear examples of adequate input synthesis.
Upstream selection/abstention, mechanical admission, oracle soundness, limited input
pools and absence of incremental information over direct generation explain different
losses. Prior suggestion to prioritize concept-to-input training is premature.

| Evidence | Observed loss | What this supports / does not support |
|---|---|---|
| Luna v23 diagnostic16 | All16 concepts/behavior descriptions faithful by independent review; concept correctly specified bug assertions5/7 vs direct7/7. Two concept hypotheses blocked by malformed JSON; one wrong expected value causes a false alarm. | Concept accuracy can coexist with end-to-end loss. Serialization and oracle reasoning matter; no concept advantage. |
| Luna v24 diagnostic9 | f06 generates6 novel bug-revealing inputs, accepted0; exact trigger input satisfies obligation=False, trigger=True, line reach=True but old support gate refuses promotion. | Concrete counterexample to a blanket inability to synthesize inputs. Verified guidance hid f06's unsupported hypothesis, so this is NOT causal evidence that that hypothesis generated the inputs. |
| v32_scope_support seen5 | Four calibrated contracts; f02/f04 supported; f14 consistent, f13 unknown. f06 correct fault condition but wrong trigger signature; global gate blocks all5 input stages. | Unattempted generation is not failed input synthesis. Support promotion CPU-only. f06 also misreads shown evidence; concepts were not uniformly correct at every reasoning layer. |
| v33 Luna chain/direct30 | Chain inputs on9/30 tasks, detections8 vs direct25 (post-hoc Python-value equality); no chain-only detections. Of17 direct-only losses,11 terminate unknown/abstain,5 mechanical source/schema rejection,1 input search finds no discriminator. | Main observed loss occurs before input generation. Eight of nine generated-task inputs expose differences, but selected easy tasks/ungolded concept accuracy prevent general capability or causal claims. |
| v27/v28 oracle/full flow | On fixed pilot20 pools, strict property precision Qwen0.14 vs Luna1.00; tool-disabled Luna recheck1.00. Full Luna arms16–17/20 including plain/toolinput. | Oracle capability is a real bottleneck for Qwen7B; stronger model largely removes it on this cohort without establishing concept benefit. Small/HumanEval cohort may be memorized. |
| v34/v35 fault-template | Five of eight concept-over-placebo wins have no exposing concept input; all16 confirmed tests in wins are newly model-written inputs. Fixed template pool exposes17/33 vs plain model discovery19/33; conditional concept ceiling14/33 fails registered threshold17. | Benefit cannot be confidently attributed to a correct site/type concept. Fixed pool is limiting;14 is NOT an upper bound on unrestricted model-generated inputs. Training an inaccurate concept association could preserve the wrong explanation. |

## v33 attribution, checked from saved JSON

The sensitivity excludes equal-Python-value typed-only differences; frozen typed
primary remains chain8/direct26. Python-value sensitivity is chain8/direct25 and
direct-only17. Breakdown:

- 10 S3_terminal_unknown +1 S3_terminal_abstain =11 upstream terminal decisions.
- 3 S2 source_refs +1 S2 behavior_fields +1 S3 comparison_source_refs =5 mechanical
  failures. Six of the seven mechanical failures across the full cohort come from a
  legacy source-reference cap not clearly advertised; these should not be described
  as proven model semantic errors.
- 1 input_search_no_discriminator.

No inference that terminal-unknown cases had correct concepts: v33 has
semantic_accuracy=null, so schema validity is not a semantic gold label. Counts locate
the observed stopping point, not a complete root-cause audit of each stopped task.
The report's optimistic rescue of all7 mechanically blocked tasks yields8+7=15, still
below direct25; this bound holds terminal decisions fixed. Fixing formatting alone
cannot close that measured whole-workflow gap. Equal-input descriptive means8 vs8.37
on shared9-task support also show no demonstrated input-quality advantage; early zero
coverage and selection bias remain part of the scope.

## Consequence for the training idea

Existing experiments support the following distinctions:

1. A verbal normative concept may be right while code/interface/evidence interpretation
   fails later. These are separate learning/engineering targets.
2. A model can already synthesize revealing inputs, sometimes without the purported
   concept being present or correctly exposing the bug. This weakens attribution.
3. A useful input can be discarded by support/retention gates or receive a wrong
   expected output. Input-generation training does not directly repair those losses.
4. Concept and direct may both succeed on the same tasks. Correct explanations do not
   establish additional information or an economical use of inference budget.

Thus no go signal yet for prioritizing concept-to-input training. A claim that such
training addresses the dominant gap would require a defined population of independently
correct concepts, an actual opportunity to generate, unsuccessful concept-conditioned
input search, and evidence that a comparable alternative can reach revealing inputs.
That conditional population has NOT been systematically labeled across these runs.
Current result is a diagnosis and a reduction in confidence in the training proposal,
not proof that training cannot help or that concepts are generally useless.

References: [Luna v23/v24/v25](luna_versions_continue_20261019/REPORT.md),
[v32](v32_scope_support_20261019/REPORT.md), [v33](v33_lunachain30_results.md),
[v27](v27_codexoracle_results.md), [v28](v28_codexflow_results.md),
[v34](v34_ftplacebo_results.md), [v35](v35_concept_ceiling/RESULTS.md).
Historical v34 suggestion to expand K/dataset is superseded by the subsequent
registered v35 stop and the user's signal-before-more-data rule.
