"""Attribute observed equivalence differences using the copied scorer and recorded data.

No functions under test are reimplemented. This compares the exact scorer with
historical and freshly recomputed CPU observations; it never executes an LLM.
"""
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch
from . import paths, oracle_b01 as ob
from .test_equivalence import load_rows, differences


def main():
    root = paths.DATA_OUT / 'equivalence'
    old = paths.REPO / 'trickcatcher_linefacts/out/oracle_v7hyb'
    record = paths.REPO / 'trickcatcher_linefacts/out/gen2_qwen7b_v7hyb_v4_r2'
    tasks, fresh_rows = ob.load_run(root / 'generation')
    old_rows = load_rows(record / 'eval.jsonl')
    order = json.loads((old/'calls.json').read_text())
    old_ex = {n:json.loads((old/'exec'/f'{n}.json').read_text()) for n in order}
    fresh_ex = {n:json.loads((root/'oracle/exec'/f'{n}.json').read_text()) for n in order}
    judges = {(r['task'],r['call']):r for r in json.loads((old/'judge_responses.json').read_text())}
    expected = (old/'report.txt').read_text()
    output = {}
    groups = [('baseline', [], []), ('evaluation_set_order', [34,58], []),
              ('evaluation_deadline', [83], []), ('evaluation_memory', [160], []),
              ('oracle_set_order', [], ['34','58']), ('oracle_deadline', [], ['59','160']),
              ('all_recomputed', [34,58,83,160], ['34','58','59','160'])]
    for name, row_tasks, exec_tasks in groups:
        chosen = [new if new['task'] in row_tasks else old for new,old in zip(fresh_rows,old_rows)]
        ex = dict(old_ex, **{n:fresh_ex[n] for n in exec_tasks})
        out = root / 'causes' / name; out.mkdir(parents=True, exist_ok=True)
        with patch.object(ob, 'load_run', return_value=(tasks,chosen)), \
             patch.object(ob, 'execute', return_value=ex), \
             patch.object(ob, 'judges', return_value=judges), \
             contextlib.redirect_stdout(io.StringIO()):
            ob.score(root/'generation', out, use_llm=False)
        text = (out/'report.txt').read_text()
        output[name] = dict(equal_to_record=text==expected,
                           changed_lines=[i+1 for i,(a,b) in enumerate(zip(text.splitlines(),expected.splitlines())) if a!=b])
    actual = (root/'oracle/report.txt').read_text()
    output['all_recomputed']['equals_actual_recomputed_report'] = (root/'causes/all_recomputed/report.txt').read_text()==actual
    summary = json.loads((root/'equivalence.json').read_text())
    fresh_by_key = {(r['task'],r['arm'],r['sample']):r for r in fresh_rows}
    eval_details = []
    for old_row in old_rows:
        new_row = fresh_by_key[old_row['task'],old_row['arm'],old_row['sample']]
        for field in differences(new_row,old_row):
            actual_value, expected_value = new_row, old_row
            location = field.split(':',1)[0]
            for key in location.strip('/').split('/'):
                if isinstance(actual_value,list): actual_value=actual_value[int(key)]
                elif isinstance(actual_value,dict): actual_value=actual_value.get(key,'<missing>')
                if isinstance(expected_value,list): expected_value=expected_value[int(key)]
                elif isinstance(expected_value,dict): expected_value=expected_value.get(key,'<missing>')
            eval_details.append(dict(task=old_row['task'],arm=old_row['arm'],sample=old_row['sample'],
                                     field=field,actual=actual_value,expected=expected_value))
    output['evaluation_field_details'] = eval_details
    (root/'difference_causes.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='evaluation_field_details'},indent=2))
    assert output['baseline']['equal_to_record'], 'copied scorer differs even with identical CPU observations'
    assert output['all_recomputed']['equals_actual_recomputed_report'], 'an observed difference is unexplained'


if __name__ == '__main__': main()
