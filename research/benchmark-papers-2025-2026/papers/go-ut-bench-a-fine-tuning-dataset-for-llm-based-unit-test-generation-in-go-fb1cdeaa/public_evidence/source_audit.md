# Public data/artifact audit — #81 Go-UT-Bench

Checked 2026-10-15 after full arXiv v2 reading. No downloads or execution.

- Paper arXiv: [2511.10868v2](https://arxiv.org/abs/2511.10868), 29 May 2026; CC BY 4.0.
- Paper Reproducibility Statement links [Nutanix/GO-UNITTEST-BENCH on HuggingFace](https://huggingface.co/datasets/Nutanix/GO-UNITTEST-BENCH).
- HuggingFace API: repository public and ungated, revision `24074620e2be3db20c11cba007649533cb677a30` (last modified 2025-02-11); files: train_data.json 124,067,486 bytes, test_data.json 30,268,029 bytes, val_data.json 20,647,345 bytes, total ~175 MB.
- The dataset API has no license tag/cardData license. The paper says samples come from ten permissively licensed repositories and provide code/test commit hashes. Upstream licenses still need per-record checks.
- No author GitHub source repository, fine-tuned checkpoint, data-curation code, AST chunking implementation, trainer, or GPT-4o-mini evaluator implementation was linked/found. Reproduction Statement links only the dataset.
- Exact paper setup: DeepSeek-Coder-V2-Lite-Instruct LoRA and Llama-3.2-3B-Instruct full fine-tuning; 2 epochs and 80GB H100 cited; GPT-4o-mini is sole pairwise judge. Local Qwen2.5-Coder-7B would be a new fine-tuning experiment, not either paper model.

**Reproduction verdict:** no code/weights, so exact execution is not feasible as released. Data-only adaptation could be a separate project if fine-tuning is authorized, but the paper's own evaluation does not compile or execute generated tests, assess bug detection, or validate its judge with humans. It is not a direct Defects4J/BugsInPy/SWT-Bench paper.
