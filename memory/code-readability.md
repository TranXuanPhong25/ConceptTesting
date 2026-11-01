---
name: code-readability
description: User reads Java comfortably; prefers explicit Python, descriptive names and less shorthand
metadata:
  type: feedback
---

2026-10-31 user: quen đọc Java, thấy Python code trong final/ khó đọc vì shorthand
và tên biến quá ngắn. This is a durable style preference, not a request to change
benchmark logic or generated PUTs.

**Why:** names like a/b, da/db, p/r/t, mp/fp, fn/ns force the reader to reconstruct
meaning; reusing a/b for different data types is especially confusing.
**How to apply:** write explicit Python with descriptive snake_case names, named
intermediate steps, straightforward for/if blocks, focused functions and useful
type hints. Avoid dense/nested comprehensions and arbitrary abbreviations. Keep
language conventions; do not translate Python into Java syntax. Respect frozen
experiment source hashes and cached PUTs when doing any later readability refactor.
Audit for the current source: final/review/READABILITY.md.

2026-11-01 user also requests each run type in a separate submodule and every
pipeline stage as a class, to track behavior and add pipes later. Apply an explicit
run(context) contract and declarative stage dependencies; central orchestration
should not need another name-based if/else when adding an arm or stage. New entry
point final/modular/ implements this and documents insert_stage() examples.
