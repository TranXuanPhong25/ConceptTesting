# Soft BVA versus direct: concrete input analysis on all10tasks

Run: `final/out/boundary_prompt_style10_20261107_120909`.
Machine-readable evidence: `boundary_soft_vs_direct_inputs_2026-11-07.json`.
Analysis uses saved requests, raw responses, decoded batches, corrected oracle
and both saved PUT repeats. No new generation or native execution. All failing
inputs counted below fail in both native repeats; no unstable outcomes recorded.

Direct and soft have the same single PUT/spec/contract/base calls/system/schema,
model, seed, temperature and20input cap. Only guidance differs. Soft suggests
behavior transitions, below/at/above, zero/sign, empty/singleton and integer
crossings, while preserving other useful ideas. Neither uses an external
selection API, applicability gate, compiler, tools or model feedback. Boundary
classifications in this report are post-hoc interpretations of concrete outputs.

## Accounting and scope

| Metric | direct | soft_bva |
|---|---:|---:|
| Raw generated input records | 200 | 199 |
| Admitted by common JSON/call parser | 199 | 199 |
| Novel valid inputs after oracle/base filtering | 199 | 192 |
| Detected PUTs/tasks | 6 | 7 |
| Inputs producing stable value mismatch | 28 | 18 |
| Inputs producing stable timeout | 2 | 1 |
| Prompt tokens, including reused historical calls | 8433 | 9033 |
| Completion tokens, including reused historical calls | 4490 | 4876 |
| Total tokens | 12923 | 13909 |

Direct has one within-response duplicate on140. Soft emits19records on23and20
on each other task, with no parser rejects. Its7oracle rejections are all base
duplicates:11has1,76has5,157has1. All7duplicate calls are present in the visible
existing-input packet; there are no domain/reference rejects or truncations for
either arm. Thus fewer soft valid inputs are a novelty loss, not a domain issue.

Across tasks,59valid calls occur in both arms (oracle canonical input identity).
Direct has140exclusive calls, soft133exclusive calls. Different literals do not
imply different fault mechanisms; one fault can have many exposing literals.
Soft uses about7.6%more total tokens. These are full10arm costs including reused
responses, not the18fresh-call cost of the continuation alone.

## Per-task comparison

The last column counts benchmark-failing inputs direct→soft, including timeouts.

| Task | Direct input pattern | Soft input pattern and practical effect | Failing inputs |
|---|---|---|---:|
| 2 | General decimal fractions plus very close integer neighbors | More explicit integer/zero neighborhoods, retains two sufficiently close below-integer witnesses; same PUT found | 2→2 |
| 11 | Binary pairs length2–8 | Adds singleton binary pairs, lengths1–6, but still no empty pair; both miss | 0→0 |
| 16 | ASCII letters/case/digits/punctuation | Adds short strings and newline/tab/carriage return, remains ASCII; neither crosses the code's character partition | 0→0 |
| 23 | All20calls contain non-ASCII characters, combining marks or Unicode sequences | Mixes short ASCII/whitespace/control inputs with Unicode; still detects but devotes fewer calls to the exposing partition | 20→9 |
| 72 | Many equality/below-total tests, negative lists tested at non-exposing thresholds | Adds empty/singleton and an explicit below/at/above positive triplet; combines a negative palindrome with w=its total, exposing early exit | 0→1 |
| 76 | Base1, x1, positive powers/nonpowers and two x0cases | Adds x/n0/1combinations but loses5calls to visible base duplicates; both detect the x0nonterminating loop | 2→1 |
| 99 | Half-integer ties and near-ties, including 0.4999999999 | Half-integer ties/sign/zero and 0.499999; both too far from0.5to expose addition rounding | 0→0 |
| 124 | Calendar limits, then short month/day/year fields | Calendar limits plus year magnitudes, separators, extra text and whitespace; trailing year whitespace exposes missing format enforcement | 2→1 |
| 140 | All-space strings, internal runs and mixed leading/trailing contexts | Systematic run lengths1–4in all-space, leading, trailing and internal contexts; both expose lengths1/2all-space | 2→2 |
| 157 | Many integer Pythagorean triples plus irrational-like float cases | Keeps many triples, adds smaller scales and irrational-like float cases; both expose arithmetic equality/tolerance mismatch | 2→3 |

## Where soft adds useful coverage

**72is the only additional PUT.** Soft emits `([1,2,1],3/4/5)`, a recognizable
below/at/above threshold group. More decisively, it emits `([-1,-2,-1],-4)`:

- The list is palindromic and final sum=-4=w, so reference returnsTrue.
- PUT's first prefix=-1>w=-4, so it returnsFalse before later negative values.
- Its neighboring `([-1,-2,-1],-5)` is rejected by both implementations.

Direct already contains negative inputs `([-1,-1],0)` and `([-1,-1],-3)`.
The first passes both implementations, the second fails both. Historical naive
also contains negative inputs, `([-1,0,-1],0)` and `([-1,0,-1],-1)`, without an
exposing result. Thus the useful difference is joint context/threshold placement,
not merely remembering negatives or testing equality somewhere.

