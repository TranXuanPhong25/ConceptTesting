import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from .transport import Client, request_key


class ContextFitTests(unittest.TestCase):
    def exercise(self, count, requested=4096):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with patch.dict('os.environ', {'CT_RETRIEVAL_BASE_URL':'https://fixture.ngrok-free.dev/v1'}):
            client = Client(directory.name)
        sent = []
        def http(path, payload=None, root=False):
            if path == '/tokenize':
                return {'count':count}
            sent.append(payload)
            return dict(model=client.model,choices=[dict(message={'content':'def strategy(): pass'},finish_reason='stop')],
                        usage=dict(prompt_tokens=count,completion_tokens=5,total_tokens=count+5))
        client.http = http
        return client, sent

    def test_exact_failure_fits_without_changing_messages_and_replays_once(self):
        client, sent = self.exercise(4964)
        messages = [dict(role='user',content='complete original prompt')]
        result = client.chat(messages,132773043,temperature=0,top_p=1,max_tokens=4096)
        self.assertEqual(sent[0]['max_tokens'],3228)
        self.assertEqual(sent[0]['messages'],messages)
        self.assertEqual(result['key'],request_key(sent[0]))
        self.assertEqual(client.chat(messages,132773043,temperature=0,top_p=1,max_tokens=4096),result)
        self.assertEqual(len(sent),1)
        self.assertEqual(len((client.root/'attempts.jsonl').read_text().splitlines()),1)

    def test_short_requests_keep_cap_and_identity(self):
        client, sent = self.exercise(825)
        result = client.chat([dict(role='user',content='short')],1,max_tokens=4096)
        self.assertEqual(sent[0]['max_tokens'],4096)
        self.assertEqual(result['key'],request_key(sent[0]))

    def test_exhausted_context_never_calls_completion(self):
        client, sent = self.exercise(8192)
        with self.assertRaisesRegex(RuntimeError,'context_preflight_failed'):
            client.chat([],1)
        self.assertEqual(sent,[])
        self.assertFalse((client.root/'attempts.jsonl').exists())

    def test_inherited_attempt_still_prevents_resending(self):
        client, sent = self.exercise(825)
        result = client.chat([],1)
        saved = client.root/'calls'/result['key']/'response.json'
        saved.unlink()
        with self.assertRaisesRegex(RuntimeError,'must_not_retry'):
            client.chat([],1)
        self.assertEqual(len(sent),1)
