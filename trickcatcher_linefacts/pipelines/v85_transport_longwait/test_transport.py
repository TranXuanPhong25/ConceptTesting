import io
import tempfile
import unittest
from unittest.mock import patch
from .transport import Client


class LongWaitTests(unittest.TestCase):
    def client(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with patch.dict('os.environ',{'CT_RETRIEVAL_BASE_URL':'https://fixture.ngrok-free.dev/v1'}):
            return Client(directory.name)

    def test_longer_wait_only_for_completions_and_payload_unchanged(self):
        client = self.client()
        seen = []
        def open_response(request,timeout):
            seen.append((request.data,timeout))
            return io.BytesIO(b'{"ok":true}')
        client._open = open_response
        client.http('/models')
        client.http('/tokenize',{'messages':[]},root=True)
        client.http('/chat/completions',{'max_tokens':4096,'seed':123})
        self.assertEqual([timeout for _,timeout in seen],[25,240,900])
        self.assertEqual(seen[-1][0],b'{"max_tokens": 4096, "seed": 123}')

    def test_timeout_still_raises_after_one_attempt(self):
        client = self.client()
        with patch.object(client,'_open',side_effect=TimeoutError) as opener:
            with self.assertRaisesRegex(RuntimeError,'transport_TimeoutError'):
                client.http('/chat/completions',{})
            self.assertEqual(opener.call_count,1)
