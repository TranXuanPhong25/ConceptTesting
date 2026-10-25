# v69 typed writer and constructor

The v67 diagnostic stopped at0/6gate: writer contract violations and unsupported
string triggers. This isolated successor compiles a simpler prospective writer
surface and adds typed string-order construction. Source lineage in PARENT_V69;
experimental scope in PREREG_V69. v66/v68 CrossHair branches are separate.

The writer supplies spec/code mismatch claims, a short Boolean condition over
arg0,arg1,... and an edit object. Operator edits preserve exact source operands;
literal and explicit pure-expression edits remain available for other cases.
The tool parses syntax with Python AST, compiles to predicate IR and checks public
input profiles. Prose is not converted into an executable meaning. Correct syntax
and passing public examples do not establish a correct repair.

String comparisons follow Python's Unicode codepoint lexicographic order,
including prefixes and empty strings. Mixed string/integer comparisons fail
before solver execution. Observed types are search support, not spec validity.
Search bounds/order, public checks, native verification, display parity and the
all-six-case gate are inherited unchanged. Oracle/ref10 remains deferred.

Legacy CPU replay is explicit: only equivalent gt/ge/ne rewrites are permitted,
with receipts; old None payloads, assignment statements and missing len() are not
silently repaired. Old source/outputs remain untouched. Fresh writer performance
has not been measured by replaying old answers.

Run (repository root, fresh output directory required):

```bash
/tmp/concepttester-v57-venv/bin/python -B -m trickcatcher_linefacts.pipelines.v69_typedwriter.replay_saved --requests trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json --out /tmp/v69-replay
```

The online entrypoint is pipeline with a fresh readiness identity; prior-version
writer caches are incompatible with the new surface. This deliverable first
validates authored compiler fixtures and frozen six-case CPU replay. Existing
version-named reports describe historical parents, not v69 model outcomes.

Validation complete:114authored tests pass. Six-case legacy CPU replay builds22
case124inputs, all with emptyword1and0sensitivity;gate0/6. See
[CPU report](../../analysis/v69_typedwriter/RESULTS.md). New writer adherence
remains unmeasured; early invalid-domain shapes remain a construction bottleneck.
