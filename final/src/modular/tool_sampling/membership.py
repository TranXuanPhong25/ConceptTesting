"""Tool membership accepts Python expressions; extended evaluation stays in bwrap."""
from __future__ import annotations

import ast
import atexit
from functools import lru_cache
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import threading

from ..common import predicates
from ..call_builder import supported_value

BUILTINS={'all','any','isinstance','type','str','bool','list','tuple','set','dict','sorted','reversed','enumerate','zip','range','round','pow','divmod','ord','chr','hex','bin','oct'}
METHODS={'isupper','islower','isalpha','isalnum','isdigit','isdecimal','isnumeric','isspace',
         'isascii','istitle','lower','upper','casefold','capitalize','title','swapcase',
         'startswith','endswith','count','find','rfind','index','rindex','strip','lstrip','rstrip',
         'split','rsplit','splitlines','replace','join','removeprefix','removesuffix',
         'issubset','issuperset','isdisjoint','union','intersection','difference',
         'symmetric_difference','keys','values','items','get'}
BOOLEAN_METHODS={'isupper','islower','isalpha','isalnum','isdigit','isdecimal','isnumeric','isspace','isascii','istitle','startswith','endswith','issubset','issuperset','isdisjoint'}
NODES=predicates.NODES+(ast.Is,ast.IsNot,ast.Mult,ast.Div,ast.FloorDiv,ast.Mod,ast.Pow,
    ast.BitAnd,ast.BitOr,ast.BitXor,
    ast.IfExp,ast.Slice,ast.Attribute,ast.keyword,ast.GeneratorExp,ast.ListComp,ast.SetComp,
    ast.DictComp,ast.Dict,ast.comprehension,ast.Store)


def expression(text,names):
    if not isinstance(text,str) or not text or len(text)>2048:
        raise ValueError('invalid_predicate_size')
    tree=ast.parse(text,mode='eval')
    if sum(1 for _ in ast.walk(tree))>512:raise ValueError('predicate_node_limit')
    class Validate(ast.NodeVisitor):
        def __init__(self):self.scope=set(names)
        def generic_visit(self,node):
            if not isinstance(node,NODES):raise ValueError('unsupported_predicate_node:'+type(node).__name__)
            super().generic_visit(node)
        def visit_Name(self,node):
            if node.id.startswith('_') or node.id not in self.scope|set(predicates.FUNCTIONS)|BUILTINS:
                raise ValueError('unknown_predicate_name:'+node.id)
        def visit_Attribute(self,node):
            raise ValueError('predicate_attribute_requires_allowed_method_call')
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name):
                if node.func.id not in set(predicates.FUNCTIONS)|BUILTINS:
                    raise ValueError('unsupported_predicate_call')
            elif isinstance(node.func,ast.Attribute) and node.func.attr in METHODS:
                self.visit(node.func.value)
            else:raise ValueError('unsupported_predicate_call')
            for argument in node.args:self.visit(argument)
            for keyword in node.keywords:
                if keyword.arg is None or keyword.arg.startswith('_'):raise ValueError('unsupported_predicate_keyword')
                self.visit(keyword.value)
        def comprehension(self,node):
            previous=self.scope.copy()
            for generator in node.generators:
                if generator.is_async:raise ValueError('async_predicate_unsupported')
                self.visit(generator.iter)
                targets=list(ast.walk(generator.target))
                if any(not isinstance(t,(ast.Name,ast.Tuple,ast.List,ast.Store)) for t in targets):
                    raise ValueError('invalid_comprehension_binding')
                bound={t.id for t in targets if isinstance(t,ast.Name)}
                if any(n.startswith('_') or n in set(predicates.FUNCTIONS)|BUILTINS for n in bound):
                    raise ValueError('predicate_binding_shadows_helper')
                self.scope|=bound
                for condition in generator.ifs:self.visit(condition)
            for field in ('elt','key','value'):
                if hasattr(node,field):self.visit(getattr(node,field))
            self.scope=previous
        visit_GeneratorExp=comprehension
        visit_ListComp=comprehension
        visit_SetComp=comprehension
        visit_DictComp=comprehension
    Validate().visit(tree)
    return tree


