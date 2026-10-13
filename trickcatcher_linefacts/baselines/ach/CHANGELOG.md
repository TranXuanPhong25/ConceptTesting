# CHANGELOG

## 2026-10-14 — held-out final readiness

- Final run uses explicit `--k 3 --llm-budget 8 --max-tests 20`; larger caps rejected. Historical CLI defaults stay 6 calls/10 assertions.
- Export assertions in generation order; record dropped count. Keep original prompt and method.
- Visible held-out bundles use module-level entry wrappers; no private data enters generation.
- Fake client follows the wrapper to `Solution` methods when constructing a scripted fault.
