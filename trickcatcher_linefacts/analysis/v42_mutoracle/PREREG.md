# v42 mutant-disagreement oracle questions: CPU ceiling before any LLM (go/no-go)

Written 2026-10-21 before any code output. User go-ahead: "cứ làm đi".

## Prior art (version tree)
Mutants as input-side concepts v7 MUTANT / v31–v34 (fault-type templates; v34 placebo rule not met); v35 ceiling (template
pool exposes 17/33, given exposure a surviving mutant equals the reference on an exposing input in 14/17); v37 Mokav over
surviving mutants on HumanEval pilot20 (mutant = canonical on an exposing input 3/20, no-go); v38/v39 spec programs as
alternatives (no-go); v41 observed I/O relations (sampling reaches bugs 22/33, relation package selects poorly: C2 11/33,
median lift 0.38). New here: the mutant is used on the **oracle side**. Over the v41 sampled pool, every input where the
PUT and a surviving mutant disagree becomes a binary question ("which of these two outputs does the spec require?"),
instead of an open expected value. This measures whether such questions (a) select bug-revealing inputs and (b) have the
mutant output as the right answer often enough for a later LLM judgement step to be worth registering.

## Material (frozen, reused)
- vibepass_half, 33 PUTs. Inputs and PUT outcomes: the v41 batch cache `out/analysis/v41_iorel/cases/<id>/put/`
  (input-set hash must equal `inputs_sha256` in v41 `ceiling.json`, else the case is an error).
- Surviving mutants: the v34 tool stage `out/pipelines/v34_ftplacebo/.../vibepass_half/cases/<id>/tool/phase2/job.json`
  (`order[1:]`, mutants surviving the public examples; PUT + public examples only, no reference).

## Tool (no reference, no LLM)
1. Run every surviving mutant on all v41 inputs (ft_worker batch, per-call timeout 1 s, `max_timeouts` 2 per mutant as
   in v34, chunks of ≤ 10 mutants per process, 3600 s per chunk; skipped/timeouts recorded).
2. Disagreement set D_m: inputs where the PUT and mutant m both give a comparable observation (`iorel.value`) and are
   not `same`. Mutants with identical outcome vectors on the pool are collapsed (first name kept); mutants with empty D_m
   are dropped.
3. Package (≤ 32 distinct inputs): mutants ordered by disagreement share |D_m| / comparable inputs ascending (rarest
   disagreement first, as v41 ranks by smallest minority), ties by name. Round-robin over that order taking each mutant's
   next not-yet-chosen input in D_m (inputs ordered by (len(repr), repr), i.e. simplest first), ≤ 2 inputs per mutant,
   stop at 32 inputs. Each chosen (input, mutant) is one question; the package also records, per input, all mutants
   that disagree on it (for the question-level counts).

## Ceiling measurements (references only here; an input exposes if contract-valid and PUT ≠ reference)
Reference/contract outcomes reuse the v41 batch cache (`cases/<id>/ref/`). As in v41, an exposure counts only if the
batch AND the official per-input path (`flow_run.Reference`) both mark it; re-checked: every package input plus the first
20 batch-exposing inputs per task.
- **D1 (primary)**: tasks where the package contains a question (x, m) with x confirmed exposing and mutant m's batch
  output on x `same` as the reference (the right answer is the mutant's output).
- **D2**: tasks where the package contains a confirmed exposing input (= v41 C2 on the same pool).
- E[random-k D2]: exact hypergeometric chance per task with k = package size (v41 `random_k`), summed.
- Lift per task with C1: (exposing share among package inputs) ÷ (exposing share among all inputs); empty package = 0;
  median reported.
- Reported, not gated: D1 uncapped (any mutant disagreement in the whole pool); question-level split over package
  questions on contract-valid inputs into mutant-right / PUT-right / neither (an upper bound on the false-alarm exposure of
  a later binary judge: a PUT-right question answered "mutant" is a false alarm); package validity share; mutants run,
  collapsed, skipped.

## Go / no-go
GO to a separately registered LLM binary-judgement step iff **D1 ≥ 17/33 AND D2 > E[random-k D2] AND median lift ≥ 2**
(thresholds as v41; 17 = the v35 template pool). Otherwise no-go for mutant-disagreement oracle questions on this pool.

## Amendment 1 (2026-10-21, after an independent read-only review, before any reference/exposure was computed)
Only a tool-side smoke on case 121 had been run. Adopted:
- Package records, per chosen input, every disagreeing mutant (`packages.json`); D1 and the question split stay on the
  chosen (input, mutant) questions only.
- A failed chunk is retried one process per mutant (as v34 `ft_run.execute`); a mutant failing alone is skipped.
  Mutants with no comparable outcome are counted as unusable (not collapsed). Chunk failures and per-mutant skipped
  call counts are reported.
- The v41 reference batch is read only after checking its job equals the expected one (never re-run, so the v41 cache
  cannot be overwritten); a mismatch is a case error. The official re-check reuses the v41 official cache
  (content-digest keyed).
- Memory: only mutant outcomes on disagreement inputs are kept.
- Reported, not gated: C1 next to v41's 22, and the median lift over the v41 C1 tasks.
