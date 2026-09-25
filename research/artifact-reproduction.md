# Official Artifact Reproduction Tracker

This tracker separates runs of the original upstream artifacts from the local
MVPs in `experiments/`. A local MVP result must not be reported as an upstream
artifact result.

## Environment used

- Host: Linux `x86_64`, 16 CPUs, approximately 23 GiB RAM.
- Docker engine: Linux `amd64`.
- GPU: unavailable (`nvidia-smi` is not installed).
- Artifact checkouts live in ignored `.artifacts/` directories.

## Results on 2026-09-21

| Artifact | Pinned upstream revision | Result | Evidence / blocker |
| --- | --- | --- | --- |
| G2FUZZ | `f62cc550c0cdc715bc960937d3017fcb1e5c11bc` | Partial health check passed; original full Docker build failed | The README-prescribed `make source-only` built an `amd64` image and its `afl-fuzz -h` and `afl-clang-fast --version` ran. The unmodified Dockerfile calls `make distrib`, whose optional QEMU step assumes `qemu_mode/qemuafl` is a Git submodule. This revision has no `.gitmodules`; the build fails at `git submodule update ./qemuafl` with “Not checked out”. No fuzzing campaign was run. |
| CKGFuzzer | `bb50d2fd81c19b82cdbf6f96832097705decd57e` | Source checkout and syntax check passed; pipeline not run | The host lacks CodeQL and every required Python runtime package checked (`yaml`, `openai`, `langchain`, `chromadb`, `llama_index`, and `sentence_transformers`). The shipped target configs also have empty LLM API-key fields. |
| LLAMAFUZZ | `a46a5328c3b7f26b5fe3af9dc4557026c77300a3` | Source checkout verified; mutator not run | The mutator explicitly sends tensors to CUDA, and the supplied checkpoint metadata uses bitsandbytes 4-bit loading. This host has no NVIDIA GPU/driver. It also requires access to gated `meta-llama/Llama-2-7b-chat-hf`. |

## Exact scope of the G2FUZZ workaround

The successful G2FUZZ image was made with a temporary Dockerfile outside this
repository that changes the Docker build command from `make distrib` to `make
source-only`, the command documented in the upstream README. Upstream source
was not edited. This establishes that the core AFL++/G2FUZZ toolchain builds
on this host; it does **not** repair or validate the upstream full Dockerfile,
QEMU mode, an LLM seed-generation run, a target build, or a fuzzing campaign.

## Local 9router adapter

The ignored G2FUZZ checkout contains a local, uncommitted adapter that passes
`G2FUZZ_BASE_URL` to the existing OpenAI SDK. The supplied local credential
script uses the repository's 9router variables (`ROUTER_BASE_URL`,
`ROUTER_API_KEY`, and `LLM_MODEL`) and defaults to
`vertex/gemini-3-flash-preview`. This is a reproducibility configuration
change, not part of the upstream artifact; report it as a separate patched
configuration.

The adapter also rate-limits G2FUZZ's otherwise bursty upstream requests to
five requests per minute by default and retries HTTP 429 responses with
backoff. Record any changed `G2FUZZ_RPM` value in experiment metadata.

## Conditions before a paper-faithful campaign

1. For G2FUZZ, either fix the upstream QEMU checkout defect in a separately
   documented reproduction patch, or use a source-only build with a compiled
   AFL/CMplog target, initial seeds, and a configured OpenAI-compatible key.
2. For CKGFuzzer, install a Linux CodeQL bundle and the artifact's pinned
   Linux-64 Python environment; configure a valid LLM service key without
   committing it; then build one documented target (for example cJSON).
3. For LLAMAFUZZ, use an NVIDIA CUDA host with sufficient GPU memory, a
   compatible CUDA PyTorch/bitsandbytes stack, and authorized access to the
   Llama-2 base model.
4. Preserve commands, target revisions, input corpora, time budgets, raw logs,
   coverage, crashes, and all ConceptCoder ablations separately from baselines.
