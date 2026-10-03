#!/usr/bin/env bash
# Count mutation-phase prompts (= LLM calls in runPrompts.py) per API by running the authors'
# gen_prompts_for_mutators.py on their shipped results, in a scratch copy. No LLM calls.
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm -v "$D":/dfuzz:ro -v "$D/run":/out dfuzz:arm64 bash -c '
for lib in torch tensorflow; do
  short=$([ $lib = torch ] && echo torch || echo tf)
  rm -rf /work && cp -r /dfuzz /work && cd /work
  cp edge_case_extraction/results/* edge_case_extraction/
  cp get_api_reference/results/$lib/* get_api_reference/
  cp gen_program/results/$short/api_programs.json gen_program/
  cd gen_program && /opt/py38/bin/python gen_prompts_for_mutators.py > /dev/null
  /opt/py38/bin/python - $short <<PY
import pickle, collections, json, sys, statistics as st
idx = pickle.load(open("outputs/torch/INDEX.pkl", "rb"))
per = collections.Counter(k.rsplit("-", 1)[0] for k in idx)
progs = json.load(open("api_programs.json"))
c = sorted(per.values())
q = lambda p: c[int(p * (len(c) - 1))]
res = {"library": sys.argv[1], "apis_with_prompts": len(per), "apis_with_seed": sum(v != "none" for v in progs.values()),
       "total_prompts": sum(c), "mean": round(st.mean(c), 1), "median": st.median(c), "p90": q(0.9), "max": c[-1],
       "top5": per.most_common(5)}
print(json.dumps(res))
open("/out/prompt_counts.jsonl", "a").write(json.dumps(res) + "\n")
PY
done'
