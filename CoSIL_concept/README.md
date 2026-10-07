# CoSIL + concept tags (stock / concept / placebo / ide)

Paper: *CoSIL: Issue Localization via LLM-Driven Iterative Code Graph Searching* (ASE 2025, arXiv 2503.22424),
code <https://github.com/ZhonghaoJiang/CoSIL> (no license; private research use), pinned at
**`0568e423735b399d5b089996961fea9ae142e4c7`** (master, 2026-05-31) and cloned by `setup.sh` into `vendor/CoSIL`
(gitignored, never edited; `setup.sh` refuses to run if it has local edits).

**Question.** In CoSIL's function-level stage the LLM sees only function/method *names* of the top-5 files and opens
about 7 bodies with tools. Do C1-C8 tags computed from the unread bodies (`concept_annotator_py.functions`) help it
decide where to look, beyond a placebo with the same tags on the wrong functions, and beyond ordinary linter
warnings (`ide`)? If concepts don't beat the linter, they add nothing over existing tools.

## Arms (differ only in the name listings)

The only place CoSIL lists function/method names to the LLM is `CoSIL.consturct_bug_file_list` (`CoSIL/fl/CoSIL.py`),
built from `FL_tools.get_functions_of_file` (static functions) and `FL_tools.get_functions_of_class` (class
functions). Its text goes into the tool-loop user prompt, and twice into the final summary prompt (directly and via
`location_summary`). `cosil_concept.py` replaces those two functions in both `FL_tools` and `CoSIL.fl.CoSIL`. The file
stage (`file_localize_with_g`) shows only the file tree and import lines, so all arms share one file-stage run.
CoSIL's pipeline uses no skeleton or compressed view (`get_skeleton` is unused Agentless code), and class names
(`class:` lists) stay untagged in every arm.

| arm | listing entry |
|---|---|
| `stock` | `read_cell` |
| `concept` | `read_cell  [C1 value_type=None … · C2 not cell.childNodes · C4 catches ValueError · C6 float()]` (`render_tags(annotate_function(body))`) |
| `placebo` | the same file's non-empty tag strings, shuffled among that file's tagged functions (seeded; a derangement), untagged functions stay untagged |
| `ide` | `parse_column_identifiers  [B904 raise-without-from-inside-except raise ... from err]`: ruff warnings inside the function's span, rendered with the same `render_tags` cap; functions without warnings stay bare |

`ide` uses ruff 0.16.10 (pinned, CPU, pip). Settings:
- `--select F,B,PLE,PLW,RUF,S`: pyflakes, bugbear, pylint errors/warnings, ruff-specific, bandit.
- `--ignore S101,RUF001-003,RUF100,RUF005,RUF010,RUF021-023`: assert-used, ambiguous unicode, unused-noqa (an artifact of the partial rule selection) and pure-style RUF rules.
- `--isolated`, `--target-version py313`.

`./run.sh lint <ds>` writes every `.py` file of a built structure (base commit) to a temp dir, runs ruff once, and maps each
warning to every listed function/method whose span contains it. This mirrors the concept tags, where a nested function's
body also counts for the enclosing function. Output goes to `structures/<ds>/<iid>.lint.json`; the step is resumable and
takes about 1 s per instance (azure-sdk 53 s).

pylint is skipped: without each repo's dependencies installed its inference is noisy, and it is slow (minutes on
django). ruff's `PLE`/`PLW` reimplement the pylint error/warning subset. pyright is skipped too (needs node).

Tag rates, from `check_tags.py` Q1b on the functions of gold files:
- concept: 78% (19 Lite instances) and 63% (12 Live instances);
- ide: 14% and 6%.

Over all functions of whole repos, ide tags 7.1% (Live sample) and 10.5% (Lite sample). Gold functions carry warnings
more often than their neighbours: Lite 35% vs 13.5% (Fisher p=0.016), Live 8.8% vs 5.4% (n.s.).

The following patches apply to all arms, so no arm differs because of them:
- LiteLLM `completion` goes to Vertex `vertex_ai/gemini-2.5-flash` with thinking budget 0 (verified: 0 thinking tokens), retries 429/5xx with backoff, and logs every call to `out/<ds>/ledger.jsonl`.
- Tool arguments and `<name>` answers are cut at the first whitespace, so an echoed tag never breaks a lookup or the scoring.
- `FL_tools.load_json` is cached. CoSIL re-reads the whole structure about 60 times per instance; a replay confirmed identical listings.
- Each listing is saved to `work/<ds>/<arm>/listings/` for audit.

