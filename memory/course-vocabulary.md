---
name: course-vocabulary
description: "test_slides/ course criteria are the default human-readable vocabulary for concepts, but NOT a hard constraint (user lifted it 2026-10-12)"
metadata:
  node_type: memory
  type: project
  originSessionId: 2dddac78-7845-4887-9c28-b6313bcf7c52
  modified: 2026-10-11T17:42:17.370Z
---

On 2026-10-10 the user gave `test_slides/` (UET-VNU testing course, 8 PDFs) as "the whole knowledge of the testing course", to decide how concepts can be human-understandable.

The course covers:
- black-box: BVA (min, min+, nom, max-, max; robust min-, max+; worst-case), equivalence classes (weak/strong, input AND output domains, special values), decision tables;
- control flow: C1 statement, C2 branch, C3 sub-condition, path, loop 0/1/2/k/n-1/n/n+1, function/call coverage;
- data flow: def / c-use / p-use, all-defs, all-uses, all-du-paths;
- mutation: ROR/AOR/COR/UOI (muJava), equivalent mutants, weak mutation (reach + infect);
- fault → error → failure; SBFL, delta debugging; static over- vs dynamic under-approximation; APR (plausible patch ≠ correct).
The slides contain no oracle / property / invariant / metamorphic / postcondition terms (checked 2026-10-12).

**Update 2026-10-12:** the user lifted the "concepts must use course vocabulary" constraint ("không sao nhé, k cần
constraint đấy") when discussing property concepts (structural / relational / boundary / algebraic / metamorphic),
which are mostly outside the slides.

**How to apply:** still phrase concepts in course terms when one fits (existing fact kinds keep their course anchors),
but concepts without a course anchor (e.g. property concepts) are allowed; do not reject a direction for lacking one.
Concepts must still be human-readable ([[thesis-concept-requirement]]). Related: [[line-concept-checklist]].
