# Official Artifact Reproduction Tracker

This tracker separates paper-faithful artifact runs from the local MVPs in
`experiments/`. Do not report an MVP result as an upstream-artifact result.

## Deferred Environment

Use a Linux `x86_64` host or VM for the following runs. Apple Silicon Docker
can emulate this environment but is too slow and memory-constrained for a fair
campaign.

| Artifact | Pinned upstream revision | Status | Required environment |
| --- | --- | --- | --- |
| G2FUZZ | `f62cc550c0cdc715bc960937d3017fcb1e5c11bc` | Deferred after starting the upstream `linux/amd64` Docker build | Linux x86_64, Docker, AFL++ target binaries, an OpenAI-compatible key configured exactly through the artifact's settings |
| CKGFuzzer | `bb50d2fd81c19b82cdbf6f96832097705decd57e` | Deferred | Linux x86_64, Docker, CodeQL, the artifact's large Linux-64 Python environment, target project setup, LLM configuration |
| LLAMAFUZZ | `a46a5328c3b7f26b5fe3af9dc4557026c77300a3` | Deferred | Linux x86_64 with NVIDIA CUDA GPU; upstream uses CUDA PyTorch, bitsandbytes 4-bit loading, and the Llama-2-7B base model plus shipped adapters |

## Artifact Availability

| Paper | Artifact state |
| --- | --- |
| STRUT | No public, independently runnable artifact found. The reported tool is integrated with commercial SunwiseAUnit. |
| HGFuzzer | No official public code/artifact confirmed. |

## Resume Order

1. Provision a Linux x86_64 machine with at least 16 CPU cores, 32 GB RAM, and
   enough storage for Docker images/corpora. Add an NVIDIA CUDA GPU for
   LLAMAFUZZ.
2. Re-clone each repository at the pinned revision and retain unmodified
   upstream source in `.artifacts/`.
3. Run upstream build/health checks first, then a documented bounded smoke,
   then the paper's fixed campaign budget. Keep generated configs, commands,
   target revisions, corpus, wall clock, and raw logs.
4. Only after a baseline artifact run is complete, add ConceptCoder as a
   separately versioned ablation. Do not overwrite the upstream pipeline.
