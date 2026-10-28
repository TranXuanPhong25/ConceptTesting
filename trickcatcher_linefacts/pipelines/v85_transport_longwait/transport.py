"""Allow slow completions to finish without changing token budgets or retries."""
import json
import urllib.error
import urllib.request
from ..v85_contextfit.transport import Client as ContextClient


class Client(ContextClient):
    def http(self, path, payload=None, root=False):
        request = urllib.request.Request((self._base[:-3] if root else self._base) + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'})
        # Observed 4096-token completions need237s; the old240s limit leaves no queue margin.
        timeout = 900 if path == '/chat/completions' else 240 if payload is not None else 25
        try:
            with self._open(request, timeout=timeout) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise RuntimeError('response_size_limit')
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'http_status_{exc.code}') from None
        except Exception as exc:
            raise RuntimeError('transport_' + type(exc).__name__) from None
