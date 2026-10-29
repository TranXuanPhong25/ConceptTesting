---
name: v85-concept-quality
description: V85 cost/gate diagnosis and ConceptCoder alignment;5draft measured-property concepts,no runtime changes
metadata:
  type: project
---

2026-10-29 user asks cost then concept-base quality and ConceptCoder alignment.
See python_bug_concepts/research/v85_concept_quality_20261029/REPORT.md and
research/conceptcoder_20261027/V85_DEFINITION_AUDIT_20261029.md.

Generation v11→retrieval:268→154logical received calls(-42.54%),273274→187568
known tokens(-31.36%). Including identical shared preparation/ref attribution:
927751→842045tokens(-9.24%).2generation requests shared across arms;round1
already included inhybrid. Historical failed usage stays separate/unknown.

206/275cardbindings areSTMTfallback,204/206hitR1;69same-line v11facts,51hit.
94tasks allgateshit,29withoutrefbug. R2tasks60→19,calls155→41;bothadd5refbugtasks.
8of9retrieval pairedlosses lackbuginput;task91has7buginputs butrefemitswrong.
Do not treatlowercalls as independentconceptquality oralllosses ascardfailures.

ConceptCoder permits variedgranularity/relations. STMTisvalidconcept butnot
semanticallyequivalent tocardtrigger. TypedOBS(property,bindings,value,evidence,
scope),REQ(publicspec,unknownallowed),TEST(realizationpredicate) is a proposed
measurementdiscipline,not learnedbottleneckequivalence. Prioraudit alreadyproposed
it;newfinding isv85gate mismatch. Priorv5site74→74,v6site90notutility,v7fullhints
hurt40taskcoverage;avoidrenamingorrepeatingthem asnewmethod.

5data-only candidatecards prepared:normalization,multiplicity,order,classifier,
recursivework.4primitivecontrast/benignselfchecks pass;notautomaticextractor,
no newmodel/targetcalls,no default/runtimechange,no measuredimprovementyet.
Repair/testsemanticcoverage beforelargerrun;fixedbudget+genericinputcontrol
needed toseparatebetterconcepts frommoreR2calls. Resourcebugrequiresbudget;
multicallstateconceptunsupported ifharnessisolateseachcall. No canonicalinruntime.
