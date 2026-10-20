---
name: concept-training-evidence-gap
description: Recent-run audit does not support prioritizing concept-to-input training; upstream admission/oracle/pool limits dominate observed losses
metadata:
  type: project
---

(2026-10-20, Codex assessment prompted by user) Proposed concept-to-input training
has no established go signal in current outputs. Synthesis in
trickcatcher_linefacts/analysis/recent_concept_failure_attribution_20261020.md and
RESULTS §11.76. This is an evidence assessment, not a claim that training cannot help.

v33's17 direct-only Python-value detections:11 upstream unknown/abstain,5 mechanical
rejections,1 input-search miss. Semantic accuracy not gold-labeled across that run;
do not call valid JSON a correct concept. v24 f06 already generates6 novel revealing
inputs but gate rejects them; f06 hypothesis was hidden, so no causal concept-use claim.
v32 C never attempted; v27/v28 show oracle model capability and little incremental
concept gain once it improves; v34/v35 show weak concept attribution and pool limits.

**Why:** accurate verbal concepts do not imply correct executable artifacts, evidence
grounding or additional useful information. These are different failure modes.
**How to apply:** do not present concept-to-input translation as the established main
bottleneck or propose training/bigger runs to salvage it. First identify independently
correct concepts with actual generation opportunity and a demonstrated translation
failure. Existing runs have not systematically labeled that conditional population.
