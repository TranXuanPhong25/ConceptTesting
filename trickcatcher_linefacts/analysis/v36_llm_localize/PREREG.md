# v36 LLM localization probe: does reading the CFG help an LLM find the bug and a bug-revealing input?

Written 2026-10-20 before any model call. User asked whether "LLM reads the CFG / concept–code relations to locate
the fault" was tried, then asked to try Qwen2.5-Coder-32B-Instruct (AWQ, vLLM, 8192-token context, free GPU endpoint).

## Prior art in this repo (rule: check the version tree first)
v13_hyp (Qwen 7B, relation chains → spec-violation hypotheses: lost to flat/toolinput), v21_flowtools (Qwen 7B,
CFG/trace tools: 1–4/20, no concept gain), v28 (Codex, same: ceiling 16–17/20 for every arm incl. plain), v23/v33
(concept-guided hypotheses: no gain). New here: a mid-size coder model, the non-ceiling VibePass half, and
**direct** measurement of localization and of bug-revealing inputs (never measured separately before), on the
bottleneck that v35 identified (reaching a bug-revealing input).

## Design
- Cohort vibepass_half (33 PUTs; the v31/v34 cases). One call per task per arm, temperature 0, seed 20261020,
  max_tokens 1024, JSON output: ≤ 3 suspect lines, each with fault type, reason, ≤ 3 inputs (JSON arrays of args).
- Arms: `code` = spec, signature, numbered code, public tests (v31 context). `cfg` = the same + the static
  control-flow structure of the entry function (flow_run.structure, one line per statement: id, kind, code,
  controlling branch), compacted to fit 8192 tokens. CFG is supported for 19/33 PUTs; on the other 14 the cfg arm
  gets the unsupported notice, so the comparison below uses the 19 supported PUTs.
- Scoring (references only here): an input exposes the bug if it is contract-valid and PUT ≠ reference.
  Localization ground truth = v35 locating-mutant lines (only tasks where v35 ceiling holds); hit@1 / hit@3.

## Go / no-go (on the 19 CFG-supported PUTs)
CFG reading is a promising direction iff (a) paired exposure tasks cfg vs code: wins > losses, AND (b) hit@3 cfg ≥
hit@3 code, AND (c) cfg exposure tasks ≥ template-pool exposure tasks on the same PUTs (v35). Otherwise no-go.
Reported, not gated: all-33 summary, hit@1 vs mutant top-1, parse failures.

## Amendment 1 (after the first score, before interpretation): harness input-parsing bug
The first score (exposure 2/33 per arm) came from my parser, not the model: (1) inputs the model wrote as strings
(e.g. `"[3, 3, 3]"`) were dropped; (2) for one-parameter functions a JSON array like `[3, 3, 3]` was unpacked into
three arguments (106/256 PUT runs raised TypeError). Fix, applied identically to both arms: each input goes through
the repo's arm-neutral `flow_tools.parse_call` (used by every v21–v34 scorer): a JSON array is tried first as the
argument list, then as a single value; a string is parsed directly. Gate and everything else unchanged; the first
score is kept as `score_parsebug.json`.
