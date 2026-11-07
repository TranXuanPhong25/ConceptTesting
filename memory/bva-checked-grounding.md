---
name: bva-checked-grounding
description: v5 restored/pushed13d92ee9; opt-in checked grounding implemented/reviewed,278tests/offline audit; live6 awaiting endpoint404
metadata:
  type: project
---

2026-11-06 user requests restoring v5, commit/push, then try proposed semantic
grounding repairs. Stable v5 restored byte-exact,234tests pass, commit13d92ee9
pushed main before experimental edits. Compact prompt archived; unrelated files
from other sessions were not staged.

Opt-in checked trial implemented/reviewed;278modular tests pass incl44newgrounding
cases. Default off templates/messages match savedv5on10tasks. Scope/limits and
offline results:final/review/boundary_grounding_offline_2026-11-06.{md,json}.
No paper reimplementation. Experimental source changes remain uncommitted for
review after stable checkpoint, not included in the v5push.

Live same6miss diagnostic authorized/preregistered,max12logical calls,exact
qwen3.5-27b-awq,plannedoutputfinal/out/boundary_checked6_20261106. Not launched:
private/tmpconfig missing, restored from prior user-supplied endpoint; modelsGET404,
0task completions. User asked asynchronously for replacement. Continue readiness/
freeze/run only with a working endpoint; do not substitute models or duplicate.
No active diagnostic process. See PREREG latest entry and reviewer amendment.

2026-11-06 endpoint reply supersedes waiting: live metadata/tokenizer6pass,
prompts2273–3463tokens; userprovided exactQwen27/8192. Detached runnerPID34215
launched in plannedchecked6output,max12logical calls. Inspect status.json and
runner.pid before any action; do not duplicate.79source/data+723prior-output
hashes frozen; exact source evidence copied locally before launch. No results
yet; stablev5commit unchanged, checked code remains uncommitted.

Terminal supersedes running:checked6COMPLETE6/6,8responses/0unknown,23valid,
bugtask16(15stablefailinputs),26,573tokens. Semantic reason improves72prefix-vs-total
but5generatedcontexts violateprefixproperty;23recognizesbyte/characterbutmissing
boundariesfield;157match/domain_lowerbutforbiddenatside. Report:
final/review/boundary_checked_grounding_2026-11-06.md. Full replay matches,
79source/data+723prior-output hashes and6freezes verified. No activecontroller,
automaticretuning/expansion or defaultpromotion. Trial staysuncommitted;v5pushdone.

2026-11-06 user asks exactgpt-5.6-lunato see failures and output inputs immediately,
no tools. Independent review clears one bundled native CLI/low call for23/72/157;
publicspec/PUT+failedcontext feedback only, no gold outputs/witnesses. Output
final/out/boundary_luna_direct3_20261106,runnerPID40666;inspectstatusbeforeaction.
Host/features disabled;schemasmayremainexposed, event/routeraudit must show0tool
attempts before accepting response. No retry/model substitution. Freeze all3
returnedbatches before sharedreference/nativeevaluation. Assistedpost-hocdiagnostic,
not matchedmodelcomparison. Unrelatedmethodgenerator edits preserved.

Luna direct3 terminal COMPLETE,supersedingrunning:1nativeCLIcall/0unknown,
0observedtool/deniedrouterattempts,3validinputs/3bugtasks23/72/157. Rawoutput
23é;72[10,-20,10],w5;157(1,1,1.41421356237). Stable2native repeats/fullreplayPASS;
83source/data+273priorcheckedfilesunchanged.8,108input/345outputtokens.
Requestedexactmodelgpt-5.6-luna/low;serverIDnotreportedin events. Report:
final/review/boundary_luna_direct3_2026-11-06.md. Feedback/directschema/model all
differ fromQwen,notmatchedcomparison. Noactivejob/retry/expansion/defaultchange.
Also found checked72b2partialselectionreject:boundary_kind=edge;failure retained
inselectioncheckpoint but not aggregated with generation rejections. Analysis only.

**Why:** v5/compact trials retain false quantity/scope/polarity claims; typed
receipts can diagnose supported errors without treating model prose as proof.
**How to apply:** retain unknown for unsupported source patterns, avoid hard-gating
all inputs on semantic verdicts, and report pool/guidance confounds. Existing
reference-after-freeze protocol remains unchanged.
