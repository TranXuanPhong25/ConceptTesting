# SWT-Bench fit for grounded concepts and conditional MRs

Reviewed 2026-10-14. Proposal only; no dataset/model/container benchmark run started.

Primary sources:
- [Paper: SWT-Bench, NeurIPS 2024](https://arxiv.org/abs/2406.12952)
- [Author repository and harness](https://github.com/logic-star-ai/swt-bench)

Source facts: SWT-Bench asks for tests reproducing a GitHub issue, failing on the original
repository and passing after the resolving patch. The author harness supports unit-test
patches and standalone reproduction scripts, uses Docker, and reports applicability,
success and coverage metrics. The repository supplies Lite/Verified evaluation instructions.
It recommends 120 GB free storage, 16 GB RAM and 8 CPU cores for fast evaluation.

Our proposed adaptation:
1. Map issue statements/documentation to candidate obligations, retrieve relevant public
   code/tests, and construct concept/dependency evidence over that same retrieved context.
2. Compare plain, flat concepts, graph concepts and conditional MR guidance using identical
   retrieval, localization, tool access and generation/execution budgets. Include witness
   controls where the adapter can produce executable witnesses.
3. Generate test patches or reproduction scripts. Use bug/fix pairs only in a separate
   evaluator: require a meaningful failure on buggy code and success on the fixed version;
   record infrastructure errors, flaky behavior and existing-test regressions separately.
4. Use issue-reproduction success as primary outcome. Track applicability, false alarms,
   cost and coverage as secondary. Accepted MR cards are not automatically valid oracles.
5. Begin with a preregistered pilot from one or two Python repositories, selected before
   model outputs by environment and deterministic bug-fix eligibility. Freeze separate
   development/evaluation IDs before iteration. This is an exploratory subset, not a full
   public leaderboard result.

Porting work: repository/environment lifecycle, imports/fixtures/object construction,
stateful calls and possibly cross-function traces; current positional-tuple strategies
and short function-level ref programs do not cover this interface. Keep the gold fix,
gold tests and evaluator metadata out of proposal/generation/retrieval. Hold localization
constant for the concept ablation; separately measure end-to-end retrieval if desired.

Engineering observation (local, 2026-10-14): Docker daemon responds, 16 logical CPUs and
149 GiB disk free. This supports investigating a small pilot, not proof that all instance
images build or all repositories fit available disk/RAM. Qwen's current 16k context needs
a smaller frozen retrieval budget than the released 27k-context prompts.

Assessment: grounded obligation graphs are a plausible fit for issue-to-execution paths.
Conditional MRs fit API-specific behaviors but require applicability checks. Both are
research hypotheses; benchmark suitability does not establish a concept advantage.
