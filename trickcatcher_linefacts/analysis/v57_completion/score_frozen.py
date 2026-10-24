"""P0B: evaluate frozen v57 raw finals after P1 freeze.

Private canonical/contract files are read only here. This script has no model
client and never writes inside the frozen generation directory.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
GENERATION = ROOT / "trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/generation_v2"
REQUESTS = ROOT / "trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json"
P1 = ROOT / "trickcatcher_linefacts/out/pipelines/v60_pathfault_complete/p1_source_inventory.json"
DATA = ROOT / "trickcatcher_linefacts/out/heldout_vibepass_real/he/humaneval_mbpp_plus.jsonl"
WORKER = ROOT / "trickcatcher_linefacts/pipelines/v60_pathfault_complete/score_worker.py"
SCORING_CORE=ROOT/'trickcatcher_linefacts/pipelines/v60_pathfault_complete/frozen_score.py'
OUT = Path(__file__).resolve().parent / "out"

sys.path.insert(0, str(ROOT))
from trickcatcher_linefacts.pipelines.v60_pathfault_complete.frozen_score import audit_freeze, label_slots, raw_final_slots, summarize,dedup_annotations  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_worker(source: str, entry: str, args: tuple[Any, ...], out_root: Path, kind: str, case_id: str) -> dict[str, Any]:
    identity={'source':source,'entry':entry,'args':repr(args),'kind':kind,'worker_sha256':_hash(WORKER),
              'scoring_core_sha256':_hash(SCORING_CORE),
              'scorer_sha256':_hash(Path(__file__)),'python':sys.version,'interpreter':sys.executable,
              'limits':{'wall':2,'memory':512*1024*1024,'outer':8},'comparator':'historical_heldout_same'}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = (out_root / "worker_cache" / key).resolve()
    job, result = folder / "job.json", folder / "result.json"
    if result.exists():
        return json.loads(result.read_text())
    folder.mkdir(parents=True, exist_ok=True)
    job.write_text(json.dumps({
        "source": source, "entry": entry, "input_repr": repr(args), "kind":kind,"mode": "ordinary", "valid_code": None,
        "limits": {"address_space_bytes": 512 * 1024 * 1024, "worker_timeout": 2, "max_events": 1,
                   "max_names": 0, "snapshot_bytes": 0, "max_output_bytes": 8192},
    }) + "\n")
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    process = subprocess.Popen(["unshare", "-rn", sys.executable, "-I", "-B", str(WORKER.resolve()), str(job.resolve()), str(result.resolve())],
                               cwd=folder, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        code = process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL); process.wait()
        return {"status": "unresolved", "reason": "outer_timeout"}
    if code or not result.exists():
        return {"status": "unresolved", "reason": "worker_failure"}
    return json.loads(result.read_text())


def _typed(value: Any) -> tuple[Any, Any]:
    if type(value) in (bool, int, float, str) or value is None:
        return (type(value).__name__, value)
    if type(value) in (list, tuple):
        return (type(value).__name__, tuple(_typed(x) for x in value))
    if type(value) is dict:
        return ("dict", tuple(sorted((_typed(k), _typed(v)) for k, v in value.items())))
    raise ValueError("unsupported_literal_type")


def _same(a: Any, b: Any, atol: float) -> bool:
    numeric=lambda x:isinstance(x,(int,float)) and not isinstance(x,bool)
    if numeric(a) and numeric(b) and (isinstance(a,float) or isinstance(b,float)):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=atol or 1e-6)
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)) and len(a)==len(b):
        return type(a)==type(b) and all(_same(x,y,atol) for x,y in zip(a,b))
    return a == b


def _decode(worker: dict[str, Any]) -> tuple[str, Any]:
    if worker.get("status") == "exception":
        return ("exception", worker.get("exception_type"))
    if worker.get("status") == "ok" and worker.get("output_repr") is not None:
        try:
            return ("ok", ast.literal_eval(worker["output_repr"]))
        except (ValueError, SyntaxError):
            return ("unresolved", None)
    return ("unresolved", None)


def _load_cases() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    requests = {r["case_id"]: r for r in json.loads(REQUESTS.read_text())}
    plus = {str(int(r["task_id"].split("/")[-1])): r for r in map(json.loads, DATA.read_text().splitlines())}
    return requests, plus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if not P1.exists():
        raise SystemExit("P1 inventory must be frozen before private scoring")
    p1 = json.loads(P1.read_text())
    if p1.get("private_data_used") is not False:
        raise SystemExit("P1 inventory is not source-only")
    freeze = audit_freeze(GENERATION)
    if not freeze["ok"]:
        raise SystemExit("frozen generation audit failed")
    requests, plus = _load_cases()
    protocol=json.loads((GENERATION/'protocol.json').read_text())
    if len(protocol['inputs'])!=len(requests): raise ValueError('protocol_case_count')
    for request,pinned in zip(requests.values(),protocol['inputs']):
        value=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
        if value!=pinned['request_sha256']: raise ValueError('public_request_manifest_mismatch')
    if _hash(REQUESTS)!=p1['requests_sha256']: raise ValueError('P1_request_manifest_mismatch')
    case_ids = list(requests)
    slots = raw_final_slots(GENERATION, case_ids)
    args.out.mkdir(parents=True, exist_ok=True)

    def evaluate(case_id: str, test_args: tuple[Any, ...], expected: Any) -> dict[str, Any]:
        request, row = requests[case_id], plus[case_id]
        contract = row["prompt"] + row["contract"] + "\n    pass\n"
        valid = _run_worker(contract, row["entry_point"], test_args, args.out, "contract", case_id)
        if valid.get('status')=='invalid':
            return {"status": "invalid_input", "reason": str(valid.get("exception_type", valid.get("status")))}
        if valid.get('status')!='ok':
            return {'status':'unresolved','reason':'validity_checker_failed:'+str(valid.get('reason',valid.get('exception_type','unknown')))}
        put = _run_worker(request["source"], request["entry"], test_args, args.out, "put", case_id)
        ref = _run_worker(row["prompt"] + row["canonical_solution"], row["entry_point"], test_args, args.out, "reference", case_id)
        put_state, put_value = _decode(put)
        ref_state, ref_value = _decode(ref)
        if "unresolved" in (put_state, ref_state):
            return {"status": "unresolved", "reason": "put_or_reference"}
        if ref_state=='exception': return {'status':'unresolved','reason':'reference_exception_outside_normal_equality_oracle'}
        if put_state != ref_state or (put_state == "ok" and not _same(put_value, ref_value, float(row.get("atol", 0.0)))):
            if ref_state == "ok" and _same(expected, ref_value, float(row.get("atol", 0.0))):
                return {"status": "confirmed"}
            return {"status": "input_discrepancy_wrong_expected"}
        if put_state == "ok" and not _same(expected, put_value, float(row.get("atol", 0.0))):
            return {"status": "false_alarm"}
        return {"status": "passing_test"}

    labels = dedup_annotations(label_slots(slots, evaluate))
    summary=summarize(labels)
    problem={cid:plus[cid]['question_id'] for cid in case_ids}
    detected={a:set(v['tasks_confirmed']) for a,v in summary.items()}
    paired={a:{b:{'wins':sorted(detected[a]-detected[b]),'losses':sorted(detected[b]-detected[a]),
                   'wins_problem_ids':sorted({str(problem[x]) for x in detected[a]-detected[b]}),
                   'losses_problem_ids':sorted({str(problem[x]) for x in detected[b]-detected[a]})}
               for b in detected if b!=a} for a in detected}
    costs={}
    for a in summary:
        responses=[json.loads(p.read_text()) for cid in case_ids for p in (GENERATION/cid/a).glob('*/response.json')]
        costs[a]={'slots':len(responses),'input_tokens':sum((r.get('response')or{}).get('input_tokens',0)or 0 for r in responses),
                  'output_tokens':sum((r.get('response')or{}).get('output_tokens',0)or 0 for r in responses)}
    report = {"scope": "retrospective frozen-v57 score", "freeze": freeze,
              'provisional':True,'review_required':True,
              'provenance':{'scorer_sha256':_hash(Path(__file__)),'worker_sha256':_hash(WORKER),
                            'scoring_core_sha256':_hash(SCORING_CORE),
                            'public_requests_sha256':_hash(REQUESTS),'private_dataset_sha256':_hash(DATA),
                            'python':sys.version,'comparator':'historical_heldout_same'},
              "p1_inventory_sha256": _hash(P1), "generation_sha256": _hash(GENERATION / "generation_frozen.json"),
              "cases": case_ids,'problem_ids':problem,'paired':paired,'generator_costs':costs,
              'shared_writer_cost_policy':'one shared slot per case; report separately, allocated to each compared package',
              'duplicate_policy':'raw slot metrics primary; duplicate/conflict annotations retain all slots',
              'invalid_alarm_policy':'invalid_input excluded from valid metrics; separate invalid count, not implicitly confirmed',
              "rows": labels, "summary": summary}
    path = args.out / "score.json"
    if path.exists():
        raise SystemExit("score output already exists")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
