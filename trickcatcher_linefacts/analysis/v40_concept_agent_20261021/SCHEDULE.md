# User-authorized delayed v40 launch —2026-10-21

User says wait10minutes then run. Not before05:23:50UTC /12:23:50Vietnam21Oct,
600seconds after initial scheduling clock. Detached controller verifiedalive, PID2966234.
Endpoint is only in inherited process environment; no env file/URL saved. Pipeline
treatment/source/prepared data unchanged. ScriptSHA and timing in owned runtime
delayed_launch.json; separate registration/lifetime locks plus D1controllerlock guard
duplicate launches. No Qwen task/tokenizer request made during the waiting period.

At deadline: recheck live Codex5h quota, wait for reset ifremaining<=15%, verify frozen
source/prepared/dependencies, then run unchanged approved Qwen32B controller exactly
once. HTTP/model/context/tokenizer failures stop; no transport retries/fallback. Only
explicit safe quota checkpoint can resume existing durable slots after reset, never
unknown attempts. This is orchestration, not changed prompts/serialization/treatment.

After completion/stop, queue a followup to the original Codex task using `codex queue`,
not second CLIresume (previous writerconflict). Callback receipt/start remains to be
observed; diagnostic execution itself does not depend on callback success. No benchmark,
heldout, paidfallback, training or newexperiment authorized by this schedule.
