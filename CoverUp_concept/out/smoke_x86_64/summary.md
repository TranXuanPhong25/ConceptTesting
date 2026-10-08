# CoverUp + concepts: smoke_x86_64

Model vertex_ai/gemini-2.5-flash; seeds s1; 3 modules with mutation results in every arm and seed, 3 with coverage. Means over modules of the per-module mean over seeds.

| arm | coverage % | line cov % | concept-site cov % | mutation score % | concept-site kill % | dropped test files | segments with block | USD |
|---|---|---|---|---|---|---|---|---|
| coverup | 92.2 | 94.1 | 88.1 | 81.3 | 58.6 | 0 | 0/27 | 0.05 |
| concept | 91.1 | 93.0 | 88.1 | 79.4 | 64.6 | 0 | 17/27 | 0.05 |
| concept_reason | 88.5 | 91.8 | 88.1 | 78.7 | 60.0 | 0 | 17/27 | 0.04 |
| placebo_reason | 88.8 | 90.7 | 81.0 | 68.2 | 43.1 | 0 | 17/27 | 0.06 |
| ide | 91.7 | 92.9 | 85.7 | 73.6 | 45.4 | 0 | 1/27 | 0.04 |

Paired by module (Wilcoxon signed-rank, two-sided; n = modules with a nonzero difference):

| contrast | metric | mean A | mean B | A>B | B>A | n | p |
|---|---|---|---|---|---|---|---|
| concept_reason vs placebo_reason | mut | 78.7 | 68.2 | 2 | 0 | 2 | 0.5 |
| concept_reason vs placebo_reason | cov | 88.5 | 88.8 | 1 | 1 | 2 | 1 |
| concept_reason vs placebo_reason | site_mut | 60.0 | 43.1 | 2 | 0 | 2 | 0.5 |
| concept_reason vs placebo_reason | site_cov | 88.1 | 81.0 | 1 | 0 | 1 | 1 |
| concept vs coverup | mut | 79.4 | 81.3 | 1 | 1 | 2 | 1 |
| concept vs coverup | cov | 91.1 | 92.2 | 0 | 1 | 1 | 1 |
| concept vs coverup | site_mut | 64.6 | 58.6 | 1 | 0 | 1 | 1 |
| concept vs coverup | site_cov | 88.1 | 88.1 | 0 | 0 | 0 | 1 |
| concept_reason vs coverup | mut | 78.7 | 81.3 | 0 | 2 | 2 | 0.5 |
| concept_reason vs coverup | cov | 88.5 | 92.2 | 1 | 2 | 3 | 0.75 |
| concept_reason vs coverup | site_mut | 60.0 | 58.6 | 1 | 1 | 2 | 1 |
| concept_reason vs coverup | site_cov | 88.1 | 88.1 | 1 | 1 | 2 | 1 |
| placebo_reason vs coverup | mut | 68.2 | 81.3 | 0 | 2 | 2 | 0.5 |
| placebo_reason vs coverup | cov | 88.8 | 92.2 | 0 | 2 | 2 | 0.5 |
| placebo_reason vs coverup | site_mut | 43.1 | 58.6 | 0 | 2 | 2 | 0.5 |
| placebo_reason vs coverup | site_cov | 81.0 | 88.1 | 0 | 2 | 2 | 0.5 |
| ide vs coverup | mut | 73.6 | 81.3 | 0 | 2 | 2 | 0.5 |
| ide vs coverup | cov | 91.7 | 92.2 | 1 | 1 | 2 | 1 |
| ide vs coverup | site_mut | 45.4 | 58.6 | 1 | 1 | 2 | 1 |
| ide vs coverup | site_cov | 85.7 | 88.1 | 1 | 1 | 2 | 1 |
| concept_reason vs concept | mut | 78.7 | 79.4 | 1 | 1 | 2 | 1 |
| concept_reason vs concept | cov | 88.5 | 91.1 | 1 | 2 | 3 | 0.75 |
| concept_reason vs concept | site_mut | 60.0 | 64.6 | 1 | 1 | 2 | 1 |
| concept_reason vs concept | site_cov | 88.1 | 88.1 | 1 | 1 | 2 | 1 |

Replication check: stock coverup arm 92.2% vs the authors' gpt-4o run 1 78.2% (same 3 modules).

Cost (ledger):

- coverup: 344 calls (279 errors), in 54,976 / out 11,457 tokens, $0.045
- ide: 416 calls (357 errors), in 44,157 / out 9,898 tokens, $0.038
- concept_reason: 427 calls (366 errors), in 54,714 / out 11,170 tokens, $0.044
- concept: 489 calls (420 errors), in 61,837 / out 11,400 tokens, $0.047
- placebo_reason: 414 calls (344 errors), in 72,481 / out 14,999 tokens, $0.059
