"""Contract tests for authored synthetic data; no model/network calls."""
import re
import unittest

from moltweave.benchmarks import (
    DEFAULT_PER_FAMILY, FAMILIES, SPLITS, ToolSession, build_suite, suite_hash,
)


class BenchmarkContractTests(unittest.TestCase):
    def test_counts_and_fresh_deterministic_results(self):
        for split in SPLITS:
            first = build_suite(split)
            self.assertEqual(len(first), len(FAMILIES) * DEFAULT_PER_FAMILY[split])
            self.assertEqual(first, build_suite(split))
            first[0]["query"] = "mutated local copy"
            self.assertNotEqual(first, build_suite(split))

    def test_size_and_seed_are_part_of_contract(self):
        self.assertEqual(len(build_suite("train", per_family=5)), 35)
        self.assertNotEqual(suite_hash(build_suite("train", 17)), suite_hash(build_suite("train", 18)))
        for split, count in [("unknown", None), ("train", 0), ("train", True), ("dev", 1001)]:
            with self.assertRaises(ValueError):
                build_suite(split, per_family=count)

    def test_records_and_expected_are_internally_supported(self):
        for task in build_suite("train") + build_suite("dev") + build_suite("guard"):
            self.assertTrue(set(("id", "family", "user_id", "query", "memories", "documents", "tools", "expected")) <= task.keys())
            expected = task["expected"]
            self.assertNotIn(expected["answer"], task["query"]) if expected["answer"] != "UNKNOWN" else None
            tools = {tool["name"]: tool for tool in task["tools"]}
            correct = tools[expected["tool"]]
            self.assertEqual((correct["kind"], correct["available"], correct["deprecated"]), ("read", 1, 0))
            self.assertTrue(1 <= expected["tool_attempts"] <= 3)
            all_ids = {item["id"] for item in task["memories"] + task["documents"]}
            for tool in tools.values():
                self.assertTrue(tool["outcomes"])
                self.assertIn(tool["kind"], ("read", "write"))
                for result in tool["outcomes"]:
                    self.assertIn(result["status"], ("ok", "transient_error", "permanent_error"))
                    if result["status"] != "ok":
                        self.assertEqual(result["evidence_ids"], [])
                    all_ids.update(result["evidence_ids"])
            self.assertTrue(set(expected["evidence_ids"]) <= all_ids)
            self.assertEqual(task["required_evidence_count"], len(expected["evidence_ids"]))
            for record in task["memories"] + task["documents"]:
                self.assertIsInstance(record["age"], int)
                self.assertGreaterEqual(record["age"], 0)
                self.assertIn(record["trusted"], (0, 1))
                self.assertTrue(set(("id", "text", "entity", "age", "trusted", "scope")) <= record.keys())

    def test_partition_namespaces_and_facts_are_disjoint(self):
        seen_ids, seen_users, seen_entities, seen_sources, seen_facts = set(), set(), set(), set(), set()
        for split in SPLITS:
            # Host-only generation: failures disclose no final examples or values.
            suite = build_suite(split)
            ids = {task["id"] for task in suite}
            users = {task["user_id"] for task in suite}
            entities = {task["entity"] for task in suite}
            sources, facts = set(), set()
            for task in suite:
                for record in task["memories"] + task["documents"]:
                    ids.add(record["id"])
                    sources.add(record["source_id"])
                    facts.update(re.findall(r"V[0-9A-F]{10}", record["text"]))
                for tool in task["tools"]:
                    for result in tool["outcomes"]:
                        ids.update(result["evidence_ids"])
                        facts.update(re.findall(r"V[0-9A-F]{10}", result["text"]))
            for previous, current in [(seen_ids, ids), (seen_users, users), (seen_entities, entities),
                                      (seen_sources, sources), (seen_facts, facts)]:
                self.assertTrue(previous.isdisjoint(current), "Partition namespace collision")
                previous.update(current)

    def test_frozen_final_and_transfer_hashes_without_running_them(self):
        self.assertEqual(suite_hash(build_suite("final", 17, per_family=10)),
                         "4ba276f641a7ce80cda2ea5de6ec1d5394dc40d9af0013f6a55574e879acf023")
        self.assertEqual(suite_hash(build_suite("transfer", 17, per_family=10)),
                         "82e088127dde55855b127afd66dc754256956f3dbe0a0c9c0fcc5481839a9f51")

    def test_stateful_transient_and_permanent_outcomes(self):
        recovery = [t for t in build_suite("train") if t["family"] == "tool_recovery"]
        for task in recovery:
            session = ToolSession(task)
            receipts = [session.call(task["expected"]["tool"]) for _ in range(task["expected"]["tool_attempts"])]
            self.assertEqual(len(session.events), task["expected"]["tool_attempts"])
            if task["expected"]["answer"] == "UNKNOWN":
                self.assertEqual(receipts[-1]["status"], "permanent_error")
                self.assertFalse(receipts[-1]["retryable"])
                self.assertEqual(receipts[-1]["evidence_ids"], [])
            else:
                self.assertEqual(receipts[-1]["status"], "ok")
                self.assertTrue(all(x["status"] == "transient_error" and x["retryable"] for x in receipts[:-1]))
                self.assertIn(task["expected"]["answer"], receipts[-1]["text"])
                self.assertTrue(all(not x["evidence_ids"] for x in receipts[:-1]))

    def test_unavailable_endpoint_and_returned_receipt_are_isolated(self):
        task = next(t for t in build_suite("train") if t["family"] == "tool_routing")
        session = ToolSession(task)
        result = session.call("read_registry_preview")
        self.assertEqual(result["status"], "permanent_error")
        result["text"] = "caller mutation"
        self.assertNotEqual(session.events[-1]["result"]["text"], "caller mutation")
        with self.assertRaises(ValueError):
            session.call("does_not_exist")

    def test_composition_requires_three_distinct_supports(self):
        for task in build_suite("train"):
            if task["family"] != "composition":
                continue
            required = set(task["expected"]["evidence_ids"])
            self.assertEqual(len(required), 3)
            self.assertTrue(required & {x["id"] for x in task["memories"]})
            self.assertTrue(required & {x["id"] for x in task["documents"]})
            tool = next(x for x in task["tools"] if x["name"] == task["expected"]["tool"])
            self.assertTrue(required & set(tool["outcomes"][-1]["evidence_ids"]))


if __name__ == "__main__":
    unittest.main()

