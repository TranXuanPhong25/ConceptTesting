"""Pinned local ONNX embeddings; no remote inference, silent fallback, or target execution."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = "jinaai/jina-embeddings-v2-base-code"
REVISION = "516f4baf13dec4ddddda8631e019b5737c8bc250"
MODEL_CACHE = Path.home() / ".cache" / "concepttester-v7"
MANIFEST = HERE / "MODEL_MANIFEST.json"


def cache_key(identity, text):
    return hashlib.sha256((identity + "\0" + text).encode()).hexdigest()


def cached_vector(dim, blob):
    vector = np.frombuffer(blob, dtype=np.float32).copy()
    if (len(vector) != dim or len(vector) != 768 or not np.isfinite(vector).all()
            or not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-5)):
        raise ValueError("Invalid cached vector")
    return vector


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare():
    """Download one explicit immutable revision; inspect/hash without loading model code."""
    from huggingface_hub import snapshot_download
    from importlib.metadata import version
    folder = Path(snapshot_download(
        MODEL, revision=REVISION, cache_dir=MODEL_CACHE / "hub",
        allow_patterns=["onnx/model.onnx", "config.json", "tokenizer.json", "tokenizer_config.json",
                        "special_tokens_map.json", "vocab.json", "vocab.txt", "merges.txt",
                        "1_Pooling/config.json", "sentence_bert_config.json", "README.md", "LICENSE*"],
    ))
    files = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}
    if "onnx/model.onnx" not in files or "tokenizer.json" not in files:
        raise ValueError("Incomplete pinned model")
    result = {"model": MODEL, "revision": REVISION, "files": files,
              "fastembed": version("fastembed"), "onnxruntime": version("onnxruntime"),
              "tokenizers": version("tokenizers"), "numpy": version("numpy"),
              "pooling": "mean", "normalization": "L2", "prefixes": {"query": "", "document": ""},
              "runtime_max_tokens": 512, "model_path": str(folder), "provider": "CPUExecutionProvider"}
    result.update(threads=2, batch_size=8, truncation_direction="right")
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text())
        if old != result:
            raise ValueError("Existing model manifest differs; use a versioned amendment, never overwrite")
    else:
        MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    return result


class Encoder:
    def __init__(self, manifest=MANIFEST, cache=None):
        from fastembed import TextEmbedding
        from importlib.metadata import version
        self.manifest = json.loads(Path(manifest).read_text())
        m = self.manifest
        if m["model"] != MODEL or m["revision"] != REVISION or any(
            version(package) != m[package] for package in ("fastembed", "onnxruntime", "tokenizers", "numpy")
        ):
            raise ValueError("Embedding identity/version mismatch")
        for name, digest in m["files"].items():
            if sha(Path(m["model_path"]) / name) != digest:
                raise ValueError("Model artifact changed: " + name)
        self.identity = hashlib.sha256(json.dumps({k: v for k, v in m.items() if k != "model_path"}, sort_keys=True).encode()).hexdigest()
        self.model = TextEmbedding(model_name=MODEL, specific_model_path=m["model_path"],
                                   local_files_only=True, threads=m["threads"], providers=[m["provider"]])
        # FastEmbed0.9.1 constructor max_length is not a tokenizer override.
        tokenizer = self.model.model.tokenizer
        self.raw_tokenizer = type(tokenizer).from_str(tokenizer.to_str())
        self.raw_tokenizer.no_truncation()
        self.raw_tokenizer.no_padding()
        tokenizer.enable_truncation(max_length=m["runtime_max_tokens"], direction=m["truncation_direction"])
        if tokenizer.truncation["max_length"] != m["runtime_max_tokens"]:
            raise ValueError("Runtime token cap mismatch")
        self.cache = Path(cache) if cache else MODEL_CACHE / "embeddings.sqlite3"
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.cache) as c:
            c.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, dim INTEGER, value BLOB)")
        self.calls = self.hits = self.truncated = 0

    def encode(self, texts):
        if not texts:
            return np.empty((0, 768), dtype=np.float32)
        self.truncated += sum(len(t.ids) > self.manifest["runtime_max_tokens"]
                              for t in self.raw_tokenizer.encode_batch(texts))
        keys = [cache_key(self.identity, t) for t in texts]
        found, missing = {}, {}
        with sqlite3.connect(self.cache) as c:
            for key, text in zip(keys, texts):
                row = c.execute("SELECT dim,value FROM vectors WHERE key=?", (key,)).fetchone()
                if row:
                    vector = cached_vector(row[0], row[1])
                    found[key] = vector
                    self.hits += 1
                else:
                    missing[key] = text
            if missing:
                values = list(missing.values())
                vectors = list(self.model.embed(values, batch_size=self.manifest["batch_size"]))
                if len(vectors) != len(missing):
                    raise ValueError("Missing embedding outputs")
                for key, vector in zip(missing, vectors):
                    vector = np.asarray(vector, dtype=np.float32)
                    if vector.shape != (768,) or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
                        raise ValueError("Invalid embedding")
                    vector = vector / np.linalg.norm(vector)
                    found[key] = vector
                    c.execute("INSERT INTO vectors VALUES (?,?,?)", (key, len(vector), vector.tobytes()))
                self.calls += len(missing)
        return np.stack([found[k] for k in keys])


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
