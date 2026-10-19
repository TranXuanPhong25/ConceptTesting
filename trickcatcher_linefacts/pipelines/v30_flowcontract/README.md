# v30_flowcontract — CPU-only repair of bounded tool disclosure

Copied from best v7, then ported the v21 implemented services. See PARENT.json/PORTS.json and
analysis/v21_failure_audit/CONTRACT_FIX_PLAN.md. Online clients and inherited experiment CLIs fail immediately.

The package advertises the same per-tool schema that the charged dispatcher validates. The outer agent reply
validator intentionally accepts object-shaped invalid actions, so one invalid action does not erase valid siblings.
IDs/names cap4, check_path sequence cap64, exact-integer radius0..3. Errors report field/limit/round/action and
optional hypothesis linkage. Invalid recognizable replay reserves the same logical execution slot as v21; no
physical execution occurs before validation. No automatic truncation/splitting/repair.

History projection retains all error summaries even if detailed feedback after the third slot is omitted. Structural
semantics, witness selection, semantic hypotheses and action/model-call ceilings are inherited, not improved by this
repair. Strict scalar/collection typing rejects bool/float integer IDs/radius and malformed false/string collections.
JSON model actions retain their exact request/resume checks; unsupported non-JSON host values are logged as static
rejection markers, so different unsupported host objects can share a marker. Cache integrity errors remain fatal.

Run the meaningful CPU checks with the dedicated interpreter in config.json:

```
PYTHONPATH=. <V4_PYTHON> -B -m pytest -q trickcatcher_linefacts/pipelines/v30_flowcontract/test_flowtools.py trickcatcher_linefacts/pipelines/v30_flowcontract/test_tool_contract.py
```

generate_fixture is a hand-authored fake-response interface test on authored fixtures only. No new Qwen/other model
call, benchmark result, efficacy claim or semantic-gate success is provided by this version.
