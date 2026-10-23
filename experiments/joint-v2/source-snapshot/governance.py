"""Fixed, non-evolvable approval boundary for MoltLoop.

This module never evaluates candidate code.  ``issue`` is an owner control-plane
operation; callers must authenticate the owner before invoking it.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any, Mapping


class ApprovalError(PermissionError):
    """An approval was absent, invalid, expired, mismatched, or consumed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    """Hash JSON data deterministically; NaN and arbitrary objects are refused."""
    return hashlib.sha256(_canonical(value)).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _file_lock(path: Path):
    """Cross-process lock in addition to each store's thread lock."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(path, "a+b") as stream:
        os.chmod(path, 0o600)
        if os.name == "nt":  # pragma: no cover - exercised on Windows only
            import msvcrt
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def _diff(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        result: list[str] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                result.append(path)
            else:
                result.extend(_diff(before[key], after[key], path))
        return result
    return [] if before == after else [prefix or "$"]


_IMMUTABLE = frozenset({"governance", "approval_store", "approval_secret", "evaluator",
                        "scorer", "tenant_boundary", "authentication", "authorization"})
_SENSITIVE = frozenset({
    "permissions", "tool_permissions", "tool_allowlist", "allowed_tools", "capabilities",
    "credentials", "secrets", "network", "egress", "upload", "upload_policy", "data_upload",
    "consent", "sharing", "retention", "deletion", "delete", "forget", "forgetting",
    "memory_policy", "memory_write", "memory_write_policy", "write_policy", "read_policy",
    "memory_read_policy", "filesystem", "shell", "dependencies", "meta_policy", "p",
})
_FORBIDDEN_CODE_KEYS = frozenset({"python", "python_code", "exec", "eval", "pickle",
                                 "shell_command", "dynamic_import"})
_PRIVILEGE_PROMPT = re.compile(
    r"(?is)(ignore.{0,45}(?:policy|policies|instructions|approval|security)|"
    r"(?:bypass|disable|skip|override).{0,45}(?:approval|permission|security|tenant)|"
    r"(?:export|upload|send|leak|exfiltrat).{0,70}(?:secret|credential|token|other user|other tenant)|"
    r"(?:忽略|绕过|关闭|跳过).{0,20}(?:审批|权限|安全|租户)|"
    r"(?:上传|发送|导出|泄露).{0,25}(?:凭据|密钥|其他用户|其他租户))")


def _walk_keys(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path
            yield from _walk_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_keys(child, f"{prefix}[{index}]")


def risk_of(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Classify structured diffs conservatively using a fixed vocabulary.

    A label is not a complete sandbox: the core must also validate its allowed
    expression IR and enforce tool grants at execution time.
    """
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise TypeError("before and after must be mappings")
    before, after = dict(before), dict(after)
    before_hash, after_hash = stable_hash(before), stable_hash(after)
    changed = _diff(before, after)
    reasons: list[str] = []
    blocked = False
    for path in changed:
        segments = {part.lower() for part in re.split(r"[.\[\]/]+", path) if part}
        immutable = segments & _IMMUTABLE
        if immutable:
            blocked = True
            reasons.append(f"immutable boundary: {path}")
        elif segments & _SENSITIVE:
            reasons.append(f"sensitive mechanism: {path}")
    # Inspect newly introduced subtrees too (a whole object can be added at once).
    for path in set(_walk_keys(before)) | set(_walk_keys(after)):
        segments = {part.lower() for part in re.split(r"[.\[\]/]+", path) if part}
        if segments & _FORBIDDEN_CODE_KEYS:
            blocked = True
            reasons.append(f"arbitrary code surface forbidden: {path}")
        if any(path == c or path.startswith(c + ".") or path.startswith(c + "[") for c in changed):
            if segments & _IMMUTABLE:
                blocked = True
                reasons.append(f"immutable boundary: {path}")
            elif segments & _SENSITIVE:
                reasons.append(f"sensitive mechanism: {path}")
    for path in changed:
        current: Any = after
        try:
            for part in path.split("."):
                current = current[part]
        except (KeyError, TypeError):
            continue
        if isinstance(current, str) and "prompt" in path.lower() and _PRIVILEGE_PROMPT.search(current):
            reasons.append(f"privilege-sensitive prompt: {path}")
    return {"sensitive": bool(reasons), "blocked": blocked,
            "classification": "blocked" if blocked else "sensitive" if reasons else "ordinary",
            "reasons": sorted(set(reasons)), "changed_paths": changed,
            "before_hash": before_hash, "after_hash": after_hash}


