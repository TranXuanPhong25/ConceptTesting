# v56: fresh LiveCodeBench cohort (conditional on completed v55)

2026-10-24, before mining PUTs or reading any new hidden-test outcomes.
This registration permits infrastructure/metadata preparation only until the
v55 writer transport and review gates pass. No completed v55 baseline exists.

## Cohort and fixed mining cap

Use official livecodebench/code_generation_lite, newest available release;
resolve and record revision before retrieving problem data. Prefer post-writer
cutoff dates only when the exact writer cutoff can be documented. Otherwise
explicitly label contamination risk; do not call the cohort post-cutoff.
Exclude all 76 original VibePass question IDs using identity metadata only,
including both dev and held-out, plus exact normalized statement duplicates.
Do not inspect or execute VibePass held-out source/tests/outcomes. The current
local LCB files are filtered to VibePass and are unsuitable as a fresh cohort.

Choose the newest 60 nonoverlapping functional LeetCode problems (contest_date
descending, question_id lexical tie-break), with parseable signatures and at
least one public and one hidden test. Eligibility uses metadata/schema only.
Two independently generated plausible solution attempts/problem, fixed at 120
PUT calls, no targeted bug injection and no hidden-test feedback to generators.
GPU endpoint first if available, model label/config recorded before calls;
otherwise Codex PUT generator is an explicitly allowed deviation, with the
same prompt-only isolation as v55. Use all attempts passing every public test
and failing >=1 hidden test, at most the first such attempt/problem. Include
empty/low-yield cohort as a result; never add more problems or calls to rescue
it. Separate public failure, hidden pass, hidden fail, timeout, and harness
error. Only ordinary wrong-value/exception hidden failures establish a buggy
PUT; ambiguous harness failures are not retained.

## Frozen comparison (not yet activated)

Before mining execution, an append-only amendment must pin source revision,
60-problem manifest hashes, generation config, and independently reviewed
adapter for official LCB tests into the v53 machinery. A second freeze before
pipeline calls pins v55's Codex writer configuration: plain input generator,
open validity filter, k=3 defn oracle, public filtering/quorum/cap20. Include
v55 interpretation only if its registered promising gate passes. Controls:
Codex defn and matched placebo, all freshly generated, paired on identical
new inputs/filter. Do not reuse Sonnet answers or select based on new pipeline
outcomes. A fresh cohort has no pre-existing v49 universe: register a fixed
public-seeded tool input pool as a separate control before execution.

Report cohort yield, confirmed tasks, confirmed tests, precision, FA invalid
vs wrong-value vs unknown, common-mode and abstention; paired task wins/losses
and problem-level exact paired sign test, with absolute differences. No claim
from a missing arm or incomplete writer batch. Independent Codex review before
mining/evaluation outcomes. Check Codex 5h quota before each large batch; <15%
remaining means checkpoint, commit, stop and report reset. No paid API fallback,
Kaggle notebook edits, automatic endpoint wait loop or VibePass held-out run.

## Amendment 1 (2026-10-25, before any PUT generation or hidden-test outcome)

User instruction 2026-10-25: run v56 on the user's new Qwen2.5-Coder-32B-Instruct endpoint (served name
`qwen2.5-coder-32b-instruct`; URL kept only in a private chmod-600 env file). This replaces the
"conditional on completed v55" gate: v55 (Codex) stopped at a quota/transport block; its interpretation
question was answered on dev by v55h (Haiku: defn = interp = placebo 21/33, FA 0). Only the **mining stage**
is activated here; the pipeline-arm freeze (writer, arms, controls) remains a separate later amendment.

- Source: livecodebench/code_generation_lite @ 0fe84c3912ea0c4d4a78037083943e8f0c4dd505 (HF lastModified
  2025-06-05, release_v6 is the newest; no newer official data exists). Files used: test6.jsonl sha256
  bb4c364f…f1f5, test5.jsonl sha256 7f77571c…1214 (full hashes in manifest.json).
- Manifest `out/v56_lcb_fresh/manifest.json` sha256 7cfdf89f87d0bc5a59ecdb9f54ebb2e4e884c16b3a5ccae8224a232406a534c2:
  eligible functional LeetCode pool 110 after excluding 34 VibePass question IDs (0 exact statement duplicates);
  newest 60 by contest_date desc / question_id asc = 2025-01-04 … 2025-04-05, easy 19 / medium 25 / hard 16.
  Eligibility read metadata, starter code, public tests and the hidden-test count only.
- Contamination label: all 60 problems are dated after the Qwen2.5-Coder-32B-Instruct public release
  (2024-11-12), so they postdate the PUT writer's training data. No claim is made for later pipeline writers.
- Generation: official LCB functional prompt (system + question + starter code), temperature 0.8,
  top_p 0.95, max_tokens 4096, seed = 1000·rank + attempt, 2 attempts/problem = 120 calls, 1 worker.
  Transport retry (≤3) only when no HTTP response was received; content is never regenerated.
