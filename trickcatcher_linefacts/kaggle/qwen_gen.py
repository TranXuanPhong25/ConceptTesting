"""Kaggle T4 script: fixed prompt export -> resumable Qwen assertions and throughput."""
import gc, glob, hashlib, importlib.metadata, json, os, subprocess, sys, time
from pathlib import Path

MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
VLLM_VERSION = "0.7.3"  # pins proven on this account: xunphongtrn/qwen2-5-coder-7b-vllm-serve
TRANSFORMERS_VERSION = "4.48.2"
ARMS = ("plain", "concept", "placebo", "coverage", "toolinput")
MAX_MODEL_LEN = 8192
SAMPLING = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 1024}
BASE_SEED = 20261010
WORK = Path("/kaggle/working")


def key(row):
    return row["task"], row["arm"], row["sample"]


def seed(row):
    return BASE_SEED + ((int(row["task"]) * len(ARMS) + ARMS.index(row["arm"])) * 1000 + int(row["sample"]))


def fingerprint(row):
    return hashlib.sha256(json.dumps([row["system"], row["user"]], ensure_ascii=False).encode()).hexdigest()


def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def pip(*args):
    print("pip", *args, flush=True)
    return subprocess.run([sys.executable, "-m", "pip", *args]).returncode


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def save_rows(path, rows, results):
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w") as fh:
        for row in rows:
            if key(row) in results:
                fh.write(json.dumps(results[key(row)]) + "\n")
    tmp.replace(path)


def result(row, text="", n_in=0, n_out=0, error=None):
    out = {k: row[k] for k in ("task", "arm", "sample")}
    out.update(model=MODEL, text=text, n_in=n_in, n_out=n_out,
               seed=seed(row), prompt_sha256=fingerprint(row))
    if error is not None:
        out["error"] = str(error)[:2000]
    return out


def prepare(rows, tokenizer, put):
    jobs = []
    for row in rows:
        ids = []
        try:
            messages = [{"role": "system", "content": row["system"]}, {"role": "user", "content": row["user"]}]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            ids = tokenizer.encode(prompt, add_special_tokens=False)
            if len(ids) + SAMPLING["max_tokens"] > MAX_MODEL_LEN:
                raise ValueError(f"prompt {len(ids)} + output budget exceeds {MAX_MODEL_LEN}; no truncation")
            jobs.append((row, ids))
        except Exception as exc:
            put(result(row, n_in=len(ids), error=exc))
    return jobs


def generate_vllm(engine, jobs, SamplingParams, torch, put):
    if not jobs:
        return 0.0
    params = [SamplingParams(**SAMPLING, seed=seed(row)) for row, _ in jobs]
    torch.cuda.synchronize()
    started = time.perf_counter()
    failure, outputs = None, None
    try:
        outputs = engine.generate([{"prompt_token_ids": ids} for _, ids in jobs], params, use_tqdm=True)
    except Exception as exc:
        failure = f"vllm batch: {exc}"
    torch.cuda.synchronize()
    seconds = time.perf_counter() - started
    if failure is not None:
        for row, ids in jobs:
            put(result(row, n_in=len(ids), error=failure))
        return seconds
    for i, (row, ids) in enumerate(jobs):
        try:
            out = outputs[i]
            answer = out.outputs[0]
            if out.prompt_token_ids != ids:
                raise ValueError("vllm returned mismatched prompt tokens")
            put(result(row, answer.text, len(ids), len(answer.token_ids)))
        except Exception as exc:
            put(result(row, n_in=len(ids), error=exc))
    return seconds


