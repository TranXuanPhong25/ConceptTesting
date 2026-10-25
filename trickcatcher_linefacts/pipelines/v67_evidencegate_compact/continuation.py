"""Import an interrupted v62 run without reissuing completed writer requests.

This is an explicit engineering continuation, not a fresh independent experiment.
The original source and receipts remain the provenance of imported observations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from .ngrok_run import read_record, write_new, digest
from .semantic_contract import writer_packet, admit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(out):
    manifest = read_record(out / 'continuation.json')
    origin = Path(manifest['origin'])
    for rel, expected in manifest['original_inventory'].items():
        if sha(origin / rel) != expected:
            raise ValueError('continuation_original_integrity')
    for rel, expected in manifest['imported_inventory'].items():
        if sha(out / rel) != expected:
            raise ValueError('continuation_import_integrity')
    return manifest


def import_run(origin, out, requests_path):
    from .pipeline import source_identity, load_checkpoint
    from ..v62_pathfault_contractfix.pipeline import readiness_identity as old_readiness
    from ..v62_pathfault_contractfix.semantic_contract import admit as old_admit
    origin = origin.resolve()
    if out.exists():
        raise ValueError('continuation_destination_exists')
    ready = read_record(origin.parent / 'reviewed_ready.json')
    if ready != {'status': 'reviewed_ready', 'identity': old_readiness(requests_path)}:
        raise ValueError('continuation_original_readiness')
    requests = read_record(requests_path)
    if list(origin.rglob('result.json')) or (origin/'generation_frozen.json').exists():
        raise ValueError('continuation_expects_pre_arm_stop')
    inventory = {str(p.relative_to(origin)): sha(p) for p in sorted(origin.rglob('*.json'))}
    plan = []
    original_cases = {}
    total_attempts = 0
    completed = []
    for request in requests:
        cid = str(request['case_id'])
        folder = origin/cid
        case = read_record(folder/'case_protocol.json')
        expected_case = {'request': request, 'model': 'qwen2.5-coder-32b-instruct',
                         'sources': ready['identity']['sources'], 'python': sys.version}
        if case != expected_case:
            raise ValueError('continuation_original_case_identity')
        original_cases[cid] = case
        slot = folder/'shared_writer'
        identity = {'messages': [
            {'role':'system','content':'Return a JSON object. Separate spec requirements from observed behavior; unknown claims remain unknown.'},
            {'role':'user','content':json.dumps(writer_packet(request))}],
            'stage':'writer','seed':20261024,'max_tokens':1536,
            'model':case['model'],'provider':'ngrok'}
        response = read_record(slot/'response.json')
        if read_record(slot/'request.json') != identity or response['request_sha256'] != digest(identity):
            raise ValueError('continuation_writer_prompt_drift')
        attempts = list(slot.glob('attempt_??.json'))
        if not 1 <= len(attempts) <= 2 or response.get('response') is None:
            raise ValueError('continuation_writer_not_completed')
        total_attempts += len(attempts)
        proposals = (response.get('value') or {}).get('hypotheses', [])
        accepted, rejected = admit(request, proposals)
        if (accepted, rejected) != old_admit(request, proposals):
            raise ValueError('continuation_admission_drift')
        plan.extend(p for p in slot.iterdir() if p.is_file())
        cpu = folder/'construction.json'
        if cpu.exists():
            construction = load_checkpoint(cpu)
            if [rec['hypothesis'] for rec in construction['records']] != accepted:
                raise ValueError('continuation_construction_binding')
            if any(not h['site']['scope'] for h in accepted):
                raise ValueError('continuation_checkpoint_incompatible_scopeguard')
            plan.extend([cpu, cpu.with_suffix('.sha256.json')])
            completed.append(cid)
    if completed != ['61','66','124','58','131'] or total_attempts != 6:
        raise ValueError('continuation_unexpected_prefix_or_attempts')
    # No writes until every original checkpoint and writer identity is verified.
    out.mkdir(parents=True)
    imported = {}
    for p in plan:
        rel = p.relative_to(origin)
        dest = out/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
        imported[str(rel)] = sha(dest)
    for cid, case in original_cases.items():
        current = dict(case, sources=source_identity())
        write_new(out/cid/'case_protocol.json', current)
    manifest = {
        'origin':str(origin), 'imported_source_version':'v62_pathfault_contractfix',
        'original_readiness':ready, 'original_case_protocols':original_cases,
        'original_inventory':inventory, 'imported_inventory':imported,
        'completed_construction_cases':completed,
        'compatibility':'Exact writer/admission unchanged; all imported construction hypotheses have nonempty scope. Only empty-scope verifier disposition differs.',
        'imported_physical_dispatches':total_attempts,
        'remaining_new_slots':102, 'total_original_and_continuation_slots':108,
        'cpu_usage':'v62 case85 uncheckpointed executions unknown; v63 case85 recovery segment independently capped at256 executions/120s. No claim of a cumulative256/120s bound.',
        'private_data_used':False,
    }
    write_new(out/'continuation.json', manifest)
    verify_manifest(out)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--requests',type=Path,required=True)
    args = parser.parse_args()
    import_run(args.origin,args.out,args.requests)
    print('verified_six_writer_slots_and_five_construction_checkpoints_imported')


if __name__ == '__main__':
    main()
