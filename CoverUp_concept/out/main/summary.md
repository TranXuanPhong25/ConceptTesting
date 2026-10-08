# CoverUp + concepts: main

Model vertex_ai/gemini-2.5-flash; seeds s1; 57 modules with mutation results in every arm and seed, 58 with coverage. Means over modules of the per-module mean over seeds.

| arm | coverage % | line cov % | concept-site cov % | mutation score % | concept-site kill % | dropped test files | segments with block | USD |
|---|---|---|---|---|---|---|---|---|
| coverup | 69.2 | 71.9 | 64.8 | 46.9 | 45.3 | 8 | 0/626 | 2.41 |
| concept | 68.7 | 71.6 | 65.7 | 47.7 | 50.7 | 8 | 364/613 | 2.91 |
| concept_reason | 67.4 | 70.2 | 64.5 | 47.7 | 45.8 | 20 | 356/605 | 2.95 |
| placebo_reason | 66.4 | 69.3 | 61.1 | 45.2 | 42.9 | 20 | 362/614 | 2.86 |
| ide | 64.9 | 68.0 | 61.2 | 45.3 | 45.1 | 8 | 88/605 | 2.89 |

Paired by module (Wilcoxon signed-rank, two-sided; n = modules with a nonzero difference):

| contrast | metric | mean A | mean B | A>B | B>A | n | p |
|---|---|---|---|---|---|---|---|
| concept_reason vs placebo_reason | mut | 47.7 | 45.2 | 27 | 17 | 44 | 0.445 |
| concept_reason vs placebo_reason | cov | 67.4 | 66.4 | 27 | 16 | 43 | 0.31 |
| concept_reason vs placebo_reason | site_mut | 45.8 | 42.9 | 14 | 7 | 21 | 0.258 |
| concept_reason vs placebo_reason | site_cov | 64.5 | 61.1 | 20 | 15 | 35 | 0.561 |
| concept vs coverup | mut | 47.7 | 46.9 | 18 | 22 | 40 | 0.868 |
| concept vs coverup | cov | 68.7 | 69.2 | 16 | 28 | 44 | 0.35 |
| concept vs coverup | site_mut | 50.7 | 45.3 | 14 | 8 | 22 | 0.235 |
| concept vs coverup | site_cov | 65.7 | 64.8 | 14 | 15 | 29 | 0.831 |
| concept_reason vs coverup | mut | 47.7 | 46.9 | 23 | 24 | 47 | 0.912 |
| concept_reason vs coverup | cov | 67.4 | 69.2 | 19 | 25 | 44 | 0.369 |
| concept_reason vs coverup | site_mut | 45.8 | 45.3 | 10 | 11 | 21 | 0.838 |
| concept_reason vs coverup | site_cov | 64.5 | 64.8 | 15 | 20 | 35 | 0.623 |
| placebo_reason vs coverup | mut | 45.2 | 46.9 | 18 | 26 | 44 | 0.54 |
| placebo_reason vs coverup | cov | 66.4 | 69.2 | 14 | 25 | 39 | 0.126 |
| placebo_reason vs coverup | site_mut | 42.9 | 45.3 | 8 | 11 | 19 | 0.441 |
| placebo_reason vs coverup | site_cov | 61.1 | 64.8 | 12 | 21 | 33 | 0.221 |
| ide vs coverup | mut | 45.3 | 46.9 | 17 | 26 | 43 | 0.329 |
| ide vs coverup | cov | 64.9 | 69.2 | 15 | 25 | 40 | 0.0408 |
| ide vs coverup | site_mut | 45.1 | 45.3 | 12 | 5 | 17 | 0.431 |
| ide vs coverup | site_cov | 61.2 | 64.8 | 11 | 15 | 26 | 0.341 |
| concept_reason vs concept | mut | 47.7 | 47.7 | 20 | 22 | 42 | 0.587 |
| concept_reason vs concept | cov | 67.4 | 68.7 | 18 | 21 | 39 | 0.557 |
| concept_reason vs concept | site_mut | 45.8 | 50.7 | 8 | 10 | 18 | 0.369 |
| concept_reason vs concept | site_cov | 64.5 | 65.7 | 11 | 19 | 30 | 0.428 |

Replication check: stock coverup arm 69.2% vs the authors' gpt-4o run 1 77.7% (same 58 modules).

Cost (ledger):

- coverup: 9172 calls (7592 errors), in 2,827,172 / out 655,654 tokens, $2.410
- placebo_reason: 8755 calls (7098 errors), in 3,486,465 / out 757,947 tokens, $2.862
- ide: 7715 calls (6151 errors), in 3,230,880 / out 812,924 tokens, $2.894
- concept: 7369 calls (5813 errors), in 3,792,663 / out 744,577 tokens, $2.913
- concept_reason: 7385 calls (5847 errors), in 3,063,700 / out 848,484 tokens, $2.953
