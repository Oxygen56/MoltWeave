"""Persistent, scoped memory with source-checked model proposals and causal events.

This module does not call a model or an answer oracle. Snapshot hashes detect
accidental changes; they are not signatures or permission to import user state.
Only the trusted host should construct an instance from a supplied snapshot.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from .common import canonical, digest
from .program import evaluate


MEMORY_FEATURES = frozenset({"revision", "authority", "conflict", "is_newer", "verified",
    "duplicate", "age", "overlap", "entity_match", "key_match", "scope_match",
    "deprecated", "source_match", "trusted", "global_scope"})
_STATUSES = {"active", "superseded", "revoked", "quarantined"}
_PROPOSAL_FIELDS = {"source_id", "entity", "key", "value"}


def _copy(value: Any) -> Any:
    return json.loads(canonical(value))


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w-]+", value.lower()))


def _same_value(left: Any, right: Any) -> bool:
    # Python equality equates True and 1; source matching must not do so.
    return canonical(left) == canonical(right)


class ContinualMemory:
    """Mutable host state; clone/snapshot are pure, other calls audit their cause.

    Scope is a fixed boundary. Entity and key are ranking features, not access
    filters. Revisions are comparable only inside one source_family, and a
    source revocation is fixed host governance rather than an evolvable score.
    Instances are intended for one sequential stream, not concurrent mutation.
    """

    def __init__(self, state: dict | None = None):
        if state is None:
            self._state = {"schema": 1, "records": [], "events": [], "revoked_sources": [],
                           "next_call": 0, "next_event": 0}
            return
        candidate = _copy(state)
        claimed = candidate.pop("snapshot_hash", None)
        if claimed is not None and claimed != digest(candidate):
            raise ValueError("Memory snapshot hash mismatch")
        required = {"schema", "records", "events", "revoked_sources", "next_call", "next_event"}
        if set(candidate) != required or candidate["schema"] != 1:
            raise ValueError("Unsupported memory state schema")
        if any(not isinstance(candidate[name], list) for name in ("records", "events", "revoked_sources")):
            raise ValueError("Invalid memory state collections")
        if any(type(candidate[name]) is not int or candidate[name] < 0 for name in ("next_call", "next_event")):
            raise ValueError("Invalid memory event counters")
        ids = set()
        for row in candidate["records"]:
            if (not self._valid_fact(row) or row.get("trusted") is not True
                    or row.get("status") not in _STATUSES or row["id"] in ids):
                raise ValueError("Invalid memory record")
            ids.add(row["id"])
        for entry in candidate["revoked_sources"]:
            if not isinstance(entry, dict) or not all(_string(entry.get(k)) for k in ("tenant", "owner", "source_id")):
                raise ValueError("Invalid source revocation")
        self._state = candidate

    def snapshot(self) -> dict:
        result = _copy(self._state)
        result["snapshot_hash"] = digest(result)
        return result

    def clone(self) -> "ContinualMemory":
        return ContinualMemory(self.snapshot())

    @staticmethod
    def _valid_fact(fact: Any) -> bool:
        if not isinstance(fact, dict) or not all(_string(fact.get(k)) for k in
                ("id", "tenant", "owner", "entity", "key", "source_id")) or "value" not in fact:
            return False
        if type(fact.get("revision")) is not int or fact["revision"] < 0:
            return False
        authority = fact.get("authority")
        if type(authority) not in (int, float) or abs(authority) > 1e6 or not math.isfinite(authority):
            return False
        if "source_family" in fact and not _string(fact["source_family"]):
            return False
        if "source_kind" in fact and not isinstance(fact["source_kind"], str):
            return False
        if "text" in fact and not isinstance(fact["text"], str):
            return False
        if "observed_round" in fact and (type(fact["observed_round"]) is not int or fact["observed_round"] < 0):
            return False
        return True

    @staticmethod
    def _scope(tenant: str, owner: str, round_index: int | None = None) -> None:
        if not _string(tenant) or not _string(owner):
            raise ValueError("Tenant and owner are required host scope")
        if round_index is not None and (type(round_index) is not int or round_index < 0):
            raise ValueError("Round index must be a nonnegative integer")

    @staticmethod
    def _mechanism(mechanism: dict) -> dict:
        # The new validator is owned by the fixed host, never model output code.
        from .continual_program import validate_expression, validate_mechanism
        result = _copy(mechanism)
        validate_mechanism(result)
        for name in ("memory_score", "memory_write"):
            validate_expression(result[name], allowed_features=MEMORY_FEATURES)
        return result

    def _event(self, event_type: str, call: dict | None = None, **fields: Any) -> dict:
        self._state["next_event"] += 1
        result = {"id": f"event-{self._state['next_event']:08d}", "type": event_type}
        if call is not None:
            result.update({"call_id": call["call_id"], "parent_event_id": call["id"],
                           "tenant": call["tenant"], "owner": call["owner"]})
            for name in ("round_index", "mechanism_hash"):
                if name in call:
                    result[name] = call[name]
        result.update(_copy(fields))
        self._state["events"].append(result)
        return _copy(result)

    def _start(self, operation: str, tenant: str, owner: str, **fields: Any) -> dict:
        self._state["next_call"] += 1
        return self._event("call_started", operation=operation, tenant=tenant, owner=owner,
                           call_id=f"call-{self._state['next_call']:08d}", **fields)

    def _rows(self, tenant: str, owner: str, *, active: bool = False) -> list[dict]:
        return [row for row in self._state["records"] if row["tenant"] == tenant and row["owner"] == owner
                and (not active or row["status"] == "active")]

    def _revoked(self, source_id: str, tenant: str, owner: str) -> bool:
        return any(row["source_id"] == source_id and row["tenant"] == tenant and row["owner"] == owner
                   for row in self._state["revoked_sources"])

    @staticmethod
    def _family(row: dict) -> str:
        return row.get("source_family", row["source_id"])

    def _features(self, row: dict, rows: list[dict], *, entity: str, key: str,
                  query: str, round_index: int, source_match: bool) -> dict[str, float]:
        slot = [other for other in rows if other["entity"] == row["entity"] and other["key"] == row["key"]]
        lineage = [other for other in slot if self._family(other) == self._family(row)
                   and other["status"] != "quarantined"]
        peers = [other for other in slot if other["status"] == "active" and other["id"] != row["id"]]
        words = _tokens(query)
        content = _tokens(row["entity"] + " " + row["key"] + " " + canonical(row["value"]) + " " + row.get("text", ""))
        return {"revision": float(min(row["revision"], 1e12)), "authority": float(row["authority"]),
                "conflict": float(any(not _same_value(other["value"], row["value"]) for other in peers)),
                "is_newer": float(not lineage or row["revision"] >= max(other["revision"] for other in lineage)),
                "verified": 1.0, "trusted": 1.0,
                "duplicate": float(any(other is not row and other["source_id"] == row["source_id"]
                    and other["revision"] == row["revision"] and _same_value(other["value"], row["value"])
                    for other in slot)),
                "age": float(min(1e12, max(0, round_index - row["observed_round"]))),
                "overlap": len(words & content) / max(1, len(words)),
                "entity_match": float(row["entity"] == entity), "key_match": float(row["key"] == key),
                "scope_match": 1.0, "global_scope": 0.0, "deprecated": float(row["status"] != "active"),
                "source_match": float(source_match)}

    def read(self, *, tenant: str, owner: str, entity: str, key: str, query: str,
             round_index: int, mechanism: dict) -> list[dict]:
        self._scope(tenant, owner, round_index)
        if not all(isinstance(value, str) for value in (entity, key, query)):
            raise ValueError("Read selectors must be strings")
        call = self._start("read", tenant, owner, round_index=round_index,
                           mechanism_hash=digest(mechanism), query_hash=digest(query), entity=entity, key=key)
        try:
            program = self._mechanism(mechanism)
            # Filter BEFORE feature extraction and scoring. M cannot undo scope.
            scoped = self._rows(tenant, owner)
            ranked = []
            for row in (item for item in scoped if item["status"] == "active"):
                features = self._features(row, scoped, entity=entity, key=key, query=query,
                    round_index=round_index, source_match=row.get("source_kind") == "primary")
                ranked.append({"record_id": row["id"], "score": evaluate(program["memory_score"], features),
                               "features": features})
            # Stable insertion order resolves equal scores; it is not an oracle.
            ranked.sort(key=lambda item: -item["score"])
            selected_ids = [item["record_id"] for item in ranked[:program["memory_top_k"]]]
            by_id = {row["id"]: row for row in scoped}
            result = [_copy(by_id[record_id]) for record_id in selected_ids]
            self._event("read_completed", call, candidates=ranked, selected_record_ids=selected_ids)
            return result
        except Exception as exc:
            self._event("call_failed", call, error_type=type(exc).__name__)
            raise

    def ingest(self, proposals: list[dict], visible_facts: list[dict], *, tenant: str, owner: str,
               round_index: int, mechanism: dict) -> list[dict]:
        self._scope(tenant, owner, round_index)
        call = self._start("ingest", tenant, owner, round_index=round_index,
            mechanism_hash=digest(mechanism), proposals_hash=digest(proposals), visible_facts_hash=digest(visible_facts))
        try:
            program = self._mechanism(mechanism)
            proposals, visible_facts = _copy(proposals), _copy(visible_facts)
            if not isinstance(proposals, list) or not isinstance(visible_facts, list):
                raise ValueError("Proposals and visible facts must be lists")
            outcomes = []
            for index, proposal in enumerate(proposals):
                details = {"proposal_index": index, "proposal_hash": digest(proposal)}
                if not isinstance(proposal, dict) or set(proposal) != _PROPOSAL_FIELDS or not all(
                        _string(proposal.get(name)) for name in ("source_id", "entity", "key")):
                    outcomes.append(self._event("rejected", call, reason="invalid_proposal_shape", **details))
                    continue
                details["source_id"] = proposal["source_id"]
                matches = [fact for fact in visible_facts if self._valid_fact(fact)
                    and fact["tenant"] == tenant and fact["owner"] == owner
                    and all(_same_value(proposal[name], fact[name]) for name in _PROPOSAL_FIELDS)]
                eligible = [fact for fact in matches if fact.get("trusted") is True
                            and fact.get("status", "active") == "active"]
                # Conflicting metadata for an otherwise identical source is not
                # resolved by list order or a model's asserted confidence.
                same_source = [fact for fact in visible_facts if self._valid_fact(fact)
                    and fact["tenant"] == tenant and fact["owner"] == owner and fact.get("trusted") is True
                    and fact.get("status", "active") == "active" and all(fact[name] == proposal[name]
                        for name in ("source_id", "entity", "key"))]
                versions = {digest({name: fact.get(name) for name in
                    ("value", "revision", "authority", "source_family", "source_kind")}) for fact in same_source}
                if not eligible or len(versions) != 1:
                    reason = "ambiguous_source_metadata" if len(versions) > 1 else (
                        "untrusted_or_inactive_source" if matches else "no_exact_visible_source")
                    outcomes.append(self._event("quarantined" if matches else "rejected", call, reason=reason, **details))
                    continue
                fact = eligible[0]
                details.update({"source_record_id": fact["id"], "source_family": self._family(fact)})
                if self._revoked(fact["source_id"], tenant, owner):
                    outcomes.append(self._event("rejected", call, reason="source_revoked", **details))
                    continue
                record = {name: _copy(fact[name]) for name in
                    ("tenant", "owner", "entity", "key", "value", "source_id", "revision", "authority")}
                record.update({"source_family": self._family(fact), "source_kind": fact.get("source_kind", "unknown"),
                    "observed_round": round_index, "status": "active", "trusted": True})
                if "text" in fact:
                    record["text"] = fact["text"]
                record["id"] = "memory-" + digest({name: record[name] for name in
                    ("tenant", "owner", "entity", "key", "value", "source_id", "source_family", "revision")})[:24]
                rows = self._rows(tenant, owner)
                lineage = [other for other in rows if other["entity"] == record["entity"]
                    and other["key"] == record["key"] and self._family(other) == self._family(record)
                    and other["status"] != "quarantined"]
                features = self._features(record, rows, entity=record["entity"], key=record["key"],
                    query=record["entity"] + " " + record["key"], round_index=round_index,
                    source_match=record.get("source_kind") == "primary")
                score = evaluate(program["memory_write"], features)
                details.update({"features": features, "write_score": score, "record_id": record["id"]})
                if any(other["id"] == record["id"] for other in rows):
                    outcomes.append(self._event("deduplicated", call, reason="identical_source_revision", **details))
                    continue
                if score <= 0:
                    outcomes.append(self._event("rejected", call, reason="memory_write_nonpositive", **details))
                    continue
                newest = max((other["revision"] for other in lineage), default=-1)
                same_revision_conflict = any(other["revision"] == record["revision"]
                    and not _same_value(other["value"], record["value"]) for other in lineage)
                if record["revision"] < newest or same_revision_conflict:
                    record["status"] = "quarantined"
                    self._state["records"].append(record)
                    outcomes.append(self._event("quarantined", call,
                        reason="older_lineage_revision" if record["revision"] < newest else "same_revision_conflict", **details))
                    continue
                replaced = [other for other in lineage if other["status"] == "active"
                            and other["revision"] < record["revision"]]
                correction = any(not _same_value(other["value"], record["value"]) for other in replaced)
                for other in replaced:
                    other["status"] = "superseded"
                self._state["records"].append(record)
                outcomes.append(self._event("replaced" if replaced else "written", call,
                    reason="newer_same_source_family" if replaced else "verified_visible_proposal",
                    old_record_ids=[other["id"] for other in replaced], new_record_id=record["id"],
                    correction=correction, **details))
            self._event("ingest_completed", call, outcome_ids=[event["id"] for event in outcomes])
            return outcomes
        except Exception as exc:
            self._event("call_failed", call, error_type=type(exc).__name__)
            raise

    def revoke_source(self, source_id: str, *, tenant: str, owner: str) -> list[dict]:
        self._scope(tenant, owner)
        if not _string(source_id):
            raise ValueError("Source ID is required")
        call = self._start("revoke_source", tenant, owner, source_id=source_id)
        if not self._revoked(source_id, tenant, owner):
            self._state["revoked_sources"].append({"tenant": tenant, "owner": owner, "source_id": source_id})
        affected = []
        for row in self._rows(tenant, owner):
            if row["source_id"] == source_id and row["status"] != "revoked":
                previous_status = row["status"]
                row["status"] = "revoked"
                affected.append(self._event("revoked", call, source_id=source_id,
                    record_id=row["id"], previous_status=previous_status))
        if not affected:
            affected.append(self._event("revocation_recorded", call, source_id=source_id,
                reason="no_unrevoked_record_in_scope"))
        self._event("revocation_completed", call, affected_event_ids=[event["id"] for event in affected])
        return affected
