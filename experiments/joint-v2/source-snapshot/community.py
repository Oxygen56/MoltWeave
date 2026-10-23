"""Opt-in, tenant-bound local HTTP trace inbox; no third-party services.

The inbox is deliberately not an execution/replay API. Uploaded text cannot
issue approvals or acquire tools. Content is stored locally with owner-only file
permissions; this stdlib implementation does not claim encryption at rest.
"""

from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .governance import _atomic_json, _file_lock, stable_hash


class TraceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class TraceHTTPError(TraceError):
    """Server rejection exposed without including authorization credentials."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise TraceHTTPError("trace client refuses redirects", code)


_CREDENTIAL_KEYS = frozenset({"authorization", "proxyauthorization", "apikey", "apisecret",
    "accesstoken", "refreshtoken", "idtoken", "password", "passwd", "secret", "clientsecret",
    "privatekey", "cookie", "setcookie", "credentials", "bearertoken"})
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=:-]+")
_API_SECRET = re.compile(r"\b(?:sk|rk|pk)-(?:live-|test-|proj-)?[A-Za-z0-9_-]{12,}\b")
_ASSIGNMENT = re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|password|client[_-]?secret)"
                         r"(\s*[=:]\s*)[^\s,;\"']+")


def filter_credentials(value: Any) -> tuple[Any, list[str]]:
    """Best-effort credential filtering, preserving full noncredential content.

    This is not a general PII detector. Arbitrary/encoded credentials cannot be
    reliably recognized; users must inspect the upload preview too.
    """
    redacted: list[str] = []

    def visit(item: Any, path: str) -> Any:
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                if not isinstance(key, str):
                    raise TraceError("JSON object keys must be strings")
                location = f"{path}.{key}" if path else key
                normalized = re.sub(r"[^a-z0-9]", "", key.lower())
                if normalized in _CREDENTIAL_KEYS:
                    result[key] = "[CREDENTIAL REDACTED]"
                    redacted.append(location)
                else:
                    result[key] = visit(child, location)
            return result
        if isinstance(item, list):
            return [visit(child, f"{path}[{index}]") for index, child in enumerate(item)]
        if isinstance(item, str):
            result = _BEARER.sub("Bearer [CREDENTIAL REDACTED]", item)
            result = _API_SECRET.sub("[CREDENTIAL REDACTED]", result)
            result = _ASSIGNMENT.sub(lambda match: match[1] + match[2] + "[CREDENTIAL REDACTED]", result)
            if result != item:
                redacted.append(path or "$")
            return result
        if item is None or isinstance(item, (bool, int)):
            return item
        if isinstance(item, float) and math.isfinite(item):
            return item
        raise TraceError("trace must contain finite JSON values only")

    return visit(value, ""), redacted


class TraceStore:
    """Private per-user traces, separate personal/general consent and lineage."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._index = self.path / "index.json"
        self._lock_path = self.path / ".trace.lock"
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        if not self._index.exists():
            return {"version": 1, "clients": {}, "consents": {}, "traces": {}, "derivatives": {}}
        return json.loads(self._index.read_text(encoding="utf-8"))

    @staticmethod
    def _authenticate(state: dict[str, Any], token: str) -> dict[str, str]:
        if not isinstance(token, str) or not token:
            raise TraceError("authentication required", 401)
        binding = state["clients"].get(hashlib.sha256(token.encode()).hexdigest())
        if binding is None or binding.get("revoked"):
            raise TraceError("authentication failed", 401)
        return binding

    @staticmethod
    def _same(binding: Mapping[str, Any], record: Mapping[str, Any]) -> bool:
        return (binding["tenant_id"], binding["user_id"]) == (record["tenant_id"], record["user_id"])

    @staticmethod
    def _scope(binding: Mapping[str, Any]) -> str:
        return stable_hash({"tenant_id": binding["tenant_id"], "user_id": binding["user_id"]})

    def _write_payload(self, binding: Mapping[str, Any], kind: str, identifier: str, content: Any) -> str:
        relative = Path("private") / self._scope(binding) / kind / f"{identifier}.json"
        _atomic_json(self.path / relative, content)
        return str(relative)

    def register_client(self, token: str, *, tenant_id: str, user_id: str) -> None:
        """Trusted setup API. HTTP clients cannot choose or register their tenant."""
        if not isinstance(token, str) or len(token) < 16:
            raise ValueError("use a random bearer token of at least 16 characters")
        if not all(isinstance(v, str) and v.strip() for v in (tenant_id, user_id)):
            raise ValueError("tenant_id and user_id must be nonempty")
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = {"tenant_id": tenant_id, "user_id": user_id, "revoked": False}
            if digest in state["clients"] and state["clients"][digest] != binding:
                raise TraceError("credential already bound; cannot rebind it", 409)
            state["clients"][digest] = binding
            _atomic_json(self._index, state)

    def revoke_client(self, token: str) -> None:
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            self._authenticate(state, token)["revoked"] = True
            _atomic_json(self._index, state)

    def grant_consent(self, token: str, *, session_ids: list[str], full_trace: bool,
                      personal_evolution: bool = False, general_evolution: bool = False,
                      expires_at: float, retention_days: int) -> dict[str, Any]:
        if not session_ids or not isinstance(session_ids, list) or any(
                not isinstance(item, str) or not item.strip() for item in session_ids):
            raise TraceError("explicit nonempty session_ids required; no wildcard consent")
        if any(item == "*" for item in session_ids):
            raise TraceError("wildcard session consent is not supported")
        if any(type(v) is not bool for v in (full_trace, personal_evolution, general_evolution)):
            raise TraceError("consent flags must be explicit booleans")
        if not full_trace:
            raise TraceError("this endpoint requires explicit full_trace authorization")
        if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)) or not math.isfinite(expires_at) or expires_at <= time.time():
            raise TraceError("expires_at must be a future Unix timestamp")
        if type(retention_days) is not int or not 1 <= retention_days <= 3650:
            raise TraceError("retention_days must be explicitly set between 1 and 3650")
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            consent_id = "consent_" + secrets.token_hex(16)
            consent = {"consent_id": consent_id, "tenant_id": binding["tenant_id"],
                "user_id": binding["user_id"], "session_ids": sorted(set(session_ids)),
                "full_trace": full_trace, "personal_evolution": personal_evolution,
                "general_evolution": general_evolution, "expires_at": expires_at,
                "retention_days": retention_days, "created_at": time.time(), "revoked": False,
                "credential_filter": "fixed-best-effort-v1"}
            state["consents"][consent_id] = consent
            _atomic_json(self._index, state)
            return dict(consent)

    def _consent(self, state: dict[str, Any], binding: Mapping[str, Any], consent_id: str,
                 purpose: str | None = None) -> dict[str, Any]:
        consent = state["consents"].get(consent_id)
        if not consent or not self._same(binding, consent):
            raise TraceError("consent not found", 404)
        if consent["revoked"] or consent["expires_at"] <= time.time():
            raise TraceError("consent withdrawn or expired", 410)
        if purpose not in (None, "personal", "general"):
            raise TraceError("purpose must be personal or general")
        if purpose and not consent[purpose + "_evolution"]:
            raise TraceError(f"{purpose} evolution is not authorized", 403)
        return consent

    def ingest(self, token: str, *, consent_id: str, trace: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(trace, Mapping):
            raise TraceError("trace must be a JSON object")
        filtered, redactions = filter_credentials(dict(trace))
        session_id = filtered.get("session_id")
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            consent = self._consent(state, binding, consent_id)
            for key in ("tenant_id", "user_id"):
                if key in filtered and filtered[key] != binding[key]:
                    raise TraceError("trace identity conflicts with authenticated credential", 403)
            if session_id not in consent["session_ids"]:
                raise TraceError("session is outside the consent scope", 403)
            trace_id = "trace_" + secrets.token_hex(16)
            created_at = time.time()
            payload = {"trace_id": trace_id, "tenant_id": binding["tenant_id"],
                       "user_id": binding["user_id"], "consent_id": consent_id,
                       "trace": filtered, "credential_redactions": redactions}
            relative = self._write_payload(binding, "raw", trace_id, payload)
            record = {"trace_id": trace_id, "tenant_id": binding["tenant_id"],
                      "user_id": binding["user_id"], "session_id": session_id,
                      "consent_id": consent_id, "created_at": created_at,
                      "expires_at": created_at + consent["retention_days"] * 86400,
                      "payload_path": relative, "payload_hash": stable_hash(payload), "revoked": False}
            state["traces"][trace_id] = record
            _atomic_json(self._index, state)
            return {"trace_id": trace_id, "tenant_id": binding["tenant_id"],
                    "user_id": binding["user_id"], "credential_redactions": redactions,
                    "payload_hash": record["payload_hash"], "expires_at": record["expires_at"]}

    def _trace_record(self, state: dict[str, Any], binding: Mapping[str, Any], trace_id: str,
                      purpose: str | None = None) -> dict[str, Any]:
        record = state["traces"].get(trace_id)
        if not record or not self._same(binding, record):
            raise TraceError("trace not found", 404)
        if record["revoked"] or record["expires_at"] <= time.time():
            raise TraceError("trace withdrawn or expired", 410)
        self._consent(state, binding, record["consent_id"], purpose)
        return record

    def get_trace(self, token: str, trace_id: str, *, purpose: str | None = None) -> dict[str, Any]:
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            record = self._trace_record(state, binding, trace_id, purpose)
            return json.loads((self.path / record["payload_path"]).read_text(encoding="utf-8"))

    def eligible_traces(self, token: str, *, purpose: str) -> list[str]:
        if purpose not in ("personal", "general"):
            raise TraceError("purpose must be personal or general")
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            result = []
            for identifier in state["traces"]:
                try:
                    self._trace_record(state, binding, identifier, purpose)
                except TraceError:
                    continue
                result.append(identifier)
            return result

    def register_derivative(self, token: str, *, source_ids: list[str], kind: str,
                            content: Any, purpose: str = "personal") -> dict[str, Any]:
        if not source_ids or not isinstance(source_ids, list) or not all(isinstance(x, str) for x in source_ids):
            raise TraceError("explicit source_ids required")
        if not isinstance(kind, str) or not kind.strip():
            raise TraceError("derivative kind required")
        if purpose not in ("personal", "general"):
            raise TraceError("purpose must be personal or general")
        filtered, redactions = filter_credentials(content)
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            ancestors: set[str] = set()
            for identifier in source_ids:
                if identifier in state["traces"]:
                    self._trace_record(state, binding, identifier, purpose)
                    ancestors.add(identifier)
                else:
                    source = state["derivatives"].get(identifier)
                    if not source or not self._same(binding, source):
                        raise TraceError("source not found", 404)
                    if source["revoked"]:
                        raise TraceError("source withdrawn", 410)
                    # A general-authorized source cannot launder a personal-only ancestor.
                    for trace_id in source["ancestor_trace_ids"]:
                        self._trace_record(state, binding, trace_id, purpose)
                        ancestors.add(trace_id)
            identifier = "derived_" + secrets.token_hex(16)
            relative = self._write_payload(binding, "derived", identifier, filtered)
            record = {"derivative_id": identifier, "tenant_id": binding["tenant_id"],
                      "user_id": binding["user_id"], "source_ids": sorted(set(source_ids)),
                      "ancestor_trace_ids": sorted(ancestors), "kind": kind, "purpose": purpose,
                      "created_at": time.time(), "payload_path": relative,
                      "payload_hash": stable_hash(filtered), "credential_redactions": redactions,
                      "revoked": False}
            state["derivatives"][identifier] = record
            _atomic_json(self._index, state)
            return dict(record)

    def get_derivative(self, token: str, identifier: str) -> dict[str, Any]:
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            record = state["derivatives"].get(identifier)
            if not record or not self._same(binding, record):
                raise TraceError("derivative not found", 404)
            if record["revoked"]:
                raise TraceError("derivative withdrawn", 410)
            for trace_id in record["ancestor_trace_ids"]:
                self._trace_record(state, binding, trace_id, record["purpose"])
            return {"metadata": dict(record), "content": json.loads(
                (self.path / record["payload_path"]).read_text(encoding="utf-8"))}

    def _revoke_traces(self, state: dict[str, Any], trace_ids: set[str], reason: str) -> list[str]:
        for identifier in trace_ids:
            record = state["traces"][identifier]
            record["revoked"] = True
            record["revocation_reason"] = reason
            (self.path / record["payload_path"]).unlink(missing_ok=True)
        affected = []
        for identifier, record in state["derivatives"].items():
            if not record["revoked"] and trace_ids.intersection(record["ancestor_trace_ids"]):
                record["revoked"] = True
                record["revocation_reason"] = reason
                (self.path / record["payload_path"]).unlink(missing_ok=True)
                affected.append(identifier)
        return sorted(affected)

    def withdraw(self, token: str, *, consent_id: str) -> dict[str, Any]:
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            binding = self._authenticate(state, token)
            consent = state["consents"].get(consent_id)
            if not consent or not self._same(binding, consent):
                raise TraceError("consent not found", 404)
            consent["revoked"] = True
            consent["withdrawn_at"] = time.time()
            identifiers = {key for key, record in state["traces"].items()
                           if record["consent_id"] == consent_id and not record["revoked"]}
            affected = self._revoke_traces(state, identifiers, "consent withdrawn")
            _atomic_json(self._index, state)
            return {"consent_id": consent_id, "withdrawn": True, "traces": sorted(identifiers),
                    "affected_derivatives": affected,
                    "requires_adopted_version_review": bool(affected)}

    def purge_expired(self, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            identifiers = {key for key, record in state["traces"].items()
                if not record["revoked"] and (record["expires_at"] <= now or
                    state["consents"][record["consent_id"]]["expires_at"] <= now)}
            affected = self._revoke_traces(state, identifiers, "retention or consent expired")
            if identifiers:
                _atomic_json(self._index, state)
            return {"purged_traces": sorted(identifiers), "affected_derivatives": affected}


class TraceHTTPServer(ThreadingHTTPServer):
    """Loopback-only self-hosted HTTP endpoint. No execution or owner-issue route."""

    daemon_threads = True

    def __init__(self, store: TraceStore, host: str = "127.0.0.1", port: int = 0, *,
                 max_body_bytes: int = 16 * 1024 * 1024):
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        if not loopback:
            raise ValueError("local HTTP server must bind to loopback; no public/cloud deployment")
        self.store = store
        self.max_body_bytes = max_body_bytes
        self._worker: threading.Thread | None = None
        super().__init__((host, port), _TraceHandler)

    @property
    def url(self) -> str:
        return f"http://{self.server_address[0]}:{self.server_address[1]}"

    def start(self) -> "TraceHTTPServer":
        if self._worker is None:
            self._worker = threading.Thread(target=self.serve_forever, daemon=True)
            self._worker.start()
        return self

    def close(self) -> None:
        if self._worker is not None:
            self.shutdown()
            self._worker.join(timeout=5)
            self._worker = None
        self.server_close()

    def __enter__(self) -> "TraceHTTPServer":
        return self.start()

    def __exit__(self, *_: Any) -> None:
        self.close()

    def service_actions(self) -> None:
        self.store.purge_expired()


class _TraceHandler(BaseHTTPRequestHandler):
    server: TraceHTTPServer

    def log_message(self, *_: Any) -> None:
        # Do not put paths, request data, or authorization into access logs.
        pass

    def _reply(self, status: int, value: Any) -> None:
        content = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _token(self) -> str:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or not header[7:]:
            raise TraceError("bearer authentication required", 401)
        return header[7:]

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise TraceError("valid Content-Length required") from None
        if length <= 0:
            raise TraceError("JSON request body required")
        if length > self.server.max_body_bytes:
            raise TraceError("trace exceeds configured body limit; nothing was truncated", 413)
        try:
            value = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError, RecursionError):
            raise TraceError("invalid finite JSON") from None
        if not isinstance(value, dict):
            raise TraceError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:
        try:
            path = urlsplit(self.path).path
            if path == "/health":
                self._reply(200, {"ok": True, "local_only": True})
                return
            token = self._token()
            if path.startswith("/v1/traces/"):
                result = self.server.store.get_trace(token, path.rsplit("/", 1)[1])
            elif path.startswith("/v1/derivatives/"):
                result = self.server.store.get_derivative(token, path.rsplit("/", 1)[1])
            else:
                raise TraceError("route not found", 404)
            self._reply(200, result)
        except TraceError as error:
            self._reply(error.status, {"error": str(error)})

    def do_POST(self) -> None:
        try:
            token, body = self._token(), self._body()
            path = urlsplit(self.path).path
            if path == "/v1/consents":
                result = self.server.store.grant_consent(token, **body)
            elif path == "/v1/traces":
                result = self.server.store.ingest(token, **body)
            elif path == "/v1/derivatives":
                result = self.server.store.register_derivative(token, **body)
            elif path == "/v1/withdrawals":
                result = self.server.store.withdraw(token, **body)
            else:
                raise TraceError("route not found", 404)
            self._reply(200, result)
        except TraceError as error:
            self._reply(error.status, {"error": str(error)})
        except (TypeError, ValueError, RecursionError):
            self._reply(400, {"error": "request does not match the endpoint schema"})


class TraceClient:
    """Explicit local client: never uploads automatically on construction."""

    def __init__(self, base_url: str, token: str, *, timeout: float = 10):
        parsed = urlsplit(base_url)
        try:
            local = ipaddress.ip_address(parsed.hostname or "").is_loopback
        except ValueError:
            local = parsed.hostname == "localhost"
        if parsed.scheme != "http" or not local or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("client supports local loopback HTTP only")
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _request(self, method: str, path: str, value: Any = None) -> Any:
        payload = None if value is None else json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        request = Request(self.base_url + path, data=payload, method=method,
                          headers={"Authorization": "Bearer " + self._token,
                                   "Content-Type": "application/json"})
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                message = json.load(error).get("error", "request rejected")
            except (ValueError, AttributeError):
                message = "request rejected"
            finally:
                error.close()
            raise TraceHTTPError(message, error.code) from None

    def grant_consent(self, **scope: Any) -> dict[str, Any]:
        return self._request("POST", "/v1/consents", scope)

    def upload(self, trace: Mapping[str, Any], *, consent_id: str) -> dict[str, Any]:
        filtered, _ = filter_credentials(dict(trace))
        return self._request("POST", "/v1/traces", {"consent_id": consent_id, "trace": filtered})

    def get_trace(self, trace_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"trace_[0-9a-f]{32}", trace_id):
            raise ValueError("invalid trace identifier")
        return self._request("GET", "/v1/traces/" + trace_id)

    def register_derivative(self, **record: Any) -> dict[str, Any]:
        return self._request("POST", "/v1/derivatives", record)

    def get_derivative(self, identifier: str) -> dict[str, Any]:
        if not re.fullmatch(r"derived_[0-9a-f]{32}", identifier):
            raise ValueError("invalid derivative identifier")
        return self._request("GET", "/v1/derivatives/" + identifier)

    def withdraw(self, consent_id: str) -> dict[str, Any]:
        return self._request("POST", "/v1/withdrawals", {"consent_id": consent_id})
