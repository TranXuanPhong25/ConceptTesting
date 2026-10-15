# v19_rulegen results — 2026-10-15

Complete: 20 design dev tasks, K=1; 120 samples. Frozen protocol/generation, pre-gold provenance/guidance, all native scores and comparisons verified. No rerun needed.

Representation17/20; rule-first model/fault coverage13/20. All20 remain denominator.

| Arm | D_IO tasks /20 | D_IO input events | Selected inputs | Nonempty tasks | Calls |
|---|---:|---:|---:|---:|---:|
| plain | 3 | 4 | 28 | 9 | 60 |
| behavior | 3 | 4 | 18 | 7 | 60 |
| behavior+concept | 3 | 6 | 24 | 8 | 60 |
| placebo | 3 | 4 | 22 | 8 | 60 |
| toolinput | 4 | 8 | 30 | 10 | 60 |
| witness-only | 13 | 40 | 62 | 18 | 0 |

D_IO task detection means at least one contract-valid PUT/reference discrepancy with a saved-reference assertion also passing canonical. Input events count within arms, not distinct bugs.

Primary concept vs behavior:3/20 each; same detected tasks [27, 85, 149]. Raw and equal-input:0 wins/0 losses, sign p=1. Concept6 input events vs behavior4 does not increase task coverage.

Equal-input matched mean detecting tasks (100 fixed random subsets; fractional values are means, not new tasks):

- Concept vs behavior: 3.00 vs 3.00; wins/losses 0/0, nominal sign p=1.
- Concept vs plain: 2.41 vs 2.65; wins/losses 1/1, nominal sign p=1.
- Concept vs placebo: 2.61 vs 3.00; wins/losses 0/1, nominal sign p=1.
- Concept vs toolinput: 3.00 vs 3.00; wins/losses 0/0, nominal sign p=1.
- Concept vs witness-only: 2.76 vs 6.72; wins/losses 0/5, nominal sign p=0.0625.

Witness-only raw13/20 versus concept3/20; equal-input6.72 vs2.76. Matching discards tasks with zero concept inputs, so does not repair overall generation failure. Witness-only includes pre-gold candidate-model discrepancies plus prior frozen tool witnesses; this is reuse of shared discovery, not13 new LLM discoveries.

Generation bottleneck: {'SyntaxError': 203, 'ValueError': 9} static rejections among300 replies; 198 rejected replies contain leading prose and fenced code. Extracting the first code block would pass the unchanged checker in 141 cases (read-only diagnosis; no repaired output was generated/scored). Additional worker errors and domain rejection reduce yield. Sparse generation means this run does not isolate concept reasoning quality under a reliable output interface.

Costs:300 logical requests,269 physical requests and31 exact-cache hits. Logical accounting210,367 input /77,150 output tokens; physical token totals in JSON exclude cache hits.0 new reference requests. Parent v18/preexisting discovery costs excluded from incremental totals; they are common reused preprocessing, not free end-to-end discovery. See JSON for arm costs and transport attempts.

All arms have zero observed shared-reference false alarms. Candidate-property audit is separate: concept8 confirmed property/card events, behavior5, plain4, placebo6, toolinput12, witness-only51; zero observed property false alarms. These counts can repeat the same input across cards, and are not D_IO. Placebo has4 property abstentions. No global property-validity claim.

Conclusion: no demonstrated concept generation gain; direct frozen witness reuse is stronger in this exploratory run. Before another comparison, preregister a separate version with a reliable output interface and assess validity/yield; do not change or repair this frozen run.
