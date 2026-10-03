"""Gap kind 1 premise check on TF 2.15: does an op's shape function run in eager mode?
Each op gets an input that violates a rank constraint stated in its shape function (ops/*.cc), and is called eagerly and
inside tf.function, each in a fresh process via the oracle. Shape-inference errors carry 'Shape must be ...' and
'with input shapes:'; kernel errors do not. Writes run/out/eager_probe.jsonl.
usage (container): /opt/pilot/bin/python run/eager_probe.py"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oracle import classify, run_once, target_lines

# op: (shape-fn constraint, call with a violating input)
CASES = {
    "DrawBoundingBoxes": ("images WithRank 4", "tf.raw_ops.DrawBoundingBoxes(images=tf.zeros([8, 8, 3]), boxes=tf.zeros([1, 2, 4]))"),
    "MatMul": ("a WithRank 2", "tf.raw_ops.MatMul(a=tf.ones([2, 2, 2]), b=tf.ones([2, 2]))"),
    "Unique": ("x WithRank 1", "tf.raw_ops.Unique(x=tf.constant([[1, 2], [2, 3]]))"),
    "ResizeBilinear": ("images WithRank 4", "tf.raw_ops.ResizeBilinear(images=tf.ones([8, 8, 3]), size=tf.constant([4, 4]))"),
    "Conv2D": ("filter WithRank 4", "tf.raw_ops.Conv2D(input=tf.ones([1, 8, 8, 3]), filter=tf.ones([3, 3, 3]), "
                                    "strides=[1, 1, 1, 1], padding='VALID')"),
}
SHAPE_FN = re.compile(r"Shape must be|with input shapes:")

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/eager_probe.jsonl"), "w")
for op, (constraint, call) in CASES.items():
    for mode in ("eager", "tf.function"):
        code = ("import tensorflow as tf\n" + (f"out = {call}\n" if mode == "eager" else
                f"@tf.function\ndef f():\n    return {call}\nout = f()\n") + "print('RESULT', getattr(out, 'shape', out))\n")
        c = classify(run_once("tf", code), target_lines(code, "tf.raw_ops." + op))
        msg = c["msg"] or c["fatal"] or ""
        fired = ("shape_fn" if SHAPE_FN.search(msg) else "kernel_check" if c["cls"] == "exception" else
                 "crash" if c["cls"] not in ("clean", "exception") else "none(clean)")
        rec = {"op": op, "constraint": constraint, "mode": mode, "cls": c["cls"], "exc": c["exc"],
               "shape_fn_check_fired": fired == "shape_fn", "outcome": fired, "msg": msg[:300]}
        out.write(json.dumps(rec) + "\n")
        print(f"{op:18} {mode:12} -> {fired:12} {c['cls']:14} {msg[:130]!r}", flush=True)