Temperatures, prompts, `max_retry=10`, top-5 files and the prune sub-agent (`localize_with_p`) are the authors'.

## Datasets (`./run.sh data`, pinned HF revisions)

| name | source | instances | notes |
|---|---|---|---|
| `swebench_live` (**primary**) | SWE-bench-Live `verified` ∪ `lite` @ `b51a8642` | **225** (84 repos) created ≥ 2025-02-01 | after Gemini 2.5 Flash's Jan 2025 cutoff; ids in `data/swebench_live_ids.txt`; gt derived from the gold patch over the base-commit structure |
| `locbench` (secondary) | `czlll/Loc-Bench_V1` @ `c44cf3b7`, category *Bug Report* | 242 (67 repos) | gt = LocBench `edit_functions` + patched files; all created before Feb 2025 |
| `swebench_lite` (reference) | `princeton-nlp/SWE-bench_Lite` @ `6ec7bb89` | 300 | gt = the authors' `evaluation/gt.json`; run `stock` only, to compare with the paper |

Patch-derived gt follows the authors' conventions (`file::Class.method`, `file::func`, `file`). On 19 Lite instances it
matches the authors' gt.json method sets 17/19. The two misses are a nested function and an unpatched sibling.

## Runbook (fresh x86_64 Linux, no GPU)

Prerequisites:
- `git`, plus `uv` (preferred: it fetches Python 3.11 itself) or `python3.10`-`python3.12`. The default `python3` is never used.
- No compiler: every dependency ships x86_64 wheels, and CoSIL parses with stdlib `ast` (no tree-sitter).
- ADC credentials at `~/.config/gcloud/application_default_credentials.json`, from `gcloud auth application-default login` on any machine; copying the file over is fine.
- `scripts/vertex_env.sh` at the repo root exporting `VERTEX_PROJECT` and `VERTEX_LOCATION`. `run.sh` sources it silently and maps the values to LiteLLM's `VERTEXAI_PROJECT`/`VERTEXAI_LOCATION`. `LLM_MODEL` in that file is ignored; set `COSIL_MODEL` to override.

```bash
cd ~/dev/ConceptTester && git pull && cd CoSIL_concept
./run.sh setup                     # ~2 min: vendor/CoSIL @ pinned SHA, .venv (py3.11), deps, selftest
./run.sh data                      # ~1 min: data/*.jsonl, ids, gt
./run.sh smoke                     # ~15-35 min, ~$0.35: 3 instances x 4 arms + verify + eval
mkdir -p work                      # long steps: no tmux, so detach with nohup setsid
nohup setsid ./run.sh structures swebench_live --jobs 6 > work/structures_live.log 2>&1 &
nohup setsid ./run.sh run all swebench_live > work/run_live.log 2>&1 &     # files, lint, then 4 arms in parallel
tail -f work/run_live.log work/swebench_live/run_*.log
# ide added after the other arms already ran? `./run.sh run ide swebench_live` (lints first; reuses files.jsonl)
./run.sh eval swebench_live && ./run.sh analyze swebench_live
# secondary + reference
nohup setsid sh -c './run.sh structures locbench --jobs 6 && ./run.sh run all locbench' > work/locbench.log 2>&1 &
nohup setsid sh -c './run.sh structures swebench_lite --jobs 6 && ./run.sh run files swebench_lite && ./run.sh run stock swebench_lite' > work/lite.log 2>&1 &
./run.sh eval locbench && ./run.sh analyze locbench && ./run.sh eval swebench_lite
git add out data && git commit -m "results(CoSIL_concept): ..." && git push     # or scp -r out/ back
```

Useful knobs:
- `--limit N` or `--ids FILE` on `run`, `structures` and `lint`.
- `COSIL_THREADS` (default 4 per arm process); 429s are frequent, so raise it carefully.
- `COSIL_MAX_USD`: per-process spend cap; the process stops cleanly once it is reached.
- `VERTEXAI_LOCATION=us-central1` to try a regional endpoint when the global one keeps returning 429.

## Expected time / disk / cost

Measured in the arm64 smoke (3 small repos):
- about 30 LLM calls per instance per arm, about $0.025 per instance per arm, and $0.002 per instance for the file stage;
- 4-8 min wall time per instance at 3 threads, mostly 429 backoff (up to 8 tries per call);
- about $0.23-0.25 per smoke run.

