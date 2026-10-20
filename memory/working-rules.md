---
name: working-rules
description: All operational rules from the user for this repo (language, git, secrets, GPU endpoint, folders, PREREG, Codex/Claude split)
metadata:
  type: feedback
---

Consolidated from many sessions (Claude, through 2026-10-14). Details and reasons in the linked memories.

**Communication:** reply in Vietnamese sentences with technical terms in English, B1–B2 level ([[reply-vocabulary]]).
The user gets angry at English replies and at unrequested fixes ([[dont-fix-unasked]]).

**Git:** `AGENTS.md` rules (no AI attribution lines, push to main, no paper reimplementation without approval, keep
vendor/ untouched, one folder per paper, keys via `scripts/*_env.sh`). In `trickcatcher_linefacts/`: commit + push your
own files after each finding, even negative ones; elsewhere only when asked ([[commit-only-when-asked]]). Never stage
files you did not write (other sessions leave untracked files, e.g. AUDIT_*, diagrams/, research/, pipelines/v12_outcome_audit).

**Secrets / endpoint:** never print or write the ngrok URL or keys into repo files or logs. Pass the URL through a
heredoc (`read -r QWEN_BASE_URL <<'EOF' ... EOF`) and export `QWEN_BASE_URL`, `QWEN_MODEL=qwen2.5-coder-7b-instruct`;
redact logs with `sed -E 's#https://[a-z0-9.-]+ngrok[a-z.-]*#<url>#g'`. Ask the user for the URL if unknown. Check
liveness with `curl $QWEN_BASE_URL/models`. **Never edit the Kaggle notebook** (`trickcatcher_linefacts/kaggle/`).
Keep a ping loop (every 20 min) during long runs so the notebook does not idle-kill; space out polling.

**Runs:** long GPU runs detached so the session can close: `setsid nohup bash -c "echo \$\$ > pidfile; exec bash chain.sh" &`
(track PIDs; never `pkill -f` patterns that match your own command). Env: `PYTHONPATH=<repo root>`,
`V4_PYTHON=` the dedicated venv in `pipelines/<v>/config.json` (Hypothesis 6.169, mutmut 3.8, coverage 7.16, libcst).
Baselines tests use `CoverUp_concept/.venv/bin/python -m pytest` (has httpx + pytest).

**Folders:** every change to a pipeline goes in a **new folder** copied from the best one, with a `CHANGELOG.md`
(what changed, files, commits, status) — never edit the best folder in place ([[pipeline-folder-workflow]]).

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
