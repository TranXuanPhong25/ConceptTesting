# Astra concept/agent diagnostic — quota checkpoint, 2026-10-20

**Latest user amendment:** continue until15%, superseding old20%threshold. On explicit
resume the live quota was already10%, so work/Astra stopped again without Qwen calls.
Old timer cancelled; replacement verified active at the SAME00:46:32Vietnam21Oct,
unit concept-astra-d1-qwen32b-1792518392-15. quota_guard now stops at remaining<=15%.
Historical19%/20%checkpoint below is retained as history; this amendment governs.

User requested Astra improve concepts and propose concrete model tests, then explicitly
requested implementation/audit followed by a run on exact qwen2.5-coder-32b-instruct.
Live Codex5h remaining fell to19%; user instructed stop below20%, so research work and
Astra were interrupted. These files are a DESIGN DRAFT, not a completed/approved runner.

A verified active one-shot systemd-user timer will resume this SAME task at
2026-10-20 17:46:32UTC /2026-10-21 00:46:32Vietnam,120s after reported reset. quota_guard.py
rechecks live quota before continuation and reschedules if still low. Runtime state:
out/agent_schedules/astra_d1_qwen32b/{task_status,schedule}.json. No endpoint is stored.

Endpoint read-only metadata verified exact requested model and max_model_len8192.
One models metadata request;0 completion calls,0 unknown model attempts,0 new PUT calls.
No implementation/preparation/native rows/model run/frozen treatment exists yet.

## Files and remaining work

- catalog.json: Astra proposed7 concepts, human relation+LLM binding+tool-measured gap.
- d1_packets.json:8 seen authored episode construction manifests; strict public catalog
  projection excludes illustrative witnesses/expected values and evaluator metadata.
- d1_evaluator_private.json: private truth/rubric; never render to agent.
- d1_protocol.json:3arms/72single-attempt task turns, bounded tools and go/no-go DRAFT.
- reply.schema.json and reply_examples.json: schema + PRIVATE examples; examples reveal
  witnesses, so a future runner must use an unrelated format-only example instead.
- parent_audit_v28.py / parent_v28_action_audit.json: reproducible read-only frozen-ledger
  audit:69actions,58replay requests,35accepted/33nativechecked,13cases;27errors. This
  corrects any claim that active replay was never tried by a capable model.
- quota_guard.py: read-only account quota RPC and user-authorized same-thread timer.

Before any Qwen task call: finish Astra DESIGN/prior-art/self-audit, independently audit
semantics and controls, validate public/private projection and fixture truths on CPU,
copy best-v7 into a fresh unoccupied version with explicit ports, implement bounded
native/tool/transport ledger with unknown-attempt preservation, run meaningful CPU
checks and clean-context code audit, preregister and freeze. Serial calls; no content
retry/fallback or automatic benchmark/heldout/training. Preserve other sessions files.

Known parent review corrections sent to Astra: no whole-catalog rendering (concrete
examples leak witnesses); distinguish proactive premise rejection from feedback-driven
revision; include v28 prior active replay and count native agreement separately. Source
fixture evaluator for these8 cases is v23_concepthyp.fixture_oracles.expected(case,literal),
evaluator-only. D1 capability does not establish concept utility; generic equality is
no incremental signal. No result or novelty claim from these draft files.
