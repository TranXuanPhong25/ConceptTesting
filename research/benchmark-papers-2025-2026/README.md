# Benchmark paper screening (2025–2026)

Start with [REPORT.md](REPORT.md). The folder contains **500 screening candidates**, not 500 verified suitable/reproducible papers.

- [Primary-source shortlist](SHORTLIST.md)
- [Defects4J/BugsInPy core](CORE_DEFECTS4J_BUGSINPY.md), [SWT reproduction](SWT_REPRODUCTION.md), [APR/fault-analysis support](REPAIR_FAULT_ANALYSIS_SUPPORT.md)
- [500 candidate catalog](CATALOG_500.md)
- [CSV](screened_500.csv), [JSON](screened_500.json)
- [Search counts](discovery_summary.json), [screening counts](screening_summary.json)

Every inspected/candidate paper has its own folder under `papers/`. `discovery/` contains OpenAlex response metadata and query URLs for audit. `discover.py`, `reviewed.py`, and `export_catalog.py` only retrieve/format bibliographic evidence; they do not implement a paper method.

No author implementation is modified; no model or benchmark has been run.
