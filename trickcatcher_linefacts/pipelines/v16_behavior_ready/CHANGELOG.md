# v16_behavior_ready

Copy of v16_behavior_compact before any model output. Hardens malformed JSON container/DSL/ID
rejections so a syntactically valid but schema-invalid Qwen response is recorded as rejection.
No extra model requests or repair calls. Model schema, semantics, operators, replay, seeds, budgets,
cohort and gates unchanged. Older source/output copies remain untouched. CPU audit re-run fresh.
