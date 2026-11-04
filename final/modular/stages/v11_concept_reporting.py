"""Modern benchmark reporting plus explicit V11 preparation cost and comparisons."""
import json

from .reporting import ReportingStage


class V11ConceptReportingStage(ReportingStage):
    def build_summary(self, contexts, cohort):
        summary = super().build_summary(contexts, cohort)
        rows = [context.result for context in contexts]
        concept_comparisons = []
        if "v11_concept" in summary["arms"]:
            for baseline in ("plain", "classical", "placebo"):
                if baseline in summary["arms"]:
                    concept_comparisons.append(self.compare(rows, "v11_concept", baseline))
        summary["comparisons"] = concept_comparisons + summary["comparisons"]
        preparation = {
            "programs": 0, "imported_programs": 0, "computed_programs": 0,
            "failed_programs": 0, "concept_cards": 0,
            "invocations": 0, "received": 0, "unknown": 0,
            "known_total_tokens": 0, "responses_with_missing_usage_footer": 0,
            "historical_mining_requests_referenced": 0,
        }
        historical_requests = set()
        for context in contexts:
            for record in context.extensions.get("v11_concepts", []):
                preparation["programs"] += 1
                preparation["concept_cards"] += len(record["cards"])
                preparation["failed_programs"] += record["state"] == "preparation_failed"
                provenance = record["provenance"]
                if provenance["origin"] == "imported":
                    preparation["imported_programs"] += 1
                    historical_requests.update(provenance["historical_mining_request_keys"])
                elif provenance["origin"] == "computed":
                    preparation["computed_programs"] += 1
        preparation["historical_mining_requests_referenced"] = len(historical_requests)
        requests_directory = contexts[0].artifacts.directory / "v11_concept_preparation/requests"
        preparation["invocations"] = len(list(requests_directory.glob("*/calls/*/attempt.json")))
        for path in requests_directory.glob("*/calls/*/response.json"):
            response = json.loads(path.read_text())
            usage = response.get("usage", {})
            preparation["received"] += 1
            preparation["known_total_tokens"] += usage.get("total_tokens", 0)
            preparation["responses_with_missing_usage_footer"] += usage.get("usage_footer_complete") is False
        preparation["unknown"] = preparation["invocations"] - preparation["received"]
        summary["v11_concept_preparation"] = preparation
        exclusions = [record for context in contexts for record in context.extensions.get("resource_exclusions", [])]
        if exclusions:
            summary["resource_exclusions"] = {
                "programs": len(exclusions), "records": exclusions,
                "scope": "preparation_prompt_and_evaluation",
                "original_cohort_base_pass": summary["base_pass"],
                "cohort_base_pass_after_exclusions": summary["base_pass"] - len(exclusions),
                "actually_evaluated_base_pass": summary["evaluated_base_pass"],
            }
        return summary

    def render(self, summary):
        exclusion_note = ""
        if summary.get("resource_exclusions"):
            exclusions = summary["resource_exclusions"]
            exclusion_note = (f"\nResource exclusions: {exclusions['programs']} PUTs omitted from concept preparation, "
                              "test-generation prompts and evaluation for BOTH arms. "
                              f"Actually evaluated base passes: {exclusions['actually_evaluated_base_pass']}. "
                              "The frozen-source cohort counts above describe the original cohort.\n")
        return super().render(summary) + exclusion_note + (
            "\nV11 concept preparation is accounted separately from the one-call inputs-only tester. "
            "Imported mining costs are historical shared costs, not zero-cost concept construction. "
            "No V11 hybrid/assertion/expected-output generation is used by this arm.\n\n"
            f"Preparation accounting: {summary['v11_concept_preparation']}.\n"
        )
