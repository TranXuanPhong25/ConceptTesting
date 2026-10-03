# PBT_EdgeCases pilot (#36, arXiv 2510.25297, AIware'25)

Question: do tool-computed input-domain concepts appended to the authors' PBT prompt raise the rate at which
LLM-written Hypothesis tests detect the 16 HumanEval canonical-solution bugs, compared with a length- and
format-matched placebo (another task's concepts)?

Everything added for this pilot lives in `run/`. `vendor/` holds the authors' artifact untouched
(Zenodo 10.5281/zenodo.16434613 -> record 17369023, `ebt_pbt_test.zip`, md5 731e774522237f8f62085e0f56a1eb6c,
sha256 3e14da31eaca8fb15282b1ad1899be6555c31a4d8d5f96f136b2f88d5e86281b, CC-BY-4.0). No vendored file was edited; the 64 unpacked files are byte-identical to the zip and there are no extra files (checked 2026-10-02).
Everything runs natively on arm64; there is no emulation.

## Method

| step | what | where |
|---|---|---|
| data | HumanEval + HumanEval+ fetched with the authors' CLI (`pbteval dataset download`, Hugging Face source). sha256 is in RESULTS. | `data/` |
| sanity | The authors' runner on the authors' Claude files reproduces the paper exactly (PBT 11/16, EBT 11/16, same tasks). All 16 HumanEval canonical solutions fail the HumanEval+ tests. All 16 HumanEval+ canonical solutions pass them, so they serve as the fixed reference. | `results/authors_claude_vendored_runner.log`, `results/he_plus_canonical_check.log` |
| arms | `ebt` = authors' EBT prompt. `pbt` = authors' PBT prompt. `pbt_concept` = PBT prompt + concept block. `pbt_placebo` = PBT prompt + placebo block. Prompts are built by the vendored `create_pbt_prompt` / `create_ebt_prompt` and use the authors' system message. | `gen.py`, exact prompts in `gen/prompts/` |
| concepts | `concepts.py` is deterministic and uses no LLM. It parses only the HumanEval `prompt` (signature + docstring) with `ast` and never executes it. Per parameter it emits: type (from the annotation, else the docstring example literals), a domain (from docstring constraints such as `1 <= k <= len(arr)`, "positive", "non-empty", "less than N", "modulo p", "format: mm-dd-yyyy", "only square brackets", and from the example range), edge values per type family, a Hypothesis strategy with bounds, and 3 `@example(...)` witnesses. The rules were frozen before any generation and before any HumanEval+ failing input was looked at. | `concepts/concept/` |
| placebo | Same line count, same category order (param/domain/edges/strategy/constraint/witness), same format, same header. Each line is replaced by a same-category line from another task, chosen by a seeded derangement over tasks with a different signature and padded from the following tasks. Donor names are renamed onto this task's function and parameters. `@example` kwargs are rebuilt to match this task's signature; the self-check asserts that they parse. Character lengths are within about 20-30% (`concepts/summary.json`). | `concepts/placebo/` |
| LLM | Gemini 2.5 Flash on Vertex (the paper used Claude Sonnet 4 via OpenRouter). Default temperature (none sent), `thinking_budget=0`, `max_output_tokens=8192`. Concurrency 1 with backoff on 429. Hard cap $3 on the ledger. Every call is logged to `gen/ledger.jsonl`. K=8 samples per task for EBT and K=10 for the three PBT arms. Calls are interleaved (k, task, arm) so the arms stay balanced. | `gen.py`, `gen/<arm>/k<i>/HumanEval_<n>.txt` |
| execution | Differential executor, see below. | `evaluate.py` |
| stats | Per-task detection rate = share of the K files with at least one detecting unit. Tests are paired at the task level: exact McNemar on per-task majority (rate > 0.5), exact sign test on per-task rate differences, exact sign-flip permutation test on the mean rate difference, and a bootstrap 95% CI over tasks. | `analyze.py` |

### Differential executor (`evaluate.py`)

The paper removed wrong tests by hand. The pilot replaces that with an automatic, arm-blind filter. Every test unit is
run against two solutions:

- buggy: the HumanEval canonical solution, which is what the paper's `run --canonical` executes;
- fixed: the HumanEval+ canonical solution.

A unit is valid if it passes on the fixed solution. It detects if it is valid and fails on the buggy solution
(assertion, exception, or the paper's 15 s timeout).

Units:

- PBT: one pytest node, run alone with `--hypothesis-seed=0` (the same seed on buggy and fixed), with the authors'
  `HYPOTHESIS_SUPPRESS_HEALTH_CHECK` env and a 15 s kill.
- EBT: one top-level check statement, executed in order after the setup statements with a 15 s alarm per statement.
  The authors' runner stops at the first failing assert.

Program assembly reuses the vendored helpers (`extract_code_block`, entry-point removal, `make_canonical_function`,
`REQUIRED_IMPORTS`). Deviations from the authors' runner:

- entry-point removal is also applied to EBT;
- the `detailed_assert` rewrite is not used (it only changes error messages, and it breaks lines that end in a
  comment).

`REPAIR=1` (primary) adds two uniform, arm-blind repairs:

1. prepend `from hypothesis import given, example, settings, assume, strategies as st`. Gemini often writes
   `@example` while importing only `given, st`, as in the prompt's template.
2. if the vendored extraction does not parse, dedent the fenced block. Gemini sometimes indents the whole answer as
   if continuing the function body.

`REPAIR=0` is strict, and both are reported. The file-level number from the authors' own runner (fail on buggy, no
filter) is also reported, via `vendored_run.sh`.

Calibration on the authors' hand-filtered Claude files:

- the filtered metric agrees with the paper on 15/16 tasks for PBT and 15/16 for EBT;
- the only disagreement is HumanEval/76. There the authors kept assertions that contradict the HumanEval+
  reference: `is_simple_power(1, 0) == False`, and n <= 0 cases where buggy hangs but the expected values disagree
  with fixed.

### Security

| role | network | credentials | executes generated code |
|---|---|---|---|
| exec container (`MODE=exec`) | `--network none` | none | yes |
| llm container (`MODE=llm`) | yes | gcloud ADC (read-only) + project/location names | no |

The exec container also has `run/` read-only at `/work`, `run/results` as the only writable mount (at `/out`), a
4 GB / 512-pid limit, and test processes running as `nobody` (`setpriv`) with a 3 GB address-space cap.

`run/results` is mounted at `/out` and not nested under `/work`. The nested rw-under-ro mount turned read-only
mid-run on Docker Desktop while the llm container was writing into `run/`. The resumable evaluator then continued
from where it stopped.

The llm container runs `gen.py`, which only writes model text to files. The key is never printed.

Mounts were verified once with `docker inspect` (`results/exec_container_check.txt`): the exec container has
net=none, no `/gcloud`, and no credential env. `GPG_KEY` is the python image's public key id for the Python source
tarball.

## Commands (from `PBT_EdgeCases/`)

```bash
# vendor (pristine)
curl -L -o vendor/ebt_pbt_test.zip https://zenodo.org/api/records/17369023/files/ebt_pbt_test.zip/content
unzip -q vendor/ebt_pbt_test.zip -d vendor/ebt_pbt_test
# image (arm64, deps from the authors' uv.lock + google-genai)
docker build -t pbt-edge:arm64 -f run/Dockerfile vendor/ebt_pbt_test
# datasets via the authors' CLI (network, no credentials)
MODE=net bash run/dock.sh bash -c 'mkdir -p /tmp/w && cd /tmp/w && python -m pbteval.cli dataset download humaneval && python -m pbteval.cli dataset download humaneval-plus && cp dataset/*.jsonl /work/data/'
# sanity checks
MODE=exec bash run/dock.sh bash -c 'mkdir -p /tmp/w && cd /tmp/w && ln -s /work/data dataset && python -m pbteval.cli run humaneval --plus --source-type canonical --dataset-type standard; python -m pbteval.cli run humaneval --plus --source-type canonical --dataset-type plus' > run/results/he_plus_canonical_check.log
MODE=exec bash run/dock.sh bash -c 'mkdir -p /tmp/w && cd /tmp/w && ln -s /work/data dataset && ln -s /vendor/output output && ln -s /vendor/prompts prompts && for t in pbt ebt; do python -m pbteval.cli run $t --canonical --model anthropic/claude-sonnet-4; done' > run/results/authors_claude_vendored_runner.log
# concepts + placebo (deterministic, host)
python3 run/concepts.py            # -v prints every block
# generation (credentials, no code execution)
MODE=llm K=8 bash run/dock.sh python gen.py
MODE=llm K=10 ARMS=pbt,pbt_concept,pbt_placebo bash run/dock.sh python gen.py
# execution (no credentials, no network); REPAIR=0 for the strict variant (files *_r0.jsonl).
# run/eval_all.sh does all of the following sequentially (one exec container at a time, same CPU load for timeouts)
for R in 1 0; do
  MODE=exec REPAIR=$R WORKERS=8 bash run/dock.sh bash -c "python evaluate.py pbt /out/eval_authors_pbt_r$R.jsonl /vendor/output/pbt/anthropic/claude_sonnet_4 && python evaluate.py ebt /out/eval_authors_ebt_r$R.jsonl /vendor/output/ebt/anthropic/claude_sonnet_4 && python evaluate.py pbt /out/eval_gemini_pbt_r$R.jsonl gen/pbt/k* gen/pbt_concept/k* gen/pbt_placebo/k* && python evaluate.py ebt /out/eval_gemini_ebt_r$R.jsonl gen/ebt/k*"
done
MODE=exec WORKERS=6 bash run/dock.sh bash vendored_run.sh      # authors' runner, file-level, on every Gemini dir
# analysis (reads JSON only)
python3 run/analyze.py r1; python3 run/analyze.py r0
# AndroB2O read-only check (HTTP range requests on the Zenodo zip; APKs streamed into memory, nothing installed)
python3 run/androb2o/inspect_apks.py > run/androb2o/apk_report.json
```
