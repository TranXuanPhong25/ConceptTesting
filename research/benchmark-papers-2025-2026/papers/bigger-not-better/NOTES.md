# Bigger Is Not Always Better: Performance and Sustainability Trade-Offs in LLMs for Python Bug-Fixing Tasks

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Bigger Is Not Always Better: Performance and Sustainability Trade-Offs in LLMs for Python Bug-Fixing Tasks](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.34)

Year/venue: 2026 ESEM

Dataset: BugsInPy; 40 bugs

Input setting: buggy Python code

Model: Six open code LLMs, 1.5B–15B; exact list/config audit pending

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Model-cost control và small-model feasibility.

Limitation: Repair/energy task; không trực tiếp test generator. Source/checkpoints chưa verified từ publisher landing page.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:24:50.020166+07:00

SupportingAPR/compute-costpaper,notcoreconcept-guidedtestgenerationbase. SmalloriginalmodelsandpublicCSVareuseful,butresolveartifact/paperandenergymeasurementdiscrepanciesfirst.

Blockers: Noauthorevaluator/modelrun; Currentrun_experiment.pystripsMarkdown/dedents/extractsASTblockcontrarytopaperpolicyofnotcleaningoutputs; CurrentGPUenergysubtracts5secondidleENERGYfromgenerationENERGYwithoutrescalingbaselinebygenerationduration;notduration-normalizedidlepowercorrection; do_sample=Falsemakes10repeatsdeterministicconditionalonhardware;nosamplingdiversityclaim; Publicmanifest40IDsnotmatching9projectresults;balanced35bug/2100runselectionneedsreconstructionfromCSV/notebook; CurrentCSV2401rowswith7modelsandmissing/duplicatebug-modelruns;cannotassumepaperbalancedtablefromallrows; Nopinneddependencyenvironmentorprojectlicense;largelegacyBugsInPydependencysetup; Passingsuppliedtestmeansplausiblepatch,notsemanticcorrectness;localizedblockscopeexcludesrepositoryrepair

Sources: https://doi.org/10.4230/LIPIcs.ESEM.2026.34, https://github.com/syedfakhar25/empirical-llm-bugfix-benchmark/tree/e3cc68f625c69eacd334437f1c9c1343aae6b348, https://github.com/esem2026-ai-study/empirical-llm-bugfix-study, https://doi.org/10.4230/artifacts.28073
