# Pending registrations (PREREG.md is pinned by the running v7_mutref oracle stage; moved verbatim when it finishes)

## Final comparison protocol (registered 2026-10-13 ~21:05, user-approved, before any baseline/held-out output)
Addresses six fairness problems (user-reviewed critique, verified in data):
1. Dev (113 HumanEval tasks; even/odd; pilot) has been used repeatedly for design choices and is development data only.
   Confirmatory claims come only from held-out sets run once with a frozen configuration: VibePass LeetCode (66 PUTs,
   24 questions, statistics clustered by question) and MBPP+ real-bug (12 PUTs). Dev results are reported as such.
2. The final configuration is generated for real in strict mode (round 2 contributes only tool-verified inputs; the
   expected-value call covers exactly those inputs and is skipped when none is kept). No CPU-reconstructed arm is used
   for confirmatory claims; LLM calls/tokens are those of the real run.
3. Placebo control matched in budget: placebo-hybrid receives the same number of round-2 strategy requests as
   concept-hybrid for the same task/sample (as plain-hybrid already does), targeting placebo hints.
4. Budgets fixed at generation time and identical for every arm and baseline: at most 8 LLM calls and at most 20
   assertions per sample (assertions beyond 20 are dropped in generation order and recorded). Matched-count analysis is
   secondary and uses random equal-size subsets (fixed seed, 100 draws, mean), not prefix truncation.
5. TrickCatcher-full adapter: inputs serialised with repr/ast.literal_eval instead of a JSON round-trip (task 127 lost
   400/400 inputs); crash/timeout accounting and budgets aligned with the other arms; the 7 empty-pool tasks rerun.
   Until then no claim of beating TrickCatcher is made.
6. One scorer everywhere: output equality = EvalPlus-style comparison with the task's atol (floats rel 1e-6 / atol,
   recursive over lists/tuples, exceptions/timeouts as distinct outcomes), used by the oracle, evaluation and analyses.
   Three separate metrics per arm: D_I (a contract-valid input on which PUT != reference), D_IO (D_I with the correct
   expected value under the oracle), and precision of bug reports (assertions failing on the PUT that are correct /
   all assertions failing on the PUT); false alarms over the same denominator for every arm.
Arms on held-out: concept-hybrid (final hint selection: v7 rule unless v7_mutref's registered odd-task comparison favours
the mutref rule), plain-hybrid, placebo-hybrid (matched), concept (round 1 only), toolinput, plain, and baselines
CoverUp, MuTAP, SymPrompt, ACH (filter: inputs where PUT and mutant differ; paper filter secondary), TrickCatcher-full
(fixed adapter), EvalAndMitigate onlydoc/advdoc. Same model, endpoint, K = 3, ref/full oracle (10 spec-only programs).
Primary: concept-hybrid vs plain-hybrid and vs each baseline, D_IO under ref, per-question sign test (VibePass) /
per-task (MBPP+). Secondary: D_I, precision, matched-count subsets, placebo.
