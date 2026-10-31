"""Read-only replay of the original request hash. Never reads credentials or networks."""
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .paths import CONFIG


class CacheMiss(RuntimeError):
    pass


def request(messages, seed, model=None, temperature=0.7, top_p=0.95, max_tokens=1024):
    params = dict(model=model or CONFIG['model'], temperature=temperature, top_p=top_p,
                  max_tokens=max_tokens, seed=seed)
    encoded = json.dumps(dict(params, messages=messages), sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest(), params


class OfflineClient:
    def __init__(self, cache_dir, *, model=None, workers=16, **kwargs):
        self.cache_dir = Path(cache_dir)
        self.model = model or CONFIG['model']
        self.workers = workers
        self.hits = []
        self.misses = []

    def chat(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        key, params = request(messages, seed, self.model, temperature, top_p, max_tokens)
        path = self.cache_dir / (key + '.json')
        if not path.is_file():
            self.misses.append(key)
            raise CacheMiss(f'offline cache miss: {key}')
        record = json.loads(path.read_text())
        if record['key'] != key or record['params'] != params:
            raise ValueError(f'corrupt cache record: {key}')
        self.hits.append(key)
        return dict(record, cache_hit=True)

    def chat_many(self, jobs):
        with ThreadPoolExecutor(self.workers) as pool:
            return list(pool.map(lambda job: self.chat(*job), jobs))
