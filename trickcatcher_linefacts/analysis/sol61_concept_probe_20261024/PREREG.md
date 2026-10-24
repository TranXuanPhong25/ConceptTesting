# Sol6.1 native-subagent concept probe — before any responses, 2026-10-24 +07

User explicitly requests spawning GPT-6.1 Sol on a few tasks to ask whether concepts
help. This is a separate native-subagent probe, not v50 or a Qwen rerun. No endpoint,
paid API, new PUT execution, benchmark expansion, training or historical repair.
No pipeline code changes; prepared packets and analyses live in this separate folder.

Six seen authored fixtures: E2,E3,E4,E6,E7,E8. Selected prospectively from known prior
v40/v43 mechanisms: threshold retention, inclusion direction, empty outcome, two
independent faults, correct masked code, ambiguous spec. This is deliberately not
an unbiased or held-out sample. Original initial hypotheses may be true or false.

Twelve independent fork_turns=none subagents, one episode per agent per arm, requested
model gpt-6.1-sol. No reasoning override (same inherited setting in both arms). No
model substitution/retry. At most3 concurrent solver agents. Single reply each;
no tools/files/network/other-agent use instructed. Tool availability is not removed
by the host; inspect actual solver turns for compliance. Noncompliance stays visible.
Reviewer agents are separate and not solver responses. Raw origin must remain Sol,
not Qwen/Luna/Astra. Usage unknown unless exposed by actual transport/session logs.

Both arms get identical spec/code/base tests, fallible initial hypothesis and ALL
saved v43 pool observations for that case (not only displayed witnesses). No hidden
fixture verdict, expected binding or per-task concept chosen by the author. Both
receive the same output request and target <=450words. Concept arm gets the SAME
7 generic relation/operational-axis cards for every task; generic-control arm gets
a prose reasoning checklist of roughly matched length. No filled per-task binding,
code-specific bug hint or concrete counterexample in either added guide.

Arms compare concept-card content against generic reasoning help, not against an
empty prompt. Packet lengths reported; no exact token budget/effective reasoning
budget matching claim. One-shot final: requirement, implementation hypothesis,
keep/revise/withdraw/unknown initial hypothesis with reason, judgment, citations and
up to2 input tuples that discriminate stated competing behaviors. Predictions are
fallible hypotheses, not expected-value assertions. Missing/invalid fields reported
individually; no whole-answer gate or repair/model retries.

Primary semantic success (independent reviewer, all6 per arm): correct spec relation,
correct supported implementation hypothesis/revision and final judgment; no invented
requirement or false bug. E2 inclusive count despite strict code; E3 subset with
container extras; E4 explicit None fallback versus exception; E6 include1 AND each
positive occurrence; E7 return sorted(xs) preserves duplicates despite unused set;
E8 suitability undefined so no unique normative violation. Proper abstention E8 is
success, unknown E7 is safe but incomplete. Initial→final decisions must be logically
consistent; exact requested labels/JSON formatting are secondary.

Report every task/arm including failure/abstention, explicit false alarms, input
quality and whether inputs separate two named hypotheses. Source/manual input
adjudication only, no actual new PUT executions. Novelty against full per-case saved
pool and entire eight-case saved input pool, separately; novel is not discovered bug.
Candidate-output predictions are not assertions. No adaptive query/feedback run.

Evidence rule: >=2 genuine concept-only semantic wins/0 opposite losses, no extra
false alarms, both controls right would justify investigating this package further.
Anything less means advantage NOT SHOWN in this probe. All12 correct is a ceiling
for this diagnostic, not concept gain. No enlarging sample or re-prompting to rescue
negative results. Comparing to Qwen historical scores is descriptive only: model,
agent harness, prompts, schemas, calls and evidence schedules differ.

Freeze packet hashes, guide text, mapping, rubric and source manifests before any
solver call. Independent clean-context packet/design audit before outcomes. Preserve
raw final responses verbatim plus requested model/agent identity, instruction, turn
status, exposed usage and observed tool calls. After all12 responses freeze them,
then independent clean-context semantic adjudication before report/commit/push.
Quota fresh>15 to launch; stop<=15, preserve completed outputs and unused slots.

## Prelaunch transport clarification

Each solver may perform exactly one read-only load of its assigned packet file;
this is input delivery, before obeying the packet's no-tools solving instruction.
No other files, memory, code execution, network, other-agent calls or edits. This
same delivery exception applies to both arms; record that file-read tool use rather
than claiming tools were disabled by the host. Final replies remain unmodified.
No extra reasoning turn or retry after invalid output. Freeze PREREG/prepare/manifest
hashes in prelaunch.json as requested by independent design reviewer. Input-reading
only is not a test tool or a dynamic feedback experiment.
