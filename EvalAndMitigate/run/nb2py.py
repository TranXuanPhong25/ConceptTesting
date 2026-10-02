"""Extract selected notebook code cells into a script, applying path/client substitutions.
usage: nb2py.py NB OUT KEEP [OVERRIDES.py]   KEEP like "0-10,15,20-26"; OVERRIDES is appended after cell 'SET_AFTER' marker lines."""
import json, re, sys

nb, out, keep = sys.argv[1:4]
cells = [c for c in json.load(open(nb))["cells"] if c["cell_type"] == "code"]
idx = set()
for part in keep.split(","):
    a, _, b = part.partition("-")
    idx.update(range(int(a), int(b or a) + 1))
overrides = {}  # cell index -> code appended after that cell
if len(sys.argv) > 4:
    for block in open(sys.argv[4]).read().split("# @after ")[1:]:
        n, _, code = block.partition("\n")
        overrides[int(n)] = code
SUBS = [
    (r"/home/drixs2050/Documents/LLM4UT", "/repo"),
    (r"/path/to/repo", "/repo"),
    (r"/path/to/defects4j", "/defects4j"),
    (r"from openai import OpenAI", "from gemini_shim import GeminiChat"),
    (r"OpenAI\(\s*api_key=os\.environ\.get\(\"OPENAI_API_KEY\"\)\s*\)", "GeminiChat()"),
]
src = ["import sys; sys.path[:0] = ['/repo', '/repo/run']"]
for i, c in enumerate(cells):
    if i not in idx:
        continue
    s = "".join(c["source"])
    s = "\n".join(l for l in s.splitlines() if not l.lstrip().startswith(("%", "!")))
    for a, b in SUBS:
        s = re.sub(a, b, s)
    src.append(f"# ---- cell {i}\n{s}")
    if i in overrides:
        src.append(f"# ---- override after cell {i}\n{overrides[i]}")
open(out, "w").write("\n\n".join(src) + "\n")
