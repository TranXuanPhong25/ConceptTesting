# v12_rel CHANGELOG

2026-10-14. Implementation of the registered B3 concept ablation ladder.
Parent: v11_fair, copied without `out/`, `__pycache__/` or bytecode. All changes
and outputs are confined to this folder. No commit/push, LLM endpoint request,
GPU run, change to shared memory, vendor, root PREREG, Kaggle or v11 output.

## Changes vs v11_fair

- New `relations.py`: CPU extraction of observed data dependence, AST enclosing
  control dependence/base branch outcomes, and lexical docstring spec links.
  Reuses original v7 hint order and unchanged tracer; hides witnesses.
- New `rel_prompts.py`: four ablation blocks, raw-flat compatibility builders,
  fixed generic review checklist and deterministic whitespace-token equalization.
  Target = whole-task rel round-one block; same target across sample requests.
- `config.json`: VERSION `v12_rel`; four fairness flags retained; defaults to
  four new arms and four references (including zero-call witness-only).
- `run_v4.py`, `v4_prompts.py`: selectable arms; internal dependencies, frozen
  legacy seed stride, strict round two and existing caps. Extraction/padding
  runs only when a new arm is selected. References match flat request count.
- `v4_worker.py`, `v4_runtime.py`: isolated relation dispatch and source hashes.
- `run.py`, `v4_evaluation.py`: CLI arm selection, selected-cohort diagnostic
  reporting; B3 oracle = ref only, with no judge/B1/postcondition requests.
- New `rel_report.py`: ref D_I/D_IO/precision, per-task sign comparisons and
  100 fixed-seed random-subset matched-count means. Witness-only expected
  values are placeholders replaced by ref, not generated assertions.
- New `relation_coverage.py`, `RELATIONS.md`, `RELATIONS.json`: reproducible
  offline coverage on frozen 133-task historical v7 bundle, with provenance.
- New `test_rel.py`, `TEST_RESULTS.txt`; copied `test_fair.py` and
  `test_equivalence.py` explicitly select legacy arms for inherited checks.
- `README.md`, `CHANGELOG.md`: v12 usage, compatibility, evidence and limits.
  All other copied files are unchanged, including tracer, mining, selection,
  strategies, scorer, templates and local historical PREREG.

## Verification and results

Offline unittest command (repository root):

```bash
python3 -B -m unittest trickcatcher_linefacts.pipelines.v12_rel.test_rel trickcatcher_linefacts.pipelines.v12_rel.test_fair -v
python3 -B -m trickcatcher_linefacts.pipelines.v12_rel.relation_coverage
```

**33 tests passed**, including 15 B3 tests and 18 inherited fair tests. Tests
cover synthetic and real HumanEval chains, real isolated CPU relation dispatch,
fake-client generation, hidden review targets, equal recorded budgets, empty
hints/inputs, retries and 8-call/20-assertion caps, ref metrics and random subsets.
Raw flat prompts are byte-identical on all 133 tasks; with new arms disabled,
fake-client requests/cache keys and results match v11 (except version/source/
run-id provenance). Inherited fair tests also run real evaluation/oracle CPU
workers with shared tolerant scoring. Both CLI help checks passed. No GPU or
live-LLM behavior is claimed. Actual log: `TEST_RESULTS.txt`.

Coverage: 133 tasks (113 dev + 20 pilot), 254 selected hints. Hints with data
edges: 144; control: 67; spec: 142; all three: 31; any edge: 206. Individual
edges: data 220, control 166, spec 142. Parameter-definition anchors: 66.
Original base checks: 133/133 pass. Tracer step-budget timeouts: 12 base calls,
17 witness calls; partial data observations are retained, incomplete base
branch outcomes are unknown. See generated report for per-task details.

## Status and limits

Implementation and offline verification complete. Registered GPU comparison
has not run. Await v11 dev completion; held-out is gated on rel beating flat
on dev. No commit was created or pushed.

The proxy is not the Qwen tokenizer and balances hint blocks, not entire
prompts or total run tokens (request counts follow the registered flow).
Raw flat byte identity holds before padding; equalized sent prompts differ.
Relations cover observed def-use and syntactically enclosing guards only;
spec links are lexical, may be absent, and are not semantic proofs. No
speculative fallback invents missing edges. Partial traces limit coverage.
- 2026-10-14 (Claude, review before any run): round-two padding target changed from the three-hint rel block to the rel
  rendering of the same single hint (rel_prompts.block); a single round-two hint had been padded with hundreds of filler
  tokens. test_rel budget check now requires equal budgets per unit across arms. test_rel 15/15, test_fair 18/18 OK.
- Status: implemented and reviewed; GPU run after the v11_fair dev sanity run (PREREG "B3 v12_rel").
- 2026-10-14 04:45 (Claude, before the GPU run): v4_evaluation.py MemoryError guard ported from v11_fair (dev sanity
  amendment 2); evaluate is run with the 3600 s sandbox wrapper analysis/v12_eval_longtimeout.py. Tests OK.
