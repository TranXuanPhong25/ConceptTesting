---
name: working-rules
description: All operational rules from the user for this repo (language, git, secrets, GPU endpoint, folders, PREREG, Codex/Claude split)
metadata:
  type: feedback
---

Consolidated from many sessions (Claude, through 2026-10-14). Details and reasons in the linked memories.

**Quyền chạy (user nhắc lại2026-11-08):** người dùng quyết định mọi lần chạy
experiment/evaluation/inference. Mặc định chuẩn bị code/preset/config rồi để
người dùng tự bấm Run; agent chỉ launch/schedule/resume/rerun khi có lệnh rõ ràng
cho run đó và trong scope/budget được cấp. “Check” chỉ kiểm tra trạng thái/kết quả,
không cấp quyền chạy thêm. Run đã được cho phép xong thì report và chờ quyết định
tiếp theo. Rule9AGENTS.md;không tự mở rộng benchmark hoặc chain thêm experiment.

**Communication:** reply in Vietnamese sentences with technical terms in English, B1–B2 level ([[reply-vocabulary]]).
The user gets angry at English replies and at unrequested fixes ([[dont-fix-unasked]]).

**Prefect/report (user2026-11-08):** publish authorized experiment/evaluation runs
with config/progress/results/report to local Prefect; reuse flow IDs per source,
verify artifacts and provide a direct run link. Reports/explanations in Vietnamese,
technical terms and existing schema fields in English. Explain metric units and
denominators; incomplete metrics remain pending. Cleanup requested by the user
backs up metadata and preserves source outputs/checkpoints. See AGENTS.md rules7–8
and [[run-console]].

**Input/output contracts (user2026-11-08):** fix routine serialization/schema/
adapter contract failures autonomously and rerun authorized work; do not stop
to report these failures as the result. Preserve old artifacts and internal
amendments, keep semantic checks and budgets intact. See
[[repair-io-contract-autonomously]].

**Flow explanations (user2026-11-07):** use visualization skills to draw a linked HTML graph when the user asks about a flow; do not output text/ASCII flow diagrams. Keep the requested module scope. See [[flow-diagrams-html]]. Explain each stage's mechanism, input/output and LLM/parser responsibilities with concrete examples; stage names or dependency edges alone are insufficient (user correction2026-11-07).


**Git:** `AGENTS.md` rules (no AI attribution lines, push to main, no paper reimplementation without approval, keep
vendor/ untouched, one folder per paper, keys via `scripts/*_env.sh`). In `trickcatcher_linefacts/`: commit + push your
own files after each finding, even negative ones; elsewhere only when asked ([[commit-only-when-asked]]). Never stage
files you did not write (other sessions leave untracked files, e.g. AUDIT_*, diagrams/, research/, pipelines/v12_outcome_audit).

**Secrets / endpoint:** never print the ngrok URL or keys into logs, and never write keys into repo files.
User exception (2026-11-08): the endpoint URL may be hardcoded only in the single
`scripts/ping_endpoint.sh`, explicitly requested together with removing its env-file dependency.
Do not inspect credential-bearing env files with cat/read commands that emit their
contents into tool output; load scripts/research_env.sh and other key env files
only by silently sourcing for authorized runs. Reviewer tasks have the same rule.

Pass the endpoint through a
heredoc (`read -r QWEN_BASE_URL <<'EOF' ... EOF`) and export `QWEN_BASE_URL`, `QWEN_MODEL=qwen2.5-coder-7b-instruct`;
redact logs with `sed -E 's#https://[a-z0-9.-]+ngrok[a-z.-]*#<url>#g'`. Ask the user for the URL if unknown. Check
liveness with `curl $QWEN_BASE_URL/models`. **Never edit the Kaggle notebook** (`trickcatcher_linefacts/kaggle/`).
Keep a ping loop (every 20 min) during long runs so the notebook does not idle-kill; space out polling.

**Runs:** long GPU runs detached so the session can close: `setsid nohup bash -c "echo \$\$ > pidfile; exec bash chain.sh" &`
(track PIDs; never `pkill -f` patterns that match your own command). Env: `PYTHONPATH=<repo root>`,
`V4_PYTHON=` the dedicated venv in `pipelines/<v>/config.json` (Hypothesis 6.169, mutmut 3.8, coverage 7.16, libcst).
Baselines tests use `CoverUp_concept/.venv/bin/python -m pytest` (has httpx + pytest).

**Folders (latest user clarification2026-11-01):** implement new versions/arms in
the existing code, without copying a new version folder. Leave changes uncommitted
for user review. This supersedes the old new-folder-per-method rule. Keep separate
arm modules/stage classes, record changes in the existing CHANGELOG, and preserve
checkpoints/results; distinct run configurations still use separate output data
directories ([[pipeline-folder-workflow]]).

**Science:** register in `PREREG.md` before running (append-only; amendments dated, before reading outputs). Dev (113)
for design, pilot (20) reported separately, held-out (VibePass, MBPP+ real-12) run once with a frozen config. Always
compare with plain-hybrid (matched calls), placebo (matched requests), toolinput and witness-only; matched counts by
random subsets, not prefixes. Prefer standard libraries when results are unchanged ([[prefer-standard-libraries]]).
Concepts must stay central ([[thesis-concept-requirement]]). Paid API budget is tiny: ask first ([[api-budget]]).

**Who does what:** large implementation → Codex (background); small fixes, analyses, GPU runs, writing → Claude.
If Codex quota is out → Claude subagents ([[codex-quota-fallback]]). Codex sandbox has no network/LLM; Claude runs
real LLM calls. After a new variant, Claude updates the diagram artifact ([[version-tree-diagram]]).

**OpenRouter secret rule (user2026-10-19):** read scripts/openrouter_env.example.sh only; scripts/openrouter_env.sh must NEVER be inspected/printed, only sourced silently for authorized runs. Key stays process environment, never logs or commits. User authorized ~30-task qwen/qwen3.5-35b-a3b feasibility run, not unlimited spend/fallback.

**New directions (2026-10-20):** before proposing/building one, check the version tree (v7…v35) and name the earlier
version that tried the same core idea and its result ([[check-version-tree-before-proposing]]). Borderline result →
look for a go/no-go signal in existing outputs; never enlarge runs to salvage it ([[signal-not-more-data]]).

**Endpoint keepalive (user update 2026-11-08):** use only `scripts/ping_endpoint.sh`;
remove the duplicate `final/ping_endpoint.sh`. URL/model/interval are hardcoded in
the script, no env file or environment variables required. Preserve the current
600-second interval. GET /models + 1-token chat; logs contain status codes only.
This supersedes the 2026-10-20 env-file requirement for keepalive only; other
runtime/API credential rules remain in force.

**Retrieval version names (user2026-10-29):** new retrieval/concept-gate experiments use `vr8`, `vr9`, ... rather than LineFacts `vNN`. Preserve earlier names/history; current implementation folder is `trickcatcher_linefacts/pipelines/vr8_semanticgate`.

**Review before running (2026-10-21):** after implementing a new experiment, spawn an independent read-only review agent (practicality, tricky implementation, correct library use, plan adherence) and apply its must-fixes as a PREREG amendment before any outcome is computed.
