# Call-Chain-Aware LLM-Based Test Generation for Java Projects

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Call-Chain-Aware LLM-Based Test Generation for Java Projects](https://arxiv.org/abs/2604.22046)

Year/venue: 2026 arXiv

Dataset: Defects4J + four post-cutoff Java projects

Input setting: caller/callee/constructor/dependency contexts

Model: Qwen3-Coder-30B (paper label)

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Interprocedural concepts và constructor/protocol constraints.

Limitation: Dataset/model verified; no usable author source verified. Main metrics coverage, không chứng minh root-cause classification.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:35:19.646653+07:00

Promote local-open-model supportingbase fordependency/contextconcepts;conditionalconfigreconciliation andlargecompute. Keepcorebuggy-input selectionseparate.

Blockers: Noauthorcode/modelrun; CurrentMAX_TOKENS_NUM100000 propagatesgeneration/repairdefaults vs16384paper;actualpaperconfigreconciliation needed; Evaluationrunner writes no_coverage_increase_iterations10 vspaper/config3; Modelwrapperhardcoded endpoint/header must be configured safely;cachecredentialliteral redacted,originalunchanged; FullD4Jgeneration353.8hours/154.9Mtokens plus8.35hstaticanalysis;newsubjects321.3hplus61.63hstatic; OnlyonerunperLLMapproach/class;cannotassumevariancecontrolled; CHA paths areoverapproximated;2.41%spurious reported,no solverfeasibility guarantee; Postcutoff/unseenclaims notindependentlyverified;repositoryreleasedate/modelreleasedate not a proof ofno pretrainedoverlap; Fixed-code regression/mutation setting;notunknownhistoricalbugdiscovery

Sources: https://arxiv.org/html/2604.22046v2, https://github.com/Amocy-Wang/CAT/tree/9da2e360b14c623067555acf806f98b297b0fbdd
