# TrickCatcher Gemini concept pilot

This is a controlled **direct-input prompt ablation** on the EvalPlus Python PUTs released with [TrickCatcher](https://github.com/RinCloud/TrickCatcher), not a reproduction of its full program-variant/input-generator pipeline. The baseline uses the artifact's `geninput_direct_sys` and `geninput_usr` templates unchanged. `generic` first asks Gemini for edge-case ideas; `concept` first asks Gemini for a structured property, suspicious code shortcut, and separating input relation. The generated plan is appended to the same official input prompt. The model never sees the canonical solution or EvalPlus contract.

Use the pinned artifact commit `a0d285a77efff7c93fc280d606497d9de5e1defe`. A sparse checkout needs `Datasets/EvalPlus/PUTs` and `Datasets/EvalPlus/PromptTemplates`. HumanEval/0 is excluded because the official prompt's demonstration reproduces it.

The runner verifies both official prompt-template SHA-256 hashes before any model call. New output rows mark `baseline` as `verbatim_original` and every other arm as a prompt extension. These labels refer to **TrickCatcher**, not ConceptCoder; see the [prompt-provenance audit](../research/conceptcoder-prompt-provenance.md).

```bash
source scripts/vertex_env.sh
for arm in baseline generic concept; do
  .venv/bin/python -m trickcatcher_pilot.run --arm "$arm" \
    --start 1 --limit 12 --resume \
    --out "/tmp/trickcatcher_${arm}_12.jsonl"
  /tmp/trickcatcher-concept-venv/bin/python -m trickcatcher_pilot.evaluate \
    --pred "/tmp/trickcatcher_${arm}_12.jsonl" \
    --out "/tmp/trickcatcher_${arm}_12_eval.jsonl"
done
.venv/bin/python -m trickcatcher_pilot.stats \
  --baseline /tmp/trickcatcher_baseline_12_eval.jsonl \
  --generic /tmp/trickcatcher_generic_12_eval.jsonl \
  --concept /tmp/trickcatcher_concept_12_eval.jsonl
```

The evaluator requires `evalplus==0.3.1` in its Python environment. It parses generated inputs with `ast.literal_eval`, applies the official EvalPlus contract, and runs the canonical solution and PUT in separate timed processes. Canonical output is private evaluation data; it is not an input-generation hint. A generated input exposes a bug only if it passes the contract, the canonical code returns successfully, and the PUT raises or returns a different value. The saved evaluation JSONL contains the reference result and concrete witness input for each exposure.

The [first 12-task pilot](../research/trickcatcher-concept-gemini-pilot-2026-09-25.md) found no difference from equal-budget generic planning. The later [66-task validation](../research/trickcatcher-concept-validation-2026-09-25.md), using the same concept schema, found 49 exposed tasks for concept versus 39 for generic planning. A same-signature shuffled-card placebo also underperformed correct concepts. This is a ConceptCoder-inspired prompt intermediate, not a trained ConceptCoder classifier.

The [fresh 30-PUT static-vs-self comparison](../research/trickcatcher-static-vs-self-concept-2026-09-25.md) adds `static_concept`: a deterministic AST/docstring card in the same three-field schema. It found 17/30 exposed PUTs with the one-call official baseline, 20/30 with static concepts (one Gemini call/PUT), 22/30 with Gemini-self-inferred concepts (two calls/PUT), and 19/30 with generic planning (two calls/PUT). None of these paired differences was statistically decisive. Run the static arm with `--arm static_concept`; it requires no plan file and records triggered AST rule IDs in `static_rules`.

The [C++ ConceptCoder-label pilot](../research/trickcatcher-conceptcoder-cpp-2026-09-25.md) uses TrickCatcher's **original TrickyBugs C++ direct-input prompt** and source-derived statement labels from the released ConceptCoder VD annotator. Its 26-task comparison found 7/26 spec-valid bug exposures in each arm. `cpp_concepts.py` exports cards in an isolated environment with `tree-sitter-languages==1.10.2`, `tree-sitter==0.21.3`, and `pandas==2.2.3`; `cpp_run.py` generates, `cpp_evaluate.py` scores with three references, and `cpp_validity.py` checks exposed inputs against eight task specifications. The 1.59 GB TrickyBugs archive is used only for public descriptions and references, kept outside this repo.

The follow-up [held-out relation-planning study](../research/trickcatcher-conceptcoder-relation-2026-09-26.md) compares two calls per arm: a generic relation planner versus the same planner grounded in ConceptCoder VD statements, followed by the original TrickCatcher prompt. On 20 new PUTs it found 8/20 valid exposures for generic planning and 7/20 for concept planning (paired p = 1.0). Run these arms with `cpp_run --arm generic_plan` and `--arm concept_plan`; raw plans and evaluations are archived with the report.

For the format sensitivity and placebo analysis, use `trickcatcher_pilot.reparse` on **both** arms' saved raw JSONL, `trickcatcher_pilot.shuffle_plans` to rotate concept cards within matching signatures, and `trickcatcher_pilot.paired` for exact paired statistics. Preserve the original strict-parser files; the lenient files are a separate analysis.
