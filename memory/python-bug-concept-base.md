---
name: python-bug-concept-base
description: User-requested external Python bug patterns → where/how/what concept corpus with local retrieval
metadata:
  type: project
---

2026-10-26 (Codex): user explicitly requested downloading Python bug patterns, synthesizing concepts with
`where / how / what` templates, and building a retrievable base. Implemented separately in
[`python_bug_concepts/`](../python_bug_concepts/README.md), with pinned Ruff/flake8-bugbear/CPython sources,
source licenses, concept→pattern provenance, and local SQLite FTS5/BM25 retrieval. Canonical cards, exports,
source inventory, coverage and usage are documented there.

**How to apply:** use this corpus when the user refers to the Python bug-pattern concept base. It is a reusable
retrieval artifact, not a paper reproduction or a new linefacts experiment. No LLM/API spend, benchmark run or
test-generation efficacy claim was authorized or made in this task. Source rule evidence supports mechanisms;
target applicability and expected outcomes still require the target contract. Earlier concept/template experiments
v17/v31–v35 remain negative or weak; this corpus does not supersede their findings.

2026-10-26 continuation: user explicitly asked to finish the remaining source records after the initial partial
curation. Complete accounting is now required: each record maps to a concept or has an explicit reviewed exclusion
with a reason; unresolved records, overlapping dispositions and missing exclusion reasons fail validation/build.
See [`COVERAGE.md`](../python_bug_concepts/COVERAGE.md) and the updated README for current counts and checks.
Do not describe merely retained raw records as completed concept curation.

2026-10-26 HumanEval retrieval continuation: user explicitly requires top-3 to
describe the **actual bug** on the 113 PUT cohort, not merely a relevant risk.
Implemented [`retrieval_v2/`](../python_bug_concepts/retrieval_v2/README.md): original
132 cards unchanged, 30 pinned Python-semantic cards added separately, AST-grounded
ranking and public API routing. Internal result: correct family + first faulty
site hit@3 **74/113** (ranking audit **25/40**); family-only **88/113**. Native
contract-valid witnesses support 91 labeled tasks, others remain misses.
Labels/sites are single-author and corpus design saw all public source, so this
is development-informed engineering evidence, not independent generalization
or test-generation efficacy. Use RESULTS.md and frozen audit artifacts before
quoting the figures; do not tune the frozen engine from audit misses.

2026-10-26 user rejects coverage alone and requests concept-quality evaluation
and further retrieval improvement, authorizing the provided Qwen3.5-27B-AWQ
endpoint. New [`retrieval_v3/`](../python_bug_concepts/retrieval_v3/PREREG.md) run:
global-catalog Qwen retrieval on 113 PUTs, blinded per-card/where-how-what grading,
and a preregistered 40-task native utility comparison (plain/v2/v3 matched test
generation calls). V2 remains frozen. Endpoint lives only in a private /tmp env
file; never copy its value into memory or reports.

Owned detached lifecycle/status is in `python_bug_concepts/retrieval_v3/out/run_20261026/`
(`OWNER.json`, `STATUS.json`, `TERMINAL.json`, `run.log`). Four initial canaries
are preserved separately; generic prompt/line-format amendment precedes wider
inference. Main run started; no terminal quality verdict yet. Before continuing,
inspect owned PID/status and reuse cached requests; never launch a duplicate run
or automatically retry an unknown completion. See PREREG/REVIEW for budgets and
same-model judge limitations; utility does not match total retrieval inference cost.

2026-10-26 user explicitly asks to wait approximately two hours for quota reset,
then continue. New completions are paused with a ledger-lock barrier, allowing
already reserved responses to finish/cache. `out/run_20261026/PAUSE.json` records
the exact resume time and barrier PID; `pause.py` rechecks the endpoint before
releasing the barrier after the timer. The original lifecycle remains alive,
blocked at new-request reservation. Do not duplicate or kill it merely because
completion count stays fixed during this authorized pause. If the user resumes
early, release the recorded barrier; if endpoint preflight fails at wake-up, the
barrier stays locked and records `resume_blocked_endpoint` for manual handling.

2026-10-27 continuation supersedes the pause/running state above: user resumes;
original owner already drained/stopped after judge15 context preflight. Retrieval
113/113, original judge112/113 cached with zero unknown completion. Separate
`retrieval_v3/continuation_20261027` compacts only the oversized witness presentation
for missing judge15, then drains the original utility plan. Identical arm prompts
share a content-addressed response; concurrent duplicate reservation stops old
STATUS updates but does not stop the queue. FINALIZER.pid waits for OWNER.pid,
fills missing arm records from exact terminal caches (no new inference), then
natively grades and writes completion-aware RESULTS/FINALIZED. Before any new
work check those PIDs and FINALIZED.json, never duplicate original work. Endpoint
was live again on resume; no URL copied here.

