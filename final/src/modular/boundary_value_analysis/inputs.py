"""Strict JSON named-argument decoder; encode values without computing targets."""
import json


def decode_inputs(response, builder, input_budget):
    if response.finish_reason == "length":
        return {"status": "invalid_generation", "inputs": [], "rejected": [{"reason": "truncated_response"}]}
    try:
        record = json.loads(response.text)
        if not isinstance(record, dict) or set(record) != {"inputs"} or not isinstance(record["inputs"], list):
            raise ValueError("invalid_envelope")
        if len(record["inputs"]) > input_budget:
            raise ValueError("input_budget_exceeded")
    except (ValueError, TypeError, RecursionError):
        return {"status": "invalid_generation", "inputs": [], "rejected": [{"reason": "invalid_response"}]}
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(record["inputs"]):
        try:
            if not isinstance(row, dict) or set(row) != {"arguments"}:
                raise ValueError("invalid_input_record")
            encoded = builder.build(row["arguments"])
            identity = encoded["args"], encoded["kwargs"]
            if identity in seen:
                raise ValueError("duplicate_within_arm")
            seen.add(identity)
            accepted.append(encoded)
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            reason = str(error) if type(error) is ValueError else "invalid_input_record"
            rejected.append({"index": index, "reason": reason})
    return {"status": "generated" if accepted else "no_inputs", "inputs": accepted, "rejected": rejected}
