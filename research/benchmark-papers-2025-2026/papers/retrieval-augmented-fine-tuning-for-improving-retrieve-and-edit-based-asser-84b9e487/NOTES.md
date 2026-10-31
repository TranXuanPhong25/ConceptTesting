# Retrieval-Augmented Fine-Tuning for Improving Retrieve-and-Edit Based Assertion Generation

Reviewed 2026-10-15. Full text read: 24 pages / 21,398 extracted words. Source status: public implementation. Reproduction: conditional.

## Why it matches

EditAS2 retrieves a similar test-assert pair, represents the differences between input and retrieved focal-tests as edit operations, then fine-tunes CodeT5 to edit the prototype assertion. It evaluates on Defects4J 2.0.0 and reports bug-finding behavior on buggy/fixed versions. Most useful for this project: it directly evaluates **Qwen2.5-Coder-7B-Instruct** with a chain-of-thought prompt, so the same local model can be evaluated on the paper’s assertion-generation datasets. The reported Qwen scores are 31.68% accuracy / 17.79% CodeBLEU on Dataatlas and 12.07% / 8.48% on Dataintegration. The paper does not report Qwen bug-finding results on Defects4J.

## Result quality and limits

Main EditAS2 uses CodeT5-base (223M), reaches 64.37% / 54.91% exact assertion accuracy on the two in-project test sets and 19.20% / 26.03% cross-project. Defects4J BugFound averages 20.1 bugs with EvoSuite prefixes and 27 with developer-provided prefixes; unique bug totals 36/19. However, EvoSuite-generated assertions compile only 30.97% of the time and bug-finding precision is 0.42%. Primary dataset train/test splits are random rather than project-disjoint. The cross-project set avoids project overlap but performance drops sharply.

## Artifact and feasibility

The paper links Zenodo 10.5281/zenodo.15118614. API metadata confirms the matching title, CC BY 4.0 and a 1.94 GB `EditAs2.zip` archive. The paper says the archive contains datasets, source, trained model and outputs; archive contents/checkpoints were not downloaded in this audit. A matching public GitHub source snapshot was downloaded (139 MB; commit `47b1a657857c23c6a5e17958364723a8bbb4092f`; SHA-256 `9ab41f35e45219332ef9bd413630192b20b5ad67ede5cff8c1152ba8b49024c9`) and selected README/model/config/training/inference/evaluator files were statically inspected. It contains substantive code, Defects4J metadata, generated tests and evaluator. The root has no explicit software license. Scripts hard-code `/codet5-base-path` and `datapath`; documented environment is old PyTorch 1.10.1/CUDA 11.3. No code was executed or changed.

## Recommendation

Top tier for a low-cost own-model test: reproduce the paper’s exact Qwen2.5-Coder-7B-Instruct CoT inference route on the open assertion datasets and compare to their published metrics. For Defects4J bug-finding, use the authors’ EditAS2/CodeT5 route; do not attribute a Qwen Defects4J result to the paper. Before reusing the author repository beyond research inspection, clarify its software license.

Full text SHA-256: `85ea6226f3604b6e17e2dbccf832c87f14e385a974b4cb4600423df2639a16b9`. Read all 1,714 extracted lines in consecutive chunks, including references and appendices. No model/API calls, code execution, or reproduction.
