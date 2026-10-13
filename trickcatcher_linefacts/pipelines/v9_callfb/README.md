# v9_callfb

Created with `cp -r pipelines/v7 pipelines/v9_callfb`. The config version is
`v9_callfb`; normal experiment outputs are version-scoped under
`trickcatcher_linefacts/out/pipelines/v9_callfb/humaneval/`.

## Changes from v7

- Only hybrid round two changes. The hint pool, hint selection, round-one
  prompts, parameters and seeds, and the four other arms retain v7 behavior.
  Concept-hybrid shares concept's round one; plain-hybrid shares plain's round
  one; placebo-hybrid retains its own placebo round one. Reusing the historical
  generation cache gives the same round-one request keys.
- Each shown hint missed by round one gets a request for exactly five concrete
  `entry(...)` calls with literal arguments, given specification, PUT, base tests,
  round-one assertions and hint. No Hypothesis strategy or 100-draw generator is
  used in hybrid round two. Literal keyword calls/defaults are normalized to
  positional calls using the source signature without executing the PUT.
- The existing namespace sandbox/classifier evaluates the calls. Structured
  feedback reports mined validity and the failed condition; reach of the hint's
  line/site; the target branch/value class or local mutation difference; and
  PUT-versus-mutant output difference for MUTANT hints. Branch/boundary feedback
  includes observed cells and compared operand values where available. Mutation
  feedback compares the changed expression's values, or locals around a changed
  statement. Diagnostics are bounded to 64 observations and 300 characters per
  value; unavailable measurements are `null`, and failures are recorded without
  changing the existing validity/fact-hit rules. Invalid literal inputs can be
  traced for diagnostics but cannot be kept.
- After feedback, there are up to two further proposal requests (three attempts
  total). Distinct valid hitting calls accumulate across attempts; finding two
  stops a targeted hint early. Up to two are selected per hint with a seeded
  choice, then deduplicated across hints. OUTCOME, STMT, MUTANT and SPEC hits use
  the existing fact-hit/input-class machinery; reach alone does not qualify a
  MUTANT call.
- Plain-hybrid gets exactly concept-hybrid's **proposal request count** per
  task/sample, including retries. It follows the same group sizes and feedback
  loop, keeps up to two valid calls per group, and receives only validity and
  whether output is new versus its own round-one PUT outputs. It receives no
  hint, mutant information, trigger condition, or PUT output values in feedback.
  Placebo-hybrid uses the targeted loop with the unchanged placebo hints.
- The final expected-value request is separate and made only when the arm kept
  calls: “For each call below write `assert <call> == <expected>`; do not add other
  assertions”. Only direct equality assertions on the kept literal calls with
  literal expected values survive. Extra calls, helpers, nested calls, duplicate
  expected values and non-equality assertions are discarded. Every kept call
  remains represented: omitted/unparseable expected values get an explicit
  `None` placeholder, as in v8-strict, and are listed in
  `round2_missing_expected_calls`. These placeholders preserve ref input scoring;
  they are not claimed to be correct o0 expected values.
- New requests/selection use a disjoint seed range starting at 1,600,000,000.
  Round-one seeds and all non-hybrid seeds remain v7's. Results record
  `round2_proposal_requests`, `round2_oracle_requests`, and
  `round2_proposal_schedule`; the legacy `round2_strategy_requests` field remains
  an alias for proposal count. Oracle counts can differ between arms.
- For explicitly identified v3m2 bundles, derived library conditions in
  `out/trigger_conditions/conditions.json` can be rendered in feedback as
  “inputs satisfying C reach it”, using only `descs`, never the witness/example
  in the historical rendered hint. Historical conditions are not transferred
  to v7's changed validator/fact pool: v7 trigger inference is omitted in this
  version, as permitted by the task.
- The copied CLI adds `--split dev` / `--split pilot` for the arms stage. This
  only filters tasks, not hints. `dry_run.py`, `test_callfb.py`, and the validation
  summary are new offline verification artifacts. `PREREG.md` is an unchanged
  copy of v7's registration; this README documents the v9 implementation delta.

## Offline verification

From `/home/phong/dev/ConceptTester`:

```bash
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.test_callfb
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.dry_run
```

The tests compare all 1,197 historical round-one requests/cache keys (133 tasks,
three samples, three unique round-one arms). They cover parsing, feedback,
accumulation/early stopping, seeded selection, strict filtering, missing expected
values, proposal-budget matching, and skipping an empty expected-value request.
The dry run uses dev tasks 2, 3, 4, all seven arms, one sample, a scripted fake
client and the real validator/tracer/mutant sandboxes. It measures protocol and
execution, not bug-detection quality. All verification writes stay inside this
folder; sandbox artifacts are temporary and the summary is
`validation/dry_run_summary.json`. The dedicated v4 interpreter from config must
exist with the pinned packages; `--python /path/to/venv/bin/python` can override
the dry-run interpreter.

Implementation validation: **16 tests passed**, with **1,197/1,197 historical
round-one cache hits**. The standalone dry run completed **21 rows** using **80
fake requests**; concept/plain proposal counts were **9/9, 9/9, 3/3** for tasks
2/3/4. No online requests were made.

## Dev experiment commands

These commands are provided for a later experiment and were **not** run online
during implementation. Use the dedicated pinned v4 interpreter. The copied CLI
defaults to offline cache replay; `--online` explicitly enables new requests.
Configure the existing endpoint separately before the GPU commands.

```bash
# CPU: copy reusable mining/facts/specfacts/caches and build the unchanged hints.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run bundle \
  --reuse-from trickcatcher_linefacts/out

# GPU: all seven arms, dev only, K=3. Round one reuses the copied v7 cache.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run arms \
  --split dev --k 3 --workers 12 --online

# CPU: o0 evaluation and report.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run evaluate
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run report

# CPU: collect inputs for post-hoc oracle scoring.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run oracle-collect

# GPU: B1, reference-program and postcondition expected-value stages.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run oracle-llm \
  --oracle-stages b1,ref,post --workers 12 --online

# CPU execution plus GPU judge requests where the copied oracle requires them.
python3 -B -m trickcatcher_linefacts.pipelines.v9_callfb.run oracle-score \
  --workers 12 --online
```

All stages also accept `--python /path/to/venv/bin/python`. A packaged v7 run
can be reused with `--reuse-from
trickcatcher_linefacts/out/pipelines/v7/humaneval` instead of the legacy `out`
directory. Run mining/facts/specfacts stages first if the chosen reuse source is
incomplete. Ref scoring replaces written expected values; comparison of input
discovery therefore matches proposal budgets independently of oracle counts.

To inspect the copy delta without touching v7:

```bash
git diff --no-index --stat -- \
  trickcatcher_linefacts/pipelines/v7 \
  trickcatcher_linefacts/pipelines/v9_callfb
```