class PredicateSandbox:
    def __init__(self):
        self.process=None;self.directory=None;self.lock=threading.Lock();self.buffer=b''
        self.owner=os.getpid()

    def close(self):
        if self.process is not None:
            self.process.kill() if self.process.poll() is None else None
            self.process.wait()
            self.process.stdin.close();self.process.stdout.close()
            self.process=None
        if self.directory is not None:self.directory.cleanup();self.directory=None
        self.buffer=b''

    def start(self):
        if not shutil.which('bwrap'):raise ValueError('predicate_sandbox_requires_bwrap')
        self.directory=tempfile.TemporaryDirectory(prefix='tool-membership-')
        folder=Path(self.directory.name)
        for relative,source in [('support/__init__.py',None),('support/common/__init__.py',None),
                ('support/call_builder.py',Path(predicates.__file__).parents[1]/'call_builder.py'),
                ('support/common/predicates.py',Path(predicates.__file__)),
                ('predicate_worker.py',Path(__file__).with_name('predicate_worker.py'))]:
            target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if source:shutil.copyfile(source,target)
            else:target.write_text('')
        command=['bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL']
        for path in ['/usr','/lib','/lib64']:
            if Path(path).exists():command+=['--ro-bind',path,path]
        prefix=str(Path(sys.base_prefix).resolve())
        if prefix!='/usr' and not prefix.startswith('/usr/'):command+=['--ro-bind',prefix,prefix]
        command+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(folder),'/work','--chdir','/work',
            str(Path(sys.executable).resolve()),'-S','-B','-P','-c',
            "import sys,runpy;sys.path.insert(0,'/work');runpy.run_path('/work/predicate_worker.py',run_name='__main__')"]
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            env={'PATH':os.defpath,'HOME':'/tmp','LANG':'C.UTF-8','PYTHONHASHSEED':'0'},bufsize=0)

    def evaluate(self,text,arguments):
        if self.owner!=os.getpid():raise ValueError('predicate_sandbox_cross_process_use')
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self.close();self.start()
            request=json.dumps({'expression':text,'arguments':repr(arguments)},ensure_ascii=True).encode()+b'\n'
            if len(request)>256000:raise ValueError('predicate_input_size_limit')
            try:
                import time
                deadline=time.monotonic()+2
                writer=self.process.stdin.fileno()
                os.set_blocking(writer,False)
                sent=0
                while sent<len(request):
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not select.select([],[writer],[],remaining)[1]:
                        raise TimeoutError('predicate_timeout')
                    try:sent+=os.write(writer,request[sent:sent+4096])
                    except BlockingIOError:continue
                while b'\n' not in self.buffer:
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not select.select([self.process.stdout],[],[],remaining)[0]:
                        raise TimeoutError('predicate_timeout')
                    part=os.read(self.process.stdout.fileno(),4096)
                    if not part:raise ValueError('predicate_worker_exited')
                    self.buffer+=part
                    if len(self.buffer)>4096:raise ValueError('predicate_output_limit')
                line,self.buffer=self.buffer.split(b'\n',1)
                response=json.loads(line)
            except (OSError,TimeoutError,ValueError) as exc:
                self.close();raise ValueError(str(exc)) from None
            if 'error' in response:raise ValueError(response['error'])
            if type(response.get('result')) is not bool:raise ValueError('predicate_must_return_bool')
            return response['result']


_SANDBOX=PredicateSandbox()
atexit.register(_SANDBOX.close)


@lru_cache(maxsize=4096)
def _extended(text,arguments_literal):
    return _SANDBOX.evaluate(text,ast.literal_eval(arguments_literal))


def evaluate(text,arguments):
    if not isinstance(arguments,dict) or not supported_value(arguments):
        raise ValueError('unsupported_predicate_arguments')
    try:predicates.expression(text,arguments)
    except (ValueError,SyntaxError):
        expression(text,arguments)
        return _extended(text,repr(arguments))
    return predicates.evaluate(text,arguments)
