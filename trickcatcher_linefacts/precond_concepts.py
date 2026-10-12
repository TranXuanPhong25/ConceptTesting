"""F4: concept-guided precondition mining (PREREG "Input-validity filters", F4 addendum).

Same observation -> confirmation -> code -> verifier pipeline and settings as B5 (out/precond_qwen7b_v4: evidence
filter off), with one change: the observation prompt walks a generic taxonomy of input-constraint categories
(structural / boundary / relational / format / definedness / arithmetic, with quantifier scope) instead of asking
open-endedly. The taxonomy was derived from even-numbered dev tasks + pilot (scratch constraint_concepts/); the prompt
carries category definitions only, no task examples.

  V4=... ; $V4 -B trickcatcher_linefacts/precond_concepts.py --workers 12       # needs QWEN_BASE_URL
"""
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import precond_prompts, preconditions, run_v4
from trickcatcher_linefacts.llm_client import Client, atomic_json

ROOT = HERE / "out/precond_qwen7b_f4"
OBSERVATION_F4 = """Go through the input-constraint categories below one by one, for every parameter. For containers and strings, also ask each category for every element, for some element, for each nesting level, and for numbers written inside strings. Write a condition only when the signature or docstring states it or its words necessarily imply it; otherwise skip the category. Use one atomic condition per item: never combine two conditions (write "n is an int" and "n >= 0" as two items).
S1 type of the parameter (annotation or wording: int, float, str, list, ...).
S2 type of the elements of a container.
S3 shape or nesting (nested lists, rows of equal length, pairs).
S4 exact, minimum or maximum length or number of elements.
B1 sign or zero: positive, non-negative, non-zero (lengths, counts, sizes and natural numbers cannot be negative).
B2 lower or upper bounds stated or implied by the meaning of the words (for example a numeric base is at least 2).
B3 non-empty (operations such as max, mean or "the largest" need at least one element).
R1 internal order (start <= end, sorted).
R2 uniqueness (no duplicates).
R3 relations between parameters (equal lengths, an index or count within a sequence's length).
F1 allowed characters or letter case; if the input is produced by another described function or encoding, it lies in that function's output range.
F2 allowed vocabulary of tokens or elements (an enumerated legend or list of valid choices).
F3 layout or grammar of strings (separators, number of fields, single spaces, fractions written a/b, date formats).
D definedness: values that make the described operation undefined (division by zero, infinity or NaN, unparsable numbers).
A arithmetic class: prime or composite, even or odd, divisibility.
Reply only with a JSON list: [{"id":"P1","category":"B1","condition":"..."}]. Use unique ids P1, P2, and so on."""

# F4b: F4 plus three rules, derived only from F4's wrongly-flagged valid inputs on even-numbered dev tasks and pilot
# (tests/filters/outcomes turned into requirements; element types guessed from examples; categories filled by default).
OBSERVATION_F4B = OBSERVATION_F4.replace("Reply only with a JSON list", """Rules:
- A condition that the function tests, filters by, counts, sorts out or returns True/False for is NOT an input requirement: the function must accept inputs on both sides of it (for example "return True if the last character is a letter" allows any last character; "sort the integers between 1 and 9" allows other integers).
- Write only what the caller must guarantee: type annotations, and wording such as "given a positive ...", "assume", "will be", "guaranteed", "non-empty", "consists only of". Do not narrow a type or element type from examples alone.
- Most categories do not apply to a given function; skipping them is the normal answer, and an empty list is allowed.
Reply only with a JSON list""")
VARIANTS = {"f4": (OBSERVATION_F4, HERE / "out/precond_qwen7b_f4"), "f4b": (OBSERVATION_F4B, HERE / "out/precond_qwen7b_f4b")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--python", type=Path, default=os.environ.get("V4_PYTHON", sys.executable))
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="f4")
    a = ap.parse_args()
    observation, a.root = VARIANTS[a.variant]
    ids = [int(n) for n in (HERE / "tasks.txt").read_text().split() if int(n) not in run_v4.run_gen.DESIGN]
    tasks, _, _ = run_v4.task_sources(ids)
    precond_prompts.OBSERVATION = observation             # the only change versus B5; set before any thread starts
    a.root.mkdir(parents=True, exist_ok=True)
    atomic_json(a.root / "variant.json", dict(variant=a.variant.upper(), observation=observation, evidence_filter=False))
    client = Client(a.root / "cache", workers=a.workers)
    with ThreadPoolExecutor(a.workers) as pool:
        res = list(pool.map(lambda t: preconditions.mine(t, client, a.root, evidence_filter=False, python=str(a.python)), tasks))
    print(f"{a.variant} mined {len(res)} tasks; failures {sum(bool(r.get('mining_failure')) for r in res)}; "
          f"surviving conditions {sum(r['surviving'] for r in res)}")


if __name__ == "__main__":
    main()
