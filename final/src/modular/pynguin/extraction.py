"""Execute exported pytest functions in isolation and capture pre-call literals."""
from pathlib import Path
import ast
import json
import shutil


def independent_calls(function, entry):
    """Prove a straight-line sequence uses only fresh literals, never prior outputs."""
    literals=set()
    consumed=set()
    def literal_argument(node):
        if isinstance(node,ast.Name): return node.id in literals
        if isinstance(node,(ast.List,ast.Tuple,ast.Set)): return all(literal_argument(item) for item in node.elts)
        if isinstance(node,ast.Dict): return all(key is not None and literal_argument(key) and literal_argument(value) for key,value in zip(node.keys,node.values))
        try: ast.literal_eval(node)
        except (ValueError,TypeError): return False
        return True
    for statement in function.body:
        value=statement.value if isinstance(statement,(ast.Expr,ast.Assign)) else None
        if value is None: return False
        if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr==entry:
            arguments=value.args+[keyword.value for keyword in value.keywords]
            names={node.id for argument in arguments for node in ast.walk(argument) if isinstance(node,ast.Name)}
            if names-literals or names & consumed or not all(literal_argument(argument) for argument in arguments): return False
            consumed.update(names)
            if isinstance(statement,ast.Assign):
                # A result may be discarded, but can never become a later input.
                for target in statement.targets:
                    if not isinstance(target,ast.Name): return False
                    literals.discard(target.id)
        elif isinstance(statement,ast.Assign) and len(statement.targets)==1 and isinstance(statement.targets[0],ast.Name):
            try: ast.literal_eval(value)
            except (ValueError,TypeError): return False
            for target in statement.targets:
                literals.add(target.id)
                consumed.discard(target.id)
        else: return False
    return True


def immutable_assignment(node):
    if not isinstance(node,(ast.Assign,ast.AnnAssign)): return False
    targets=node.targets if isinstance(node,ast.Assign) else [node.target]
    if not all(isinstance(target,ast.Name) for target in targets): return False
    try: value=ast.literal_eval(node.value)
    except (ValueError,TypeError): return False
    def immutable(value):
        return type(value) in (str,bytes,int,float,complex,bool,type(None)) or type(value) is tuple and all(immutable(item) for item in value)
    return immutable(value)


def target_source(source, context_source=''):
    prefix=context_source+'\n\n' if context_source else ''
    return prefix+source, prefix.count('\n')


def extract(python, workspace, source, entry, exports, maximum, wall, *, context_source=''):
    from . import runner
    from .. import call_builder
    from .runner import sandbox
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace/'target.py').write_text(target_source(source,context_source)[0])
    (workspace/'job.json').write_text(json.dumps({'entry':entry,'maximum':maximum}))
    shutil.copyfile(__file__, workspace/'extract.py')
    shutil.copyfile(runner.__file__, workspace/'runner.py')
    shutil.copyfile(call_builder.__file__, workspace/'call_builder.py')
    for name, text in exports.items():
        if not name.startswith('test_') or Path(name).name != name or not name.endswith('.py'):
            raise ValueError('invalid_export_name')
        (workspace/name).write_text(text)
    receipt = sandbox(python,workspace,'extract.py',wall)
    if receipt['status'] != 'complete': return {**receipt,'calls':[],'rejected':[]}
    try:
        from final.src.runtime.artifacts import read_sandbox_file
        value=json.loads(read_sandbox_file(workspace,'extraction.json'))
        if not isinstance(value,dict) or not isinstance(value['calls'],list): raise ValueError()
        return {**receipt,**value}
    except (OSError,ValueError,KeyError):
        return {**receipt,'status':'failed','reason':'missing_or_invalid_extraction','calls':[],'rejected':[]}


