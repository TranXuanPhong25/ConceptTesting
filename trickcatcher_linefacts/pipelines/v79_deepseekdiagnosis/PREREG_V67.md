# v67 compact writer protocol — 2026-10-25, before completions

User explicitly authorizes the six-case prepare-only diagnostic. v65 public
preflight found case66 context overflow:6755prompt+1536output=8291>8192;
all six tokenizer requests completed, zero completion requests. Preserve v65.

Repair only JSON whitespace via json.dumps(writer,separators=(',',':')) for
all six cases. Parsed packet must equal v65 packet exactly, including source,
spec clauses, sites, public examples, predicates, and output schema. No lower
output allowance, data omission, provider/model/cohort substitution, or retries
for invalid model responses. Same qwen2.5-coder-32b-instruct, context8192.

Inherit PREREG_V65 hypothesis/public-consistency/selection/all-six-case gate,
64candidates/256native/120s construction budget and max3hypotheses per writer.
Exactly six logical writer slots; at most two transport dispatches per slot.
Completed invalid/truncated answers are retained without adaptive repair.

Authorized stage ONLY --prepare-only. Obtain six writers, run public checks and
construction, assess exact prepared concept contexts, then stop regardless of
pass/fail. Zero arm calls, final assertions, private oracle reads or scores.
Report actual usage, rejects, public-check status, realized/sensitive/displayed
witnesses and gate result per case, including all failures in denominator.
A prepared context is not a physically dispatched generator prompt.

Review: owner source/protocol audit and offline regressions are recorded in
analysis/v67_prepare6/REVIEW_RUN.md. Independent subagent review is not performed:
current orchestration rules prohibit spawning agents without an explicit user
or applicable AGENTS.md delegation request. This limitation is disclosed; no
independent-review claim is made. User authorization covers this bounded
engineering diagnostic; neither readiness nor gate establishes semantic truth.

Freeze request bytes, all sources/config/runtime/author artifact and exact
preflight counts before dispatch. Fresh output folder; no v63 writer reuse.
Detach execution and preserve attempts/checkpoints on transport or process
failure. No automatic wider run or model/provider fallback. Sparse observer
interval30min only if still running; no completion endpoint keepalive needed
for this short diagnostic. Terminal artifact audit after freeze.
