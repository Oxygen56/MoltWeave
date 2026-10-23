"""Authored public event streams. Hidden answers never enter the task executor.

This is a synthetic, executable state environment, not a native external benchmark.
Split namespaces and event schedules are disjoint; their generation grammar is shared.
"""
from __future__ import annotations

from .common import digest


def token(*parts) -> str:
    return "V" + digest(parts)[:12].upper()


def fact(seed: int, split: str, entity: str, revision: int, round_index: int,
         *, source: str = "primary", authority: float = 1.0, value: str | None = None) -> dict:
    return {"id": "fact-" + digest([seed, split, entity, revision, source])[:18],
            "tenant": "public-tenant-" + str(seed), "owner": "public-owner-" + split,
            "entity": entity, "key": "registration_token", "value": value or token(seed, split, entity, revision, source),
            "source_id": "src-" + digest([seed, split, entity, revision, source])[:18],
            "source_family": source + "-" + entity, "revision": revision, "authority": authority,
            "observed_round": round_index, "status": "active", "trusted": True,
            "text": f"{source} registry revision {revision} records {entity}'s registration token.",
            "source_kind": source}


def _task(seed: int, split: str, label: str, entity: str, r: int, expected: dict,
          docs: list[dict], tools: list[dict] | None = None, *, recall: bool = False,
          policy_required: bool = False) -> dict:
    query = (f"Recall the most recently verified PRIMARY registry token for {entity} from our prior observations. "
             if recall else f"Establish the approved PRIMARY registry token for {entity}; replica registries can lag or disagree. ")
    query += "Return only the token, or UNKNOWN if supporting evidence is unavailable. Cite the source_id."
    if policy_required:
        query = (f"{'Recall' if recall else 'Establish'} the approved registration token for {entity}. "
                 "Use the most recently verified source-of-truth policy for this entity; its designated registry can change. "
                 "Other verified registries may disagree. If the policy or its token is unsupported, answer UNKNOWN. "
                 "Return only the token. Cite BOTH the governing policy's source_id and the designated token's source_id. "
                 "Retain relevant facts and source-of-truth rules for later tasks.")
    return {"id": "case-" + digest([seed, split, label, r])[:18], "tenant": expected["tenant"],
            "owner": expected["owner"], "entity": entity, "key": "registration_token", "round_index": r,
            "query": query, "documents": docs, "tools": tools or [], "kind": "recall" if recall else "observe",
            "expected": {"answer": expected["value"], "source_id": expected["source_id"]}}


