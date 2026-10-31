# LLMutantKiller: Using Large Language Models to Generate Tests that Kill Mutants

Reviewed 2026-10-15. Full author-hosted final paper read: 23 pages, 15,171 extracted words. Public source + complete replication package verified. Reproduction: artifact inspection/smoke feasible; full live run conditional and heavy.

## Method and results

For each surviving StrykerJS mutant, the tool sees original and mutated source fragments, generates a Jest test, checks it passes on original and fails on mutant, then gives categorized execution feedback for up to 10 attempts. It rejects dependency violations and source introspection/cheating. Across 915 sampled survivors in 13 JS/TS repositories, authors manually classify 815 as behavioral and 100 equivalent. Claude Sonnet 4.6 produces valid killing tests for 777/815 behavior-changing mutants (95.3%); Devstral 2512 509/815 (62.4%); Llama 3.3 70B 216/815 (26.5%). Two prompt variants (with/without existing tests) complement each other, union 798/815 (97.9%). This is very close to behavioral oracle generation but targets synthetic mutants, not real issue reports or historical bugs.

## Artifact and reproduction

Official [artifact repo](https://github.com/neu-se/LLMutantKiller___Artifact) is at API-observed main commit `ec7b46370e63035ae3229bf7a89e3737c005ab9a`. It contains MIT software, TypeScript implementation, complete prompts/mutations, Docker, 553 MB `paper_results` from the visible API tree, manual equivalence/validity labels, TestPilot baseline and claim-by-claim reproduction docs. Documentation is CC BY 4.0; included project source retains upstream licenses. The linked [author paper PDF](https://www.franktip.org/pubs/issta2026.pdf) is 23 pages; final DOI 10.1145/3832098 is verified from the author's artifact and ISSTA listing.

A 13-mutant, one-attempt smoke run takes ~17 minutes in Docker and historically costs <$1 with Devstral; CLI smoke test itself takes ~5 seconds. Full 915-mutant configurations are much larger: authors estimate 456.6 native hours or ~108 Docker days sequentially and ~$1,313 for all 12 runs at historical prices; artifact storage is ~1.7 GB compressed / 9 GB expanded, 20 GB free disk. Stored outputs are accessible without API calls. The source supports a configurable chat-completions endpoint plus auth headers, so custom local Qwen inference may work if the endpoint is compatible; this has not been tested. No code/model/API run performed.

## Fit and caveats

Best recent fully reproducible method candidate for test generation that verifies expected-vs-mutated behavior and audits false-positive “tests.” Pair with #52 for Defects4J real bugs and #55 for repository issue reproducer quality. This paper itself is JS/TS mutation testing, not Defects4J/BugsInPy/SWT-Bench or causal root-cause classification. Full text SHA-256 `e43ee7976b4851e8cbb89bd0155c4e1a70bc322fa94eebb659270c54b8e95ba6`; PDF SHA-256 `b63dd28ea79d3b7dd91dca008bd942535e255e77c5bd8d45f9b2ee2856a5ec13`.
