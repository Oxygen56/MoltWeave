"""Pipeline structure with readable fake clients; no model-effect measurement.

The fakes select from visible evidence or deliberately emit malformed output.
They never establish real model capability, experimental gains, or safety rates.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from moltweave.common import canonical, digest
from moltweave.continual_environment import episode, episode_identity
from moltweave.continual_memory import ContinualMemory
from moltweave.continual_program import baseline_mechanism
from moltweave import continual_runtime as runtime


METADATA = {"input_source": "authored_synthetic_unit_fixture", "client": "fake_not_real_model"}


def test_mechanism():
    """Give structural fixtures enough context; this is not an optimized arm."""
    result = baseline_mechanism()
    result.update(memory_top_k=6, rag_top_k=6,
        memory_score={"op": "add", "args": [{"op": "mul", "args": [100, {"var": "entity_match"}]},
                                               {"var": "authority"}]})
    return result


def proposal(fact):
    return {name: deepcopy(fact[name]) for name in ("source_id", "entity", "key", "value")}


def has_hidden_key(value):
    if isinstance(value, dict):
        return any(key in {"expected", "expected_after_sealing", "feedback"} or has_hidden_key(item)
                   for key, item in value.items())
    return isinstance(value, list) and any(has_hidden_key(item) for item in value)


class EvidenceOnlyFakeClient:
    """Deterministic fixture oracle over *visible* facts, not a real LLM.

    Task calls read the latest visible policy, then that registry's latest local
    revision. Writer calls simply copy their supplied visible source records.
    No expected labels or task objects are supplied to either decision method.
    """
    def __init__(self, *, omit_policy_citation=False):
        self.calls = []
        self.omit_policy_citation = omit_policy_citation

    def complete(self, messages, **kwargs):
        request = json.loads(messages[-1]["content"])
        self.calls.append({"messages": deepcopy(messages), "request": request, **deepcopy(kwargs)})
        purpose = kwargs["purpose"]
        if purpose == "continual_memory_extraction":
            facts = request.get("newly_observed_facts")
            if not isinstance(facts, list):
                raise AssertionError("Writer fixture requires an explicit visible-facts list")
            return {"memory_proposals": [proposal(fact) for fact in facts
                    if fact.get("trusted") is True and fact.get("status", "active") == "active"]}
        if purpose != "continual_task":
            raise AssertionError("Unexpected unit fixture purpose")
        relevant = [fact for fact in request["evidence"] if fact.get("entity") == request["entity"]
                    and fact.get("trusted") is True and fact.get("status", "active") == "active"]
        policies = [fact for fact in relevant if fact["key"] == "source_of_truth"]
        policy = max(policies, key=lambda fact: fact["revision"]) if policies else None
        requires_policy = "source-of-truth policy" in request["query"]
        if requires_policy and policy is None:
            return {"answer": "UNKNOWN", "evidence_ids": []}
        designated = policy["value"] if requires_policy else "primary"
        facts = [fact for fact in relevant if fact["key"] == request["key"]
                 and fact.get("source_kind") == designated]
        if not facts:
            return {"answer": "UNKNOWN", "evidence_ids": []}
        selected = max(facts, key=lambda fact: fact["revision"])
        ids = [selected["source_id"]]
        if requires_policy and not self.omit_policy_citation:
            ids.append(policy["source_id"])
        return {"answer": selected["value"], "evidence_ids": ids}


class InspectingMemory(ContinualMemory):
    def __init__(self):
        super().__init__()
        self.ingest_inputs = []

    def ingest(self, proposals, visible_facts, **kwargs):
        self.ingest_inputs.append(deepcopy({"proposals": proposals, "visible_facts": visible_facts, **kwargs}))
        return super().ingest(proposals, visible_facts, **kwargs)


class NoReadWriteMemory(ContinualMemory):
    def read(self, **kwargs):
        raise AssertionError("No-memory ablation called read")

    def ingest(self, *args, **kwargs):
        raise AssertionError("No-memory ablation called ingest")


class ContinualRuntimeTests(unittest.TestCase):
    def test_expected_is_accessed_only_after_sealing_and_never_sent_to_model_or_ingest(self):
        memory = InspectingMemory()
        client = EvidenceOnlyFakeClient()
        state = {"sealed": False, "expected_reads": 0}
        oracle_marker = "HIDDEN-UNIT-ORACLE-DO-NOT-TRANSMIT"
        original = episode(71, 0, "unit-seal", tools=False)[0]
        original["expected"] = {"answer": oracle_marker, "source_id": "hidden-unit-source"}

        class SealCheckedTask(dict):
            def __getitem__(self, key):
                if key == "expected":
                    self_case.assertTrue(state["sealed"])
                    self_case.assertTrue(memory.ingest_inputs)
                    state["expected_reads"] += 1
                return super().__getitem__(key)

        self_case = self
        ordinary_digest = runtime.digest
        def watch_seal(value):
            if isinstance(value, dict) and set(value) == {"output", "writer", "writes", "memory_after"}:
                state["sealed"] = True
            return ordinary_digest(value)

        with patch.object(runtime, "digest", side_effect=watch_seal):
            result = runtime.execute_task(SealCheckedTask(original), test_mechanism(), memory, client,
                                          metadata=METADATA)
        self.assertEqual(state["expected_reads"], 1)
        self.assertFalse(result["feedback"]["passed"])
        for payload in client.calls + memory.ingest_inputs:
            self.assertFalse(has_hidden_key(payload))
            self.assertNotIn(oracle_marker, canonical(payload))
        self.assertEqual(result["feedback"]["expected_after_sealing"]["answer"], oracle_marker)

    def test_writer_can_only_propose_facts_actually_selected_into_visible_context(self):
        task = episode(72, 0, "unit-visible", tools=False)[0]
        program = test_mechanism()
        program["rag_top_k"] = 1
        unselected = next(fact for fact in task["documents"] if fact["source_kind"] == "replica")
        memory = InspectingMemory()

        class AdversarialWriter(EvidenceOnlyFakeClient):
            def complete(self, messages, **kwargs):
                output = super().complete(messages, **kwargs)
                if kwargs["purpose"] == "continual_memory_extraction":
                    good = output["memory_proposals"][0]
                    output["memory_proposals"] += [proposal(unselected),
                        {**good, "value": "not-the-visible-value"},
                        {**good, "source_id": "invented-source"}]
                return output

        result = runtime.execute_task(task, program, memory, AdversarialWriter(), metadata=METADATA)
        visible = result["trace"]["visible_facts"]
        self.assertEqual(len(visible), 1)
        self.assertNotIn(unselected["source_id"], {fact["source_id"] for fact in visible})
        self.assertEqual(len(memory.snapshot()["records"]), 1)
        events = result["trace"]["write_events"]
        self.assertEqual([event["type"] for event in events], ["written", "rejected", "rejected", "rejected"])
        self.assertEqual(memory.ingest_inputs[0]["visible_facts"], visible)

    def test_observe_recall_revision_recall_uses_persisted_source_chain(self):
        tasks = episode(73, 0, "unit-chain", tools=False)
        memory = ContinualMemory()
        client = EvidenceOnlyFakeClient()
        result = runtime.execute_episode(tasks, test_mechanism(), memory, client, metadata=METADATA)
        self.assertEqual(result["passed"], 4)
        traces = result["traces"]
        for index in (1, 3):
            self.assertEqual(tasks[index]["documents"], [])
            self.assertEqual(tasks[index]["tools"], [])
            self.assertTrue(traces[index]["trace"]["selected_memories"])
            self.assertEqual(traces[index]["trace"]["output"]["answer"], tasks[index]["expected"]["answer"])
        old_id, new_id = tasks[0]["expected"]["source_id"], tasks[2]["expected"]["source_id"]
        self.assertNotEqual(old_id, new_id)
        self.assertIn(old_id, traces[1]["trace"]["output"]["evidence_ids"])
        self.assertIn(new_id, traces[3]["trace"]["output"]["evidence_ids"])
        rows = {row["source_id"]: row for row in memory.snapshot()["records"]}
        self.assertEqual(rows[old_id]["status"], "superseded")
        self.assertEqual(rows[new_id]["status"], "active")
        self.assertTrue(any(event["type"] == "replaced" and event["correction"]
                            for event in traces[2]["trace"]["write_events"]))
        self.assertEqual(sum(call["purpose"] == "continual_task" for call in client.calls), 4)
        self.assertEqual(sum(call["purpose"] == "continual_memory_extraction" for call in client.calls), 2)

    def test_governed_policy_switch_requires_both_policy_and_token_citations(self):
        for round_index in (2, 3):
            with self.subTest(round_index=round_index):
                tasks = episode(74, round_index, "unit-governed", tools=False)
                result = runtime.execute_episode(tasks, test_mechanism(), ContinualMemory(),
                                                  EvidenceOnlyFakeClient(), metadata=METADATA)
                self.assertEqual(result["passed"], 4)
                self.assertNotEqual(tasks[0]["expected"]["policy_source_id"], tasks[2]["expected"]["policy_source_id"])
                for task, trace in zip(tasks, result["traces"]):
                    cited = trace["trace"]["output"]["evidence_ids"]
                    self.assertIn(task["expected"]["source_id"], cited)
                    self.assertIn(task["expected"]["policy_source_id"], cited)
                omitted = runtime.execute_task(tasks[2], test_mechanism(), ContinualMemory(),
                    EvidenceOnlyFakeClient(omit_policy_citation=True), metadata=METADATA)
                self.assertTrue(omitted["feedback"]["answer_ok"])
                self.assertFalse(omitted["feedback"]["evidence_ok"])
                self.assertFalse(omitted["feedback"]["passed"])

    def test_retention_uses_previous_episode_final_expected_including_policy(self):
        for round_index in range(1, 5):
            previous = episode(75, round_index - 1, "unit-retention", tools=False)
            current = episode(75, round_index, "unit-retention", tools=False, retain_previous=True)
            retained = next(task for task in current if task["kind"] == "retention")
            self.assertEqual(retained["entity"], previous[-1]["entity"])
            self.assertEqual(retained["expected"], previous[-1]["expected"])
            if round_index >= 3:
                delayed = next(task for task in current if task["kind"] == "delayed_retention")
                earlier = episode(75, round_index - 3, "unit-retention", tools=False)[-1]
                self.assertEqual(delayed["entity"], earlier["entity"])
                self.assertEqual(delayed["expected"], earlier["expected"])
        # Execute across the boundary where the preceding episode ends under a
        # changed policy, rather than assuming a fixed primary-registry answer.
        memory = ContinualMemory()
        for round_index in range(3):
            runtime.execute_episode(episode(75, round_index, "unit-retention", tools=False), test_mechanism(),
                                    memory, EvidenceOnlyFakeClient(), metadata=METADATA)
        next_tasks = episode(75, 3, "unit-retention", tools=False, retain_previous=True)
        following = runtime.execute_episode(next_tasks, test_mechanism(), memory,
                                            EvidenceOnlyFakeClient(), metadata=METADATA)
        retention_index = next(index for index, task in enumerate(next_tasks) if task["kind"] == "retention")
        self.assertTrue(following["traces"][retention_index]["feedback"]["passed"])
        self.assertIn(next_tasks[retention_index]["expected"]["policy_source_id"],
                      following["traces"][retention_index]["trace"]["output"]["evidence_ids"])
        self.assertTrue(following["traces"][-1]["feedback"]["passed"])

    def test_no_memory_ablation_really_skips_read_write_and_writer_calls(self):
        tasks = episode(76, 0, "unit-no-memory", tools=False)
        memory = NoReadWriteMemory()
        before = memory.snapshot()
        client = EvidenceOnlyFakeClient()
        result = runtime.execute_episode(tasks, test_mechanism(), memory, client, metadata=METADATA,
                                          use_memory=False, write_memory=False)
        self.assertEqual(memory.snapshot(), before)
        self.assertEqual(result["initial_memory_hash"], result["final_memory_hash"])
        self.assertEqual([call["purpose"] for call in client.calls], ["continual_task"] * 4)
        for item in result["traces"]:
            self.assertEqual(item["trace"]["selected_memories"], [])
            self.assertEqual(item["trace"]["write_events"], [])
        for index in (1, 3):
            self.assertEqual(result["traces"][index]["trace"]["output"]["answer"], "UNKNOWN")

    def test_missing_task_or_writer_schema_raises_runtime_error_not_score_zero(self):
        task = episode(77, 0, "unit-schema", tools=False)[0]
        cases = [("continual_task", {"evidence_ids": []}),
                 ("continual_task", {"answer": "UNKNOWN"}),
                 ("continual_task", {"answer": 4, "evidence_ids": []}),
                 ("continual_memory_extraction", {}),
                 ("continual_memory_extraction", {"memory_proposals": "not-a-list"})]
        for failed_purpose, bad_output in cases:
            with self.subTest(purpose=failed_purpose, fields=list(bad_output)):
                class MalformedFakeClient(EvidenceOnlyFakeClient):
                    def complete(self, messages, **kwargs):
                        good_output = super().complete(messages, **kwargs)
                        return deepcopy(bad_output) if kwargs["purpose"] == failed_purpose else good_output
                with self.assertRaises(RuntimeError):
                    runtime.execute_task(task, test_mechanism(), ContinualMemory(), MalformedFakeClient(),
                                         metadata=METADATA)

    def test_tool_observation_retry_returns_actual_source_before_memory_write(self):
        tasks = episode(78, 1, "unit-tool", tools=True)
        memory = ContinualMemory()
        result = runtime.execute_task(tasks[0], test_mechanism(), memory, EvidenceOnlyFakeClient(), metadata=METADATA)
        events = result["trace"]["tool_events"]
        self.assertEqual([event["result"] for event in events], ["transient_error", "ok"])
        source_id = tasks[0]["expected"]["source_id"]
        self.assertNotIn(source_id, {fact["source_id"] for fact in tasks[0]["documents"]})
        self.assertIn(source_id, {fact["source_id"] for fact in events[-1]["facts"]})
        self.assertIn(source_id, {row["source_id"] for row in memory.snapshot()["records"]})
        self.assertTrue(result["feedback"]["passed"])

    def test_namespaces_have_disjoint_entities_source_records_and_token_values(self):
        def content(split):
            tasks = episode(79, 3, split, tools=False, retain_previous=True)
            facts = [fact for task in tasks for fact in task["documents"]]
            return ({task["entity"] for task in tasks} | {fact["entity"] for fact in facts},
                    {fact["id"] for fact in facts}, {fact["source_id"] for fact in facts},
                    {fact["value"] for fact in facts if fact["key"] == "registration_token"})
        left, right = content("unit-development"), content("unit-heldout")
        for a, b in zip(left, right):
            self.assertTrue(a)
            self.assertTrue(b)
            self.assertTrue(a.isdisjoint(b))
        self.assertEqual(episode_identity(79, 3, "unit-development"),
                         episode_identity(79, 3, "unit-development"))
        self.assertNotEqual(episode_identity(79, 3, "unit-development"),
                            episode_identity(79, 3, "unit-heldout"))

    def test_successful_tool_facts_are_scope_filtered_before_model_and_writer(self):
        task = episode(80, 1, "unit-tool-scope", tools=True)[0]
        selected = next(tool for tool in task["tools"] if tool["id"] == "read_primary_registry")
        foreign = {**deepcopy(selected["facts"][0]), "tenant": "foreign-tenant",
                   "source_id": "foreign-unit-source", "id": "foreign-unit-fact",
                   "value": "FOREIGN-UNIT-VALUE-MUST-NOT-ENTER-MODEL"}
        selected["facts"].append(foreign)
        memory = ContinualMemory()
        client = EvidenceOnlyFakeClient()
        result = runtime.execute_task(task, test_mechanism(), memory, client, metadata=METADATA)
        for call in client.calls:
            self.assertNotIn(foreign["value"], canonical(call))
        self.assertNotIn(foreign["source_id"], {fact["source_id"] for fact in result["trace"]["visible_facts"]})
        self.assertNotIn(foreign["source_id"], {fact["source_id"] for fact in memory.snapshot()["records"]})
        self.assertTrue(result["feedback"]["passed"])


if __name__ == "__main__":
    unittest.main()
