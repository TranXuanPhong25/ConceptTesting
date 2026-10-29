---
name: v85-retrievalhybrid
description: Complete113pairs/1130refs;primary ref retrieval78 vs v11 77,FA10vs13,paired10-9 p1.0;secondary73vs61
metadata:
  type: project
---

2026-10-28 user asks direct comparison, then specifically requests replacing
v11's concept mechanism with the v2 retrieval pipeline in a new version.
Implemented trickcatcher_linefacts/pipelines/v85_retrievalhybrid, copied from
v11_fair. See README,PREREG_V85,CHANGELOG,PARENT,FREEZE andCPU_CHECKS there.

Both arms: full113,K1,Qwen3.5-27B-AWQ,shared fresh B5 validity/domain preparation,
original v11 hybrid flow/caps and10shared spec-only oracle programs per task.
Target canonical/contracts final-grading-only. Treatment selects v2 top3 cards,
binds source spans to existing v11 execution targets; if unavailable, explicitly
uses weaker source-line reachability. No claim that either proves the card's bug.
Primary ref consensus,secondary o0;matched caps,not necessarily realized requests.
No historical inference reuse,paid fallback,transport retry or heldout evaluation.

27CPUtests pass,including native preprocessing/classification/Hypothesis/oracle
and denied network access. Mac sandbox-exec port applies equally to both arms;
separate /tmp/pytoy-v84-venv has pinned original tool versions.225source/input and
57parent hashes verified. Source/protocol frozen before attempted launch.

Initial detached PID97647 at2026-10-28 08:36UTC stopped on GET/models HTTP404:
0completion attempts,all113pairs/oracles unattempted,controller exited. Receipt:
out/humaneval/comparison/PREFLIGHT_TERMINAL.json. User asked asynchronously to
restore endpoint or supply changed URL; no answer yet. Do not reset original
CLAIM or imply benchmark has run. Once live, use same frozen code with fresh
output root via comparison.ROOT=comparison.DATA_OUT/'comparison_live_1' before
comparison.main(); launch detached,recordPID. Max3503attempt budget remains unused.

**Why:** standalone v2's45/113cannot be fairly compared with historical v11's61:
different model,rounds andoracle. This preserves v11's hybrid/oracle while changing
the concept package. It is not KITE reimplementation or v77's v31 combination.
**How to apply:** continue this already authorized run when endpoint returns;
no new permission question. Keep standalone results and all frozen parents intact.

2026-10-28 09:46UTC /16:46Vietnam user restores the same endpoint and says run.
Detached comparison_live_1 launched PID51658; exact model/context preflight passes.
226current source/input and57parent hashes/tool versions verified before launch.
Observed6/113prepared tasks,31received completions/32attempts,0transport errors
at the first progress checkpoint. These are shared preprocessing calls, not final
test-generation/detection results. Same frozen algorithm,113/K1,3503global cap.
The controller automatically continues paired generation,1130shared spec-only
oracle requests, generation freeze, then final reference grading. No extra ping
completions while task traffic is active. No retry/duplicate controller.

Active root: trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/comparison_live_1.
Read STATUS.json,transport/attempts.jsonl,controller.pid and eventual RESULTS.json/
COMPLETE.json. Initial comparison/404 receipt stays untouched. The older statement
about waiting for an endpoint is superseded; no further permission is required.

2026-10-28 10:30UTC status check:shared preparation completed113/113 with480
received preprocessing responses,0transport failures. Last task160 do_algebra
was computing native facts (CPU active),then finished without intervention.
PREPARATION_FREEZE exists; controller moved to generation_pairs. Source/parent
hashes still pass,PID51658 alive. No oracle/final grading or efficacy result yet.

2026-10-28 11:02UTC check supersedes prior running status:PID51658 exited at
10:38:47UTC. Task125 retrieval correction has4964input+4096requestedoutput=9060
tokens>8192; preceding strategy truncated at4096.509responses/225211tokens,
0unknown usage;6complete pairs (7baseline/6retrieval),113prepared,0oracle/scoring.
Original last status5 undercounts one pair finishing while the error unwound.
Server tokenizer confirms4964; endpoint alive. Parent source/input/output intact.

Authorized full113 completion resumed in separate v85_contextfit with prospective
PREREG:effectiveoutput=min(requested,8192-prompttokens), applied symmetrically,
no prompt truncation.509responses/attempts and all113 preparations imported by
verified hashes; inherited calls count toward3503cap.31CPU checks pass,6054parent
output files frozen. PID30096 launched11:12UTC with6pairs restored and formerly
blocked correction submitted with3228cap. This is amended protocol, not original
fixed-cap completion. No efficacy result yet; do not duplicate/restart.

Active status now:trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/comparison_contextfit_1/STATUS.json.
Child source:trickcatcher_linefacts/pipelines/v85_contextfit/.
Read analysis/v85_context_stop_20261028/REPORT.md for diagnosis/provenance.

