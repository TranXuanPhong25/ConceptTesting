# Evaluating Developer-written Unit Test Case Reduction for Java -- A Replication Study

Reviewed 2026-10-15. Full text read: 3,781 words / 12 pages. Public author source checked. Reproduction: conditional.

The paper replicates a C# test-reduction study with ReduJavator and Java tests: 30 Defects4J failure tests plus 30 mutant tests from six projects. For Defects4J, average test reduction is 69.42%; non-tree statements are removed more often in count, but probability of removal is not significantly higher than for tree statements (paired Wilcoxon p=.5426). Similar mutant test results (p=.5731). This is test minimization/FL support, not issue-to-test generation, root-cause labeling or oracle correctness.

Author source is public at [ReduJavator](https://github.com/amchristi/ReduJavator), pinned in downloaded archive to `00fc681edf99e975959b879376e8491327a75154` (SHA-256 `666e4a3cb5599377af1568751ec80dd3458d99de9c0e738ca56b26669b4a7cef`). Static inspection found Java source and Maven config, but no explicit license. `TestObject.java` hardcodes author machine paths and has only a small default project list; `Main.java` selects one configured case by default. `Observations.txt` documents prior Maven/Gradle build issues and a previous false pass/fail problem from too-short polling. Exact paper rerun needs reconstructing all study cases and project environments. No code run/modified.

Full-text SHA-256 `7894581d8d84ed6c738f5195dc6913a48ff975bdf746be8987a018748c62cd48`. Read all 1,013 extracted lines in consecutive chunks.
