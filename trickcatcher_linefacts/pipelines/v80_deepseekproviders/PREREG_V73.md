# v73 GPT-OSS120B writer diagnostic — before paid completions2026-10-25

User explicitly requests openai/gpt-oss-120b via streaming OpenRouter, using
existing env and cheapest-priority providers. This authorizes4paidcalls only on
the same2cases85/124raw_known/full_known prompts from frozenv72. Source/spec,
known-bugpremise,ordering,seed20261024,temp.2,top_p.95,response_formatjsonobject
unchanged. No answer hints, model feedback, constructor/oracle/fullpipeline.
V72Qwen rawtrace/expected errors and fullabstentions remain historical controls.

Transport:curl-N/streamtrue,APIkey passed only in process stdin configuration,
never printed/stored/commandargs. Source scripts/research_env.sh and silently
source scripts/openrouter_env.sh;never inspect its contents. Fixed official
OpenRouterURL;no model fallback. One physical dispatch per slot,no paid retries.
Persist request and dispatched-unknown receipt before network,rawSSE plus finish/
usage/provider receipts after. Missing usage/cost or failed stream stops further
spend. Preserve malformed/truncated outputs;no adaptive second model call.

Provider:sortprice,require_parameters=true,max_price prompt$0.05/M,completion
$0.25/M,request0. Captured public endpoint metadata currently advertises lowest
$0.03/Minput,$0.15/Moutput;cheapest endpoint supporting required JSON/seed is
NearAI. Router can fall back within caps if unavailable;record actualprovider.
No separate Hello/smoke completion. Overallrun capmin(envcap,$0.02);worstcase
reservation based on serialized prompt bytebound+2048overhead and8192output,
using providermaxprices, checked before any dispatch. Report actualusage.cost.

Reasoning:effortlow,excludevisible reasoning,max_tokens8192TOTAL. GPT-OSS needs
reasoning budget;this differs from Qwen1536without equivalent accounting. Thus
model/provider/quantization/reasoning/tokenbudget all confound attribution;this
is a practical package comparison,not a matched-compute model-size experiment.
Prompts are byte-identical tov72but provider/model/wireoptions differ.

Streaming parser must handle comments,multiline data,usage frame with empty or
repeatedfinishchoice,midstreamerror,missingDONE/usage and failednon-SSEerror.
Outputsize/deadline bounded. Tests cover parse/accounting/no-key-on-commandarg.
Owner review only;no independent-agentPASS under current delegation restrictions.
Freeze all sources/config/protocol/review/runtime,prompts and endpoint metadata
before first paid call;all4denominators fixed,zero private labels.

After all4outputsfreeze, reviewsemanticcontent separately from schema/compiler.
Reuse two public reviewer anchors fromv72as historicalprobes (no newnativecall)
when applicable. New model candidates/edits may get<=2publicnetworkless probes
pernewresponse(8total),afterfreeze,using visible-spec reasoning,not private
canonical or reference-program implementation. Do not infer correctness from
nonemptyprose or matching baseexamples. Full-hypothesis local edits remain
semantically unverified without decisive source/spec evidence. No autoretry,
largercohort,paidjudge or fullpipeline follows this diagnostic.

References for wire/routing/usage semantics:
https://openrouter.ai/docs/guides/routing/provider-selection
https://openrouter.ai/docs/api/reference/streaming
https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
