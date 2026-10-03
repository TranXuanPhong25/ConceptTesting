"""TF raw_ops Python arg names that differ from op input names (api_def renames, e.g. reduction_indices -> axis).
usage (container): /opt/tf215/bin/python run/tf_renames.py  -> run/out/tf_arg_renames.json"""
import inspect, json, os
import tensorflow as tf
from tensorflow.python.framework import op_def_registry

out = {}
for op in dir(tf.raw_ops):
    od = None if op.startswith("_") else op_def_registry.get(op)
    if od is None:
        continue
    try:
        params = list(inspect.signature(getattr(tf.raw_ops, op)).parameters)
    except (TypeError, ValueError):
        continue
    ren = {a.name: p for a, p in zip(od.input_arg, params) if a.name != p and a.name not in params}
    if ren:
        out[op] = ren
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/tf_arg_renames.json"), "w"), indent=0)
print(len(out), "ops with renamed inputs")
