# v75 DeepSeek-V4-Flash concept selection (v47 replay, third model)

Written 2026-10-25 before any v75 model output. User request: "dùng thử deepseek với provider này" (relace/fp4),
after v74 (GPT-OSS-120B no-go, 15/14 vs random 18.25/17.96).

Identical to v74 PREREG (frozen v47 menus copied byte-identical, v47 prompt/parser/scorer, 33 vibepass_half PUTs,
temperature 0, seed sent but relace does not support it) except:
- Model `deepseek/deepseek-v4-flash-0731`, OpenRouter provider `only: ["relace/fp4"]`, `allow_fallbacks: false`,
  `reasoning: {enabled: true}`, max_tokens 8192, no response_format. Single-turn (no reasoning_details carry-over:
  each selection is one call). Cost cap $0.20. Output `out/analysis/v75_deepseek_select/`.

Rule unchanged: promising iff spec+code covered@3 ≥ random3 + 3 AND ≥ 0.5 × perfect_menu. One run, no rerun.

## Amendment 1 (2026-10-25, before any pick was produced or scored)
Attempt 1 (`reasoning: {enabled: true}`, max_tokens 8192): 31/31 calls finish=length with empty content ($0.0457);
the run then crashed on a non-JSON OpenRouter body. Raw probes on case 3 spec-only (scratchpad, not scored):
enabled + 32768 → still length, 83k reasoning chars of hand-enumerated examples (not a loop); effort low → ignored,
length; reasoning max_tokens 2048 → stop with valid picks; disabled → stop. Probe cost ≈ $0.0096.
Change: `reasoning: {max_tokens: 4096}`, max_tokens 16384. Attempt-1 records kept in `calls_attempt1_enabled_8192/`
(never scored). Everything else unchanged; cap $0.20 for attempt 2.

## Amendment 2 (2026-10-25, user: "cứ mở giới hạn token lên là được")
Attempt 2 had 28/66 finish=length with empty content (provider ignores reasoning.max_tokens). Attempt-2 score kept as
`score_attempt2.json` (no-go, 10/12). The 28 length records moved to `calls_attempt2_length16384/`; only those 28
are re-called with max_tokens 65536 (timeout 3600 s), same prompt/reasoning settings. The 38 stop records stay: they
ended below the 16384 cap, so a higher cap would not change termination. Cap $0.40 for this step (spend counter
starts from the 38 kept records' $). Calls still at length after 65536 stay empty (not covered). Rescore once.
