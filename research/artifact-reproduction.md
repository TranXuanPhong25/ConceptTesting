# Official Artifact Reproduction Tracker

This tracker separates paper-faithful runs of upstream artifacts from local
MVPs in `experiments/`. A local MVP result must not be reported as an upstream
artifact result. Upstream checkouts belong in ignored `.artifacts/` directories
and must remain unmodified.

## Environment used

- Host: Linux `x86_64`, 16 CPUs, approximately 23 GiB RAM.
- Docker engine: Linux `amd64`.
- GPU: unavailable (`nvidia-smi` is not installed).

Apple Silicon Docker can emulate `linux/amd64`, but is too slow and
memory-constrained for a fair campaign. A future run should use Linux x86_64,
at least 16 CPU cores and 32 GiB RAM, plus an NVIDIA GPU for LLAMAFUZZ.

## Artifact status

| Artifact | Pinned upstream revision | Status | Evidence / blocker |
| --- | --- | --- | --- |
| G2FUZZ | `f62cc550c0cdc715bc960937d3017fcb1e5c11bc` | Partial health check passed; full upstream build/campaign deferred | The README-prescribed `make source-only` built an `amd64` image; `afl-fuzz -h` and `afl-clang-fast --version` ran. The unmodified Dockerfile calls `make distrib`, whose QEMU step assumes a missing `qemu_mode/qemuafl` submodule; it fails with “Not checked out”. No fuzzing campaign was run. |
| CKGFuzzer | `bb50d2fd81c19b82cdbf6f96832097705decd57e` | Source checkout and syntax check passed; pipeline deferred | Host lacks CodeQL and required runtime packages (`yaml`, `openai`, `langchain`, `chromadb`, `llama_index`, `sentence_transformers`). Shipped target configs have empty LLM API-key fields. |
| LLAMAFUZZ | `a46a5328c3b7f26b5fe3af9dc4557026c77300a3` | Source checkout verified; mutator/campaign deferred | Mutator requires CUDA tensors and bitsandbytes 4-bit loading. Host has no NVIDIA GPU/driver and the artifact requires authorized access to gated `meta-llama/Llama-2-7b-chat-hf`. |
| STRUT | Paper reviewed; artifact not reproduced | No public, independently runnable artifact was found; the reported tool is integrated with commercial SunwiseAUnit. |
| HGFuzzer | Paper/repository search incomplete | No official public code/artifact was confirmed. |

## Exact scope of the G2FUZZ workaround

The successful G2FUZZ image used a temporary Dockerfile outside this
repository that changed the Docker build command from `make distrib` to the
README-documented `make source-only`. Upstream source was not edited. This
establishes only that the core AFL++/G2FUZZ toolchain builds on this host; it
does not validate upstream QEMU mode, LLM seed generation, a target build, or
a fuzzing campaign.

## Local 9router adapter

The ignored G2FUZZ checkout contains a local, uncommitted adapter that passes
`G2FUZZ_BASE_URL` to the existing OpenAI SDK. The local credential script uses
`ROUTER_BASE_URL`, `ROUTER_API_KEY`, and `LLM_MODEL`, defaulting to
`vertex/gemini-3-flash-preview`. This is a reproducibility configuration
change, not part of the upstream artifact, and must be reported separately.
The adapter rate-limits requests to five per minute by default and retries HTTP
429 responses with backoff; record any changed `G2FUZZ_RPM` value.

## Conditions before a paper-faithful campaign

1. For G2FUZZ, document a separate patch for the missing QEMU checkout, or
   use a source-only build with a compiled AFL/CMplog target, initial seeds and
   an OpenAI-compatible key configured through the artifact settings.
2. For CKGFuzzer, install Linux CodeQL and the pinned Linux-64 Python
   environment, configure a valid LLM key without committing it, and build a
   documented target such as cJSON.
3. For LLAMAFUZZ, use an NVIDIA CUDA host with compatible PyTorch/bitsandbytes,
   sufficient GPU memory, and authorized Llama-2 access.
4. Re-clone at the pinned revisions, run health checks, then a bounded smoke
   test and finally the paper's fixed campaign budget. Preserve commands,
   target revisions, input corpora, wall time, raw logs, coverage and crashes.
5. Only after an upstream baseline is complete, add ConceptCoder as a
   separately versioned ablation. Never overwrite the upstream pipeline.
