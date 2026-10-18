# CHANGELOG v21_flowtools

Plan: `trickcatcher_linefacts/PLAN_FLOW_HYPOTHESIS_TOOLS.md`. Design review: `analysis/flowtools_plan_review.md`.

## 2026-10-18 — online runner and Qwen diag16 / pilot20 (steps 3–5 of the plan)

- New: `flow_run.py` (shared concept/behavior/hypothesis, common discovery, 9 LLM arms × 3 calls + witness-only,
  generation freeze, post-freeze scoring), `flow_client.py` + `chat_template.jinja` + `tokenizer_manifest.json`
  (v23 ports), `flow_common.py`, `pilot_fixtures.py` + `fixture_oracles.py` (v23 ports), `flow_tools.parse_call`.
- PREREG amendments 1–3 (format fix for fenced JSON; fixed-tools empty-ids bug; arm-neutral argument
  normalization; operational slot/temp-file fixes). 27 CPU tests pass.
- Results: `analysis/v21_flowtools_results.md`. diag16 ceiling (toolinput = concept+input+hyp = 7/7, the latter
  11 vs 4 false alarms). pilot20: confirmed tasks 1–4/20 per arm, false alarms 19–38; no concept arm passes the
  registered rule → negative/inconclusive. Not promoted.

## 2026-10-18 — P1 CPU flow services and tool dispatcher (no model calls)

- Parent: full copy of `pipelines/v7` (best on dev), hashes and parent commit in `PARENT.json`. Reviewed v22
  mechanical interfaces (source view, literal transport, schemas, store) ported as listed in `PORTS.json`; v22 semantic
  gate not inherited. No outputs/caches copied. v7 files unchanged except `config.json` (`chain` + `flowtools` blocks).
- New files:
  - `flow_cfg.py`: entry-function CFG (sequence, if/else, return, while/for, break/continue, loop-else, explicit raise,
    assert). Try/with/match/nested defs/async/generators fail closed. Only the literal `while True` drops its false edge.
    Control dependence from networkx postdominators (installed `networkx==3.4.2` in the V4 venv); scope = terminating
    paths to normal or explicit-raise exit, `unknown` if a reachable node has no exit path. Data facts: syntactic
    reads/writes/heap-writes-through; reaching definitions and alias/heap propagation `unknown`.
  - `flow_worker.py`: isolated ordinary/traced worker with invocation IDs, code identity, 2,048-event cap (stops
    recording, never changes execution), bounded pre-statement snapshots (4 names, 256 bytes), 2 s / 512 MiB.
  - `flow_trace.py`: line events → CFG nodes; an edge is observed only for a unique CFG transition between consecutive
    mapped events of one invocation. Same-line statements, unmapped lines, truncation, implicit exceptions break proof
    segments. `not_observed` only on complete unbroken traces; `check_path` = contiguous ordered sequence in one invocation.
  - `flow_tools.py`: JSON-action dispatcher (`inspect_flow`, `inspect_data`, `replay_input`, `check_path`), 2 rounds × 6
    actions, 18 execution requests/arm, 6 final inputs (no revision), 6 common discovery inputs (separate counter).
    Invalid calls consume slots and return typed errors; invalid replays also consume an execution slot. Append-only
    ledger; resume replays logged results and rejects drift. Executions cached per task (physical vs logical counters).
    Native/traced agreement required before any trace evidence. `fixed_schedule` = predeclared query order.
  - `flow_packages.py`: arm packages (`concept+hyp`, `input+hyp`, `concept+input+hyp`, `agent-tools`, `fixed-tools`,
    `flow+input`, `toolinput`, `plain`, `placebo+input`, `witness-only`) with provenance labels; model rank kept;
    `concept+hyp` has no concrete inputs/traces/outputs; `flow+input` gets the same structural facts without hypotheses.
  - `test_flowtools.py`: 23 CPU tests (early return, unreachable, loops/else, break/continue, while True, unsupported
    constructs, Unicode byte columns, ordered paths, recursion, same-line ambiguity, raise/implicit exceptions, mutation,
    truncation, snapshots, budgets, resume/drift, shared cache, discovery/final budgets, fixed schedule, packages).
  - `p1_interface_check.py`: CPU interface check on the 133 selection PUTs with public docstring `>>>` inputs.
- Design delta vs review: explicit `raise`/failing `assert` go to a `RAISE_EXIT` node included in the postdominator
  sink (review said normal exit only); implicit exceptions are still not modeled.
- Results (CPU interface only, no efficacy claim): tests 23/23 pass. Interface check: CFG supported 130/133 (Try 1,
  nested FunctionDef 2); 55 tasks have docstring inputs (136 inputs); native agreement 136/136; traces fully proven
  134/136 (2 hit the 2,048-event cap, tasks 31 and 49 → `unknown`, as designed). 272 worker processes, 0 model calls.
  Output: `out/pipelines/v21_flowtools/humaneval/p1_interface/summary.json`.
- Status: P1 done. Not done / still gated: online Qwen runner for S1–S3 + tool rounds (endpoint offline since v25),
  frozen parent fuzz-witness selector for common discovery, controlled semantic diagnostic with human adjudication,
  20-task dev pilot, PREREG for any comparison. `chain.py` still lazily imports v22 `execution_adapter` (not ported).

## v7 base (copied)

- 10f991c (2026-10-13): self-contained copy of the v7 pipeline. Current best on dev (v8-strict construction:
  concept-hybrid 61.0 vs plain-hybrid 55.7, per task 29/20 n.s.).
