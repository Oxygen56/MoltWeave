"""Local synthetic transport regressions; never use a real API credential."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from moltweave.llm import ModelClient, ModelTransportError, _NoRedirect


class _LocalServer:
    def __init__(self, responder):
        self.requests = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                owner.requests.append({"method": "POST", "authorization": self.headers.get("Authorization"), "body": body})
                responder(self)
            def do_GET(self):
                owner.requests.append({"method": "GET", "authorization": self.headers.get("Authorization")})
                responder(self)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
    def close(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


def _json_response(handler):
    payload = json.dumps({"id": "synthetic-response", "model": "synthetic-transport-model",
        "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


class ModelTransportTests(unittest.TestCase):
    synthetic_key = "synthetic-transport-key-not-a-provider-key"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def client(self, **changes):
        return ModelClient(Path(self.temp.name) / "calls", **{
            "model": "synthetic-transport-model", "base_url": "https://model.example.invalid",
            "api_key": self.synthetic_key, "timeout": 2, **changes})

    def test_two_servers_redirect_never_forwards_authorization(self):
        sink = _LocalServer(_json_response)
        self.addCleanup(sink.close)
        def redirect(handler):
            handler.send_response(302)
            handler.send_header("Location", sink.url.replace("127.0.0.1", "localhost") + "/sink")
            handler.send_header("Content-Length", "0")
            handler.end_headers()
        source = _LocalServer(redirect)
        self.addCleanup(source.close)
        client = self.client(base_url=source.url, allow_http_loopback=True)
        with self.assertRaisesRegex(RuntimeError, "ModelTransportError"):
            client.complete([{"role": "user", "content": "Synthetic public transport check"}])
        self.assertEqual(len(source.requests), 1)
        self.assertEqual(source.requests[0]["authorization"], "Bearer " + self.synthetic_key)
        self.assertEqual(sink.requests, [])
        receipts = list((Path(self.temp.name) / "calls").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        receipt_text = receipts[0].read_text()
        self.assertNotIn(self.synthetic_key, receipt_text)
        receipt = json.loads(receipt_text)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["attempts"], 1)
        self.assertFalse(receipt["transport"]["redirects_allowed"])

    def test_https_downgrade_redirect_is_denied_before_a_new_request(self):
        # Pure handler check: no TLS fixture and no network request are involved.
        request = urllib.request.Request("https://approved.example.invalid/chat/completions",
            data=b"{}", headers={"Authorization": "Bearer " + self.synthetic_key})
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code), self.assertRaises(ModelTransportError):
                _NoRedirect().redirect_request(request, None, code, "redirect", {},
                                               "http://unapproved.example.invalid/sink")

    def test_https_required_and_http_flag_only_allows_loopback(self):
        for url in ("http://model.example.invalid", "ftp://model.example.invalid", "file:///tmp/model", "https:///missing-host"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.client(base_url=url, allow_http_loopback=True)
        with self.assertRaises(ValueError):
            self.client(base_url="http://127.0.0.1:8123")
        self.assertTrue(self.client(base_url="http://127.0.0.1:8123", allow_http_loopback=True).allow_http_loopback)

    def test_userinfo_fragment_query_and_control_characters_rejected(self):
        for url in ("https://synthetic-user:synthetic-password@model.example.invalid",
                    "https://model.example.invalid/#fragment", "https://model.example.invalid/?secret=value",
                    "https://api.deepseek.com/anthropic#must-not-be-normalized-away",
                    "https://model.example.invalid/\npath"):
            with self.subTest(category="invalid-url"), self.assertRaises(ValueError):
                self.client(base_url=url)

    def test_environment_proxy_disabled_by_default_and_only_explicitly_enabled(self):
        proxy = _LocalServer(_json_response)
        source = _LocalServer(_json_response)
        self.addCleanup(proxy.close)
        self.addCleanup(source.close)
        with patch.dict("os.environ", {"https_proxy": proxy.url, "HTTPS_PROXY": proxy.url,
                                      "http_proxy": proxy.url, "HTTP_PROXY": proxy.url,
                                      "no_proxy": "", "NO_PROXY": ""}):
            default = self.client()
            proxies = [h for h in default._opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            self.assertTrue(all(not h.proxies for h in proxies))
            self.assertEqual(self.client(base_url=source.url, allow_http_loopback=True).complete(
                [{"role": "user", "content": "Synthetic direct-transport check"}]), {"ok": True})
            self.assertEqual(len(source.requests), 1)
            self.assertEqual(proxy.requests, [])
            explicit = self.client(allow_env_proxy=True)
            enabled = [h for h in explicit._opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            self.assertTrue(any("https" in h.proxies for h in enabled))
        with self.assertRaises(ValueError):
            self.client(allow_env_proxy="false")

    def test_explicit_local_http_request_succeeds_with_nonsecret_receipt(self):
        source = _LocalServer(_json_response)
        self.addCleanup(source.close)
        result = self.client(base_url=source.url, allow_http_loopback=True).complete(
            [{"role": "user", "content": "Synthetic public JSON request"}])
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(source.requests), 1)
        receipts = list((Path(self.temp.name) / "calls").glob("*.json"))
        self.assertNotIn(self.synthetic_key, receipts[0].read_text())

    def test_mutating_endpoint_after_construction_cannot_bypass_https_requirement(self):
        client = self.client()
        client.base_url = "http://model.example.invalid"
        with self.assertRaises(ValueError):
            client.complete([{"role": "user", "content": "Synthetic"}])

    def test_legacy_key_without_its_own_base_is_rejected_before_transport(self):
        for prefix, other_base in (("OPENAI", "ANTHROPIC_BASE_URL"), ("ANTHROPIC", "OPENAI_BASE_URL")):
            with self.subTest(group=prefix), patch.dict("os.environ", {
                    prefix + "_API_KEY": self.synthetic_key, other_base: "https://wrong-group.example.invalid",
                    "MOLTWEAVE_API_BASE": "https://another-wrong-group.example.invalid"}, clear=True), \
                    patch("moltweave.llm.urllib.request.build_opener") as opener:
                with self.assertRaisesRegex(ValueError, "requires"):
                    ModelClient()
                opener.assert_not_called()

    def test_environment_groups_never_mix_credentials_destinations_or_models(self):
        all_groups = {"MOLTWEAVE_API_KEY": "synthetic-molt-key", "MOLTWEAVE_API_BASE": "https://molt.example.invalid",
                      "MOLTWEAVE_MODEL": "molt-model", "OPENAI_API_KEY": "synthetic-openai-key",
                      "OPENAI_BASE_URL": "https://openai.example.invalid", "OPENAI_MODEL": "openai-model",
                      "ANTHROPIC_API_KEY": "synthetic-anthropic-key",
                      "ANTHROPIC_BASE_URL": "https://anthropic.example.invalid", "ANTHROPIC_MODEL": "anthropic-model"}
        for prefix, expected_host, expected_model in (("MOLTWEAVE", "molt", "molt"),
                                                     ("OPENAI", "openai", "openai"),
                                                     ("ANTHROPIC", "anthropic", "anthropic")):
            with self.subTest(group=prefix), patch.dict("os.environ", all_groups, clear=True):
                client = ModelClient()
                self.assertEqual(client.api_key, all_groups[prefix + "_API_KEY"])
                self.assertEqual(client.base_url, f"https://{expected_host}.example.invalid")
                self.assertEqual(client.model, expected_model + "-model")
            all_groups.pop(prefix + "_API_KEY")
        with patch.dict("os.environ", {"MOLTWEAVE_API_KEY": self.synthetic_key,
                       "OPENAI_BASE_URL": "https://wrong-group.example.invalid",
                       "ANTHROPIC_MODEL": "wrong-model"}, clear=True):
            client = ModelClient()
            self.assertEqual(client.base_url, "https://api.deepseek.com")
            self.assertEqual(client.model, "deepseek-flash")

    def test_each_legacy_pair_can_call_its_explicit_loopback_destination(self):
        source = _LocalServer(_json_response)
        self.addCleanup(source.close)
        for prefix in ("OPENAI", "ANTHROPIC"):
            with self.subTest(group=prefix), patch.dict("os.environ", {
                    prefix + "_API_KEY": self.synthetic_key, prefix + "_BASE_URL": source.url,
                    prefix + "_MODEL": "synthetic-paired-model"}, clear=True):
                client = ModelClient(Path(self.temp.name) / prefix, allow_http_loopback=True)
                self.assertEqual(client.complete([{"role": "user", "content": "Synthetic pair check"}]), {"ok": True})
                self.assertEqual(client.credential_source, prefix.lower())
                self.assertEqual(json.loads(source.requests[-1]["body"])["model"], "synthetic-paired-model")
        self.assertEqual(len(source.requests), 2)

    def test_environment_credential_cannot_be_rebound_without_explicit_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": self.synthetic_key,
                       "ANTHROPIC_BASE_URL": "https://approved.example.invalid"}, clear=True):
            with self.assertRaisesRegex(ValueError, "explicitly supplied"):
                ModelClient(base_url="https://unapproved.example.invalid")
            client = ModelClient(base_url="https://operator.example.invalid", api_key=self.synthetic_key)
            self.assertEqual(client.base_url, "https://operator.example.invalid")
            self.assertEqual(client.credential_source, "explicit")


if __name__ == "__main__":
    unittest.main()
