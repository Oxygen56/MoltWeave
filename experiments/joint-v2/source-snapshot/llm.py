"""Real model calls with per-call evidence; credentials never enter receipts."""
from __future__ import annotations
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from .common import digest, write_json


class ModelClient:
    def __init__(self, output_dir: str | Path | None = None, *, model: str | None = None,
                 base_url: str | None = None, api_key: str | None = None, timeout: int = 120):
        self.model = model or os.environ.get("MOLTLOOP_MODEL") or os.environ.get("ANTHROPIC_MODEL") or "deepseek-flash"
        self.base_url = (base_url or os.environ.get("MOLTLOOP_API_BASE") or os.environ.get("OPENAI_BASE_URL")
                         or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        parsed = urllib.parse.urlparse(self.base_url)
        # DeepSeek's Anthropic integration uses a different path than chat completions.
        if parsed.hostname == "api.deepseek.com" and parsed.path.startswith("/anthropic"):
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.api_key = api_key or os.environ.get("MOLTLOOP_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Set MOLTLOOP_API_KEY. Offline tests do not require a key.")
        self.output_dir = Path(output_dir) if output_dir else None
        self.timeout = timeout
        self._lock = threading.Lock()
        self.usage: list[dict] = []

    def complete(self, messages: list[dict], max_tokens: int = 4096, purpose: str = "agent", metadata: dict | None = None) -> dict:
        body = {"model": self.model, "messages": messages, "temperature": 0,
                "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
        call_id = uuid.uuid4().hex
        receipt = {"id": call_id, "purpose": purpose, "metadata": metadata or {}, "model_requested": self.model,
                   "endpoint_host": urllib.parse.urlparse(self.base_url).hostname,
                   "request_hash": digest(body), "messages": messages, "started_at": time.time()}
        started = time.monotonic()
        for attempt in range(3):
            try:
                req = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = json.load(response)
                content = data["choices"][0]["message"].get("content") or ""
                receipt.update({"status": "completed", "model_returned": data.get("model"), "usage": data.get("usage", {}),
                                "response_id": data.get("id"), "content": content,
                                "finish_reason": data["choices"][0].get("finish_reason"), "attempts": attempt + 1})
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise ValueError("Model output must be a JSON object")
                return parsed
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError) as exc:
                # Do not expose request headers or error bodies (may contain credentials).
                receipt.update({"status": "failed", "error_type": type(exc).__name__, "attempts": attempt + 1})
                if attempt == 2:
                    raise RuntimeError(f"Model call failed ({type(exc).__name__}); see local receipt {call_id}") from None
                time.sleep(min(2 ** attempt, 4))
            finally:
                receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
                if self.output_dir:
                    write_json(self.output_dir / f"{call_id}.json", receipt)
        raise RuntimeError("unreachable")
