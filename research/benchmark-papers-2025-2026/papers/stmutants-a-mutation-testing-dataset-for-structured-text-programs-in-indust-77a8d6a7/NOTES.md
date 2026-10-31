# STMutants: A Mutation Testing Dataset for Structured Text Programs in Industrial Automation

Reviewed 2026-10-15. Full text read: 6,770 words. Public dataset checked; author experiment source not found. Exact reproduction: not feasible.

This is an IEC 61131-3 Structured Text mutation dataset for PLC programs, not Defects4J/BugsInPy/SWT-Bench. The paper cites Defects4J in related work only. It reports 108 retained mutants over 11 programs and LLM-generated test suites evaluated via MATIEC. Hosted model scores: GPT-5.2 86.1%, Gemini 2.5 94.4%, Claude Sonnet 4.5 86.1%.

Figshare record https://doi.org/10.6084/m9.figshare.31724761.v3 is public, CC BY 4.0, and lists the three paper authors. `Mutations.zip` is only 213 KB and contains 110 ST mutant text files. There is no author experiment runner, test harness, original test data or machine-readable complete prompt artifact. Upstream MATIEC is a dependency, not author source. Exact replication would require recreating missing experiment workflow and paying for hosted model calls, so do not select it as a primary paper.

The dataset could be a future adjacent benchmark if the project expands to PLC/Structured Text and stateful multi-cycle behavior. This is not relevant to the current Java/Python issue-reproduction or root-cause goal. Full text SHA-256 `5db7be8c8755df616b20ab78018c794cb32c6e14c5b03bfd0992d87101ab272c`; artifact SHA-256 `c0355e78ff4e17b00cb63425b399fd441d0179e24628ad7678789934ad118da7`. No code/model calls or execution.
