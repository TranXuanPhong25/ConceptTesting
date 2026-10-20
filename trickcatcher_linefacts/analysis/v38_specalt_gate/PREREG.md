# v38 spec-alternative gate: can spec-derived programs serve as the "other version" for differential testing? (CPU only)

Written 2026-10-20 before computing anything below. Follows v37 (no-go: surviving mutants witness the bug in only 3/20
pilot20 tasks). Registered next step: replace mutant alternatives with spec-derived programs, as in CASCADE (FSE 2026:
doc-derived implementation, fail-to-pass filter) and TrickCatcher (spec-only DPP programs + differential inputs).
Prior art in this repo: B2 ref oracle (same programs, used as oracle), v7_mutref (refs used to rank hints: good@3 35
vs random 29.4, no LLM gain 13/10), tc-full baseline (44.0 bug/run). What is new here is only the question whether a
Mokav-style difference-exposing input (DET) search between PUT and these programs has headroom.

## Data (dev only)
- pilot20 PUTs and the EvalPlus pool U of v37 (same seed, same sample; evaluation only).
- Alternatives: the 10 existing Qwen2.5-Coder-7B DPP programs per task (`out/oracle_v7hyb_witness/ref_responses.json`,
  identical across oracle dirs), parsed with B2's `code_block`. Valid = loads and equals the PUT on every public base
  input (the PUT passes the public tests, so this is "passes the public tests"). No new model call.
- Reference = HumanEval+ canonical; comparison as v37 (atol, exception type, timeouts excluded).

## Definitions (per task)
- C': some valid program P with P(x) = canonical(x) != PUT(x) for some x in U.
- Consensus witness: some x in U where all valid programs (>= 3) agree, differ from the PUT, and equal canonical
  (the B2 rule on this pool).
- DET precision (descriptive): over x in U where the valid-program consensus differs from the PUT, share where the PUT
  is wrong.
- H': C' and the v31 template pool (v37 output) exposes nothing.

## Go / no-go rule
Mokav-style DET search between the PUT and spec-derived programs is worth a model run on dev only if
- G1': C' >= 10/20, and
- G2': H' >= 3.
Fails either → no-go for this candidate; next candidate from the review (NeuroTestGen path solving / SAVIOR-style
fault predicate) is checked only for eligibility, separately registered. Secondary: consensus witness count, DET
precision, valid programs per task.
