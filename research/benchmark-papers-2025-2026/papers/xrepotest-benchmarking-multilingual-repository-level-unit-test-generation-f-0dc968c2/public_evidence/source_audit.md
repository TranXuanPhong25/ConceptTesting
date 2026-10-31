# Public source/data audit — #65 XRepoTest

Checked 2026-10-15. Full paper and appendices read. No code/model/data execution or downloads were performed.

## Identity and public artifacts

- Paper arXiv: [2608.25939v2](https://arxiv.org/abs/2608.25939), posted 15 September 2026. The paper says dataset and code are public at the repository below.
- Official author repository: [solis-team/XRepoTest](https://github.com/solis-team/XRepoTest/tree/39fb6ab3173136d3dac2d38ed7c98baf6c470270), verified public; HEAD `39fb6ab3173136d3dac2d38ed7c98baf6c470270`, commit author date 2026-08-27. GitHub tree: 313 entries / 3,349,430 bytes. Repository license: MIT.
- Public HuggingFace dataset [solis-soict/xrepotest](https://huggingface.co/datasets/solis-soict/xrepotest) verified via HuggingFace API: `private=false`, `gated=false`, card/tag license `mit`, dataset revision `cd694c00d20951aef189a406abac980a6b1c49d4` (2026-08-27).
- Dataset contains 40 JSONL artifacts: 5 base language files (~105 MB), 5 LSP-enriched files (~106 MB), 30 RAG-enriched files (~1.48 GB), ~1.69 GB total. The base group enables `standard` and `file_context`; LSP and RAG groups are optional context modes.

## Substantive implementation and model route

Static inspection covered README, LICENSE, `scripts/fetch_data.py`, CLI/config, prompt generation, OpenAI-compatible response generation and local vLLM wrapper, response preprocessing, Docker-based base evaluators, all five language evaluators, RAG/LSP systems, iterative repair, agentic evaluation, and tests. The README documents `pip install -e .`, fetching data from HF, pulling per-language Docker images, and running prompts → model responses → preprocess → evaluate; a local `--api_base` can connect a Qwen OpenAI-compatible endpoint. No paid model calls are required for local model inference. The user’s Qwen2.5-Coder-7B is not one of the exact 14 paper models (paper has Qwen3-8B and Qwen3-Coder-Next-80B), so using it is a new-model evaluation, not exact paper replication.

Raw `repo_data/` clones are not distributed; README states they are needed only to rebuild benchmark records/images from source. Published benchmark data and prebuilt Docker images are the intended evaluation route. Underlying repository code remains under upstream licenses.

## Fit and reproduction limits

The benchmark covers Rust/Go/Julia/PHP/Ruby, deliberately excluding Java and Python. Defects4J is only a related-work comparison, not an experiment; there is no Defects4J F2P, BugsInPy or SWT-Bench cohort. It generates tests for current focal implementations and evaluates compile/pass/coverage/invocation/mutation, not issue-report reproduction against fixed versions or developer oracles. Mutation tools are available only for Go, Rust and Ruby. It is therefore a strong complementary own-model repository-level test-quality evaluation, but not a direct match for the user's primary Java/Python issue-reproduction dataset.

Exact full paper replication is **conditional**: substantial Docker/toolchain setup and 14 original model routes; some hosted-model aliases change, and the Docker tags are `latest` rather than pinned digests. A bounded custom-Qwen single-language evaluation on the public base dataset is comparatively straightforward. No run was performed.
