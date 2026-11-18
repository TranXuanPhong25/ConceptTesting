"""Compare completed same-target BVA/plain verdicts; no generation or execution."""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import json
import math
import os
from pathlib import Path
import time

from .continue_bva_evaluation import read, save, digest
from .run_bva_precision import evaluation_observations


def collect(directory, arm):
    manifest = read(directory / "modular_manifest.json")
    detected, non_timeout, value, targets = set(), set(), set(), set()
    rows, witnesses = {}, {}
    for task_id in manifest["tasks"]:
        number = task_id.split('/')[-1]
        task_directory = directory / "tasks" / number
        result = read(task_directory / "result.json")
        if result.get("skip"):
            rows[task_id] = {"skip": result["skip"]}
            continue
        oracle = read(task_directory / "oracle_valid.json")
        indices = set(result["arm_indices"][arm])
        found = set()
        failure_counts = {}
        for put, outcome in result["outcomes"].items():
            key = task_id, str(put)
            targets.add(key)
            failed = sorted(indices & set(outcome["failing"]))
            failure_counts[str(put)] = len(failed)
            if not failed:
                continue
            found.add(str(put))
            detected.add(key)
            observations = evaluation_observations(task_directory, put, outcome)
            candidates = []
            for index in failed:
                observed = observations[index]
                if len(observed) != 2 or not all(item['status'] in ('fail', 'error', 'timeout') for item in observed):
                    raise ValueError("Unconfirmed detection")
                statuses = {item['status'] for item in observed}
                if statuses == {'fail'}:
                    value.add(key)
                if 'timeout' not in statuses:
                    non_timeout.add(key)
                candidates.append({'input': oracle['tests'][index], 'outcomes': observed})
            candidates.sort(key=lambda item: (any(v['status']=='timeout' for v in item['outcomes']),
                                               any(v['status']!='fail' for v in item['outcomes'])))
            witnesses[key] = candidates[0]
        if found != set(result['arms'][arm]['detected_put_ids']):
            raise ValueError("Detected PUT identity mismatch")
        rows[task_id] = {'valid_inputs': result['arms'][arm]['valid_inputs'], 'detected_put_ids': sorted(found),
            'failure_counts': failure_counts, 'valid_input_keys': [oracle['tests'][index]['input_key'] for index in indices],
            'source_admitted_inputs': None}
    summary = read(directory / 'modular_summary.json')
    if len(detected) != summary['arms'][arm]['detected']:
        raise ValueError('Summary detection count differs')
    return {'manifest': manifest, 'summary': summary['arms'][arm], 'detected': detected, 'non_timeout': non_timeout,
            'value': value, 'targets': targets, 'rows': rows, 'witnesses': witnesses}


def partition(left, right, targets):
    left, right = left & targets, right & targets
    return {'bva': len(left), 'naive': len(right), 'shared': len(left & right),
            'bva_only': len(left-right), 'naive_only': len(right-left), 'union': len(left | right),
            'net_bva_minus_naive': len(left)-len(right),
            'bva_only_puts': [{'task_id': t, 'put_id': p} for t, p in sorted(left-right)],
            'naive_only_puts': [{'task_id': t, 'put_id': p} for t, p in sorted(right-left)]}


