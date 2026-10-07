# JitVul + concept facts (concept vs placebo)

Paper: Yildiz et al., *Benchmarking LLMs and LLM-based Agents in Practical Vulnerability Detection for Code
Repositories* (JitVul, ACL 2025, arXiv 2503.03586). Code and data: https://github.com/alperen21/JitVul (no license,
private use only), pinned at `00e8f9ad6a74cac59a21354da093a6845af7b1af`. `setup.sh` clones it into `vendor/JitVul`,
which is gitignored and never edited.

**Question.** The JitVul baseline sees only the target function. Does a compact block of static concept facts about the
target **and its callees** help? The callee facts are inter-procedural information the model otherwise never reads.
The `placebo` arm controls for "any concept-looking text". The `ide` arm gives ordinary static-analyzer
warnings instead: if concept facts do not beat them, concepts add nothing beyond existing tools.

## What runs

| piece | source |
|---|---|
| dataset | `vendor/JitVul/data/final_benchmark.jsonl`: 879 vulnerable/patched pairs, 730 CVEs, 267 projects, 91 CWEs |
| prompt | authors' `prompt.construct_cot_prompt` (unmodified, imported) |
| verdict / CWE parsing | authors' `agent.BaselineAgent.predict` (unmodified, imported; the LLM object is swapped) |
| LLM | Gemini 2.5 Flash on Vertex, temperature 0 (authors use `--temp 0`), thinking budget 0, max 8192 output tokens, same for every arm |
| concept annotator | official ConceptCoder VD annotator `ConceptCoder_org/code/design_concept/design_and_annotate_VD_concepts.py` (`bfs`, unmodified) |
| `ide` analyzers | `flawfinder==2.0.20` (pure Python) + `cppcheck==1.5.2` (PyPI binary wheel = Cppcheck 2.20.0, manylinux_2_28 x86_64 / macOS arm64); pip into the venv, no root, no compiler |

**Base configuration = plain LLM + CoT** (`main_baseline.py --prompt cot`). The paper names no single main baseline.
Its function-level reference is the plain LLM (`BaselineAgent`). Among the plain-LLM prompts, CoT is the single-function
prompt whose pAcc is not near zero (4o 15.0, vs vanilla 1.0). Vanilla collapses to "always vulnerable", which would leave
no room to measure the arms. Few-shot calls `random.choice` without a seed, which adds noise across arms. The `concept`,
`placebo` and `callee_code` blocks go between the code and the CoT instruction, so the authors' text stays intact.

**Annotator choice.** We use the official ConceptCoder annotator. It is pure CPU tree-sitter, needs only
`tree-sitter==0.20.4` and `tree-sitter-languages==1.9.1` (the versions in `ConceptCoder_org/requirements.txt`) plus
pandas, and ships wheels for both arm64 macOS and x86_64 Linux. It annotated 4,261 unique functions in about 7 s with
0 errors. Do not let `tree-sitter-languages` drift to 1.10.x: the newer C++ grammar crashes the official
`utils_VD.get_indices`. The vocabulary is the paper's 7 VD labels, mapped through `conceptcoder_bridge.PAPER_LABELS`:
Null assignment, Null check, Pointer dereference, Memory allocation (alloc calls and array declarators), Buffer access,
Bounds check, Memory free. The 8th prop, `if_statement`, is dropped. There is no C1-C8 mapping.

### Arms (prompt = authors' CoT prompt + block)

- `base`: the authors' prompt, unchanged.
- `concept`: a `Concept facts` block. It lists the labels for the target with line numbers (up to 6 per label), then
  one line per direct callee (up to 15) with label counts. Callees come from the **fixed** `get_callees`, and only
  callees whose source is in the dataset are listed.
- `placebo`: same header, same function names, same number of lines. The label facts come from a **different pair**.
  The derangement uses a fixed seed (`SEED=20251007`) and has no fixed points. The donor is never a pair of the same
  CVE and has a similar callee count and block length; the mean length gap is -3.6 chars. The donor side
  (vulnerable/patched) is a seeded coin flip, so the placebo carries no label signal. Line numbers are wrapped into
  the target's line range.
