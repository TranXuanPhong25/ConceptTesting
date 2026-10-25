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

2026-10-25 (Claude): user instruction to run v56 on new Qwen2.5-Coder-32B endpoint (URL in private
chmod-600 env file only). Downloaded pinned LCB test5/test6 (rev 0fe84c39, newest official release_v6).
mine.py manifest: 110 eligible functional LeetCode after excluding 34 VibePass IDs; newest 60 =
2025-01-04..2025-04-05 (19/25/16), all after the Qwen2.5-Coder-32B release. Amendments 1–3 appended.
Independent Codex review: BLOCK (4 must-fix) → fixed → BLOCK (2) → fixed → APPROVE (no must-fix).
Mining only; pipeline-arm freeze (writer/arms/controls) is a separate later amendment. No PUT yet.

## 2026-10-25 — mining run (Qwen2.5-Coder-32B-Instruct-AWQ, max_model_len 8192)
generate: 120/120 records; 119 ok, 1 final `read_error` (3709 attempt 1, server stall 1823 s; not resent).
evaluate (evaluation.json sha256 19b22d05…, cohort.json 0297b786…): attempts public_fail 60,
hidden_pass 36, hidden_fail 15, timeout_only 8, no_response 1; harness 0, exc 0.
Cohort (first hidden_fail per problem) = 11/60 problems: easy 2, medium 6, hard 3
(3750 3788 3784 3705 3770 3776 3771 3677 3720 3562 3634); all failures are wrong-output
(3784 also 5 TLE). Mining cap reached; no enlargement. Pipeline arms not frozen/run.

## 2026-10-25 — pipeline-arm freeze (Amendments 4–8)
User: writer = Qwen2.5-Coder-32B; scoring reference = Codex certified reference (LCB has no reference solution).
`arms.py` (sha256 289570e6ad1ab493…): Codex reference/validator certified on all tests; Qwen defn/brute/plain k=3 + plain
input generator + open checker (121 calls); public ∪ fuzz tool ∪ LLM inputs; v49 primary quorum, cap 20; bubblewrap
fork-per-input sandbox. Codex review BLOCK(7) → BLOCK(5) → BLOCK(2) → APPROVE. No reference or arm outcome yet.

## 2026-10-25 — reference + arm run + score (frozen, no change)
ref: Codex references certified 11/11 (attempt 0); validators 10/11 (3784: 3× rc=1 turn.failed, not resent →
"reference does not raise"). generate: 121/121 Qwen calls saved ok. score: defn 5 tasks prec .918 FA 5; brute 6 .51 FA 47;
plain 4 .41 FA 36. defn vs brute 0–1 NO-GO; brute vs plain 4–2 NO-GO; defn vs plain 3–2 NO-GO. See RESULTS.md.
