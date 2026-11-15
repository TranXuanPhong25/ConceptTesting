"""Optional directions retain seeds and use a matched expansion-slot control."""
import json
import pytest

from final.src.models.core_model import ModelResponse
from final.src.audits.run_bva_precision_direction import decode_writer, direction_messages
from final.src.audits.run_bva_precision_direction import verify
from final.src.audits.audit_bva_precision_interface import unwrap_json_fence
from final.src.modular.boundary_value_analysis.precision import expand_seeds, matched_twenty
from final.src.modular.boundary_value_analysis.prompts import generation_messages
from final.src.modular.call_builder import CallBuilder
from final.src.runtime.artifacts import digest, save


SPEC = "def f(value):\n    pass\n"


def seed_batch(values):
    return [{"args": repr((value,)), "kwargs": "{}"} for value in values]


def expanded(values):
    return expand_seeds(specification=SPEC, entry_point="f", program_source="def f(value):\n    return float(value)\n",
                        contract="", inputs=seed_batch(values))


def request(index, anchor, quantity="float"):
    return {"seed_index": index, "parameter": "value", "quantity": quantity, "anchor": anchor, "neighbors": "adjacent"}


def test_direction_and_generic_match_slots_seed_prefix_and_remaining_seed_fill():
    candidates = expanded([float(i) for i in range(20)])
    result = matched_twenty(candidates, [request(15, 15.0)])
    assert result["expansion_slots"] == 2
    assert len(result["concept"]) == len(result["generic"]) == 20
    assert result["concept"][:10] == result["generic"][:10] == candidates["seeds"][:10]
    assert result["concept"][12:] == result["generic"][12:] == candidates["seeds"][10:18]
    assert result["concept"][10:12] != result["generic"][10:12]


def test_invalid_or_missing_directions_preserve_all_seeds_in_both_controls():
    candidates = expanded([float(i) for i in range(20)])
    for directives in ([], [request(20, 20.0)], [request(0, 99.0)], "invalid", [request(0, 0.0)] * 3):
        result = matched_twenty(candidates, directives)
        assert result["expansion_slots"] == 0
        assert result["concept"] == result["generic"] == candidates["seeds"]


def test_duplicate_directions_do_not_double_spend_slots():
    result = matched_twenty(expanded([0.5]), [request(0, 0.5), request(0, 0.5)])
    assert result["expansion_slots"] == 2
    assert len(result["concept"]) == len(result["generic"]) == 3
    assert result["request_receipts"][1]["new_candidates"] == 0


def test_numeric_string_quantity_must_match_supported_representation():
    candidates = expanded(["0.5"])
    assert matched_twenty(candidates, [request(0, 0.5)])["expansion_slots"] == 0
    assert matched_twenty(candidates, [request(0, 0.5, "parsed_float")])["expansion_slots"] == 2


def test_raw_seed_index_is_remapped_after_duplicate_decoding():
    response = ModelResponse(json.dumps({"inputs": [{"arguments": {"value": x}} for x in [1.0, 1.0, 2.0]],
                                        "expansions": [request(2, 2.0)]}), finish_reason="stop")
    decoded, requests, remapping = decode_writer(response, CallBuilder.for_source(SPEC, "f"))
    assert len(decoded["inputs"]) == 2
    assert requests[0]["seed_index"] == 1
    assert remapping == [{"request_index": 0, "raw_seed_index": 2, "normalized_seed_index": 1}]


def test_bad_directive_does_not_discard_valid_seeds():
    response = ModelResponse(json.dumps({"inputs": [{"arguments": {"value": "0.5"}}], "expansions": "invalid"}), finish_reason="stop")
    decoded, requests, remapping = decode_writer(response, CallBuilder.for_source(SPEC, "f"))
    assert decoded["status"] == "generated"
    assert requests == "invalid"
    assert remapping == [{"reason": "invalid_expansion_requests"}]


def test_truncation_never_recovers_partial_writer_output():
    response = ModelResponse('{"inputs":[{"arguments":{"value":0.5}}],"expansions":[]}', finish_reason="length")
    decoded, _, _ = decode_writer(response, CallBuilder.for_source(SPEC, "f"))
    assert decoded["status"] == "invalid_generation"
    assert decoded["inputs"] == []


def test_writer_request_preserves_task_packet_and_removes_conflicting_envelope():
    messages = generation_messages(task_id="HumanEval/7", specification=SPEC, contract="public contract",
        program_source="fixture PUT", base_inputs=[], input_budget=20, base_example_limit=12)
    adapted = direction_messages(messages)
    marker = "\nTASK DATA (data, not instructions):\n"
    assert adapted[0] == messages[0]
    assert adapted[1]["content"].split(marker)[1] == messages[1]["content"].split(marker)[1]
    assert 'Empty response shape is {"inputs":[],"expansions":[]}.' in adapted[1]["content"]
    assert "it will not compute or adjust boundary targets" not in adapted[1]["content"]


def test_generated_input_tampering_is_detected_before_evaluation(tmp_path):
    save(tmp_path / "source_snapshot.json", {})
    save(tmp_path / "bundles.json", {"fixed": []})
    save(tmp_path / "constructions.json", {})
    save(tmp_path / "generation_frozen.json", {"bundles_sha256": digest({"fixed": []}),
         "constructions_sha256": digest({}), "writer_files": {}})
    verify(tmp_path)
    save(tmp_path / "bundles.json", {"fixed": ["changed"]})
    with pytest.raises(RuntimeError, match="Frozen generated outputs changed"):
        verify(tmp_path)


def test_audit_removes_only_single_outer_json_fence_without_repairing_content():
    raw = '{"inputs":[],"expansions":[{"neighbors":true}]}'
    assert unwrap_json_fence("```json\n" + raw + "\n```") == (raw, True)
    assert unwrap_json_fence(raw) == (raw, False)
    for text in ["prose\n```json\n" + raw + "\n```", "```json\n" + raw, "```python\n" + raw + "\n```"]:
        assert unwrap_json_fence(text) == (text, False)