def episode(seed: int, round_index: int, split: str, *, retain_previous: bool = False,
            tools: bool = True) -> list[dict]:
    """Observe → recall → correction → recall, optionally retaining previous entity.

    Every source value comes from this fixed environment; model-written memories
    may only copy facts actually visible in a completed execution. A correction is
    a later observation, not a hidden grade injected into memory.
    """
    entity = "Entity-" + digest([seed, split, round_index % 4])[:10]
    revision = 2 * (round_index // 4) + 1
    first = fact(seed, split, entity, revision, round_index)
    corrected = fact(seed, split, entity, revision + 1, round_index)
    # A verified replica is not the primary source. Its larger local revision is
    # deliberately incomparable across lineages; trust never means omniscience.
    replica = fact(seed, split, entity, 20 + round_index, round_index, source="replica", authority=.65)
    distractor = fact(seed, split, "Neighbor-" + entity, 30, round_index, source="primary")
    stale = dict(first, observed_round=max(0, round_index - 5))
    # Events include actual transient/permanent read results. Permission and
    # retry ceilings are fixed; the candidate controls only bounded decisions.
    available_tools = []
    first_docs = [replica, first, distractor]
    if tools and round_index % 3 == 1:
        first_docs = [replica, distractor]
        available_tools = [
            {"id": "read_primary_registry", "description": "Read approved primary registry current registration token",
             "available": True, "read_only": True, "deprecated": False, "facts": [first],
             "outcomes": ["transient_error", "ok"] if round_index % 2 else ["ok"]},
            {"id": "read_replica_registry", "description": "Read registry registration token quickly",
             "available": True, "read_only": True, "deprecated": True, "facts": [replica], "outcomes": ["ok"]}]
    governed = round_index % 4 in {2, 3}
    if governed:
        designated = "replica" if round_index % 4 == 3 else "primary"
        changed = "primary" if designated == "replica" else "replica"
        rule1 = dict(fact(seed, split, entity, revision, round_index, source="policy", value=designated), key="source_of_truth",
                     text=f"Verified source-of-truth policy for {entity}: use the {designated} registry.")
        rule2 = dict(fact(seed, split, entity, revision + 1, round_index, source="policy", value=changed), key="source_of_truth",
                     text=f"Revised source-of-truth policy for {entity}: now use the {changed} registry.")
        replica2 = fact(seed, split, entity, 21 + round_index, round_index, source="replica", authority=.65)
        first_docs = [first, replica, rule1, distractor]
        corrected_docs = [corrected, replica2, rule2, rule1, distractor]
        if round_index % 4 == 3:
            mirror = fact(seed, split, entity, 40, round_index, source="mirror", authority=.8)
            first_docs.insert(1, mirror)
            corrected_docs.insert(1, mirror)
        original_expected = replica if designated == "replica" else first
        corrected_expected = replica2 if changed == "replica" else corrected
        tasks = [_task(seed, split, "observe", entity, round_index, original_expected, first_docs, policy_required=True),
                 _task(seed, split, "recall", entity, round_index, original_expected, [], recall=True, policy_required=True),
                 _task(seed, split, "correction", entity, round_index, corrected_expected, corrected_docs, policy_required=True),
                 _task(seed, split, "corrected-recall", entity, round_index, corrected_expected, [], recall=True, policy_required=True)]
        tasks[0]["expected"]["policy_source_id"] = rule1["source_id"]
        tasks[1]["expected"]["policy_source_id"] = rule1["source_id"]
        tasks[2]["expected"]["policy_source_id"] = rule2["source_id"]
        tasks[3]["expected"]["policy_source_id"] = rule2["source_id"]
    else:
        tasks = [_task(seed, split, "observe", entity, round_index, first, first_docs, available_tools),
             _task(seed, split, "recall", entity, round_index, first, [], recall=True),
             _task(seed, split, "correction", entity, round_index, corrected,
                   [replica, corrected, stale, distractor]),
             _task(seed, split, "corrected-recall", entity, round_index, corrected, [], recall=True)]
    if retain_previous and round_index:
        old_entity = "Entity-" + digest([seed, split, (round_index - 1) % 4])[:10]
        previous = episode(seed, round_index - 1, split, retain_previous=False)[-1]
        old = dict(previous["expected"], tenant=first["tenant"], owner=first["owner"], value=previous["expected"]["answer"])
        tasks.append(_task(seed, split, "retention", old_entity, round_index, old, [], recall=True,
                           policy_required="policy_source_id" in previous["expected"]))
        tasks[-1]["expected"] = dict(previous["expected"])
        tasks[-1]["kind"] = "retention"
    if retain_previous and round_index >= 3:
        delayed = episode(seed, round_index - 3, split, retain_previous=False)[-1]
        old = dict(delayed["expected"], tenant=first["tenant"], owner=first["owner"], value=delayed["expected"]["answer"])
        tasks.append(_task(seed, split, "delayed-retention", delayed["entity"], round_index, old, [], recall=True,
                           policy_required="policy_source_id" in delayed["expected"]))
        tasks[-1]["expected"] = dict(delayed["expected"])
        tasks[-1]["kind"] = "delayed_retention"
    return tasks


def protection(seed: int, round_index: int, split: str) -> list[dict]:
    # A distinct owner and entity namespace checks basic reading and abstention.
    ent = "Guard-" + digest([seed, split, round_index])[:10]
    f = fact(seed, split, ent, 1, round_index)
    good = _task(seed, split, "guard-supported", ent, round_index, f, [f])
    unknown = _task(seed, split, "guard-unknown", ent + "-absent", round_index, f, [])
    unknown["expected"] = {"answer": "UNKNOWN", "source_id": None}
    return [good, unknown]


def episode_identity(seed: int, round_index: int, split: str, **kwargs) -> str:
    return digest(episode(seed, round_index, split, **kwargs))
