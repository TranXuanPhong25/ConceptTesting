# Multi-SWT-Bench: A Multilingual Benchmark for Reproduction Test Generation

Reviewed: 2026-10-15. Full paper and replication package verified. Grade: A- artifact; exact rerun conditional.

Paper: [arXiv:2609.34752 v1](https://arxiv.org/abs/2609.34752), 28 September 2026.

Task fit is very high for issue-conditioned bug-reproducing tests. The package has 1,963 full tasks across eight languages/51 repos; frozen Lite/Flash subset has 340 unique tasks and is used for every experiment. It was built from Multi-SWE-Bench issues and validates the golden tests' pre-fix fail/post-fix pass behavior. It does not use Defects4J, BugsInPy or SWT-Bench tasks experimentally.

Author-linked replication package: [Zenodo 22961970](https://doi.org/10.5281/zenodo.22961970), 225.7 MB, CC BY 4.0 metadata. Static range inspection verifies data/full and Lite ID lists, expected outcomes, build/evaluation scripts, four method integrations/prompts, experiment configs and cached result files for 12 configurations. Embedded package code is Apache-2.0; upstream code/data retain own terms, with an MSWE-agent fork license caveat.

This is the strongest multilingual SWT-style reproduction package in the audit. Paper's best score is 65.29% for Claude Code + Claude Opus 5; MOpenHands + Claude Sonnet 5 is 57.94%; DeepSeek-V4-Flash is 55.29% at $0.0175/task reported. README supports full/one-method setup and evaluation. MOpenHands runner has configurable model/base_url/API allowlist, so an OpenAI-compatible local Qwen endpoint may be possible after configuration; not tested. Exact hosted-model snapshots are not pinned, Docker setup is substantial, and no fault-root-cause taxonomy is provided.

No package source was executed and no model/API calls made. Detailed verdict: `audit/reviews/089.json`; artifact evidence: `public_evidence/source_audit.md`.
