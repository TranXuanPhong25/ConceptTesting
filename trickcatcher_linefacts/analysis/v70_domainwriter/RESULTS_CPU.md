# v70 public-domain CPU replay — 2026-10-25

Complete fixed6v67response replay:15proposals,6admitted,2public-consistent
alternatives. All native candidates satisfy the explicit public domain. Gate0/6;
no new writer, endpoint, generator or private-reference call in this CPU stage.

| Case | Admitted | Candidates / realized | Domain-valid | Sensitive | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
|61|1|0 /0|0|0|FAIL|
|66|0|0 /0|0|0|FAIL|
|124|3|8 /8|8|0|FAIL|
|58|0|0 /0|0|0|FAIL|
|131|0|0 /0|0|0|FAIL|
|85|2|0 /0|0|0|FAIL|

The same case124hypotheses in v69built22inputs with word1empty, all violating
public length constraints. V70prunes those shapes before solver/native budgets;
8actual candidate runs satisfy length/alphabet constraints and realize exact
site/event/predicate/repeatability, but still show no output sensitivity.
Only4models per feasible shape are explored, and the trigger itself restricts
word1length<3. No equivalence or general hypothesis-validity conclusion follows.

Actual140native executions=76public checks+64construction executions. Case124
138,case612; all within256/case,64candidates,120seconds. No budget expansion or
outcome-based hypothesis rewrite. Domain receipts bind exact source/spec/quotes;
unsupported constraints block instead of silently widening the domain.

Owner read-only artifact auditPASS52freeze entries (cpu_terminal_audit.json),
including source/runtime/protocol/request/writer identity, domain validity of all
candidates, checksums, native accounting and context/gate parity. No independent
agent review claimed. Priorv69/v67sources/outputs unchanged. New writer surface
has not been tested by this legacy replay; the preregistered fresh6writer stage
runs separately under the same frozen implementation.
