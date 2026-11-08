---
name: bva-batch-comparison
description: Matched batch evaluation-only resume ACTIVE158735;314 responses frozen,60 checkpoints reused,C-call hard timeout repaired;0new model calls
metadata:
  type: project
---

LATEST2026-11-08 full matched batch evaluation COMPLETE:Direct68/2926valid/21tasks,
Soft73/2851valid/23tasks;shared52,Direct-only16,Soft-only21,netSoft+5PUTs.
Stable wrong-value46vs59.1454same targets,all164taskrecords,immutable replay/hash
checksPASS;0newmodelcalls. Output140053/Prefect5319cd2eCompleted,worker158735exited.

Read-only82oldnaivevs68newDirectdiff:final/review/naive_old_vs_direct_batch_diff_
2026-11-08.md;Prefectartifactd01ee2e8-497a-4e9e-a97a-c6642e06244d,
key naive-old-vs-direct-new-diff.
153/157tasks same visiblePUTIDs/order;all156shared requests same spec/contract/
base;1437sharedPUTcode stringsidentical. Onlyvisibilitychanges144(8→9),147(3→10),
150(2→10),160(skip→1),all0detectionsbothruns. SYSTEMidentical,no conceptcards in
156oldplainrequests. Mainchangesexactly20→upto20/instructions,namedJSONvsPython
literalstrings,posthocwrappingrepairvsCallBuilder,freshresponses. Full2repeat
andconfirm-first-failures have SAME detection predicate;different unstable/cost.
CorrectedreferenceSHAandcomparatorASTidentical.82vs68shared52/old-only30/new16.
Task151Direct907tokens/stopcontainsPythonTrueFalseinsideJSON→invalid_response,
0valid/0detection;old18valid/10detections. Task23oldUnicode16valid/1PUT,newASCII
20valid/0PUT. No newinputrepair/replay/modelrun;do not infer causality from totals.

2026-11-08 user yêu cầu chia commit và push khi flow sinh BVA chính không đổi.
Đã push main5commits:9823b7ca(audit),94f05ef3(batch),b8bb3ee4(Prefect),
7a5e0a1a(C-call timeout/evaluation resume),006e0bc1(agent rules).
Diff so6dcfbd48xác nhận BVA prompts/constructor/default/per-PUT budget path
không đổi.58offlinechecksPASS;fix fixture port test để không launch service.
Research/slides/memory/endpoint-script edits còn ngoài commit theo scope.

LATEST2026-11-08 user yêu cầu sửa và chạy phép so full matched batch.
Generation đã hoàn tất314responses(157/arm),315attempts/1historicalunknown,
785916known tokens. Worker28517sau đó dừng ở60/164evaluationtasks do task60PUT7
reduce(operator.add,range(1,n+1),0) với n2147483647 không dispatch SIGALRM.
Đây là execution failure,không phải thiếu response hay endpoint.

Evaluation-only continuation ACTIVE PID158735 tại
final/out/bva_batch_matched164_evaluation_20261108_140053.
Giữ314response bytes,164frozen batches,60task native checkpoints;0newmodel/
tokenizercalls. Runtime copy chỉ sửa execution.py/worker.py:active-user-call marker
cho phép single-input outer wall timeout trả timeout khi C call bị kẹt;startup
hang không có marker vẫn là infrastructure error. Không đổi timeout3s,outer10+
timeout,seeds,oracle,comparator hay confirm-first-failures scorer. Dùng native lock
cũ;guard/checkpoint receipts/hash freeze và immutable replay bắt buộc.
49regressiontestsPASS,157cached decode tasks/314responses unchanged PASS;
nativeNumPy pass/fail smokesPASS. Chưa có full result;không dùng partial counts.
Đã vượt chỗ lỗi thật:task60hoàn tất,61/164evaluated;PUT7/8hard-timeout được ghi
riêng ở firstpass và confirmation,worker tiếp tục task61. Không còn abort tại
C-call cũ. Run vẫn active;Prefect importer tự cập nhật khi full/replay hoàn tất.
Prefect Running flow5319cd2e-fdd0-4296-ad51-7a6b93579fc1,report tiếng Việt.
Controller final/src/audits/resume_bva_batch_evaluation.py;giữ toàn bộ parent
output/status và các suppression của stopped historical rows. Các ACTIVE/stopped
notices bên dưới là lịch sử. Không duplicate launch hoặc chỉnh frozen runtime.

