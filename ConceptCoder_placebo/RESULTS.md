# Results: ConceptCoder placebo control (PARTIAL; k1 done, k2 running)

Setup: README.md (1 epoch, LoRA, seed 123456). Test set: 2,892 functions, 16.67% vulnerable;
predicting "all vulnerable" gives F1 28.57.

| arm | test F1 | acc | prec | rec | AUROC | robust F1 | robust AUROC | concept head macro-F1 (test, true) | linear probe macro-F1 |
|---|---|---|---|---|---|---|---|---|---|
| conceptcoder | **55.54** | 86.55 | 61.83 | 50.41 | 0.855 | 25.57 | 0.533 | 26.22 | 70.42 |
| placebo | 0.00 (predicts nothing vulnerable) | 83.33 | 0 | 0 | 0.637 | 0.00 | 0.637 | 0.00 | 4.12 |
| regular | k2 running | | | | | | | | |
| regular_paperhead | k2 running | | | | | | | | |

Primary contrast, conceptcoder vs placebo, on test:
- exact McNemar: b = 243, c = 150, p = 3.1e-6;
- ΔF1 = +55.5, 95% CI [+51.3, +59.4].

Read with care:
- **The F1 gap overstates the effect.** The placebo model's p(vul) lies only between 0.07 and 0.40, so at
  the authors' 0.5 threshold it never predicts "vulnerable".
- **The ranking is still clearly worse.** Threshold-free, the placebo model reaches AUROC 0.64, against
  0.86 for conceptcoder. Even with the threshold tuned on the test set its F1 is 34.0, against 57.2.
- **The placebo arm trained normally.** Its loss stayed finite: CE fell to 0.536 (chance is 0.69) and BCE
  to 0.203. It did not diverge.
- **The placebo head learned nothing about real concepts.** It predicts no concept at all on test
  (macro-F1 0), and its fit to its own shuffled train labels is also 0. It fell back to marginal rates
  below 0.5. The conceptcoder head fits true train labels at 24.9 macro-F1 and placebo labels at only 4.3.
- **The representations collapse.** On the authors' probing files, a linear probe on the placebo model's
  representations scores 4.12 macro-F1, against 70.42 for conceptcoder.
- **Robustness is weak.** conceptcoder loses most of its signal on the robustness transforms (AUROC 0.53).
- **Interim reading:** the concept content is not inert. Supervising the bottleneck with mismatched labels
  hurts badly. Whether *true* concepts help beyond **no** concept loss is the `regular` arm's question,
  in k2.
- **The earlier student run:** it reached F1 64.36 after 3 epochs, with the best epoch chosen on test.
  This run used 1 epoch and the final model.

Full tables: `python analyze.py out`.
