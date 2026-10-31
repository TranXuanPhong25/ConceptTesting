# AG-RAG public artifact audit

Checked 2026-10-15. Paper: [arXiv:2502.10696 v2](https://arxiv.org/abs/2502.10696); final TSE DOI 10.1109/TSE.2025.3545970.

- Paper explicitly links the author implementation: <https://github.com/iSEngLab/AG-RAG>.
- Checked master HEAD `47d69677e371209d9b6665ae879df3708886b1bb` (last commit 2025-02-15); GitHub API tree has 154 entries. Repository has no LICENSE file and GitHub reports no detected license.
- README says `dataset.tar.gz` contains the old/new TAP datasets and links a separate Google Drive folder for fine-tuned checkpoints. The tree includes RQ1–RQ3 training/evaluation scripts, model code, baseline and AG-RAG outputs/golds, and CodeBLEU evaluator; `dataset.tar.gz` is 74,369,230 bytes. Fine-tuned checkpoint files are not in the GitHub tree; Google Drive access/content was not verified.
- Statically inspected README, `requirements.txt`, `run.py`, `model.py`, `args_config.py`, and training scripts. Code is PyTorch/Transformers/T5-specific; main model is CodeT5-base 220M. Reported training used two RTX 4090 GPUs; joint training takes about 29.22 hours by epoch 10 on Data_old.
- Paper's main TAP datasets are Data_old (156,760 samples) and Data_new (265,420 samples). A separate Defects4J experiment runs generated assertions on EvoSuite prefixes from 835 bugs/17 projects, counting fail-on-buggy/pass-on-fixed; the repository contains result files.
- README extraction command is printed as `tar -xzcf dataset.tar.gz`, which appears to combine conflicting create/extract flags and should be checked before setup. No commands were run.
- No code/model execution. Full verdict: `../../../../audit/reviews/086.json`.