- Classification (`mine.py evaluate`, sandbox = analysis/vibepass_feasibility.py sha256 aca91152…517e, read-only):
  no_response / no_code / public_fail / hidden_pass / timeout_only / hidden_fail. Buggy PUT = passes every
  public test and has ≥1 wrong-value or exception hidden test; first such attempt per problem. Timeout-only
  failures are not retained. Low yield is a result; no extra problems or calls.
- Code: mine.py sha256 491a6d09bba24dc7d4a88b82ede11078e516ae698d27dc2a187c04d758766268.

## Amendment 2 (2026-10-25, after independent Codex review BLOCK, before any PUT generation)

Review must-fixes applied in mine.py (now sha256 a8726a3dda2acec0792f211ab680dfe00823a78bacb6d1e03113afe912c73c95):
(1) append-only fsync'd journal per send; any saved record, including HTTP/read errors, is final and never resent;
a key sent without a saved record becomes `unknown`, never resent; retries only when the connection fails before
any HTTP status; body-read failures are final. (2) Test execution distinguishes PUT exception (`exc`, result marker
with error) from harness failure (`harness`, no marker); buggy PUT = ≥1 hidden wrong/exc; harness-only failures
are `harness_error` and never retained. (3) Starter signature validated by `ast` (class Solution defines
func_name); decode failure aborts the manifest instead of skipping. Rebuilt manifest is byte-identical
(sha256 7cfdf89f…34c2). (4) generate/evaluate verify the frozen manifest hash and per-problem tests/statement/
starter hashes, require served name `qwen2.5-coder-32b-instruct` in GET /models, record served metadata,
model, gen config and request sha256 per call, and reject cached records with a different request.
Should-fix applied: extraction = last fenced block containing `class Solution`. Not changed (reported):
`from __future__` lines would fail under the shared PREFIX (adapter limitation, counted as public failure);
thread-pool subprocess launch with preexec_fn is the same harness used in v40/VibePass feasibility.

## Amendment 3 (2026-10-25, after Codex re-review BLOCK, before any PUT generation)

mine.py sha256 e352d9166d3b9c10329b43fd1b977cfc87cf58761600abca1fac84b361b9a245. Retry only when the URLError
reason is DNS failure (socket.gaierror) or ConnectionRefusedError (request provably never reached the server);
every other timeout/OS/URL error is a final `unknown` record, never resent. Request body is built by one
function for generate and evaluate; evaluate rejects any record whose request sha256 differs from the frozen
prompt/seed/config.

## Amendment 4 — pipeline-arm freeze (2026-10-25, after mining, before any reference, arm call or arm outcome)

Mining result (CHANGELOG): cohort = 11 problems (easy 2 / medium 6 / hard 3). User choices 2026-10-25:
**writer = Qwen2.5-Coder-32B-Instruct** (same endpoint as mining, replaces Codex writer); **scoring reference =
certified reference** (LiveCodeBench ships no reference solution). Runner: `arms.py` (sha256 to be pinned after
review; draft e757dfd602e2b631…).

- **Reference (scoring only):** Codex CLI (`codex exec --ephemeral -s read-only`, empty cwd, `--json` event audit;
  account default model gpt-6-astra, reasoning high), prompt = statement + starter only, "no tools". Up to 3 separate
  attempts/problem; the first attempt whose answer passes **every public and hidden test** (mine.py harness, 10 s/60 s)
  is the reference. An answer with any tool/command/file event is rejected (counts as an attempt). No certified
  reference in 3 → problem excluded from scoring (reported). A **certified validator** `is_valid(args)` is made the same
  way (certified iff True on every public+hidden input); used only to split FA into invalid vs wrong-value; none
  certified → validity = "reference does not raise". Neither is ever shown to a Qwen arm.
- **Oracle families (Qwen, k = 3 each, 99 calls):** v49 `defn` / `brute` / `plain` prompts verbatim (statement,
  public tests as asserts, module-level signature from the starter), temperature 0.8, top_p 0.95, max_tokens 1024,
  seed = sha256(`v56/<qid>/<arm>/<i>`)[:8]. Code = v7 `code_block`. Program valid iff every public test returns the
  expected output within 2 s. Concept effect = defn vs brute (primary); family effect = brute vs plain (v49 secondary,
  the only robust earlier effect, reversed with Haiku in v64); defn vs plain reported. v55 interpretation arm excluded
  (v55h not promising). TC variants not run (not in the v56 freeze).
- **Inputs, identical for all arms:** public inputs ∪ tool pool `vibepass_feasibility.fuzz_inputs` (public seeds,
  n = 400, rng `v56/fuzz/<qid>`) ∪ one Qwen v53 `plain` generator answer (≤ 300, 20 s, max_tokens 2048), filtered by
  one Qwen v53 `open` checker answer (all checks True; checker dropped if it rejects any public input). Order =
  sha256(input). Report per source.
- **Oracle rule:** v49 primary quorum on inputs where the PUT returns within 2 s: largest group of valid programs with
  value ≠ PUT, ≥ 2 members and > V/2 (V = valid programs; timeouts/exceptions at 1 s do not agree). Cap 20 tests/task.
