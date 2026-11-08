# Historical naive packaging diagnostic

Packaging-repaired baseline: generated literal values remain unchanged; only statically proven argument wrapping is corrected. This is separate from the original admitted-input baseline and the fresh matched batch trial.

| Metric | Original naive | Packaging-repaired naive | Historical BVA |
|---|---:|---:|---:|
| Detected PUTs | 44 | 82 | 61 |
| Novel valid inputs | 1536 | 2758 | 1449 |
| Tasks with detection | 16 | 29 | 22 |

Of the original 30 BVA-only PUTs, 30 are now detected by the repaired naive inputs; 0 remain BVA-only relative to the repaired set.
BVA versus repaired naive: shared 61, BVA-only 0, naive-only 21, net BVA -21.

Repair summary: {'changed_raw_slots': 1250, 'changed_tasks': 64, 'decisions': {'unsupported_or_ambiguous_signature': 779, 'rewrap_single_argument': 1250, 'existing_binding_preserved': 841, 'unparseable_response': 3, 'unsupported_literal': 40, 'truncated_response_not_reparsed': 3, 'candidate_not_proven_compatible': 9, 'no_static_type_proof': 80}, 'new_model_calls': 0}.
Old naive detections lost: 0. Stable wrong-value witnesses: {'original_naive': 17, 'repaired_naive': 53, 'bva': 46}.

All 1,454 base-passing PUTs use the same historical full-two-repeat frozen scorer, corrected reference and 3 s timeout. No model calls, semantic value edits or oracle-guided repair selection. Raw-slot/proof receipts, authenticated original responses and the original baseline are preserved. Input/source hash checks and immutable replay passed.

This diagnostic does not isolate boundary guidance, writer visibility or call budget. Exact recovered/remaining/new/lost identities are in comparison.json.
