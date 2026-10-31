# TOGLL: Correct and Strong Test Oracle Generation with LLMs

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [TOGLL: Correct and Strong Test Oracle Generation with LLMs](https://arxiv.org/abs/2405.03786)

Year/venue: 2025 ICSE; preprint 2024

Dataset: SF110 training + OracleEval25 + Defects4J real-bug evaluation (paper v2 III-E)

Input setting: prefix + method/documentation context

Model: Fine-tuned code LLMs including CodeGen-350M

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Small oracle model baseline và oracle strength evaluation.

Limitation: Defects4J experiment verified in paper v2; fine-tuned checkpoint/source not verified. Separate real bugs from mutation results and exclude prefix-only implicit failures when measuring assertion contribution.

Local reproduction: **not performed**. No author source modified.


## Correction and full review — 2026-10-15 (#35)

Full arXiv v2 text has now been read (11,131 words; hash in audit/reviews/035.json). The paper evaluates oracle correctness, diversity and strength; Defects4J uses 374 prefixes (304 assertion, 70 exception), while the 69,793 PIT mutants are a separate study. The paper explicitly defines TOGLL as fine-tuned CodeParrot-110M with P6 (prefix + doc + MUT).

The author Figshare artifact is public, substantial and includes fine-tuned weights. Its README and license PDFs were downloaded and checksum-verified; selected ZIP64 central-directory entries and relevant Python source were inspected through HTTP Range without retrieving/extracting the 6.66-GiB archive. `model.safetensors` exists for RQ5 TOGLL (444,048,000 bytes uncompressed); configs identify CodeParrot. Figshare license PDF states ODbL 1.0 for artifact and DBCL 1.0 for individual database contents; no separate permissive software license was verified.

Exact replay remains conditional: RQ5 inference code chooses `tc_mut` and `codeparrot_tc_mut`, while the paper says P6 and the included RQ5 checkpoint is under `model/TOGLL`. This needs author-package path/config clarification. Static source only; no run, no API call. Strong oracle-generation/Defects4J evaluation reference, but not a concept-based test-prefix generator.
