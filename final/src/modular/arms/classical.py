"""One catalogue/input completion per task/arm, using shared freeze and execution."""
from dataclasses import asdict, dataclass, replace
import re

from .base import InputGenerationMethod
from ..catalogue import validate_catalogue
from ..fault_oriented_testing.prompts import FAULT_HYPOTHESIS_OUTPUT_NOTE, soft_example_for
from ..response_json import load_response_json
from ..catalogue_response import read_catalogue_response


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
              '\nFor measured EP membership, add class predicate: a boolean expression over exact input parameter names, e.g. \"x > 0\" or \"len(xs) == 0\". Output-category predicates must describe the input scenario; do not invent or call an oracle.'
              '\nBoundary may add parameter, transform, lower/upper, numeric_kind(integer/float/discrete), step, context and nominal (complete named arguments). Float neighbors use a spec-defined step or adjacent representable values.'
              '\nDT may add catalogue.conditions (condition ID to possible values), mutually_exclusive (lists of condition IDs), and original_rules [{id,conditions,actions,status(feasible/infeasible/unresolved),reason}]. Preserve original IDs in covers after merging.'
              '\nFor measured DT membership, add catalogue.condition_predicates mapping each condition ID to a boolean input expression. Use boolean or T/F condition values and retain feasible original_rules; covers alone earns no observed coverage. Unsupported or missing definitions remain unknown.'
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
    example_key = ""

    def __init__(self, settings=None):
        self.settings = settings or CatalogueSettings()

    def configuration(self):
        configuration = {
            **asdict(self.settings),
            "sections": list(self.sections),
            "calls": "one-per-task-arm",
            "guidance": self.guidance,
        }
        if self.example_key:
            configuration.update(
                example_key=self.example_key,
                soft_example=soft_example_for(self.example_key),
                output_note=FAULT_HYPOTHESIS_OUTPUT_NOTE,
                semantic_fault_hypothesis_validation="pending",
            )
        return configuration

    def reporter(self):
        from ..catalogue_reporting import CatalogueReporter
        return CatalogueReporter()

    def build_guidance(self, packet):
        guidance = self.guidance
        if not self.settings.catalogue:
            guidance = re.sub(r"List (?:the )?(?:classes|boundaries|rules|classes and boundaries|classes, boundaries and rules) in the catalogue\.", "", guidance)
        if not self.example_key:
            return guidance
        if self.settings.catalogue:
            guidance += "\n" + FAULT_HYPOTHESIS_OUTPUT_NOTE
        return (
            guidance
            + "\n\nSOFT EXAMPLE (another domain; adapt only useful ideas):\n"
            + soft_example_for(self.example_key)
        )

    def extend_summary(self, contexts, summary, reporting):
        if not self.example_key:
            return
        accounting = {
            "classes": 0,
            "rules": 0,
            "annotated_classes": 0,
            "annotated_rules": 0,
            "status": "self_reported",
            "semantic_validation": "pending",
        }
        for context in contexts:
            batch = (context.inputs or {}).get("arms", {}).get(self.name, {})
            catalogue = batch.get("catalogue") or {}
            for section in ("classes", "rules"):
                for obligation in catalogue.get(section, []):
                    accounting[section] += 1
                    accounting["annotated_" + section] += bool(
                        obligation.get("fault_hypothesis")
                    )
        summary.setdefault("fault_hypothesis_annotations", {})[self.name] = accounting

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
        repairs=[]
        if not self.settings.catalogue:
            try:
                raw,repairs=read_catalogue_response(response.text)
                if repairs:response=replace(response,text=repr(raw))
            except (ValueError,TypeError,RecursionError):
                pass
        result = super().decode_response(response, context)
        if not self.settings.catalogue:
            if repairs:
                result["response_repairs"] = repairs + result.get("response_repairs", [])
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