- `callee_code` (reference): the raw callee bodies, truncated to the concept block's character budget.
- `ide` (strong baseline, added later, runs last): a `Static analyzer warnings` block in the same position and shape.
  - Each function (the target, then the same callees as the concept block) is written to a temp `.c`/`.cpp` file,
    following the dataset's `file_name` extension. Callee bodies, which have no signature in the dataset, get a
    `void name() ` prefix.
  - The tools run as `cppcheck --enable=warning,style,portability,performance` and `flawfinder --csv` (default level).
  - cppcheck parse failures (`syntaxError`, `unknownMacro`, …) count as failures, not findings. `returnImplicitInt`,
    `unusedFunction` and `unusedStructMember` are dropped as artifacts of analysing a lone function.
  - Each function gets one line. Findings are grouped by tool and rule, e.g. `L4 cppcheck nullPointerRedundantCheck:
    <short message>`, and ranked: cppcheck error = flawfinder risk ≥4 > warning = flawfinder 3 > … > style.
  - Warnings are added best-first while the block fits the concept block's length. The single best warning is always
    shown.
  - Sizes: ide mean 429 / median 333 / p90 826 chars vs concept 489 / 382 / 958.
  - 512/1758 ide blocks (29%) have no warning at all; 244/879 pairs are empty on both sides. 652 blocks were cut to the
    budget, and cppcheck could not parse 157/1758 targets.
  - Blocks are written to `out/ide_blocks.jsonl` (cache in `cache/ide.jsonl`), separately from `out/blocks.jsonl`.
    That keeps the other arms byte-identical.

### `get_callees` bug (fixed in the wrapper only)

The released `code/evaluation_pipeline/tools.py:get_callees` reads `session.caller_graph`, so it returns **callers**.
The dataset compounds the confusion: the inner key of `{side}_callee_graph` is also named `"callers"`, although it
lists callees. `harness.target_and_callees` reads `{side}_callee_graph[target]["callers"]`. With the fix, functions
average 9.5 callees; the released tool returns callers (mean 0.6), and the two lists differ for 1471/1758 functions
(`./run.sh setup` prints this).

### Leaks handled

- 875/879 patched (`non_vulnerable`) bodies start with a stray fence-language line (`c`/`cpp`). None of the vulnerable
  bodies do, so the line is a label leak. Every arm strips it. Callee bodies show no such difference.
- Each function is judged in its own call, as the authors do. Pairs are never shown together, so there is no
  within-pair order to leak.
- **Return-type leak (not fixed in the first four arms).** The dataset drops the return-type line (e.g.
  `static mrb_value`) from 327/879 vulnerable bodies and from no patched body. The four original arms keep the authors'
  bodies as they are, because their full run had already started. All four see the same cue, so contrasts between
  them remain valid, but absolute P-C may be inflated. The `ide` arm analyses both sides from the function name on,
  so the cue cannot reach the analyzer warnings (cppcheck would otherwise flag `returnImplicitInt` on exactly these
  bodies). The prompt body itself is still the authors' body, as in every arm. A per-rule check found no other
  side-asymmetric warning (max 6 vs 1 pairs).
- 142 pairs have an identical target body before and after the fix; the fix was elsewhere. `base` cannot get P-C on
  these except by luck. `analyze.py` reports this subset separately.

### Metrics (`analyze.py` writes `out/summary.md`)

