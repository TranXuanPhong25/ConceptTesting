# v80 DeepSeek provider diagnostic — 2026-10-26, prospective

User explicitly requests Reka and deepinfra/fp8 after two Relace429 attempts.
Isolated v79 copy; exact four frozen v72 prompts/cases85,124/order per provider.
Same DeepSeek V4 Flash0731, reasoning enabled, total output131072, JSON object,
temperature.2/top_p.95, no API seed. No v77/full pipeline/task enlargement.
Prior art: v72 Qwen/v73 GPT-OSS diagnostic; v79 no responses due Relace429.

Two explicit independent routes, NOT silent fallback. V80_PROVIDER chooses
reka or deepinfra/fp8, provider.only exact tag, allow_fallbacks false,
require_parameters true. Each route checks live price ceilings, context and
supported parameters, freezes exact source/plan/provider identity and has a
separate ledger/output root. Reka cap$0.17, price ceilings .05/.28 USD/M;
DeepInfra cap$0.12, ceilings .06/.18. New maximum authorized caps total$0.29;
prior Relace unresolved$0.04898572 retained separately (overall exposure <=
$0.33898572). Four maximum reservations must fit each cap before first call.

Four logical requests/physical attempts per provider, no Hello, paid retry,
resend on empty/length, additional model or provider. Run Reka then DeepInfra;
provider-specific upstream errors stop that run, not the other explicitly
authorized route. Account/login/global usage denial or unknown bill stops all
additional spending until clarified; provider-specific non-generating rejection
may proceed to the separately authorized route with its reservation retained.
Actual usage.cost required before next slot within each run. One unknown charged
request retains its maximum reservation; never treat absent receipt as free.

Reuse bounded SSE transport and exact prompt identity from v79, preserve all
parents. Credentials only silently sourced, never inspect secret env files.
No partial output semantics reviewed until both providers terminal/frozen.
Semantic review public spec/source only, <=2 native public probes/response,
16 total across eight responses. No private oracle/reference program/paid judge.
Separate correctness, schema/compiler, abstention, length and costs. Provider
packages differ (DeepInfra fp8, Reka quantization unknown): no pure quantization
or causal concept claim, no pooled efficacy result. Owner/independent prelaunch
review and targeted transport/diagnostic tests precede paid dispatch.
