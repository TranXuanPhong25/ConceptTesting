# Transport amendment A — before ANY DeepInfra dispatch, 2026-10-26

Reka stopped at its third request after curl360s with partial reasoning stream,
no answer or usage. Two earlier receipts total$0.00392265. Read-only generation
lookup returns404, so retain the third request's FULL maximum reservation; do
not label cost zero or retry it. Fourth Reka slot remains unattempted/terminal.
Original runner/plan/source/freeze and controller terminal remain unchanged.

User explicitly requested BOTH Reka and DeepInfra/fp8. Original cross-provider
unknown-billing guard was unnecessarily strict given independent provider caps.
Proceed with the separately prepared, explicitly requested four-slot DeepInfra
run without any Reka retry or budget transfer. Its maximum four reservations
$0.10073340 fit its$0.12 cap regardless of the Reka bill. Original overall caps
$0.17+$0.12 and prior Relace reserve$0.04898572 remain unchanged, so worstcase
exposure remains bounded at$0.33898572 even with unknown Reka charge. No global
account denial occurred (only curl28 timeout). Any error/unknown within DeepInfra
still stops its run immediately;401/402/403 stops all additional spending.

No model answer or semantic assessment was inspected to make this transport-only
decision. No prompt/order/seed/provider/tokenbudget/scorer/cohort change. Existing
DeepInfra source/plan identity remains valid; amendment and separate launch
receipt are appended outside frozen artifacts. No further provider or retry.
