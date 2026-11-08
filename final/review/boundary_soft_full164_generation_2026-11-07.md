# Full HumanEval soft BVA — generation audit

Generation is complete and globally frozen. Native evaluation is still running;
this report contains no detection result or claim of domain validity.
Source: `final/out/boundary_soft_humaneval164_resume_20261107_195417`.

| Metric | Count |
|---|---:|
| Requested tasks | 164 |
| Eligible tasks | 157 |
| Received generation calls | 1454 |
| Nominal input cap across eligible tasks | 3140 |
| Parseable records within each PUT allocation | 3050 |
| Encoded calls before cross-PUT deduplication | 3034 |
| Duplicate calls across PUTs within a task | 1550 |
| Retained calls before reference/domain/base filtering | 1484 |

51.1% of encoded calls repeat a call proposed for another PUT of the same
task. They add no distinct test to the shared suite. Deduplication does not remove
a unique value; the lost opportunity is unused generation budget under fixed
per-PUT shares and no redistribution. This audit does not establish how many bugs
additional distinct calls would expose.

All1454registered request identities and received checksums were validated. All164
input batches match the recorded global freeze. There are no eligible tasks with
zero retained encoded calls. Per-PUT statuses:1402generated,44invalid_generation,
8no_inputs. Invalid calls:31Markdown-fenced,10invalid JSON,1invalid envelope,
2truncated. Individual record rejects:14unknown/invalid parameter mappings and
2invalid input records. No scoring or format-recovery rerun is performed here.

Known generation usage:1,311,541prompt +
111,944completion =
1,423,485tokens. Count the493imported response
checkpoints only once in these1454calls. Historical unknown transport attempts
and notebook keepalive costs remain separately recorded in their source runs.

This is the full multi-PUT configuration:20inputs per task divided across its
base-passing PUTs,typically2–3per PUT. The earlier10task diagnostic used20inputs
for one selected PUT/task;its results do not directly describe this allocation.
No precision tool,concept-request writer,legacy selector or new plain control is
enabled. The164tasks are a previously used frozen LLM-generated cohort,not a
new held-out efficacy set. All statistics here are generation-only.
