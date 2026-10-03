# DFUZZ reproducer replay on native arm64 CPU (2026-10-01)

Source: https://github.com/DFUZZ-ICSE/DFUZZ @ `3d7ba50` (2024-12-10). It is vendored as-is in `DFUZZ/`, with no original file edited. Everything we added lives in `DFUZZ/run/` and `DFUZZ/docker/`. No LLM calls were made.

## Environment (`docker/Dockerfile`, image `dfuzz:arm64`, linux/arm64, no emulation)

| venv | python | key pins | used for |
|---|---|---|---|
| `/opt/py38` | 3.8.20 (README: `python=3.8`) | `requirements.txt` as-is: torch==2.2.0, transformers==4.36.2, openai 0.27.10 (`~=0.27.8`), plus networkx (imported but not listed) | PyTorch bugs, DFUZZ pipeline |
| `/opt/tf215` | 3.9.25 | tensorflow==2.15.0 (resolves to `tensorflow-cpu-aws==2.15.0` on aarch64), plus requirements.txt | TF bugs |

- TF is not in `requirements.txt`. The paper's bug hunt used "TensorFlow (v2.15)", and TF 2.15 requires Python >= 3.9. The authors' TF issues report Python 3.9.
- The paper's bug hunt used torch 2.2.1, while the repo pins 2.2.0. We used the pin. Both have manylinux aarch64 wheels.
- Every wheel came from PyPI with a native aarch64 build. Nothing stopped under rule 4. The full freeze is in `env_freeze.txt`.

## How to run

`run/replay.sh` mounts the tree read-only and runs each `bug.py` 3 times plus `ori.py`/`original.py` once. Each script runs in its own process with a 60 s timeout, in a scratch cwd. Outputs are `replay_results.jsonl` and `replay.log`. The expected symptom of each bug comes from its GitHub issue (`expected.tsv`). The two "known" TF bugs have no issue, so we inferred abort from paper Table VI by elimination.

## Result

**31 of the 33 CPU-checkable reproducers reproduce on arm64 with the expected symptom.** The other 4 of the 37 need CUDA. All 37 seed programs (`ori.py`/`original.py`) exit cleanly. Nothing timed out or hit OOM.

| | CPU-checkable | reproduce | no | needs CUDA (n/a) |
|---|---|---|---|---|
| PyTorch (10) | 7 | 6: 4/5 runtime error (INTERNAL ASSERT x3, rfftfreq leaf-grad), 2/2 SIGSEGV | 1: fft.fft2 | 3: all, Tensor.to, fft.fft (cuFFT) |
| TensorFlow (27) | 26 | 25: 23/24 SIGABRT, 2/2 SIGSEGV | 1: linalg.solve | 1: experimental.numpy.cos |
| Total (37) | 33 | **31** | 2 | 4 |