class ApprovalStore:
    """Owner-issued HMAC tickets, exact-plan binding, atomic single consumption."""

    def __init__(self, path: str | Path, secret: bytes | str | None = None):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = threading.RLock()
        self._ledger = self.path / "approvals.json"
        self._lock_path = self.path / ".approval.lock"
        if secret is None:
            key_path = self.path / ".approval-key"
            try:
                fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(secrets.token_bytes(32))
            secret = key_path.read_bytes()
        if isinstance(secret, str):
            secret = secret.encode()
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("approval signing secret must contain at least 32 bytes")
        self._secret = secret

    def _read(self) -> dict[str, Any]:
        if not self._ledger.exists():
            return {"version": 1, "issued": {}}
        return json.loads(self._ledger.read_text(encoding="utf-8"))

    def _sign(self, body: Mapping[str, Any]) -> str:
        return hmac.new(self._secret, _canonical(body), hashlib.sha256).hexdigest()

    def issue(self, *, candidate_hash: str, base_hash: str,
              dependencies: Any, scope: Any, action: str, expires_at: float,
              owner: str, nonce: str | None = None) -> dict[str, Any]:
        """Trusted owner API, never an operation exposed to the evolving agent."""
        now = time.time()
        if not all(isinstance(x, str) and x.strip() for x in (candidate_hash, base_hash, action, owner)):
            raise ValueError("candidate_hash, base_hash, action, and owner are required")
        if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)) or expires_at <= now:
            raise ValueError("approval expiry must be a future Unix timestamp")
        nonce = nonce or secrets.token_hex(24)
        if not isinstance(nonce, str) or not nonce.strip():
            raise ValueError("nonce must be nonempty")
        body = {"version": 1, "candidate_hash": candidate_hash, "base_hash": base_hash,
                "dependencies": dependencies, "scope": scope, "action": action,
                "expires_at": expires_at, "issued_at": now, "owner": owner, "nonce": nonce}
        # Round-trip makes the returned ticket independent of caller-owned dicts.
        body = json.loads(_canonical(body))
        ticket = {**body, "signature": self._sign(body)}
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            if nonce in state["issued"]:
                raise ApprovalError("approval nonce already exists")
            state["issued"][nonce] = {"ticket_hash": stable_hash(ticket), "consumed_at": None,
                                      "revoked": False}
            _atomic_json(self._ledger, state)
        return ticket

    def authorize(self, ticket: Mapping[str, Any] | None, *, candidate_hash: str,
                  base_hash: str, dependencies: Any, scope: Any, action: str,
                  consume: bool = True) -> dict[str, Any]:
        if not isinstance(ticket, Mapping):
            raise ApprovalError("owner approval required")
        ticket = dict(ticket)
        signature = ticket.pop("signature", None)
        try:
            valid = isinstance(signature, str) and hmac.compare_digest(self._sign(ticket), signature)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ApprovalError("approval signature invalid")
        expected = {"candidate_hash": candidate_hash, "base_hash": base_hash,
                    "dependencies": dependencies, "scope": scope, "action": action}
        if any(_canonical(ticket.get(key)) != _canonical(value) for key, value in expected.items()):
            raise ApprovalError("approval does not match the complete execution plan")
        if ticket.get("version") != 1 or not isinstance(ticket.get("expires_at"), (int, float)):
            raise ApprovalError("approval schema invalid")
        if time.time() >= ticket["expires_at"]:
            raise ApprovalError("approval expired")
        complete = {**ticket, "signature": signature}
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            entry = state["issued"].get(ticket.get("nonce"))
            if not entry or entry["ticket_hash"] != stable_hash(complete):
                raise ApprovalError("approval was not issued by this store")
            if entry.get("revoked"):
                raise ApprovalError("approval revoked")
            if entry["consumed_at"] is not None:
                raise ApprovalError("approval already consumed")
            if consume:
                entry["consumed_at"] = time.time()
                _atomic_json(self._ledger, state)
        return {"authorized": True, "consumed": consume, "nonce": ticket["nonce"],
                "approval_hash": stable_hash(complete), "owner": ticket["owner"]}

    def revoke(self, nonce: str) -> None:
        with self._lock, _file_lock(self._lock_path):
            state = self._read()
            if nonce not in state["issued"]:
                raise ApprovalError("unknown approval")
            state["issued"][nonce]["revoked"] = True
            _atomic_json(self._ledger, state)


def require_approval(before: Mapping[str, Any], after: Mapping[str, Any], *,
                     approval_store: ApprovalStore | None = None,
                     ticket: Mapping[str, Any] | None = None,
                     candidate_hash: str | None = None, base_hash: str | None = None,
                     dependencies: Any = None, scope: Any = None,
                     action: str = "adopt") -> dict[str, Any]:
    """Check immediately before adoption; consumes sensitive approvals once."""
    risk = risk_of(before, after)
    if risk["blocked"]:
        raise ApprovalError("fixed governance/evaluator or arbitrary code cannot be evolved")
    receipt = None
    if risk["sensitive"]:
        if approval_store is None:
            raise ApprovalError("sensitive diff requires owner approval")
        receipt = approval_store.authorize(
            ticket, candidate_hash=candidate_hash or stable_hash(after),
            base_hash=base_hash or stable_hash(before), dependencies=dependencies,
            scope=scope, action=action)
    return {"risk": risk, "approval": receipt}
