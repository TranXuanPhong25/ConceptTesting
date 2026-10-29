# V85 saved-generation owner audit

Descriptive audit of frozen generation; no new model calls, target execution, reference execution or final scoring.

Verified 8583 imported file hashes, archive, 113 prepared hashes and 113 completed generation pairs. Imported ledger prefix only; active requests are outside this audit.

| Adapter gate | Cards | Round1 hit | Round1 missed | Round2 requested | Selected | Delivered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| existing_v11_gap | 69 | 51 | 18 | 18 | 15 | 15 |
| line_reachability_only | 206 | 204 | 2 | 2 | 1 | 1 |

Counts after the first column are card/target counts, not independent tasks. Multiple targets can deliver the same input. Delivered only checks that the retained call appears in a final assertion; it does not validate the expected output.

The adapter joins a card to the first ranked v11 fact whose line lies in the retrieved span. When none exists it creates a STMT line-reachability gate. Round1 hits suppress round2 targeting of that card, even though reaching the line does not establish its semantic trigger.

Manual source-based examples (illustrative, not a measured semantic error rate):

- Task102: evidence `x % 2 == 0` is attached to the `y % 2` → `y // 2` mutant on the same line. The expressions differ; the gate tests a different operand/operator.
- Task110: index-out-of-bounds card at `lst1[i]` is attached to a `%` → `//` mutant in `lst1[i] % 2`. Mutation sensitivity does not test the required out-of-range index trigger.
- Task10: negative-sentinel card at literal `string[-1]` is attached to the true branch of `string[0] == string[-1]`. The saved source uses a literal last-element lookup, not a computed missing-item sentinel.

Saved v6 comparison: all113 query sources match byte-for-byte; 17 tasks keep the identical ordered card/site list. These are cached selection differences only. Exact rebind is unavailable: the portable snapshot omits the full original tool candidate pool. The selected prepared targets cannot reconstruct its eligibility/ranking.

Owner status at observation: `{"error_type": "RuntimeError", "stage": "blocked"}`. This report does not diagnose or resume the owner's controller. No final detection result is reported.

Reproduce from repo root: `python python_bug_concepts/retrieval_v7/owner_audit.py --check` verifies the existing report/source hashes without reading changed owner status. Run without `--check` only for a first report; existing differing outputs are never overwritten.

Machine-readable per-task/card funnel, source-span checks and saved v6 differences are in `RESULTS.json`; `SOURCE_HASHES.json` records every interpreted input plus the archive/manifest/code hashes. Integrity hashing reads imported reference bytes opaquely but never interprets their outcomes.
