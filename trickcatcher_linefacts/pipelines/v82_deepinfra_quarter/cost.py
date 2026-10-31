"""Two-arm K1 planning, not a completion guarantee under hard cap."""
from .paths import CONFIG


def estimate(model=None):
    c=CONFIG['openrouter'];p=c['price_per_million']['prompt'];q=c['price_per_million']['completion']
    calls=28*2*8
    return dict(tasks=28,K=1,arms=CONFIG['combined']['arms'],max_logical_calls=calls,
                estimate_usd=calls*(4096*p+32768*q)/1e6,
                full_output_cost_usd=calls*(4096*p+CONFIG['openrouter']['max_tokens']*q)/1e6,
                hard_cap_usd=c['hard_max_usd'],dataset_caps_usd={'humaneval':c['hard_max_usd']},
                scope='generation only; CPU ref scoring, no paid judge;429attempts retain separate reserves')
