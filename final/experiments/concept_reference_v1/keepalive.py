"""Recorded notebook keepalive, at most one one-token request every 20 minutes."""
import threading
import urllib.request

from final.pipeline import save
from .model import QwenModel


class KeepAlive:
    def __init__(self,out):
        self.out=out
        self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set()
        self.thread.join(timeout=2)

    def run(self):
        sequence=1+max((int(p.stem) for p in (self.out/'keepalive').glob('*.json') if p.stem.isdigit()),default=-1)
        while not self.stop.wait(1200):
            path=self.out/'keepalive'/f'{sequence:04d}.json'
            sequence+=1
            save(path,dict(state='started'))
            try:
                model=QwenModel(timeout=60)
                with urllib.request.urlopen(model.url+'/models',timeout=30) as response:
                    status=response.status
                data=model.post('/chat/completions',dict(model=model.model_id,
                    messages=[dict(role='user',content='ping')],temperature=0,max_tokens=1,stream=False,
                    chat_template_kwargs={'enable_thinking':False}))
                save(path,dict(state='received',models_status=status,usage=data.get('usage',{})))
            except Exception as exc:
                save(path,dict(state='unknown',error_type=type(exc).__name__))
