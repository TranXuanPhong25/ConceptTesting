# CHANGELOG v26_proporacle

Plan: `trickcatcher_linefacts/PLAN_PROPERTY_ORACLE.md`. Parent: copy of `pipelines/v21_flowtools` (PARENT.json);
best-on-dev remains v7.

## 2026-10-18 — oracle comparison on fixed input pools

- New: `oracle_run.py` (fixed pools, 4 oracle arms, sandboxed model property/metamorphic code, freeze, scoring),
  `prop_worker.py`, fake-client test in `test_flowtools.py` (28/28 pass). `config.json`: VERSION, `oracle` block,
  extra `flowrun.max_tokens` stages. Other files unchanged from the parent.
- PREREG: "v26_proporacle preregistration" section appended before any output.
- Amendment 1: bare JSON arrays wrapped for all arms (format only); attempt 1 archived.
- Results: `analysis/v26_proporacle_results.md`. pilot20 precision exact_spec 0.213, exact_code 0.197, property 0.148,
  metamorphic 0.179; 19% of property checks fail on the reference output. Negative by the registered rule; not promoted.
