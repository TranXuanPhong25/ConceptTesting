# Prelaunch validation — 2026-10-30

- Selected server advertises qwen3.5-27b-awq with 8192-token context.
- Actual inference probe passed: `{"ok":true}`, 27 prompt + 6 completion tokens,
  thinking disabled. Probe is recorded under `final/validation/` and is not an arm.
- **27 engineering checks pass**, including synthetic end-to-end cohort → five
  input arms → reference outputs → detected failures → offline controller scoring.
- **164/164 original canonical solutions pass** the new traced base harness; see
  `canonical_preflight.json`. All164 trusted contract wrappers compile.
- Independent read-only review completed; all must-fixes and the observer-log
  resume fix recorded in PREREG Amendment1. No remaining launch blocker.
- All generated-PUT benchmark outcomes occur only after this validation and frozen
  configuration. No efficacy result may be inferred from the fixture/probe evidence.

## Post-launch live readiness

The exact input prompt/adapter, parser, sandbox reference oracle and PUT evaluator
were also exercised with the real selected model on a separate tiny engineering
fixture (`live_readiness.py`, invoked as a module). It generated **3 valid novel
inputs** and detected the fixture's deliberate error on both repeats. Cost: **591
prompt + 111 completion = 702 tokens**. This fixture is not HumanEval benchmark
data, never enters any arm/cohort, and does not establish concept efficacy.

Actual readiness record: `live_readiness_result.json`. Together with the earlier
33-token transport probe, preflight/readiness completions total **735 known tokens**,
separate from writer/tester/observer accounting in the benchmark report.

Full164 controller PID93111 observed alive; first 3 tasks completed cohort building:
30 structurally distinct generated programs, 27 base passes, no unknown responses.
This is a progress observation only. Check live status rather than assuming these
counts remain current or treating the launch as completed benchmark scoring.
