"""Post-pilot generator arms; existing prompt/export constants stay unchanged."""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import ast
import hashlib
from pathlib import Path

from . import prompts

DEFAULT_ARMS = ("plain", "concept", "toolinput", "gen-plain", "gen-concept", "gen-placebo")
ARMS = DEFAULT_ARMS + ("concept-toolinput",)
INPUT_ARMS = ("toolinput", "gen-plain", "gen-concept", "gen-placebo", "concept-toolinput")
ARTIFACT_COMMIT = "a0d285a77efff7c93fc280d606497d9de5e1defe"
TEMPLATE_SHA256 = {
    "geninput_generator_sys": "4c9164d6fabaebe04301471c690cfa927eef4b2e39d80561b6125da06c35017d",
    "geninput_usr": "ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317",
}
CONSTRUCTION = ("Write `sample_one()` so that the inputs it returns exercise these facts (each call may "
                "target one fact). Compute such inputs in code (e.g. construct them) rather than guessing "
                "values; every input must still satisfy the specification.")


def read_original_templates(template_dir=None):
    directory = Path(template_dir) if template_dir else Path(__file__).parent / "tc_templates"
    result = []
    for name, expected in TEMPLATE_SHA256.items():
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Official TrickCatcher template {name} failed SHA256 verification")
        result.append(raw.decode("utf-8"))
    return tuple(result)


def messages(system, user):
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generator_messages(arm, task):
    if arm not in DEFAULT_ARMS[3:]:
        raise ValueError(arm)
    system, template = read_original_templates()
    user = template.format(function_and_docstring=task["put"])
    facts = task["placebo_facts"] if arm == "gen-placebo" else task["concept_facts"]
    if arm != "gen-plain" and facts:
        user += prompts.FACTS_HEAD + "".join(f"- {f}\n" for f in facts) + CONSTRUCTION
    return messages(system, user)


def oracle_messages(task, selected):
    return messages(*prompts.build("toolinput", dict(task, tool_inputs=[r["call"] for r in selected])))


def concept_toolinput_messages(task, selected):
    kept = {r["input_repr"]: r["call"] for r in selected}
    witnesses = []
    for fact in task["concept_meta"]:
        call = fact.get("witness_call")
        args = [ast.literal_eval(n) for n in ast.parse(call, mode="eval").body.args] if call else None
        witnesses.append(kept.get(repr(args)))
    if len(witnesses) != len(task["concept_facts"]):
        raise ValueError("concept facts/metadata mismatch")
    return messages(*prompts.build("concept-toolinput", dict(task, fact_witnesses=witnesses)))


def seed(task, arm, sample, stage=0, retry=0):
    if not 0 <= sample < 1000 or stage not in range(4) or retry not in (0, 1):
        raise ValueError("seed indices out of range")
    # Freeze the six-arm stride; give the added arm a disjoint seed range.
    index = int(task) * len(DEFAULT_ARMS) + ARMS.index(arm)
    if arm == "concept-toolinput":
        index = 125000 + int(task)
    return 20261010 + ((index * 1000 + sample) * 8 + stage * 2 + retry)


def strict_oracle_messages(task, selected):
    system = prompts.SYSTEM
    user = prompts.HEAD.format(put=task["put"].rstrip(), base=task["base"].strip())
    user += "\n\nFor EXACTLY the calls below, write one `assert <call> == <expected>` per call, in the listed order. Compute the expected values from the specification. Do not add, replace, or omit inputs. Reply with a single Python code block.\n"
    user += "\n".join(r['call'] for r in selected)
    return messages(system, user)
