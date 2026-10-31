# Multi-SWT-Bench replication-package audit

Checked 2026-10-15. Paper: [arXiv:2609.34752 v1](https://arxiv.org/abs/2609.34752).

- The paper directly links [Zenodo DOI 10.5281/zenodo.22961970](https://doi.org/10.5281/zenodo.22961970) as the replication package.
- Zenodo API metadata matches the title; version record 22961970 was created 2026-09-25, reports CC BY 4.0 metadata, and contains `multi-swt-bench-replication.zip` (225,722,979 bytes; MD5 `1ad4bc29eaf2bb7d8198a2f6afc69053`). A different nearby DOI 21887892 is an unrelated BehaviorAudit software release, not this paper.
- Inspected the ZIP central directory using HTTP Range requests only; did not download/extract the complete archive or execute any package code. It contains 289 entries.
- Confirmed frozen lists: `benchmark/full.txt` has 1,963 unique IDs (SHA-256 `2c787a54a0d9cbd3e722f0c66d95c9dd5b45356d21df36f1223334116842f557`); `benchmark/flash.txt` has 340 unique IDs (SHA-256 `8a8cb30105f85436052b69a4f5bb626cf39b63430af39c88a75f1ada7be567fb`). The paper uses the 340-task Lite/Flash subset for experiments.
- Archive includes `benchmark/build.py`, `sources.json`, `expected.json`, coverage/instance lists, multilingual evaluation harness and scoring, method-specific prompts and upstream patches, `methods/experiments.json`, setup/run/evaluate scripts, and 12 compressed result files for model/method runs.
- Embedded README documents Ubuntu 24.04, Python 3.12, Docker, benchmark construction, method setup, experiment execution, and result evaluation. Package's `LICENSE` is Apache-2.0; Zenodo metadata is CC BY 4.0. README cautions that third-party code/data retain upstream terms and the pinned MSWE-agent fork has conflicting license metadata and no LICENSE file.
- Statically inspected selected `README.md`, `LICENSE`, `methods/experiments.json` and `methods/run.py` via byte-range reads. The MOpenHands runner forwards `model`, `base_url`, API-key environment and `allowed_host` through a model API proxy, so local OpenAI-compatible endpoints appear adaptable but have not been tested.
- No API/model calls, full task execution, archive extraction, or source modification.
- Detailed paper verdict: `../../../../audit/reviews/089.json`.