11:15UTC actual formerly blocked correction received4964input/3228output,
finish_reason=length;controller advanced7/113pairs,511received responses.
Transport recovery demonstrated; strategy still truncated,no efficacy claim.

2026-10-28 13:05UTC user says continue. PID30096 had exited12:02:52UTC on
transport failure after25/113paired tasks;113prepared,0oracle/scored.574received
responses/575attempts;295979known tokens plus1unknown-usage timeout (task78,
retrieval round1). Separate tokenize URLError used0completions. Source/ancestor
hashes and574request identities pass.13:06:58UTC GET/models404;0newcompletions,
no new controller. User asked to restore endpoint or provide changed URL.
This supersedes running status. Do not reset either terminal root; continuation
is authorized when reachable, but requires fresh output/provenance and keeping
the unknown attempt in cumulative3503cap (2928remaining). No efficacy result.

2026-10-28 user clarified desired integration keeps v11 two rounds/10refs while
replacing fuzz/trace concept generation. Disclosed current v85 still computes
v11facts to bind cards to executable targets; it is not yet a clean removal of
that dependency. User then restored endpoint and says run. Continue this frozen
comparison consistently; do not silently mix a different concept mechanism into
the remaining88tasks. A clean replacement requires a separate registered variant.

15:00:55UTC GET/models confirms exactQwen27B/context8192. New v85_transport_resume
copies continuation runner; unchanged contextfit transport/generation/scorer.
574received receipts and25paired checkpoints imported; failed task78round1
request retained in HISTORICAL_UNKNOWN.json and authorized for one fresh attempt.
Active ledger cap3502 + historical unknown1 = original3503cumulative cap; final
cost accounting explicitly retains unknownusage1.7CPUchecks pass,574request
identities and3900parent output files verified/frozen. No original source edits.

PID54121 launched15:04:58UTC. At15:05UTC restored25/113pairs and observed575
received responses,including a fresh completion; oldunknown remains separate.
Active root:trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/comparison_contextfit_2.
Source:trickcatcher_linefacts/pipelines/v85_transport_resume. No oracle/scoring
result yet. Do not duplicate/restart; inspect STATUS.json and controller.pid.

2026-10-28 15:49UTC user check:PID54121 had stopped15:27:07UTC on
RemoteDisconnected at task81 retrieval round2 expected-output request.43paired,
44v11/43retrieval rows,653received,654active+1historical=655attempts.379796known
tokens and2cumulative unknown attempts;0oracle/scoring. Source/parent hashes and
all653request identities verified.15:50:04UTC GET/models same27B/context8192 live.

Continued standing full113 execution in new v85_transport_resume2; method and
contextfit transport unchanged.653responses imported,2failed physical attempts
retained separately (task78 remains unknown even though its later call succeeded).
Active cap3501+historical2=3503;2848new attempts remaining at launch.7focusedCPU
checks pass;5147parent output files frozen. PID65630 launched15:53:12UTC;observed
44pairs/655received responses at15:53:48UTC,including recovery past failed task81.
Active root now:trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/comparison_contextfit_3.
Source:trickcatcher_linefacts/pipelines/v85_transport_resume2. No efficacy result.
All predecessor roots terminal; do not duplicate/reset or modify frozen code.

2026-10-28 16:21UTC check:PID65630 exited16:10:45UTC after240.81s timeout at
task124 baseline strategy_0_1 (2783prompt/4096cap).54paired tasks;55v11/55retrieval
rows on different task sets;694received,695active+2historical=697attempts,
429482known tokens and3unknown-usage failures.0oracle/scoring. Nearby successful
4096-token response took237.20s; endpoint same27B/context8192 live16:22:37UTC.
Evidence suggests the240s cap is too tight, but failed server outcome is unknown.

New v85_transport_longwait changes completion HTTP timeout only to900seconds,
both arms; tokenizer240/models25 unchanged. No prompt/token/method/round/ref
changes or automatic retry loop.9focusedchecks pass;694request identities and
5833parent output files verified/frozen. Activecap3500+historicalunknown3=3503;
2806new attempts remaining at launch. PID76780 launched16:25:07UTC,54pairs and
694responses restored,missing completion submitted. No efficacy result yet.
Active root:trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/comparison_contextfit_4.
Source:trickcatcher_linefacts/pipelines/v85_transport_longwait. Predecessors terminal.

2026-10-28 17:16UTC (00:16Vietnam29Oct):generation complete113/113pairs, verified
113final hybrid rows per arm. PID76780 alive; shared_spec_oracle19/1130,919received
responses total,0new transport failures in contextfit_4.3historical unknowns remain.
Scoring not started; no efficacy result. Same active root/controller; do not duplicate.

2026-10-29 handoff supersedes all running status above: user explicitly stops
local execution so another machine can continue. PID76780 exited17:19:23UTC28Oct
after draining in-flight requests.113/113paired generation,36/1130shared refs,
936received/936active attempts,0unresolved;3historical unknowns=939cumulative.
No scoring yet. Do not restart local inference. Portable frozen snapshot and
resume-only driver: trickcatcher_linefacts/handoffs/v85_20261029/README.md.
Destination generates only1094missing refs then scores; same3503cumulative cap.
Offline manifest/native checks and3resume tests pass; no new model calls.
Linux destination not executed here; sandbox check required before inference.

