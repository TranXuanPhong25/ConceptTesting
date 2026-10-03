# DFUZZ concept pilot — plan agreed after a 4-way debate (2026-10-01)

Debaters: concept (gap cards), docstring/API docs, knowledge base/retrieval, skeptic/methodologist; two rounds.
Infra facts (agent, verified): image `dfuzz:arm64` (torch 2.2.0 py3.8, TF 2.15 `tensorflow-cpu-aws` py3.9), no rule-4 stop;
31/33 CPU-checkable reproducers reproduce on arm64 (`run/REPLAY.md`); the repo ships no executor/oracle;
`gen_program/genPrograms.py` prints the API key on every request → only a dummy key in any config, the real token is
attached inside a wrapper and never printed.

## Consensus
- The only contrast that 3 of 4 debaters expect to show a real effect: WHERE TO LOOK — choosing which
  (parameter, edge case) pairs get the call budget from tool-computed guard gaps, with DFUZZ's prompt held fixed.
- Prompt-text content (evidence blocks, concept cards vs placebo, more docs) is expected to be null, as in MAGMA.
- Docstring direction reduced to one optional dose arm (untruncated `help()`; DFUZZ keeps `[:10]`); its doc-derived
  D1/D2 oracle was dropped (no knowable false-positive rate; maintainers closed 20+/24 TF issues as stale/misuse).
- Knowledge base direction kept as a sampling stratum (pre-2.15 TFSA history: 11/19 bug raw ops, RR≈4, OR≈8, post hoc)
  and as part of the guard index; evidence text expected null.

## Gap definition (tool-only, no LLM; tree-sitter on TF v2.15 / torch v2.2 sources)
A parameter role of the target API is a gap when it is
1. constrained in the op's shape function only (eager mode runs the kernel without shape inference — verify on 2.15 first), or
2. guarded in a sibling op (V2 / Resource* / out= variant, param-name Jaccard ≥ 0.6) but not in the target kernel, or
3. READ before any guard on it in the target kernel (order-aware, e.g. `draw_bounding_box_op.cc` reads
   `images.dim_size(3)` at line 61 before `OP_REQUIRES(images.dims()==4)` at line 63).
Each gap maps to one of DFUZZ's released edge cases (146 / 21 type patterns) — no new edge-case vocabulary.

## Arms (run sequentially; same frozen seed per API; same edge-case pool; 8 calls per API incl. repairs; T=0 as in DFUZZ)
| arm | what | isolates |
|---|---|---|
| M0 | non-LLM type-keyed argument swap from the same edge-case pool ($0) | does the LLM add anything |
| M1 | DFUZZ Fig. 7 prompt verbatim, DFUZZ's own selection | reference (the paper) |
| M2 | M1 prompt, benign condition of equal length instead of the edge case | edge-case text content (DFUZZ's untested claim) |
| M3 | gap-ranked (parameter, edge case) selection, M1 prompt unchanged | **where to look — primary** |
| M4 | M3 + ≤2 repairs matched to the rejecting check (target check fired → gap false, move on) | targeted repair lever |
| M5 (optional, if budget) | M1 with untruncated `help()` | documentation dose |
| A/A | M1 again on 40 APIs | noise floor |

## Sample
APIs with ≥1 gap and a seed that runs on arm64; strata: raw_ops with pre-2.15 TFSA history / other raw_ops / torch.
Missing seeds regenerated once with DFUZZ Alg. 1 (≈$0.5), then frozen and shared by all arms.
Excluded from the primary sample: the 37 known-bug APIs and aliases (positive-control stratum for the harness only);
sensitivity analysis also drops their sibling families. Reproducers never appear in any prompt.

## Oracle and metrics (pre-registered)
- Crash = SIGSEGV/BUS/FPE/ILL/ABRT or torch INTERNAL ASSERT, faulthandler frame at the target call, reproduced 3/3 in
  fresh processes. Not crashes: exit 137, timeouts, programs that abort themselves. Report CHECK-aborts and
  memory-safety crashes separately. Secondary: two fresh runs disagree (uninitialised memory, cf. `fft2(dim=[])` on arm64).
- Primary: per API, ≥1 crash among its 8 mutants; exact McNemar M3 vs M1.
- Mechanism (fires on every program, gives power): share of mutants rejected by the target's own check; paired
  Wilcoxon M3 vs M1.
- Secondaries, Holm-corrected: M1 vs M0, M2 vs M1, M4 vs M3, M5 vs M1, TFSA-stratum interaction; unique crash
  signatures per 1,000 calls (dedup by CHECK file:line or top native frame).

## Phases and stopping rules
- Phase 0 ($0): eager vs `tf.function` probe on ~5 ops (TF 2.15); gap extraction; build sample frame.
  Stop if gaps exist on < 50% of seeded APIs.
- Phase 1 (40 APIs, ≈$2-3): stop if pooled crash APIs across all arms < 4, or the gap's own check fires on > 60% of
  M3 mutants, or M3 does not cut own-check rejections by ≥ 10 pts vs M1. Drop M2/M5 if their crash sets ⊆ M1's.
- Phase 2: size N (≤ 200) from Phase-1 discordance; analyse once. Hard budget stop $18.
- Go: M3 beats M1 by ≥ 8 pts at p < 0.05, holds without the TFSA stratum and without sibling families, and M0 at equal
  wall-clock does not match M3. Adopt repair if M4 beats M3 by ≥ 8 pts.

## Open disagreements (recorded, not resolved)
- Temperature: T=0 (DFUZZ fidelity, KB debater) vs T=1.0 (concept, skeptic). Chosen: T=0; diversity comes from
  distinct (parameter, edge case) prompts; A/A measures residual nondeterminism.
- Skeptic's preferred primary was content-vs-placebo (gap card text vs another API's card); kept implicit via M2 and
  dropped as primary because all three proposers expect text effects to be null.

