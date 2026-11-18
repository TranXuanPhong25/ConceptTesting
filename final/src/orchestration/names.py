"""Tên hiển thị trên Prefect; source directory và schema giữ nguyên."""
from pathlib import Path

RESUME_PRESET_NAME = 'Resume · Tiếp tục run đã dừng'


def historical_run_name(directory, metrics=None):
    name = Path(directory).name
    metrics = metrics or {}
    if name.startswith('naive_packaging_audit'):
        title = 'Full164 · Naive cũ + packaging repair'
        count = metrics.get('plain', {}).get('detected')
        return title + (f' · {count} PUT' if count is not None else '')
    if name.startswith('bva_batch_matched164'):
        title = 'Full164 · Direct vs Soft BVA · batch'
        direct = metrics.get('direct', {}).get('detected')
        soft = metrics.get('soft_bva', {}).get('detected')
        return title + (f' · {direct} vs {soft} PUT' if direct is not None and soft is not None else '')
    if name.startswith('boundary_soft_humaneval164'):
        title = 'Full164 · Soft BVA · per-PUT, shared 20'
        count = metrics.get('boundary', {}).get('detected')
        return title + (f' · {count} PUT' if count is not None else '')
    if name.startswith('boundary_prompt_style10'):
        return 'Known10 · Direct vs Soft BVA vs Worksheet · 1 PUT mỗi task'
    if name.startswith('boundary_prompt_style3'):
        return 'Pilot3 · Direct vs Soft BVA vs Worksheet'
    if name.startswith('bucket_candidates_grounded'):
        return 'Bucket tools · Grounded generation · 44 task'
    if name.startswith('bucket_candidates_contractfix'):
        return 'Bucket tools · Pilot 44 task · corrected evaluation'
    return name


def benchmark_run_name(config, preview_only=False):
    selected = config.get('task_numbers', [])
    scope = f'{len(selected)} task' if selected else 'Full164'
    labels = {'direct': 'Direct', 'soft_bva': 'Soft BVA', 'boundary': 'Soft BVA'}
    labels.update(plain='Plain', equivalence='Weak EP', bva_normal='Normal BVA', ep_bva='EP + BVA',
                  decision_table='DT', ep_strong='Strong EP', bva_robust='Robust BVA',
                  bva_worst_case='Worst-case BVA', ep_dt_bva='EP + DT + BVA')
    labels.update(pynguin='Pynguin')
    labels.update(ep_bva_v2='EP + BVA v2', decision_table_v2='DT v2')
    labels.update(control_flow='Control-flow')
    labels.update(tool_direct='Direct seeds', tool_hypothesis='Hypothesis',
                  tool_hypothesis_z3='Hypothesis + Z3', tool_hypothesis_extra='Extra Hypothesis',
                  tool_planner='Combination planner')
    arms = ' vs '.join(labels[name] for name in config['arms'])
    mode = {'batch': 'batch', 'per_put': 'per-PUT, shared budget', 'tools': 'tool sampling', 'pynguin': 'Pynguin baseline'}[config['mode']]
    return ('Preview · ' if preview_only else '') + f'{scope} · {arms} · {mode} · {config["inputs_per_task"]} inputs mỗi task mỗi arm'
