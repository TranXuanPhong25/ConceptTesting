"""v11 chat contract over v76's reserved OpenRouter client; one global ledger."""
import hashlib
import json
import time
from .paths import CONFIG


def user_feedback(messages):
    """Flatten visible retry history into user content; never assistant turns."""
    if [m['role'] for m in messages] == ['system','user']:
        return messages
    if not messages or messages[0]['role'] != 'system':
        raise ValueError('system_prompt_required')
    body = messages[1]['content']
    for m in messages[2:]:
        label = 'Previous proposed strategy' if m['role']=='assistant' else 'Execution feedback / correction'
        body += '\n\n' + label + ':\n' + m['content']
    return [messages[0],dict(role='user',content=body)]


class Client:
    model=CONFIG['openrouter']['model']
    def __init__(self,transport): self.transport=transport; self.model=transport.model
    def chat(self,messages,seed,**legacy):
        messages=user_feedback(messages)
        # Sampling/reasoning are one registered package for every arm/stage.
        # v11 strategy-only local sampling kwargs are deliberately superseded.
        params=dict(CONFIG['openrouter']['params'],model=self.model,max_tokens=CONFIG['openrouter']['max_tokens'],seed=seed)
        key=hashlib.sha256(json.dumps(dict(messages=messages,params=params),sort_keys=True).encode()).hexdigest()
        start=time.perf_counter()
        r=self.transport.complete(dict(slot='chat/'+key,messages=messages,seed=seed))
        return dict(text=r['text'],key=key,params=params,n_in=r['input_tokens'],n_out=r['output_tokens'],
                    seconds=time.perf_counter()-start,cost_usd=r['cost_usd'],transport_attempts=r['attempts'],cache_hit=False)
