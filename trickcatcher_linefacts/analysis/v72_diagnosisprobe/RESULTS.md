# v72 two-case diagnosis/contract diagnostic — 2026-10-25

**Raw diagnosis produces prose2/2; full contract with the same known-bug premise
still explicitly abstains2/2. Neither raw answer supplies a fully supported
semantic diagnosis with a correct demonstration. Case124does supply a useful
bug-revealing input, despite an incorrect expected value/explanation.**

Four fresh calls completed normally10:05:52–10:09:09UTC (17:05–17:09Vietnam),
Qwen2.5-Coder32B/ngrok/context8192,1536output tokens per call. Cases85/124are the
two shortest public sources from the fixed6with distinctentry/problems. They are
already-seen dev cases; this is not a blinded efficacy evaluation. Model received
no bug-site hints or reviewer counterexamples. Four independent calls, same seed/
system/temp/top_p, counterbalanced raw/full order. All4stop, no truncation,
transport failure or unknown usage.12,499input+663output=13,162new tokens.

## Observed answers and source/spec review

| Case | Raw with known bug | Full with known bug | Historical full without premise |
| --- | --- | --- | --- |
|85|Nonempty circular-gap hypothesis, but incorrect trace and non-failing candidate.|Explicit empty hypotheses.|Explicit empty hypotheses.|
|124|Points to mismatch-placement loop; candidate reaches bug, expected and explanation are wrong.|Explicit empty hypotheses.|Explicit empty hypotheses.|

**Case85:** raw answer suspects circular wrap-around gap handling and proposes
[1,3,1,3,1]. It claims the gap for1is3and PUTreturns2while optimum1. Actual1
positions0,2,4have circular gaps2,2,1. Native PUTreturns1, agreeing with the
model's claimed correct result. That proposed counterexample does not expose a
bug. This is a substantive tracing error, not an output-schema issue.

A reviewer-generated anchor [1,2,3] returns2from PUT, but public spec implies1:
in one simultaneous step both other positions can copy1from a circular neighbor;
zero steps cannot suffice. The actual rounding issue is ceil(max_gap/2) vs the
propagation radius over the intervening positions for odd gaps. The model did
not articulate this correct condition. The anchor was not supplied to the model
and is not counted as a model-discovered test.

**Case124:** raw answer names the loop choosing mismatch positiontand proposes
('abcde','ace'). It claims correct output[0,2,4], with a contradictory explanation
involving two character changes despite the at-most-one rule. PUTreturns exactly
[0,2,4], so the model's own expected would not detect the bug.

Public reasoning gives[0,1,4]: these positions formabe, changed once(b→c)toace.
Index0is minimal, then1is minimal; since that uses the sole mismatch, the third
index must contain e, at4. Thus the model-generated input is domain-valid and
**does expose a real discrepancy under a correct spec-derived expected**, even
though its oracle/causal explanation is unreliable. This is partial localization/
input-generation evidence, not a fully correct fault hypothesis.

A separate reviewer anchor('aab','ab')returns[0,2]from PUT versus public-spec
minimum[0,1]. It illustrates early return at a feasible earlier tmissing a smaller
index sequence using the one change later. Again this anchor is not a model test.

## Bounded verification

All4model outputs froze before native verification. PUBLIC_REVIEW_ANCHORS.json
was written after dispatch but before reading any v72answers; it records the two
reviewer-derived tiny source/spec examples, not private-reference answers.
public_probe_plan/results contain exactly4networkless CPython replays: one model
candidate and one reviewer anchor per raw response, under the registered<=2per
newresponse/8total cap. All4inputs satisfy explicit visible domain constraints;
all executions normal. No private canonical/contract/scorer, substitute program,
reference algorithm or native feedback between model calls was used.

Manual expected values and explanations are explicit in those receipts. They
are owner judgments, not independently adjudicated benchmark labels. The model
candidate and reviewer-anchor provenance remains separate. Raw semantic status:
case85unsupported/incorrectdemonstration;case124partialsignal with wrongexpected.
There are0/2fullysupported raw diagnoses and1/2useful model-generated inputs on
this tiny selected diagnostic. This is not a detection rate for the pipeline.

## What this tells us

- Adding the known-bug premise alone did not yield a full-contract hypothesis on
  these two cases: full_known is empty like both exact historical controls.
  The historical comparison has time/sampling confounds and one sample per case.
- Relaxing to raw diagnosis changes output from empty to prose2/2, supporting a
  task/contract-burden concern. Raw also removes derived AST/clause/schema menus
  and is shorter, so this is not a pure syntax-only causal ablation.
- The raw tracing/spec errors show that fixing JSON is insufficient. Semantic
  reasoning and expected-value derivation remain weak on these examples.
  Case124demonstrates that useful input ideas can exist despite those weaknesses.
- These observations do not prove general model incapability or isolate model
  size from prompt/task effects. A stronger-writer comparison was not performed.
  No automatic larger run or full generator/oracle stage follows this probe.

## Integrity, usage and artifacts

Owner read-only auditPASS32frozenJSONentries,4unique exactrequest hashes, source/
config/protocol/runtime identity, model/tokenizer counts and attempt receipts.
Two historicalv71responses are reused without modification and excluded from new
usage. New calls4,actualdispatches4,unknown0;nativepublicreviewcalls4,privatecalls0.
Six new authored diagnostic tests pass; inherited transport/compiler sources are
pinned unchanged. No independent-agent review claimed. Original v71/v70pipelines
and outputs remain unchanged. Process exited; no active owned job or autoqueue.

See PLAN_FROZEN.json, frozen_artifacts/, terminal_audit.json,
PUBLIC_REVIEW_ANCHORS.json and public_probe_results.json. Semantic assessment is
kept outside the immutable model-output freeze and never overwrites raw answers.
