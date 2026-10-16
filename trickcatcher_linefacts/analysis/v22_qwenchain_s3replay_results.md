# S3 isolation diagnostic — 2026-10-16

Exact accepted real-Qwen S1/S2 parents from v21 singlejson f11/f12/f13 replayed, validated and provenance-hashed. No content rewrite; no new S1/S2 calls. All source/parent/generation snapshots verified. Frozen treatment/schema/prompts identical to v22 except VERSION/phase.

3/3 new S3 completions;5,352 input/1,029 output tokens;3 tokenizer metadata calls,0 errors. Six imported parent records are not charged again. No S4/S5/generation/native execution/D_IO.

All3 new S3 artifacts rejected: f11 empty_ok; f12/f13 invalid root status=mismatch. No output repairs.

Qualitative, provisional observations: f11 compares equivalent relations and reports consistency, but status=ok with no items violates terminal convention. f12 now explicitly identifies the unpermitted length guard, whereas old S3 said consistent; this is raw candidate evidence, not accepted-artifact success. Its divergence condition len(xs)>2 alone is insufficient to guarantee differing outputs (must also satisfy the required True condition), so trigger precision remains unproven. f13 recognizes undefined suitable yet calls it mismatch instead of preserving unknown: ambiguity handling remains weak.

This seen-fixture diagnostic isolates S3 from new upstream ID errors; it does not establish semantic accuracy, successful end-to-end correction or generalization. Human semantic gate pending. No additional retries/content changes implied.