OLDER2026-11-08 continuation ACTIVE,supersedes stopped notices below.
User supplies endpoint and explicitly requests batch continuation. Local private
configuration pointed elsewhere;corrected outside repo. ExactQwen27/context8192
and tokenizer13verified. No URL/secret stored here.
New output:final/out/bva_batch_matched164_resume_20261108_104541,workerPID28517.
Actual progress228received(114perarm),2freshresponses observed,now task116/direct
running.226receivedresponses imported unchanged,88logicalresponses remained at
launch/86now. Original226response bytes
captured in recovery receipts;request/attempt identities and parent snapshot pass.
Original interrupted output preserved byte-for-byte.1archived115soft unknown
attempt1retained;recovery continues atattempt2/max3,not a fresh retry budget.

Controller final/src/audits/resume_bva_batch.py uses the copied original frozen
runtime/generate/evaluate/paired_verdicts and original314request_plan. No packet
repreparation/visibility changes,prompt/schema/quota/sampling/scorer changes or
received-response regeneration. All120savedbatches re-decoded with cached calls
under actual frozen runtime,0model/nativecalls in that smoke. Independent
batch_resume_review PASS,428testsPASS(including6recoverychecks),sourcehash guards,
native lock,full input freeze/immutable replay required. Cumulative imported costs
counted once,new costs separate. REPORT.md/result_digest.json automatic in new
output. Do not duplicate/relaunch worker/reset old markers or modify frozen files.

LATEST2026-11-08 status supersedes ACTIVE/SCHEDULED notices below. All three
workers410483/415105/415461have exited. Step1packaging audit COMPLETE:naive44→82
detectedPUTs,16→29tasks,1536→2758novelvalidinputs.0old detections lost. ALL30
original BVA-onlyrecovered;BVA61is a subset of repaired naive82,naive-only21.
Stable wrong-value witnesses repairednaive53vsBVA46. Same1454targets/full2repeat
scorer,source/input hashes and immutable replayPASS,0newmodelcalls in thisaudit.
Report final/review/naive_packaging_audit_2026-11-08.{md,json}. This removes the
old raw BVA advantage after packaging repair;new matched batch remains incomplete.

Step2batch started scheduled endpoint check exactly19:17:40UTC(expectedQwen27,
ctx8192),then stopped at1794087448.384UTC on tokenizerHTTP404 before the next
completion.226received responses(113direct/113soft),314planned,88logicalslots
without response.120savedtaskbatches include113completed eligible pairs+7cohort
skips;do not report120eligible tasks generated.1archived unknown completion
attempt at115/soft_bva/OpenAIConnectionError remains,227total attempt records.
Known writer usage545796tokens(416341prompt+129455completion),6keepalive records
separate. Request/visibility plan exists;no global generation freeze or native
evaluation. Current GET/models again404,0newcompletions during statuscheck.
Async request pending for user to revive configured endpoint/send replacement.
Do not restart one-shot worker/reset markers or regenerate226receivedresponses.
Any continuation must preserve frozen runtime/requests,allcachedcalls/unknown
transport history and remaining per-request attempt limits in a fresh output.

2026-11-08 user asks why10case soft7/direct6 did not transfer to full. Concrete
trace:the ONLY soft-only win was72PUT4with20inputs,including([-1,-2,-1],-4).
Full run gives that SAMEPUTonly2inputs:([1,2,1],4),([2,3,2],7),both positive;
all10PUTgenerations for72lack negative context and full BVA misses72 entirely.
Thus full run changes per-PUT value budget20→2–3,not merely task count10→164.
Its control also changes fresh matched single-PUT Direct→historical multi-PUT
naive(fixed packaging). Outcome-selected10andoneextraPUTdid not establish a
general advantage. Keep the positive diagnostic result scoped;do not claim a
matched full guidance verdict before the pending batch trial completes.

