# Offline execution of the Reka strategy

Ran the exact Reka `strategy()` response from the one-prompt provider diagnostic
through v81's existing AST gate, Hypothesis draw sandbox and fact classifier.
Task19, original concept-hybrid SPACE fact, fixed draw seed20261027, 100 requested
draws, max500 Hypothesis attempts. No API/model call, private oracle or hidden
reference was used.

- Strategy syntax/contract: accepted by `v4_strategies.checked`.
- Generated:100 unique candidates; B5 validator accepted100/100.
- Target SPACE fact hits:100/100. Examples include repeated, leading and trailing
  spaces (see `reka_strategy_execution/REPORT.json`).
- Sandbox/classification errors:0.

This proves the strategy runs and exercises the intended input class. The provider
returned an input strategy only, not expected-output assertions. This check did
not decide which generated inputs make the PUT disagree with the specification,
so it is not a bug-detection or efficacy result and it does not change v81 scoring.
