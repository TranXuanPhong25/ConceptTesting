"""Render documentation-only execution diagrams; never run research pipelines."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent
PALETTE = {
    "CUSTOM": ("#eaf1fc", "#708daf"),
    "LLM": ("#efe6ff", "#9473bd"),
    "CONCEPT": ("#fff1d4", "#b9954e"),
    "LIB": ("#e5f4ec", "#72a18a"),
    "SCORE": ("#edf0f5", "#929fb1"),
}


def canvas(title, subtitle, width, height):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")
    ax.text(.4, .42, title, fontsize=23, fontweight="bold", color="#172338")
    ax.text(.4, .82, subtitle, fontsize=11, color="#596579")
    for i, (name, (fill, stroke)) in enumerate(PALETTE.items()):
        x = .4 + i * 2.35
        ax.add_patch(FancyBboxPatch((x, 1.08), 2.05, .35,
                     boxstyle="round,pad=.025,rounding_size=.06", facecolor=fill, edgecolor=stroke))
        ax.text(x+.12, 1.26, name, fontsize=10.5, va="center", color="#27364b")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax


def node(ax, x, y, w, h, title, function, details, kind="CUSTOM"):
    fill, stroke = PALETTE[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=.025,rounding_size=.09",
                 lw=1.2, edgecolor=stroke, facecolor=fill, zorder=3))
    ax.text(x+.14, y+.25, title, fontsize=12.5, fontweight="bold", color="#172338", va="center", zorder=4)
    ax.text(x+.14, y+.53, function, fontsize=9.5, color="#344358", va="center", zorder=4)
    for i, line in enumerate(details):
        ax.text(x+.14, y+.79+i*.23, line, fontsize=10, color="#344358", va="center", zorder=4)


def arrow(ax, points, label=None, label_at=None, dashed=False):
    color = "#7c8a9d"
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=1.25,
                linestyle="--" if dashed else "-", zorder=1)
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>",
                 mutation_scale=13, lw=1.25, color=color,
                 linestyle="--" if dashed else "-", zorder=2))
    if label:
        x, y = label_at or points[-2]
        ax.text(x, y, label, fontsize=9, ha="center", color="#596579",
                bbox=dict(facecolor="#f8fafc", edgecolor="none", pad=2), zorder=5)


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", facecolor=fig.get_facecolor(), dpi=160)
    plt.close(fig)


def v3m2():
    fig, ax = canvas("v3m2 — End-to-end execution flow",
                     "Current source + preserved prompts | One task per HTTP request | No results-based inference", 18, 14)
    starts = [.4, 6.15, 11.9]
    w, h, gap = 5.1, 1.13, 1.33
    columns = [
        ("1. Per-task preparation", [
            ("Task loading and selection", "run_gen.main -> run_mined.work", ["T=133 tasks; dev=113, pilot=20"], "CUSTOM"),
            ("Specification projection", "preconditions.specification", ["Signature + docstring; implementation hidden"], "CUSTOM"),
            ("Precondition observation", "preconditions.mine.query('observation')", ["LLM: 1 request; whole candidate list"], "LLM"),
            ("Precondition confirmation", "mine.query('confirmation') + norm", ["LLM: 0-1 request; exact-quote gate stays on"], "LLM"),
            ("Predicate synthesis", "mine.query('code') -> predicates / predicate", ["LLM: 0-1 request; AST checks are custom"], "LLM"),
            ("Known-valid verification", "preconditions.worker / doc_inputs / run_base", ["CPU: base + doc examples -> surviving predicates"], "CUSTOM"),
            ("Concept extraction and confirmation", "prepare_task -> facts.main / tracer.instrument", ["Custom fuzz <=400; custom AST mutation/tracing"], "CONCEPT"),
            ("Fact selection and bundling", "facts.pick -> generate.bundle", ["H<=3 fact texts + placebo + witnesses + valid.py"], "CONCEPT"),
        ]),
        ("2. Per task-arm-sample job", [
            ("Generation job grid", "run_gen.run -> work((task, arm, sample))", ["133 x 6 arms x 3 repeats = 2394 jobs"], "CUSTOM"),
            ("Arm dispatch", "work / prompts.build / generator_messages", ["Direct: 1 LLM call; input paths continue below"], "CUSTOM"),
            ("Input-generator synthesis", "generator_messages -> Client.chat", ["gen-* only: 1-2 requests -> sample_one()"], "LLM"),
            ("Candidate generation and classification", "generate_candidates OR witness_candidates -> classify", ["gen-*: 100 draws; toolinput/CT: <=3 witnesses", "Validity + fact-hit vectors; no canonical outputs"], "CONCEPT"),
            ("Valid-input selection", "gen_inputs.select", ["<=3 valid calls; gen-concept prioritizes shown hits"], "CUSTOM"),
            ("Expected-output synthesis", "oracle_messages / concept_toolinput_messages", ["LLM: 1 grouped request; PUT + base tests visible"], "LLM"),
            ("Completion persistence", "atomic_json + locked gen.jsonl append", ["2394 completion rows; not 2394 HTTP requests"], "CUSTOM"),
        ]),
        ("3. Separate evaluation command", [
            ("Evaluation dispatch", "evaluate.main -> evaluate.evaluate", ["One isolated worker per task; task loop sequential"], "SCORE"),
            ("Assertion extraction", "evaluate.extract_asserts", ["<=10 assertions per raw completion"], "SCORE"),
            ("Differential assertion execution", "evaluate.worker.run_assert", ["Execute same assertion on PUT and canonical"], "SCORE"),
            ("Delivery and input-quality checks", "tracer.fact_hit / gen_evaluation.input_metrics", ["Fact hits; input validity; revealing-input flags"], "CONCEPT"),
            ("Scored-row persistence", "evaluate.worker -> evaluate.evaluate", ["eval.jsonl: task / arm / sample / asserts / metrics"], "SCORE"),
            ("Reporting", "evaluate.report -> gen_evaluation.report", ["Detection, false alarms, delivery, costs, sign test"], "SCORE"),
        ]),
    ]
    for x, (heading, rows) in zip(starts, columns):
        ax.text(x, 1.85, heading, fontsize=13, fontweight="bold", color="#172338")
        for i, (title, fn, details, kind) in enumerate(rows):
            y = 2.2+i*gap
            node(ax, x, y, w, h, title, fn, details, kind)
            if i:
                arrow(ax, [(x+w/2, y-gap+h), (x+w/2, y)])
    # Artifact hand-offs route through gutters between the three lanes.
    arrow(ax, [(5.5, 2.2+7*gap+h/2), (5.8, 2.2+7*gap+h/2), (5.8, 2.765), (6.15, 2.765)])
    arrow(ax, [(11.25, 2.2+6*gap+h/2), (11.57, 2.2+6*gap+h/2), (11.57, 2.765), (11.9, 2.765)])
    # The direct branch returns one completion and skips input-generator/oracle stages.
    arrow(ax, [(11.25, 2.2+gap+h/2), (11.4, 2.2+gap+h/2),
               (11.4, 2.2+6*gap+h*.25), (11.25, 2.2+6*gap+h*.25)], dashed=True)
    ax.text(6.2, 12.55, "Direct arms skip generator/selection/oracle; toolinput skips generator synthesis.", fontsize=10.5, color="#596579")
    ax.text(.4, 13.13, "Tasks/jobs run concurrently (default W=16); dependent stages run sequentially. Cache may eliminate HTTP requests.", fontsize=11, color="#344358")
    ax.text(.4, 13.57, "Offline HumanEval+ fact-quality scoring is a separate branch from frozen facts. All step details and bounds: PIPELINES.md.", fontsize=10.5, color="#596579")
    save(fig, "pipeline_v3m2")


def lanes(name, title, subtitle, columns, footer):
    n = len(columns)
    w, margin, spacing = 5.5, .4, .7
    width = n*w+(n-1)*spacing+2*margin
    max_rows = max(len(rows) for _, rows in columns)
    height = 3.15+max_rows*1.48
    fig, ax = canvas(title, subtitle, width, height)
    for j, (heading, rows) in enumerate(columns):
        x = margin+j*(w+spacing)
        ax.text(x, 1.9, heading, fontsize=13, fontweight="bold", color="#172338")
        for i, row in enumerate(rows):
            y = 2.25+i*1.48
            node(ax, x, y, w, 1.23, *row)
            if i:
                arrow(ax, [(x+w/2, y-1.48+1.23), (x+w/2, y)])
        if j<n-1:
            y = 2.25+(len(rows)-1)*1.48+.615
            gx = x+w+spacing/2
            arrow(ax, [(x+w, y), (gx, y), (gx, 2.865), (x+w+spacing, 2.865)])
    for i, line in enumerate(footer):
        ax.text(.4, height-.6+i*.26, line, fontsize=10.2, color="#596579")
    save(fig, name)


def main():
    v3m2()
    lanes("pipeline_facts", "Line-fact extraction — Internal execution flow", "Custom implementation on Python stdlib; no LLM calls in this CPU phase", [
        ("1. Runtime observations", [
            ("Compile and capture base inputs", "tracer.load_module -> run_base", ["B_t InputPairs = (args tuple, kwargs dict)"], "CUSTOM"),
            ("Docstring-example diagnostics", "facts.doc_fail -> parse_examples", ["Compare PUT to parseable example outputs"], "CUSTOM"),
            ("AST instrumentation", "tracer.instrument -> Inst visitor methods", ["Custom hooks for values, conditions, loops and DU"], "CONCEPT"),
            ("Trace-time abstract-state probes", "absval / numcls / __v / __c / __p / __u", ["Inside trace calls; ConceptCoder BP-style classes"], "CONCEPT"),
            ("Base-test tracing", "tracer.trace -> call", ["cells + lines + status + value per captured input"], "CONCEPT"),
            ("Type-aware candidate transformations", "facts.fuzz_inputs -> variants / scalar_variants", ["Custom base-input fuzzer; no Hypothesis here"], "CUSTOM"),
            ("Validity filtering", "valid_fuzz -> fuzz_validity.validator", ["<=400 accepted; cap 2000; isolated valid.py/contract"], "CUSTOM"),
            ("Confirmation-input tracing", "tracer.trace -> call", ["F_t traces, each preserving cells/lines/status/value"], "CONCEPT"),
        ]),
        ("2. Gap enumeration and selection", [
            ("Missing-behavior facts", "facts.main / describe / say", ["OUTCOME, STMT, BOUND, REL, SHAPE, NUM"], "CONCEPT"),
            ("Mutation-point selection", "mutation_points -> make_mutant", ["Custom AST operators; <=80 +80 points"], "CUSTOM"),
            ("Survival and discrimination", "run_base -> call(mutant) / same", ["Base-surviving mutant must have fuzz witness"], "CUSTOM"),
            ("Extended-concept extraction", "facts.new_facts", ["LOOP, OUTPUT, DU, DECISION; selection gates apply"], "CONCEPT"),
            ("Deduplication and optional v5 hook", "facts.main.dedupe / evidence hook", ["v5 can inject saved witnesses before reranking"], "CUSTOM"),
            ("Attach reachability and witness calls", "facts.main / call_src", ["reached + witness_call before guard analysis"], "CONCEPT"),
            ("Block grouping and guard demotion", "set_blocks / guard_features / make_forced / tier", ["Custom G-prime heuristic; no solver proof"], "CUSTOM"),
            ("Reached-only diverse selection", "facts.pick / display_slot / du_key", ["<=3 facts; category/block/DU diversity"], "CONCEPT"),
            ("Fact and placebo persistence", "facts.main JSON write", ["Full pool + top3 indices + matched placebo"], "CUSTOM"),
        ]),
    ], ["v4 substitutes the input pool, C1/C2 measurement and mutant enumeration with libraries; custom concept selection remains."])
    lanes("pipeline_v4", "v4 — Preparation and hybrid execution", "Separate command barriers: mine -> facts -> arms -> evaluate -> report", [
        ("1. mine + facts", [
            ("B5 precondition mining", "run_v4.mine -> preconditions.mine", ["LLM 1-3/task; evidence_filter=False"], "LLM"),
            ("Domain-strategy synthesis", "v4_strategies.mine / domain_messages", ["LLM 1-2/task; spec + surviving conditions"], "LLM"),
            ("Strategy verification / fallback", "checked -> draws / fallback_source", ["Hypothesis n=100, cap=500; from_type fallback"], "LIB"),
            ("Coverage initialization and base trace", "v4_facts.build / Coverage / run_base", ["Capture base inputs; coverage.py + custom AST trace"], "LIB"),
            ("Fact-confirmation input pool", "v4_facts.build -> v4_worker.draw", ["Hypothesis n=400, cap=2000; replaces legacy fuzz"], "LIB"),
            ("Coverage and mutant enumeration", "Coverage.trace / enumerate_mutants", ["coverage.py + mutmut + LibCST; custom probes remain"], "LIB"),
            ("Concept ranking and bundling", "facts.pick / run_v4.facts", ["Custom templates, G-prime, <=3 facts and placebo"], "CONCEPT"),
        ]),
        ("2. arms: hybrid branch", [
            ("Task-sample group", "run_v4.run -> work((task, sample))", ["Groups parallel W=16; seven arms sequential"], "CUSTOM"),
            ("Round-one assertions", "prompts.build -> query / cached shared result", ["Concept/plain reused; placebo round one is new"], "LLM"),
            ("Missing shown-fact detection", "run_v4.classify -> v4_worker.classify", ["Capture inputs; validity and shown_hits"], "CONCEPT"),
            ("Targeted-strategy synthesis", "hybrid_messages -> query", ["1 fact/request; <=1 repair; plain control has no fact"], "LLM"),
            ("Targeted draw and verification", "v4_strategies.draws -> classify", ["Hypothesis n=100/cap=500; <=2 inputs/request"], "LIB"),
            ("Round-two expected values", "gen_prompts.oracle_messages -> query", ["One grouped call if any strategy request occurred"], "LLM"),
            ("Assertion merge and persistence", "run_v4.merge -> gen.jsonl", ["Round one + round two; potentially 20 assertions"], "CUSTOM"),
        ]),
        ("3. evaluate + report", [
            ("v4 evaluation dispatch", "evaluate.evaluate -> v4_evaluation.evaluate", ["Sequential tasks; up to 3 sandbox attempts/task"], "SCORE"),
            ("Assertion and input evaluation", "v4_evaluation.worker", ["PUT/canonical; memoized coverage and fact hits"], "SCORE"),
            ("False-alarm classification", "false_alarm / validity / expected_value", ["Separate mined/contract validity diagnostics"], "SCORE"),
            ("Aggregation and comparisons", "v4_evaluation.report / comparison", ["Detection, delivery, calls/tokens; paired sign test"], "SCORE"),
        ]),
    ], ["Plain/concept/toolinput/gen-plain branches can skip round two. Full control flow, contexts and call formula: PIPELINES.md."])
    lanes("pipeline_v5", "v3mm / v5 — Fact-preparation execution", "Existing v3m2 validators are reused; Hypothesis augments individual gaps", [
        ("1. Existing inputs + base facts", [
            ("Load and verify v3m2 artifacts", "run_v5.inputs / provenance", ["Task, base tests and validator hash checked"], "CUSTOM"),
            ("Optional mutation substitution", "v4_tools.enumerate_mutants", ["mutmut or handwritten; v3mm forces mutmut"], "LIB"),
            ("Frozen legacy fact construction", "build_one -> v5_worker.build -> facts.main", ["Custom fuzz/tracer; same v3m2 validator"], "CONCEPT"),
            ("Retained-gap enumeration", "run_v5.mine_tasks", ["v5 only: first <=10 facts with reached=False"], "CONCEPT"),
        ]),
        ("2. v5 mine: one gap at a time", [
            ("Targeted-strategy prompt", "run_v5.messages -> mine_gap", ["Spec + PUT + base tests + base inputs + one fact"], "LLM"),
            ("Strategy synthesis / repair", "Client.chat -> v4_strategies.checked", ["1-2 calls/gap; max 20/task; gaps sequential"], "LLM"),
            ("Hypothesis targeted draws", "v5_worker.targeted -> v4_worker.draw", ["cap=200; validate with actual task mined source"], "LIB"),
            ("Witness verification", "tracer.trace / fact_hit / call", ["First valid hit; record witness or failure"], "CONCEPT"),
            ("Gap-summary persistence", "mine_gap -> mine_tasks summary.json", ["Task pool W=12; artifact cache avoids repeated work"], "CUSTOM"),
        ]),
        ("3. facts -> generation -> scoring", [
            ("Rebuild and inject witnesses", "v5_worker.build.evidence", ["Saved witness revalidated/retraced; append to pool"], "CONCEPT"),
            ("Rerank and serialize bundle", "facts.pick -> run_v5.bundle_facts", ["Tag v3m retained; tasks_v5_all.json"], "CONCEPT"),
            ("Generate assertions", "run_gen.main --from-bundle -> run", ["Same direct/generator arms; oracle still required"], "LLM"),
            ("Evaluate and report", "evaluate.evaluate -> gen_evaluation.report", ["Separate CPU command; no LLM scoring"], "SCORE"),
        ]),
    ], ["v3mm skips the gap-mining/injection branch; CPU-only preparation then bundle. Removed unreachable mutants are not recovered by v5."])
    lanes("pipeline_v6_v7", "v6 / v7 — Revalidation and SPEC augmentation", "No new LLM calls in these preparation functions; generation uses existing runners", [
        ("1. v6 preparation", [
            ("Load upstream artifacts", "run_v6 SOURCE / PRECOND", ["v3m2 task IDs + existing B5 validators"], "CUSTOM"),
            ("Refuzz with B5", "run_v6.facts -> facts.main", ["W=12 task processes; custom fuzz and AST tracer"], "CONCEPT"),
            ("Rebundle refreshed facts", "run_v6.bundle -> generate.bundle", ["Copy B5 source + refreshed top facts and witnesses"], "CUSTOM"),
            ("Create direct and hybrid schemas", "bundle / oracle_b01.mutant_source", ["Hybrid copies v4c strategies and full mutant source"], "CUSTOM"),
        ]),
        ("2. Optional v7 augmentation", [
            ("Traverse both v6 bundles", "spec_facts.build / base_args", ["Sequential loops; statically extract literal base inputs"], "CUSTOM"),
            ("Find uncovered input classes", "worker / applies / in_class", ["LARGE, DUP, NONASCII, SPACE"], "CONCEPT"),
            ("Construct valid class witnesses", "transforms -> worker.ok", ["Deterministic transforms; B5 validity gate"], "CONCEPT"),
            ("Conditional augmentation", "spec_facts.build", ["Only if concept_facts empty; <=3 SPEC facts"], "CONCEPT"),
            ("Persist v7 bundles", "tasks_v7_all / tasks_v7hyb_v4", ["Large witness may not fit toolinput prompt"], "CUSTOM"),
        ]),
        ("3. Generation and evaluation", [
            ("Runner dispatch", "run_gen --from-bundle OR run_v4 arms", ["Direct schema uses gen2; hybrid schema uses v4"], "CUSTOM"),
            ("Arm-specific inference", "Existing prompt / generator / oracle functions", ["Same calls and contexts as the selected runner"], "LLM"),
            ("Assertion evaluation", "evaluate.evaluate: tag-based dispatch", ["Canonical comparisons + input/fact metrics"], "SCORE"),
            ("Report", "gen_evaluation.report OR v4_evaluation.report", ["Separate CPU stage; no model feedback"], "SCORE"),
        ]),
    ], ["v6 can proceed directly to generation without v7. Hybrid bundle construction depends on existing tasks_v4c_all.json."])
    lanes("pipeline_tc_full", "tc-full — Baseline execution", "Original TrickCatcher templates; no concept-fact conditioning", [
        ("1. gen: model inference", [
            ("Load task sources", "tc_full.load_tasks / templates", ["133 non-design tasks; template SHA256 verified"], "CUSTOM"),
            ("Generate repaired variants", "tc_full.generate / messages('variant')", ["10 sequential LLM calls/task; PUT + docstring"], "LLM"),
            ("Generate input generators", "messages('generator') / Client.chat", ["4 sequential LLM calls/task; sample_one code"], "LLM"),
            ("Save inference responses", "put_json -> generation/task.json", ["14 records/task; task pool CLI W=8"], "CUSTOM"),
        ]),
        ("2. run: isolated execution", [
            ("Base-test variant filtering", "tc_full_worker.base_filter", ["Keep only base-passing generated variants"], "CUSTOM"),
            ("Generator execution", "generate_candidates -> generator_worker.main", ["Custom runner: 4 x100 calls; generated code may use cyaron"], "CUSTOM"),
            ("Pool construction and resampling", "tc_full.execute_task", ["Restore multiplicities; <=100 positions/repeat"], "CUSTOM"),
            ("Differential variant execution", "tc_full_worker.execute", ["PUT + survivors; only differing successful outputs"], "CUSTOM"),
            ("Output vote and assertion emission", "execute -> assertion", ["Plurality expected; discard PUT failures; no LLM oracle"], "CUSTOM"),
        ]),
        ("3. Score and aggregate", [
            ("Reference scoring", "tc_full_worker.execute", ["Canonical + contract; not fed into generation"], "SCORE"),
            ("Per-row assertion metrics", "tc_full.row_metrics", ["Main S=3; RQ2 S=1 on canonical PUT"], "SCORE"),
            ("Survivor-subset analysis", "tc_full.subset_scores", ["k=2..10; all maximal-vote ties in metric"], "SCORE"),
            ("Report persistence", "tc_full.aggregate -> report.json", ["14*T LLM requests reused across all resamples"], "SCORE"),
        ]),
    ], ["Canonical and contract scoring execute alongside variants inside the worker; the right lane shows their evaluation role."])
    print("Rendered 6 documentation diagrams (SVG + PNG).")


if __name__ == "__main__":
    main()
