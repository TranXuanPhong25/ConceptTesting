"""Frozen six-case CPU construction diagnostic (PREREG_V66): source catalog only, no model, no private oracle."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
import time

import crosshair
import z3

from . import hypotheses
from .crosshair_construct import construct, sandbox_preflight
from .deep_run import validate_request

HERE = Path(__file__).resolve().parent


def manifest(request, config):
    return dict(request_sha256=hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(), config=config,
                source_files_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))},
                sandbox_preflight=sandbox_preflight(), crosshair=crosshair.__version__, z3=z3.get_full_version(), python=sys.version)


def run_case(request, config):
    _, seeds = validate_request(request)
    rows, issues = hypotheses.catalog(request['source'], request['entry'], config['max_hypotheses'])
    started, reports = time.monotonic(), []
    for h in rows:  # every catalogued hypothesis stays in the denominator
        try:
            reports.append(construct(request['source'], request['entry'], seeds, h, config))
        except Exception as exc:  # harness failure stays in the denominator
            reports.append(dict(hypothesis=h, status='harness_error', inputs=[], issues=[type(exc).__name__ + ':' + str(exc)[:160]]))
    counts = collections.Counter(r['status'] for r in reports)
    verified = [r['hypothesis'] for r in reports if r['inputs']]
    by_family = dict(collections.Counter(h['family'] for h in verified))
    by_site = dict(collections.Counter(h['node_kind'] for h in verified))
    return dict(case_id=request['case_id'], catalog_issues=issues, hypotheses=len(rows), status_counts=dict(counts),
                verified_hypotheses=len(verified), verified_by_family=by_family, verified_by_site_kind=by_site,
                verified_inputs=sorted({x['arguments'] for r in reports for x in r['inputs']}),
                elapsed_seconds=round(time.monotonic() - started, 2), reports=reports)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    request = next(r for r in json.loads(args.requests.read_text()) if r['case_id'] == args.case)
    config = json.loads((HERE / 'config.json').read_text())['symbolicpath']
    if not sandbox_preflight():
        raise SystemExit('sandbox preflight failed (unshare -rn); every replay would be worker_error')
    target = args.out / f'case_{args.case}.json'
    args.out.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit('existing case artifact; choose a fresh output directory')
    result = dict(manifest=manifest(request, config), result=run_case(request, config))
    with target.open('x') as stream:
        json.dump(result, stream, indent=1, ensure_ascii=True)
    r = result['result']
    print(json.dumps(dict(case=r['case_id'], hypotheses=r['hypotheses'], verified=r['verified_hypotheses'], statuses=r['status_counts'])))


if __name__ == '__main__':
    main()
