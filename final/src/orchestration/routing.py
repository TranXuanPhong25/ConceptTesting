"""Private routing comparisons; raw endpoint URLs never leave this module."""
import hashlib
import json
from pathlib import Path
import shlex


def endpoint_identity_for_run(directory):
    """Read the worker's private route and return an opaque endpoint identity."""
    try:
        plan = json.loads((Path(directory) / 'launch_plan.json').read_text())
        profile = Path(plan['endpoint_env_file'])
        endpoint = None
        for line in profile.read_text().splitlines():
            fields = shlex.split(line, comments=True)
            if fields and fields[0] == 'export':
                fields = fields[1:]
            if len(fields) == 1 and fields[0].startswith('FINAL_BASE_URL='):
                endpoint = fields[0].split('=', 1)[1].rstrip('/')
        # Match the transport's environment parser: the last assignment wins.
        return hashlib.sha256(endpoint.encode()).hexdigest() if endpoint else None
    except (OSError, KeyError, TypeError, ValueError):
        # Missing private routing cannot establish independent endpoints safely.
        return None
    return None