def compare(bva_directory, naive_directory, output_prefix):
    for directory in (bva_directory, naive_directory):
        status = read(directory / 'status.json')
        if status['state'] != 'complete':
            raise ValueError('Comparison requires completed evaluation')
    bva, naive = collect(bva_directory, 'boundary'), collect(naive_directory, 'plain')
    if bva['targets'] != naive['targets'] or len(bva['targets']) != 1454:
        raise ValueError('Evaluated PUT sets differ')
    export_path = Path(read(naive_directory/'plan.json')['source'])
    receipts = read(export_path/'export_receipts.json')
    excluded={(row['task_id'],str(row['put_id'])) for row in receipts['historical_resource_exclusions']}
    if not excluded.issubset(bva['targets']) or len(excluded)!=17:
        raise ValueError('Historical exclusion target mismatch')
    common = bva['targets']-excluded
    all_counts = partition(bva['detected'],naive['detected'],bva['targets'])
    evidence=[]
    for winner, loser, name in ((bva,naive,'bva_only'),(naive,bva,'naive_only')):
        for key in sorted(winner['detected']-loser['detected']):
            task,put=key;witness=winner['witnesses'][key];other=loser['rows'][task]
            reason='different_input_set'
            if other.get('source_admitted_inputs') is None:reason='source_input_count_pending'
            elif other['source_admitted_inputs']==0:reason='no_source_admitted_inputs'
            elif other.get('valid_inputs',0)==0:reason='no_novel_valid_inputs'
            elif witness['input']['input_key'] in other['valid_input_keys']:reason='shared_input_with_different_confirmation'
            evidence.append({'side':name,'task_id':task,'put_id':put,'other_side_loss_stage':reason,
                'witness':witness,'other_side_valid_inputs':other.get('valid_inputs',0)})
    # Descriptive average over uniform random valid-input subsets; no new tests or selected outcomes.
    normalized={'bva':0.0,'naive':0.0,'zero_matched_input_tasks':0}
    task_rows=[]
    for task in bva['manifest']['tasks']:
        left,right=bva['rows'][task],naive['rows'][task]
        if left.get('skip'):
            task_rows.append({'task_id':task,'skip':left['skip']});continue
        k=min(left['valid_inputs'],right['valid_inputs']);normalized['zero_matched_input_tasks']+=k==0
        for label,row in [('bva',left),('naive',right)]:
            n=row['valid_inputs']
            for failed in row['failure_counts'].values():
                if k and failed:
                    normalized[label]+=1-(math.comb(n-failed,k)/math.comb(n,k) if n-failed>=k else 0)
        task_rows.append({'task_id':task,'bva_valid_inputs':left['valid_inputs'],'naive_valid_inputs':right['valid_inputs'],
            'bva_detected_ids':left['detected_put_ids'],'naive_detected_ids':right['detected_put_ids']})
    loss_stages = {}
    for side in ('bva_only', 'naive_only'):
        loss_stages[side] = dict(Counter(row['other_side_loss_stage'] for row in evidence if row['side'] == side))
    both_valid_tasks = {row['task_id'] for row in task_rows if not row.get('skip')
                        and row['bva_valid_inputs'] and row['naive_valid_inputs']}
    both_valid_targets = {key for key in bva['targets'] if key[0] in both_valid_tasks}
    coverage = {'eligible_tasks': sum(not row.get('skip') for row in task_rows),
        'tasks_with_valid_inputs': {side: sum(not row.get('skip') and row[side+'_valid_inputs'] > 0 for row in task_rows)
                                   for side in ('bva', 'naive')},
        'both_have_valid_inputs': {'tasks': len(both_valid_tasks),
            **partition(bva['detected'], naive['detected'], both_valid_targets)}}
    report={'scope':'Retrospective stored-input comparison on identical cohort/oracle/scorer,not prompt-only or call-matched efficacy',
        'full_targets':all_counts,'common_1437_targets':partition(bva['detected'],naive['detected'],common),
        'non_timeout_confirmations':partition(bva['non_timeout'],naive['non_timeout'],bva['targets']),
        'stable_value_mismatches':partition(bva['value'],naive['value'],bva['targets']),
        'bva_summary':bva['summary'],'naive_summary':naive['summary'],
        'generation_calls':{'bva':1454,'naive':receipts['original_plain_usage']['received'],'new_model_calls':0},
        'generation_usage':{'bva':read(bva_directory/'result_digest.json')['source_generation_usage'],
                            'naive':receipts['original_plain_usage']},
        'uniform_valid_budget_expected_detections_secondary':normalized,
        'coverage': coverage, 'unique_detection_loss_stages': loss_stages,
        'evidence':evidence,'tasks':task_rows,'bva_evaluation':str(bva_directory),'naive_evaluation':str(naive_directory),
        'scoring_identities_match':None,'read_only_replays_match':None}
    save(output_prefix.with_suffix('.json'),report)
    f=all_counts;c=report['common_1437_targets']
    lines=['# Cached naiveLLM versus full soft BVA','',
        'Stored naive inputs have now been rescored against the same 1,454 base-passing PUTs as BVA, using the same corrected oracle and frozen evaluator. No new model calls or input repairs were made. Comparison reads saved outcomes; source hashes and generation freezes are not checked.','',
        '| Target scope | BVA | Naive | Shared | BVA-only | Naive-only | Net BVA |',
        '|---|---:|---:|---:|---:|---:|---:|',
        f"| Full 1,454 PUTs | {f['bva']} | {f['naive']} | {f['shared']} | {f['bva_only']} | {f['naive_only']} | {f['net_bva_minus_naive']:+d} |",
        f"| Historical common 1,437 PUTs | {c['bva']} | {c['naive']} | {c['shared']} | {c['bva_only']} | {c['naive_only']} | {c['net_bva_minus_naive']:+d} |",'',
        'These are absolute additional detections beyond base tests. The net difference above compares the two generators; it is not bug recall. The historical naive result of 72 used an older oracle/runtime and is superseded here by the unchanged-input rescore.','',
        '| Metric | BVA | Naive |', '|---|---:|---:|',
        f"| Valid novel task inputs | {bva['summary']['valid_inputs']:,} | {naive['summary']['valid_inputs']:,} |",
        f"| Tasks with detection | {bva['summary']['tasks_detected']} | {naive['summary']['tasks_detected']} |",
        f"| Eligible tasks with valid novel inputs | {coverage['tasks_with_valid_inputs']['bva']} | {coverage['tasks_with_valid_inputs']['naive']} |",
        f"| PUTs with a stable wrong-value witness | {report['stable_value_mismatches']['bva']} | {report['stable_value_mismatches']['naive']} |",
        f"| PUTs with a non-timeout failure witness | {report['non_timeout_confirmations']['bva']} | {report['non_timeout_confirmations']['naive']} |",
        f"| Original received writer calls | 1,454 | {receipts['original_plain_usage']['received']} |",
        f"| Original known generation tokens | {report['generation_usage']['bva']['known_usage']['total_tokens']:,} | {report['generation_usage']['naive']['known_usage']['total_tokens']:,} |",'',
        'Failure categories can overlap. A non-timeout witness may be an exception rather than an incorrect returned value. Unknown historical transport attempts are recorded separately in the JSON usage receipts.','',
        'Coverage and interface losses matter:', '',
        '| Unique detection | Other side has no admitted source input | Other side has no novel valid input | Different valid input set |',
        '|---|---:|---:|---:|']
    for side in ('bva_only', 'naive_only'):
        stages = loss_stages[side]
        lines.append(f"| {side} | {stages.get('no_source_admitted_inputs', 0)} | {stages.get('no_novel_valid_inputs', 0)} | {stages.get('different_input_set', 0)} |")
    supported = coverage['both_have_valid_inputs']
    lines.extend(['',
        f"On the {supported['tasks']} tasks where both generators retain a valid novel input, BVA detects {supported['bva']} PUTs and naive detects {supported['naive']}. This is a descriptive coverage restriction, not an input-budget or writer-call matched comparison. A gain on tasks with no executable baseline input does not by itself demonstrate better boundary selection.",
        '', 'For example, old task 23 generated Unicode strings but encoded a single argument as `(\'你好\')` instead of `(\'你好\',)`, so the parser rejected it. In tasks 40, 43, 126 and 151, list contents were encoded as the positional argument list; oracle binding/domain checks rejected every admitted record. These records remain unchanged and rejected. Repairing them would be a separate experiment.',
        '', 'All original admitted naive input records were reused unchanged. Empty source batches and the resource-skipped task 160 stay empty. Corrected HumanEval+reference, full two-repeat scorer, 3 s timeout and the exact frozen cohort are the same as BVA.',
        '',f"Both generators nominally request 20 inputs/task. Naive saw multiple PUTs together and omitted 17 resource-risk PUTs from its historical context/evaluation. BVA generated per PUT with fixed shares. Visibility, schemas, generation epochs and writer costs differ, so the raw counts do not isolate boundary guidance.",
        '',f"Secondary expected detections under uniform valid-input budget matching: BVA {normalized['bva']:.2f}, naive {normalized['naive']:.2f}. For each task, k=min(valid_BVA, valid_naive); {normalized['zero_matched_input_tasks']} eligible tasks have k=0 and contribute no detections for either side. The analytical mean 1-C(n-f,k)/C(n,k) is conditional on recorded confirmed failures. It is not another executed trial, a primary result or a superiority test.",
        '', 'PUT identities below are task-local IDs. All unique witnesses and loss-stage classifications are preserved in the JSON report.','',
        '| Task | BVA detected PUTs | Naive detected PUTs |','|---|---|---|'])
    for row in task_rows:
        if row.get('skip'):lines.append(f"| {row['task_id']} | skip | {row['skip']} |")
        else:lines.append(f"| {row['task_id']} | {', '.join(row['bva_detected_ids']) or '—'} | {', '.join(row['naive_detected_ids']) or '—'} |")
    output_prefix.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bva',type=Path,default=Path('final/out/boundary_soft_humaneval164_evaluation_20261107_224720'))
    parser.add_argument('--naive',type=Path,required=True)
    parser.add_argument('--output-prefix',type=Path)
    parser.add_argument('--watch',action='store_true')
    options=parser.parse_args();last=None
    while True:
        status=read(options.naive/'status.json')
        if status['state']=='complete':break
        if not options.watch or status['state']=='interrupted':raise RuntimeError('Naive rescore is not complete: '+str(status))
        progress=read(options.naive/'progress.json') if (options.naive/'progress.json').exists() else {}
        if progress.get('evaluated_tasks')!=last:
            last=progress.get('evaluated_tasks');print(json.dumps({'state':status['state'],'evaluated_tasks':last}),flush=True)
        if status.get('pid'):os.kill(status['pid'],0)
        time.sleep(20)
    prefix=options.output_prefix or Path('final/review/naive_vs_soft_bva_full164_'+dt.datetime.now().strftime('%Y-%m-%d'))
    report=compare(options.bva.resolve(),options.naive.resolve(),prefix)
    print(json.dumps({'report':str(prefix.with_suffix('.md')),'full_targets':report['full_targets'],
        'common_1437_targets':report['common_1437_targets'],'naive_summary':report['naive_summary']}),flush=True)


if __name__=='__main__':
    main()
