# EvoOtter: Evolutionary Reproduction Test Generator

Reviewed: 2026-10-15. Full 9,024-word arXiv v1 read; public-source and exact reproduction check complete.

Paper: [arXiv:2607.02854](https://arxiv.org/abs/2607.02854). Full text: `public_evidence/paper_fulltext.txt`.

**Fit:** High as SWT-Bench/BRT method prior. EvoOtter makes fail-to-pass bug reproduction tests using heterogeneous prompting, localization, rule-based mutants, mutant-informed selection, and batched crossover. It reports 77.8% on SWT-Bench-Verified, but its main controlled evaluations are TDD-Bench-Verified and SWE-Rebench. No Defects4J or BugsInPy experiment and no root-cause labels.

**Public source:** No author implementation, evaluator, pinned code, data manifest, or result cache was located. Exact-title/author searches found no attributable repository. Martin Hirzel's official publication page lists the paper but has no EvoOtter code link. Prompts are mentioned as supplementary material; these alone do not enable a faithful rerun.

**Reproduction:** Not feasible from the located public artifacts. Exact reported models are Claude-Sonnet-4.5 and Claude-Opus-4.7; no immutable snapshots or weights are bundled. A custom-model study requires implementing/adapting the method and is not an exact reproduction. No code, API, or model was run.

**Recommendation:** Keep as a high-priority conceptual comparator for reproduction-test selection and execution feedback. It does not explain root causes. Prefer #74 for an immediately inspectable Defects4J buggy/fixed analysis base because that paper provides public MIT source, processed data, and notebooks.

See [`audit/reviews/076.json`](../../../audit/reviews/076.json) for the detailed evidence and verdict.