def generate_transformers(model, tokenizer, jobs, torch, put):
    from transformers import GenerationConfig, LogitsProcessor, LogitsProcessorList
    seconds = 0.0

    class RowSampler(LogitsProcessor):
        def __init__(self, rows):
            self.seeds = [seed(row) for row, _ in rows]
            self.generators = None

        def __call__(self, input_ids, scores):
            if self.generators is None:
                self.generators = [torch.Generator(device=scores.device).manual_seed(s) for s in self.seeds]
            values, indices = torch.sort(scores.float() / SAMPLING["temperature"], descending=True)
            probs = torch.softmax(values, dim=-1)
            probs.masked_fill_(probs.cumsum(dim=-1) - probs >= SAMPLING["top_p"], 0)
            picks = torch.stack([torch.multinomial(p, 1, generator=g) for p, g in zip(probs, self.generators)])
            selected = indices.gather(1, picks)
            return torch.full_like(scores, float("-inf")).scatter_(1, selected, 0)

    config = GenerationConfig(max_new_tokens=SAMPLING["max_tokens"], do_sample=False,
                              eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
                              bos_token_id=tokenizer.bos_token_id, use_cache=True)

    def batch(items):
        nonlocal seconds
        if not items:
            return
        failure = None
        inputs, outputs = None, None
        try:
            inputs = tokenizer.pad([{"input_ids": ids, "attention_mask": [1] * len(ids)} for _, ids in items],
                                   padding=True, return_tensors="pt").to(model.device)
            width = inputs["input_ids"].shape[1]
            torch.cuda.synchronize()
            started = time.perf_counter()
            try:
                with torch.inference_mode():
                    outputs = model.generate(**inputs, generation_config=config,
                                             logits_processor=LogitsProcessorList([RowSampler(items)]))
            finally:
                torch.cuda.synchronize()
                seconds += time.perf_counter() - started
            for (row, ids), tokens in zip(items, outputs[:, width:]):
                try:
                    tokens = tokens.tolist()
                    if tokenizer.eos_token_id in tokens:
                        tokens = tokens[:tokens.index(tokenizer.eos_token_id) + 1]
                    put(result(row, tokenizer.decode(tokens, skip_special_tokens=True), len(ids), len(tokens)))
                except Exception as exc:
                    put(result(row, n_in=len(ids), error=exc))
        except Exception as exc:
            failure = f"transformers batch: {exc}"
        del inputs, outputs
        if failure is not None:
            gc.collect()
            torch.cuda.empty_cache()
            if len(items) == 1:
                row, ids = items[0]
                put(result(row, n_in=len(ids), error=failure))
            else:
                mid = len(items) // 2
                print(f"splitting failed fallback batch {len(items)}: {failure[:200]}", flush=True)
                batch(items[:mid])
                batch(items[mid:])

    batch(jobs)
    return seconds


