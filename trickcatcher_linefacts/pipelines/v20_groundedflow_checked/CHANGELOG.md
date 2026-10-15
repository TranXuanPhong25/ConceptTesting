# v20_groundedflow_checked — cpu_v2, 2026-10-15

New copy after independent post-implementation audit found blockers in frozen cpu_v1: scope-insensitive lambda graph, function-name builtin shadowing, static may-flow promoted to concrete identity, unrelated local loss.
Lexically scoped def-use, reject entry shadowing, conditional/Boolean provenance unsupported, original-argument identity + per-value eligible loss + transparent collection transport and final count match required. Derived-input associations abstain rather than claim exact provenance.28 preregistered fixtures include reviewer counterexamples. CPU-only, no D_IO. Original frozen folder/outputs unchanged.
