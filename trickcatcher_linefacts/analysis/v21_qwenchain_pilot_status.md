# Qwen chain controlled16 — live run status

2026-10-16: user explicitly authorized calls on their Qwen endpoint. New frozen v21_qwenchain_pilot copy from offline P1.74 offline/preflight checks passed; two independent reviewers accepted transport/alias/fixture contracts before first completion. Actual generation started detached; stage responses and physical completion/token logs under out/pipelines/v21_qwenchain_pilot/humaneval/qwen_chain_pilot. Controller/PID/status under out/runlogs_v21_qwenchain_pilot.

Pinned model qwen2.5-coder-7b-instruct, context16384. Official Qwen chat template pinned and raw server tokenization used; observed completion prompt usage matches preflight. Maximum80 scheduled slots/240physicalattempts, controlled16 only. Human semantic gate pending, no real20 or D_IO. Callback queues result review after completion/stoppage. Never start a duplicate controller or reset attempts; no mid-run prompt/validator/budget edits.

Early S1/S2 failures include bare item or copied contract description instead of the requested envelope. These observations do not measure downstream alignment. Final result must be read from the frozen completed report, not this live note.

## Final

Controlled16 completed,32 real completions,35169 input/11946 output tokens. S1 and S2 each0/16 schema-valid; S3–S5 blocked. Source/generation hashes verified. Main interface failures:12 bare S1 items,4 S1 contract copies,16 S2 contract copies. No D_IO or semantic-accuracy claim. See v21_qwenchain_pilot_results.md/json. Source/prompts/validators/results remain frozen; any prompt-only follow-up is a distinct registered copy/result.
