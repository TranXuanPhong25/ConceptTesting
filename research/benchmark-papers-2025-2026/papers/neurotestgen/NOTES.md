# NEUROTESTGEN: Neuro-Symbolic Guided Test Generation with Large Language Models

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [NEUROTESTGEN: Neuro-Symbolic Guided Test Generation with Large Language Models](https://arxiv.org/abs/2609.30178)

Year/venue: 2026 arXiv

Dataset: Defects4J; 2,971 methods / 130 classes / 14 projects

Input setting: CFG + numerical Z3 constraints or LLM object-path solving

Model: Llama 3.3 70B, GPT-4o-mini, Claude 3.5 Haiku, Claude Sonnet 4.6

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Symbolic guidance specification sát ý tưởng behavioral IR + constraints.

Limitation: No source verified; paper skips loop bodies in symbolic phase. Coverage claim không tự chứng minh bug detection hay completeness.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:38:12.032610+07:00

Publicimplementationverified;keepascloseneuro-symboliccoveragepriorwork,conditionalbaseonlyafterbatchflags/solversemantics/modelconfig reconciliation. Do notsilentlyreimplement.

Blockers: Authorrootlink401not_connectedbutdirectfilepaths200;do notinferwholeartifactunavailablefromrootfailure; Currentdocumentedbatchrunner writes enable_symbolic_execution=false,enable_LLM_path_solving=false,enable_LLM_verify=false;READMEexplicitlyacknowledges this. Runningdocumentedcommanddoesnotenablepaperfullmethod; LightweighttranslatorisnotfullJavasymbolicexecution:skiploops/methodbodies,unsupportedexpressionsignored,float/doubleasRealsratherthanIEEE754; LLMverifierisaheuristicmodelpass,notindependentexecutionproof;80.96%pathsobjectrelated; NumericalSAT/UNSATonlyappliestopartialencoding,notsoundfullJavafeasibility; No immutable source revision/licenseverified;baselineprovenance saysoriginalPANTAresultsbut tablevaluesdifferfromauditedPANTAv2; No mutation/historicalbugdetectionmeasure;mainmetricscoverage/passrate/cost; Noauthorsourceexecutedormodelcallmade

Sources: https://arxiv.org/html/2609.30178v1, https://anonymous.4open.science/r/Symbolic_Execution_Based_Test_Generation-F4F3/README.md, https://anonymous.4open.science/r/Symbolic_Execution_Based_Test_Generation-F4F3/SYMBOLIC_EXECUTION.md, https://anonymous.4open.science/r/Symbolic_Execution_Based_Test_Generation-F4F3/evaluation/README.md, https://anonymous.4open.science/r/Symbolic_Execution_Based_Test_Generation-F4F3/evaluation/execute_classes_with_high_complexity.py
