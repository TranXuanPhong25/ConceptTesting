"""B2 references before generation: unchanged oracle_b01 DPP requests and seeds."""
from concurrent.futures import ThreadPoolExecutor
import json
from . import oracle_b01 as ob, preconditions
from .offline_client import request
from .v4_runtime import immutable


def jobs(tasks):
    dsys, dusr = ob.dpp_templates()
    for t in tasks:
        spec = preconditions.specification(t)[0]
        for s in range(ob.NREF):
            yield dict(stage='ref', task=str(t['task']), sample=s,
                       seed=ob.SEED + 500000 + t['task'] * 100 + s,
                       temperature=0.8, max_tokens=1024,
                       messages=ob.msgs(dusr.replace('{signature_and_doctoring}', spec), system=dsys))


def stage(layout, client, workers=12):
    from .run import task_sources
    tasks, _, _ = task_sources(layout)
    pending = list(jobs(tasks))
    dest = layout.refs / 'ref_responses.json'
    existing = json.loads(dest.read_text()) if dest.exists() else None

    def one(j):
        response = client.chat(j['messages'], j['seed'], temperature=j['temperature'],
                               top_p=0.95, max_tokens=j['max_tokens'])
        return dict({k: v for k, v in j.items() if k != 'messages'}, text=response['text'])

    with ThreadPoolExecutor(workers) as pool:
        responses = list(pool.map(one, pending))
    if existing is not None:
        # Historical response order may differ; only task/sample identify a B2 request.
        old = {(r['task'], r['sample']): r for r in existing}
        if any(old.get((r['task'], r['sample'])) != r for r in responses):
            raise ValueError('B2 replay differs from the saved reference responses')
    immutable(layout.refs / 'requests.json', [dict(task=j['task'], sample=j['sample'],
              key=request(j['messages'], j['seed'], client.model, j['temperature'], 0.95, j['max_tokens'])[0])
              for j in pending])
    if existing is None:
        immutable(dest, responses)
    print(f'refs: {len(responses)} unchanged B2 requests replayed/requested', flush=True)
