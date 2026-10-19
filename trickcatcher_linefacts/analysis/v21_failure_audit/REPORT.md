# v21 mechanism audit — 2026-10-19

This is a retrospective audit of existing frozen outputs, following the user's “tiếp tục”. No new model, PUT or reference execution. See PREREG.md for post-hoc scope and audit.py/audit.json for reproducible counts.

## Verification and what changed in our interpretation

All 352 diag16 and 437 pilot20 frozen-file hashes and all current frozen source hashes are checked by the script. Reconstructed per-input confirmed/false-alarm/wrong-expected totals, using only saved canonical execution results, match score.json exactly. Published detection numbers are unchanged. The earlier report's “few errors” description of agent tools was too broad: pilot20 has 16 errors in 40 actions.

| Actual agent usage | diag16 | pilot20 |
|---|---:|---:|
| All actions |35|40|
| inspect_flow |31|38|
| inspect_data |2|2|
| replay_input |1|0|
| check_path |1|0|
| Error actions |2 unknown_id|16 ids_shape_or_count|
| Cases repeating the identical nonempty query list in both rounds |12/16|16/20|
| Explicit hypothesis-ID links on actions |0|0|

Pilot20's 16 errors occur on eight tasks (0,43,70,77,84,90,105,131), twice per task. inspect_flow accepts at most4 IDs through FlowSession._ids/max_names. The prompt's TOOL_PROTOCOL lists `ids:[...]` but does not disclose this cap; the agent output schema accepts any object, without tool-specific field limits. These are an underspecified interface plus model failure to recover, not evidence that inspecting CFG cannot help. No pilot20 agent actively replayed an input or checked a path. Common witness traces were already available, so zero replay does not mean the model had zero execution evidence.

## Hypothesis grounding and observation limits

- Pilot20 has24 mismatch hypotheses across19/20 tasks.5/24 contain at least one unmapped source line; none loses all source IDs. Mapping drops missing lines into `unmapped_lines`, but the rendered hypothesis omits that diagnostic. It therefore weakens source provenance without warning the generator.
- The online shared schema extracts one central relation and uses O1 for every hypothesis. It does not require a quoted spec span.0/20 pilot concepts and0/16 fixture concepts have a quote field. Every arm still sees the original spec; this is missing claim-specific grounding, not missing spec context.
- Trigger is free text. There is no compiled predicate check or template validation establishing that the chosen input satisfies the claim. A guard/site hit is not output propagation.
- Frozen hypotheses are never updated by a structured keep/revise/withdraw artifact. Two agent replies contain actions/reason; the final reply contains tests/reason. A final explanation can change, but it does not provide an auditable hypothesis-revision result.
- Fixed replay observations take only the first4 distinct hypothesis source IDs.7/20 tasks have more IDs, so a relevant later node can be omitted. Final executions request no hypothesis-specific observations. All28 common pilot inputs have checked native agreement and complete proven traces; usable baseline tracing coexists with incomplete claim-specific observation.
- Runner code trims feedback histories to the first3 results/round when serialized history exceeds12,000 characters. Full records stay on disk and an omission count is shown; which facts/counterevidence the model loses is not semantically controlled. This is a design limitation, not a measured explanation of any particular failure in this audit.

## Illustrative saved cases (post-hoc, not an accuracy sample)

**Task90, next_smallest.** Hypothesis cites line22, `return min(lst)`, and proposes `[1,1]`. Source guards at lines18–20 return None for equal length-two values before reaching line22. Saved final tests for concept+hyp, agent-tools and toolinput all return None, with canonical None and expected None. The input does not distinguish the faulty min branch. The second hypothesis even describes `0**0` as zero, although it is one; its trigger is unevaluated prose. Real code defects exist, but these proposals do not establish their activation.

**Task131, digits.** Hypothesis says all-even input2468 fails the required zero case. Saved replay/final outputs are0 and cached canonical is0. The actual source's return at line14 gates product on the first digit; mixed input beginning with an even digit is the relevant suspect family. The fixed observation cap can exclude line14 because the hypothesis lists lines10–14. These are three separable issues: wrong concrete claim, wrong discriminator, and insufficient observation selection.

**Task116, sort_array.** Hypothesis says decimal tie ordering is absent; source line19 contains `sorted(y)` within each bit-count bin. The original docstring also says nonnegative inputs but includes a negative example whose stated result conflicts with cached canonical behavior. Five arms reproduce that exact example's expected `[-6,-5,-4,-3,-2]`; PUT and canonical both return `[-4,-2,-6,-5,-3]`, so the registered scorer labels them false alarms. Preserve the scores, but do not classify these five events as pure arithmetic/expected-value inability: contradictory supplied specification evidence is involved. The mined filter accepts the input and does not resolve normative ambiguity.

**Task82, prime_length.** The hypothesis correctly notices a fixed prime list ending29, but proposes a string of length21. Twenty-one is composite; it cannot distinguish the intended primality requirement from the literal prime list. This case illustrates why a plausible hypothesis needs a separately checked discriminator.

Further source snapshots for0,108,143,151 are retained in audit.json for review, without inventing an aggregate semantic-accuracy label.

## Next increment

Fix only the bounded tool contract first, then perform a separate controlled diagnostic if warranted. Copy best v7 to a fresh folder and record v21 ports. Publish per-tool schemas/caps, structured error details and model-visible previous-slot failures; preserve the12-action/2-round ceilings. Do not force a replay or alter hypotheses/rewards in the same increment: that would conflate interface repair with adaptive policy and semantic reasoning changes.

Later, independently reviewed claim/discriminator packets and explicit hypothesis revision remain needed to test the full planned mechanism. Existing v26–v29 already explore oracle/model limitations; this audit does not rerun them. The current negative/inconclusive v21 result remains a result for the implemented package. It does not demonstrate the efficacy or failure of a successfully executed hypothesis→path verification→revision mechanism.
