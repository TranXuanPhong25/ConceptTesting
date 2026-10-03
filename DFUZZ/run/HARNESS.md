# DFUZZ concept pilot: harness and Phase 0 (2026-10-02)

Plan: `run/PILOT_PLAN.md`. The original DFUZZ files are untouched: every container mounts the tree read-only, and only `run/` is writable. Everything runs on native arm64. The pilot made no git commits.

**Status: Phase 0 is done, and its stopping rule fired.** Only 33 of the 1,799 seeded APIs have a gap (1.8%), against the 50% threshold. Even if every API the extractor could not resolve were counted as having a gap, the share would be at most 37.0% for TF raw ops and 47.0% for torch, so the stop does not depend on resolution failures. Arms M0-M5 were therefore **not built**, and no LLM smoke tests ran (see the last section). Spend so far: one self-test call, $0.000007.

## Components

| file | what |
|---|---|
| `Dockerfile.pilot` | `dfuzz-pilot:arm64` = `dfuzz:arm64` plus a separate `/opt/pilot` py3.11 venv (google-genai, openai 0.27.10 + cachetools + networkx so DFUZZ's own modules import unmodified, tree-sitter-cpp, pyyaml) and gdb. The TF and torch venvs are not touched. |
| `dock.sh` | Runs any command in the image. The tree is mounted read-only, `run/` read-write. `~/.config/gcloud` is mounted read-only with `GOOGLE_APPLICATION_CREDENTIALS` set, and `VERTEX_PROJECT`/`VERTEX_LOCATION` are passed by name (sourced from `scripts/vertex_env.sh` with stdout discarded). `NOCREDS=1` starts a container with no credentials at all; use it for every executor-only step. |
| `llm.py` | The only LLM gateway. Calls Vertex `gemini-2.5-flash` with thinking budget 0 and T=0, retries with backoff on 429/5xx, and caps output at 8,192 tokens. Every call appends a line to `out/ledger.jsonl` (arm, api, kind, in/out/think tokens, USD at $0.30/M in + $2.50/M out). The hard cap is `BUDGET_CAP` (default 18) and the per-step cap is `PHASE_CAP`. Hitting a cap raises a `BaseException`, so DFUZZ's `except Exception` retry loops cannot swallow it. `patch_openai()` points openai 0.27's `ChatCompletion.create` at Vertex: DFUZZ's dummy key and model are ignored, the real credentials never reach DFUZZ code, and nothing is printed. |
| `launch.py` | Runs one program under faulthandler (all threads) with seeded RNGs (random, numpy, torch/tf), through `runpy`, so the program's own line numbers are kept. It also writes a structured record of any Python exception: type, message, innermost program line, and where it was raised (lib/native/prog). |
| `oracle.py` | Executor and oracle. Each run gets a fresh process, its own cwd, a timeout (`ORACLE_TIMEOUT`, 30 s, which kills the process group), `prlimit --as` (6 GiB), and an env stripped of GOOGLE/VERTEX/OPENAI variables. Protocol: run 1 always; run 2 if run 1 is clean or a crash; runs 2-3 if any run crashes. Classes are `check_abort`, `memory_safety` (SEGV/BUS/glibc heap aborts), `fpe`, `ill`, `trap`, `abort_other` and `internal_assert`, versus `exception` (with type, message, `at_target`, and `own_check` = raised inside the target call by the library), `clean`, `resource` (137/SIGKILL/bad_alloc/OOM) and `timeout`. **Strict crash** = a crash class in 3 of 3 runs, with the innermost program frame on the target call. A run whose faulthandler dump has no program frame (garbled by heap corruption) neither confirms nor refutes. `disagree` = the two fresh runs differ in class or in hex-normalised stdout. Dedup signature = CHECK/assert `file:line`; otherwise one extra gdb run gives the top native frame. |
| `validate_oracle.py` | Runs the oracle over the 37 reproducers and their seeds and writes `out/oracle_validation.jsonl`. |
| `eager_probe.py` | Gap-kind-1 premise check on TF 2.15 and writes `out/eager_probe.jsonl`. |
| `cpp.py`, `gaps.py`, `edgecases.py` | Gap extractor (no LLM). Produces `out/gaps.jsonl`, `out/gap_index.json`, `out/gap_raw_{tf,torch}.json` and `out/tf_arg_renames.json`. |
| `tf_renames.py` | Python arg names of raw ops that differ from op input names (`out/tf_arg_renames.json`). |
| `frame.py` | Sample frame: runs the candidate seeds through the oracle and writes `out/frame.jsonl`. |
| `out/gap_review.jsonl` | Manual verdicts for 28 gaps, each with a source citation. |

## Commands (from `DFUZZ/`)

```bash
docker build -t dfuzz-pilot:arm64 -f run/Dockerfile.pilot run          # once
PHASE_CAP=2 bash run/dock.sh /opt/pilot/bin/python run/llm.py           # Vertex self-test (1 call)
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/validate_oracle.py # oracle on 37 reproducers (~3 min)
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/eager_probe.py     # ~1 min
# source cache (not tracked, run/.gitignore), ~80 MB:
cd run/cache && git clone --filter=blob:none --no-checkout --depth 1 --branch v2.15.0 https://github.com/tensorflow/tensorflow tf \
  && (cd tf && git sparse-checkout set --no-cone /tensorflow/core/kernels/ /tensorflow/core/ops/ \
      /tensorflow/core/framework/common_shape_fns.cc /tensorflow/security/ && git checkout v2.15.0) \
  && git clone --filter=blob:none --no-checkout --depth 1 --branch v2.2.0 https://github.com/pytorch/pytorch torch \
  && (cd torch && git sparse-checkout set --no-cone /aten/src/ATen/native/ && git checkout v2.2.0) && cd ../..
NOCREDS=1 bash run/dock.sh /opt/tf215/bin/python run/tf_renames.py      # raw_ops arg renames (reduction_indices -> axis)
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/edgecases.py        # self-check of the edge-case annotation
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/gaps.py             # ~40 s, prints the stop-rule numbers
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/frame.py            # runs candidate seeds
```

Long steps: wrap them in `nohup ... > run/out/<step>.log 2>&1 &` and poll the log.

## Phase 0 results

**Oracle validation.** 29 of the 31 reproducers that REPLAY.md says reproduce are strict crashes: 21 check_abort, 5 memory_safety, 3 internal_assert. 0 of the 37 seeds are flagged. The 2 misses:
- `torch.fft.rfftfreq` raises an ordinary RuntimeError (leaf variable in-place), which is outside the pre-registered crash definition.
- `TensorListConcat` crashed in 1 of 3 runs here (replay had 3/3; its issue calls it flaky). Its `disagree` flag fired.

The definition has one extension: calls that consume an instance of the target count as the target, so `tf.io.TFRecordOptions` crashes at `TFRecordWriter(path, options)`.

**Eager probe** (5 ops whose shape functions require a rank: DrawBoundingBoxes, MatMul, Unique, ResizeBilinear, Conv2D). The shape-function check fired in 0 of 5 eager calls and in 5 of 5 `tf.function` calls. In eager mode, 4 kernel checks fired and DrawBoundingBoxes aborted. So gap kind 1 is reachable in eager mode.

**Gap extractor.** The extractor works as follows:
- **TF.** `REGISTER_KERNEL_BUILDER` (CPU) leads to the class and its `Compute` (bases are followed). Helpers are inlined two levels deep, from the same file, sibling files, or definitions that are unique across all kernels. Guards are scoped by block, so a check in an if-branch does not protect the else-branch, while for-loop bodies are transparent. Locals derived from a shape (`n = x.dims()`) are substituted back. Validators that receive the context, and objects built from the input and later checked with `.IsValid()`, count as opaque guards.
- **torch.** `native_functions.yaml` gives the dispatch target (CPU or Composite*). Structured meta and impl functions, `at::foo`, `at::foo_out` and `_symint` calls, and zero-argument macros are all inlined.
- **Mapping.** Each gap is mapped to DFUZZ's parameter name (TF api_def renames applied) and to the best of the 146 released edge cases for that parameter's DFUZZ type (`edgecases.py` annotates rank, empty, dtype and negative properties).

| | seeded | resolved | with ≥1 gap | mapped to a DFUZZ role + edge case | upper bound if every unresolved API had a gap |
|---|---|---|---|---|---|
| TF raw_ops | 354 | 241 | 18 (5.1%) | 13 | 37.0% |
| torch | 1445 | 781 | 15 (1.0%) | 8 | 47.0% |
| pooled | 1799 | | **33 (1.8%)** | | < 50% |

There are 57 gaps across all APIs. By kind, on seeded APIs: kind 1 (shape function only) dominates TF, kind 3 (read before guard) gives 10 TF records, and kind 2 (sibling) gives only torch out=/inplace records. Recall on the 19 known-bug raw ops (excluded from the frame): gaps were found for DrawBoundingBoxes(V2), FakeQuantWithMinMaxVarsPerChannel, FusedPadConv2D and UnicodeEncode, all at the actual crash site.

**Precision.** I read the source for 28 gaps (`out/gap_review.jsonl`):
- **TF: 18 of 24 true (75%).** 10 are crash-capable reads and 8 are true but benign (the kernel flattens the input). The 6 false positives come from validation done in helpers the extractor does not follow (`GroupShapeFromInputs`, `GetShape(ctx, 0)`) and from merges checked through a ternary-derived local.
- **torch: 0 of 4 true**, and 10 more records follow the same pattern. Torch kind-2 gaps are checks specific to the out= or inplace variant (out dtype, in-place complex) and are not missing guards.
- **Spot check.** The QuantizeAndDequantizeV2 kind-3 gap is a real strict crash (`tensor.cc:852`, `out/qdqv2_gap_check.py`). It has the same signature as the known V3 bug, so it is a sibling of a known bug, not a new finding.

**Frame** (`out/frame.jsonl`: ≥1 mapped gap, seed exits clean and calls the target, known bugs and aliases excluded):

| stratum | in frame | with a verified gap |
|---|---|---|
| tf_tfsa | 3 | 0 |
| tf_other | 3 | 1 (ReduceJoin, benign) |
| torch | 8 | 0 |

No API in the frame has a verified crash-capable gap. Regenerating the missing seeds was skipped: only 4 unseeded APIs have a mapped gap, which would not clearly enlarge the frame.

**Why gaps rarely map.** DFUZZ's LLM-generated types decide the edge-case vocabulary. `axis: Int` (All/Any/Min) and `input_min: Scalar` (QuantizeAndDequantizeV4) have no released edge case that produces a tensor of the wrong rank, so these true gaps cannot be expressed without new vocabulary, which the plan forbids.

## Findings that matter for any later phase

1. **DFUZZ's released generator drops 53 of its 54 single-tensor edge cases.** `gen_prompts_for_mutators.py` keys individual mutators by `pattern[0][:-2]`, so `['tensor_2']` (1 case) overwrites `['tensor_1']` (54 cases). Every individual tensor prompt is therefore "A 2D matrix of size 2x2". Rich tensor cases appear only through pair and triple patterns. Running the verbatim generator on the shipped data shows this: it is the most frequent requirement, appearing 1,691 times. An arm that uses the 54 cases would differ from the verbatim M1 pool in vocabulary as well as in selection.
2. Python arg names differ from op input names for 13 raw ops (`reduction_indices` vs `axis`).
3. The ADC file mounted read-only is readable by programs running in the same container (Docker Desktop's virtiofs ignores ownership). Executor-only steps therefore use `NOCREDS=1`. The arms would interleave LLM calls with execution (M4), so they would share the container with the credentials.

## Phase 1 / Phase 2

Not runnable: the pre-registered Phase-0 stop fired, so the arm drivers (M0-M5, A/A) were not written, and spending on LLM smoke tests would contradict the stop. A frame of 14 APIs, with 1 verified gap that is benign, cannot meet Phase 1's 40 APIs, and gap-ranked selection has nothing to rank on most APIs. If you want to continue anyway, these decisions are needed first:
- (a) Loosen the gap definition (for example, value and index guards, helpers in other files).
- (b) Allow new edge-case vocabulary for rank or numel violations on `Int`/`Scalar`-typed roles.
- (c) Choose the M1 pool: verbatim (with the overwrite) or the 54 tensor cases restored through a scratch `unique_mutators.json`, which changes data, not code.

The pieces already built (gateway, ledger, oracle, frame builder) are what the arm drivers would call. The ledger and caps already enforce the $18 limit.

## Phase 0b (post hoc, exploratory; 2026-10-02)

The user chose to continue after Phase 0's stop, knowing the rules change after seeing data. The amendment was appended to
`PILOT_PLAN.md` ("Phase 0b amendment") **before** any Phase 0b number was computed. It fixed the V0b edge-case templates,
the X0b reach, and the new go rule: frame >= 40 APIs with >= 1 mapped gap, a clean seed that calls the target, outside
the 37 known bugs, their aliases and sibling families. Phase 0 outputs are untouched; new files carry `_0b`.

**Status: the go rule failed (frame 22 < 40). Phase 1 was not run. No LLM calls were made (ledger total still $0.000007).**

### New files
| file | what |
|---|---|
| `edgecases_ext.py` | V0b vocabulary: gap record -> ordered candidates (released best first, then T-rm/T-req/T-rle/T-n1/T-dv/T-mm/S-t1/S-tn/S-s0/S-sn/S-ax, then secondary T-r0/T-e0/T-dx). Self-check: `python run/edgecases_ext.py`. |
| `gaps_ext.py` | X0b reach on top of unchanged `gaps.py`: depth-4 inlining with a size cap, symbol index over TF `core/{kernels,framework,util}` and ATen native + top level + `c10/core`, cross-file resolution (same stem -> `#include` closure -> unique), classes merged across `.h`/`.cc`, registration and structured macros expanded, `using`/`typedef` aliases resolved. It also records read-site details for V0b (literal index, index -> `GetAttr`, casts). Mapping covers both Phase 0 raw gaps (`gap_index_p0v0b.json`, `gaps_p0v0b.jsonl`) and X0b raw gaps (`gap_raw_{tf,torch}_0b.json`, `gaps_0b.jsonl`, `gap_index_0b.json`). |
| `frame_0b.py` | Runs the seeds of the union of candidates through the oracle and reports the frame for the 2x2 (extractor p0/x0b) x (vocabulary released/v0b). Output: `out/frame_0b.jsonl`, `out/frame_0b.log`. |
| `out/gap_review_0b.jsonl` | Manual verdicts with source citations for every new gap record (9). |

### Commands (from `DFUZZ/`)
```bash
# source cache: widen the sparse checkouts (symbol index only)
(cd run/cache/tf && git sparse-checkout set --no-cone /tensorflow/core/kernels/ /tensorflow/core/ops/ \
   /tensorflow/core/framework/ /tensorflow/core/util/ /tensorflow/security/)
(cd run/cache/torch && git sparse-checkout set --no-cone /aten/src/ATen/native/ '/aten/src/ATen/*.h' '/aten/src/ATen/*.cpp' /c10/core/)
python3 run/edgecases_ext.py                                                       # self-check
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/gaps_ext.py tf                # ~80 s
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/gaps_ext.py torch             # ~20 s
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/gaps_ext.py assemble
NOCREDS=1 bash run/dock.sh /opt/pilot/bin/python run/frame_0b.py > run/out/frame_0b.log   # ~1 min
```
Operational note: while another agent's containers mounted sibling `py-toy` paths, writes to `/dfuzz/run/out` sometimes
failed with EROFS (Docker Desktop fakeowner mount). Rerunning the step, or pre-creating the output file, fixed it.

### Results

**Resolution (seeded APIs).** TF raw_ops: 241 -> 337 of 354 resolved. Torch: 781 -> 920 of 1445; the remaining 521 have
no ATen native function (Python-level composites). The macro and alias patterns resolved the cwise ops (`REGISTERn(UnaryOp|BinaryOp, CPU, ..)`),
linalg, segment, Relu/Elu (`numeric_op.h`), Concat (`using` alias), Cast (out-of-line `CastOpBase::Compute`), and
torch's macro-generated structured pointwise ops. `UnsortedSegment*` is still unresolved. No API hit the TF size cap; 11 seeded torch APIs did.

**Gaps.** Seeded APIs with >= 1 gap: TF 18 -> 21, torch 15 -> 14; pooled 33 -> 35 of 1,799 (1.8% -> 1.9%). The record
diff is +9 new and -5 dropped. The dropped records are 4 Phase 0 torch kind-2 FPs (histc, logsumexp: deeper inlining
now sees the call into the out= path) and TensorArrayCloseV2's kind-1 record. The newly resolved kernels (cwise, linalg,
segment, activation) add no gaps: their checks are in the code that is now inlined. Deeper inlining reached Phase 0's
FP helpers (`GroupShapeFromInputs`, `GetShape`), but those FPs survive. The guarded value flows through a `ShapeArray`
local or an out-param, which the unchanged binding logic does not track.

**Mappability (gap records).** Phase 0 records: 34/57 mapped with released cases, 45/57 with V0b (+11). The other 11
have no DFUZZ role (`self` of `torch.Tensor.*`). X0b records: 40/62 released, 51/62 V0b. V0b cases used: T-rm 16, S-tn 7,
T-mm 6, T-e0 5, S-t1 4, T-n1 4, T-req 4, T-rle 3, T-r0 2. S-ax and T-dx never applied: no kind-3 gap read was indexed by
an Int role or wrapped in a cast.

**Precision of new gaps** (`out/gap_review_0b.jsonl`). Only 9 new records exist, fewer than the pre-committed sample of
20, so all 9 were reviewed (a census). **Precision is 2/9 = 22%, below 50%, and 0/9 are crash-capable.**
- TP-benign: MatchingFilesDataset and its Experimental twin. The rank <= 1 limit exists only in the shape fn; the kernel reads `flat<tstring>()`.
- FP: RandomShuffle. The short-circuit `NumElements() <= 1 ||` (`shuffle_common.h:67`) means a rank-0 input never reaches `dim_size(0)`.
- FP: SoftmaxCrossEntropyWithLogits. The read is loop-bounded in `BCast::FromShape` (`util/bcast.cc:22`).
- FP: torch.cross/Tensor.cross ×4 and torch.normal. The read is the in-range ternary in `infer_size_impl` (`ExpandUtils.cpp:26-28`).
- Per distinct site: 1 of 4 is true.

**Frame and go rule** (`out/frame_0b.log`). The new rule also excludes sibling families, so QuantizeAndDequantizeV4 leaves the Phase 0 frame (14 -> 13).

| extractor \ vocabulary | released | V0b |
|---|---|---|
| Phase 0 | 13 (14 candidates) | 18 (19) |
| X0b | 17 (18) | **22** (23) |

- Vocabulary alone adds +5: All, Any, Min, MatrixDiagPartV2/V3. These are `Int`/`Scalar` roles that are now expressible; all were reviewed in Phase 0 as TP-benign.
- Reach alone adds +4: MatchingFilesDataset ×2, RandomShuffle, torch.cross, torch.Tensor.cross and torch.normal (+6), minus histc and logsumexp (-2).
- Both together add +9.

Strata of the 22: tf_other 9, tf_tfsa 4, torch 9. Review status: 0 crash-capable, 8 TP-benign, 11 FP, 3 unreviewed
(torch kind-2, the same pattern as the reviewed FPs). SparseSegmentSqrtNGrad's seed raises, which is why 23 candidates give a frame of 22.

**Go rule.** 22 < 40, so **stop**. Seed regeneration was not triggered: 8 unseeded candidates give at most 30 < 40.

**Executor isolation.** `docker inspect` of a `NOCREDS=1` container shows two mounts only: `DFUZZ -> /dfuzz` (ro) and
`DFUZZ/run -> /dfuzz/run` (rw). There is no gcloud mount, and the environment has no `GOOGLE_*` or `VERTEX_*` variables.
All Phase 0b steps ran under `NOCREDS=1`.

### Phase 1
Not run, because the Phase 0b go rule failed. No arm drivers were written and no M1-verbatim/M1-restored prompts were
generated. The pre-committed Phase 1 design (M3 vs M1-restored, M3 slots = gap prompts + M1-restored fill) is in
`PILOT_PLAN.md` if a later decision revives it.
