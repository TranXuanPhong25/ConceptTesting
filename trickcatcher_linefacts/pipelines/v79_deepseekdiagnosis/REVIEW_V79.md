# Pre-dispatch independent review — 2026-10-26

Independent read-only Codex reviewer reviewed ds_probe/openrouter_stream against
v73 and PREREG_V79. Two must-fixes applied before any paid call: per-job exact
provider context gate using the conservative prompt envelope, and preserving
API/stream error together with missing-usage status. Routing/model/no-seed,
no fallback/retry, four frozen v72 prompts and $0.15 budget were otherwise sound.
Four total worstcase reservations $0.09967314; maximum input+output166374 versus
advertised context1048576. Owner rechecks implementation of the two fixes.

Targeted stream/diagnostic tests: 19 pass using
/tmp/concepttester-v64-venv/bin/python (Z3 5.3.1.0). Other venvs lack Z3 and were
not modified. Public-input semantic probes remain post-generation only; no
private oracle, reference program, paid judge or full pipeline authorized.

Amendment B owner review: fresh retry subtracts prior unknown reservation from
the original overall cap before checking the four-slot total. Original terminal
run/source identity is retained; new source/plan frozen separately. No prompt or
wire changes, duplicate-root launch or within-run retries. Independent initial
review remains scoped to pre-retry code; no second independent review claimed.
