# v19_rulegen — 2026-10-15

User authorized implement and run matched rule-first generation comparison.
Code/preregistration complete. CPU checks:38 passed. Frozen representation17/20; rule-first concepts13/20; gate passed.
Same20 dev tasks, K=1;300 generation requests maximum across five LLM arms, plus witness-only.
Primary behavior+concept vs behavior; plain/placebo/toolinput/witness-only controls; equal-input random subsets.
No gold-driven model replacement, no new reference model calls. Candidate-property false alarms separate from D_IO.
Launch attempted: metadata endpoint HTTP404 / ERR_NGROK_3200. No generation requests sent, no D_IO results.
Run with the dedicated interpreter via analysis/run_rulegen.py after source scripts/research_env.sh and providing a live QWEN_BASE_URL in environment. Detached controller includes metadata keepalive and completion notification.
Exact protocol/pre-gold inputs frozen under pipelines/v19_rulegen/out/humaneval/behavior_smoke; do not modify source/config/guidance on resume.

User subsequently authorized waiting about10 minutes for the same endpoint to return. Detached analysis/wait_rulegen_gpu.py checks metadata every60 seconds, maximum2 hours, requires pinned model ID, verifies frozen protocol and launches unchanged controller automatically. Waiter status/PID under out/runlogs_v19_rulegen; controller handles completion notification. No GPU requests until readiness.

## Completed

GPU returned; all generation and scoring complete, exit0 (13:22–13:51 Asia/Ho_Chi_Minh). Frozen artifacts verified; no missing work to resume. See v19_rulegen_results.md/json and RESULTS §11.53. Prior waiting/offline entries above are historical.
