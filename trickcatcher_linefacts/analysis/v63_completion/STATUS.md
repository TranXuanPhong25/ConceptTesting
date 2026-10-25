# v62 stop and v63 recovery — 2026-10-25

User-requested check found v62 stopped_requires_review, runner/supervisor exited. Exact stop: case85 module-level sys.setrecursionlimit(50000) produced empty lexical scope; verify_input indexed scope[-1] after replay, raising IndexError. This is an implementation failure. No generation arm/final/scoring exists.

Six writer responses:18proposals,14admitted/4rejected (two predicate operators, one external/keyword alternative call, one GeneratorExp alternative). Five completed construction checkpoints:61=0witness,66=24,124=0,58=3,131=30; only131has1sensitive witness. These are native descriptive witnesses, not validated spec semantics or confirmed bugs. Case85 CPU work lacks checkpoint: exact native usage unknown. Saved native executions across five checkpoints=1024. Gate prefix already exceeds its registered case thresholds but gate artifact was not written before crash.

Actual v62 model usage:6physical dispatches,6received/stop responses,33560input+3228output=36788tokens;0unknown completions. All six writer prompt counts had exact tokenizer preflight. No five-arm scores are available. Detailed source artifact hashes and counts are in v62_stop_audit.json.

v63 is an engineering continuation, not a new independent replication. It preserves six exact writer slots and five checkpoints with original identities/receipts, accounting once. Minimal empty-scope guard reports unsupported without replay or fabricated witness. Case85 recovers CPU work under a separate bounded segment; historical unknown execution usage remains explicit. No reset/retry of completed writer outputs, no cohort/provider expansion, no v62 source/artifact changes. New arm calls wait for independent review, exact readiness and unchanged gate.

24targeted tests passed locally (new2 + inherited22). Independent read-only review PASS:24tests independently passed,47originalJSON/40importedfiles hashverified. User monitoring preference remains30minutes; exact old v62 observer was retired after this manual check to avoid stale callback, same thread retained privately for v63 observer. No generation is currently active at this checkpoint.

## Reviewed launch

2026-10-25 01:21:58UTC (08:21:58Vietnam): exact readiness generated after independent PASS; implementationcommitbeb6b9a pushedmain. Runner397684, supervisor397685, observer397686. Initial verification: generation_active, protocol exists,6importedresponses/6historicalattempts, no new model attempt yet; case85 CPU recovery precedes unchangedgate andremaining102armslots. Next scheduled observation01:51:58UTC/08:51:58Vietnam, interval1800seconds. Runfolder out/pipelines/v63_scopeguard/pilot6_20261025/generation; monitor_v2 sibling; postfreeze score target analysis/v63_completion/out_reviewed. No score known atlaunch.

## Terminal — supersedes launch

Usermanualcheck02:41UTC foundgeneration+scorecomplete,108responses/6results/778freezeentries. IndependentterminalauditPASS; labelsremainprovisional. Pattern1/6confirmed(case85),otherfourarms0/6;6PUTs=5problems.14admitted/57realizedconstructorwitnesses/1sensitive, but sensitiveexampleusesunvalidatedNoneexpressionandwasnotdisplayed. Fullresults/caveats/447667actualtokensinRESULTS.md andterminal_audit.json. Source/readiness/continuation/scorer hashesallverified; noongoingownedrunner/supervisor. Exactobserverretiredaftermanualcheck; nofurthercalls/runs.
