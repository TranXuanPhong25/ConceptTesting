# Artifact index — 2026-10-24

This audit implements P0/P1 of [the plan](../../PLAN_CONCEPT_MECHANISM_20261024.md). Local generated data exist; `out/` is gitignored. No keys or endpoint URLs are needed for this audit.

| Artifact | Exact location | Use and current limitation |
|---|---|---|
| v50 frozen protocol/source | `pipelines/v50_binding_revision/`; `analysis/v50_binding_revision_20261023/EVALUATION.md` | Original binding/revision diagnostic; eight seen fixtures, not a generalization benchmark |
| v50 run | `out/pipelines/v50_binding_revision/humaneval/revision8/` | 24 artifacts and generation freeze; complete transport state does not imply semantic success |
| v50 generation record | `revision8/{requests,artifacts,prepared,feedback,transitions,transport}/` | Read-only review inputs; inspect raw replies as well as admitted items |
| v53 protocol/scorer | `analysis/v53_validity_smallscope/{PREREG.md,validity.py}` | Amendment 1 includes concept/lines/open/tool; taxonomy comparison remains report-only |
| v53 generated answers | `out/analysis/v53_validity_smallscope/{problems.json,prompts/,answers/}` | 24 problems, 33 PUTs, 72 prompt/answer files; provenance review separate from file count |
| v49 execution/oracle inputs | `out/analysis/v49_defn_oracle/` | Frozen decisive universe and saved spec programs; hidden reference remains evaluator-only |
| Historical reports | `analysis/v34_ftplacebo_results.md`, `analysis/v47_concept_select/RESULTS.md`, `analysis/v49_defn_oracle/RESULTS.md`, v52/v54 reports | Original metrics and gates preserved; no pooled cross-cohort claim |
| Current inventory | `ARTIFACT_INVENTORY.json` | Hashes and bounded file coverage from `inventory.py`; no generated code execution |
| Concept definition | `CONCEPT_CONTRACT.md` | Operational semantics and checks, not an implemented new method |

Paths in the table are relative to `trickcatcher_linefacts/`, except paths beginning with `revision8/` (relative to the v50 run) and audit-owned filenames (relative to this folder).

Mechanical v50 verification: `revision.verify(full=True)` passed with the original pinned `/home/phong/.cache/concepttester/v50-venv/bin/python`. This checks frozen sources/dependencies, prepared pools, evaluator rubric, preparation approval, and v43/v40 parents. The independent inventory additionally matches every section of `generation_frozen.json`. No run-owned files are written by these checks.

At audit start, a narrow `/proc` scan found no active v50 revision controller or v53 validity scorer. No controller was restarted or endpoint requested. Ownership checks concern these two runners and do not assert that all unrelated sessions are idle.
