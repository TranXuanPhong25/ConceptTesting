# Reproduction and LineFacts compatibility audit

2026-10-24, Codex. Scope: artifact inspection and dataset/schema checks, no generation, training, author-code edits or paper reimplementation.

## Artifact inspected

Unmodified author checkout: `vendor/UTGenDebug`, commit `03bc690c28b6331e7ff0131cb001dab66f4e546f` (working tree clean).

- JSONL row counts verified: HE+Fix 158, MBPP+Fix 325, MBPP+Fix Hard 170.
- Dataset includes buggy code, specification, signature, reference and evaluation tests. MBPP datasets also contain `test_list`; its method-visible subset must be frozen explicitly.
- Every author Python source parses. Imports, dependencies, GPU inference and generated-code execution were not tested.
- Author tree contains evaluation/debugging scripts but no training script, training instances or trained adapter weights. README expects a user-supplied `--ckpt-dir`. Author HF profile lists no public models. This establishes a missing artifact in inspected sources, not proof no checkpoint exists elsewhere.
- [Author issue #1](https://github.com/archiki/UTGenDebug/issues/1) asks about training-data release; it is not evidence that the released debugging evaluation dataset is the UTGen training corpus.

## Code obstacles before model runs

1. `mbpp_intrinsic_eval.py:61–64`: without `--hard`, the hard JSONL is selected; with `--hard`, the ordinary JSONL is selected. This contradicts README. Freeze the actual dataset/hash rather than trust the flag.
2. `mbpp_utdebug.py:368`: default `--source` points to an absent training file; `code_src` is loaded but not subsequently used. `:374` calls `load_dataset` with a local JSONL path rather than the JSON builder/data_files pattern used by the intrinsic script. Needs a loading smoke check and an explicitly recorded compatibility adapter if necessary.
3. `utils.py:65–72`: the HF model map has `qwen` = Qwen2.5-Coder-7B-Instruct, no 32B entry; STOP_WORDS mentions `big_qwen`. Reproducing the 32B table needs an explicit model configuration.
4. Backend uses in-process vLLM/LoRARequest. A hosted OpenAI-compatible endpoint is not a drop-in for these scripts.
5. In SC modes, canonical execution measures output accuracy; admitted output is still the voted model output (`mbpp_utdebug.py:267–290`). Do not call this an oracle replacement or infer leakage merely from reference-code execution. Audit control flow and ensure evaluation metadata never influences generation/selection.

These are static findings, not a claim that the reported numerical results are false. Preserve vendor source; any repairs need an external, documented adapter and a separate repaired-execution label.

## What can be reproduced

- Prompted/Random intrinsic evaluation: data and generation/evaluation logic available; likely feasible after environment and loading checks.
- UTDebug with base models: available, with the compatibility obstacles above.
- Trained UTGen rows: not reproducible from the inspected artifact alone; need released LoRA weights, or training data and training implementation/configuration. Retraining would require separate authorization and cannot be substituted silently.
- Exact table numbers remain unverified; model revision, seed, sampling settings and repetition aggregation must be pinned first.

## LineFacts mapping

Existing v11_fair `facts.py:790+` consumes PUT source, HumanEval-shaped spec/base-test object and a dataset-specific validator. `gen_prompts.py` already exposes concept/placebo/toolinput arms. Thus reuse is plausible, but not a zero-change dataset swap.

Proposed boundary:

`public spec + buggy code + explicitly visible examples -> LineFacts facts/witnesses -> test generator -> generated (input, expected output) -> original intrinsic evaluator -> optional UTDebug`.

- Convert dataset schema, task IDs, signatures, imports, argument representation and base-test wrapper outside vendor.
- Use only the same public examples across arms; original UTDebug uses the first MBPP `test_list` example in its initial generation context. Giving all examples to LineFacts alone would confound the comparison. Reconcile differing generation contexts before freezing.
- Never feed the extended private `test` suite or canonical solution into fact extraction, fuzz validity, prompt construction or selection. Keep them evaluator-only at inference.
- MBPP partially correct code need not pass public examples. Record this stratum and base-test behavior rather than silently inherit TrickCatcher's pass-base selection.
- Current contracts and paths are HumanEval-specific; MBPP requires spec-based validity treatment. A mutant witness is a PUT/mutant difference, not proof of a real spec violation.
- Retain generated expected outputs and original attack/output/joint metrics for the first comparison. Replacing the oracle with LineFacts's independent program ensemble would change another factor.

Minimum concept attribution controls: plain, concept, matched placebo, toolinput and witness-only, with matched generation/output-voting budget, public information and test-count accounting. Repeat the frozen generator comparison inside the same UTDebug settings only after intrinsic behavior is understood.

Prior local checks: v11_fair's concept/placebo comparison was 26/22 (no clear gain); v48 selection arms found the same six tasks with oracle failures; v49 concept gain disappeared on both-eligible tasks; v54 stronger writer solved both arms. Moving datasets or attaching hints therefore does not itself establish a new concept mechanism. Concept-conditioned fine-tuning would be a separate untested extension, requiring a training control.

Verdict: feasible benchmark/LineFacts adapter candidate; trained UTGen reproduction is currently artifact-blocked. No new experiment was implemented or launched.
