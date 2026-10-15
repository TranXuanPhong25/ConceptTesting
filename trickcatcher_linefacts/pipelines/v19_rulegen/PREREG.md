# v19 rulegen preregistration — 2026-10-15, before generation

Exploratory 20-task dev cohort inherited unchanged from v18; prior dev audit is known, no held-out claims.
Use ONLY parent prepared native behavior plus frozen candidates/pool/rule_first. No audit, LLM choice, or canonical labels for guidance.
Rule-first model unchanged, first up to 3 deterministic semantic alternatives. No replacement of imperfect/unsupported models.
Representation gate >=16/20; candidate/fault gate >=10/20. Failure stops all generation.
Primary behavior+concept vs behavior-only; controls plain, placebo, toolinput, witness-only. All 20 remain denominator, K=1.
Five LLM arms x20 tasks x3 slots =300 logical requests, 1024 output tokens each, temperature .7/top_p .95.
Each slot draws<=100; same domain-only validator, uniformly select<=2 valid inputs, dedup task sample, cap12 (effective <=6).
Witness-only samples<=6 from shared<=12 pool, no LLM. Pool is pre-gold rule-model/PUT discrepancies plus old frozen tool witnesses, seeded cap12.
Common pool available equally; concrete values appear only toolinput/witness-only. Concept gets abstract typed model/fault, no concrete witness values/outputs.
Same PUT, spec and base prompt context in all LLM arms. Same strategy seed per task/slot across arms. No repair or content retry.
Unsupported representation: behavior and concept arms same generic fallback. Missing card slots: behavior fallback.
Freeze sources/config and parent hashes before calls; freeze all 120 generated samples before reading scoring gold.
Evaluate same saved V11 spec-only references, no new reference requests; canonical only during scoring. D_IO primary, D_I, precision, false alarms, request/token/input costs secondary.
Paired raw and equal-input 100 seeded random-subset comparisons, not prefix matching. K=1 is exploratory, no promotion criterion.
Audit candidate-property false alarms separately from D_IO; discovery candidate discrepancies are not D_IO.
Resume exact cache only after transport interruptions; never modify frozen treatment. No paid fallback.
