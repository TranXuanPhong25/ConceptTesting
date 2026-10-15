# New concept variants, 2026-10-14

```mermaid
flowchart LR
  V7[v7 frozen foundation] --> V11[v11 fair: dev results complete]
  V11 --> V12[v12 relations: existing experiment]
  V12 --> V13[v13 hypotheses: CPU machinery]
  V13 --> V14[v14 obligation graph: proposal format failure]
  V13 --> V15[v15 conditional MR concepts: proposal format failure]
```

| Variant | New concept use | Main exploratory contrast | Status |
|---|---|---|---|
| [v14_obgraph](v14_obgraph/README.md) | Spec obligation + tool concept anchor + connected dependency path + T/O | graph vs same-evidence cards | GPU complete; 0 accepted cards/20 tasks |
| [v15_mrconcept](v15_mrconcept/README.md) | Conditional family + D/tau/rho + valid source/follow-up pairs | guided vs blind, identical pair filter | GPU complete; 0 accepted cards/20 tasks |

Both add original/new-pool toolinput and witness-only controls and keep main detection on common saved ref responses.
Each proposes up to six cards, shows up to three and has three strategy slots/sample. Initial scope is 20 dev tasks,
K=1; no held-out run. v14 consumes at most 440 logical model requests, v15 at most 380 (820 combined), including
shared proposal calls, excluding transport retries and cache hits from actual new usage. Ref responses are already
cached; no new expected-value/reference requests are required. Actual tokens must be reported after the online run.

References informing design are in [the research report](../research/relations_2026-10-14/REPORT.md).
Both variants are original LineFacts adaptations, not implementations of PromeFuzz/MR-Coupler/MemoRIA.
The user subsequently corrected the order: resume B3 then B4 before returning to v14/v15. The two smoke runs
had already finished when this correction arrived; their zero-card failure is recorded without changing treatment.
The private Claude diagram has not been edited; this local tree records the new variants for the next handoff.

## Ordered format-repair copies

Initially gated on B3 and B4 scoring. User later authorized using the GPU during B4 CPU-heavy work;
the new overlap chain runs
[v14_obgraph_py](v14_obgraph_py/README.md) then [v15_mrconcept_py](v15_mrconcept_py/README.md).
Only Python/JSON proposal guidance changes; zero accepted cards now stops generation. 30 CPU tests pass,
20-task preparation is complete; v14 model stages launched alongside B4 with two workers, then v15.
The dormant old waiter was stopped; original method budgets/seeds/validators remain frozen.
See [GPU queue](../GPU_QUEUE-2026-10-14.md) for progress paths, dependency gates and resume rules.

GPU restart checkpoint: repaired v14 accepted 5 shown cards on 3/20 tasks and enabled generation.
The original v14 zero-card result remains separate; repaired effectiveness scoring is pending.

Completed repaired runs: v14 has 5 shown cards on 3/20 tasks, primary graph/card D_IO 6/6;
v15 has 41 shown cards on 16/20 tasks, MR/blind D_IO 5/5. See RESULTS §11.46 and the tracked
[format-repair report](../analysis/v14_v15_format_repair.md). B4 generation completed and CPU evaluation is running.

B4 final: full native ref score completed, hyp-hybrid 46.33 vs flat 62.67/toolinput 63.00 tasks/run
on dev; registered primary comparisons favor controls. RESULTS §11.47. All B3/B4/repaired v14/v15 runs
are complete. New FSM/spec-mutation direction remains a plan, not an implemented variant.


## Behavioral concept foundation, 2026-10-15

```mermaid
flowchart LR
  V11[v11_fair] --> V16[v16_behavior: CPU IPC limit]
  V16 --> V16C[v16_behavior_compact: representation gate 17/20]
  V16C --> C[Spec-only DSL obligations + concept binding: awaiting live Qwen]
  C --> G[Conditional seven-arm generation + shared-ref score]
```

[CPU validation](v16_behavior_compact/CPU_VALIDATION.md): 26 tests, zero model calls.
Concept = candidate quoted requirement + semantic family + fault alternative + discriminator;
IR/FSM is supporting evidence, not the semantic concept itself. The machine projects observed
state predicates, not all program executions. Primary planned contrast remains behavior+concept
vs the same behavior representation. No D_IO result or completed concept gate yet.


```mermaid
flowchart LR
  V16C[v16_behavior_compact: storage repair] --> V16R[v16_behavior_ready: schema hardening]
  V16R --> P[Concept proposal gate: not run]
```

Ready copy repeats the representation gate 17/20 and passes 29 CPU tests. Use
[v16_behavior_ready](v16_behavior_ready/README.md) for continuation; no model calls or D_IO yet.


## v16 GPU gate outcome, 2026-10-15

v16_behavior_ready: CPU representation 17/20; semantic concept gate **0/20** (requires 10).
Six quoted/schema candidate obligations, zero cards. Forty new model completions; generation
stopped, no D_IO. Frozen external import-preload resume reused three exact cache entries.
[Full gate/rejection/cost report](../analysis/v16_behavior_gate_results.md).


## v17 compiled templates, 2026-10-15

```mermaid
flowchart LR
  V16R[v16 ready: concept gate 0/20] --> V17[v17 typed spec templates: gate 2/20]
  V17 --> Stop[Generation stopped; no D_IO]
  V17 --> Probe[Separate six synthetic cases: choose 6/6, construct + schema + examples 1/6]
```

Registry uses nine generic operations without task-ID dispatch. Tool compiles semantic model
alternatives and discriminator comparisons; Qwen chooses parameters/source bindings. Two technically
accepted cards do not demonstrate explicit reasoning: one copies placeholder rationale, one supplies
an unsupported explanation. Probe suggests investigating tool-generated candidates + LLM selection,
not treating synthetic accuracy as a benchmark result. No next pipeline launched.
[Report](../analysis/v17_template_results.md).


## v18 model selection pilot, 2026-10-15

```mermaid
flowchart LR
  V17[v17: parameter generation gate2/20] --> V18[v18: tool enumerates/base-filters models]
  V18 --> Menu[13/20 menus;12/20 contain sampled-consistent model]
  Menu --> Choice[LLM11 vs rule12 vs uniform9.17]
  Choice --> Audit[Frozen-pool audit; no D_IO generation run]
```

52 tests; no MCTS. Tool-produced flow/effect evidence supports bounded fault discrimination,
but LLM selection adds no measured gain over lexical-rule-first.119 input-level candidate
reports confirmed by canonical across12 tasks, zero observed false alarms; one selected model
is a partial output-component property and one is not consistent over the entire pool.
[Report](../analysis/v18_modelselect_results.md). No subsequent generation experiment launched.
