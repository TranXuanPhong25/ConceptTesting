# Concept-supervised test generation: feasibility, 2026-10-26

Status: source and prior-result assessment only. No adaptation, training, new dataset generation, or GPU run was performed.

## Decision

Possible as a substantial new research/engineering effort, but not ready for a GPU experiment. The main missing prerequisite is a validated training task: independently correct, applicable concepts paired with executable testing actions and a demonstrated failure to translate those concepts into revealing tests.

## What the available papers/code establish

[CB-LLMs author repository](https://github.com/Trustworthy-ML-Lab/CB-LLMs), its [generation training source](https://github.com/Trustworthy-ML-Lab/CB-LLMs/blob/main/generation/train_CBLLM.py), and [paper](https://arxiv.org/abs/2412.07992) support concept-controlled natural-language generation. Released generation examples use sentiment/topic datasets, with class labels as concepts; the trainer uses LoRA on Llama-3-8B. These are not executable test-generation datasets or demonstrations of finding code bugs. A code-test generator requires new data, losses/validation choices, and integration.

For the separate ConceptCoder paper, use the existing [paper-facts memory](../../memory/conceptcoder-paper-facts.md) and immutable `ConceptCoder_org/` checkout. Its demonstrated targets are vulnerability detection and branch prediction; a test generator is a new downstream task. [ConceptCoder Table 6](https://arxiv.org/html/2603.23470v1#S3.SS3.SSS4) shows non-vulnerability concept supervision also improves SFT. The existing audit estimates that NVC recovers about three quarters of the VC gain: useful auxiliary supervision must be controlled when attributing improvement to fault-relevant concepts.

## Known warnings from this repository

- [v51](../../memory/v51-latent-concept.md): frozen Qwen-1.5B residual probes and a concept-bottleneck oracle were no-go; MBPP+ CBM .627 versus direct .626 and placebo .631; VibePass CBM .495 versus direct .476, below intrinsic NLL .650. This tested frozen readouts/oracle selection, not end-to-end concept-supervised generator fine-tuning. It warns about transfer and concept choice without ruling out every training method.
- [Training evidence gap](../../memory/concept-training-evidence-gap.md): observed losses also came from upstream abstention, mechanical gates, input-pool reach, and oracle capability. Those do not establish a concept-to-input translation bottleneck. Changing a loss cannot be assumed to fix unavailable input structures or wrong task semantics.
- Existing menu descriptions are candidate test ideas, not gold annotations of a task's true fault. A reference-confirmed revealing input is an evaluator label, not proof that an accompanying verbal concept is semantically correct or caused generation.
- The 33 VibePass tasks have been repeatedly inspected. They cannot become a new untouched final test set, nor can their labels be reused across train/eval versions as if independent examples.

## Prerequisites for an experiment

1. Audit existing artifacts for the conditional population: correct/applicable concept, permitted evidence, actual generation opportunity, and failed executable translation. Do not build a large new corpus merely to rescue a borderline signal.
2. Define one trainable target and verification protocol, e.g. concept → input strategy, with an independent oracle and legality checks. Preserve task/project separation and keep evaluation tasks, fixed solutions, hidden tests, and PBT-Bench benchmark data out of training.
3. Compare plain SFT, concept-supervised SFT, and matched auxiliary/placebo supervision using the same backbone, data volume, training compute, and inference budget. Report concept correctness and bug detection separately. An intervention should change generated tests in the predicted semantic direction.
4. Measure real model/data memory and step-time on an approved training machine before quoting GPU-hours or VRAM. Neither the source nor the current audit establishes that a particular small Kaggle GPU can run the original configuration. LoRA/quantization choices may change method fidelity.
5. Register and independently review the proposed experiment. Any paper adaptation/reimplementation requires the authorization specified by root `AGENTS.md`; this feasibility request does not authorize model training or spending.

The next useful deliverable is an audit of available correct-concept/failed-translation examples and label reliability, not a claim that concept-supervised training is the remaining proven solution.
