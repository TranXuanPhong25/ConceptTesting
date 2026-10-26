# v79 DeepSeek diagnosis

2026-10-26: isolated copy of v73_ossdiagnosis for four exact v72 prompt replays.
Change model/provider/output budget only; unsupported API seed removed. New
ds_probe.py uses PREREG_V79/REVIEW_V79, exact Relace eligibility/provider checks,
$0.15 cap and doubled prompt byte envelope. No parent/vendor modification.
Inherited PREREG_V73/REVIEW_V73 are historical; V79 files govern this run.

Terminal: first request returned Relace upstream shared-pool HTTP429, zero model
responses, three unattempted slots, one unknown-cost attempt. No retry/fallback.
Four-call reservation $0.09967314 under $0.15. Source/prior/output hashes verified;
see analysis/v79_deepseekdiagnosis/RESULTS.md. Credentials only silently sourced.

User-authorized fresh retry after429 (amendment B) also terminal on first429.
Subtract prior unresolved reservation from overallcap before new planning.
Cumulative2attempts/0responses/2unknowncharges, reserved$0.04898572, no more calls.
