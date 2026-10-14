# v13_hyp — CPU machinery checks (no LLM)

Design: root `PREREG.md`, "B4 v13_hyp: spec-violation hypotheses". This file reports **only** checks of the CPU
machinery. Real hypothesis counts (parsed / dropped as already tested / witnessed / unwitnessed / mutant-diff) need
the GPU proposal stage; nothing below is a result about hypotheses or bugs.

## What was checked (2026-10-14, Claude)

- 44 offline tests OK (`TEST_RESULTS.txt`), incl. real sandbox checks on a synthetic PUT: an impure T is rejected
  again inside the sandbox; T satisfied by a base input -> "already tested"; T = `x > 50` gets a witness on which
  the PUT differs from a surviving mutant (ranked first); T = `x > 5000` (outside the validator range) is kept as
  unwitnessed (ranked last); the seeded search is deterministic.
- Candidate stage (`hyp_candidates`) on 8 real dev tasks (2, 3, 4, 5, 8, 9, 10, 11): 63 candidate sites, 58 executed
  by base tests (covered sites dominate); 0–11 surviving v4c mutants per task; base_ok on all 8; ~0.6 s per task;
  proposal prompt 400–1040 words.
- End-to-end CPU smoke on task 3 with a hand-written fake proposal: the hypothesis "intermediate balance below zero"
  was dropped as already tested (base input `[1, 2, -4, 5, 6]` satisfies T); T = `len(operations) > 1000` was kept
  unwitnessed, the T-filter gave no input, the LLM-strategy fallback ran twice (fake), calls 3 <= 8.

## Limits

1. **Budget truncation (main).** Per the registered v12 rule, the hyp round-one block is fitted to the task's
   rel-hybrid round-one block. Over the 133 frozen tasks that budget has median 119 tokens (10% 67, 90% 241; 5 tasks
   with 0 hints -> budget 0, hyp-hybrid shows nothing there); 67 tasks < 120, 97 < 180. A realistic block of 3
   hypotheses (R + chain + 7-line T) is ~230 tokens, one hypothesis ~60 vs a median per-hint round-two budget of
   50. So on most tasks the round-one block will be cut mid-hypothesis (prefix truncation, as in v12). Decide before
   the GPU run whether to keep this rule or register an amendment (e.g. whole-hypothesis truncation, or a budget
   that is not tied to the hint count).
2. R matching accepts near quotations (difflib >= 0.9) and records `R_quotation` = exact/near.
3. "Usable filter" is operationalized as: the T-filtered domain draw returns >= 1 valid T-satisfying input; else the
   LLM strategy fallback runs (so unwitnessed hypotheses can still be reached in round 2).
4. Missed = no **valid** round-1 input satisfies T. T that raises counts as not satisfied.
5. Mutant difference is checked on up to 20 witnesses of the 200-draw search (first differing one is the witness).
6. Plain/placebo references stay matched to flat-hybrid's strategy-request count (v12 rule); hyp-hybrid's T-filter
   requests are not LLM requests and are reported as `t_filter_requests`.

## GPU run (dev, after the v11_fair baselines and v12_rel runs finish)

Never write the URL into files; redact logs. From the repository root:

```bash
cd /home/phong/dev/ConceptTester
read -r QWEN_BASE_URL <<'EOF'
<paste the ngrok URL>
EOF
export QWEN_BASE_URL QWEN_MODEL=qwen2.5-coder-7b-instruct
export V4_PYTHON=$(python3 -c "import json;print(json.load(open('trickcatcher_linefacts/pipelines/v13_hyp/config.json'))['V4_PYTHON'])")
export PYTHONPATH=$PWD
curl -s -m 60 -o /dev/null -w "%{http_code}\n" "$QWEN_BASE_URL/models"     # expect 200
mkdir -p trickcatcher_linefacts/out/runlogs_v13
cat > trickcatcher_linefacts/out/runlogs_v13/chain.sh <<'SH'
#!/bin/bash
# B4 v13_hyp dev run. Needs QWEN_BASE_URL/QWEN_MODEL/V4_PYTHON/PYTHONPATH exported (never written).
cd /home/phong/dev/ConceptTester
L=trickcatcher_linefacts/out/runlogs_v13; M=trickcatcher_linefacts.pipelines.v13_hyp.run
red() { sed -E 's#https://[a-z0-9.-]+ngrok[a-z.-]*#<url>#g'; }
step() { local name=$1; shift; "$@" 2>&1 | red > $L/$name.log; local rc=${PIPESTATUS[0]}; echo "$name $rc $(date +%T)" >> $L/steps.txt; return $rc; }
step bundle python3 -B -m $M bundle --reuse-from trickcatcher_linefacts/out \
  --reuse-from trickcatcher_linefacts/pipelines/v11_fair/out/humaneval \
  --reuse-from trickcatcher_linefacts/pipelines/v12_rel/out/humaneval || exit 1
until [ "$(curl -s -m 60 -o /dev/null -w "%{http_code}" "$QWEN_BASE_URL/models")" = 200 ]; do sleep 300; done
step arms python3 -B -m $M arms --arms hyp-hybrid hyp-witness-only flat-hybrid rel-hybrid plain-hybrid toolinput witness-only --k 3 --workers 12 --online || exit 1
step evaluate python3 -B -m trickcatcher_linefacts.pipelines.v13_hyp.eval_longtimeout || exit 1
step oracle_collect python3 -B -m $M oracle-collect || exit 1
step oracle_llm python3 -B -m $M oracle-llm --oracle-stages ref --workers 12 --online || exit 1
step oracle_score python3 -B -m $M oracle-score --workers 12 || exit 1
echo DONE >> $L/steps.txt
SH
setsid nohup bash -c "echo \$\$ > trickcatcher_linefacts/out/runlogs_v13/pid; exec bash trickcatcher_linefacts/out/runlogs_v13/chain.sh" \
  > trickcatcher_linefacts/out/runlogs_v13/chain.out 2>&1 &
```

The `arms` stage first runs the per-task proposal stage (133 proposal calls, logged in
`pipelines/v13_hyp/out/humaneval/generation/hypotheses/proposal_accounting.json`), then the arms. Reused caches make
flat/rel/plain/toolinput requests cache hits where prompts and seeds are identical to v12_rel. Real hypothesis
counts: read `generation/hypotheses/<task>/summary.json` (parsed, failures with reasons, witnessed, mutant_diff,
covered_site). Oracle-score writes `oracle/ref_metrics.json` (B4 pairs) and `oracle/hyp_attribution.json`.
