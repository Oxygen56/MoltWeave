"""Actual loopback HTTP requests with synthetic replies; no real model claims."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from moltweave.common import digest
from moltweave.llm import ModelClient


class ScriptedProvider:
    """Return authored provider envelopes, errors, or redirects in request order."""
    def __init__(self, replies):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                number = len(owner.requests)
                owner.requests.append(body)
                reply = replies[min(number, len(replies) - 1)]
                status = reply.get("status", 200)
                if "location" in reply:
                    self.send_response(status)
                    self.send_header("Location", reply["location"])
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if "raw_body" in reply:
                    payload = reply["raw_body"]
                elif status != 200:
                    payload = b'{"error":"authored synthetic transport failure"}'
                else:
                    payload = json.dumps({"id": f"synthetic-response-{number + 1}",
                        "model": "synthetic-json-repair-model", "choices": [{"message": {
                            "content": reply["content"]}, "finish_reason": reply.get("finish_reason", "stop")}],
                        "usage": reply.get("usage", {"prompt_tokens": number + 2,
                            "completion_tokens": number + 3, "total_tokens": 2 * number + 5})}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                # If a redirect ever leaks through, make it visible to the test.
                owner.requests.append({"unexpected_method": "GET"})
                self.send_response(500)
                self.send_header("Content-Length", "0")
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


class ModelJSONRepairTests(unittest.TestCase):
    synthetic_key = "synthetic-json-repair-key-not-a-provider-key"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # This checks retry requests, not wall-clock backoff behavior.
        sleeper = patch("moltweave.llm.time.sleep", return_value=None)
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.messages = [{"role": "system", "content": "Preserve task, permission and evaluation rules."},
                         {"role": "user", "content": [{"type": "text", "text": "Author one synthetic plan as JSON."}]}]

    def provider(self, replies):
        result = ScriptedProvider(replies)
        self.addCleanup(result.close)
        return result

    def client(self, provider):
        return ModelClient(Path(self.temp.name) / "calls", model="synthetic-json-repair-model",
            api_key=self.synthetic_key, base_url=provider.url, allow_http_loopback=True, timeout=2)

    def receipt(self):
        paths = list((Path(self.temp.name) / "calls").glob("*.json"))
        self.assertEqual(len(paths), 1)
        text = paths[0].read_text()
        self.assertNotIn(self.synthetic_key, text)
        return json.loads(text)

    def assert_request_evidence(self, receipt, provider):
        self.assertEqual(len(receipt["physical_attempts"]), len(provider.requests))
        for attempt, sent in zip(receipt["physical_attempts"], provider.requests):
            self.assertEqual(attempt["messages"], sent["messages"])
            self.assertEqual(attempt["request_parameters"], {k: v for k, v in sent.items() if k != "messages"})
            self.assertEqual(attempt["request_hash"], digest(sent))
        self.assertEqual(receipt["request_hash"], digest(provider.requests[0]))
        self.assertEqual(receipt["messages"], provider.requests[0]["messages"])

    def test_malformed_response_is_sent_raw_to_second_real_http_request(self):
        malformed = '{"plan":{"action":"retain","items":["一","二"]}'
        valid = {"plan": {"action": "retain", "items": ["一", "二"]}}
        provider = self.provider([{"content": malformed, "finish_reason": "stop"},
                                  {"content": json.dumps(valid, ensure_ascii=False)}])
        original = deepcopy(self.messages)
        output = self.client(provider).complete(self.messages, max_tokens=777, repair_json=True,
                                                purpose="synthetic_json_transport_test")
        self.assertEqual(output, valid)
        self.assertEqual(self.messages, original)
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(provider.requests[1]["messages"][:len(original)], original)
        repair = provider.requests[1]["messages"][len(original):]
        self.assertEqual(repair[0], {"role": "assistant", "content": malformed})
        self.assertEqual(repair[1]["role"], "user")
        self.assertIn("JSONDecodeError", repair[1]["content"])
        self.assertIn("original task", repair[1]["content"])
        self.assertIn("permissions", repair[1]["content"])
        self.assertIn("evaluation rules", repair[1]["content"])
        self.assertIn("entire original proposal", repair[1]["content"])
        receipt = self.receipt()
        self.assert_request_evidence(receipt, provider)
        first, second = receipt["physical_attempts"]
        self.assertNotEqual(first["request_hash"], second["request_hash"])
        self.assertEqual(first["content"], malformed)
        self.assertEqual(first["usage"]["total_tokens"], 5)
        self.assertEqual(second["usage"]["total_tokens"], 7)
        self.assertEqual(first["finish_reason"], "stop")
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["error_type"], "JSONDecodeError")
        self.assertEqual(first["next_retry"], "model_json_syntax_repair")
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["request_parameters"]["max_tokens"], 777)
        self.assertEqual(first["request_parameters"], second["request_parameters"])
        self.messages[1]["content"][0]["text"] = "caller changed later"
        self.assertEqual(receipt["messages"], original)

    def test_default_false_retries_identical_request_without_repair_turns(self):
        provider = self.provider([{"content": '{"ok":'}, {"content": '{"ok":true}'}])
        self.assertEqual(self.client(provider).complete(self.messages), {"ok": True})
        self.assertEqual(provider.requests[0], provider.requests[1])
        receipt = self.receipt()
        self.assertFalse(receipt["repair_json"])
        self.assert_request_evidence(receipt, provider)
        first, second = receipt["physical_attempts"]
        self.assertEqual(first["request_hash"], second["request_hash"])
        self.assertNotIn("next_retry", first)

    def test_nonobject_json_uses_shape_feedback_without_local_conversion(self):
        provider = self.provider([{"content": '["retain-original-plan"]'},
                                  {"content": '{"plan":["retain-original-plan"]}'}])
        result = self.client(provider).complete(self.messages, repair_json=True)
        self.assertEqual(result, {"plan": ["retain-original-plan"]})
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(provider.requests[1]["messages"][-2]["content"], '["retain-original-plan"]')
        receipt = self.receipt()
        first = receipt["physical_attempts"][0]
        self.assertEqual(first["json_error"]["error_type"], "JSONShapeError")
        self.assertEqual(first["json_error"]["parsed_type"], "list")
        self.assertEqual(first["error_type"], "ValueError")

    def test_three_invalid_responses_abort_and_preserve_each_raw_failure(self):
        invalid = ['{"plan":', '{"plan":{"action":}', '{"plan":{"action":"retain"}']
        provider = self.provider([{"content": content} for content in invalid])
        with self.assertRaisesRegex(RuntimeError, "JSONDecodeError"):
            self.client(provider).complete(self.messages, repair_json=True)
        self.assertEqual(len(provider.requests), 3)
        self.assertEqual([len(request["messages"]) for request in provider.requests], [2, 4, 6])
        receipt = self.receipt()
        self.assert_request_evidence(receipt, provider)
        attempts = receipt["physical_attempts"]
        self.assertEqual([attempt["content"] for attempt in attempts], invalid)
        self.assertEqual([attempt["status"] for attempt in attempts], ["failed"] * 3)
        self.assertEqual([attempt["usage"]["total_tokens"] for attempt in attempts], [5, 7, 9])
        self.assertEqual(len({attempt["request_hash"] for attempt in attempts}), 3)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["attempts"], 3)

    def test_network_error_with_repair_enabled_does_not_change_request(self):
        provider = self.provider([{"status": 503}, {"content": '{"ok":true}'}])
        self.assertEqual(self.client(provider).complete(self.messages, repair_json=True), {"ok": True})
        self.assertEqual(provider.requests[0], provider.requests[1])
        receipt = self.receipt()
        self.assert_request_evidence(receipt, provider)
        self.assertEqual(receipt["physical_attempts"][0]["error_type"], "HTTPError")
        self.assertNotIn("json_error", receipt["physical_attempts"][0])

    def test_network_retry_after_syntax_repair_reuses_that_repaired_request(self):
        provider = self.provider([{"content": '{"ok":'}, {"status": 503}, {"content": '{"ok":true}'}])
        self.assertEqual(self.client(provider).complete(self.messages, repair_json=True), {"ok": True})
        self.assertNotEqual(provider.requests[0], provider.requests[1])
        self.assertEqual(provider.requests[1], provider.requests[2])
        receipt = self.receipt()
        self.assert_request_evidence(receipt, provider)
        self.assertNotIn("json_error", receipt["physical_attempts"][1])
        self.assertEqual(receipt["physical_attempts"][0]["content"], '{"ok":')

    def test_invalid_provider_envelope_is_not_treated_as_model_content(self):
        provider = self.provider([{"raw_body": b"invalid-provider-envelope"}, {"content": '{"ok":true}'}])
        self.assertEqual(self.client(provider).complete(self.messages, repair_json=True), {"ok": True})
        self.assertEqual(provider.requests[0], provider.requests[1])
        first = self.receipt()["physical_attempts"][0]
        self.assertEqual(first["error_type"], "JSONDecodeError")
        self.assertNotIn("json_error", first)
        self.assertNotIn("content", first)

    def test_redirect_is_fatal_even_when_json_repair_was_requested(self):
        sink = self.provider([{"content": '{"ok":true}'}])
        source = self.provider([{"status": 302, "location": sink.url.replace("127.0.0.1", "localhost") + "/sink"}])
        with self.assertRaisesRegex(RuntimeError, "ModelTransportError"):
            self.client(source).complete(self.messages, repair_json=True)
        self.assertEqual(len(source.requests), 1)
        self.assertEqual(sink.requests, [])
        receipt = self.receipt()
        self.assertEqual(receipt["attempts"], 1)
        self.assertEqual(receipt["physical_attempts"][0]["error_type"], "ModelTransportError")
        self.assertNotIn("next_retry", receipt["physical_attempts"][0])

    def test_json_repair_opt_in_requires_actual_bool_before_network(self):
        provider = self.provider([{"content": '{"ok":true}'}])
        client = self.client(provider)
        for value in ("false", 1, 0, None, []):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError):
                client.complete(self.messages, repair_json=value)
        self.assertEqual(provider.requests, [])
        self.assertEqual(list((Path(self.temp.name) / "calls").glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