Full-settings audit requested2026-11-08 saved in
final/review/boundary_settings_10_vs_full_2026-11-08.{md,json}. Scanned1640received
requestrecords(30small+1454BVA+156naive),verified sampler/seed/caps. All10selected
Soft task packets/spec/code/basecontext exactly match corresponding fullPUTcalls;
only instructionquota changes20→2/3. Model/checkpoint/nativeworker/execution/
CallBuilder frozen hashes match. Actual selected16ID=4,not oldprosePUT0.
Full quota histogram:1280PUTs×2,164×3,2×4,4×5,2×10,2×20;total3140slots.
Quota is generation allocation,not inputs executed perPUT:pooled valid taskset
has min2/median9/mean9.2293/max20inputs,run on everyPUT of task.
Audit includes strict-vs-legacy-vs-newbatch decoder differences,all manifests/
exactprompts/unknownserverdefaults,costs/reuse and oldfull2repeat vsfreshconditional
scorer. No new model/native calls in settings audit;source/result artifacts unchanged.

User authorizes two steps2026-11-08,with new LLM calls40minutes after request.
Not-before timestamp2026-11-07T19:17:40Z(08Nov02:17:40Vietnam). This is an opt-in
diagnostic;main per-PUT soft BVA default unchanged,no commit requested.

Step1CPUevaluation ACTIVE PID410483 at
final/out/naive_packaging_audit_20261108_0200/evaluation.
Original sources/values preserved;packaging-repaired view has1250changed rawslots
on64tasks,at most20original slots/task. No outcome yet/no modelcalls. Static
signature/annotation/unconditional-contract proof only;no oracle-guided fixes,
no expression execution,truncation recovery or ambiguous bindings. Source raw
hashes authenticated against prior naive export. Full1454targets use original
frozen full2repeat runtime/scorer/3stimeout. Original44baseline and oldBVA61remain
unchanged. Reporter415461waits and writes packaging-specific old/repaired/BVA
partitions and how many of original30BVA-onlyare recovered. Expected report:
final/review/naive_packaging_audit_2026-11-08.{md,json}.

Step2SCHEDULED workerPID415105,not-before above,0newmodelcalls at lastcheck.
Output:final/out/bva_batch_matched164_20261108_021740.
Direct and SoftBVA each1call/task,same visible PUT batch/spec/base/contract,
schema/CallBuilder/parser,20inputs,2048outputtokens,8192context,temp.7,seed.
Only GUIDANCE differs. Joint tokenizer fitting before anycompletion;parity arm
order;all1454targets remain in evaluation even if visibility trims. Max314logical
writer calls;bounded transport attempts/unknowns/keepalive separately reported.
No network/tokenization/KeepAlive before deadline. Metadata-only waiting up to6h
afterdeadline for expected model/context;no substitution. Private endpoint config
outside repo is used,never recorded here. No duplicate launch/reset markers.

Runtime/data/review/test receipt frozen in output;readonly runtime isolatedfrom
live worktree. Same-current confirm-first-failures scorer for both fresh arms,
distinctfromStep1oldfull2repeat;do not treat historical/fresh totals as prompt-only.
Shared native flock serializes Step1/Step2CPUscoring;LLMgeneration starts by
schedule while CPUaudit may still run. All input batches freeze before scoring;
source/hash/immutable replay and exact shared/direct-only/soft-only reports/witnesses.

Independent reviewer batch_fairness_review finalPASS;422tests before CPUlaunch,
31targetedoffline after reporting/scheduler changes. Preregistration appended
before outcomes. No fresh semantic result yet;inspect status/PID/progress/logs
for both outputs before acting. Final batch report goes to its REPORT.md and
result_digest.json automatically. Scheduler/reporters are detached,not tool waits.

