---
name: vr10-retrieval-diagnostic
description: V7 dense diagnostic NO_GO;12tasks/28sourcequeries,117blindedbindings,0incremental supported dense wins
metadata:
  type: project
---

2026-10-29 user authorizes agents to complete vr9 and assess V7 retrieval quality.
Own diagnostic in [report](../python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/REPORT.md),
prospective PREREG/freeze/review, unchangedV6+V7A-D,12deterministic developmenttasks,
12independent canonical queries,4oldengineeringfixtures. Runtime receives source
only; gold joins after seal.48newlocalJinatextvectors/1092cachehits/24token-truncated
encode occurrences (not unique queries); no Qwen/paid/target execution in vr10.

Allarms8/8knownlabelsitehits;4tasksunlabelled. TwoCodexagents method-blind grade117
of132unionbindings coveringallincrementaldensetop3queryunions+controls. BothB-A
andD-C recover0new supported buggybindings/0mechanisms: registeredNO_GO. Many
newproposals contradicted by source; runtime unknown status means this is proposal
quality, not detectorFP. Oldfixtures cannot supply GO, revisedprose not separately
graded. Review is source reasoning, not independent human annotation/formalproof.

**Why:** independent dense/openpool increased proposals but not useful mechanism
bindings under current restricted lexical binder. V6 and V7 sources unchanged.
**How to apply:** keep defaultV2; no V7→vr9 promotion, largerbenchmark, modelshopping
or after-outcome retuning. Preserve rawpredictions/reviewgrades/unknown labels.
Vr9's separately completed retention repair also gives noefficacygain. Do not
propose the same dense/currentbase+samebinder package as untried; identify a new
mechanism before newcalls. Allactualoutcomes/rawpaths are in the linked report.