- **Judge:** confirmed test = certified-valid input, reference returns within 10 s, oracle value = reference ≠ PUT.
  FA = invalid (validator False or reference raises) / wrong-value / unknown. Confirmed task = ≥ 1 confirmed test.
  Diagnostics: reach (valid exposing inputs in pool), abstention, common-mode (all finishing valid programs = PUT, or
  all equal a non-reference value), valid programs, finish_reason=length.
- **Decision (each comparison A vs B):** GO iff confirmed tasks A ≥ B + 2, paired task wins > losses, and FA tests
  A ≤ B; exact two-sided sign test reported. 11 tasks is underpowered: a null is "not replicated", not evidence of no
  effect. Missing/unknown Qwen calls count as no program (reported); > 10 % missing in an arm → no verdict for it.
  No regeneration, no extra problems/samples, no post-outcome prompt or rule change. Independent Codex review of
  this amendment + runner before any reference or arm call.

## Amendment 5 — Codex review BLOCK (7 must-fix) applied, 2026-10-25, before any reference, arm call or outcome

1. Equality: `same(a, b)` = decoded JSON value `==` everywhere (public validation, quorum groups, judge); no JSON
   re-decoding of strings; quorum groups by `same` (no JSON-key grouping).
2. Fresh state: the program module is re-executed in a new namespace (new `Solution` instance) for every input,
   matching the certification harness.
3. Missing calls: an absent record = `missing` (no program); an arm with > 10 % missing/no-response oracle calls gets
   no verdict (`go = null`) in every comparison it is part of.
4. Cache: per-key lock + unique temp files; cache key includes harness version and interpreter path.
5. Codex reference/validator attempts: `sent.json` (fsync) before each call; a sent attempt without audit is final
   `unknown` and consumes the 3-attempt cap; saved audits are reused, never resent. Model pinned `-m gpt-6-astra`,
   `model_reasoning_effort="high"`, recorded per attempt.
6. Sandbox: bubblewrap (`--unshare-all`, `--die-with-parent`, new session, empty tmpfs root, read-only /usr +
   interpreter + the three runner files, the job dir is the only writable host path; no `out/`), RLIMIT_AS 4 GB,
   process group killed on timeout. Smoke-tested: no host-file access, no network, forked children killed.
7. Result channel = `result.json` in the job dir (not stdout); unreadable/malformed → harness failure → chunk
   fallback 200 → 25 → 1, then `timeout`/`crash` (abstention).
Should-fix applied: comment on filter rule; diagnostic `no_quorum` (≥ 2 finishing valid programs, not common-mode,
no quorum). Reference certification itself still uses mine.py's harness (unchanged, as for mining).

## Amendment 6 — Codex re-review BLOCK (5 must-fix) applied, 2026-10-25, before any reference, arm call or outcome

1. Per-input isolation: inside the sandbox a supervisor forks one process per input (and for the generator call);
   each child loads the program into a fresh namespace from a fresh copy of the interpreter state (sys.modules,
   builtins), stdout/stderr → /dev/null, own process group killed afterwards; per-input wall limit 10 + per_call + 5 s.
2. Result channel = the supervisor's original stdout, written once; size-capped (256 MB) and schema-validated
   (`ok`/`timeout`/`exception`/`load`/`crash`, bool for checks; generator dict schema) before acceptance; otherwise
   harness failure → chunk fallback. The sandbox has no writable path at all (read-only root, job dir bound
   read-only), so no symlink/FIFO result tricks.
3. Reference/validator certification uses the same hardened harness (`certify`: 10 s per test, timeout retried once
   at 60 s, LCB value equality) instead of mine.py's `unshare -rn` harness.
4. Quorum uses a dedicated sentinel, so a JSON `null` oracle value is emitted and judged like any other value.
5. The > 10 % missing-call gate counts every oracle call of the 11-problem cohort, before reference exclusion.
Should-fix applied: interpreter bind roots follow the whole symlink chain; a single-runner file lock (flock).

## Amendment 7 — Codex re-review #3 BLOCK (2 must-fix) applied, 2026-10-25, before any reference, arm call or outcome

1. Each forked program child closes the supervisor's result fd before running program code; the parent accepts a
   result only if the sandbox exits with status 0 (tested: a child that writes a forged batch to every fd and kills
   the supervisor yields `crash`, not its forged values).
2. `/dev` is remounted read-only as well as `/` (tested: `/dev/shm` writes fail, no state between inputs).
Should-fix applied: monotonic deadlines; stdout read capped at 256 MB while streaming; generator argument strings
that are not valid JSON are dropped (counted). Harness cache version v56-arms-4.

## Amendment 8 — Codex re-review #4 APPROVE (no must-fix), freeze, 2026-10-25, before any reference, arm call or outcome

Should-fix applied (`canon` also drops RecursionError). Runner lock is per command (`ref` writes only `arms/ref/`,
`generate` only `arms/calls/` + journal), so the Codex reference job and the Qwen generation may run concurrently;
`score` runs after both. Frozen runner: `arms.py` sha256 289570e6ad1ab493b2bc85875ec9b2b0970291e149c35b7907d5c5dd9f2152a3. Review sequence: BLOCK(7) → BLOCK(5) → BLOCK(2) → APPROVE.
