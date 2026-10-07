# ConceptCoder placebo control (arXiv 2603.23470, VD, Qwen2.5-Coder-3B, Kaggle T4)

## Question
ConceptCoder reports VD F1 65.15 (regular fine-tuning) -> 73.44 (ConceptCoder) for Qwen2.5-Coder-3B.
Is the gain caused by the **content** of the concept labels, or by the **extra multi-task supervision**
(a concept bottleneck head plus an auxiliary per-line BCE) no matter what the labels say? The released
package compares only regular vs ConceptCoder fine-tuning (plus probing and robustness). It has no
shuffled-concept control.

## Arms (written before any training; everything not listed is identical)
Shared settings: Qwen2.5-Coder-3B in fp16 with LoRA (r 16, alpha 32, dropout 0.05) on q/k/v/o.
Tokenisation is the authors' per-line `convert_examples_to_features` (block 512, at most 100 statements).
Every arm uses the same 23,184 training functions (`train_concept.jsonl`, 16.67% vulnerable) in the same order
(seeded DataLoader generator). Seed 123456 (the authors' seed). AdamW 2e-4 with OneCycle (5% warm-up),
batch 2 x accum 8, clip 1.0, class-weighted CE, fp16 autocast, **1 epoch**. Evaluation uses the
**final model**, with no checkpoint selection. (The old `student/kaggle_train.py` chose the best epoch
by TEST F1. That leak is removed here.)

| arm | head (authors' code, unmodified) | per-line concept labels | loss |
|---|---|---|---|
| `conceptcoder` | concept bottleneck: line mean-pool -> `cbl` 2048->8 -> mean over lines -> Linear 8->2 | true | CE + 0.2 BCE |
| `placebo` | same | **deranged** (scheme below) | CE + 0.2 BCE |
| `regular` | same | none | CE |
| `regular_paperhead` | authors' regular head: last token -> Linear 2048->2 | none | CE |

Pre-registered contrasts. The first one is the **primary** test.
1. `conceptcoder` vs `placebo`: concept *content*; nothing else differs.
2. `placebo` vs `regular`: auxiliary supervision without content.
3. `conceptcoder` vs `regular`: ConceptCoder's gain with the head held fixed.
4. `regular` vs `regular_paperhead`: head architecture only.
5. `conceptcoder` vs `regular_paperhead`: the paper's own comparison (head and loss differ together).

Interpretation rule, fixed before training:
- C > P with exact McNemar p < .05 and a paired-bootstrap ΔF1 95% CI that excludes 0: the content matters.
- C ≈ P (CI contains 0) and both > R: the gain comes from the multi-task supervision or format, not the content.
- C ≈ P ≈ R: this budget (1 epoch, LoRA) reproduces no gain, so the paper's setting is not decided.

### Why two "regular" arms
- **Same data.** `run_regular_fine_tuning.sh` and `run_conceptcoder_fine_tuning.sh` take the same
  `<dataset>` argument and both read `{train,valid,test}_<dataset>.jsonl`. With `concept` they see the
  same functions. The `_general` files are a different, larger dataset (134 CWEs) and are not used here.
- **Different head.** The authors' regular model also changes the head (last-token linear instead of the
  concept bottleneck), so "regular vs ConceptCoder" changes the architecture and the objective together.
  `regular` keeps the head fixed and changes only the objective, as the brief asks. `regular_paperhead`
  is the paper's baseline architecture. To keep inputs identical across arms, it is fed the same per-line
  tokenisation.
- **The released regular model cannot train.** Its `forward` ends with `output.append(loss)` while
  `loss = ...` is commented out, which raises a NameError whenever labels are passed. So, for every arm,
  we call the authors' `forward` without labels and compute the loss in `train_arm.py` with their formula:
  `CE(vuln) * 1 + BCE(per-line concepts, rows of all -1 masked) * concept_weight`. The conceptcoder
  `forward` would also cast BCE targets to bf16, which the earlier student copy had patched. The authors'
  files are used **unmodified**.

### Deviations from the paper (identical across arms)
- LoRA instead of the paper's "full" fine-tuning. Their scripts actually freeze all but the last 5 layers
  and the embeddings.
- 1 epoch instead of 10.
- fp16 instead of bf16 (T4).
- Class-weighted CE (the `student/` setup).
- No selection of the best checkpoint on validation.
- Multi-task loss only. The paper text describes a concept stage followed by a multi-task stage, but the
  released script runs the multi-task loss only.

## Pre-registered placebo scheme (`make_placebo.py`, seed 20261007)
Only the **training** split is altered. The model never sees altered labels at test time.
- **Stratum** = raw line count `n = len(func.split("\n"))`. This equals `len(lines_concept)` for all
  23,184 rows.
- **Strata with ≥2 functions:** apply a uniform random derangement. Each function receives the whole n x 8
  `lines_concept` matrix of **a different function with the same number of lines**.
- **Singleton strata** (157 long functions): the donor is a uniform random function with strictly more lines,
  and only its first n lines are used. The single longest function (4,403 lines) has no longer donor, so its
  own line vectors are permuted.
- `concepts` (the function-level OR of the line labels) is recomputed. Function code, `target` and `idx`
  are unchanged; `train_arm.py` asserts this.

Why this scheme and not a within-function line shuffle:
- The bottleneck head **averages concept logits over lines**, and function-level concept counts predict
  vulnerability on their own. For example, vulnerable functions have 2.3x more concept-2 lines, and
  P(c3|vul) = .30 vs P(c3|ben) = .14.
- A within-function shuffle keeps every function's counts, so most of the signal that reaches the
  classifier would survive and the placebo would be weak.
- The cross-function derangement keeps:
  - the supervision format (same lines, same 8 labels, realistic co-occurrence and layout);
  - global per-concept line rates (± singletons);
  - the length -> concept association, which the model can read from the code anyway.
- It destroys the link between this function's code and its labels, at both line and function level. It
  also ignores `target`. Deranging within (n, target) strata was rejected because that would leak the
  vulnerability label through the concept channel.

Checks (`python make_placebo.py data/VD/train_concept.jsonl data/VD/train_concept_placebo.jsonl`):
```
functions=23184  self-donor=0  within-perm=1  singleton-donor=156
placebo matrix identical to true matrix by chance: 1971 (8.50%)      # mostly all-zero short functions
line-level positive rate  true   : [0.0065 0.0191 0.1668 0.0083 0.0416 0.0113 0.0084 0.113 ]
line-level positive rate  placebo: [0.0064 0.0188 0.1676 0.0081 0.0445 0.011  0.0081 0.1153]
P(c|vul)-P(c|ben) true   : [0.072 0.108 0.144 0.157 0.21  0.18  0.073 0.178]
P(c|vul)-P(c|ben) placebo: [0.086 0.134 0.124 0.108 0.134 0.121 0.078 0.166]   # residual = line-count effect
sha256(train_concept_placebo.jsonl) = 081da3a2357ea3cda74ea0e3cc036bc5756ec798d1c0e646a4aa8934939a9822
```
The output is deterministic: two independent runs gave the same sha256.

## Evaluation (`train_arm.py`, per arm, after training)
- **VD:** acc, precision, recall and F1 (threshold p(vul) > .5, as the authors use) on `test_concept`
  (2,892 functions, 16.67% vulnerable, so predicting "all vulnerable" gives F1 = 28.57). The same metrics
  on `test_concept_robustness`, which holds the same 2,892 functions after renaming and dead-code transforms.
  That file keeps the *original* function's line labels: 2,887 of 2,892 rows have more lines than labels,
  so the authors' loader would raise KeyError. Missing labels are zero-filled; only the VD label is used.
- **Paired predictions:** `preds_test.jsonl` and `preds_robust.jsonl` (`idx`, `label`, `p1`, `pred`). `analyze.py`
  runs an exact McNemar test and a paired bootstrap of ΔF1 (2,000 resamples).
- **Concept head** (bottleneck arms): `cbl` sigmoid > .5 against the true test line labels (macro-F1 over
  8 concepts, plus per-concept predicted vs true positive rates to detect collapse). It is also scored on
  the first 1,000 *training* functions against the true **and** the placebo labels. This answers "does the
  placebo model learn the shuffled labels?"
- **Linear probe** (authors' protocol, all arms):
  - representation: line mean-pooled final hidden states;
  - probe: Linear 2048->8 with BCE, Adam 1e-3, batch 64;
  - training set: the authors' `train_concept_probing` (same idx and targets as the VD test set, but a
    *transformed* function text with re-annotated line labels);
  - test set: `test_concept_probing` (2,892 functions from another source, none in VD train);
  - schedule: 20 fixed epochs instead of best-on-validation.

## Budget and schedule
- `kaggle quota` on 2026-10-07: GPU 18.62 h used, **11.38 h left**, refresh 2026-10-10 00:00 UTC.
- Previous single-arm run (`conceptcoder-vd-train`): epoch 0 took about 160 min to train plus 9 min of
  test evaluation. Epochs 1–2 took about 228 min each (10.5 h for 3 epochs).
- `machine_shape: NvidiaTeslaT4` is **2x T4**, and the old run used one. Each kernel therefore trains
  **two arms in parallel**, one per GPU, inside one session's quota.

| kernel | arms | est. | when |
|---|---|---|---|
| `ccplacebo-smoke` | placebo ‖ regular_paperhead, 64 train / 32 eval examples | ~0.3 h | now |
| `ccplacebo-k1-conceptcoder-placebo` | conceptcoder ‖ placebo, 1 epoch | 3.5–4.5 h | after smoke |
| `ccplacebo-k2-regular` | regular ‖ regular_paperhead, 1 epoch | 3.5–4.5 h | after k1 |
| (next week) | second seed: placebo ‖ regular, then conceptcoder ‖ regular_paperhead, or 3 epochs | 2 x 4 h | after 10-10 |

Total this week is about 8–9 h, under 11.38 h. Before each push, check that the remaining quota is at
least the expected duration plus 1 h. Kernels run one at a time, all private. The push uses `-t` as a
hard session ceiling.

## Commands
```bash
cd ConceptCoder_placebo
# data: figshare data.zip (https://figshare.com/s/1decab8232c653b44f71) -> data/VD/ ; teest_concept.jsonl -> test_concept.jsonl
python make_placebo.py --selftest && python analyze.py --selftest
python make_placebo.py $D/train_concept.jsonl $D/train_concept_placebo.jsonl
# package: code + authors' VD .py (unmodified) + data -> one private dataset
S=/tmp/ccp/stage; mkdir -p $S/ConceptCoder_placebo $S/ConceptCoder_org/code/concept_learning/VD $S/data/VD
cp train_arm.py kaggle_run.py make_placebo.py analyze.py $S/ConceptCoder_placebo/
cp ../ConceptCoder_org/code/concept_learning/VD/*.py $S/ConceptCoder_org/code/concept_learning/VD/
cp $D/{train_concept,test_concept,train_concept_placebo,test_concept_robustness,train_concept_probing,test_concept_probing}.jsonl $S/data/VD/
tar czf /tmp/ccp/ds/ccp.tgz -C $S .            # /tmp/ccp/ds/dataset-metadata.json: id xunphongtrn/conceptcoder-placebo
kaggle datasets create -p /tmp/ccp/ds          # updates: kaggle datasets version -p /tmp/ccp/ds -m "..."
kaggle datasets status xunphongtrn/conceptcoder-placebo   # wait for "ready"
kaggle kernels push -p kernels/smoke -t 3600
kaggle kernels push -p kernels/k1 -t 21600     # then k2 once k1 is complete
kaggle kernels status xunphongtrn/ccplacebo-k1-conceptcoder-placebo
kaggle kernels output xunphongtrn/ccplacebo-k1-conceptcoder-placebo -p out/k1 && cp -r out/k1/out/* out/
python analyze.py out
```
Local CPU test: a tiny random Qwen2 model plus 40/20-row subsets. `python train_arm.py --arm placebo
--model /tmp/tiny --workers 0 ...` runs end to end.

## Kernel ids / status
| kernel | id | status |
|---|---|---|
| smoke | `xunphongtrn/ccplacebo-smoke` (v1) | COMPLETE 2026-10-07: both heads ran end to end; LoRA receives gradient; ~0.1 h quota |
| k1 | `xunphongtrn/ccplacebo-k1-conceptcoder-placebo` (v1) | COMPLETE (06:50 to ~11:25 UTC, ~4.6 h quota); output in `out/k1/` |
| k2 | `xunphongtrn/ccplacebo-k2-regular` (v1) | pushed 2026-10-07 11:53 UTC, `-t 21600` |

Dataset: `xunphongtrn/conceptcoder-placebo` (private, `ccp.tgz`), v1. Smoke env: torch 2.10.0+cu128,
transformers 5.0.0, peft 0.19.1, 2x Tesla T4, 31 GB RAM.
