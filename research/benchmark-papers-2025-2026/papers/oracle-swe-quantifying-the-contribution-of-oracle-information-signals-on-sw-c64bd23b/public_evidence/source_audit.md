# Public source audit — #111 ORACLE-SWE

Checked 2026-10-15 after reading full arXiv v2 text. No code was run.

The paper's source is [arXiv:2604.07789v2](https://arxiv.org/html/2604.07789v2), with CC BY 4.0 paper license. The text contains no Data Availability/code release statement, GitHub link, artifact DOI or author source reference. Exact-title / arXiv-ID searches for an author repository did not find an Oracle-SWE artifact. SWE-agent is named as the open-source base agent; it is third-party baseline software and does not provide this paper's extraction scripts, signal data, evaluation modifications or results.

Paper appendices do include example extraction prompts for edit location, context, API use and F2P/P2P tests. This aids conceptual understanding, but is not a runnable implementation or result cache. The paper describes rule-based oracle extraction and manually verified correctness, plus a two-stage model-extracted signal study; neither extraction outputs nor scripts were found publicly.

**Verdict: `not_found` / exact reproduction not feasible from verified public source.** The paper's core experimental extraction/injection flow would need to be independently implemented, which this audit does not authorize. Hosted models (GPT-5, GPT-4o, Claude-4.5/4.6 Sonnet) are used, with no immutable snapshots; local Qwen would be a new evaluation and requires implementing the missing method. Benchmarks are SWE-bench Verified/Live/Pro, not Defects4J, BugsInPy or SWT-Bench.

Search references:

- [arXiv full paper](https://arxiv.org/html/2604.07789v2)
- [Exact title search results](https://www.google.com/search?q=%22ORACLE-SWE%3A+Quantifying+the+Contribution+of+Oracle+Information+Signals+on+SWE+Agents%22+github)
- [arXiv ID search results](https://www.google.com/search?q=%222604.07789%22+github)