**140shows a clearer matrix of contexts with no detection gain.** Soft varies
space runs1/2/3/4without tokens, at the start, at the end and between tokens.
Direct also contains every run length1–4at an internal position and contains the
same exposing all-space lengths1/2. PUT's early no-parts branch returns'-' for
both' 'and'  ', instead of'_'and'__'. Both find it. Soft's output is more
systematic here; direct already covers the needed condition.

**124shows retained exploratory coverage.** Direct catches short year widths:
`'01-01-20'` and `'01-01-202'` returnTrue instead ofFalse. Soft does not test
those widths; its witness is `'01-01-2000 '`. int()accepts the year whitespace
and PUT fails to enforce the requested format. This witness is a format
variation, not a demonstrated below/at/above triplet. Soft retains useful
non-numeric test ideas while adding boundary guidance. Each arm finds an input
the other did not generate; both expose the same PUT.

## Where direct is at least as strong

**23: direct targets the semantic mismatch more tightly.** PUT counts UTF-8
bytes instead of string characters. Direct starts with'你好'(expected2/actual6)
and every one of its20calls exposes the distinction. Soft's'中文'also gives2/6,
but it spends10of19calls on ASCII, whitespace or NUL, where byte and character
lengths agree. It also includes Unicode accents/emoji and catches the PUT with
9calls. Broader edge coverage reduces witness concentration here without losing
the detection. Multiple witnesses still represent one detected PUT.

**2: direct needs no BVA label to find precision-sensitive neighbors.** Direct
uses0.999999999and0.9999999999999999; soft uses999.9999999999999and
2.9999999999999996. Fraction.limit_denominator()approximates each as an integer,
making PUT's fractional part0rather than close to1. Both get two value mismatches.
Soft did not uniquely introduce this capability.

**76: extra edges do not ensure better yield.** Direct's(0,2)/(0,5)and soft's
(0,2)trigger an infinite loop because0%n=0and0//n=0. These detections are
timeouts, not wrong returned values. Soft also tries(0,1)but misses negative
bases and does not include(1,0). Historical naive has(1,0),(-8,-2),(-1,-1)
and(1,-5), producing value mismatches in addition to its(0,2)timeout. Direct
and soft therefore catch this PUT through a narrower fault condition than
historical naive. Soft repeats5visible base calls here, leaving15novel inputs.

## Remaining blind spots

**11: singleton is not empty.** Soft chooses'0'/'1'pairs but never('', '').
Direct never goes below length2. PUT calls int(a,2), so empty input raises
ValueError while the reference returns''. Historical naive did include('', '')
and catches this PUT. The soft instruction explicitly suggests empty containers,
but that suggestion does not guarantee a concrete empty test.

**16: type-level string edges miss the code-specific partition.** All40direct
and soft inputs are ASCII. Newline/tab/NUL-like control ideas are not substitutes
for testing after lowercasing at or beyond code point256. The known PUT silently
ignores those characters. Neither arm uses the useful Unicode partition here;
the worksheet arm's'€'finds it. Soft also does not produce a255/256/257group.

**99: nominally near a boundary can still be too far.** Direct tests
'0.4999999999'; soft tests'0.499999'and'0.499'. Both correctly identify the
half-integer neighborhood but miss the sensitive float value
'0.49999999999999994'. Worksheet emits that input and its negative counterpart,
which give expected0but actual1/-1. No model reasoning trace establishes why
soft selected its epsilon or whether it understood the float-addition mechanism.

**157: numerical scale coverage helps without proving a tolerance-boundary
strategy.** Soft has3witnesses: small-scale
(0.0001,0.0001,0.000141421356237), shared(1,1,1.4142135623730951), and
(0.1,0.1,0.1414213562373095). Direct has the shared witness and
(0.001,0.001,0.0014142135623730952). Reference uses its exact equality behavior;
PUT accepts residuals below1e-9. Both returnTruewhere the reference saysFalse.
These are near arithmetic equality, not a measured systematic sweep around
the PUT's1e-9cutoff. Historical naive's(0.5,1.2,1.3)already finds this mismatch.

## Historical naive is a separate comparison

Historical plain inputs are fromv11_concept_inputs, rescored unchanged in
naive_known_bug10_rescore_20261106. It saw multiple PUTs/task and has different
requests/visibility. Its113novel inputs detect2/11/76/157(4PUTs). Soft detects
2/23/72/76/124/140/157(7PUTs): shared2/76/157; soft-only23/72/124/140;
naive-only11. Historical naive has no admitted generation inputs on23/99/124/140,
so those misses are not evidence its concrete values were worse than soft's.
The current matched direct control has valid inputs for all10tasks and detects6.
Do not attribute the historical4→7change solely to soft guidance.

## Interpretation

Observed soft outputs more often include short-container contexts and explicit
threshold triplets. The practical detection gain is one correctly combined
negative equality case on72. Direct already generates many useful boundary
values; soft is neither uniformly more precise nor universally more code-aware.
It misses empty11and Unicode16, lacks precision on99, dilutes targeted23testing
and repeats visible base inputs. The absence of PUT losses at a20input budget
does not establish dominance at lower budgets or across seeds/tasks.

This supports soft as a lightweight next diagnostic direction. It does not
establish causal internal reasoning, prompt-length effects or general efficacy:
these10known-bug tasks are outcome-selected and informed prompt development;
there is one response per task/arm and historical epochs are reused/disclosed.