## Phase 0b amendment (post hoc, exploratory) — 2026-10-02, written before any Phase 0b gap number was computed

**Status: post hoc.** Phase 0's pre-registered stop fired (33/1,799 seeded APIs with a gap, frame 14). The user chose to
continue knowing this changes the rules after seeing Phase 0 data. Every Phase 0b / Phase 1 result is exploratory and
is labelled so; none of it can confirm the pre-registered hypothesis. Phase 0 outputs are kept unchanged; Phase 0b
writes `_0b` files. DFUZZ upstream files stay untouched. Budget for this continuation: hard cap $8 (`BUDGET_CAP=8`).
Only two things change: the edge-case vocabulary (V0b) and the extractor reach (X0b). Gap kinds 1-3, guard categories,
protection logic and block scoping are unchanged.

### V0b: new edge cases (`run/edgecases_ext.py`; tool-derived from one gap record each, no LLM)
Instantiated per gap from its `need`, its read site and its DFUZZ role type; written in DFUZZ's individual-mutator
style and inserted unchanged into Fig. 7 (`The parameter `<VAR>` in `<API>` satisfies the requirement of "<REQ>".`).
`R(k)` = "A tensor with 0 dimensions (a scalar)" for k=0, "A 1-dimensional tensor (vector)" for k=1,
"A tensor with {k} dimensions" for k>=2. `ph` = DFUZZ placeholder of the role type (int/scalar/float/bool/list).

Tensor-typed roles:
| id | applies to | text |
|---|---|---|
| T-rm | need rank_ge m (m>=1) | R(m-1) (for `dim_size(k)` reads: the dimension index k is out of range) |
| T-r0 | need rank_ge m (m>=2) | R(0) |
| T-req | need rank_eq n | R(n+1); and R(n-1) if n>=1 |
| T-rle | need rank_le n | R(n+1) |
| T-n1 | need numel_eq 1 (`scalar<T>()` read) | "A 1-dimensional tensor with 2 elements" |
| T-e0 | kind-3 read `dim_size(k)` / `sizes()[k]` with literal k | "A tensor with {k+1} dimensions where dimension {k} has size 0" |
| T-dv | kind-1 `WithValue(c->Dim(x, d), v)`, d and v literal | "A tensor where dimension {d} has size {v+1}" |
| T-mm | kind-1 merge of x with y (pair prompt, VAR = [x, y], placeholders replaced by names as DFUZZ does) | "tensor_1 and tensor_2 have the same number of dimensions, but dimension {dx} of tensor_1 has size 3 while dimension {dy} of tensor_2 has size 4" (dx/dy literal from the shape fn; else "the dimension that must match") |
| T-dx | kind-3 value read (`scalar/flat/vec<T>`) wrapped in `static_cast<int..>`/`reinterpret_cast`/`bit_cast`/`saturate_cast` (reinterpreted values only) | "A tensor containing the largest value its dtype can represent (e.g. 2147483647 for int32)"; plus, if T is floating, "A tensor containing NaN and infinity values" |

Non-tensor roles (Int / Scalar / Float / Bool / List typed by DFUZZ):
| id | applies to | text |
|---|---|---|
| S-t1 | need rank_eq 0 or numel_eq 1 (tensor-for-scalar) | "{ph}_1 is a 1-dimensional tensor with 2 elements instead of a single value" |
| S-tn | need rank_le n (tensor-for-scalar, e.g. `axis`) | "{ph}_1 is a {n+1}-dimensional tensor of integers, such as [[0]], instead of a single value" |
| S-s0 | need rank_ge m>=1 or rank_eq n>=1 (scalar-for-tensor) | "{ph}_1 is a single number (a 0-dimensional tensor) instead of a list" |
| S-sn | need rank_eq n>=1 | "{ph}_1 is a nested list with {n+1} levels, such as [[1, 2]], instead of a {n}-dimensional list" |
| S-ax | kind-3 read `x.dim_size(i)` / `x.sizes()[i]` whose index i is (via `GetAttr("a", &i)` or name) an Int role a | on role a: "int_1 is equal to the number of dimensions of `{x}` (an axis that does not exist)" |

