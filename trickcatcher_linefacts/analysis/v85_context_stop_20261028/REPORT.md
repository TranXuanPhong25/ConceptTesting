# V85 execution stop and continuation — 2026-10-28

The original `comparison_live_1` stopped at10:38:47UTC (17:38Vietnam), after the
previous status check at10:34UTC. PID51658 exited. The endpoint remained live.

Cause: task125, retrieval arm, first strategy-correction request. Its preceding
response exhausted4096 output tokens and ended in incomplete Python. Including
that response in the correction prompt produced4964 prompt tokens. Reserving
another4096 output tokens required9060 tokens, exceeding the8192 context.
The request stopped before completion; its usage is known to be zero.
The reconstructed request matches failure hash
`e823280f015cba110380814a56dd5acb42b7bcdc7fd8500072cd435153d750ec`.
Server tokenization independently confirmed the4964 count; see DIAGNOSIS.json.

Actual terminal progress:113/113 prepared;7 v11 and6 retrieval final rows,
6 complete pairs. The last progress log says5 because a pair completed while
the controller was unwinding the failing future.509 completion attempts all
have received responses; one additional tokenizer/preflight failure had no
completion attempt. Known usage185732 input +39479 output =225211 tokens;
0 unknown usage. No shared oracle requests or target grading occurred.

No method winner can be inferred. Parent source/input hashes226 and original
v11 hashes57 passed verification. Original outputs6054files are frozen in the
child inventory and remain unchanged.

The authorized full113 comparison continues under an explicit amendment in
[v85_contextfit](../../pipelines/v85_contextfit/PREREG.md). Both arms use the
same context allocation: `min(requested_max_tokens,8192-prompt_tokens)`.
Prompts stay complete; the failing request now has3228 output tokens available.
This changes the execution protocol and can shorten long responses. Report
adjusted requests with the final results; do not label it the original protocol.

Imported113 prepared tasks,6 paired checkpoints and all509 successful request
receipts, with exact request identities and inherited cost verified. The original
3503 cumulative attempt cap still applies.31 CPU tests passed (4 transport
regressions plus27 existing fairness, equivalence and native runtime tests).

Continuation PID30096 launched11:12UTC. At the first checkpoint it had passed
model/context preflight, restored6pairs and submitted two new completions,
including the exact formerly blocked correction with the recorded3228 cap.
Live status: `pipelines/v85_retrievalhybrid/out/humaneval/comparison_contextfit_1/STATUS.json`.

11:15UTC verification: the formerly blocked request returned successfully with
4964 input/3228 output tokens (finish_reason=length). The controller advanced to
7/113 pairs;511 received responses in total. Context transport recovery is
demonstrated, but this strategy remains truncated and no efficacy is claimed.

13:05UTC continuation request: PID30096 had exited at12:02:52UTC. Saved paired
generation reached25/113, all113preparations intact,0oracle/scored tasks. There
are575 unique completion attempts:574received,1timeout with unknown usage.
Known usage244999input+50980output=295979tokens. The unknown request is task78
retrieval round1, hash c1bcf735fd22e9e6e0571c0f98ffa6c543ed7b0a0ca31a16c527a49ebd7a0f3f;
it timed out after240.84seconds. A separate tokenize URLError used no completion.
Source/ancestor hashes and all574successful request identities verify unchanged.

At13:06:58UTC a read-only GET/models returnedHTTP404. No new completion calls,
no retry and no duplicate process launched. User was asked to restore endpoint
or provide the updated address.575attempts already count toward3503cumulative
cap, leaving2928attempts; unknown prior usage must remain explicit on resumption.
