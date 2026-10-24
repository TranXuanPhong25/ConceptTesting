# v55 changelog

2026-10-24: registered three-arm Codex dev comparison before any run. Existing
dirty/untracked files belong to other sessions and will not be staged. v55 was
free; latest quota check 99% remaining. Implementation and independent review
pending; no new outcomes computed. Next: isolated writer transport preflight,
prompt manifest, review, fixed-budget generation, scoring; then Task B and C.

2026-10-24 checkpoint: prepared 24 problems/33 dev PUTs, 33 isolated-call
prompts covering 216 oracle answers +48 shared generator/checker answers.
No answer was generated. Manifest records hashes and required entrypoints;
source dependency hashes retained. The preflight used a spec-free prompt and
failed before any model answer with `workspace routing discovery failed`.
One earlier mount setup failure occurred before launching Codex. No retry of
the failed transport and no alternate writer/model was used.

Independent Codex reviewer completed multiple read-only passes. Must-fixes
and append-only Amendments1–2 are in PREREG/REVIEW; five engineering tests
pass and the repository-hidden PID-namespace probe passes. No hidden outcome
or model program was executed. `REVIEW_APPROVED.json` pins the final reviewed
source, PREREG, manifest and dependency inventory. CLI transport/full scoring
remain operationally unvalidated.

Git finding: attempted explicit-file `git add`, failed creating
`.git/index.lock` with `Read-only file system`. No file staged, no commit or
push possible in this permission profile; did not attempt a workaround or
push existing commits belonging to other sessions. Own-file list is captured
in FILES.txt. Existing dirty/untracked work left unchanged.

Task B preparation is in v56_lcb_fresh, conditional on A. Thesis status saved
in ../SUMMARY_v48_v55.md; memory entries/index updated. No A/B efficacy
numbers or claim are available. This is an operational checkpoint, not a
quota stop (initial primary quota was 99% remaining).

Next in an environment permitting Codex transport and Git writes: inspect
this checkpoint; verify pinned hashes/quota; run `experiment.py generate`
using the registered interpreter and PYTHONPATH=. from repo root; no new
budget or repairs. Then `score` only when all accepted calls are present;
audit outcomes/write results/commit owned files to main. Task B requires its
additional adapter/manifest freezes and independent review before mining.

Quota stop: {"timestamp": "2026-10-24T12:14:23.802Z", "remaining_percent": 10.0, "resets_at": 1792854939}; next call defn_0_0.
