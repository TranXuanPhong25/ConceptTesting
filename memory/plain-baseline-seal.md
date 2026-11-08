---
name: plain-baseline-seal
description: User wants fixed plain baseline reused; completed44task compiled run sealed read-only with1375originalfilehashes
metadata:
  type: project
---

2026-11-05/06 user asks whether recent runs skip unchanged plain and requests
locking the baseline. Verified latest smoke/v4/v5diagnostics contain boundary
calls only, no fresh plain calls. Latest plain is in
final/out/boundary_all_plain_bva_compiled_20261105:44tasks,840validplaininputs,
2detectedPUTs (99/124). Do not confuse with original164task baseline.

Sealed that completed run after exclusive .run.lock acquisition. Added SEALED.json;
removed all file/directory write bits. All1375originalfileSHA256s still match.
Receipt tracked candidate:final/data/baselines/plain_compiled_44tasks_20261105.seal.json
contains original file hashes/modes and generation freeze. No source changes,
new generation,model calls,scoring or historicalartifactcontentmutation.

User preference: reuse unchanged plain rather than regenerate it for each BVA
repair. Reuse requires matching task/PUT/spec/prompt/model/budget/sampling;
changed reference/scoring requires frozen-input rescore in separate output.
Existing code does not automatically assemble cross-run plain/BVA comparisons.
Readonly permissions prevent ordinary writes,not ownerchmodoverride. Do not
unseal/resume/overwrite the baseline; preserve shared execution cache separately.

**Why:** avoid unnecessary baseline generation and preserve a stable comparator.
**How to apply:** verify seal before reuse; use only intersecting matched cases.
New development outputs go to fresh directories. No commit requested for seal.

2026-11-08 full164cached naive rescore COMPLETE with0newmodelcalls. This uses
v11_concept_inputs plain,not this sealed44baseline. Same1454targets/frozen oracle
as fullsoftBVA:naive44vsBVA61,shared31,only13vs30. All30BVA-onlyhave no naive
valid novel input;raw gain is not demonstrated better boundary selection.
Original naive72is historical under an older oracle/runtime. Source records are
unchanged;see [[bva-full-humaneval]] and
final/review/naive_vs_soft_bva_full164_2026-11-08.{md,json} for verified results.

2026-11-06 usercorrects: check actual naive-detected PUT overlap rather than
refusing because run cohorts differ. Read-only intersection audit:
final/review/plain_known_bug10_overlap_2026-11-06.json. Latestcorrected44plain
does overlap exact124PUT0, with malformed-year inputs. Its99detection isPUT0,
not knownbug10target99PUT1. Original164v11plaincached detections overlap exact
2PUT6,11PUT1,76PUT0,157PUT3; source/parentcohort identities match. That old
reference protocol differs, so label historical and do not pool runs. All1375
sealed originalfile hashes verified unchanged,0newmodel/native/referencecalls.
Never claim naive has0overlap or generated0inputs on thesePUTs.

2026-11-06 user asks exact10boundary/naivenumbers. Reused frozen164plain batches
unchanged and rescored against exactknownbug10PUTs/currentcorrectedHumanEval+
oracle,0newmodelcalls. Naive113valid/4PUTs(2,11,76,157), boundaryv5 64valid/4PUTs
(76,99,124,140), shared76; fullrescorereplaymatches. Report:
final/review/boundary_naive_known_bug10_2026-11-06.{md,json}. Rawnaive119records;
23/99/124/140already0admittedsourceinputs. Keep distinctfromsealed44baseline.
Generationvisibility/calls differ (historicalnaive10calls vsboundary16), so
same-target/oracle descriptivecomparison,not efficacy/general detectionrate.

Naive's successful inputs include boundary values:2nearintegers,11emptystrings,
76zeroedge;157nearPythagorean equality in float arithmetic. Do not confuse
noBVA-guidance with no-boundary-inputs; posthoc classification does not establish
systematic below/at/above generation. Evidence is in the exact10comparison report.

2026-11-06 detailed3lossanalysis:final/review/boundary_v5_losses_to_plain_2026-11-06.md.
Actualnaivevisibility9/10/10PUTsvsBVA1;task2naiveseesexplicitnumber<1.0inotherPUT.
BVA2/11stopresponses129/82tokensabstain,nottruncation;157falsepolaritymismatch
lockscontexttoa0neighborhoodandobservedinttemplatesrestrictfloatneighbors.
ExtraBVAinstructionsare notverifiedsemanticknowledge; cannotattributecausality
topromptalone withdifferentvisibility/temp/roles. No newmodel/PUTruns/codefixes.
