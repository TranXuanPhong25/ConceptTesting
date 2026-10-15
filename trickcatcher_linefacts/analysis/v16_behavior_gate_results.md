# v16_behavior_ready — proposal gate

20-task design dev proposal smoke; not efficacy evaluation

Representation gate 17/20; concept gate **0/20**, required 10: **failed**.

Accepted obligations: 6; checked cards: 0; shown: 0.
Generation rows: 0; scored: False. D_IO is unmeasured when no score exists.

| Task | Obligations | Checked cards | Shown | Rejections |
|---|---:|---:|---:|---|
| 27 | 0 | 0 | 0 | {"DSL operator/arity": 1, "'R0'": 4} |
| 31 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 2} |
| 51 | 5 | 0 | 0 | {"relation must connect input and result": 1, "DSL depth/type": 1} |
| 56 | 0 | 0 | 0 | {"relation must connect input and result": 5, "quote not verbatim docstring": 1, "'R0'": 1} |
| 57 | 0 | 0 | 0 | {"DSL operator/arity": 1, "'R0'": 1} |
| 59 | 0 | 0 | 0 | {"DSL operator/arity": 2, "relation must connect input and result": 2, "'R0'": 6} |
| 63 | 0 | 0 | 0 | {"DSL operator/arity": 5, "quote not verbatim docstring": 1, "'R0'": 6} |
| 76 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 1} |
| 78 | 0 | 0 | 0 | {"quote not verbatim docstring": 4, "relation must connect input and result": 2, "'R0'": 1} |
| 85 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 4} |
| 91 | 0 | 0 | 0 | {"quote not verbatim docstring": 1, "'R0'": 3} |
| 94 | 0 | 0 | 0 | {"relation must connect input and result": 5, "DSL operator/arity": 1, "'R0'": 5} |
| 98 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 2} |
| 110 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 6} |
| 118 | 0 | 0 | 0 | {"relation must connect input and result": 3, "quote not verbatim docstring": 3, "'R0'": 1} |
| 126 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 1} |
| 136 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 1} |
| 144 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 1} |
| 149 | 0 | 0 | 0 | {"spec_parse": 1, "'R0'": 1} |
| 152 | 1 | 0 | 0 | {"result in input predicate": 2, "quote not verbatim docstring": 3, "'M1'": 1} |

Actual request ledger: {"logical_proposal_requests": 40, "successful_new_requests": 40, "unique_success_keys": 40, "cache_hits": 3, "failed_attempts": 0, "actual_input_tokens": 35582, "actual_output_tokens": 23251, "request_seconds_sum": 881.4146032880526}.

Rejection counts: {"DSL operator/arity": 10, "'R0'": 47, "spec_parse": 9, "relation must connect input and result": 18, "DSL depth/type": 1, "quote not verbatim docstring": 13, "result in input predicate": 2, "'M1'": 1}.

Unsupported operator mentions in raw response text (occurrences, not card counts): {"mod": 13, "map": 7, "starts_with": 1, "split": 1, "filter": 9, "tuple": 1, "fibfib": 9, "range": 2, "digits": 1, "largest_prime": 1, "pow": 1, "compare": 1, "largest_prime_factor": 1, "is_prime": 1, "flip_case": 1}.

First attempt stopped when binding prompt construction lazily imported tracer in a thread; SIGALRM registration needs the main thread. Three exact spec responses were cached. The external resume preloaded behavior/tracer on main thread, verified original source hashes and reused exact caches. No pipeline source, prompts, validators, seeds or budgets changed.

A gate failure measures proposal/mechanism feasibility, not whether semantic concepts improve detection. No canonical/reference scores feed this proposal stage. Schema/quotation/binding/predicate rejections need a separately registered future revision; do not relax this run or start generation to obtain a result.
