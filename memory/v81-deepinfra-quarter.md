---
name: v81-deepinfra-quarter
description: Running DeepInfra28/113HEdev,combined versus concept-hybrid,K1,$4.20cap;fixedseed/CPUreview passed
metadata:
  type: project
---

2026-10-26 (Codex): user requests quarter HumanEval on DeepInfra, following exact
2arms combined/concept-hybrid,K1. Isolatedv81fromv77, fixed random28/113dev with
seed20261026 beforeoutcomes, sourcecohort in COHORT.json; no other actualarm calls.
Baselineoriginal prompt/seed, unchangedFTmerge. Production28CPU bundlesready,
24tests incl3taskrealworker/scorer smoke, independentprelaunchreviewPASS,
84contextpreflights fit. Primaryfixedreforacle replacement, secondaryo0 original
modelassertions; CPUonlyscoring/no paidjudge. Planning$2.752512,cap$4.20.

Launched2026-10-26T15:23:58UTC detached; PID/root/protocol in
[CURRENT_RUN](../trickcatcher_linefacts/analysis/v81_deepinfra_quarter/CURRENT_RUN.json).
DeepSeekV4Flash0731 onlydeepinfra/fp8, reasoning131072outputcap, temp.6/.95,
noAPIseed,streaming1800stimeout. Only explicit nongenerating sharedpool429 may
retry<=3with30/60sbackoff;eachunknownrejectionFULLreserve counts towardcap.
Otherunknown/timeout/accountdenial halts; no resends generated/empty/length.
Parents andpriorunknowncharges unchanged. Noautomaticlargerrun/newseed/fallback.

**Why:** user-authorized actual combined-versus-original package experiment.
**How to apply:** readSTATUS.json/terminal.json and exactPID before any action;
neverduplicate. Localwatch writes RESULTS.json/md after terminal, freezeverifies,
no modelcalls. Partial = complete pairedleadingprefix only, noefficacyverdict.
Do not report launch or mocktests as scientific results. Futureterminal findings
should update this memory and ownindex/versiontree, commit+push ownfilesonly.
