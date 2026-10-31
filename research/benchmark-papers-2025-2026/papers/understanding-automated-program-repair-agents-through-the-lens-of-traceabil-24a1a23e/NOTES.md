# Understanding Automated Program Repair Agents through the Lens of Traceability: An Empirical Study

Reviewed 2026-10-15. Full text read: 13,613 words (arXiv v3, 24 pages). Author source and public trajectory data verified. Full replication: conditional; no local run.

## Why it is promising

The paper traces five APR agents across 500 SWE-bench Verified Python tasks, and directly studies reproduction-test generation, whether tests trigger the reported issue, reproducer overfitting, regression-test selection and localization context. It finds that Agentless/SWE-Agent generate many reproducers but trigger bugs only ~41–57%; SWE-Agent has substantially higher overfit than Agentless. On Verified-50, Agentless test generation at 40 samples reaches 46.0% issue reproduction at temperature .2 versus 42.3% at 1.0; adding localization raises successful tests from 614/1500 to 697/1500, benefiting 27/50 tasks. These are strong test-quality and diagnosis-context measures for the thesis.

This is SWE-bench Verified, not SWT-Bench; SWT-Bench appears in related work only. It is process/protocol analysis, not a root-cause taxonomy or classifier.

## Artifact and reproduction

The author-linked [ARiSE-Lab repository](https://github.com/ARiSE-Lab/understanding-apr-agents) provides scripts, result tables, plots and analysis README files. The public [Hugging Face trajectory dataset](https://huggingface.co/datasets/zt6c3mxv8q/logs_and_trajs) is 3.28 GB and includes predictions, metadata, logs and trajectories. The viewer currently errors on heterogeneous schemas, though raw files are downloadable. GitHub archive pinned by its zip comment to `31251be42ca1aa3251890f7b1d1b678462fa1420` (SHA-256 `1c436709062954c3834b7226c17d9b4553f74bac44433a40853ea9b8a251b515`). The software repository and dataset card do not declare licenses; the paper is CC BY 4.0.

Cached trace analyses are reproducible in principle without model calls. Exact reruns of 50-task test generation/localization require paid Claude Sonnet 4, Dockerized SWE-bench and the external Agentless repository; docs also retain a hard-coded author filesystem path. Original multi-agent traces require GPT-4o/Claude endpoints or relying on the public trajectory archive. No APIs or code were run.

Full text SHA-256 `94e7c0db3e6c139515fc7a1bb34e46e160f0d23908199f87c261b272226b9d27`. All 1,310 extracted lines were read in consecutive chunks, including references.
