"""Exact-request replay; only repaired-arm expected-output calls may be fresh."""
import hashlib
import json


def key(body):
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class Client:
    def __init__(self,live,receipts,allow_new):
        self.live=live;self.model=live.model;self.receipts=receipts;self.allow_new=allow_new

    def chat(self,messages,seed,*,temperature=0.7,top_p=0.95,max_tokens=1024):
        body=dict(model=self.model,messages=messages,seed=seed,temperature=temperature,
                  top_p=top_p,max_tokens=max_tokens,stream=False,chat_template_kwargs={'enable_thinking':False})
        saved=self.receipts.get(key(body))
        if saved is not None:return saved
        if max_tokens==4096 or not self.allow_new:raise RuntimeError('unregistered_replay_request')
        return self.live.chat(messages,seed,temperature=temperature,top_p=top_p,max_tokens=max_tokens)