Per gap the candidates are ordered: released best (Phase 0 mapping, if any), then V0b primary violations (T-rm, T-req,
T-rle, T-n1, T-dv, T-mm, S-*), then secondary probes (T-r0, T-e0, T-dx). No dtype-extreme case without a reinterpreting
read. A gap is **mapped** if its role is a DFUZZ parameter of the API and it has >=1 candidate (released or V0b).
Reported: mapped gaps with released-only vs released+V0b.

### X0b: extractor reach (`run/gaps_ext.py`, imports `gaps.py` unchanged; writes `gaps_0b.jsonl`, `gap_index_0b.json`, `gap_raw_{tf,torch}_0b.json`)
- X1 helper inlining depth 2 -> 4 (TF Compute expansion and torch expansion); a total-size cap per API stops further
  inlining (recorded, not a gap).
- X2 sparse checkout extended (symbol index only, never kernels): TF `tensorflow/core/framework/`, `tensorflow/core/util/`;
  torch `aten/src/ATen/*.{h,cpp}` (top level) and `c10/core/`.
- X3 cross-file resolution via one symbol index: an unresolved call resolves, in order, to a same-stem file, then a file
  in the caller's `#include` closure (depth <= 3, header plus its `.cc` twin), then the unique definition across the index.
- X4 class definitions merged across same-stem files (out-of-line `Foo::Compute` in `.cc` for a class declared in `.h`).
- X5 macro/template patterns seen among Phase 0's unresolved APIs: (a) function-like macros whose expansion (depth <= 4,
  argument substitution, `##` pasting) contains `REGISTER_KERNEL_BUILDER` (TF: `REGISTERn(UnaryOp|BinaryOp, CPU, "X", ..)`,
  `REGISTER_LINALG_OP`, `REGISTER_CPU_KERNEL_SEGMENT`, ...) or `TORCH_META_FUNC`/`TORCH_IMPL_FUNC` (torch:
  `CREATE_UNARY_FLOAT_META_FUNC`, `CREATE_*_TORCH_IMPL_FUNC`, ...) are expanded at their invocation sites; (b) template
  aliases `using A = B<..>;` / `typedef B<..> A;` resolve a registered class A to B.
- Precision: manual source review of a fresh random sample of >= 20 gap records that are new in `gaps_0b.jsonl`
  (not in `gaps.jsonl` by api/kind/param/cat), `random.Random(20261002)`, written to `out/gap_review_0b.jsonl` with
  citations. Precision < 50% is reported prominently; it is not a gate.

### Go/stop rule for Phase 0b (replaces the 50% rule)
Go to Phase 1 only if the frame has **>= 40 APIs** that (i) have >= 1 mapped gap, (ii) have a seed that runs clean on
arm64 and calls the target (oracle, `NOCREDS=1`), and (iii) are not among the 37 known-bug APIs, their aliases, or
their sibling families (TF `tf_family`; torch same base name incl. `torch.Tensor.X`/`X_`). Seeds are regenerated
(once, genPrograms, <= $0.5) only if frame < 40 <= frame + unseeded candidates. Otherwise stop and report.
If more than 40 qualify, 40 are drawn with `random.Random(20261002).sample` over the sorted frame.

### Phase 1 (only if go): arms, metrics and stop rules unchanged from the plan above
- Arms run: M0, M1 (two variants), M2, M3, A/A. M4 only if executor isolation is verified; M5 not run. T=0; 8 calls per
  API per arm; seeds frozen; LLM concurrency 1; all mutant execution under `NOCREDS=1`.
- M1-verbatim: DFUZZ's generator logic on the released data (incl. the `pattern[0][:-2]` overwrite: one individual
  tensor case). M1-restored: same logic on a scratch copy of `unique_mutators.json` keyed so the 54 `['tensor_1']` cases
  are used. Per API, 8 prompts drawn from the variant's prompt list with `random.Random(20261002)`.
- **M3 is compared against M1-restored** (closest vocabulary; pre-committed here). M3 = k <= 8 gap-ranked
  (parameter, edge case) prompts (gaps ordered kind 3, 1, 2; round-robin over gaps; candidate order above) followed by
  the first 8-k prompts of M1-restored's list, so M3 and M1-restored differ only in the gap slots.
- M2 = M1-restored's 8 prompts with the requirement replaced by a benign condition of equal length ("the same value as
  in the initial program", padded). A/A = M1-restored rerun. M0 = M3's (parameter, edge case) list realized without LLM
  by an AST argument swap with a value synthesized from the edge-case annotation (pairs without one are no-mutant).
- Primary: exact McNemar M3 vs M1-restored on per-API ">= 1 strict crash among 8 mutants"; M3 vs M1-verbatim reported as
  secondary. Mechanism: per-API share of mutants rejected by the target's own check, paired Wilcoxon M3 vs M1-restored.
- Stop rules exactly as in Phase 1 above (pooled crash APIs < 4; own check fires on > 60% of M3 mutants; M3 cuts own-check
  rejections by < 10 pts vs M1-restored). Crash signatures are compared with the 37 known bugs.
