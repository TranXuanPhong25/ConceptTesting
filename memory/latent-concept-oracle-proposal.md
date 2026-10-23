---
name: latent-concept-oracle-proposal
description: 2026-10-23 literature search → implemented as v51, NO-GO (see v51-latent-concept); concept-bottleneck probes on hidden states as per-input oracle
metadata:
  type: project
---

2026-10-23 (Claude), user: "tìm hướng mới không liên quan đến các pp hiện có nhưng vẫn concept centric, tự research paper".

**Proposal (not implemented, needs go-ahead):** freeze Qwen2.5-Coder-7B, read hidden states on (spec, input, PUT output),
train linear concept probes for human-defined *discrepancy concepts* (missing/extra element, order, off-by-one,
type/shape, crash, boundary-input mishandled) with labels computed by tool (canonical vs mutants on tasks disjoint from
eval), aggregate through a concept bottleneck into "output wrong" → rank a Hypothesis-sampled pool (v41 pool).
Controls: direct correctness probe, placebo bottleneck (permuted concept labels, ConceptCoder Table 6 style),
random-k, likelihood/length baseline. Metric = v41/v42 selection lift.

- Literature: program-level correctness probes exist (2512.07404 LAT, Qwen2.5-Coder-7B, code sanadlab/code-repe;
  2606.14530 pre-generation AUC .93; ICML'26 steering 1.5B/7B MBPP+; 2609.13975 line-level; SAE 2505.10375,
  2510.02917). Found none for per-input test oracles or a behavioural concept bottleneck for code.
- Repo prior art: v45 verbal in-head judge (abstains 66–83%), v27 verbal Codex oracle, concept_sft_harness (concept
  head SFT, stopped for compute, no results). No probing/steering work in repo.
- Second option: concept steering vectors for test generation (no test-gen paper found), lower priority because input
  reach is not the bottleneck (v41). Rejected: FCA lattice (overlaps v41/v44), CD-CAT diagnosis (selection ≈ random,
  v47), SeGa-style requirement KB (2604.23509; overlaps v24).

**How to apply:** if the user approves, start with a CPU/small-model gate (torch not installed locally) or a new Kaggle
notebook (never edit the existing one); PREREG + independent review before scoring. Related: [[v41-iorel]],
[[v42-v45-mutoracle]], [[thesis-concept-requirement]], [[check-version-tree-before-proposing]].
