"""Public-only retrieval prompts and separate blinded grading prompts."""
from __future__ import annotations

import ast
import hashlib
import json
import random

from ..retrieval_v2 import corpus
from ..retrieval_v2.engine import search as structural_search

CARDS = corpus.cards()
CODE_TO_CARD = {f"C{i:03d}": card for i, card in enumerate(CARDS, 1)}
ID_TO_CODE = {card["id"]: code for code, card in CODE_TO_CARD.items()}
BY_ID = {c["id"]: c for c in CARDS}


def numbered(code):
    return "\n".join(f"{i}: {line}" for i, line in enumerate(code.splitlines(), 1))


def compact(card):
    return {"title": card["title"], "where": card["where"]["summary"], "how": card["how"]["mechanism"],
            "what": card["what"]["observable_failure"], "test": card["how"]["trigger_template"]}


def retrieval(task):
    local = structural_search(code=task["code"], top_k=8)["results"]
    catalog = "\n".join(code + " " + card["title"] for code, card in CODE_TO_CARD.items())
    details = [{"id": ID_TO_CODE[x["concept"]["id"]], **compact(x["concept"])} for x in local[:6]]
    system = """You retrieve bug concepts to guide testing of Python code. Analyze the specification and implementation, then select up to THREE catalog concepts describing plausible actual faults. A card describing an operation merely present in correct code is not a useful hit. Use the full catalog to recover concepts absent from the detailed shortlist. Do not invent catalog IDs. A candidate is a hypothesis, not proof. Prefer precise mechanisms and abstain if none fit.
Return ONLY JSON: {"selected":[{"id":"C001","line":12,"where":"concrete faulty expression and relevant contract","how":"specific causal mechanism; explain which assumption is wrong","what":"observable consequence and input class distinguishing correct from faulty behavior"}],"abstain_reason":""}.
The line must be ONE real implementation line as a JSON integer, not a docstring/example. Do not output tests, reference code, markdown or chain-of-thought. Keep each where/how/what under 35 words. Rank strongest first. Do not select multiple descriptions of the same fault when a distinct supported fault is available.
Before selecting, mentally compare a small valid example with the specification. In what, name a concrete distinguishing input class or tiny example and the expected versus faulty consequence. If the alleged bad case actually returns the specified result, reject that hypothesis. A correct min call, correct empty guard, or presence of a numeric comparison is not itself a bug. Do not fill three slots just to fill the array."""
    user = "PUBLIC SOURCE (line numbered):\n" + numbered(task["code"]) + "\n\nCATALOG:\n" + catalog
    user += "\n\nDETAILED CANDIDATES (not a restriction):\n" + json.dumps(details, ensure_ascii=False)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_retrieval(response, code):
    if response.get("status") != "received" or not isinstance(response.get("parsed"), dict) or "selected" not in response["parsed"]:
        return [], "no_valid_retrieval_response"
    parsed = response.get("parsed") or {}
    rows = parsed.get("selected", [])
    if not isinstance(rows, list) or len(rows) > 3:
        return [], "invalid_selected_array"
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in CODE_TO_CARD:
            return [], "invalid_catalog_id"
        if row["id"] in seen:
            return [], "duplicate_concept"
        # Explicit transport normalization, recorded in the protocol: JSON decimal
        # strings and integers denote the same source-line number. No re-prompt.
        if isinstance(row.get("line"), str) and row["line"].isdigit():
            row = {**row, "line": int(row["line"]), "line_normalized_from_string": True}
        if type(row.get("line")) is not int or not 1 <= row["line"] <= len(code.splitlines()):
            return [], "invalid_source_line"
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("where", "how", "what")):
            return [], "missing_where_how_what"
        seen.add(row["id"])
        result.append({"concept_id": CODE_TO_CARD[row["id"]]["id"], "line": row["line"],
                       "where": row["where"], "how": row["how"], "what": row["what"],
                       "line_normalized_from_string": row.get("line_normalized_from_string", False)})
    return result, None


def baseline(task):
    hits = structural_search(code=task["code"], top_k=3)["results"]
    return [{"concept_id": h["concept"]["id"], "line": h["evidence"][0]["line"] if h["evidence"] else None,
             "where": h["evidence"][0]["expression"] if h["evidence"] else h["concept"]["where"]["summary"],
             "how": h["concept"]["how"]["mechanism"], "what": h["concept"]["what"]["observable_failure"]} for h in hits]


def judge(task, systems, reference, witness):
    # Dedupe card selections; bindings remain separate anonymous records.
    ids = sorted({row["concept_id"] for rows in systems.values() for row in rows})
    rng = random.Random(int(hashlib.sha256(task["code"].encode()).hexdigest(), 16))
    rng.shuffle(ids)
    labels = {f"K{i}": key for i, key in enumerate(ids)}
    cards = [{"key": key, **compact(BY_ID[cid])} for key, cid in labels.items()]
    binding_rows = []
    binding_map = {}
    items = [(system, rank, row) for system, rows in systems.items() for rank, row in enumerate(rows)]
    rng.shuffle(items)
    for i, (system, rank, row) in enumerate(items):
        key = f"B{i}"
        card_key = next(k for k, cid in labels.items() if cid == row["concept_id"])
        binding_rows.append({"key": key, "card": card_key, **{k: row[k] for k in ("line", "where", "how", "what")}})
        binding_map[key] = {"system": system, "rank": rank, "concept_id": row["concept_id"]}
    schema = {"cards": [{"key": "K0", "grade": 0, "reason": "one precise sentence"}],
              "bindings": [{"key": "B0", "where": 0, "how": 0, "what": 0, "reason": "one precise sentence"}]}
    system = """You evaluate retrieved concepts, not the programming solution. Methods and ranks are hidden. Use the reference implementation and validated example only as grading evidence. Never assume a concept is good because its title sounds related.
Grade EACH card selection: 0 irrelevant or wrong mechanism; 1 operation/context applicable but no actual bug connection; 2 correctly describes an actual bug mechanism in the PUT; 3 precise actual mechanism with a concrete consequence and distinguishing input class. A card need not match the single supplied witness if another actual bug is supported by code/reference. Mere generic boundary or empty-input advice receives at most 1 unless concretely connected to a real fault.
Separately grade EACH binding on where/how/what, 0 or 1 each. where=1 only if cited line/expression is a real fault site, how=1 only if explanation correctly states the causal mechanism, what=1 only if consequence and input class can distinguish PUT from correct behavior. Generic text is not automatically false but gets 0 when it fails to establish the task-specific connection. Return only the requested JSON. Keep each reason <=20 words. Do not reveal chain-of-thought."""
    payload = {"source": numbered(task["code"]), "reference": reference,
               "validated_witness": witness, "cards": cards, "bindings": binding_rows, "output_shape": schema}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], {"cards": labels, "bindings": binding_map}


def utility(task, hints):
    system = """Write diagnostic tests for the provided Python function using only its public specification and implementation. Return ONLY JSON {"tests":[{"args":[...],"expected":...}]} with at most THREE tests. args is the positional argument list and expected is the correct return value from the specification, not the buggy code's output. Use literal JSON data, no code strings, no nan/inf. Prefer small valid boundary inputs that can expose a concrete bug. Hints, if present, are unverified hypotheses: reject them if inconsistent with the spec. No prose or chain-of-thought."""
    payload = {"entry": task["entry_point"], "source": task["code"], "concept_hints": [compact(BY_ID[h["concept_id"]]) for h in hints]}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
