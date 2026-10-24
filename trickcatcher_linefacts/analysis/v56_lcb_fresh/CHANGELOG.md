# v56 changelog

2026-10-24: fresh-cohort protocol registered; execution remains conditional on
Task A, pinned source/manifest, adapter and independent review. No PUT generated,
no new public/hidden tests executed, no cohort outcome. Task A's isolated Codex
preflight failed before any model answer (workspace routing discovery failed).

Infrastructure found: `analysis/vibepass_feasibility.py` decodes LCB private
tests in a restricted child, applies official-style equality, and checks
public-pass/private-fail; `heldout/vibepass.py` creates functional wrappers;
`pipelines/v34_ftplacebo/ft_run.py` supplies the dev runner interface;
`HELDOUT_RUNBOOK.md` documents freeze/scoring boundaries. Do not invoke their
old fixed-output entry points for the new cohort and do not modify them.

Sourced research env and both existing private endpoint env files silently.
Endpoint A GET /models: URLError; endpoint B: URLError caused by gaierror.
These establish local connectivity failure, not proof that a GPU is offline.
No completion requested from either GPU. URLs and keys were not printed or
stored. Existing local LCB caches are filtered to original VibePass questions;
the only other cached Arrow data found has student-feedback fields, not LCB.

Official source inspected through web: dataset loader currently defines v1–v6
and release_latest using test.jsonl through test6.jsonl. No exact cutoff for
gpt-6.1-sol was established; a post-cutoff claim is not justified. Metadata
preparation does not authorize reading fresh hidden outcomes before the gates.

Next: restore Codex transport; finish A; pin/download fresh official LCB data,
exclude all VibePass identities, prepare adapter without executing outcomes,
obtain independent Codex review, append freezes, then mine exactly the fixed
budget and evaluate frozen paired arms. No automatic enlargement.