def child_extract():
    import functools
    import importlib
    import inspect
    import sys
    sys.path.insert(0,'/work')
    from runner import limits
    limits()
    job=json.loads(Path('/work/job.json').read_text())
    # Copy the project's supported-literal check into this isolated worker verbatim.
    from call_builder import supported_value
    result={'status':'complete','calls':[],'rejected':[]}
    remaining=job['maximum']
    target_tree=ast.parse(Path('target.py').read_text())
    if (any(isinstance(node,(ast.Global,ast.Nonlocal)) for node in ast.walk(target_tree))
            or any(isinstance(node,ast.Attribute) and isinstance(node.ctx,(ast.Store,ast.Del)) for node in ast.walk(target_tree))
            or any(isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('setattr','delattr') for node in ast.walk(target_tree))
            or any(isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.ClassDef)) and not immutable_assignment(node) for node in target_tree.body)):
        result.update(status='unsupported_input',reason='explicit_global_or_closure_state')
        Path('extraction.json').write_text(json.dumps(result)); return
    for path in sorted(Path('/work').glob('test_*.py')):
        tree=ast.parse(path.read_text())
        names=[node.name for node in tree.body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')]
        for name in names:
            if remaining <= 0: break
            sys.modules.pop('target',None)
            target=importlib.import_module('target')
            original=getattr(target,job['entry'])
            signature=inspect.signature(original)
            calls=[]
            interactions=[]
            depth=0
            def track_helper(function):
                @functools.wraps(function)
                def tracked(*args,**kwargs):
                    if depth == 0: interactions.append(function.__name__)
                    return function(*args,**kwargs)
                return tracked
            for helper_name,function in list(vars(target).items()):
                if (helper_name != job['entry'] and not helper_name.startswith('_')
                        and (inspect.isfunction(function) or inspect.isbuiltin(function))):
                    setattr(target,helper_name,track_helper(function))
            def capture(*args,**kwargs):
                nonlocal depth,remaining
                if depth == 0:
                    if remaining <= 0: raise RuntimeError('extraction_call_cap')
                    remaining-=1
                    try:
                        bound=signature.bind(*args,**kwargs)
                        bound.apply_defaults()
                        if not all(supported_value(value) for value in bound.arguments.values()):
                            raise ValueError('unsupported_object_input')
                        # Mutable aliases change fresh-call semantics even when both values serialize.
                        seen=set()
                        def check_alias(value):
                            if type(value) in (list,dict,set):
                                if id(value) in seen: raise ValueError('aliased_mutable_input')
                                seen.add(id(value))
                            if type(value) in (list,tuple,set):
                                for item in value: check_alias(item)
                            elif type(value) is dict:
                                for key,item in value.items(): check_alias(key); check_alias(item)
                        for value in bound.arguments.values(): check_alias(value)
                        calls.append({'args':repr(args),'kwargs':repr(kwargs),'test':path.name+'::'+name})
                    except (TypeError,ValueError,RecursionError) as error:
                        calls.append({'reason':str(error),'test':path.name+'::'+name})
                depth+=1
                try: return original(*args,**kwargs)
                finally: depth-=1
            capture=functools.wraps(original)(capture)
            setattr(target,job['entry'],capture)
            namespace={'__name__':'exported_tests'}
            try:
                exec(compile(tree,str(path),'exec'),namespace)
                namespace[name]()
            except Exception as error:
                # A target exception does not invalidate its pre-call input.
                if not calls: result['rejected'].append({'reason':'test_import_or_execution:'+type(error).__name__,'test':path.name+'::'+name})
            test_function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
            mutates_attributes=any(isinstance(node,ast.Attribute) and isinstance(node.ctx,(ast.Store,ast.Del))
                                  or isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('setattr','delattr')
                                  for node in ast.walk(test_function))
            if interactions or mutates_attributes:
                result['rejected'].extend({**call,'reason':'target_helper_interaction'} for call in calls)
            elif len(calls)>1 and not independent_calls(test_function,job['entry']):
                result['rejected'].extend({**call,'reason':'stateful_test_sequence'} for call in calls)
            else:
                for call in calls:
                    result['rejected' if 'reason' in call else 'calls'].append(call)
    if not result['calls']:
        result['status']='unsupported_input' if result['rejected'] else 'empty'
    Path('extraction.json').write_text(json.dumps(result))


if __name__ == '__main__':
    child_extract()
