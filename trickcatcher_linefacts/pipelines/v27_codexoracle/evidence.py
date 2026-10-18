"""Type-aware observation checks; relation prose is never compiled into semantics."""
from .chain_inputs import parse_literal,typed_value


def compare_prediction(prediction,execution):
    kind=prediction['kind'];status=execution.get('status')
    if kind in ('relation_text','unknown'):return dict(result='unverified',reason='relation_not_executable' if kind=='relation_text' else 'no_prediction')
    if status in ('timeout','unresolved','unsupported') or not execution.get('native_checked',False):return dict(result='unverified',reason='execution_unresolved_or_not_checked')
    if kind=='exception_type':
        actual=execution.get('exception_type')
        if status=='exception' and type(actual) is str:return dict(result='observed_match' if actual==prediction['exception_type'] else 'observed_contradiction',scope='native_exception_class')
        if status=='ok':return dict(result='observed_contradiction',scope='normal_return_not_exception')
        return dict(result='unverified',reason='exception_not_captured')
    if kind=='exact_value':
        if status=='exception':return dict(result='observed_contradiction',scope='exception_not_value')
        if status!='ok' or execution.get('output_capture')!='literal':return dict(result='unverified',reason='output_not_literal_or_oversize')
        try:
            expected=parse_literal(prediction['value_repr'],output=True);actual=parse_literal(execution['output_repr'],output=True)
            same=typed_value(expected)==typed_value(actual)
        except (ValueError,TypeError,KeyError,RecursionError):return dict(result='unverified',reason='unsupported_value')
        return dict(result='observed_match' if same else 'observed_contradiction',scope='exact_typed_value_on_this_input')
    return dict(result='unverified',reason='unsupported_prediction')


def project_feedback(attempts):
    """All attempted slots, fixed first/last samples per requested ID; no outcome ranking."""
    rows=[]
    for i,attempt in enumerate(attempts):
        row={k:attempt[k] for k in ('proposal_id','input_repr','status','reason','prediction_check') if k in attempt}
        row['id']=f'F{i+1}';execution=attempt.get('execution',{})
        row['execution']={k:execution[k] for k in ('status','exception_type','exception_module','output_capture','output_repr','native_checked','worker_details','verification_reason') if k in execution}
        observations=[]
        for observation in execution.get('observations',[]):
            rec={k:observation[k] for k in ('source_id','kind','status','reason') if k in observation}
            values=observation.get('events',[])
            rec['events']=values if len(values)<=2 else [values[0],values[-1]]
            rec['omitted_events']=max(0,len(values)-2)+observation.get('omitted_events',0)
            observations.append(rec)
        row['observations']=observations;rows.append(row)
    return rows