def main():
    started = time.perf_counter()
    WORK.mkdir(parents=True, exist_ok=True)
    out_path = WORK / "gen_qwen7b.jsonl"
    paths = sorted(glob.glob("/kaggle/input/**/prompts.jsonl", recursive=True))
    if len(paths) != 1:
        raise RuntimeError(f"expected exactly one mounted prompts.jsonl, found {paths}; wait for dataset ready")
    rows = [json.loads(line) for line in Path(paths[0]).read_text().splitlines() if line.strip()]
    if len({key(row) for row in rows}) != len(rows):
        raise ValueError("duplicate task/arm/sample in prompt export")
    for row in rows:
        if row["arm"] not in ARMS or not 0 <= row["sample"] < 1000:
            raise ValueError(f"invalid row key {key(row)}")
    expected = {key(row): row for row in rows}
    results = {}
    resume = Path(os.environ.get("QWEN_RESUME", str(out_path)))
    if resume.exists():
        for line in resume.read_text().splitlines():
            try:
                r = json.loads(line)
                old = expected.get(key(r))
                if (old is not None and r.get("model") == MODEL and not r.get("error")
                        and r.get("prompt_sha256") == fingerprint(old) and r.get("seed") == seed(old)):
                    results[key(r)] = r
            except (ValueError, KeyError, TypeError):
                pass
    pending = [row for row in rows if key(row) not in results]
    resumed = len(results)
    current = {}

    def put(r):
        results[key(r)] = current[key(r)] = r
        save_rows(out_path, rows, results)
        if r.get("error"):
            print("ROW ERROR", key(r), r["error"], flush=True)

    save_rows(out_path, rows, results)
    info = {"model": MODEL, "prompt_file": paths[0], "n_rows": len(rows), "n_resumed": resumed,
            "dtype": "float16", "max_model_len": MAX_MODEL_LEN, "sampling": SAMPLING,
            "seed_rule": "20261010 + ((task * 5 + arm_index) * 1000 + sample)",
            "arm_order": ARMS, "model_load_seconds": 0.0, "generation_seconds": 0.0, "gpu_names": []}
    load_start, gen_start, torch = None, None, None
    try:
        if pending:
            os.environ["VLLM_USE_V1"] = "0"
            os.environ["VLLM_ATTENTION_BACKEND"] = "XFORMERS"
            os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            pip("uninstall", "-y", "torchao")
            rc = pip("install", "-q", "--only-binary=vllm", f"vllm=={VLLM_VERSION}",
                     f"transformers=={TRANSFORMERS_VERSION}", "tokenizers>=0.21,<0.22", "accelerate==1.6.0")
            # the install downgrades protobuf to 4.x; Kaggle's preinstalled generated code needs >=5.26 (runtime_version)
            rc = rc or pip("install", "-q", "protobuf>=5.29.5,<6")
            try:
                if rc:
                    raise ImportError(f"vllm install exit {rc}")
                from vllm import LLM, SamplingParams
                info["backend"] = "vllm"
            except Exception as exc:
                info.update(backend="transformers", fallback_reason=str(exc))
                print("TRANSFORMERS FALLBACK", str(exc), flush=True)
                if pip("install", "-q", f"transformers=={TRANSFORMERS_VERSION}", "accelerate==1.6.0"):
                    raise RuntimeError("fallback dependency installation failed")
            import torch
            from huggingface_hub import snapshot_download
            from transformers import AutoModelForCausalLM, AutoTokenizer

            ngpu = torch.cuda.device_count()
            info.update(gpu_names=[torch.cuda.get_device_name(i) for i in range(ngpu)],
                        tensor_parallel_size=ngpu if info["backend"] == "vllm" else None,
                        cuda_version=torch.version.cuda)
            if not ngpu:
                raise RuntimeError("no visible GPU; select NvidiaTeslaT4 in kernel metadata")
            load_start = time.perf_counter()
            local_model = snapshot_download(MODEL, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
            tokenizer = AutoTokenizer.from_pretrained(local_model, padding_side="left")
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token = tokenizer.eos_token
            if info["backend"] == "vllm":
                model = LLM(model=local_model, tokenizer=local_model, dtype="float16", tensor_parallel_size=ngpu,
                            max_model_len=MAX_MODEL_LEN, seed=BASE_SEED, gpu_memory_utilization=0.90,
                            max_num_seqs=16, enforce_eager=True, disable_custom_all_reduce=True,
                            generation_config="vllm")
            else:
                model = AutoModelForCausalLM.from_pretrained(local_model, torch_dtype=torch.float16,
                            device_map="auto", max_memory={i: "12GiB" for i in range(ngpu)},
                            attn_implementation="sdpa").eval()
            info["model_load_seconds"] = time.perf_counter() - load_start
            jobs = prepare(pending, tokenizer, put)
            gen_start = time.perf_counter()
            if info["backend"] == "vllm":
                info["generation_seconds"] = generate_vllm(model, jobs, SamplingParams, torch, put)
            else:
                info["generation_seconds"] = generate_transformers(model, tokenizer, jobs, torch, put)
    except Exception as exc:
        info["error"] = str(exc)[:2000]
        if load_start is not None and gen_start is None:
            info["model_load_seconds"] = time.perf_counter() - load_start
        if gen_start is not None:
            info["generation_seconds"] = time.perf_counter() - gen_start
        for row in pending:
            if key(row) not in current:
                put(result(row, error=exc))
    successful = [r for r in current.values() if not r.get("error")]
    n_in, n_out = sum(r["n_in"] for r in successful), sum(r["n_out"] for r in successful)
    seconds = info["generation_seconds"]
    info.update(vllm_version=version("vllm"), torch_version=version("torch"),
                transformers_version=version("transformers"), wall_seconds=time.perf_counter() - started,
                n_generated=len(successful), n_errors=sum(bool(r.get("error")) for r in results.values()),
                total_prompt_tokens=n_in, total_generated_tokens=n_out,
                output_tokens_per_second=n_out / seconds if seconds else 0.0,
                total_tokens_per_second=(n_in + n_out) / seconds if seconds else 0.0,
                throughput_scope="this invocation; successful new rows; excludes resumed rows; timed generate calls including retries")
    save_rows(out_path, rows, results)
    atomic_json(WORK / "run_info.json", info)
    print("THROUGHPUT", json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