The two non-reproductions:
- `torch.fft.fft2(x, dim=[])` (pt#120986). On x86 it raises `MKL FFT error`. The arm64 torch build has no MKL (it uses pocketfft), so the call exits cleanly but **returns uninitialised memory**: values up to 1e33 that change from run to run, not equal to the input. The bug is still there, but here it shows as a silent wrong result, which a crash oracle cannot catch.
- `tf.linalg.solve` (tf#63339). On arm64 TF 2.15.0 this raises a graceful `InvalidArgumentError: All input tensors must have the same rank`. The issue reported `Check failed: d < dims()` followed by an abort on x86. We could not tell whether the difference comes from the architecture or the patch level: an x86 cross-check is not allowed (rule 4).

Other observations:
- For every TF abort whose issue quotes a `Check failed` line, the arm64 line matches.
- `AvgPoolGrad` and `TensorListConcat` are heap corruption, not CHECK failures: glibc reports `free(): corrupted unsorted chunks` and `munmap_chunk(): invalid pointer`. AvgPoolGrad gave SIGABRT 2/3 and SIGSEGV 1/3.
- The CPU halves of the CPU/GPU bugs run on arm64. `torch.Tensor.to` (NaN to int32) prints `tensor([0])` on arm64 CPU, while the issue reports `-2147483648` on x86 CPU and `0` on GPU. So the arm64 CPU already disagrees with the x86 CPU, because NaN-to-int is undefined behaviour.
- Our per-issue classification gives PyTorch 2 inconsistency, 6 runtime error and 2 segfault. Paper Table VI gives 3 / 5 / 2. The paper probably counts one GPU-side bug differently. TF matches Table VI exactly (24 / 2 / 1).

| # | lib | API | issue | expected | observed (3 runs) | detail on arm64 | reproduces |
|---|---|---|---|---|---|---|---|
| 1 | torch | `torch.Tensor.to` | pt#121226 | cpu_gpu_inconsistency | exception | AssertionError (no CUDA); CPU half prints tensor([0]) | n/a-needs-cuda |
| 2 | torch | `torch.all` | pt#120875 | cpu_gpu_inconsistency | exception | AssertionError (no CUDA); CPU half prints tensor(False) | n/a-needs-cuda |
| 3 | torch | `torch.conj_physical` | pt#120989 | runtime_error | exception | RuntimeError input.is_sparse() INTERNAL ASSERT FAILED | yes (3/3) |
| 4 | torch | `torch.fake_quantize_per_channel_affine` | pt#120903 | runtime_error | exception | RuntimeError INTERNAL ASSERT FAILED | yes (3/3) |
| 5 | torch | `torch.fft.fft` | pt#120902 | runtime_error (cuFFT, GPU only) | exception | AssertionError (no CUDA); CPU half fine | n/a-needs-cuda |
| 6 | torch | `torch.fft.fft2` | pt#120986 | runtime_error (MKL FFT) | clean | returns uninitialised memory (no MKL on arm64) | no (0/3) |
| 7 | torch | `torch.fft.rfftfreq` | pt#120988 | runtime_error | exception | RuntimeError leaf Variable ... in-place | yes (3/3) |
| 8 | torch | `torch.lu_unpack` | pt#121584 | segfault | SIGSEGV | | yes (3/3) |
| 9 | torch | `torch.quantized_max_pool1d` | pt#121585 | segfault | SIGSEGV | | yes (3/3) |
| 10 | torch | `torch.where` | pt#121397 | runtime_error | exception | RuntimeError INTERNAL ASSERT FAILED | yes (3/3) |
| 11 | tf | `tf.audio.decode_wav` | tf#63687 | abort | SIGABRT | Non-OK-status InitDims: Expected a non-negative size | yes (3/3) |
| 12 | tf | `tf.experimental.numpy.cos` | tf#63271 | cpu_gpu_inconsistency | clean | `gpu:0` soft-placed on CPU | n/a-needs-cuda |
| 13 | tf | `tf.image.draw_bounding_boxes` | tf#63688 | abort | SIGABRT | Check failed: d < dims() (3 vs. 3) | yes (3/3) |
| 14 | tf | `tf.io.TFRecordOptions` | tf#63337 | abort | SIGABRT | Non-OK-status: deflateInit failed with status -2 | yes (3/3) |
| 15 | tf | `tf.linalg.solve` | tf#63339 | abort | exception | InvalidArgumentError: All input tensors must have the same rank | no (0/3) |
| 16 | tf | `tf.quantization.fake_quant_with_min_max_vars_per_channel` | tf#63351 | abort | SIGABRT | Check failed: d >= 0 (0 vs. -1) | yes (3/3) |
| 17 | tf | `tf.raw_ops.AudioSpectrogram` | tf#63352 | segfault | SIGSEGV | | yes (3/3) |
| 18 | tf | `tf.raw_ops.AvgPoolGrad` | tf#63353 | abort | SIGABRT,SIGSEGV,SIGABRT | free(): corrupted unsorted chunks | yes (2/3) |
| 19 | tf | `tf.raw_ops.DatasetToTFRecord` | tf#63689 | abort | SIGABRT | Check failed: 1 == NumElements() (1 vs. 2) | yes (3/3) |
| 20 | tf | `tf.raw_ops.Dilation2DBackpropFilter` | known, no issue | abort | SIGABRT | Check failed: NDIMS == dims() (4 vs. 5) | yes (3/3) |
| 21 | tf | `tf.raw_ops.DrawBoundingBoxes` | tf#63354 | abort | SIGABRT | Check failed: d < dims() (3 vs. 3) | yes (3/3) |
| 22 | tf | `tf.raw_ops.DrawBoundingBoxesV2` | tf#63354 | abort | SIGABRT | Check failed: d < dims() (3 vs. 3) | yes (3/3) |
| 23 | tf | `tf.raw_ops.ExperimentalDatasetToTFRecord` | tf#63691 | abort | SIGABRT | Check failed: 1 == NumElements() (1 vs. 2) | yes (3/3) |
| 24 | tf | `tf.raw_ops.FakeQuantWithMinMaxVarsPerChannel` | tf#63355 | abort | SIGABRT | Check failed: d >= 0 (0 vs. -1) | yes (3/3) |
| 25 | tf | `tf.raw_ops.FusedPadConv2D` | tf#63376 | abort | SIGABRT | Check failed: d < dims() (3 vs. 3) | yes (3/3) |
| 26 | tf | `tf.raw_ops.QuantizeAndDequantizeV3` | tf#63693 | abort | SIGABRT | Check failed: 1 == NumElements() (1 vs. 12) | yes (3/3) |
| 27 | tf | `tf.raw_ops.ResourceApplyGradientDescent` | tf#63695 | abort | SIGABRT | Check failed: dtype() == expected_dtype (8 vs. 1) | yes (3/3) |
| 28 | tf | `tf.raw_ops.ResourceApplyMomentum` | tf#63696 | abort | SIGABRT | Check failed: dtype() == expected_dtype (8 vs. 1) | yes (3/3) |
| 29 | tf | `tf.raw_ops.ResourceApplyProximalAdagrad` | tf#63697 | abort | SIGABRT | Check failed: dtype() == expected_dtype (1 vs. 2) | yes (3/3) |
| 30 | tf | `tf.raw_ops.ResourceGather` | known, no issue | abort | SIGABRT | Check failed: dtype() == expected_dtype (1 vs. 3) | yes (3/3) |
| 31 | tf | `tf.raw_ops.ResourceSparseApplyKerasMomentum` | tf#63720 | abort | SIGABRT | Check failed: dtype() == expected_dtype (8 vs. 1) | yes (3/3) |
| 32 | tf | `tf.raw_ops.StatefulPartitionedCall` | tf#63721 | abort | SIGABRT | Check failed: index < outputs_.size() (0 vs. 0) | yes (3/3) |
| 33 | tf | `tf.raw_ops.TensorListConcat` | tf#63722 | abort (flaky per issue) | SIGABRT | munmap_chunk(): invalid pointer | yes (3/3) |
| 34 | tf | `tf.raw_ops.TensorScatterSub` | tf#63378 | abort | SIGABRT | Check failed: d < dims() (1 vs. 1) | yes (3/3) |
| 35 | tf | `tf.raw_ops.UnicodeEncode` | tf#63379 | segfault | SIGSEGV | | yes (3/3) |
| 36 | tf | `tf.tensor_scatter_nd_add` | tf#63380 | abort | SIGABRT | Check failed: d < dims() (1 vs. 1) | yes (3/3) |
| 37 | tf | `tf.tensor_scatter_nd_update` | tf#63375 | abort | SIGABRT | Check failed: d < dims() (1 vs. 1) | yes (3/3) |

## Pipeline notes for a pilot

- **Stages.** (I) `edge_case_extraction/`: libclang over `TORCH_CHECK` sites, then LLM clustering plus `text-embedding-ada-002`. Its output ships in `results/unique_mutators.json`: 21 type patterns and 146 edge cases, against the paper's 20 and 132. (II) `get_api_reference/`: the LLM writes API descriptions and types; results are shipped for torch (1593 APIs) and TF (3316). (III) `gen_program/genPrograms.py` generates the seed programs; `results/{torch,tf}/api_programs.json` ships 1445 and 1865 valid seeds. Then `gen_prompts_for_mutators.py` (no LLM), `runPrompts.py` (LLM, 20 threads) and `extract_programs.py`.
- **No executor or oracle is shipped.** Nothing runs the mutated programs or classifies crashes and CPU/GPU differences. `validate.py`'s `run_cmd` (from TitanFuzz) maps exit codes but is only used for seed validation. A pilot needs a small runner, for example `replay.py`'s `run()`.
- **LLM calls per API.** For the seed, `genPrograms.py` makes 1 call, plus up to 2 format re-asks, plus up to 2 debug rounds of up to 3 calls each: 1 to 9 calls per API. The paper reports 2839/1593 = 1.8 for torch and 13938/3316 = 4.2 for TF. Mutation is exactly one call per prompt, with no validation loop. Counted by running the authors' generator on their shipped data (`count_prompts.sh`, `prompt_counts.jsonl`): torch has 26,774 prompts over 1,165 APIs (mean 23, median 9, p90 54, max 348). TF has 38,887 prompts over 1,712 APIs (mean 22.7, median 11, p90 46, max 542). Which prompts are chosen is random (`random.sample`, unseeded), but the count per API is deterministic.
- **Pointing it at Vertex Gemini without edits.** The model is hard-coded as `gpt-3.5-turbo-1106` (`openai_parallel_toolkit/api/model.py` ignores `model_name`, and `genPrograms.py` maps it too), so a thin wrapper has to rewrite it. The wrapper patches `openai.ChatCompletion.create` to set `model=os.environ["LLM_MODEL"]` (e.g. `google/gemini-2.5-flash`) and then calls `runpy.run_path(script, run_name="__main__")`. For the base URL, `runPrompts.py` and `get_reference_torch.py` take `api_base` from `../config.json`, so use a scratch copy of the tree with its own `config.json`, the same pattern as `count_prompts.sh`. `genPrograms.py` reads `api_base` but never applies it, so set the `OPENAI_API_BASE` env var, which openai 0.27 reads at import. Use `https://aiplatform.googleapis.com/v1/projects/$VERTEX_PROJECT/locations/global/endpoints/openapi`. Auth is an OAuth access token (valid 1 h). Put a dummy in the scratch `config.json` `api_keys` and have the wrapper inject the real token as `api_key` at call time, refreshing it when it expires. This matters because `genPrograms.py` runs `print("key:", key)` on every request (rule 6). Also watch `request_timeout=20` in `genPrograms.py`, which may be too short with Gemini thinking on, and its retry loop, which never gives up on a persistent error.
