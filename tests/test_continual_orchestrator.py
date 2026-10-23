"""Structural orchestration checks with explicit fakes, never model-effect tests.

Fixture counts below exercise gates and failure paths. They are not experimental
scores, real model outputs, or evidence that either policy performs better.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from moltweave import continual as c
from moltweave.common import digest, read_json, write_json
from moltweave.continual_environment import episode, protection
from moltweave.continual_memory import ContinualMemory
from moltweave.continual_policy import baseline_policy
from moltweave.continual_program import baseline_mechanism


META = {"input_source": "synthetic_orchestration_test", "model": "fake_no_network"}


def fixture_report(mechanism, tasks=(), *, passed=0, guard_passed=2):
    return {"passed": passed, "total": len(tasks) or 4, "guard_passed": guard_passed,
            "mechanism_hash": digest(mechanism), "traces": []}


class NoNetworkClient:
    model = "orchestration-test-fake"
    base_url = "https://orchestration.invalid.test"

    def __init__(self, *args, **kwargs):
        self.calls = []

    def complete(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("Structural tests must not call any model")


class PairedProbeTests(unittest.TestCase):
    def setUp(self):
        self.mechanism = baseline_mechanism()
        self.old = baseline_policy()
        self.new = deepcopy(self.old)
        self.new["diagnosis_prompt"] += " Test-only altered strategy."
        self.observations = [{"trace_id": "structural-trace", "trace": {"event": "fixture"},
                              "feedback": {"sealed": True, "passed": False}}]
        self.history = [{"status": "executed", "modules": ["memory"], "gain": -0.25}]
        self.snapshot = ContinualMemory().snapshot()

    def probe(self, *, failure=None, same_policy=False, same_descendant=False, guard_regression=False):
        calls, lock = [], threading.Lock()
        original = deepcopy((self.mechanism, self.history, self.snapshot, self.observations))

        def record(kind, **payload):
            with lock:
                calls.append({"kind": kind, **deepcopy(payload)})

        def fake_evaluate(seed, r, split, mechanism, snapshot, client, metadata):
            record("evaluation", split=split, mechanism=mechanism, snapshot=snapshot, metadata=metadata)
            if metadata["fork"] == "shared-baseline":
                return fixture_report(mechanism, passed=1)
            return fixture_report(mechanism, passed=4 if metadata["fork"] == "new" else 1,
                                  guard_passed=1 if guard_regression and metadata["fork"] == "new" else 2)

        def fake_diagnose(client, policy, observations, history, *, metadata):
            record("diagnosis", policy=policy, observations=observations, history=history, metadata=metadata)
            if failure == "invalid_diagnosis" and metadata["fork"] == "new":
                raise ValueError("explicit malformed-diagnosis fixture")
            return {"fork": metadata["fork"]}

        def fake_select(policy, diagnosis, history, limit):
            record("selection", fork=diagnosis["fork"], limit=limit, history=history)
            return [] if failure == "no_action" and diagnosis["fork"] == "new" else [{"fork": diagnosis["fork"]}]

        def fake_trial(client, mechanism, policy, action, observations, history, snapshot, **kwargs):
            label = kwargs["metadata"]["fork"]
            record("trial", fork=label, mechanism=mechanism, snapshot=snapshot,
                   history=history, observations=observations, split=kwargs["split"])
            if failure == "invalid_candidate" and label == "new":
                return {"status": "invalid_candidate", "effect": None, "action": action}
            candidate = deepcopy(mechanism)
            candidate["memory_top_k"] = 4 if label == "old" or same_descendant else 5
            return {"status": "executed", "action": action, "mechanism": candidate,
                    "evaluation": fixture_report(candidate, passed=3)}

        with patch.object(c, "evaluate_partition", side_effect=fake_evaluate), \
             patch("moltweave.continual_policy.diagnose", side_effect=fake_diagnose), \
             patch("moltweave.continual_policy.select_actions", side_effect=fake_select), \
             patch.object(c, "candidate_trial", side_effect=fake_trial):
            result = c.paired_probe(NoNetworkClient(), self.mechanism, self.old,
                                    self.old if same_policy else self.new,
                                    self.observations, self.history, self.snapshot,
                                    seed=101, r=2, split="structural-probe", metadata=META)
        self.assertEqual((self.mechanism, self.history, self.snapshot, self.observations), original)
        return result, calls

    def test_forks_share_initial_state_observations_history_and_one_opportunity(self):
        result, calls = self.probe()
        self.assertTrue(result["valid_search_pair"])
        self.assertTrue(result["promotion_eligible"])
        self.assertEqual(result["initial_snapshot_hash"], digest({"mechanism": self.mechanism,
                         "memory": self.snapshot, "history": self.history}))
        for fork in result["forks"].values():
            self.assertEqual(fork["initial_mechanism_hash"], digest(self.mechanism))
            self.assertEqual(fork["initial_memory_hash"], digest(self.snapshot))
            self.assertEqual(fork["history_hash"], digest(self.history))
        diagnoses = [call for call in calls if call["kind"] == "diagnosis"]
        self.assertEqual(len(diagnoses), 2)
        self.assertEqual(diagnoses[0]["observations"], diagnoses[1]["observations"])
        self.assertEqual(diagnoses[0]["history"], diagnoses[1]["history"])
        self.assertEqual(diagnoses[0]["metadata"]["parent_options"], diagnoses[1]["metadata"]["parent_options"])
        trials = [call for call in calls if call["kind"] == "trial"]
        self.assertCountEqual([call["fork"] for call in trials], ["old", "new"])
        self.assertTrue(all(call["snapshot"] == self.snapshot and call["history"] == self.history for call in trials))
        self.assertEqual([call["limit"] for call in calls if call["kind"] == "selection"], [1, 1])
        self.assertEqual(sum(call["kind"] == "evaluation" and call["metadata"]["fork"] == "shared-baseline" for call in calls), 1)

    def test_invalid_or_absent_search_has_unknown_delta_despite_better_fallback_readout(self):
        for failure in ("invalid_diagnosis", "no_action", "invalid_candidate"):
            with self.subTest(failure=failure):
                result, _ = self.probe(failure=failure)
                self.assertFalse(result["valid_search_pair"])
                self.assertIsNone(result["future_delta"])
                self.assertGreater(result["raw_future_delta"], 0)
                self.assertFalse(result["promotion_eligible"])
                self.assertEqual(result["forks"]["new"]["trial"]["effect"], None)

    def test_same_policy_same_descendant_or_protection_regression_cannot_promote(self):
        for condition in ("same_policy", "same_descendant", "guard_regression"):
            with self.subTest(condition=condition):
                result, _ = self.probe(**{condition: True})
                self.assertTrue(result["valid_search_pair"])
                self.assertGreater(result["future_delta"], 0)
                self.assertFalse(result["promotion_eligible"])


class CandidateAndLaneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mechanism, self.policy = baseline_mechanism(), baseline_policy()
        self.snapshot = ContinualMemory().snapshot()

    def trial(self, action=None):
        return c.candidate_trial(NoNetworkClient(), self.mechanism, self.policy, action or {}, [], [], self.snapshot,
                                 seed=101, r=0, split="structural", metadata=META)

    def test_actual_host_rejected_parent_is_passed_to_proposer_and_candidate_to_execution(self):
        rejected = deepcopy(self.mechanism)
        rejected["memory_top_k"] = 2
        candidate = deepcopy(rejected)
        candidate["memory_top_k"] = 4
        action = {"parent": "best_rejected", "parent_hash": digest(rejected), "parent_mechanism": rejected}
        with patch("moltweave.continual_policy.propose_mechanism", return_value={"mechanism": candidate}) as proposer, \
             patch.object(c, "evaluate_partition", return_value=fixture_report(candidate)) as execute:
            result = self.trial(action)
        self.assertEqual(proposer.call_args.args[1], rejected)
        self.assertEqual(execute.call_args.args[3], candidate)
        self.assertEqual(result["mechanism_hash"], digest(candidate))
        self.assertEqual(result["status"], "executed")

    def test_real_execution_exceptions_propagate_instead_of_becoming_invalid_candidates(self):
        for error in (ValueError, TypeError, KeyError, RuntimeError):
            with self.subTest(error=error.__name__), \
                 patch("moltweave.continual_policy.propose_mechanism", return_value={"mechanism": self.mechanism}), \
                 patch.object(c, "evaluate_partition", side_effect=error("structural execution failure")):
                with self.assertRaises(error):
                    self.trial()

    def test_proposal_errors_remain_unknown_without_execution(self):
        with patch("moltweave.continual_policy.propose_mechanism", side_effect=ValueError("invalid IR fixture")), \
             patch.object(c, "evaluate_partition") as execute:
            result = self.trial()
        self.assertEqual(result["status"], "invalid_candidate")
        self.assertIsNone(result["effect"])
        self.assertNotIn("gain", result)
        execute.assert_not_called()

    def fake_experience(self, tasks, mechanism, memory, client, **kwargs):
        return {**fixture_report(mechanism, tasks), "traces": [{"trace_id": "fixture-trace", "trace": {"event": "fixture"},
                 "feedback": {"passed": False}}], "final_memory": memory.snapshot()}

    def test_invalid_policy_proposal_is_recorded_unknown_and_does_not_launch_probe(self):
        search = {"selected_mechanism": self.mechanism, "trials": []}
        with patch.object(c, "execute_episode", side_effect=self.fake_experience), \
             patch.object(c, "search_once", return_value=search), \
             patch("moltweave.continual_policy.propose_policy", side_effect=ValueError("invalid policy fixture")), \
             patch.object(c, "paired_probe") as probe, redirect_stdout(io.StringIO()):
            c.run_lane(self.root, NoNetworkClient(), 101, "joint", 1)
        folder = self.root / "streams/101/joint"
        proposal = read_json(folder / "rounds/r00/policy-proposal.json")
        self.assertEqual(proposal["status"], "invalid_policy")
        self.assertIsNone(proposal["effect"])
        self.assertNotIn("gain", proposal)
        self.assertFalse((folder / "rounds/r00/policy-probe.json").exists())
        self.assertEqual(read_json(folder / "versions/g1.json")["policy"], self.policy)
        probe.assert_not_called()

    def test_policy_transport_error_aborts_instead_of_becoming_invalid_policy(self):
        with patch.object(c, "execute_episode", side_effect=self.fake_experience), \
             patch.object(c, "search_once", return_value={"selected_mechanism": self.mechanism, "trials": []}), \
             patch("moltweave.continual_policy.propose_policy", side_effect=RuntimeError("transport fixture")), \
             redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "transport fixture"):
                c.run_lane(self.root, NoNetworkClient(), 101, "joint", 1)
        self.assertFalse((self.root / "streams/101/joint/versions/g1.json").exists())

    def test_best_rejected_uses_protection_then_development_not_last_trial(self):
        trials = []
        for k, passed, guard in [(2, 3, 1), (4, 2, 2), (5, 1, 2)]:
            mechanism = deepcopy(self.mechanism)
            mechanism["memory_top_k"] = k
            trials.append({"status": "executed", "action": {"modules": ["memory"], "operator": "rewrite", "parent": "current"},
                           "mechanism": mechanism, "mechanism_hash": digest(mechanism), "gain": -0.25,
                           "evaluation": fixture_report(mechanism, passed=passed, guard_passed=guard)})
        search = {"selected_mechanism": self.mechanism, "trials": trials, "baseline": {"guard_passed": 2}}
        new_policy = deepcopy(self.policy)
        new_policy["proposal_prompt"] += " Structural fixture."
        with patch.object(c, "execute_episode", side_effect=self.fake_experience), \
             patch.object(c, "search_once", return_value=search), \
             patch("moltweave.continual_policy.propose_policy", return_value={"policy": new_policy}), \
             patch.object(c, "paired_probe", return_value={"promotion_eligible": False, "future_delta": 0}) as probe, \
             redirect_stdout(io.StringIO()):
            c.run_lane(self.root, NoNetworkClient(), 101, "joint", 1)
        self.assertEqual(probe.call_args.kwargs["rejected"]["memory_top_k"], 4)


class PartitionAndReadoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed, self.rounds = 101, 2

    def freeze_fixture(self):
        mechanism, policy = baseline_mechanism(), baseline_policy()
        manifest = {"schema": 2, "rounds": self.rounds, "seeds": [self.seed],
                    "model": NoNetworkClient.model, "provider_base": NoNetworkClient.base_url,
                    "sources": {"structural_fixture": "not_real_frozen_source"},
                    "partition_hashes": {str(self.seed): c.partition_contract(self.seed, self.rounds)},
                    "protocol": {"policy_audit_checkpoints": [0, 1, 2]}}
        hashes = {}
        for arm in c.ARMS:
            previous = None
            for g in range(self.rounds + 1):
                state = {"mechanism": deepcopy(mechanism), "policy": deepcopy(policy),
                         "memory": ContinualMemory().snapshot(), "history": [], "round": g}
                state["mechanism"]["memory_top_k"] = 3 + g
                if arm == "joint":
                    state["policy"]["diagnosis_prompt"] += f" Structural checkpoint {g}."
                path = self.root / "streams" / str(self.seed) / arm / "versions" / f"g{g}.json"
                write_json(path, state)
                hashes[f"{self.seed}/{arm}/g{g}"] = digest(state)
                if previous is not None:
                    write_json(path.parent.parent / "rounds" / f"r{g-1:02d}" / "transition.json",
                               {"parent_m": digest(previous["mechanism"]), "parent_p": digest(previous["policy"]),
                                "loaded_m_next": digest(state["mechanism"]), "loaded_p_next": digest(state["policy"])})
                previous = state
        write_json(self.root / "manifest.json", manifest)
        write_json(self.root / "summary.json", {"status": "all_versions_frozen_pending_readout", "frozen_versions": hashes})
        return manifest

    def test_partition_contract_matches_actual_partition_execution_and_acceptance_sequences(self):
        contract = c.partition_contract(self.seed, self.rounds)
        mechanism, snapshot = baseline_mechanism(), ContinualMemory().snapshot()
        calls = []
        def fake_execute(tasks, mechanism, memory, client, **kwargs):
            calls.append(deepcopy(tasks))
            return fixture_report(mechanism, tasks)
        for split in ("development", "meta-development-search", "meta-development-future"):
            for r in range(self.rounds):
                with patch.object(c, "execute_episode", side_effect=fake_execute):
                    c.evaluate_partition(self.seed, r, split, mechanism, snapshot, NoNetworkClient(), META)
                self.assertEqual(contract[f"{split}/r{r}"], digest(calls[-2]))
                self.assertEqual(contract[f"{split}/r{r}/guard"], digest(calls[-1]))
        for split in ("audit-search", "audit-future"):
            with patch.object(c, "execute_episode", side_effect=fake_execute):
                c.evaluate_partition(self.seed, 3, split, mechanism, snapshot, NoNetworkClient(), META)
            self.assertEqual(contract[split], digest(calls[-2]))
            self.assertEqual(contract[split + "/guard"], digest(calls[-1]))
        self.assertEqual(contract["acceptance"], digest(c.acceptance_tasks(self.seed)))
        self.assertEqual(contract["transfer"], digest(c.acceptance_tasks(self.seed, "transfer")))
        self.assertEqual({t["round_index"] for t in c.acceptance_tasks(self.seed)}, {0, 1, 2, 3, 4})
        self.assertTrue(any(t["kind"] == "retention" for t in c.acceptance_tasks(self.seed)))
        for r in range(self.rounds):
            self.assertEqual(contract[f"experience/r{r}"], digest(episode(self.seed, r, "experience", retain_previous=True)))
        self.assertEqual(contract["audit-observations"], digest(episode(self.seed, 3, "audit-observations")))

    def test_all_versions_start_empty_and_all_checkpoints_share_one_sealed_audit_input(self):
        manifest = self.freeze_fixture()
        executions, audit_calls, lock = [], [], threading.Lock()
        empty_hash = digest(ContinualMemory().snapshot())
        def fake_execute(tasks, mechanism, memory, client, *, metadata, **kwargs):
            with lock:
                executions.append({"metadata": deepcopy(metadata), "task_hash": digest(tasks),
                                   "initial_memory_hash": digest(memory.snapshot()), **kwargs})
            return {**fixture_report(mechanism, tasks), "traces": [{"trace_id": "structural-audit-trace",
                    "trace": {"input": "fixture"}, "feedback": {"passed": False}}]}
        def fake_probe(client, mechanism, old_policy, new_policy, observations, history, snapshot, **kwargs):
            with lock:
                audit_calls.append({"generation": kwargs["metadata"]["version"], "mechanism": digest(mechanism),
                                    "observations": digest(observations), "history": digest(history), "snapshot": digest(snapshot)})
            return {"future_delta": 0, "raw_future_delta": 0, "valid_search_pair": True,
                    "policy_distinct": digest(old_policy) != digest(new_policy),
                    "distinct_selected_mechanisms": False,
                    "forks": {name: {"policy_hash": digest(policy), "future": {"passed": 0, "total": 4}}
                              for name, policy in (("old", old_policy), ("new", new_policy))}}
        with patch("moltweave.llm.ModelClient", NoNetworkClient), \
             patch.object(c, "frozen_sources", return_value=manifest["sources"]), \
             patch.object(c, "execute_episode", side_effect=fake_execute), \
             patch.object(c, "paired_probe", side_effect=fake_probe):
            result = c.independent_readout(self.root, concurrency=2)
        self.assertFalse(result["selection_allowed"])
        self.assertEqual(len(result["versions"]), len(c.ARMS) * (self.rounds + 1))
        independent = [call for call in executions if call["metadata"]["phase"] == "independent"]
        self.assertEqual(len(independent), len(c.ARMS) * (self.rounds + 1) * 2)
        self.assertTrue(all(call["initial_memory_hash"] == empty_hash for call in independent))
        for call in independent:
            self.assertEqual(call["task_hash"], manifest["partition_hashes"][str(self.seed)][call["metadata"]["split"]])
        self.assertEqual(sum(call["metadata"]["phase"] == "independent_policy_audit_observations" for call in executions), 1)
        self.assertCountEqual([call["generation"] for call in audit_calls], [0, 1, 2])
        self.assertEqual(len({digest({k: v for k, v in call.items() if k != "generation"}) for call in audit_calls}), 1)
        shared = read_json(self.root / "policy-audit-inputs" / f"{self.seed}.json")
        shared_hash = shared.pop("input_hash")
        self.assertEqual(shared_hash, digest(shared))
        for g in (0, 1, 2):
            self.assertEqual(read_json(self.root / "policy-audits" / str(self.seed) / f"g{g}.json")["audit_input_hash"], shared_hash)

    def test_model_endpoint_partition_version_and_parent_chain_changes_block_before_execution(self):
        for altered in ("model", "endpoint", "partition", "version", "transition"):
            with self.subTest(altered=altered), tempfile.TemporaryDirectory() as fresh:
                self.root = Path(fresh)
                manifest = self.freeze_fixture()
                if altered in {"model", "endpoint", "partition"}:
                    if altered == "model":
                        manifest["model"] = "another-model"
                    elif altered == "endpoint":
                        manifest["provider_base"] = "https://another.invalid.test"
                    else:
                        manifest["partition_hashes"][str(self.seed)]["acceptance"] = "changed-plan"
                    write_json(self.root / "manifest.json", manifest)
                elif altered == "version":
                    path = self.root / "streams" / str(self.seed) / "joint/versions/g2.json"
                    state = read_json(path)
                    state["mechanism"]["memory_top_k"] = 6
                    write_json(path, state)
                else:
                    path = self.root / "streams" / str(self.seed) / "joint/rounds/r01/transition.json"
                    state = read_json(path)
                    state["parent_p"] = "wrong-parent"
                    write_json(path, state)
                with patch("moltweave.llm.ModelClient", NoNetworkClient), \
                     patch.object(c, "frozen_sources", return_value=manifest["sources"]), \
                     patch.object(c, "execute_episode") as execute:
                    with self.assertRaises(ValueError):
                        c.independent_readout(self.root, concurrency=2)
                    execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
