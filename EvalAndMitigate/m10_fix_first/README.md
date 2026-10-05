# m10_fix_first: raise the fix rate of the Advanced prompt's Part 2, then test whether better fixes give better tests

## Why
m9 showed that when Part 2 of the Advanced prompt (the "corrected implementation") really fixes the bug, the Part 3
docstring written from it yields more E tests and no M (rerun: ≥1 E in 9/16 fixed methods vs 17/54 not fixed, 0 M).
But Part 2 fixes only ~17-19 of 60 bugs, and m9's concept checklist did not raise that. m10 targets the fix rate
directly. It is cheap to measure offline: substitute Part 2 into a scratch copy of the buggy checkout, compile it and
run the bug's trigger tests. Trigger tests and patches never enter a prompt. Phase B then checks whether the better
fixes give better tests.

## Phase A: fix-rate arms (78 methods, 60 bugs)
All arms use the upstream Advanced prompt built by m9's builder (`m9.base_prompt` = the notebook's
`PromptFormatter().apply_format_summarize(...)` call), unless stated. Docstrings are parsed with the notebook's own
code (`m9.nb_parse`). There is no `max_tokens`, as in the notebook.

| arm | model / settings | prompt | samples |
|---|---|---|---|
| **A0** | m9 `adv_rerun` completions, reused (Flash, thinking off, T=0) | Advanced | 1, no new call |
| **A1** | Gemini 2.5 Flash, thinking on (`THINKING_BUDGET=-1`, dynamic), T=0 | Advanced | 1 |
| **A1r** | Flash, thinking on (dynamic), T=0 | the paper's reasoning-model prompt | 1 |
| **A2** | Flash, thinking off, T=1.0 (the Gemini default) | Advanced | K=5, then filter + consensus |
| **A3** | Gemini 2.5 Pro, default thinking (dynamic), T=0 | Advanced | 1 |

- **A1r prompt.** The formatter builds `context + "\n```\n" + instruction block`. Its restored block is byte-identical
  to the text after the context of `Prompt_example/Advanced_Docstring_Prompt_Base_Model` (asserted in `selftest`).
  A1r puts the same part of `Prompt_example/Advanced_Docstring_Prompt_Reasoning_Model` in its place, which is how
  upstream would build it. That prompt asks for **no corrected implementation**. A1r's "Part 2" is therefore any
  ```java block that happens to declare the focal method, so expect a fix rate near 0. A1r is a docstring arm. It is
  reported, but it will practically never be the automatic Phase B choice; pass it explicitly to test it
  (`run.sh phaseB A1r`).
- **A2 regression filter.** A developer only has the tests that pass on the current code. Per bug, the oracle is the
  Defects4J relevant tests (`defects4j export -p tests.relevant`, run on a scratch copy of the buggy version). A test
  is kept only if it passes there twice: once on the classes `defects4j compile` built, and once with the focal file
  recompiled alone (as every candidate is). Trigger tests are excluded explicitly. For the other tests that fail on
  the buggy code only a count is stored, never their names (trigger names are kept for offline scoring only).
  A candidate is dropped if it does not compile, or if any oracle test fails or does not finish.
  - **Caveat:** `tests.relevant` is derived from the classes the fix modifies. The focal class is always one of them,
    so this reveals almost nothing, but it is not purely developer-side information.
- **A2 behavioural consensus.** The survivors run m8's probe for the method (`m8_concept_mutants/out/probe_gen.jsonl`,
  accepted attempt). The probe was written blind, from the Advanced docstring and interface evidence, with no body.
  Only cases that give the same output in two runs on the buggy code are used.
  - Survivors are clustered by their output vector. The largest cluster wins; a tie goes to the cluster with the
    earliest sample, and its earliest sample is the representative.
  - Per method, the run records the number of survivors, the cluster sizes and the probe inputs on which survivors
    disagree.
  - Fallbacks: if no candidate survives, the first sample is used; for the 6 methods without an accepted m8 probe, the
    first survivor.
  - The selection reads only compile status, oracle results and probe outputs; `selftest` asserts it is blind to
    trigger outcomes.
- **Scoring (offline only).** A method is fixed when its Part 2 compiles and all trigger tests pass. A bug is fixed
  when all its focal methods are substituted together (11 bugs have 2-6 methods, always in one file). Part 2
  extraction and substitution are m9's `fixrate.py` (`part2`, `substitute`), unchanged, so A0 reproduces m9's
  measurement: m9 found Part 2 in 74/78 completions and 17 fixed methods / 19 bugs.
  - Harness check: substituting the developer's fixed focal methods must fix the bug. m9 found this for 50/60 bugs;
    the other 10 need changes outside the focal methods.

**Metrics (`analyze.py A`):**
- per arm: Part 2 found, compiled, regression-safe, fixed methods, fixed and regression-safe, bugs fixed (of 60 and of
  the reproducible ones);
- exact McNemar of each arm vs A0 (methods, bugs);
- for A2: pass@5 (oracle), selected vs first sample, and the disagreement statistics;
- memorization check: normalised token similarity (comments and layout ignored, `difflib`) of the selected Part 2 to
  the developer's fixed method. Near-verbatim means ≥ 0.95. The fix rate is split into near-verbatim and other;
- cost per arm (every API attempt is logged with tokens incl. thinking, at Vertex list prices).

The Phase B arm is the complete new arm with the most fixed methods, then the most fixed bugs, then the lowest cost.
It is written to `out/best_arm.txt`.

## Phase B: docstrings, tests, evaluation
- **Docstring.** For the chosen arm, each method's docstring is the Part 3 docstring of the selected candidate, i.e.
  written from the selected fix.
  - For A2, up to 8 lines `// Undetermined (do not assume): <probe input>` are appended where the surviving
    candidates disagree. The probe input is the probe case's expression.
  - `docs` asserts that these lines carry no fixed-side patch line and no trigger test name that is not already in the
    upstream prompt.
