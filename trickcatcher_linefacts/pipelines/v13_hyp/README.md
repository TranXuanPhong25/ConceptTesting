# v12_rel — B3 concept ablation ladder

> **v13_hyp note:** this README is inherited from v12_rel. B4 changes: `CHANGELOG.md`; CPU checks and GPU commands:
> `HYPOTHESES.md`. Default arms: hyp-hybrid, hyp-witness-only, flat-hybrid, rel-hybrid, plain-hybrid, toolinput, witness-only.

Self-contained copy of v11_fair, excluding `out/`, `__pycache__/` and bytecode.
The normative design is root `trickcatcher_linefacts/PREREG.md`, section
**B3 v12_rel: concept ablation ladder** (2026-10-14). The copied local PREREG and
EQUIVALENCE files are historical records, unchanged from v11, not v12 results.
All four fairness flags remain on. No live generation or endpoint run has been done.

## Arms and execution

Config defaults to `review-hybrid flat-hybrid rel-hybrid rel-nospec-hybrid
plain-hybrid toolinput witness-only placebo-hybrid`. The original seven arms
remain supported. Choose a subset through `--arms` on either CLI or `config.json`.
The B3 comparison should retain all four references.

- `review-hybrid`: fixed checklist (boundaries, off-by-one, empty/singleton,
  ordering/ties, types, large values). The same selected concept hints are used
  internally to find missed targets and verify draws; they are absent from prompts.
- `flat-hybrid`: original concept-hybrid hint sentences and round-two target text.
- `rel-hybrid`: those same sentences, with typed data/control/spec chains.
- `rel-nospec-hybrid`: same chains with spec-link edges removed. The ordinary
  specification/docstring is still visible to every arm.
- `witness-only`: first three valid deduplicated selected witnesses; zero LLM
  calls. Its `== None` assertions are collection placeholders. Ref replaces
  their expected values; their own-expected-value diagnostic metrics are meaningless.

New arms use the existing strict Hypothesis flow: classify round-one assertions,
one request per missed hint with at most one retry, draw 100 inputs, retain at
most two verified hits per hint, deduplicate and exclude round-one inputs, then
request expected values for exactly those retained calls. Skip that last request
if none remain. Caps: 8 logical calls and 20 assertions per sample. Plain/placebo
references match flat-hybrid's strategy-request count in a B3 run; dependency
arms execute internally without extra exported rows. K defaults to 3. Hint
selection and input-domain strategies are unchanged.

Offline commands, from repository root:

```bash
python3 -B -m unittest trickcatcher_linefacts.pipelines.v12_rel.test_rel trickcatcher_linefacts.pipelines.v12_rel.test_fair -v
python3 -B -m trickcatcher_linefacts.pipelines.v12_rel.relation_coverage
python3 -B -m trickcatcher_linefacts.pipelines.v12_rel.run_v4 --help
```

`run_v4 arms --tasks <v7-format-bundle> --out-dir <v12_rel/out/humaneval/run>
--arms ...` accepts a read-only bundle source outside the output folder. It
uses an offline cache client by default and confines outputs to this copy.
The unified `run` CLI retains the mine/facts/specfacts/bundle workflow, supports
`--arms`, and defaults oracle generation to `ref`. B3 oracle scoring uses
`rel_report.py`: no judge, B1 or postcondition request. It reports dev and pilot
separately, D_I, D_IO, precision, registered per-task sign comparisons, and
100 fixed-seed random equal-size subsets (means, not prefix truncation).

The registered future GPU gate still applies: dev only after v11_fair dev
sanity completes; held-out only if rel-hybrid beats flat-hybrid on dev.

## Input budget and compatibility

The proxy counts non-whitespace runs (`re.findall(r'\S+', block)`), not the
model's tokenizer. Each task's budget is the complete rel-hybrid round-one
hint block length. Every hint block in every request of that sample, including
single-target strategy requests, references, retries and expected-value requests,
uses that same budget. Pad with `.` tokens; truncate at token boundaries. PUT,
docstring, base tests, domain strategy and assertions are never truncated.
`hint_budgets` records target/raw/actual length, padding/truncation, request label
and hint index. Zero selected hints means zero budget, so the review checklist
is omitted too. Witness-only has no prompt.

The **raw, before-padding** flat round-one and round-two prompts are byte-identical
to v11 concept-hybrid, verified on all 133 tasks. Sent prompts necessarily differ
when padding is enabled. Byte identity and a larger equalized rel budget cannot
both hold for a flat block; this distinction is explicit in the API and tests.

With all new arms disabled (e.g. `--arms plain concept toolinput gen-plain
concept-hybrid placebo-hybrid plain-hybrid`), there is no extraction or padding.
Legacy seeds keep their seven-arm stride and legacy cache keys are identical.
Fake-client end-to-end results equal v11 except version/source/run-id provenance.

## Relation limits and verification

`relations.py` replays original base calls and selected witnesses using the
unchanged tracer. Generation extracts relations in isolated CPU workers before
starting the threaded LLM loop. Existing trace records can also be supplied.
No witness inputs enter rendered hint chains. Data edges are observed def-use
pairs, including loop-carried updates; no static edges are fabricated. Control
edges cover syntactically enclosing if/while/for guards. This is not a full
postdominator graph; loop else exhaustion is omitted. Truncated base traces
make branch outcomes unknown. Comprehensions/lambdas and object mutation have
the original tracer's limits.

Docstring prose before doctests is split into sentences. Identifier words and
operator synonyms score lexical overlap; ties choose the earliest sentence,
zero overlap yields no link. These links are lexical associations, not proved
specification obligations. SPEC hints with no executable line use a labelled
parameter-definition anchor.

Actual test log: `TEST_RESULTS.txt`. Coverage, edge counts, source hashes,
per-hint metadata and examples: `RELATIONS.md` and `RELATIONS.json`.
