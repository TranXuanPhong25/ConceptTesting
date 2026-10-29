# V85 checkpoint: resume shared references on another machine

**Superseded:** continue from [resume2](../v85_20261029_resume2/README.md), which
imports the newer174-ref Linux checkpoint and accounts for13duplicate Mac calls.
Old MacPID44302 and LinuxPID22898 stopped. User confirmed execution on Mac;
resume2PID46002 launched03:31:22UTC. Do not launch this older archive.

The archived checkpoint below records the earlier stop at
2026-10-28 17:19:23 UTC (Oct29 00:19 Vietnam); it does not include later progress.

- Both generation arms complete: **113/113 pairs**, including two rounds.
- Shared spec-only references: **36/1130 saved; 1094 remain**, then final scoring.
- 936 received completions; zero outstanding current requests. Three historical
  attempts retain unknown usage: **939 cumulative attempts**, original cap3503.
- No final detection result yet. This is a continuation, not an independent run.

`checkpoint.tar.gz` contains frozen source, inputs, prepared tasks, both generated
arms, all received request/response receipts and the partial oracle pool. The
manifest hashes every imported file. Source bytes stay unchanged; the driver
relocates the venv interpreter in memory. No real endpoint or credentials are
included. Dummy endpoint strings remain in the original unit tests.

## On the destination machine

Use Python 3.11.8+ (3.11 recommended), macOS or Linux. Linux needs working
`unshare -rn` network/user namespaces; restricted containers may disallow this.
The offline native check must pass before inference. Run on **one host only**.
From the repository root, in Bash:

```bash
git pull --ff-only origin main
cd trickcatcher_linefacts/handoffs/v85_20261029
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s . -p 'test_resume.py'
.venv/bin/python resume.py --check
```

Expected check: `generation_pairs=113`, `received=936`, `historical_unknown=3`,
`saved_oracles=36`, `missing_oracles=1094`. Check mode makes no model requests.
The extraction under `work/` is isolated from the rest of the checkout.

Enter the endpoint privately; do not commit it or paste it into logs:

```bash
read -rsp 'Endpoint ending in /v1: ' CT_RETRIEVAL_BASE_URL
export CT_RETRIEVAL_BASE_URL
nohup .venv/bin/python -u resume.py --run > runner.log 2>&1 < /dev/null &
```

Server must expose `qwen3.5-27b-awq`, context8192, `/models`, `/chat/completions`,
and the root `/tokenize` endpoint. Two workers, temperature0.8/top_p0.95,
1024 requested output tokens with existing context fitting, completion timeout900s.
No model substitution, automatic retry or generation rerun.

Progress: `runner.log` and
`work/snapshot/trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_20261029/STATUS.json`.
Final files in the same directory: `RESULTS.json` and **`HANDOFF_COMPLETE.json`**.
Only the latter indicates completion with cumulative historical accounting.
`controller.pid` is a local process ID, not proof that a controller is still alive.

A cleanly interrupted run can reuse the same `work/` directory. The original
ledger prefix and every imported receipt remain hash-checked. Saved oracle slots
are skipped. Failed/unresolved completion attempts stop continuation for manual
review; do not delete receipts or use a fresh work directory to retry them.
Keep the updated work directory when transferring again. Never run two copies.

## Method and verification limits

This comparison keeps v11's hybrid stages, gates and ten shared reference
programs. Retrieval uses v2 top3 cards bound to existing v11 executable facts,
with line-reachability fallback. It **still uses fuzz/trace facts for binding**;
it is not the later desired clean replacement of that dependency.
Canonical implementations/contracts enter only final grading. Primary `ref`
requires at least three base-passing reference programs and unanimous successful
outputs; `o0` is secondary. Preserve all historical unknown usage in reporting.

Local verification: archive/source/receipt hashes, 113 prepared tasks, 226 final
hybrid rows, 36 saved reference identities, focused resume tests and synthetic
native oracle/network-isolation checks. No new model calls or target grading.
Linux destination execution has not been tested here; OS differences must be
reported with the final results.
