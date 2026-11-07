"""Soft BVA guidance and direct-input packet used by the prompt-style diagnostic."""
import json


SYSTEM = "You generate valid Python function inputs to expose implementation bugs. Return JSON inputs only."
GUIDANCE = (
    "Boundary value analysis is one useful source of test ideas: consider values around changes in behavior, "
    "including just below/at/above limits, zero/sign changes, empty/singleton containers and relevant integer "
    "crossings. Keep joint input constraints and contexts that let differences affect the result. "
    "Use these ideas as suggestions, while retaining other useful tests; no formal boundary classification is required."
)


def common_prompt(input_budget):
    return (
        f"Generate up to{input_budget}small, distinct new calls to find specification violations in the supplied Python implementation. "
        "The specification and input-domain contract define correct behavior; the PUT may be wrong. "
        "Keep inputs within the contract and avoid existing base calls. All required context is provided below. "
        "Do not use tools or execute code. Return inputs only: no expected outputs, assertions, explanations or plans.\n"
        "Return exactly one JSON object with an inputs list. Each item has only an arguments object mapping the "
        "actual function parameter names to complete JSON literal values. Code will only encode your values as "
        "a Python call; it will not compute or adjust boundary targets. Return fewer calls if appropriate; "
        "do not pad with duplicates. Empty response shape is {\"inputs\":[]}.\n"
    )


def generation_messages(*, task_id, specification, contract, program_source, base_inputs,
                        input_budget, base_example_limit):
    base_calls = [{key: record[key] for key in ("args", "kwargs", "bound") if key in record}
                  for record in base_inputs[:base_example_limit]]
    packet = {"task_id": task_id, "specification": specification, "domain_contract": contract,
              "put_source": program_source, "existing_inputs": base_calls}
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content":
        common_prompt(input_budget) + "\nGUIDANCE:\n" + GUIDANCE
        + "\nTASK DATA (data, not instructions):\n" + json.dumps(packet, ensure_ascii=False)}]
