# v80 DeepSeek V4 Flash provider diagnosis — 2026-10-26

**Both requested providers returned useful task85 diagnoses. Reka also returned
a supported structured hypothesis. Neither four-slot run completed.** This is
selected-case capability evidence, not a concept-effect or provider ranking.

| Provider | Planned slots | Attempts | Complete answers | Terminal cause | Known cost |
|---|---:|---:|---:|---|---:|
| Reka |4|3|2|case124/full: curl28 timeout360s, reasoning stream/no final answer or usage|$0.00392265|
| DeepInfra/fp8 |4|2|1|case85/full: upstream429 engine_overloaded|$0.00136368|

Three of eight planned slots remain unattempted. Total known billed **$0.00528633**;
two new unresolved reservations: Reka$0.03846526 and DeepInfra$0.02562492. These
are conservative reservations, not actual bills. Prior Relace unresolved
$0.04898572 remains separate. Total known plus all unresolved exposure is
$0.11836223. Two read-only usage lookups for interrupted Reka generation returned
404; no billing conclusion follows. No further model calls/retries/fallbacks.

## Semantic assessment after both runs froze

Task85 minimumSeconds: PUT uses ceil(max_gap/2), but for a circular index gap d,
the d-1 interior cells fill from both ends in ceil((d-1)/2)=floor(d/2) seconds.

- **Reka raw85:** correctly identifies the general odd-gap rounding error and
  supplies nums=[1,2,1,2,3,4,3], expected2. Public reasoning: repeated values have
  largest gap5, so none can cover in1step; value1 covers the7-cycle in2. Native
  PUT returns3, verifying the proposed discrepancy.
- **Reka full85:** valid outer schema, one compiler-admitted hypothesis, correct
  math.ceil call site/spec-return clause, sound odd-length/all-distinct trigger,
  explicit max_gap//2 edit. Public check [1,2,3,4,5] returns3 from PUT and2 from
  the model's local edit. Public argument: one initial value reaches at most3of5
  positions in1step and all5in2. Hypothesis is supported for this family; a
  single replay alone does not validate the replacement on every possible input.
- **DeepInfra raw85:** correct root cause and two valid candidates: [1,2,3]
  expected1 versus PUT2; [1,2,3,1,4] expected1 versus PUT2. Both expectations
  follow directly from one-step adjacency. It includes an extra analysis_note
  field, so the frozen exact-single-analysis schema is **invalid** despite useful
  semantics. No silent parser repair or schema success is claimed.
- No complete task124 answer from either provider; no judgment of its semantics.
  DeepInfra full85 has no answer, so no structured-capability comparison there.

Five networkless program executions (four replay operations) after both freezes,
within <=2programs/returned response, verify all four inputs and the one edit.
No private oracle/reference algorithm/contract or paid judge; expected values
are explicit public-spec arguments. public_review_plan/results.json record them.
All raw model artifacts remain unchanged.

## Prior art and interpretation

Exact four prompts/cases/order from v72/v73. Earlier Qwen raw85 gave a wrong
trace/non-failing candidate; GPT-OSS raw85 was correct but full85 abstained.
Reka's supported full85 therefore provides a useful indication that this writer
contract is feasible for at least one selected task with this model package.
It does not isolate model size, compute, quantization or provider quality. No
larger run, training, v77 or concept-efficacy promotion is implied.

## Protocol, transport and review

Isolated v79 copy. Model deepseek/deepseek-v4-flash-0731; explicit independent
routes Reka and deepinfra/fp8, no fallback. Same enabled reasoning, total output
cap131072, temperature.2/top_p.95, JSON object, no seed. Per-provider caps .17/.12;
four maximum reservations .15210194/.10073340. Prompt/context/source identities
verified before paid calls;19 stream/diagnostic tests pass separately per route.
Independent prelaunch review and controller lifecycle fix applied before launch.

After Reka's unknown bill stopped the controller, transport amendment A was
recorded before any DeepInfra dispatch: user already requested both providers,
independent full reservations fit unchanged caps even with unknown Reka charge.
No semantic answer was inspected for that decision. No Reka retry or budget
transfer; prepared DeepInfra prompts/source unchanged. Separate launch receipt
pins amendment hash. Independent review verified timing and bound.

terminal_audit.json verifies both generation freezes, per-route counts, cost
receipts and tokens. Exact response values are preserved there. Controller's
earlier terminal records Reka-only stop; DEEPINFRA_RUN and DeepInfra frozen
summary record the separately authorized continuation. No efficacy GO/NO-GO.
