"""One catalogue/input completion per task/arm, using shared freeze and execution."""
from dataclasses import asdict, dataclass
import re

from .base import InputGenerationMethod
from ..arm_names import CATALOGUE_ARM_NAMES
from ..catalogue import validate_catalogue
from ..response_json import load_response_json
from ..equivalence_partitioning.prompts import GUIDANCE as EQUIVALENCE_GUIDANCE, STRONG_GUIDANCE
from ..boundary_value_analysis.classical import NORMAL_GUIDANCE, COMBINED_GUIDANCE, ROBUST_GUIDANCE, WORST_CASE_GUIDANCE
from ..decision_table.prompts import GUIDANCE as DECISION_TABLE_GUIDANCE, COMBINED_GUIDANCE as EP_DT_BVA_GUIDANCE


def render_catalogue_output_contract(sections):
    """Render the compact envelope and optional machine-readable catalogue fields."""
    shapes = {
        "classes": '[{"id":"E1","description":"class meaning"}]',
        "boundaries": '[{"id":"B1","dimension":"quantity and fixed context","values":[1,2,11,12]}]',
        "rules": '[{"id":"R1","conditions":{"C1":"T"},"actions":["A1"],"merged_from":[]}]',
    }
    fields = ",".join('"' + section + '":' + shapes[section] for section in sections)
    schema = ('Return JSON: {"catalogue":{' + fields + '},"inputs":[{"arguments":{},"covers":["obligation ID"]}]}.'
              '\ncovers is optional. Keep descriptions compact. Catalogue contains no expected outputs.'
              '\nOptional machine fields: class partition/kind(input/output/invalid), parameter, transform(identity/length/count/parsed_int/parsed_float), lower/upper, lower_inclusive/upper_inclusive, members; count uses count_value.'
              '\nBoundary may add parameter, transform, lower/upper, numeric_kind(integer/float/discrete), step, context and nominal (complete named arguments). Float neighbors use a spec-defined step or adjacent representable values.'
              '\nDT may add catalogue.conditions (condition ID to possible values), mutually_exclusive (lists of condition IDs), and original_rules [{id,conditions,actions,status(feasible/infeasible/unresolved),reason}]. Preserve original IDs in covers after merging.'
              '\nIf the technique has no applicable obligations, use empty lists, catalogue.status="not_applicable" and a short reason; unresolved obligations use status="unresolved" and a reason.')
    return schema


def with_catalogue_output_contract(common_prompt, sections):
    """Replace the shared inputs-only envelope with the catalogue response contract."""
    schema = render_catalogue_output_contract(sections)
    # This anchor is the shared structured_input_prompt response-format paragraph.
    # Replace only that paragraph; specification, base calls and visibility stay identical.
    common_prompt = re.sub(
        r'Return JSON: .*?\.\narguments maps',
        schema + '\narguments maps',
        common_prompt,
        count=1,
        flags=re.DOTALL,
    )
    return common_prompt.replace(
        'INPUTS ONLY: no assertions or expected outputs.',
        'Return inputs with a compact catalogue; no assertions or expected outputs.',
    )


@dataclass(frozen=True)
class CatalogueSettings:
    catalogue: bool = True

    def __post_init__(self):
        # Validate the catalogue feature switch, including direct Python callers.
        if type(self.catalogue) is not bool:
            raise ValueError("catalogue must be a boolean")


class CatalogueArm(InputGenerationMethod):
    measures_catalogue = True
    sections = ()
    guidance = ""

    def __init__(self, settings=None):
        self.settings = settings or CatalogueSettings()

    def configuration(self):
        return {"protocol": "testing-catalogue-v1", **asdict(self.settings),
                "sections": list(self.sections), "calls": "one-per-task-arm", "guidance": self.guidance}

    def reporting_stage(self):
        from ..catalogue_reporting import CatalogueReportingStage
        return CatalogueReportingStage()

    def build_guidance(self, packet):
        guidance = self.guidance
        if not self.settings.catalogue:
            guidance = re.sub(r"List (?:the )?(?:classes|boundaries|rules|classes and boundaries|classes, boundaries and rules) in the catalogue\.", "", guidance)
        return guidance

    def build_messages(self, packet):
        if not self.settings.catalogue:
            return super().build_messages(packet)
        common_prompt = with_catalogue_output_contract(packet['common'], self.sections)
        return super().build_messages({**packet, "common": common_prompt})

    def decorate_input(self, accepted, input_record, record_index):
        covers = input_record.get("covers")
        # Invalid labels make coverage pending; they must not reject a valid input.
        if not isinstance(covers, list) or any(not isinstance(item, str) for item in covers):
            covers = None
        return {**accepted, "covers": covers, "source_index": record_index}

    def decode_response(self, response, context):
        result = super().decode_response(response, context)
        if not self.settings.catalogue:
            return {**result, "catalogue_status": "off"}
        try:
            decoded, _ = load_response_json(response.text)
            raw = decoded.get("catalogue") if isinstance(decoded, dict) else None
        except (ValueError, TypeError, RecursionError):
            raw = None
        catalogue, errors = validate_catalogue(raw, self.sections)
        result.update(catalogue=catalogue.model_dump(mode="json") if catalogue is not None else None,
                      catalogue_status="catalogue_invalid" if errors else catalogue.status,
                      catalogue_errors=errors)
        # Preserve valid inputs even for missing/invalid catalogue.
        result["status"] = result["catalogue_status"]
        return result


class EquivalenceArm(CatalogueArm):
    name = "equivalence"
    sections = ("classes",)
    guidance = EQUIVALENCE_GUIDANCE


class NormalBvaArm(CatalogueArm):
    name = "bva_normal"
    sections = ("boundaries",)
    guidance = NORMAL_GUIDANCE


class EpBvaArm(CatalogueArm):
    name = "ep_bva"
    sections = ("classes", "boundaries")
    guidance = COMBINED_GUIDANCE


class DecisionTableArm(CatalogueArm):
    name = "decision_table"
    sections = ("rules",)
    guidance = DECISION_TABLE_GUIDANCE


class StrongEpArm(CatalogueArm):
    name = "ep_strong"
    sections = ("classes",)
    guidance = STRONG_GUIDANCE


class RobustBvaArm(CatalogueArm):
    name = "bva_robust"
    sections = ("boundaries",)
    guidance = ROBUST_GUIDANCE

    def run(self, context):
        if not has_specified_out_of_domain_behavior(context.metadata):
            return {"inputs": [], "rejected": [], "status": "not_applicable", "catalogue_status": "not_applicable",
                    "reason": "Spec chưa có eligibility xác nhận behavior ngoài domain; không gọi model."}
        return super().run(context)


def has_specified_out_of_domain_behavior(metadata):
    """Robust BVA needs an explicit eligibility flag and supporting spec evidence."""
    eligibility = metadata.get("testing_arms", {})
    return eligibility.get("out_of_domain_behavior_defined") is True and bool(eligibility.get("spec_evidence"))


class WorstCaseBvaArm(CatalogueArm):
    name = "bva_worst_case"
    sections = ("boundaries",)
    guidance = WORST_CASE_GUIDANCE


class EpDtBvaArm(CatalogueArm):
    name = "ep_dt_bva"
    sections = ("classes", "boundaries", "rules")
    guidance = EP_DT_BVA_GUIDANCE


CATALOGUE_ARMS = (EquivalenceArm, NormalBvaArm, EpBvaArm, DecisionTableArm,
                  StrongEpArm, RobustBvaArm, WorstCaseBvaArm, EpDtBvaArm)