Larger repos have longer listings and tool results, so the estimates below assume $0.03-0.05 per instance per arm.

| step | time | disk | cost |
|---|---|---|---|
| setup / data | 2 min / 1 min | 0.6 GB venv | 0 |
| structures `swebench_live` (225) | ~30-60 min at `--jobs 6` | ~6-8 GB structures + ~4 GB clones | 0 |
| structures `locbench` (242) | ~30-60 min | ~5 GB + clones | 0 |
| structures `swebench_lite` (300) | ~45 min (django 18 s, 42 MB each) | ~10 GB + ~1.5 GB clones | 0 |
| run `swebench_live`: files | ~1 h | small | ~$1-2 |
| lint (any dataset) | ~1 s per instance (azure 53 s) | ~KB per instance | 0 |
| run `swebench_live`: per arm (4 arms) | ~6-10 h at 4 threads, 429-bound; the four arms run in parallel | small | **~$7-11 per arm** |
| run `locbench`: per arm | similar | small | ~$7-12 per arm |
| run `swebench_lite`: files + stock | ~10 h | small | ~$15-20 |

Sample structure sizes: matplotlib 23 MB, keras 24 MB, conan 18 MB, haystack 8 MB. **Azure/azure-sdk-for-python** (1 live
instance) is the outlier:
- 1.65 GB of JSON, 12 min to build;
- about 3.3 GB of RAM per loaded copy, two copies per arm process while it runs;
- a ~300k-token file-stage prompt.

Each arm starts at a different quarter of the instance list, so parallel arms do not load it at the same moment.

## Resume, outputs

Every command is idempotent:
- Structures skip finished JSONs.
- Runs append one line per finished instance and skip it on rerun; failed instances (429 exhaustion, budget cap, crashes) are simply retried.
- The function stage only runs instances that have file-stage output.

Results go to `out/<ds>/` (small; **commit or copy back**):
- `files.jsonl`, `stock.jsonl`, `concept.jsonl`, `placebo.jsonl`, `ide.jsonl`: predictions in the authors' format;
- `ledger.jsonl`: tokens and USD per call;
- `metrics.json`: the authors' Acc@1/3/5, MAP and MRR, file and function level;
- `per_instance.jsonl`: per arm, with the gold function's concepts;
- `stats.json`: exact McNemar on function Acc@5/1/3 and Wilcoxon on reciprocal rank for concept vs placebo (primary), concept vs stock, placebo vs stock, **concept vs ide** and **ide vs stock**, plus a per-concept breakdown and cost;
- `check_tags.txt`: the offline annotator check; `verify_smoke.txt`.

Full trajectories, logs and listings stay in `work/` (gitignored).
`out/smoke_arm64/` is the local smoke on the Mac. It is kept separate so the x86 run doesn't resume from it.

## Files

- `setup.sh`, `run.sh`: the driver.
- `prepare.py`: datasets; structures built with CoSIL's own `create_structure` from one partial bare clone per repo plus a temporary `git worktree`; patch → gt; `lint` (ruff → ide tags).
- `cosil_concept.py`: launcher and monkeypatches, arms, `verify`.
- `analyze.py`: eval with the authors' `evaluation/FLEvalNew.py` functions, plus stats.
- `check_tags.py`: the offline check (no LLM). Do gold functions carry tags more often than the other functions of the same files? Do the concepts the fix adds already show in the pre-patch tags?

Selftests: `python cosil_concept.py selftest`, `python check_tags.py selftest`.

## Caveats

- Metrics use the authors' scorer. Function-level hits compare bare `Class.method` names, ranked in file order of the XML answer.
- Patch-derived gt can include functions that only gained a line. Instances whose fix only adds new functions have no function-level gt and always score 0, identically in every arm.
- Tags are syntactic: they show where a concept is handled, not whether it is handled correctly.
- Temperature 0 does not make Gemini deterministic, so stock and placebo differ by noise as well. That noise is why the primary contrast is concept vs placebo.
- `ide` tags are sparse (6-14% of functions in gold files vs 63-78% for concept). Where the five listed files have no warnings, the `ide` prompt equals `stock` (e.g. `delgan__loguru-1297` in the smoke). So concept vs ide compares two real tools at their natural density, not equal-length strings; placebo is the length-matched control.
