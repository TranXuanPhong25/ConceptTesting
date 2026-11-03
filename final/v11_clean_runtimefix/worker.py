"""Bridge into unmodified V11 kernels, executed only inside bubblewrap."""

import contextlib
import io
import json
import os
import resource
import sys
from pathlib import Path


def main():
    job_path, output_path = map(Path, sys.argv[1:3])
    job = json.loads(job_path.read_text())
    os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = "/work/.hypothesis"
    from trickcatcher_linefacts.pipelines.v11_fair import v4_runtime, v4_worker

    v4_runtime.require_versions()
    # tracer installs the original3GiB memory ceiling on import.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with (
        open("/dev/null", "w") as sink,
        contextlib.redirect_stdout(sink),
        contextlib.redirect_stderr(sink),
    ):
        mode = job["mode"]
        if mode == "verify":
            from trickcatcher_linefacts.pipelines.v11_fair import preconditions

            preconditions.worker(job_path, output_path)
            return
        if mode == "draw":
            result = v4_worker.draw(job)
        elif mode == "classify":
            result = v4_worker.classify(job, Path("/work"))
        elif mode == "facts":
            from trickcatcher_linefacts.pipelines.v11_fair.v4_facts import build

            result = build(job, Path("/work"))
        elif mode == "coverage_probe":
            from trickcatcher_linefacts.pipelines.v11_fair.v4_tools import Coverage

            measurement = Coverage(job["source"], job["entry"], Path("/work"))
            observations = []
            for arguments in job["inputs"]:
                lines, arcs = measurement.measure((tuple(arguments), {}))
                observations.append({"lines": sorted(lines), "arcs": sorted(arcs)})
            result = {
                "core": measurement.cov._collector.tracer_name(),
                "observations": observations,
            }
        elif mode == "inactivity_probe":
            import threading

            never_released = threading.Lock()
            never_released.acquire()
            never_released.acquire()
        elif mode == "specfacts":
            from trickcatcher_linefacts.pipelines.v11_fair import spec_facts

            spec_facts.worker(job_path, output_path)
            return
        else:
            raise ValueError("Unsupported V11 worker mode")
    output_path.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        Path(sys.argv[2]).write_text(json.dumps({"worker_error": type(error).__name__}))
