# v71 response-contract repair and fresh diagnostic — 2026-10-25

**6/6fresh responses are structurally valid explicit abstentions; gate0/6.**
Each response is exactly {"hypotheses":[]}, finishes stop, and is now recognized
as deliberate empty output rather than a missing-field default. No hypothesis
is rejected by compiler because none is proposed. Zero fresh native construction,
generator-arm calls, private oracle or detection score.

Run09:41:05–09:43:57UTC (16:41–16:43Vietnam), same6cases61,66,124,58,131,85,
Qwen2.5-Coder32B/ngrok/context8192,1536output cap.6physical dispatches and6
received responses,zero failures/unknown/truncation.31,949input+60output =
32,009tokens. Exact request hashes and prompt/tokenizer usage match all receipts.

| Case | Outer schema | Explicit abstention | Proposed/admitted | Gate |
| --- | --- | --- | ---: | --- |
|61|valid|yes|0 /0|FAIL|
|66|valid|yes|0 /0|FAIL|
|124|valid|yes|0 /0|FAIL|
|58|valid|yes|0 /0|FAIL|
|131|valid|yes|0 /0|FAIL|
|85|valid|yes|0 /0|FAIL|

## Engineering changes and causal limits

The earlier v70run had4missing-root schema responses and2explicit abstentions.
Its parser silently defaulted missing hypotheses keys to[], concealing contract
failures. V71shows full nested output_schema, separates hypothesis_fields from
root, includes exact empty_output, and records invalid payload vs true abstention
with raw-response hash. Single root claims are never automatically wrapped.
Domain/condition/edit semantics, evidence rules and all-case gate remain unchanged.

142authored regression tests passed17.44s. Read-only classification of the six
frozen v70responses yields exactly4contract errors+2explicitabstentions withzero
model/native calls. All new6prompts fit context(max6332+1536=7868<=8192) before
first dispatch. V70raw responses/source/outcomes remain byte-identical.

This repair resolves response classification and observed outer-schema compliance
on these six fresh answers. It does not establish better semantic hypotheses,
model understanding, lower false-alarm rate or improved bug detection. The common
empty output could reflect inability, prompt conservatism or other model behavior;
this small diagnostic does not identify that cause. Client receipts rule out an
application-cache collision; remote serving behavior is not independently proved.
No rerun, gate relaxation or automatic third fresh writer diagnostic follows.

## Domain work from v70

The requested input-domain integration is implemented in v70and preserved here:
closed grammar over exact public Constraints quotes binds numeric lengths,
relations, element bounds, alphabets and square point geometry/uniqueness. Rules
are conjoined before solver/native budgets; unknown lines block rather than
silently widen the domain. Concrete model/native/displayed inputs are rechecked.
No domain bound is inferred from public-example sizes/signs.

Saved-v67CPU replay with domain constraints generates8case124valid realized
inputs, replacing v69's22empty invalid inputs, with0sensitivewitnesses.140native
executions total;0newmodel/private calls. Case124shape pruning eliminates34
invalid shapes for each of the two viable alternatives. This verifies the
engineering improvement, not the hypotheses' correctness or efficacy.
See ../v70_domainwriter/RESULTS_CPU.md and cpu_terminal_audit.json.

Fresh writer testing is now completed. The current bottleneck is nonempty,
justified fault hypotheses under this writer contract. Another oracle cannot
supply missing hypotheses or constructed inputs. Oracle/ref10 and full generation
remain deferred. No new promising-concept claim follows from gate0/6.

## Usage, integrity and completion

V70fresh:6responses,31,317tokens. V71fresh:6responses,32,009tokens. Cumulative
12fresh writer dispatches,62,794input+532output=63,326tokens,zero unknown usage.
No monetary price inferred for the notebook endpoint. Historicalv67tokens and
CPU-only replays are not charged again as new model generation.

Owner artifact auditPASS77frozenJSONentries, source/config/protocol/preflight/
request/response hashes, all actual attempt receipts, exact server-token counts,
public-domain receipts and prepared-evidence parity. No independent-agent review
performed or claimed. Domain grammar is limited to supported explicit forms;
its completeness marker does not establish arbitrary English/spec correctness.
Controller and child exited; no active owned job, endpoint observer or automatic
continuation remains. Full generation is blocked by the unchanged gate.

Artifacts: fresh_artifacts/, fresh_terminal_audit.json, preflight.json,
saved_contract_classification.json, CURRENT_RUN.json. Raw writer answers are
preserved without normalization or hypothesis invention.
