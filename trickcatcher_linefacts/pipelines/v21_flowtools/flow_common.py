"""Shared JSON/immutability helpers for the flowtools online run (same rules as v23 diagnostic_core)."""
import hashlib
import json
import os
import threading
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def immutable(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('immutable_record_changed:' + path.name)
    else:
        tmp = path.with_name(f'{path.name}.{os.getpid()}.{threading.get_ident()}.tmp')
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        tmp.replace(path)
    return value


def strict_json(text, max_bytes=65536):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_JSON_key')
            result[key] = value
        return result
    if type(text) is not str or len(text.encode()) > max_bytes:
        raise ValueError('response_size')
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_JSON')))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid_JSON') from exc
