"""Original-coordinate source index and isolated spec/body views; syntax only."""
import ast
import hashlib
import io
import re
import tokenize
from .paths import CONFIG
LIMITS=CONFIG['chain']


def digest(text):
    try:return hashlib.sha256(text.encode('utf-8')).hexdigest()
    except UnicodeError as exc:raise ValueError('invalid_unicode') from exc


def prepare(source,entry,base='',*,valid_code=None):
    if type(source) is not str or len(source)>LIMITS['max_source_chars']:raise ValueError('source_size')
    try:source.encode('utf-8')
    except UnicodeError as exc:raise ValueError('invalid_unicode') from exc
    if re.search(r'\r(?!\n)',source):raise ValueError('standalone_CR_unsupported')
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError) as exc:raise ValueError('source_parse') from exc
    todo=[(tree,0)];size=0
    while todo:
        node,depth=todo.pop();size+=1
        if size>LIMITS['max_ast_nodes'] or depth>LIMITS['max_ast_depth']:raise ValueError('source_ast_limit')
        todo.extend((child,depth+1) for child in ast.iter_child_nodes(node))
    targets=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==entry]
    if len(targets)!=1:raise ValueError('entry_not_unique')
    fn=targets[0];raw=source.encode('utf-8');parts=source.split('\n');lines=[part+'\n' for part in parts[:-1]]+[parts[-1]]
    byte_lines=[x.encode('utf-8') for x in lines];starts=[0]
    for line in byte_lines:starts.append(starts[-1]+len(line))
    def offset(line,col):return starts[line-1]+col
    def token_offset(position):
        line,col=position
        return starts[line-1]+len(lines[line-1][:col].encode('utf-8'))
    masks=[];excluded=set()
    for owner in ast.walk(tree):
        if isinstance(owner,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and owner.body:
            doc=owner.body[0]
            if isinstance(doc,ast.Expr) and isinstance(doc.value,ast.Constant) and type(doc.value.value) is str:
                masks.append((offset(doc.lineno,doc.col_offset),offset(doc.end_lineno,doc.end_col_offset)))
                excluded.update(id(x) for x in ast.walk(doc))
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type==tokenize.COMMENT:masks.append((token_offset(token.start),token_offset(token.end)))
    masked=bytearray(raw)
    for start,end in masks:
        for i in range(start,end):
            if masked[i] not in (10,13):masked[i]=32
    function_body=set()
    for f in ast.walk(tree):
        if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for statement in f.body:function_body.update(id(x) for x in ast.walk(statement))
    sha=digest(source);nodes=[];edges=[];lookup={}
    for node in ast.walk(tree):
        if id(node) in excluded or not hasattr(node,'end_lineno') or node.end_lineno is None:continue
        uid=f'{sha}:{type(node).__name__}:{node.lineno}:{node.col_offset}:{node.end_lineno}:{node.end_col_offset}'
        lookup[id(node)]=uid
        nodes.append(dict(id=uid,kind=type(node).__name__,is_statement=isinstance(node,ast.stmt),execution_scope='function_body' if id(node) in function_body else 'initialization',span=[node.lineno,node.col_offset,node.end_lineno,node.end_col_offset]))
    for parent in ast.walk(tree):
        if id(parent) not in lookup:continue
        for child in ast.iter_child_nodes(parent):
            if id(child) in lookup:edges.append(dict(source=lookup[id(parent)],target=lookup[id(child)],kind='syntactic_child'))
    spec=ast.get_docstring(fn,clean=False) or ''
    signature=('async ' if isinstance(fn,ast.AsyncFunctionDef) else '')+fn.name+'('+ast.unparse(fn.args)+')'
    if fn.returns:signature+=' -> '+ast.unparse(fn.returns)
    task_hash=digest(source+'\0'+entry+'\0'+base+'\0'+(valid_code or ''))
    return dict(task_hash=task_hash,source_hash=sha,spec_hash=digest(spec),source_original=source,valid_code=valid_code,validity_provenance='mined_filter_not_spec_proof' if valid_code else 'no_filter',
                source_masked=bytes(masked).decode('utf-8'),spec=spec,signature=signature,entry=entry,base=base,
                entry_source_id=lookup[id(fn)],parameter_ids=[a.arg for a in fn.args.posonlyargs+fn.args.args+fn.args.kwonlyargs],
                arity=dict(positional=len(fn.args.posonlyargs+fn.args.args),required=len(fn.args.posonlyargs+fn.args.args)-len(fn.args.defaults),varargs=fn.args.vararg is not None,required_keyword_only=any(x is None for x in fn.args.kw_defaults)),
                nodes=nodes,edges=edges,masked_ranges=[list(x) for x in masks],coordinates=dict(source_columns='UTF8_bytes',quote_offsets='decoded_spec_characters'),
                limitations=['external/imported implementation context is not fetched','names and executable literals may reveal intent'])
