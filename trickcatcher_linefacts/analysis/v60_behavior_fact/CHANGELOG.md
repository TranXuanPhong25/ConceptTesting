# v60_behavior_fact CHANGELOG

## 2026-10-25 (Claude)
Created from v59_blind_concept (Stage 2 scoring path) with a Qwen writer (endpoint client as v49 gen.py). New: Qwen
behaviour-fact extraction from the PUT (concept) and spec-fact extraction (placebo); 33 tasks; k = 2.
Self-review (no subagents, user rule): blind prompts byte-identical to Stage 2 plain for 33/33 tasks; prompts built only
from task_view (statement, public tests, signature, masked PUT); only task 75 exceeds the 8192 context with the code
(known since v46) -> recorded as context_overflow (empty answer) in `facts` and `code`, reported; oracle/filter shared.
