"""Dependency-free configuration for the isolated, pinned Pynguin runtime."""
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class PynguinSettings:
    python: str
    search_seconds: int = 10
    wall_seconds: int = 30
    maximum_test_executions: int = 200
    seed: int = 17
    max_extract_calls: int = 64
    owner_limit: int = 10

    def __post_init__(self):
        limits = {'search_seconds':300, 'wall_seconds':600, 'maximum_test_executions':100000,
                  'max_extract_calls':1000, 'owner_limit':100}
        for name, upper in limits.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError('invalid_' + name)
        if self.wall_seconds < self.search_seconds:
            raise ValueError('wall_seconds_must_cover_search')
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError('invalid_seed')
        if not isinstance(self.python, str) or not self.python or '\n' in self.python:
            raise ValueError('invalid_python')

    def to_dict(self):
        return asdict(self)

    def runtime_identity(self):
        from pathlib import Path
        import hashlib
        executable=Path(self.python).absolute()
        paths=[executable]
        root=executable.parent.parent
        paths += sorted(root.glob('lib/python*/site-packages/pynguin/**/*.py'))
        paths += sorted(root.glob('lib/python*/site-packages/pynguin-*.dist-info/METADATA'))
        return {str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths if path.is_file()}

    def validate_environment(self):
        from pathlib import Path
        import json
        import os
        import shutil
        import subprocess
        if not Path(self.python).is_file() or not shutil.which('bwrap'):
            raise ValueError('pynguin_missing_python_or_bwrap')
        code = "import importlib.metadata,json,platform;print(json.dumps({'version':importlib.metadata.version('pynguin'),'python':platform.python_version()}))"
        try:
            completed = subprocess.run([self.python, '-I', '-c', code],
                env={'PATH':os.defpath,'LANG':'C.UTF-8'},capture_output=True,text=True,timeout=10,check=True)
            info = json.loads(completed.stdout)
            if info['version'] != '0.48.0': raise ValueError('pynguin_version_mismatch')
            return info
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
            raise ValueError('unsupported_pynguin_environment') from error

    def configuration(self):
        return {**asdict(self), 'version':'0.48.0', 'algorithm':'DYNAMOSA',
                'assertion_generation':'NONE', 'type_inference_strategy':'TYPE_HINTS',
                'use_master_worker':False, 'execution_cap':'iteration_checked_soft',
                'network':False, 'model_calls':0}