2026-10-29 03:23:48UTC user explicitly says run again, superseding local-stop
and transfer instructions. Portable resume launched detached PID44302 from
trickcatcher_linefacts/handoffs/v85_20261029/resume.py --run, existing work/.
Offline hash/ledger/native checks pass; first fresh ref received (37/1130,
937received total,2in-flight,0new failures at first check). SameQwen27B,2workers,
900s completion timeout,3historical unknowns;1094remaining refs at launch,
then automatic paired scoring. No generation rerun; original roots untouched.
Active root: trickcatcher_linefacts/handoffs/v85_20261029/work/snapshot/
trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_20261029.
Inspect STATUS.json and HANDOFF_COMPLETE.json; do not launch another copy.

2026-10-29 (Vietnam), Codex: user explicitly requests continuation on the Linux
destination and supplies the live endpoint. This supersedes the local-stop
notice for this destination only. Python3.11.14 venv installed with the exact
pinned tool versions;3resume tests,native shared-oracle test and reachable-listener
network-denial check PASS. Offline manifest/ledger checks report113generation
pairs,936received,3historical unknowns,36saved/1094missing references.
Detached PID22898 launched about17:43UTC28Oct using the unchanged resume.py.
Endpoint preflight passed;first2new reference slots saved by17:44:43UTC.
Only missing references run,then the driver automatically freezes and grades.
No final result yet. Do not start a duplicate or rerun failed/unresolved attempts.
Destination status and completion markers are under
trickcatcher_linefacts/handoffs/v85_20261029/work/snapshot/trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_20261029/.
Read HANDOFF_COMPLETE.json,not PID or COMPLETE.json alone,to establish final
cumulative accounting. Linux portability preflight is now tested;report OS change.

Historical Linux continuation checkpoint (2026-10-29 Vietnam, Codex; superseded
by the Mac continuation and completion recorded below):
PID22898 exited after138new references:174/1130saved,956remain.
Last attempt:2026-10-28 18:09:34UTC. Final two completion attempts received
HTTP503 (unknown usage) and HTTP404 (recorded without unknown usage).
1074received/1076current-ledger attempts+3historical=1079cumulative attempts;
4unknown usage. Both113generation arms remained complete;no final grading then.
Source/import hashes,saved-oracle identities and request hashes passed offline audit.

User requested continuation, but that session's network was restricted:metadata
probe failed DNS resolution;0new completion requests. The unchanged driver refused
the retained failed attempts. All receipts and the work directory were preserved
for networked continuation with explicit failure accounting. See
CONTINUATION_AUDIT_20261029.json. No source or protocol changes made in that check.

2026-10-29 03:31:22UTC latest supersedes both previous hosts: user confirms
Mac execution, Linux stopped. SSH found LinuxPID22898 exited at174refs with
1074received+503unknown/404known failures. MacPID44302 was briefly launched
before fetching that notice;blocked reservations/drained then stopped03:25:46UTC
at49refs,13new successful calls,0unresolved. All13match already-received Linux
request identities;Linux outputs retained without content-based selection.

Fresh v85_20261029_resume2 snapshot imports174refs/113pairs and preserves18
historical attempts (3oldunknown+503unknown+404known+13known duplicate calls).
1092physical attempts at launch,4unknowns,3503global cap;duplicate known usage
added to final totals. Three CPU tests/nativechecks andLinux originalhashesPASS.
Detached MacPID46002 resumed only956missing refs then automatic scoring.
Active root:trickcatcher_linefacts/handoffs/v85_20261029_resume2/work/snapshot/
trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_resume2_20261029.
Original generation/source unchanged;see resume2 README/PREREG. No final result.
Do not launch old archive or duplicate controllers;preserve allhost accounting.

2026-10-29 07:04UTC completion check supersedes every RUNNING notice:
MacPID46002 exited;HANDOFF_COMPLETE exists,1130refs/113scored tasks,0pending.
Primaryref retrieval78/113vs v11 77/113,FA tasks10vs13,paired10wins/9losses,p1.0.
No reliable primary detection gain. Secondaryo0 retrieval73vs61,FA51vs57,
paired17/5,p.01690;do not substitute secondary for primary. D_I_samples85vs84.
Note o0retrieval D_IO_samples72 differs from confirmed_tasks73 by definition;
no independent replay of that discrepancy. Primaryref summaries agree.
Final hashes/receipts/1130oracle identities/cumulative arithmetic audited:
2030active received+18historical=2048physical attempts;4unknown usage,13known
duplicate successes included. Known usage1,118,505tokens;RESULTS authoritative
(STATUS usage omits duplicate tokens). Allfinal artifacts andreport committed
under trickcatcher_linefacts/handoffs/v85_20261029_resume2/completed/.
No new calls/fullrescoring/heldout replication;no automatic continuation.
