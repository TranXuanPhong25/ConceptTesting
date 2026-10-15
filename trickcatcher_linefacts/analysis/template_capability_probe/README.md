# Synthetic template interface capability probe

Six declared requirements/models/examples in probe.py. Run only after the failed v17 gate.
Twelve separate Qwen requests compare parameter generation with choosing a supplied model ID.
No benchmark PUT/canonical code, no content repair, no detection claim. Choice positions fixed
by declared random seeds before responses. Both interfaces use 512 output tokens/request.
Generation also asks for one proposal; report semantic example match separately from evidence schema.

Results and limits: ../v17_template_results.md and .json. Raw cache/declared cases under
trickcatcher_linefacts/out/template_capability_probe (ignored). Replaying byte-identical requests
uses the original exact cache; do not treat cache hits as new independent trials.

```bash
python3 -B trickcatcher_linefacts/analysis/template_capability_probe/probe.py --prepare-only
# Requires the user's Qwen environment; consumes model calls on cache misses:
python3 -B trickcatcher_linefacts/analysis/template_capability_probe/probe.py --online
```

Observed: selection6/6, synthesis compiles5/6 and example-correct4/6, evidence-schema-valid2/6,
both example-correct and schema-valid1/6. Six selected synthetic examples do not establish general
requirement understanding, source reasoning or bug-detection gains. Prompts intentionally differ;
this is an interface probe, not a clean intervention on output syntax alone.
