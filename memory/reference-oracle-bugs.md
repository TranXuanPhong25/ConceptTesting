---
name: reference-oracle-bugs
description: Original HumanEval references97/140 cause both unique plain/BVA false alarms;HumanEval+ corrected references agree with PUTs
metadata:
  type: project
---

2026-11-05 user asks to inspect unique all44detections97plain-only/140BVA-only.
Both are false alarms from original HumanEval canonical solutions,not PUTbugs.
multiply(-1,2):original18,PUT2,HumanEval+2. fix_spaces(two spaces):originalone
underscore,PUTtwo,HumanEval+two. Four native diagnostic reference checks (2each)
agree with PUT;no model calls/hidden inputs. Frozen benchmark artifacts unchanged.

Task140plain also proposed two-spaces case,but all20raw args are string literals
without singletontuplecomma and were rejected. BVA binds whole-string length to
a consecutive-space-count quote;only all-space strings make these coincide.
This is not a demonstrated semantic concept win. Shared task44/122not audited.

**Why:** current final pipeline uses original HumanEval reference source plus
EvalPlus contracts/atol;contracts do not include canonical corrections.
**How to apply:** do not report raw3vs3 as confirmed bug counts. Read
final/review/boundary_unique_task_audit_2026-11-05.md and JSON before interpreting
these results or switching the oracle. No pipeline/oracle changes yet authorized
or made in this diagnostic task.

2026-11-05 subsequent user explicitly authorized corrected HumanEval+ references
and rescoring all44saved input batches. Implemented pinnedreference-onlyv0.1.10
provider(default for modern pipeline)and FrozenInputsGenerator/rescore CLI with
no model backend. All164signature/spec/domain bindings checked;only115mathimport
relocation. Legacy/synthetic fixtures explicitly opt into original task references.

Corrected44rescore COMPLETE:plain595validinputs/0detected,BVA121/0. Alloriginal
generationfreeze and1336artifactfiles unchanged;0newmodelcalls,1412cachehits/
1766nativeexecutions,118source/datahashes verified. Fullread-only replay matches.
122engineeringchecks pass. Old raw3vs3all disappear under corrected references;
do not report them as confirmed PUTbugs. Output:
final/out/boundary_all_plain_bva_evalplus_v0110_20261105.
Report:final/review/boundary_evalplus_rescore_2026-11-05.md.

User next asks for BVA improvement proposal. Saved-data audit and proposal only,
no BVA algorithm change/new generation:final/review/boundary_improvement_plan_
2026-11-05.md and boundary_mechanism_audit_2026-11-05.json.26constructioncalls,
473rawrecords→121retained;272targetmisses,41format,21side,18duplicate.49accepted
schema cards=41domainbounds/8behavior;not49semanticallyverified concepts. Binding
errors140/138/21and missed supported thresholds30/52/146ground the recommendations.

User subsequently requested implementing the BVA repairs. Done in existing code:
compiled targets/shared argument encoder/typed binding and explicit statuses;
165combinedchecks pass,no new model benchmark. Correctedreference remains default;
old44rescore0vs0is still the last live result. See [[boundary-test-applicability]].
