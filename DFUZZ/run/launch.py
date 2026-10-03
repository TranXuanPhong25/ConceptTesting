"""Run one program for the oracle: faulthandler on, RNGs seeded, structured record of any Python exception.
usage: python -X faulthandler launch.py <torch|tf> <prog.py> <rec.json>
The program runs via runpy, so its own line numbers are kept in tracebacks and faulthandler dumps."""
import faulthandler, json, os, random, runpy, sys, traceback

faulthandler.enable(all_threads=True)
lib, prog, rec_path = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
random.seed(0)
try:
    import numpy as np
    np.random.seed(0)
except Exception:
    pass
if lib == "torch":
    import torch
    torch.manual_seed(0)
else:
    import tensorflow as tf
    tf.random.set_seed(0)


def where(tb):
    frames = traceback.extract_tb(tb)
    mine = [f for f in frames if f.filename == prog]
    last = frames[-1] if frames else None
    if last is None or last.filename == prog:  # raised by a C extension, or by the program's own raise/assert
        src = (last.line or "").lstrip() if last else ""
        raised_in = "prog" if src.startswith(("raise", "assert")) else "native"
    else:
        f = last.filename
        raised_in = next((f"lib:{p}" for p in ("tensorflow", "keras", "torch", "numpy") if f"/site-packages/{p}/" in f),
                         "other")
    return {"prog_line": mine[-1].lineno if mine else None, "raised_in": raised_in,
            "last": f"{last.filename.split('site-packages/')[-1]}:{last.lineno}" if last else None}


sys.argv = [prog] + sys.argv[4:]
try:
    runpy.run_path(prog, run_name="__main__")
except SystemExit as e:
    json.dump({"kind": "exit", "code": str(e.code)}, open(rec_path, "w"))
    raise
except BaseException as e:
    json.dump({"kind": "exception", "type": f"{type(e).__module__}.{type(e).__qualname__}", "msg": str(e)[:3000],
               **where(e.__traceback__)}, open(rec_path, "w"))
    raise
