"""subset150 sampling plan (host, stdlib, no checkout, no LLM).

Per new project: every bug of data/d4j2_fix_info in a fixed-seed random order. Removed up front (both are certain to
yield no method in the upstream pipeline, so dropping them only saves checkouts):
  - the evaluation notebook's deprecated_bugs (UT_Compile_and_Test_Project.ipynb code cell 7, exec'd, not copied);
  - bugs whose fix_info lists no changed function (generate_source_data_for_prompt.ipynb cell 77 makes no record).
sample.py walks each order and stops a project once QUOTA methods pass the upstream filters.
usage: python3 subset150/plan.py   -> subset150/out/plan.json
"""
import json, os, random

SEED = 150
QUOTA = 12  # methods per new project; a bug's methods are kept together, so a project can end a few above
PROJECTS = ["Time", "Jsoup", "Compress", "Math", "JacksonDatabind", "Closure"]  # checkout order (small repos first)
# Closure was stopped by the coordinator after 147 of its 172 candidates (5 methods; disk). No extra project was added.
EXTRA_QUOTA = {}
FIX = "data/d4j2_fix_info"


def deprecated():
    cells = [c for c in json.load(open("UT_Compile_and_Test_Project.ipynb"))["cells"] if c["cell_type"] == "code"]
    ns = {}
    exec("".join(cells[7]["source"]), ns)
    return ns["deprecated_bugs"]


def plan():
    dep = deprecated()
    out = {"seed": SEED, "quota": QUOTA, "deprecated": dep, "projects": {}}
    for p in PROJECTS + list(EXTRA_QUOTA):
        bugs = sorted((b for b in os.listdir(FIX) if b.rsplit("_", 1)[0] == p), key=lambda b: int(b.rsplit("_", 1)[1]))
        drop_dep = [b for b in bugs if any(f"{b}_".startswith(d) for d in dep)]
        no_fn = [b for b in bugs if not any(q for fc in json.load(open(f"{FIX}/{b}/buggy_fix_info.json"))["fixing_changes"]
                                            for cf in fc["changed_functions"] for q in cf["qualified_names"])]
        cand = [b for b in bugs if b not in drop_dep and b not in no_fn]
        out["projects"][p] = {"bugs": len(bugs), "deprecated": drop_dep, "no_changed_function": no_fn,
                              "order": random.Random(SEED).sample(cand, len(cand)),
                              "quota": EXTRA_QUOTA.get(p, QUOTA)}
    return out


if __name__ == "__main__":
    pl = plan()
    assert pl == plan() and pl["projects"]["JacksonDatabind"]["deprecated"] == ["JacksonDatabind_65", "JacksonDatabind_89"]  # deterministic; deprecated list applied
    assert all(not set(v["order"]) & set(v["deprecated"] + v["no_changed_function"]) for v in pl["projects"].values())
    os.makedirs("subset150/out", exist_ok=True)
    json.dump(pl, open("subset150/out/plan.json", "w"), indent=1)
    for p, v in pl["projects"].items():
        print(p, v["bugs"], "bugs;", len(v["order"]), "candidates; first 10:", v["order"][:10])
