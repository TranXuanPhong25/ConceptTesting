---
name: ckgfuzzer-paper-facts
description: CKGFuzzer (arXiv 2411.11532) verified method/eval facts; headline +8.73% coverage rests on a Table I typo (corrected ≈ +4.25%)
metadata:
  node_type: memory
  type: project
  originSessionId: 73fe6c73-8303-472c-a0d7-101fa0e48535
  modified: 2026-10-09T17:26:04.870Z
---

CKGFuzzer (Xu et al., arXiv 2411.11532v3, ICSE'25 companion; artifact github.com/security-pride/CKGFuzzer). Full PDF checked 2026-10-10.

- KG: Tree-sitter + CodeQL; nodes function / file / LIBRARY_FUNCTION, edges CONTAINS / CALLS / LIBRARY_CALLS, plus LLM summaries and two embedding indexes (NL, code; LlamaIndex + bge-small-en-v1.5). It has no state/precondition edges. The requires/establishes/clears schema in experiments/ckgfuzzer/graph.json is this repo's own addition.
- Compile repair draws on a KB of OSS-Fuzz driver samples + headers, not the KG. Pass rate: 57.39% → 77.19% (LLM-only) → 93.99%.
- The headline "+8.73% coverage" equals total covered branches vs PromptFuzz (28727 vs 26421). But the lcms CKGFuzzer cell says 4693 branches, while 46.93% × 7482 = 3511; every other cell matches. Corrected gain ≈ +4.25%; mean branch coverage 47.80% vs 45.53%. CKGFuzzer loses to PromptFuzz on libtiff and zlib.
- "84.4% less crash review" = 168/199 crashes auto-labelled as API misuse; precision was only spot-checked on 10% of the misuse cases.

**Why:** the repo notes (research/fulltext-batches/batch-05.md §84) repeat the 8.73% claim uncritically.
**How to apply:** if CKGFuzzer is cited or used as a base paper or baseline, quote the corrected figure and the typo rather than repeating 8.73%. See [[thesis-concept-requirement]].
