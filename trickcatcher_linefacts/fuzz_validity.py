"""Pluggable fuzz validity; contract code executes only in an isolated worker."""
import ast, contextlib, io, json, os, select, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts.gen_inputs import CONTRACTS


class EvalPlus:
    mode = "evalplus"
    def __init__(self, task, path):
        self.task = task
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
        self.process = subprocess.Popen(["unshare", "-rn", sys.executable, "-I", "-B", __file__,
                                         self.mode, str(task), str(path)], env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if self.read() is not True:
            self.close()
            raise RuntimeError("contract worker did not initialize")

    def read(self):
        if not select.select([self.process.stdout], [], [], 10)[0]:
            self.close()
            raise RuntimeError("contract worker timeout")
        line = self.process.stdout.readline()
        if not line:
            self.close()
            raise RuntimeError("contract worker failed")
        return json.loads(line)

    def __call__(self, task, args):
        if task != self.task:
            raise ValueError("contract task mismatch")
        self.process.stdin.write(json.dumps(repr(args)) + "\n")
        self.process.stdin.flush()
        return self.read()

    def close(self):
        if self.process.stdin.closed:
            return
        self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()


class Mined(EvalPlus):
    mode = "mined"


MINED_ROOT = HERE / "out/precond_qwen7b"
VALIDATORS = {"evalplus": EvalPlus, "mined": Mined}


@contextlib.contextmanager
def validator(name="evalplus", task=None, path=None):
    if name == "none":
        yield None
        return
    check = VALIDATORS[name](task, path or (MINED_ROOT if name == "mined" else CONTRACTS))
    try:
        yield check
    finally:
        check.close()


def worker(task, path, mode="evalplus"):
    from trickcatcher_linefacts.gen_inputs import load_contracts
    from trickcatcher_linefacts.tracer import alarm, dcopy, load_module
    with alarm(5):
        if mode == "mined":
            from trickcatcher_linefacts.preconditions import load_predicate
            checker = load_predicate((Path(path) / str(task) / "valid.py").read_text(), "valid")
        else:
            row = load_contracts(path)[task]
            checker = load_module(row["contract_src"], filename="<contract>")[row["entry"]]
    print(json.dumps(True), flush=True)
    for line in sys.stdin:
        args, kwargs = ast.literal_eval(json.loads(line))
        accepted = True
        try:
            with contextlib.redirect_stdout(io.StringIO()), alarm(1):
                result = checker(*dcopy(args), **dcopy(kwargs))
                if mode == "mined":
                    accepted = result is True
        except BaseException:
            accepted = False
        print(json.dumps(accepted), flush=True)


if __name__ == "__main__":
    worker(int(sys.argv[2]), sys.argv[3], sys.argv[1])