2026-11-08 old-only30 classification: 14 large-value timeout/RecursionError (new common prompt "small enough for execution budget; resource caps are not semantic boundaries" suppresses |x|>=1000: old179inputs/50tasks vs Direct57/20, Soft67/25), 10 task151 JSON bool reject, 6 content (non-ASCII1, whitespace2, palindrome/date3). Basic BVA values (empty/0/neg/±1) not reduced. Shared by Soft, so Direct-vs-Soft stays matched; no prompt ablation run.

2026-11-08 user chose option2: keep "resource caps" sentence, report resource separately. detection_kinds.py (read-only): old82=wv53/crash3/res26 (non-resource56); Direct68=46/3/19 (49); Soft73=59/1/13 (60). Old-vs-Direct net14 = resource+7 (14 vs 7) + interface+5 (task151 Direct JSON bool 10 vs task99 old missing singleton comma 5) + content+2 (6 vs 4). Report final/review/naive_old_vs_direct_batch_diff_2026-11-08.md; Prefect artifact 0e329855 on flow 5319cd2e.

2026-11-08 parser fix (user "sửa đi"): response_json.py strict JSON then ast.literal_eval fallback in InputGenerationMethod.run. Replay saved batch responses 0 calls: Direct recovers 22(19)/151(20); Soft recovers 22/52/57/125/162 (20 each); Soft99 truncated still rejected. Not rescored, not committed; rescore needs user-run evaluation (0 model calls).

2026-11-08 REPARSE COMPLETE (user "cứ chạy đi rồi up lên prefect"): final/out/bva_batch_matched164_reparse_20261108_192012,
script final/src/audits/reparse_bva_batch.py; saved responses re-parsed with literal fallback, 0 model calls, 158 task checkpoints
reused, 6 tasks rescored (22,52,57,125,151,162). Direct 78 (wv56/crash3/res19, nonresource59) vs Soft 73 (59/1/13, 60);
shared62, Direct-only16, Soft-only11. Only task151 adds detections (+10 Direct, shared with Soft); Soft's 5 recovered tasks add 0.
Conclusion: Soft BVA ≈ Direct excluding resource (60 vs 59). Prefect flow 7f4424a3-262d-48f1-8bee-d09fe3832598 (auto-indexed),
note artifact on source flow 5319cd2e.

2026-11-08 boundary share (boundary_share.py, heuristic natural_edge|reference_threshold, 0 calls): failing inputs boundary Direct 60% (46/77) vs base 68%; Soft 56% (46/82) vs base 71%; shared25 84%, Direct-only 48%, Soft-only 44%. PUT-level Direct 55/78, Soft 62/73 revealed by >=1 boundary input. Boundary not overrepresented among failures. Report final/review/boundary_share_direct_soft_2026-11-08.md.
Manual Haiku labels (3 parts, blind): failing boundary Direct 43/77=56%, Soft 53/82=65%; only Direct 48%, only Soft 61% (excl task43 47 vs 55%); PUTs via boundary input 56 vs 56. Flags boundary_manual in final/review/boundary_share_direct_soft_2026-11-08.json. User: no second-rater cross-check needed; Codex job stopped.

2026-11-08 NAIVE FORMAT REPAIR COMPLETE: final/out/naive_packaging_audit_format_repair_20261108_201016, 123 inputs/10 tasks fixed (format only), 0 calls; naive 87 (wv58/crash3/res26, nonresource61) vs repaired 82; +5 PUT (99:0,7,8,9; 124:1), 0 lost. Nonresource naive61/Soft60/Direct59 ≈ tie. Prefect 1a674c37-de6b-4095-9f27-313697b176ac. Report final/review/naive_format_repair_2026-11-08.md.

2026-11-08 user: PUT timeout while reference finishes = real bug. Common batch prompt size sentence replaced by naive one ("Keep floats finite, integers bounded, strings/lists modest (normally <=30 elements), and execution under 3 seconds."), final/src/modular/input_prompts.py; 409 tests pass; no new run launched.
