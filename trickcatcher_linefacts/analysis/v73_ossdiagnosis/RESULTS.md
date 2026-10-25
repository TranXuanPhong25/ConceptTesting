# v73 OpenRouter GPT-OSS120B diagnostic — 2026-10-25

**All4streamed calls completed through Near AI, actual total$0.00062757.**
Raw diagnosis correctly identifies a narrow rounding failure with a real
counterexample on case85; case124off-by-one hypothesis is incorrect and its
proposed edit breaks a supplied public example. Full contract explicitly
abstains on both cases. No full pipeline/gate-construction/oracle evaluation.

## Same prompts, different model package

User requested openai/gpt-oss-120b via existing OpenRouter env with cheapest
provider priority. Exact4v72promptmessages/cases85,124/order/known-bugpremise
are byte-identical. Requests streamed usingcurl-N/streamtrue,credentials supplied
only through stdinconfig. No separate Hello completion,paidretry or model fallback.

Routing:provider.sortprice,require_parameters=true,pricecaps input$0.05/M,
output$0.25/M,request0. Public endpoint metadata advertises Near AI at$0.03/Minput,
$0.15/Moutput,the lowest eligible endpoint supporting the requested JSON/seed.
Venice has the same headline prices but lacks those requested parameter flags.
Actual SSE receipts report Near AI for all4calls. Currentprices are a captured
snapshot,not a promise of future rates; routing uses live availability.

Reasoningeffortlow,excludedfromvisibletext;8192totalreasoning+answer cap differs
fromQwen1536. Same prompts/seed/temp.2/top_p.95, but model/provider/quantization/
reasoningbudget differ. Thus this is a practicalpackagecomparison,not a causal
model-size or matched-compute test. Endpoint advertisesfp4;actual hardware/weights
were not independently inspected. All streams finishstop;none hits tokenlimit.

## Results and bounded public checks

| Case | GPT-OSS raw | GPT-OSS full | Earlier Qwen raw/full |
| --- | --- | --- | --- |
|85|Correct narrow odd-length/single-occurrence failure;candidate[1,2,3,4,5]expects2,PUTreturns3.|Explicit[]|Rawwrongtrace/nonfailingcandidate;full[]|
|124|Incorrectsuffix-feasibilityoff-by-one claim;proposed<=teditbreakspublicexample.|Explicit[]|Rawusefulinputbutwrongexpected;full[]|

**Case85:** model identifies ceil(max_gap/2)overestimation for a single-occurrence
value on an odd cycle and gives all-distinct[1,2,3,4,5]. Public reasoning proves
optimum2:one target initially occupies1position,one step reaches at most3of5,
two steps reach the entire5cycle. Native PUTreturns3,matchingmodeltraceand
establishing this specific discrepancy without a private reference.
The proposed n→n-1single-occurrence adjustment addresses that family;it is not
validated as a full repair for repeated-occurrence odd-gap bugs. Some verbal
radius wording is imprecise;credit is limited to the correct operational family
and demonstrated counterexample,not universal correctness.

**Case124:** model claims current jAfter[mi+1]<=t+1is too strict and should be
<=t. This reverses the inequality implication:<=tis stricter. Source jAfter
tracks the earliest suffix position that can still be matched;after using the
change at t,it suffices to match word2[t+1:]. The current threshold reflects that.
Applying the model's explicit suggested edit on the first supplied public example
('vbcca','abc')changes output[0,1,2]to[],breaking an already visible requirement.
The unchanged PUTpasses that example. This hypothesis is not semantically valid.

Both full outputs are well-formed{"hypotheses":[]}with zero proposals;no compiler
rejection or parser loss. They used only41and51total outputtokens(including19
and29reasoning tokens),so their abstention was not forced by budget exhaustion.
Raw outputs use735/919total tokens(including446/559reasoning).

After all4outputs froze,two networkless replay operations executed three programs:
case85originalcandidate once;case124original+model-edit once each on supplied
baseexample. This stays within<=2program probes per new response/8total.
All inputs satisfy public domain constraints. No new API call,private canonical/
contract/scorer,reference algorithm,or oracle-program implementation. Explicit
public reasoning and raw execution artifacts are inpublic_review_results.json.

## Interpretation

GPT-OSS improves the raw85diagnosis over Qwen,so stronger semantic reasoning can
help. It still gives a wrong124claim. Both models abstain under the full contract,
consistent with a contract/task-burden issue as well as model reasoning limits.
The evidence does not support simply increasing gate strictness or treating all
nonempty hypotheses as correct. A lighter hypothesis/input writer plus tool
verification remains worth distinguishing from a writer required to supply a
justified exact-site local repair. No concept-effect or full-generation gain is
measured by this selected2case/one-sample diagnostic. No automatic larger run.

## Usage, price and completion

Actual4dispatches,4completecostreceipts,0unknowncost/transportfailures/truncation.
12,285inputtokens,1,746outputtokens including1,053reasoning(693visible).
48cachedinputtokens per call. Usage costs per slot in dispatch order:
$0.00016524,$0.00012699,$0.00013854,$0.00019680;total$0.00062757.
PRICE_AUDIT.jsonrecomputes every bill from capturedNearAIrates and usage exactly.
Before launch,worstcase reservation$0.01084265fit under$0.02cap;actualis lower.

Owner read-only auditPASS60frozenfiles,source/config/protocol/runtime/request
identity,exactv72messages,rawSSEparsing,provider/model/usage/cost/attempt receipts.
19authoredstream/diagnostic tests passed. No independent-agentreviewclaimed.
EarlierQwenpipelines/outputs unchanged. Run11:17:11–11:17:59UTC
(18:17–18:17Vietnam),process exited,noactivejob/autoretry. Key/envcontents never
printed,inspected orcommitted. Assessment is separate from immutable model output.

Artifacts:PLAN_FROZEN.json,endpoints_before_run.json,frozen_artifacts/,
terminal_audit.json,PRICE_AUDIT.json,public_review_plan/results.json.
Wire semantics references:[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[streaming](https://openrouter.ai/docs/api/reference/streaming),
[reasoning tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
