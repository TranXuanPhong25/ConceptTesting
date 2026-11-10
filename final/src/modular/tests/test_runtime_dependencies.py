"""Current entry points must work without importing historical research packages."""
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_current_modules_import_with_historical_packages_blocked():
    script = '''
import importlib
import importlib.abc
import pathlib
import sys
class RejectHistoricalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ("final.experiments", "final.v11_clean_runtimefix", "trickcatcher_linefacts", "final.pipeline", "final.run", "final.src.pipeline", "final.src.run", "final.src.contracts", "final.src.prompts", "final.src.execution", "final.src.worker")
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise ImportError("Historical dependency: " + fullname)
sys.meta_path.insert(0, RejectHistoricalImports())
importlib.import_module("final.src.development_groups")
for directory in (pathlib.Path("final/src/modular"), pathlib.Path("final/src/runtime")):
    for path in sorted(directory.rglob("*.py")):
        if "tests" in path.parts or path.name in ("__init__.py", "worker.py"):
            continue
        importlib.import_module(".".join(path.with_suffix("").parts))
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_cli_only_lists_supported_methods():
    result = subprocess.run([sys.executable, "-m", "final.src.modular.run", "--help"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "{plain,boundary,equivalence,bva_normal,ep_bva,decision_table," in result.stdout
    for removed in ("--legacy-generation", "--v11", "classical", "witness_only"):
        assert removed not in result.stdout
