# LLM-based Low-Level Integration Test Generation for Java

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [LLM-based Low-Level Integration Test Generation for Java](https://arxiv.org/abs/2605.26851)

Year/venue: 2026 arXiv

Dataset: Defects4J + Deps4J

Input setting: real in-project dependencies; ClassIndex/typestate constraints

Model: Exact backbone/config not verified in this scan

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Markov typestate/protocol constraints gần state-transition concepts.

Limitation: Code/model artifacts pending. Low-level integration tests và mutation metric khác function-level bug detection.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:27:18.035847+07:00

Importantstate/protocolconceptpriorwork;notimmediatereproductionbasewithoutsource. KeepseparatefromDefects4Jbuggy-inputtests;originalpublicmodelcanbeusedonlyafterauthorizedmethodaccess/adaptation.

Blockers: Authorimplementation,Deps4Jcompletecommits/CUTmanifestandgroundtruthoutputsnotfound; Currentpublicmodelidentityisavailablebutbaseweightsalonearenot originalmethodcode; Typestatemodelislast-methodtransitionabstraction/softfilter,notformalprotocolspec;paperacknowledgesimplementationdefectcanbeblockedasinvalidsequence; Generationusesfixedreferencewithrepairtopassingtests;nohistoricalbugdetectionevaluation,onlycoverage/mutation/DepLC; No repeatedLLMruns;pooledCUTstatisticsdonotreplacewithinCUTrunvariance; Statedpathbudgettop2pathsfromeach2methods plus2explorationpathsversusK4isambiguous;earlierstop2vslaterpatience4requiresconfigreconciliation; Deps4Jprojectcreation/trainingcutoffclaimsnotindependentlyverified; Noauthorcode/modelrun;reimplementationnotauthorized

Sources: https://arxiv.org/html/2605.26851v2, https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
