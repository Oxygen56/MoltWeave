"""Real model calls with per-call evidence; credentials never enter receipts."""
from __future__ import annotations
import json
import ipaddress
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from .common import digest, write_json


class ModelTransportError(urllib.error.URLError):
    """A fixed transport policy rejected the request; never retry it."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            fp.close()
        raise ModelTransportError("Model redirects are forbidden")


def _validate_base_url(value: str, *, allow_http_loopback: bool) -> None:
    """Validate before provider normalization and again before each request."""
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("Invalid model endpoint URL") from None
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.fragment or parsed.query or any(ord(char) <= 32 or ord(char) == 127 for char in value)):
        raise ValueError("Model URL must not contain userinfo, query, fragment, or control characters")
    if parsed.scheme == "https":
        return
    try:
        local = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = parsed.hostname == "localhost"
    if parsed.scheme != "http" or not allow_http_loopback or not local:
        raise ValueError("HTTPS is required; HTTP loopback needs explicit test authorization")


def _resolve_configuration(*, model: str | None, base_url: str | None,
                           api_key: str | None) -> tuple[str, str, str, str]:
    """A credential may only use its own configuration group's destination."""
    default_base = "https://api.deepseek.com"
    default_model = "deepseek-flash"
    if api_key is not None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("An explicit API key must be nonempty")
        return (model or os.environ.get("MOLTWEAVE_MODEL") or default_model,
                base_url or os.environ.get("MOLTWEAVE_API_BASE") or default_base,
                api_key, "explicit")
    groups = (("MOLTWEAVE", "MOLTWEAVE_API_BASE", "MOLTWEAVE_MODEL"),
              ("OPENAI", "OPENAI_BASE_URL", "OPENAI_MODEL"),
              ("ANTHROPIC", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"))
    for prefix, base_name, model_name in groups:
        key = os.environ.get(prefix + "_API_KEY")
        if not key:
            continue
        bound_base = os.environ.get(base_name)
        if not bound_base:
            if prefix != "MOLTWEAVE":
                raise ValueError(f"{prefix}_API_KEY requires {base_name}; refusing an unbound destination")
            bound_base = default_base
        if base_url is not None and base_url.rstrip("/") != bound_base.rstrip("/"):
            raise ValueError("Endpoint override requires an explicitly supplied API key")
        return model or os.environ.get(model_name) or default_model, bound_base, key, prefix.lower()
    raise ValueError("Set MOLTWEAVE_API_KEY. Legacy keys require their matching BASE_URL.")


class ModelClient:
    def __init__(self, output_dir: str | Path | None = None, *, model: str | None = None,
                 base_url: str | None = None, api_key: str | None = None, timeout: int = 120,
                 allow_env_proxy: bool = False, allow_http_loopback: bool = False):
        if type(allow_env_proxy) is not bool or type(allow_http_loopback) is not bool:
            raise ValueError("Transport opt-ins must be explicit booleans")
        self.allow_env_proxy = allow_env_proxy
        self.allow_http_loopback = allow_http_loopback
        self.model, configured_base, self.api_key, self.credential_source = _resolve_configuration(
            model=model, base_url=base_url, api_key=api_key)
        self.base_url = configured_base.rstrip("/")
        _validate_base_url(self.base_url, allow_http_loopback=allow_http_loopback)
        parsed = urllib.parse.urlparse(self.base_url)
        # DeepSeek's Anthropic integration uses a different path than chat completions.
        if parsed.hostname == "api.deepseek.com" and parsed.path.startswith("/anthropic"):
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.output_dir = Path(output_dir) if output_dir else None
        self.timeout = timeout
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler() if allow_env_proxy else urllib.request.ProxyHandler({}),
            _NoRedirect(),
        )
        self._lock = threading.Lock()
        self.usage: list[dict] = []

    def complete(self, messages: list[dict], max_tokens: int = 4096, purpose: str = "agent", metadata: dict | None = None) -> dict:
        _validate_base_url(self.base_url, allow_http_loopback=self.allow_http_loopback)
        body = {"model": self.model, "messages": messages, "temperature": 0,
                "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
        if urllib.parse.urlparse(self.base_url).hostname == "api.deepseek.com":
            body["thinking"] = {"type": "disabled"}
        call_id = uuid.uuid4().hex
        receipt = {"id": call_id, "purpose": purpose, "metadata": metadata or {}, "model_requested": self.model,
                   "endpoint_host": urllib.parse.urlparse(self.base_url).hostname,
                   "request_hash": digest(body), "messages": messages, "started_at": time.time(),
                   "request_parameters": {k: v for k, v in body.items() if k != "messages"}, "physical_attempts": [],
                   "transport": {"redirects_allowed": False, "allow_env_proxy": self.allow_env_proxy,
                                 "allow_http_loopback": self.allow_http_loopback},
                   "credential_source": self.credential_source}
        started = time.monotonic()
        for attempt in range(3):
            attempt_record = {"number": attempt + 1, "started_at": time.time()}
            try:
                req = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key})
                with self._opener.open(req, timeout=self.timeout) as response:
                    data = json.load(response)
                content = data["choices"][0]["message"].get("content") or ""
                attempt_record.update({"status": "response", "content": content, "usage": data.get("usage", {}),
                                       "response_id": data.get("id"), "finish_reason": data["choices"][0].get("finish_reason")})
                receipt.update({"status": "completed", "model_returned": data.get("model"), "usage": data.get("usage", {}),
                                "response_id": data.get("id"), "content": content,
                                "finish_reason": data["choices"][0].get("finish_reason"), "attempts": attempt + 1})
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise ValueError("Model output must be a JSON object")
                attempt_record["status"] = "completed"
                return parsed
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError) as exc:
                # Do not expose request headers or error bodies (may contain credentials).
                receipt.update({"status": "failed", "error_type": type(exc).__name__, "attempts": attempt + 1})
                attempt_record.update({"status": "failed", "error_type": type(exc).__name__})
                if isinstance(exc, ModelTransportError) or attempt == 2:
                    raise RuntimeError(f"Model call failed ({type(exc).__name__}); see local receipt {call_id}") from None
                time.sleep(min(2 ** attempt, 4))
            finally:
                receipt["physical_attempts"].append(attempt_record)
                receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
                if self.output_dir:
                    write_json(self.output_dir / f"{call_id}.json", receipt)
        raise RuntimeError("unreachable")
