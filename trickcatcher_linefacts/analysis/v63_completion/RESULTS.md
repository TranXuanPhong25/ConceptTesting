# v62→v63 completed engineering continuation — 2026-10-25

Generation and independent scoring completed:108responses/108physicaldispatches,6case results,778frozenJSON entries. Exact readiness, original47JSON and imported40files, source/evaluator identities and allfreeze hashes verified. v63 preserves6v62writers and5construction checkpoints;102newarmcalls followed reviewed repair. This is one interrupted-and-continued pilot, not an independent replication. SixPUTs coverfiveproblems (61/66 share3701).

## Five-arm outcomes

Each arm has36raw final slots. Scores remain `provisional=true`, `review_required=true`: artifact/implementation review does not independently re-adjudicate every private validity/reference label.

| Arm | Confirmed bug cases | Confirmed slots | Bug-revealing input, wrong expected | False alarms | Invalid | Unresolved parse | Passing |
|---|---:|---:|---:|---:|---:|---:|---:|
| Plain |0/6|0|3|3|3|0|27|
| Explicit pattern |1/6|1|7|1|6|6|15|
| Concept |0/6|0|3|3|3|0|27|
| Equal evidence raw |0/6|0|4|3|3|0|26|
| Inputs only |0/6|0|3|3|3|0|27|

Only explicit_pattern confirms case85/problem2920: input([1,2,3,4,5,1],), expected2. At unique-problem level pattern1/5, others0/5. No concept-only win. Public-example-only baseline19/19passing,0confirmed. Do not call this a reproduction of the trained UTGen model; explicit_pattern adapts the author prompt.

## Admission and actual realization

Writer18proposals→14admitted across6cases;4rejections:two unsupported predicate operators, one external/keyword alternative call, one GeneratorExp alternative. Unlike v61's18/18rejection, treatment was instantiated, but source/schema admission is not semantic correctness.

| Case | Admitted | Candidates | Native-realized runs | Sensitive runs |
|---|---:|---:|---:|---:|
|61|1|0|0|0|
|66|3|64|24|0|
|124|3|32|0|0|
|58|3|64|3|0|
|131|2|32|30|1|
|85|2|50|0|0|

Gate passed:6admittedcases,3native-realizedcases,1sensitivecase.57realized construction runs are descriptive, not proof of57valid bug-revealing inputs. Checkpointed construction reports1124nativeexecutions (1024imported+100case85recovery); historical uncheckpointed v62case85 CPU usage remainsunknown. Module-scope repair produced25explicitunsupported candidate records with0native calls for that hypothesis; it no longer crashes.

Critical semantic limitations from saved artifacts:

- Case124allthree event predicates are literalFalse: those hypotheses cannot realize the requested event.
- Case131both alternatives are the Python expression string`"None"`, not JSONnull. Replacing a modulo expression byNone causes output1→0 on('6',), but supplies no justified correct repair or evidence that originaloutput1 iswrong. Never reinterpret that received string as abstention after the fact.
- The only sensitive construction witness('6',) is qualifyingindex3. Existingfirst-two display policy shows('7',),('9',) and('8',),('4',), allnonsensitive. Thus the gate has a sensitive witness somewhere, but no sensitive witness was actually delivered to the generator. This is a disclosed selection limitation, not evidence the concept mechanism succeeded semantically.

Final audit rechecks inputs, without transferring prior certificates:

| Arm | Realized final inputs | Realized hypothesis/input pairs | Sensitive pairs | Native executions |
|---|---:|---:|---:|---:|
|Plain|17|30|2|336|
|Explicit pattern|10|14|0|240|
|Concept|18|33|2|336|
|Equal evidence raw|18|32|2|336|
|Inputs only|19|35|2|336|

Sensitivity again means behavior differs from an unverifiedalternative, not a confirmedbug. Concept reaches hypotheses but gains no confirmedtest. Finalpositive sensitivity is shared with controls. The practical failures include weak/nonrealizable hypotheses, evidence selection, and wrong expected outputs; this pilot does not establish general concept inefficacy.

## Errors, integrity and usage

105stop/3length completions. Allthree truncations are case131explicit_pattern plan/probe1/final; final yields6unresolvedparse slots. Probe feedback420entries:408ok/12malformed; no saved branchcap or PUT-output instrumentation errors. No transport failures, retries or unknown model completions. No missing case or duplicate controller.

108distinct request hashes match their response and actual attempt receipts; all30finalrequest hashes distinct. Plain/concept/inputs_only final test lists match exactly for124/58, not the otherfour cases. No application cache collision evidence; remote server independence cannot be proven from client receipts alone.

Actual model usage415420input+32247output=447667tokens; exactserver tokenizer agrees108/108. Historical6writers33560+3228=36788tokens countedonce;102newcalls381860+29019=410879tokens. The sharedwriter is reported separately and allocated as one logical planning call to deep/raw/input packages; do not sum replicated per-package allocations as physicalcost. No monetaryprice inferred for the notebookendpoint.

Independent read-only reviewer confirms the caveats, integrity and counts; see REVIEW_COMPLETION.md. Originalv61/v62code/artifacts unchanged. No modelcalls or new experimental runs were made during this terminal audit. Runner/supervisor exited; exact30minuteobserver retired after user-requested manualcheck, so no stalecallback remains. No automatic cohortexpansion/newrun.