- **Primary: P-C** (pair-correct = paper's pAcc): vulnerable flagged and patched not flagged. Exact two-sided McNemar
  on P-C for concept vs placebo, concept vs base, callee_code vs base, placebo vs base, concept vs ide and ide vs
  base. The summary also reports the share of empty ide blocks. Each test runs on all pairs,
  on pairs with callee source on both sides, and on the identical-target-body subset.
- **Secondary:**
  - P-V (both flagged, the "always vulnerable" degenerate rate), P-B and P-R (the paper's pairwise failure types);
  - F1 and per-function accuracy;
  - CWE match (authors' rule: predicted CWE in the gold list, scored on the vulnerable side);
  - P-C strict (last `@@…@@` tag wins);
  - % of replies with no tag, % truncated, tokens and cost.

## Runbook (fresh x86_64 Linux, no GPU)

Prerequisites:
- git, bash, and [uv](https://docs.astral.sh/uv/). uv fetches CPython 3.11; without uv, `python3.10` is used.
- Never the system `python3` if it is 3.13 or newer: `tree-sitter-languages` has no wheels for it.
- No C compiler is needed: all pins ship manylinux x86_64 wheels.
- Google ADC at `~/.config/gcloud/application_default_credentials.json`. No gcloud CLI is needed.
- `VERTEX_PROJECT` and `VERTEX_LOCATION`: `run.sh` sources `../scripts/vertex_env.sh` if present, else uses the
  exported env. Values are never printed.
- Network access to github.com, PyPI and Vertex.

```bash
cd ~/dev/ConceptTester && git pull
cd JitVul_concept
./run.sh setup          # clone pinned JitVul, venv, deps, dataset + annotator + get_callees check (~1 min)
./run.sh annotate       # offline, ~40 s: concept blocks (out/blocks.jsonl) + ide blocks (out/ide_blocks.jsonl)
./run.sh smoke          # 5 pairs x 5 arms (cached already if out/ was committed; else ~5 min, ~$0.35)
# full set: long, so detach (no tmux on thinkbook)
JV_WORKERS=6 nohup setsid ./run.sh run all > out/run_all.log 2>&1 &
tail -f out/run_all.log
./run.sh verify         # re-renders every cached prompt, asserts it matches its stored sha1 (arms did not drift)
./run.sh analyze        # any time; reads whatever is done
```

To run the arms one by one: `./run.sh run base`, then `concept`, `placebo`, `callee_code`, `ide`.

**Adding `ide` to a full run already in progress.**
- `git pull` is safe mid-run. Git replaces files instead of rewriting them in place, and the running bash keeps the
  old `run.sh`. Its later `harness.py run <arm>` calls use the new code, whose prompts for the four original arms are
  byte-identical (checked: 2400 old-vs-new prompts on a 300-pair sample, and `./run.sh verify` on cached rows).
- After the pull, run `./run.sh setup` (it adds flawfinder and cppcheck to the venv) and `./run.sh annotate`
  (`out/blocks.jsonl` is rewritten byte-identical).
- The old loop does not know `ide`. Start it separately, e.g.
  `JV_WORKERS=4 nohup setsid ./run.sh run ide > out/run_ide.log 2>&1 &`, either once `run all` finishes or now in
  parallel if 429s stay rare.
To run two arms in parallel, start two `nohup setsid` jobs on different arms, but watch for 429s.

**Expected cost and time (full set, 1,758 calls per arm).**
- Smoke: $0.0066 per call → about $12 per arm, about $50 for the original 4 arms, about $62 with `ide`.
- Latency is ~15-25 s per CoT reply. With `JV_WORKERS=4` (default) that is about 2-2.5 h per arm; with 6-8 workers,
  about 1-1.5 h per arm if quota allows.
- 429/5xx errors retry with jittered exponential backoff (up to 10 tries, 90 s cap).

**Resume.** Re-run the same command. Each (arm, pair, side) is appended to `out/responses/<arm>.jsonl` as it finishes.
Cached rows are skipped, and rows with `"error"` are retried. Killing the job loses at most the in-flight calls.

**Results.**
- `out/summary.md` holds the tables.
- `out/responses/*.jsonl` holds one row per call: raw reply, verdict, CWE, tokens, cost, prompt sha1.
- `out/blocks.jsonl` holds every rendered block plus the placebo donor.

To bring results back, either commit `out/` (responses are ~8 KB per call, ~55 MB for all arms), or
`rsync -a thinkbook:~/dev/ConceptTester/JitVul_concept/out/ JitVul_concept/out/`.

Inspect one prompt: `.venv/bin/python harness.py show concept --pair 120 --side vulnerable`.

## Smoke (arm64 Mac, 2026-10-07, 5 pairs with callee source, $0.35)

`out/summary.md`: P-C base 0/5, concept 0/5, placebo 1/5, callee_code 2/5, ide 2/5. P-V (always vulnerable) is 4/5 for base and
concept. One callee_code reply looped (`%s%s…`) to the 8192-token cap and counts as "not vulnerable" under the
authors' rule. This shows only that the plumbing works; n=5 says nothing.

## Known risks

- **Contamination.** The CVEs date from 2017-2022 and the fixes are public, so the model may recognise the code.
- **Coverage.** Callee bodies are missing for many functions: only 530/879 pairs have callee source on both sides.
  For the rest, the concept block holds facts about the target only, which are the static facts the model already
  sees (≈ placebo in earlier runs in this repo).
- **Labels.** The labels are generic memory-safety facts, but many CWEs here are not memory bugs (CWE-20, -703, -601…).
- **Truncation.** A degenerate reply that loops to the output cap scores as "not vulnerable"; check `truncated %` per arm.
- **cppcheck wheel on Linux.** The cppcheck wheel was tested on arm64 macOS only. The x86_64 manylinux_2_28 wheel
  needs glibc ≥ 2.28 (EndeavourOS is fine), and `./run.sh setup` runs an analyzer self-check.
- **CWE hints in `ide`.** flawfinder messages carry CWE ids, so CWE match in `ide` is not comparable with the other
  arms.
- **Model choice.** Gemini 2.5 Flash is not one of the paper's models, so absolute pAcc is not comparable with the
  paper's GPT-4o numbers. Only the within-model arm differences matter.
