"""Version-scoped output and read-only dataset paths, shared by workers."""
from pathlib import Path
import hashlib
import json
import os
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CONFIG = json.loads((HERE / 'config.json').read_text())


def select_model(choice=None):
    choice = choice or os.environ.get('LINEFACTS_MODEL', 'gpt-oss-120b')
    if choice not in CONFIG['models']:
        raise ValueError('unregistered_model_choice:' + choice)
    CONFIG['openrouter'].clear()
    CONFIG['openrouter'].update(CONFIG['models'][choice])
    CONFIG['model_choice'] = choice
    return CONFIG['openrouter']


select_model()

FAIR_FLAGS = ('strict_round2','placebo_matched','caps','shared_scorer')
if 'LINEFACTS_FAIR_FLAGS' in os.environ:
    overrides=json.loads(os.environ['LINEFACTS_FAIR_FLAGS'])
    if set(overrides)-set(FAIR_FLAGS) or any(type(v) is not bool for v in overrides.values()):
        raise ValueError('invalid fairness flag overrides')
    CONFIG.update(overrides)
VERSION = CONFIG['VERSION']
if not re.fullmatch(r'[A-Za-z0-9_-]+', VERSION):
    raise ValueError('VERSION must be a single directory name')
DATASET = os.environ.get('LINEFACTS_DATASET', 'humaneval')


def dataset_paths(dataset=None):
    dataset = dataset or DATASET
    if dataset == 'humaneval':
        data = CONFIG['datasets']['humaneval']
        resolve = lambda value: (REPO / Path(value).expanduser()).resolve()
        result = {k: resolve(v) for k, v in data.items()}
        result['selection'] = HERE / 'selection.json'
        result['name'] = 'humaneval'
    else:
        root = Path(dataset).expanduser().resolve()
        result = {k: root / v for k, v in CONFIG['datasets']['heldout'].items()}
        name = root.parent.name if root.name == 'he' else root.name
        result['name'] = name + '-' + hashlib.sha256(str(root).encode()).hexdigest()[:8]
        result['root'] = root
    return result


DATA_OUT = HERE / 'out' / dataset_paths()['name']


def set_dataset(dataset):
    global DATASET, DATA_OUT
    DATASET = dataset
    os.environ['LINEFACTS_DATASET'] = dataset
    DATA_OUT = HERE / 'out' / dataset_paths()['name']


def safe_output(path):
    path = Path(path).resolve()
    if DATA_OUT.resolve() not in path.parents:
        raise ValueError(f'output must be below {DATA_OUT}')
    return path


def worker_env():
    return {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
            'LINEFACTS_DATASET': DATASET,
            'LINEFACTS_FAIR_FLAGS': json.dumps({k:CONFIG.get(k,False) for k in FAIR_FLAGS})}
