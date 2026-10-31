# Targeted-unit-test benchmark artifact audit

Checked 2026-10-15. Official paper: [LIPIcs ESEM 2026.47](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.47).

- Supplementary software link: [Zenodo 10.5281/zenodo.20283766](https://doi.org/10.5281/zenodo.20283766). Zenodo API record title exactly matches the paper, reports CC BY 4.0, and provides `ESEM-2026.zip` (2,164,140,463 bytes; MD5 `34fd257d4c0c9b77c4b202856d03fda1`).
- Retrieved the ZIP root README by HTTP byte-range reads, without downloading/extracting the complete archive. It identifies itself as the paper's replication package and lists `run_evaluation.py`, `build_image.py`, Docker/JDK images, `benchmarks/` with 210 real Java bugs across 66 projects, and a random `--case-count` option for subsets.
- The article's Data Availability section says the 210-bug benchmark, containerized execution setup and evaluation scripts are public. README says agents are configured through OpenCode, Claude Code or OpenHands and a default model.
- The archive's complete central directory is about 86 MB and the archive is 2.16 GB. This audit did not enumerate the full package, inspect the runner source, or execute any code; treat implementation verification as partial.
- The benchmark targets runtime exceptions given the exact target exception and source line. It includes Defects4J-derived items plus other sources and 41 post-cutoff bugs. The oracle checks exception type and top-of-stack target location, not a pre-fix fail/post-fix pass.
- No task/model calls or reproduction run. Full review: `../../../../audit/reviews/069.json`.
