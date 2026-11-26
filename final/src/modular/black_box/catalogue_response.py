"""Generation-only catalogue contract; legacy catalogue readers stay tolerant."""
import json

from ..response_json import read_input_object, strip_code_fence


def read_catalogue_response(text):
    """Restore a missing envelope around complete JSON values; never invent metadata."""
    try:
        return read_input_object(text)
    except ValueError:
        if not isinstance(text,str) or len(text)>160000:
            raise
        cleaned=strip_code_fence(text)
        if not cleaned.startswith('['):
            raise
    decoder=json.JSONDecoder()
    try:
        inputs,end=decoder.raw_decode(cleaned)
    except ValueError:
        inputs=[];position=1
        for _ in range(128):
            while position<len(cleaned) and cleaned[position] in ' \t\r\n,':position+=1
            try:row,position=decoder.raw_decode(cleaned,position)
            except (ValueError,RecursionError):break
            if not isinstance(row,dict):break
            inputs.append(row)
        if not inputs:raise ValueError('no_complete_input_records') from None
        return {'inputs':inputs},['complete_input_records_recovered']
    tail=cleaned[end:].strip()
    if tail.startswith(','):tail=tail[1:].lstrip()
    if not tail:return {'inputs':inputs},['input_list_envelope_restored']
    catalogue,end=decoder.raw_decode(tail)
    if tail[end:].strip() or not isinstance(catalogue,dict) or not set(catalogue)&{'classes','boundaries','rules'}:
        raise ValueError('ambiguous_catalogue_envelope')
    return {'inputs':inputs,'catalogue':catalogue},['catalogue_envelope_restored']

