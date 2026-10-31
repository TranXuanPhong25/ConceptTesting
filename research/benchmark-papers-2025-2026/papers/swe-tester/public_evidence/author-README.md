# SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories

SWE-Tester is a training and evaluation framework for teaching open-source large language models to reproduce real-world software issues by generating executable tests. The repository provides the data-preparation pipeline, supervised fine-tuning recipes, inference utilities, and the containerized SWT-Bench harness used to measure whether generated tests reliably expose repository issues.

The accompanying paper, [SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories](https://arxiv.org/abs/2601.13713), has been accepted to **EMNLP 2026 (Industry Track)**.

![SWE-Tester pipeline](./assets/system_diagram.png)

## Resources

- Paper: [arXiv:2601.13713](https://arxiv.org/abs/2601.13713)
- Dataset: [SWE-Tester on Hugging Face](https://huggingface.co/datasets/adityasoni17/SWE-Tester)

Large datasets, model outputs, and evaluation artifacts are hosted externally and are not committed to this repository.

## Repository structure

- `data_preparation/`: prepares and curates issue-reproduction training data.
- `torchtune_train/`: contains model download, data conversion, and `torchtune` training utilities.
- `eval/`: runs inference and evaluates trained models.
- `bm25_retrieval/`: retrieves repository context for issue reproduction.
- `swt-bench/`: provides the containerized harness for evaluating LLM-generated tests.

## Getting started

Use the component-specific documentation for setup and execution:

- [Data preparation](./data_preparation/README.md)
- [Training with torchtune](./torchtune_train/README.md)
- [Inference and evaluation](./eval/README.md)
- [SWT-Bench harness](./swt-bench/README.md)

## Citation

If you use SWE-Tester, please cite:

```bibtex
@misc{soni2026swetestertrainingopensourcellms,
      title={SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories},
      author={Aditya Bharat Soni and Rajat Ghosh and Vaishnavi Bhargava and Valerie Chen and Debojyoti Dutta},
      year={2026},
      eprint={2601.13713},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2601.13713},
}
```
