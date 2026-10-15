# v18_modelselect — selection-only pilot

New copy of v17_templates; no MCTS. Tool enumerates <=2048 typed model configurations,
filters all public base observations, ranks with a disclosed lexical/complexity prior, keeps
<=64 and displays <=4, prioritizing sampled behavior diversity. IDs are shuffled; the prompt
hides rule ranks and internal pool IDs. LLM returns one menu ID/NONE, not parameters or rationale.
No task-number/function-name dispatch. Primitive parameter vocabulary includes English vowels,
mathematically computed prime-valued hexadecimal digits and public quoted literals.

CPU: 52 tests; representation17/20; nonempty candidate menus13/20, seven behavior-ambiguous menus.
Task78 abstains because public base inputs mix strings and empty list; the current type abstraction
is conservative. Unsupported tasks remain in the denominator. Nonempty is not semantic correctness.

```bash
python3 -B -m trickcatcher_linefacts.pipelines.v18_modelselect.selection_experiment all --online --workers 2
```

Use `selection_experiment` only; inherited `behavior_experiment` is foundation code, not this pilot CLI.

One Qwen call/task, max256 tokens, no content repair, <=20 completions. Source/config/menu/input
pool/choice/evidence hashes freeze BEFORE canonical/contract selection audit. Pool <=80 literal
calls/task, uniformly mined-valid; literal representations do not preserve hidden argument aliasing.
Tool evidence records actual observed source/state and model/PUT discrepancies; no free-form
rationale is accepted as proof. Fault matches on a witness are not unique causal explanations.

Audit distinguishes retained-pool coverage, displayed-menu coverage, LLM missed available models,
rule-first and uniform controls on the exact same menu, and partial output-component requirements.
Consistency means agreement on valid resolved frozen inputs, not universal spec correctness.
This pilot ends after the audit. NO strategy generation, end-to-end D_IO or held-out comparison.
A future generation experiment needs a separate preregistration; audit does not feed back into
this run's model construction/choice. See root PREREG v18 and selection_pilot outputs.
