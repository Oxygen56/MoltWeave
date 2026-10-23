"""Authored synthetic tasks; not official benchmarks or production/model evidence."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import random

GENERATOR_VERSION = "moltloop-synthetic-v1"
FAMILIES = ("memory_temporal", "memory_scope", "rag_authority", "tool_routing", "tool_recovery", "composition", "clean")
SPLITS = ("train", "dev", "guard", "final", "transfer")
FROZEN_FINAL_SEED = 17
DEFAULT_PER_FAMILY = {"train": 3, "dev": 3, "guard": 2, "final": 2, "transfer": 2}
_WORDS = {"train": ("Aster", "Birch", "Cedar"), "dev": ("Elm", "Fennel", "Ginkgo"),
          "guard": ("Indigo", "Juniper", "Kestrel"), "final": ("Maple", "Nectar", "Orchid"),
          "transfer": ("Quartz", "Rowan", "Sorrel")}
_PREFIX = {"train": "Please verify the current record for", "dev": "Reconcile the latest applicable entry concerning",
           "guard": "Resolve the active assignment associated with", "final": "Establish the presently effective details of",
           "transfer": "Audit the operative configuration belonging to"}


def _hash(*parts: object, length: int = 16) -> str:
    return hashlib.sha256("\0".join(map(str, parts)).encode()).hexdigest()[:length]


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def suite_hash(tasks: list[dict]) -> str:
    return hashlib.sha256(canonical_json(tasks).encode()).hexdigest()


def build_suite(split: str, seed: int = 17, *, per_family: int | None = None) -> list[dict]:
    """Generate independent partition namespaces without running a model."""
    if split not in SPLITS:
        raise ValueError(f"Unknown split: {split!r}")
    count = DEFAULT_PER_FAMILY[split] if per_family is None else per_family
    if type(count) is not int or not 1 <= count <= 1000:
        raise ValueError("per_family must be an integer in 1..1000")
    tasks = []
    for family in FAMILIES:
        for index in range(count):
            ns = (GENERATOR_VERSION, split, seed, family, index)
            rng = random.Random(int(_hash(*ns, "shuffle"), 16))
            entity = f"{_WORDS[split][index % 3]}-{_hash(*ns, 'entity', length=6)}"
            neighbor = f"{_WORDS[split][(index + 1) % 3]}-{_hash(*ns, 'neighbor', length=6)}"
            user, other_user = "usr-" + _hash(*ns, "owner"), "usr-" + _hash(*ns, "other-owner")
            value = lambda key: "V" + _hash(*ns, "fact", key, length=10).upper()

            def record(key, text, *, age=0, trusted=1, scope=None, ent=None):
                return {"id": "ev-" + _hash(*ns, "evidence", key), "text": text,
                        "entity": entity if ent is None else ent, "age": age, "trusted": trusted,
                        "scope": user if scope is None else scope, "source_id": "src-" + _hash(*ns, "source", key)}

            def outcome(key, text, *, status="ok", retryable=False):
                return {"status": status, "retryable": retryable, "text": text,
                        "evidence_ids": ["ev-" + _hash(*ns, "receipt", key)] if status == "ok" else []}

            query = f"{_PREFIX[split]} {entity}. "
            if family == "composition":
                query += "Return its current assigned channel, applicable policy tier, and live registration token as channel|tier|token."
            elif family in ("memory_temporal", "memory_scope"):
                query += "Return my current assigned channel code. Confirm the object using a read-only live registry lookup."
            elif family == "rag_authority":
                query += "Return the currently applicable policy tier from an authoritative source. Confirm the object with the read-only live registry."
            else:
                query += "Return the live registration token using the current read-only registry."
            query += " If the required facts cannot be established, return UNKNOWN. Cite supporting evidence IDs."
            current, tier, token = value("channel"), value("tier"), value("token")
            old, foreign, unofficial = value("old"), value("foreign"), value("unofficial")
            good_mem = record("memory-current", f"Assignment for {entity}: channel {current}. Current owner's assignment.",
                              scope="global" if family == "clean" and index % 2 else user)
            good_doc = record("document-current", f"Effective policy for {entity}: tier {tier}. Issued by registry authority.", scope="global")
            memories, documents = [good_mem], [good_doc]
            if family in ("memory_temporal", "composition"):
                memories += [
                    record("memory-old", f"Archived note: {query} Assigned channel was {old}.", age=18 + index),
                    record("memory-older", f"Previous record for {entity}: assigned channel {unofficial}; live registry checked.", age=47),
                    record("memory-neighbor", f"Current assigned channel code for {neighbor} is {foreign}.", ent=neighbor)]
            if family in ("memory_scope", "composition"):
                # Cross-user items are fixed host-filter tests, never permission-learning targets.
                memories += [
                    record("memory-other-owner", f"Private assignment: {query} Assigned channel {foreign}.", scope=other_user),
                    record("memory-default", f"Global default for {entity}: channel {unofficial}; individual assignment overrides default.", scope="global", age=3),
                    record("memory-neighbor-owner", f"My current assigned channel code for {neighbor} is {old}.", ent=neighbor)]
            if family in ("rag_authority", "composition"):
                documents += [
                    record("document-untrusted", f"Search excerpt: {query} Applicable policy tier {unofficial}.", trusted=0, scope="global"),
                    record("document-old", f"Superseded authority bulletin for {entity}: policy tier {old}.", age=36 + index, scope="global"),
                    record("document-neighbor", f"Current authority policy tier for {neighbor}: {foreign}.", scope="global", ent=neighbor)]
            receipt = outcome("live", f"Live registry confirms {entity} is active. Registration token: {token}.")
            gold_name = "read_current_registry"
            tools = [
                {"name": gold_name, "description": f"Read the current authoritative live registry for {entity}; confirm object and fetch registration token.",
                 "entity": entity, "kind": "read", "deprecated": 0, "available": 1, "outcomes": [receipt]},
                {"name": "read_archived_registry", "description": f"Read historical registry entries for {entity}.",
                 "entity": entity, "kind": "read", "deprecated": 1, "available": 1,
                 "outcomes": [outcome("archive", f"Archived registration token for {entity}: {old}.")]},
                {"name": "update_registry", "description": f"Write a changed registration token for {entity}; not a lookup.",
                 "entity": entity, "kind": "write", "deprecated": 0, "available": 1,
                 "outcomes": [outcome("write", "Write operation is not valid evidence for a read-only lookup.", status="permanent_error")]}]
            attempts = 1
            if family == "tool_routing":
                tools += [
                    {"name": "read_registry_preview", "description": f"Read the current live registration token for {entity}; preview endpoint temporarily unavailable.",
                     "entity": entity, "kind": "read", "deprecated": 0, "available": 0,
                     "outcomes": [outcome("unavailable", "Endpoint unavailable.", status="permanent_error")]},
                    {"name": "read_neighbor_registry", "description": f"Read the current live registration token for {neighbor}.",
                     "entity": neighbor, "kind": "read", "deprecated": 0, "available": 1,
                     "outcomes": [outcome("neighbor", f"Registration token for {neighbor}: {foreign}.")]}]
                if index % 3 == 1:
                    tools[1]["description"] = f"Read the current live registration token for {entity}; legacy compatibility endpoint, deprecated."
                if index % 3 == 2:
                    tools[0]["description"] = f"Authoritative active-entry lookup for {entity}; read-only."
            if family == "tool_recovery":
                if index % 3 == 1:
                    tools[0]["outcomes"] = [outcome("access", "Access denied; unchanged credentials must not be retried.", status="permanent_error")]
                else:
                    errors = [outcome(f"temporary-{j}", "Read timed out before any result; retry is permitted.", status="transient_error", retryable=True)
                              for j in range(2 if index % 3 == 2 else 1)]
                    tools[0]["outcomes"], attempts = errors + [receipt], len(errors) + 1
            if family == "composition" and index % 2:
                tools[0]["outcomes"] = [outcome("temporary", "Transient read timeout; retry permitted.", status="transient_error", retryable=True), receipt]
                attempts = 2
            if family in ("memory_temporal", "memory_scope"):
                answer, evidence = current, [good_mem["id"]]
            elif family == "rag_authority":
                answer, evidence = tier, [good_doc["id"]]
            elif family == "composition":
                answer, evidence = f"{current}|{tier}|{token}", [good_mem["id"], good_doc["id"], *receipt["evidence_ids"]]
            elif family == "tool_recovery" and index % 3 == 1:
                answer, evidence = "UNKNOWN", []
            else:
                answer, evidence = token, receipt["evidence_ids"]
            rng.shuffle(memories); rng.shuffle(documents); rng.shuffle(tools)
            tasks.append({"id": "task-" + _hash(*ns, "task-id"), "family": family, "split": split,
                          "entity": entity, "user_id": user, "query": query,
                          "memories": memories, "documents": documents, "tools": tools,
                          "required_evidence_count": len(evidence),
                          "expected": {"answer": answer, "tool": gold_name, "evidence_ids": evidence, "tool_attempts": attempts}})
    return tasks


class ToolSession:
    """Reference synthetic state machine; only the current receipt is returned."""
    def __init__(self, task: dict):
        self._tools = {t["name"]: deepcopy(t) for t in task["tools"]}
        self.attempts: dict[str, int] = {}
        self.events: list[dict] = []

    def call(self, name: str) -> dict:
        if name not in self._tools:
            raise ValueError("Unknown tool")
        tool = self._tools[name]
        count = self.attempts.get(name, 0)
        self.attempts[name] = count + 1
        if not tool["available"]:
            result = {"status": "permanent_error", "retryable": False, "text": "Endpoint unavailable.", "evidence_ids": []}
        else:
            result = deepcopy(tool["outcomes"][min(count, len(tool["outcomes"]) - 1)])
        self.events.append({"tool": name, "attempt": count + 1, "result": deepcopy(result)})
        return result

