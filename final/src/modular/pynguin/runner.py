"""Run upstream and extraction in a disposable, resource-bounded bwrap workspace."""
from pathlib import Path
import json
import os
import shutil
import signal
import subprocess
import sys
import time

VERSION = '0.48.0'


def sandbox(python, workspace, script, wall_seconds):
    """No host home, credentials or network; PID namespace dies with its init."""
    python = Path(python).absolute()
    if not python.is_file() or not os.access(python, os.X_OK) or not shutil.which('bwrap'):
        return {'status':'unsupported_environment', 'reason':'missing_python_or_bwrap'}
    # The venv interpreter symlink needs both its venv and base installation.
    base_python = python.resolve()
    command = ['bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL']
    roots = ['/usr','/bin','/lib','/lib64', str(python.parent.parent), str(base_python.parent.parent)]
    for root in dict.fromkeys(roots):
        if Path(root).exists(): command += ['--ro-bind',root,root]
    command += ['--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                '--bind',str(workspace),'/work','--chdir','/work',str(python),'-I','-B','/work/' + script]
    env = {'PATH':os.defpath,'HOME':'/tmp','LANG':'C.UTF-8','PYTHONHASHSEED':'0',
           'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYNGUIN_DANGER_AWARE':'1'}
    started = time.monotonic()
    with (workspace/'stdout.log').open('wb') as out, (workspace/'stderr.log').open('wb') as err:
        process = subprocess.Popen(command, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            process.wait(timeout=wall_seconds)
        except BaseException as error:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
            if not isinstance(error, subprocess.TimeoutExpired): raise
            return {'status':'timeout','reason':'parent_wall_guard','command':command,
                    'elapsed_seconds':time.monotonic()-started}
    return {'status':'complete' if process.returncode == 0 else 'failed',
            'reason':None if process.returncode == 0 else 'child_exit', 'returncode':process.returncode,
            'elapsed_seconds':time.monotonic()-started,'command':command}


def limits():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8*1024**2, 8*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128,128))
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))


def child_search():
    from dataclasses import asdict
    from importlib.metadata import version
    import platform
    import pynguin.configuration as conf
    from pynguin import generator
    from pynguin.utils.statistics.runtimevariable import RuntimeVariable
    limits()
    settings = json.loads(Path('/work/settings.json').read_text())
    if version('pynguin') != VERSION: raise RuntimeError('wrong_pynguin_version')
    config = conf.Configuration(project_path='/work', module_name='target',
        test_case_output=conf.TestCaseOutputConfiguration(output_path='/work/export',
            assertion_generation=conf.AssertionGenerator.NONE),
        algorithm=conf.Algorithm.DYNAMOSA, use_master_worker=False,
        subprocess=False, subprocess_if_recommended=False)
    config.stopping.maximum_search_time = settings['search_seconds']
    config.stopping.maximum_test_executions = settings['maximum_test_executions']
    config.stopping.maximum_test_execution_timeout = 1
    config.stopping.maximum_module_execution_timeout = 1
    config.seeding.seed = settings['seed']
    config.statistics_output.report_dir = '/work/statistics'
    config.statistics_output.output_variables = [RuntimeVariable.Coverage, RuntimeVariable.TotalTime,
                                                 RuntimeVariable.Executed]
    config.type_inference.type_inference_strategy = conf.TypeInferenceStrategy.TYPE_HINTS
    config.local_search.local_search_llm = False
    config.large_language_model.hybrid_initial_population = False
    Path('/work/actual_config.json').write_text(json.dumps({'version':version('pynguin'),
        'python':platform.python_version(),'configuration':asdict(config)},default=str))
    conf.configuration = config
    sys.path.insert(0, '/work')
    result = generator.run_pynguin()
    Path('/work/tool_result.json').write_text(json.dumps({'exit_code':int(result)}))
    if int(result) != 0: raise SystemExit(int(result))


if __name__ == '__main__':
    child_search()
