"""Scoped durable memory with explicit quarantine, correction and provenance.

Model-written facts start as proposals. Trust comes from a host-side review,
not from a quoted prompt or the model's own claim of success.
"""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import time
import uuid
from .program import evaluate, validate_expr
from .runtime import features


class MemoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, owner TEXT NOT NULL,
                entity TEXT NOT NULL, text TEXT NOT NULL, source TEXT NOT NULL,
                created REAL NOT NULL, state TEXT NOT NULL, supersedes TEXT,
                reviewer TEXT, metadata TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fact_id TEXT NOT NULL,
                tenant TEXT NOT NULL, event TEXT NOT NULL, actor TEXT NOT NULL, at REAL NOT NULL);
              CREATE INDEX IF NOT EXISTS facts_scope ON facts(tenant,owner,state);
            """)

    def _db(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def propose(self, *, tenant: str, owner: str, entity: str, text: str, source: str,
                metadata: dict | None = None, supersedes: str | None = None) -> str:
        if not all(isinstance(x, str) and x for x in (tenant, owner, entity, text, source)):
            raise ValueError("Explicit scope and provenance are required")
        fact_id = uuid.uuid4().hex
        with self._db() as db:
            if supersedes:
                old = db.execute("SELECT * FROM facts WHERE id=? AND tenant=? AND owner=?", (supersedes, tenant, owner)).fetchone()
                if not old:
                    raise PermissionError("Cannot correct memory outside this scope")
            db.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (fact_id, tenant, owner, entity, text, source, time.time(), "quarantined", supersedes, None, json.dumps(metadata or {})))
            db.execute("INSERT INTO events(fact_id,tenant,event,actor,at) VALUES(?,?,?,?,?)", (fact_id, tenant, "proposed", owner, time.time()))
        return fact_id

    def review(self, fact_id: str, *, tenant: str, owner: str, reviewer: str, accept: bool) -> None:
        """Trusted host API: the application authenticates reviewer before calling."""
        if not reviewer:
            raise PermissionError("Reviewer identity required")
        with self._db() as db:
            row = db.execute("SELECT * FROM facts WHERE id=? AND tenant=? AND owner=?", (fact_id, tenant, owner)).fetchone()
            if not row:
                raise PermissionError("Unknown memory in authenticated scope")
            if row["state"] != "quarantined":
                raise ValueError("Memory already reviewed or revoked")
            state = "active" if accept else "rejected"
            db.execute("UPDATE facts SET state=?,reviewer=? WHERE id=?", (state, reviewer, fact_id))
            if accept and row["supersedes"]:
                db.execute("UPDATE facts SET state='superseded' WHERE id=? AND tenant=? AND owner=?", (row["supersedes"], tenant, owner))
            db.execute("INSERT INTO events(fact_id,tenant,event,actor,at) VALUES(?,?,?,?,?)", (fact_id, tenant, state, reviewer, time.time()))

    def read(self, *, tenant: str, owner: str, query: str, score: dict | int, limit: int = 5) -> list[dict]:
        validate_expr(score)
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        with self._db() as db:
            rows = db.execute("SELECT * FROM facts WHERE tenant=? AND owner=? AND state='active'", (tenant, owner)).fetchall()
        task = {"user_id": owner, "query": query}
        items = []
        for row in rows:
            item = dict(row)
            item.update({"scope": owner, "age": max(0, (time.time() - row["created"]) / 86400), "trusted": 1})
            item["score"] = evaluate(score, features(item, task))
            items.append(item)
        return sorted(items, key=lambda x: (-x["score"], x["id"]))[:limit]

    def revoke_source(self, source: str, *, tenant: str, owner: str, actor: str) -> int:
        with self._db() as db:
            rows = db.execute("SELECT id FROM facts WHERE source=? AND tenant=? AND owner=?", (source, tenant, owner)).fetchall()
            for row in rows:
                db.execute("UPDATE facts SET state='revoked',text='' WHERE id=?", (row["id"],))
                db.execute("INSERT INTO events(fact_id,tenant,event,actor,at) VALUES(?,?,?,?,?)", (row["id"], tenant, "source_revoked", actor, time.time()))
        return len(rows)
