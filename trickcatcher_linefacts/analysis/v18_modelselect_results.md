# v18 candidate construction and selection pilot

20 design dev selection-only pilot, finite frozen input audit; no D_IO comparison

52 CPU tests pass; observed representation17/20; nonempty base-consistent model menus13/20.
One model-ID request per task. All20 responses valid:13 model choices and7 NONE responses.
All menus, input pools, choices and pre-gold execution records were frozen before canonical/contract audit.

| Measure | Tasks /20 |
|---|---:|
| Retained pool contains a sampled-consistent requirement | 12 |
| Displayed menu contains one | 12 |
| LLM selects one | 11 |
| Lexical-rule-first selects one | 12 |
| Uniform over same menu, expected | 9.17 |

Paired LLM vs rule:0 wins/1 loss. Candidate-pool construction is viable here; extra LLM selection benefit is not established.
Among7 menus with differing sampled behaviors in the same output scope: LLM5, rule6, uniform expected3.17. One selected task uses a partial tuple-component requirement, not a full function specification.

| Task | Retained/menu | Pool consistent | LLM | Rule | Confirmed input reports |
|---|---:|---|---|---|---:|
| 27 | 1/1 | True | True | True | 41 |
| 31 | 0/0 | False | False | False | 0 |
| 51 | 2/2 | True | True | True | 4 |
| 56 | 2/2 | True | False | True | 0 |
| 57 | 1/1 | True | True | True | 2 |
| 59 | 0/0 | False | False | False | 0 |
| 63 | 0/0 | False | False | False | 0 |
| 76 | 0/0 | False | False | False | 0 |
| 78 | 0/0 | False | False | False | 0 |
| 85 | 1/1 | True | True | True | 3 |
| 91 | 2/2 | False | False | False | 3 |
| 94 | 0/0 | False | False | False | 0 |
| 98 | 1/1 | True | True | True | 4 |
| 110 | 8/4 | True | True | True | 30 |
| 118 | 2/2 | True | True | True | 4 |
| 126 | 1/1 | True | True | True | 2 |
| 136 | 2/2 | True | True | True | 1 |
| 144 | 0/0 | False | False | False | 0 |
| 149 | 2/2 | True | True | True | 2 |
| 152 | 3/3 | True | True | True | 23 |

Audit:703 valid frozen input calls, zero contract-invalid/unresolved calls. Selected model candidates report119 PUT discrepancies across12 tasks; all119 agree with canonical behavior for the claimed property, zero candidate-property false alarms. These are INPUT-LEVEL reports, not119 bugs and not end-to-end D_IO. The chosen model for task91 is not globally consistent on the pool despite yielding some confirmed reports; no observed false alarms does not certify its requirement.

## Where the misses occur

Seven tasks have no candidates: three opaque representations, scalar algorithms outside the registry, one unsupported algorithm, and task78 whose public calls mix str and empty-list representations. The conservative type abstraction misses the latter even though the generic registry can express its behavior. No tasks are removed from the denominator.
Task91 has base-consistent segmented-word models but neither matches reference behavior on every frozen input. No sampled-consistent model was lost when building the displayed menus. Task56 has both empty=True and empty=False BALANCE models; LLM selects empty=False, causing one audited mismatch, while the lexical rule selects empty=True. This is the sole LLM-vs-rule loss.

## Execution evidence, not free-form rationale

- Task152: input ([0],[1]); absolute-difference model predicts [1], PUT returns [-1]. The signed-subtraction fault alternative matches all59 frozen native calls. Source/state traces contain the list write and return.
- Task149: input ["aa","aa"]; multiplicity-preserving model predicts two occurrences, PUT returns one. Multiple alternatives match this one input; the frozen-pool diagnostic separates them. See JSON rather than assuming a unique cause from one witness.
- Task136: [0,0] yields a normal None for the selected output component, while the PUT raises ValueError. An empty-policy alternative matches this exception type on that input, but this does not uniquely localize which aggregate/guard caused it.
Tool records include model requirement, input relation class, actual effect, source/state observations and alternative matches. Guard sites are observed; uninstrumented logical implications and global correctness are not assumed. Post-hoc fault matching uses only unchanged pre-gold PUT outcomes, never changes primary choices or inputs.

## Costs and limits

Costs: {"logical_selection_requests": 20, "successful_new_requests": 20, "cache_hits": 0, "failed_attempts": 0, "input_tokens": 6410, "output_tokens": 165}.
Candidate ranking is disclosed feature engineering: typed templates, primitive vocabularies, public-base filtering and a lexical/complexity prior. This selection-only pilot does not implement MCTS or show LLM reasoning gains.
No strategy-generation arms, shared-ref assertion/oracle comparison, held-out test or D_IO score was run. A subsequent generation study needs a new protocol with matched concept/rule/random/plain/toolinput/witness controls. Preserve this frozen pilot.
