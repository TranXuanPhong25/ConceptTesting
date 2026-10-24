# v53_validity_smallscope CHANGELOG

## 2026-10-24 (Claude)
Folder created for the next experiment of the v48→v52 line. Only $0 diagnostics so far (DIAGNOSTICS.md, two read-only
scripts copied from the session scratchpad). No PREREG, no model call yet.
Stage 1 PREREG + `validity.py` (prompts/score). Prompts per distinct problem (24) × {concept, open}; the concept prompt has
no RELATION examples (the D1 relations come from this dev set). Next: Codex review of PREREG/script, then 48 Sonnet calls.
Amendment 1 after Codex review (2 must-fix, 5 should-fix): `lines` control arm, F1b-faithful `open`, shared caller-only
rules, strict bool, public drop rule for `tool`, set-difference losses, verdict blocked on missing/unparseable answers,
absolute per-oracle safety gate. Smoke on task 87 (300 inputs): relation check accepts exactly the 122 relation-valid
inputs; non-bool and public-rejecting checks dropped. 72 prompts.

## 2026-10-24 — existing answers evaluated under mechanism-audit plan

Completed original scorer after independent source/transcript review; no new generation or source changes. Guarded
journal checks reviewed inputs before/after and withholds verdict on unresolved references. All33 tasks/24problems,
72answers and99model-arm evaluations complete, zero exclusions. Independent raw-reference audit:32,311/32,311rows,
zero missing/conflicting/unresolved. Concept/lines/open each catch12,842invalid, reject0valid/0exposing; numeric tool
catches1,854. Original primary verdict not promising (concept-open margin0, required+.10); taxonomy comparison also0.
Sonnet FA56→0 in all3LLMarms, Qwen145→108, no confirmed task gained/lost. See RESULTS.md and
../concept_mechanism_20261024/ for reproducibility, resource and protocol limits. Stage2 not launched.
Stage 1 run: 72 Sonnet answers, score: concept = lines = open = recall 1.000, 0 valid/exposing rejected; tool 0.144.
Registered verdict not promising (ceiling, margin 0). Sonnet defn FA 56 → 0 with any LLM filter. RESULTS.md.

## 2026-10-24 — Stage 2 (small-scope inputs) launched
PREREG_STAGE2.md + self-review amendment 1 (Codex out of quota; user asked Claude to review). `smallscope.py`
prompts/score. 17 batched Sonnet subagents (9 oracle: 18 problems × k=3; 8 generator: 24 problems × scope/plain), all
transcripts = Read own prompts + Write own answers only, 102/102 answers. Smoke: every generator runs (122–290 inputs,
0 arity drops); typed/random candidate lists built. Full score running.
Stage 2 score done: scope 18 / plain 24 / typed 17 / random_small 21 / universe 22 confirmed tasks; verdict not promising
(scope − plain = −6). RESULTS_STAGE2.md. Diagnostic for 161 FA (common-mode oracle error) under stage2/diag161/.
