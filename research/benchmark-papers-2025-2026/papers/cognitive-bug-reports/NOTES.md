# Test Case Generation from Bug Reports via Large Language Models: A Cognitive Layered Evaluation Framework

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Test Case Generation from Bug Reports via Large Language Models: A Cognitive Layered Evaluation Framework](https://arxiv.org/abs/2510.05365)

Year/venue: 2025 arXiv

Dataset: Defects4J + GHRB + transformed variants

Input setting: bug reports + few-shot examples

Model: StarCoder, GPT-4o

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Identifier/semantic transformations dùng để đo generalization vượt memorization.

Limitation: Builds on LIBRO; riêng modified dataset/source chưa verified. Original LIBRO paper 2023 không tính là new 2025 paper.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:28:53.528268+07:00

Supportingevaluationmethodologypaper,notimmediatebase:fourtestedlayers,nopublicstudysource;usecausal/contaminationclaimscautiously.

Blockers: Nooriginalstudyimplementation,mutateddatasetsorannotationreleasefound; Evaluatecasestudysection4.5isemptyinbothofficialPDFandHTML;Createlayerexplicitlyfuturework:sixlayersproposed,butonlyfourhaveexperimentalresults; IdentifiersaffectlegitimateAPIsemanticcuesandrenamingpipeline;performancedropaloneisnotcausalproof ofmemorization; Open-bookretrievessamedatasetnear-identicalexamples;notunseenretrievalgeneralization; RandomForestfeatureimportancecorrelatescomponentpresencewithsuccess,notcausalcontributionofremovingthatcomponent; Sparseorambiguousreports(47),sharedissuegroups(66bugs/29groups)couldcorrelateexamples;exactsplit/dedupcontrolunverified; TOSEM-styletemplatehasplaceholderpublicationdetails;only2025arXivpreprintverified; Noauthormodel/evaluatorrun

Sources: https://arxiv.org/html/2510.05365v1, https://arxiv.org/pdf/2510.05365v1
