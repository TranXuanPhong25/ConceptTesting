# v14_obgraph: grounded obligation graph

User requested trying this direction first in a separate folder on 2026-10-14. This copy retains the frozen
v7/v11 machinery via v13_hyp. Use **`experiment.py`**, not the inherited legacy `run.py`, for the new arms.

Method: exact spec clause → semantic obligation family + AST/linefact concept → connected tool DATA/CONTROL path
ending at RETURN → pure trigger T + obligation O(args,result) → sandboxed input/path evidence. One Qwen proposal
per task supplies up to six cards; tool checks them, keeps top three, and retains unwitnessed candidates.
200 domain draws per task locate witnesses; PUT fails O and a surviving mutant passes O is the strongest ranking
signal, followed by PUT fails O, witnessed, and unwitnessed. This evidence does not certify intended semantics.

Three strategy slots per arm then draw at most 100 candidates/slot with a 500-example cap. Graph/card/noconcept/new-
toolinput arms require both T and the observed path; plain/placebo/original-toolinput controls retain valid inputs
without target filtering. Each slot selects at most two sources; globally <=12 distinct inputs and <=20 placeholder
assertions. The common ref oracle supplies expected values after generation, with no additional model calls.

Arms:

| Arm | Guidance / role |
|---|---|
| graph-strategy | Typed connected path, concepts, R/T/O and explicit fault alternative |
| card-strategy | Same nodes/concepts/R/T/O/edge evidence as unordered cards; same target/filter |
| graph-noconcept | Path and obligation without concept labels in guidance |
| plain-strategy | Generic edge-case strategy; same three requests |
| placebo-strategy | Existing covered facts; same three requests |
| toolinput | Original frozen fuzz witnesses used as strategy seeds |
| new-toolinput | New obligation witnesses used as strategy seeds |
| witness-only | Original witnesses, zero generation requests |
| new-witness-only | New obligation witnesses, zero generation requests; proposal cost separate |

Primary exploratory contrast: graph-strategy vs card-strategy under shared ref D_IO. This tests path organization
with fixed evidence and selection. Controls with different filtering are bundle comparisons, not a pure prompting
effect. Concept-label removal tests visible abstraction guidance; it does not remove concept use inside the tool.
Same request caps are enforced; actual server token counts are reported, without punctuation padding.

Initial cohort: fixed 20 dev tasks, K=1, sampled with seed 20261014 (config.json). This is an exploratory smoke,
not held-out validation. The GPU smoke is now complete: no proposal passed the schema/grounding gate, so the
graph/card arms used generic fallback. See [the tracked result](../../analysis/v14_v15_gpu_smoke.md).
[CPU evidence](CPU_VALIDATION.md), [changelog](CHANGELOG.md), [research](../../research/relations_2026-10-14/REPORT.md).

CPU preparation (repo root):

```bash
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v14_obgraph.experiment prepare --workers 2
```

Online run when QWEN_BASE_URL is privately available in the environment:

```bash
bash trickcatcher_linefacts/pipelines/v14_obgraph/run_experiment.sh
```

Output: this folder's `out/humaneval/experiment_smoke/`. Stages `prepare`, `propose`, `generate`, `oracle`, `score`.
Offline is the default; only `--online` enables the Qwen client. The shell runner checks the endpoint and keeps it
alive during its own run. To resume, repeat it with unchanged code/config: cached complete proposals, samples and
worker jobs replay; interrupted samples reuse the response cache. Transport failures abort for a same-config resume.
Source/config/task changes require a fresh experiment output and a protocol amendment; do not overwrite old results.

`gen.jsonl` contains literal calls with `== None` placeholders. `eval.jsonl` is only the inherited ref-input-collection
adapter, explicitly marked `not-scored`; do not report o0/own-assertion metrics from it. `oracle/exec/` holds actual
ref/canonical/PUT scoring. `report.json` contains common ref metrics and a separate property-oracle diagnostic.
Canonical code never enters proposal/selection. Saved v11 spec-only responses are reused only for final scoring;
missing/disagreeing references abstain. Clauses and obligations remain candidates, even after finite validation.
