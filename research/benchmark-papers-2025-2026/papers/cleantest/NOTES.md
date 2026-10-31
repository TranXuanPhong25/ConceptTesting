# Less Is More: On the Importance of Data Quality for Unit Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Less Is More: On the Importance of Data Quality for Unit Test Generation](https://doi.org/10.1145/3715778)

Year/venue: 2025 FSE

Dataset: Methods2Test/ATLAS training; Defects4J validation

Input setting: fine-tuning on filtered code/test pairs

Model: CodeBERT, AthenaTest, StarCoder, CodeLlama-7B

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Data quality control; không phải base tốt nhất cho prompt-only concept extension.

Limitation: Training/checkpoints và code release chưa verified; same base model không đủ replicate reported gains.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:37:29.595205+07:00

Public replication package is substantive and covers exact paper scripts/data/evaluation, but exact fine-tuned model weights absent. Supporting candidate only if retraining access/resources exist; do not infer exact reproduction from artifact completeness.

Blockers: No trained checkpoints in artifact models.zip;fullpaper uses 4models and coveragefilter;retraining substantial (4xRTXA800) and local run not performed; Model weights pretrainedbase access/precise revisions not confirmed;paperCodeLlama7B/StarCoder requireLoRAfine-tuning; Methods2Test/Atlas splits and paper aggregate percentages have modest count/format inconsistencies acrossREADME (e.g.annotations 43.6357 vs paper41.64; noise examples duplicates);pin exactarchive then recalc; Leakage control removes equal function names, not project-level duplicates;paper acknowledges Defects4J overlap threat; Coverage predicted by CodeGPT using previous study coverage-labeleddataset;data/source lineage can influence filter and evaluation; Comparisonis training-data intervention;not a new test-generator/concept method;Defects4J outcomes are transferred tests but testcases train from broad repo data; Noauthor training/inference/reproduction executed

Sources: https://doi.org/10.1145/3715778, https://zenodo.org/records/15347368, https://zenodo.org/records/13767073
