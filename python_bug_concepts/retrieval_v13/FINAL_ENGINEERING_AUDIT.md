# Final engineering integrity audit

2026-10-29,16:53UTC. Read-only checks passed. Frozen runtime and outcomes were
not modified. No new grade/semantic-review queues or RESULTS files were opened;
historical frozen input artifacts were hashed only. No model inference, HTTP
request, controller launch or target execution was performed.

| Check | vr11 | vr13 |
|---|---:|---:|
| Frozen runtime files verified |38/38|38/38|
| Frozen evaluation source/inputs verified |12/12|12/12|
| Authored engineering tests passed |15/15|26/26|
| Stored source queries |28|28|
| Source identity matches,4arms/query |112/112|112/112|
| Candidate objects identical to cached V7 control |112/112|112/112|
| Packet model identities match fixed manifest |112/112|112/112|
| Review approval and run receipts match current freezes |PASS|PASS|
| Prediction seal verifies |PASS|PASS|

Both copies have byte-identical dense.py and MODEL_MANIFEST.json. All9pinned
local model artifacts were hashed and verified, without loading the model.
Model: `jinaai/jina-embeddings-v2-base-code`, revision
`516f4baf13dec4ddddda8631e019b5737c8bc250`. Identity:
`e9791680f9321f102812040951d91d9233e1559f40d761b26561bf18789cf8d1`.

Runtime freeze SHA256:

- vr11: `e864ed7f6bac626042a76a5298b49fa4429c98693f56cc918dfd9efdf72d0b3e`.
- vr13: `c258ac2c4c80985df62642e0a195da7dd348c59a2780bc1031238bc2b34e4a7a`.

Prediction SHA256:

- vr11: `753b8a181ea5c3b71cf1b62a96920ec36e413ec68ac82f3ae0e4784860eaf6eb`.
- vr13: `db316dd0f4403b7837b6b807539ec7362394f0968852cb657430adf3def88d91`.

The original V7 prediction seal also verifies. Full manifest/evaluation hashes
and checks are recorded in FINAL_ENGINEERING_AUDIT.json.

Vr12 local check independently verified79/79frozen source/input files and64/64
parent files. Approval matches freeze
`f5203c91de991ae64a19428723106d50da89735b185a9046552e2beeb447afd5`.
No active controller invocation was found through `/proc`; no local generation,
attempt or completion-receipt artifact exists and no complete marker exists.
Saved stage is blocked/RuntimeError. This agrees with the prior terminal audit's
zero new completions; stale status/PID alone was not used as process evidence.

These findings establish engineering integrity only. They do not validate semantic
applicability, proposal-quality gains or downstream bug detection. Blinded semantic
review remains separate.