Quality results so far: original v3 family+site67/113, v2 74/113; generic duplicate
recovery + hybrid v4 reaches78/113 (family90/113), explicitly post-hoc, no independent
holdout. Manual hash-sample20 v3 rows gives13actual-bug concepts but9fully-correct
where/how/what. Native audit contradicts five grade2 judge positives. Judge is
auxiliary, not truth; do not promote its precision or v4 utility without evidence.
[RESULTS](../python_bug_concepts/retrieval_v3/RESULTS.md) tracks actual utility
completion. New v4 API is opt-in; default remains v2. All60 tests passed.

2026-10-27 COMPLETE supersedes active-continuation status: FINALIZED.json and
FINAL_VALIDATION.json confirm120arm slots,112unique utility responses (8 shared
identical-request slots;7restored after queue),351native test rows,0unknown usage.
Confirmed bug tasks on40: plain4, v2 18, originalv3 15; false-alarm tasks0/2/4.
V3 vs v2 has2wins/5losses. No new request or native utility for v4; keep v2 default.
Original stopped terminals are retained as history; FINALIZED is authoritative.
All owned request/finalizer processes finished, no automatic follow-up/new spend.
Full quality/sample/utility limitations and raw paths in RESULTS.md. Main341
received calls plus4canaries+1review=346known completions, within356registered cap.

2026-10-27 research request: user asks alternate representation/parsing to improve
quality and retrieval. [Research report](../python_bug_concepts/research/representation_20261027/REPORT.md)
reviews7primary papers plus official parser/analysis docs; no reproduction/new
model calls/dependency install/engine changes. Existing-v2 diagnostic: AST113/113;
89/91labeled families in pool,88top3; all raw evidence sites have87matching tasks
vs74selected. Thus site binding/applicability is stronger current evidence for
next diagnostic than swapping parser or increasing top-k.22unlabeled remainunknown.
Proposed only: scoped source facts + value provenance/guards + explicit concept
requires/excludes + pair(concept,site) retrieval; optional multi-view embedding.
Do not repeat v36rawCFG/v47/v78selectors/v50/v63gates as if untried. Literature
performance is not evidence this proposal works; keep baseline/default unchanged.

2026-10-27 user explicitly requests commit old version first, then create new by
copying old and editing copy. Baseline163b58a committed/pushed main with corpus,
research, frozen raw evaluation evidence (force-added out JSON despite global
ignore); only owned files staged. Actual retrieval_v2→retrieval_v5 copy44files
recorded in COPY_MANIFEST; baseline_engine.py retains byte-identical old engine.
V5 adds LibCST1.9.0 metadata, bounded origins, conditional applicability, guard/
loop exclusion and concept/site pairs. Opt-in API/CLI; requires separate .venv.
118tests pass/32new; pre-score freeze still valid. Result **NO RETRIEVAL GAIN**:
family88,firstsite74/113, same v2; exact source binding275/275,4lower-ranked
exclusions,0backendfallback. No Qwen/paid calls/native utility forv5. Keep v2
default; do not retune frozenv5 from these outcomes. Read retrieval_v5/RESULTS.md
and python_bug_concepts/VERSIONS.md. Source/corpus/oldfreeze hashes unchanged.

2026-10-27 user explicitly authorizes autonomous iterative retrieval improvement
from returned errors and implementation audit. V6 is an actual copy of frozenv5;
no task IDs/gold/reference lookup inside runtime. Six versioned/source-frozen
development iterations preserved. Final semantic-v6.6/iter06: **balanced family91,
firstsite90/113**,126cards vs v2/v5 88/74,275cards;16sitewins0losses. Frozen-label
match74.6%vs34.9%, NOT independent actual precision. All113sources already seen;
labels incomplete/single-author,22unlabeled remainmisses. Precise abstains without
support: family/site63,82cards,80.5%labelmatch; correct-program overretrieval5/113
vs v2 100/113 (not bug-report FP rate). Balanced retains weak fallback and still
returns on99/113canonical programs; do not hide this tradeoff.

Implementation fixes: meaningful semantic tiers, alternative ASCII/multiplicity
eligibility, invalid index/consumed-sentinel/compound sites, operation roles,
comprehension/tuple/branch provenance, helper public purpose without inherited
inputtype, builtin annotation identity, modulefragments, exportedfact integrity.
242testsPASS;126exact source bindings/160dependency references checked.21purposive
native cases valid+PUT/reference different;20cached valid outcomes reused, initial
invalid shape preserved and corrected separately. Not random precision or testgen
efficacy. No new Qwen/paid calls. Root API/CLI explicitv6 defaults balanced; lowlevel
engine defaults precise; public auto staysv2. [Report](../python_bug_concepts/retrieval_v6/RESULTS.md).
No frozen oldsource/corpus change. User authorized this adaptation; do not misread
v5's no-retuning protocol as prohibiting this separately recorded v6 work.
