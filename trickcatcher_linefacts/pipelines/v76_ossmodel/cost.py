"""Current-price planning against reconstructed historical requests; no API calls."""
from decimal import Decimal
import json
from .paths import CONFIG,HERE,select_model
from .context_preflight import preflight


def estimate():
    c=CONFIG['openrouter'];r=preflight();prices=c['price_per_million']
    prompt=Decimal(r['total_historical_input_tokens'])*Decimal(str(prices['prompt']))/1000000
    planned=prompt+Decimal(297*c['planning_output_tokens'])*Decimal(str(prices['completion']))/1000000
    full=prompt+Decimal(297*c['max_tokens'])*Decimal(str(prices['completion']))/1000000
    return dict(model=CONFIG['model_choice'],requests=297,estimate_usd=str(planned),full_output_cost_usd=str(full),hard_cap_usd='3',
        prompt_per_million=prices['prompt'],completion_per_million=prices['completion'],
        planning_output_tokens=c['planning_output_tokens'],scope=r['scope'])

if __name__=='__main__':
    rows={}
    for choice in CONFIG['models']:
        select_model(choice);rows[choice]=estimate()
    print(json.dumps(rows,indent=2))
