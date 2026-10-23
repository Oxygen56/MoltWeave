"""Structural frozen-host tests. All model calls are explicitly mocked."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from moltweave import continual as engine
from moltweave import continual_memory, continual_policy, continual_program

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resume_readout_wrapper", ROOT / "scripts/resume_readout.py")
resume = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resume)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class MockPhysicalClient:
    """Deterministic wrong/unknown answers test reuse, never model performance."""
    def __init__(self, output, manifest, *, fail_joint=False, invalid_candidates=False):
        self.output_dir = output
        self.model, self.base_url = manifest["model"], manifest["provider_base"]
        self.allow_env_proxy = self.allow_http_loopback = False
        self.fail_joint = fail_joint
        self.invalid_candidates = invalid_candidates
        self.calls, self.lock = [], threading.Lock()

    def complete(self, messages, *, purpose, metadata, **kwargs):
        with self.lock:
            self.calls.append((purpose, deepcopy(metadata)))
        if purpose == "continual_task":
            output = {"answer": "UNKNOWN", "evidence_ids": []}
        elif purpose == "continual_memory_extraction":
            output = {"memory_proposals": []}
        elif purpose == "continual_diagnosis":
            observations = json.loads(messages[-1]["content"])["observations"]
            output = {"hypotheses": [{"modules": ["memory"], "cause": "structural fixture",
                "trace_refs": [{"trace_id": observations[0]["trace_id"], "pointer": "/trace/query"}],
                "probe": "fixture only", "confidence": .5}]}
        elif purpose in {"continual_mechanism_proposal", "continual_mechanism_syntax_repair"}:
            output = {"hypothesis": "structural fixture", "changes": {"forbidden": 4} if self.invalid_candidates else {"memory_top_k": 4},
                      "predicted_behavior": "fixture only", "regression_risk": "not measured"}
        else:
            raise AssertionError("Unexpected mocked model operation: " + purpose)
        failed = self.fail_joint and metadata.get("arm") == "joint" and metadata.get("phase") == "independent"
        identity = uuid.uuid4().hex
        dump(self.output_dir / f"{identity}.json", {"id": identity, "model_requested": self.model,
            "endpoint_host": "synthetic.example.invalid", "metadata": deepcopy(metadata), "purpose": purpose,
            "status": "failed" if failed else "completed", "content": json.dumps(output),
            "physical_attempts": [{"status": "failed" if failed else "completed", "usage": {"total_tokens": 1}}],
            "fixture": "not a real model call"})
        if failed:
            raise RuntimeError("Synthetic measurement unavailable")
        return output


class ResumeReadoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "structural-experiment"
        self.output.mkdir()
        package = self.output / "frozen-source/moltweave"
        package.mkdir(parents=True)
        sources = {}
        for name in resume._verifier.SOURCES:
            text = (ROOT / "src/moltweave" / name).read_text()
            (package / name).write_text(text)
            sources[name] = resume.digest(text)
        (package / "__init__.py").write_text(resume._verifier.INIT)
        self.seed, self.rounds = 811, 1
        self.manifest = {"schema": 2, "rounds": 1, "seeds": [self.seed], "arms": list(resume.ARMS),
            "model": "synthetic-not-called", "provider_base": "https://synthetic.example.invalid",
            "request_contract": {"fixture": "mocked calls only"}, "sources": sources,
            "source_scope": "structural fixture, not model effects",
            "protocol": {"policy_audit_checkpoints": [0, 1]},
            "partition_hashes": {str(self.seed): engine.partition_contract(self.seed, 1)}}
        dump(self.output / "manifest.json", self.manifest)
        frozen = {}
        for arm in resume.ARMS:
            state = {"mechanism": continual_program.baseline_mechanism(), "policy": continual_policy.baseline_policy(),
                     "memory": continual_memory.ContinualMemory().snapshot(), "history": []}
            for g in range(2):
                value = {**deepcopy(state), "round": g}
                dump(self.output / "streams" / str(self.seed) / arm / "versions" / f"g{g}.json", value)
                frozen[f"{self.seed}/{arm}/g{g}"] = resume.digest(value)
            dump(self.output / "streams" / str(self.seed) / arm / "rounds/r00/transition.json", {
                "status": "completed", "parent_m": resume.digest(state["mechanism"]), "loaded_m_next": resume.digest(state["mechanism"]),
                "parent_p": resume.digest(state["policy"]), "loaded_p_next": resume.digest(state["policy"])})
        dump(self.output / "summary.json", {"status": "all_versions_frozen_pending_readout", "errors": [],
            "completed": [{"seed": self.seed, "arm": arm, "rounds": 1, "status": "versions_frozen"} for arm in resume.ARMS],
            "frozen_versions": frozen})
        self.instances = []

    def factory(self, host, manifest, output, concurrency):
        client = MockPhysicalClient(output, manifest)
        self.instances.append(client)
        return host.engine.LimitedClient(client, concurrency)

    def run_mocked(self, factory=None):
        with patch.object(resume, "new_client", side_effect=factory or self.factory):
            return resume.resume_readout(self.output, concurrency=2)

    def test_offline_check_loads_actual_host_and_never_creates_client_lock_or_ledger(self):
        before = {str(path.relative_to(self.output)): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        with patch.object(resume, "new_client", side_effect=AssertionError("check instantiated client")):
            result = resume.resume_readout(self.output, check_only=True)
        self.assertEqual(result["status"], "checked")
        self.assertEqual(result["pending_versions"], 6)
        after = {str(path.relative_to(self.output)): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_first_run_and_final_reuse_are_immutable_even_with_zero_scores(self):
        result = self.run_mocked()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["versions"]), 6)
        self.assertTrue(all(row["reports"]["acceptance"]["passed"] == 0 for row in result["versions"]))
        self.assertTrue(all(row["valid_search_pair"] for row in result["policy_audits"]))
        paths = [self.output / "independent.json", *self.output.glob("independent/*/*/*.json"),
                 *self.output.glob("policy-audits/*/*.json"), *self.output.glob("policy-audit-inputs/*.json")]
        before = {str(path): path.read_bytes() for path in paths}
        with patch.object(resume, "new_client", side_effect=AssertionError("completed evidence was remeasured")):
            self.assertEqual(resume.resume_readout(self.output), result)
        self.assertEqual(before, {str(path): path.read_bytes() for path in paths})

    def test_interruption_retains_complete_versions_and_partial_calls_then_resumes(self):
        def fail(host, manifest, output, concurrency):
            client = MockPhysicalClient(output, manifest, fail_joint=True)
            self.instances.append(client)
            return host.engine.LimitedClient(client, concurrency)
        with self.assertRaises(RuntimeError):
            self.run_mocked(fail)
        self.assertFalse((self.output / "independent.json").exists())
        before = {str(path): path.read_bytes() for path in self.output.glob("independent/*/*/*.json")}
        self.assertTrue(before)
        calls_before = {str(path): path.read_bytes() for path in (self.output / "model-calls").rglob("*.json")}
        result = self.run_mocked()
        self.assertEqual(result["status"], "completed")
        for path, data in {**before, **calls_before}.items():
            self.assertEqual(Path(path).read_bytes(), data)
        ledgers = [resume.read_json(path) for path in (self.output / "readout-resume").glob("*/ledger.json")]
        self.assertTrue(any(row["status"] == "measurement_incomplete" for row in ledgers))
        self.assertTrue(any(event["action"] == "started" and event.get("prior_call_receipts")
                            for row in ledgers for event in row["events"]))

    def test_crash_before_final_publish_reuses_inputs_and_audits_without_client(self):
        original = resume.write_exclusive
        def crash(path, value):
            if path.name == "independent.json":
                raise RuntimeError("Synthetic crash before final publication")
            original(path, value)
        with patch.object(resume, "write_exclusive", side_effect=crash), self.assertRaises(RuntimeError):
            self.run_mocked()
        before = {str(path): path.read_bytes() for base in ("independent", "policy-audits", "policy-audit-inputs")
                  for path in (self.output / base).rglob("*.json")}
        self.assertTrue(any("policy-audit-inputs" in path for path in before))
        with patch.object(resume, "new_client", side_effect=AssertionError("all raw artifacts already complete")):
            result = resume.resume_readout(self.output)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(before, {path: Path(path).read_bytes() for path in before})

    def test_partial_split_is_preserved_and_whole_version_restarted(self):
        _, host, states = resume.load_contract(self.output)
        state = states[(self.seed, "joint", 0)]
        client = MockPhysicalClient(self.output / "model-calls/original-partial", self.manifest)
        report = host.runtime.execute_episode(host.engine.acceptance_tasks(self.seed, "transfer"), state["mechanism"],
            host.memory.ContinualMemory(), client,
            metadata={"phase": "independent", "stream": self.seed, "arm": "joint", "version": 0, "split": "transfer"})
        path = self.output / "independent" / str(self.seed) / "joint/g0.json"
        dump(path, {"transfer": report})
        partial_bytes = path.read_bytes()
        self.run_mocked()
        saved = list((self.output / "readout-resume").glob("*/preserved-partial/independent/*/joint/g0.json"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), partial_bytes)
        self.assertEqual(set(resume.read_json(path)), {"acceptance", "transfer"})

    def test_tampered_complete_task_ids_or_scores_are_rejected_before_requests(self):
        self.run_mocked()
        path = self.output / "independent" / str(self.seed) / "joint/g0.json"
        original = resume.read_json(path)
        for mutate in (lambda report: report["acceptance"].update(passed=1),
                       lambda report: report["acceptance"]["traces"][0].update(trace_id="unrelated-task")):
            value = deepcopy(original)
            mutate(value)
            dump(path, value)
            with patch.object(resume, "new_client", side_effect=AssertionError("tampering triggered a request")), self.assertRaises(ValueError):
                resume.resume_readout(self.output)
        dump(path, original)

    def test_partition_and_transition_mutations_rejected_before_client(self):
        changed = deepcopy(self.manifest)
        changed["partition_hashes"][str(self.seed)] = {}
        dump(self.output / "manifest.json", changed)
        with patch.object(resume, "new_client", side_effect=AssertionError), self.assertRaises(ValueError):
            resume.resume_readout(self.output)
        dump(self.output / "manifest.json", self.manifest)
        path = self.output / "streams" / str(self.seed) / "joint/rounds/r00/transition.json"
        transition = resume.read_json(path)
        transition["loaded_m_next"] = "wrong"
        dump(path, transition)
        with patch.object(resume, "new_client", side_effect=AssertionError), self.assertRaises(ValueError):
            resume.resume_readout(self.output)

    def test_provider_mismatch_and_duplicate_receipt_ids_fail_closed(self):
        _, host, _ = resume.load_contract(self.output)
        fake = SimpleNamespace(model="wrong-model", base_url=self.manifest["provider_base"],
                               allow_env_proxy=False, allow_http_loopback=False)
        with patch.object(host.llm, "ModelClient", return_value=fake), self.assertRaises(ValueError):
            resume.new_client(host, self.manifest, self.output / "not-created", 2)
        receipt = {"id": "same-fixture-id", "model_requested": self.manifest["model"], "endpoint_host": "synthetic.example.invalid"}
        dump(self.output / "model-calls/one.json", receipt)
        dump(self.output / "model-calls/nested/two.json", receipt)
        with patch.object(resume, "new_client", side_effect=AssertionError), self.assertRaisesRegex(ValueError, "duplicated"):
            resume.resume_readout(self.output)

    def test_invalid_audit_candidates_remain_unknown_and_are_reused(self):
        def invalid(host, manifest, output, concurrency):
            client = MockPhysicalClient(output, manifest, invalid_candidates=True)
            self.instances.append(client)
            return host.engine.LimitedClient(client, concurrency)
        result = self.run_mocked(invalid)
        self.assertTrue(all(not row["valid_search_pair"] and row["future_delta"] is None
                            for row in result["policy_audits"]))
        audit = self.output / "policy-audits" / str(self.seed) / "g1.json"
        original = audit.read_bytes()
        with patch.object(resume, "new_client", side_effect=AssertionError("invalid audit was selectively retried")):
            self.assertEqual(resume.resume_readout(self.output), result)
        self.assertEqual(audit.read_bytes(), original)

    def test_active_execution_lock_rejects_second_writer_but_not_offline_check(self):
        with resume.readout_lock(self.output):
            self.assertEqual(resume.resume_readout(self.output, check_only=True)["status"], "checked")
            with patch.object(resume, "new_client", side_effect=AssertionError("locked writer constructed client")), self.assertRaisesRegex(ValueError, "lock"):
                resume.resume_readout(self.output)


if __name__ == "__main__":
    unittest.main()