- **Tests and evaluation.** They use the unchanged upstream pipeline:
  `DOC_FILE=… WITH_CODE=0 FILE_POST_FIX=m10_<arm> bash run/dock.sh gen_env`. This is test generation with Flash,
  thinking off, the same as every baseline. The evaluation is `eval_parts.py` (m9's, resumable, `NO_ADC=1`).
- **Analysis (`analyze.py B <arm>`).**
  - M/E/FP, red-precision, ≥1 M / ≥1 E on the intersection of clean methods.
  - Exact McNemar vs A0 and vs the original Advanced Doc. A0 is the m9 `adv_rerun` evaluation; A0 and Advanced Doc
    come from `inputs/ref_outcomes.json`, parsed from the source machine's logs.
  - The Gson_4/Cli_1 sensitivity.
  - ≥1 E / ≥1 M split by "selected fix correct or not" (Fisher), for the arm and for A0.
  - Methods with vs without Undetermined lines.
  - Focal-body windows in the docstrings.
  - Test-generation cost (estimate).

## Leakage and security
- **Leakage.** The new prompts are the upstream prompt (A1, A2, A3) or the upstream context with the paper's
  reasoning-model block (A1r). Neither carries per-method additions. The Phase B prompt contains only the docstring
  (plus the Undetermined lines, checked).
  - The fixed version, patches, trigger tests and failing test names are used only for offline scoring, the harness
    check and the similarity analysis.
- **Sandbox.** All LLM-written code (Part 2 candidates, probes) is compiled and run in `dock10.sh`:
  - no gcloud credentials, `--network none`;
  - repo read-only, outputs only to `out/`;
  - checkouts read-only (`/d4j`);
  - every job in its own scratch copy (`m10scratch` volume).
- **Exceptions to the sandbox.**
  - `env` keeps the network (`M10_NET=1`), because it compiles only the developers' own code with defects4j.
  - LLM calls run through `run/dock.sh` with credentials, and run no code.
  - Evaluations always use `NO_ADC=1`.

## Portability (the run happens on another machine)
- **Inputs.** Some inputs are gitignored here, so they are copied into `inputs/`, with `inputs/MANIFEST.sha256`
  (`shasum -a 256 -c` / `sha256sum -c` inside `inputs/`). `m10.py install` verifies it. They were produced by
  `m10.py make-inputs` on the source machine. The list:

| file | size | from |
|---|---|---|
| `buggy_source_data_unified_invoked.jsonl` | 6.8 MB | `data/prompts/` (78 records) |
| `Gemini-2-5-flash_…_with_advanced_docstring_base_cot_code.jsonl` | 7.1 MB | `data/prompts/` (Advanced docstring file) |
| `m9_docs_adv_rerun.jsonl` | 2.0 MB | `m9_concept_advanced/out/docs_adv_rerun.jsonl` (A0 completions + upstream prompts) |
| `m9_fixrate_adv_rerun.json` | 0.06 MB | m9's own fix-rate measurement of A0 (cross-check) |
| `m9_llm_calls_adv_rerun.jsonl` | 0.01 MB | A0's call cost |
| `m8_probes.json` | 0.3 MB | accepted probe code per method (72), from m8 `probe_gen.jsonl` + `probe_check.json` |
| `m8_spans.json` | 0.01 MB | focal method byte spans + md5 of the buggy file, from m8 `mutants.jsonl` |
| `ref_outcomes.json` | 0.03 MB | per-method M/E/glitch of Advanced Doc and m9 adv_rerun, parsed from the evaluation logs (gitignored) |

- **No host paths.**
  - Code paths are relative to the repo (`/repo` in containers).
  - Classpaths are exported at runtime inside the container and stored with a `{ROOT}` placeholder. m8's `env.json`,
    which has container paths into the old checkouts, is not used.
- **Reused code, unchanged.** These files must be in the clone; `m8_concept_mutants/` and `m9_concept_advanced/`
  must be committed:
  - `m9_concept_advanced/m9.py`, `m9_concept_advanced/fixrate.py`;
  - `m8_concept_mutants/{probe.py,phase0.py,mutate.py}`;
  - `m6_agent_oracle/analyze.py`, `m2_concept_diag/analyze.py`, `m5_blind_concept_spec/spec.py`, and their imports
    (`m1`, `m3`, `m6/oracle.py`).
- **Architecture.**
  - `docker/Dockerfile` is arch-neutral (ubuntu:22.04, `openjdk-11-jdk`, Defects4J 3.0.1 from source, jar-only
    dependencies, multi-arch uv image). The same build works natively on arm64 and x86_64; no emulation is needed.
  - `data/build/java.so` (tree-sitter) is built inside the container and is gitignored. If you copy a working tree
    (rsync) instead of cloning, delete it; `install` warns when its arch does not match.
- **Linux file ownership.** On Linux (rootful Docker), files written by containers are owned by root. `install`
  creates the output folders on the host first, so host-side steps can still write. If you hit "permission denied":
  `sudo chown -R $USER m10_fix_first/out data/prompts data/rq1`.

## Fresh-machine runbook (from `EvalAndMitigate/`)
Prerequisites:
- Docker (Desktop or Engine, arm64 or x86_64);
- python3 ≥ 3.8 on the host (stdlib only);
- the gcloud CLI with ADC and a project with Vertex AI enabled;
- ~25 GB free disk: image ~4 GB, 120 checkouts ~8 GB, scratch ~5 GB;
- RAM: 2 GB plus ~1.5 GB per job.
```bash
git clone <repo> && cd py-toy/EvalAndMitigate
gcloud auth application-default login                    # mounted read-only into LLM containers only
export GOOGLE_CLOUD_PROJECT=<your-project>               # or: gcloud config set project <your-project>
docker build -t evalmitigate docker/                     # ~20-40 min; equivalent: docker build -t evalmitigate -f docker/Dockerfile docker/
python3 m10_fix_first/m10.py install                     # verifies inputs/MANIFEST.sha256, creates output folders
python3 m10_fix_first/m10.py selftest                    # host part; the container part runs in the smoke
bash m10_fix_first/run.sh checkout                       # sequential, 60 bugs x (buggy, fixed): ~45-90 min
bash m10_fix_first/run.sh smoke 2>&1 | tee m10_fix_first/out/smoke.console          # ~30-45 min, ~$0.5
JOBS=8 bash m10_fix_first/run.sh phaseA 2>&1 | tee -a m10_fix_first/out/phaseA.console
bash m10_fix_first/run.sh analyzeA                       # -> out/analysisA.txt, out/best_arm.txt
bash m10_fix_first/run.sh phaseB 2>&1 | tee -a m10_fix_first/out/phaseB.console      # arm from best_arm.txt (or: phaseB A2)
bash m10_fix_first/run.sh analyzeB                       # -> out/analysisB_<arm>.txt
```
- Use `nohup … &` for the long stages. They print timestamped progress lines and can be rerun at any point.
- `docker build -t evalmitigate .` from `EvalAndMitigate/` also works, but it sends the whole folder as build context.
- `PROJECTS="Lang Cli Csv Codec Gson" bash run/dock.sh checkout` also works, but it checks out all ~155 bugs of those
  projects; `run.sh checkout` takes only the 60 needed.

**Expected smoke output:**
1. `checkout` prints `[checkout k/3 …] Cli_32: buggy + fixed ready`.
2. The container `selftest` ends with `container checks ok: fixrate selftest, Part 2 found in 74/78 A0 completions
   (m9: 74), 72 probes parse, M10Runner compiles` and `selftest ok`.
3. `env` prints one line per bug. Expect `trigger fails on buggy: True` and `fixed methods substituted: FIX` for all
   3 bugs; all 3 are reproducible in m9's check.
4. `vertexcheck` prints `'OK'` for `gemini-2.5-flash thinking_budget=0`, `gemini-2.5-flash thinking_budget=-1` (>0
   thought tokens) and `gemini-2.5-pro thinking_budget=-1`.
5. `gen` writes 3 calls for each of A1, A1r and A3, and 15 for A2.
6. `fix` prints one line per candidate (`regression ok|FAIL n, trigger FIXED|not fixed`) and one per (arm, bug).
7. `smoke_analysisA.txt` shows A0 with 0 fixed of idx 3/33/53, as m9 found; the bugs column is empty for Lang_20,
   whose second method has no smoke candidate.
8. The A2 smoke evaluation ends with a `run/summarize.py` line `clean (excl. … glitched): methods=3 …`.

**Runtime and cost on a typical machine (8 cores; estimates, not measured here):**

| stage | wall time | Vertex |
|---|---|---|
| image build | 20-40 min | – |
| checkout (sequential) | 45-90 min | – |
| smoke | 30-45 min | ~$0.5 |
| phaseA `env` (60 bugs: compile + relevant tests 2x + harness check) | ~3 CPU-h → ~45 min at JOBS=4 | – |
| phaseA `gen` | ~1-1.5 h at JOBS=4 | A1 ~$1-2, A1r ~$1-2, A2 (390 calls) ~$3-5, A3 (Pro) ~$5-8 |
| phaseA `fix` (~700 candidates; identical ones run once per job) | ~6-10 CPU-h → ~1-1.5 h at JOBS=8 | – |
| phaseB (78 docstrings → tests → evaluation) | ~45-60 min | ~$1 |

- Phase A totals about $10-17.
- A Flash repetition loop (65,536 output tokens) adds about $0.17. A Pro one adds about $0.66.
- `M10_CAP_USD` (default 60) stops new calls above the logged spend.

**Where results land.** Everything is in `m10_fix_first/out/` (tracked in git):
- `env.json`, `gen_<arm>.jsonl`, `fix_<arm>.jsonl`, `llm_calls.jsonl`;
- `analysisA.txt`, `best_arm.txt`, `analysisB_<arm>.txt`;
- `m10_<arm>_parts.json`, consoles.

Pipeline files go to the usual gitignored places:
- `data/prompts/…_with_m10_<arm>.jsonl`;
- `data/prompts/rq1/*m10_*`;
- `data/rq1/logs/*m10_*`;
- `data/rq1/results_test/chatgpt/*m10_*`.

To bring the results back, commit and push `m10_fix_first/out/` from that machine, or
`rsync -a <host>:<path>/EvalAndMitigate/m10_fix_first/out/ m10_fix_first/out/`. Add the logs with
`rsync -a <host>:<path>/EvalAndMitigate/data/rq1/logs/ data/rq1/logs/` if you want to re-parse them here.

**Troubleshooting.**
- A crashed stage is rerun as is: the caches skip finished work.
- `eval_parts.py` refuses to start a part whose log already exists (`<fpf> already has a log`). This happens after a
  hard kill: move that log and its console away, then rerun.
- Glitched evaluation blocks (empty error report) can be re-evaluated once:
  `python3 m10_fix_first/eval_parts.py m10_<arm> --redo i j …`.
- `env` failures are printed per bug (`FAILED (rerun env to retry)`). `fix` failures are printed per (arm, bug).

## Files
- `m10.py`: install / make-inputs / selftest / checkout / env / gen / vertexcheck / fix / docs / cost.
- `M10Runner.java`: JUnit runner for whole classes or `Class::method`, with a per-class timeout.
- `dock10.sh`: the sandbox.
- `run.sh`: the driver.
- `analyze.py`: Phase A / Phase B numbers.
- `eval_parts.py`: m9's, paths moved.
- `inputs/`: see above.
- `out/`: results. `out/vertexcheck_source_machine.console` holds the 3 verification calls made on the source machine
  ($0.0017, also in `out/llm_calls.jsonl` as arm `vertexcheck`).
