"""Structural analysis fixtures only. No model effects, network or credentials."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from moltweave.common import digest, read_json, write_json
from moltweave.continual_analysis import (
    ARMS, _aggregate_secondary, _secondary_report, _call_statistics, analyze, memory_chain, paired_statistics,
)


def experience_fixture():
    old = {"id": "old-record", "source_id": "old-source", "source_family": "rule-lineage",
           "tenant": "fixture-tenant", "owner": "fixture-owner", "entity": "object",
           "key": "source_of_truth", "status": "active"}
    new = {**old, "id": "new-record", "source_id": "new-source"}
    initial = {"id": "write-old", "type": "written", "new_record_id": old["id"],
               "source_id": old["source_id"], "source_family": old["source_family"]}
    replacement = {"id": "replace-new", "type": "replaced", "old_record_ids": [old["id"]],
                   "new_record_id": new["id"], "source_id": new["source_id"], "source_family": new["source_family"]}
    traces = []
    for index, kind in enumerate(("observe", "recall", "observe", "recall")):
        traces.append({"trace_id": f"fixture-step-{index}", "kind": kind,
            "feedback": {"passed": True},
            "trace": {"entity": "object", "mechanism_hash": "fixture-mechanism",
                "memory_before_hash": f"state-{index}", "memory_after_hash": f"state-{index+1}",
                "selected_memories": [old] if index == 1 else [new] if index == 3 else [],
                "ranked_documents": [], "tool_events": [],
                "write_events": [initial] if index == 0 else [replacement] if index == 2 else []}})
    return {"passed": 4, "total": 4, "traces": traces}


def diagnostic_fixture():
    return {"passed": 1, "total": 4, "mechanism_hash": "fixture-mechanism", "traces": [
        {"trace_id": "wrong-answer-supported", "feedback": {"answer_ok": False, "evidence_ok": True,
            "expected_after_sealing": {"source_id": "token-source", "policy_source_id": "policy-source"}},
         "trace": {"visible_facts": [{"source_id": "token-source"}, {"source_id": "policy-source"}]}},
        {"trace_id": "correct-answer-missing-policy", "feedback": {"answer_ok": True, "evidence_ok": False,
            "expected_after_sealing": {"source_id": "token-source", "policy_source_id": "policy-source"}},
         "trace": {"visible_facts": [{"source_id": "token-source"}], "output": {"evidence_ids": ["policy-source"]}}},
        {"trace_id": "abstention", "feedback": {"answer_ok": False, "evidence_ok": False,
            "expected_after_sealing": {"source_id": None}}, "trace": {"visible_facts": []}},
        {"trace_id": "legacy-missing-fields", "feedback": {}, "trace": {}},
    ]}


def write_experiment_fixture(root):
    seeds, rounds = [101, 102], 2
    write_json(root / "manifest.json", {"schema": 2, "seeds": seeds, "rounds": rounds,
        "arms": list(ARMS), "source_scope": "structural fixture, not measured model performance"})
    versions, audits = [], []
    for seed in seeds:
        for arm in ARMS:
            lane = root / "streams" / str(seed) / arm
            states = []
            for g in range(rounds + 1):
                m = {"score": 0 if arm == "fixed_mechanism" else g}
                p = {"prompt": "constant" if arm != "joint" else f"policy-{g}</script><script>NOT_EXECUTABLE</script>"}
                state = {"mechanism": m, "policy": p, "memory": {"records": []}, "history": [], "round": g}
                states.append(state)
                write_json(lane / "versions" / f"g{g}.json", state)
                passed = 2 if arm == "fixed_mechanism" else min(4, g + (2 if arm == "joint" else 1))
                report = {"passed": passed, "total": 4, "mechanism_hash": digest(m)}
                reports = {"acceptance": report, "transfer": report}
                if g == rounds:
                    reports["no_memory"] = {"passed": 1, "total": 4, "mechanism_hash": digest(m)}
                    reports["wide_context_baseline"] = {"passed": 3, "total": 4, "mechanism_hash": digest({"wide": True})}
                versions.append({"stream": seed, "arm": arm, "generation": g, "reports": reports})
                write_json(root / "independent" / str(seed) / arm / f"g{g}.json", reports)
            for r in range(rounds):
                dest = lane / "rounds" / f"r{r:02d}"
                write_json(dest / "experience.json", experience_fixture())
                before, after = states[r], states[r+1]
                write_json(dest / "transition.json", {"stream": seed, "arm": arm, "round": r,
                    "parent_m": digest(before["mechanism"]), "loaded_m_next": digest(after["mechanism"]),
                    "parent_p": digest(before["policy"]), "loaded_p_next": digest(after["policy"]),
                    "mechanism_changed": before["mechanism"] != after["mechanism"],
                    "policy_changed": before["policy"] != after["policy"]})
                if arm != "fixed_mechanism":
                    write_json(dest / "mechanism-search.json", {"initial_mechanism_hash": digest(before["mechanism"]),
                        "policy_hash": digest(before["policy"]), "selected_mechanism_hash": digest(after["mechanism"]),
                        "selected_trial": 0, "trials": [{"status": "executed", "gain": .25, "action": {"modules": ["memory"], "operator": "rewrite", "parent": "current"}},
                            {"status": "invalid_candidate", "effect": None}]})
                    write_json(dest / "policy-proposal.json", {"status": "invalid_policy"})
                    write_json(dest / "policy-probe.json", {"scope": "meta-development", "future_delta": 1.,
                        "adopted": False, "distinct_selected_mechanisms": True,
                        "forks": {"old": {"trial": {"status": "invalid_candidate"}}, "new": {"trial": {"status": "executed"}}}})
        audits.append({"stream": seed, "generation": rounds, "future_delta": -.25,
                       "raw_future_delta": -.25, "valid_search_pair": True,
                       "policy_distinct": True, "old_policy_hash": "fixture-policy-0", "new_policy_hash": "fixture-policy-2",
                       "distinct_selected_mechanisms": False, "old_passed": 3, "new_passed": 2, "total": 4})
    write_json(root / "independent.json", {"status": "completed", "versions": versions, "policy_audits": audits})
    write_json(root / "model-calls/request.json", {"status": "completed", "purpose": "continual_task",
        "metadata": {"arm": "joint", "phase": "online"}, "request_body": "SYNTHETIC_PRIVATE_CONTENT",
        "usage": {"total_tokens": 23},
        "physical_attempts": [{"status": "failed", "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}},
                              {"status": "completed", "usage": {"prompt_tokens": 20, "completion_tokens": 3, "total_tokens": 23}}]})
    write_json(root / "model-calls/audit.json", {"status": "failed", "purpose": "continual_diagnosis",
        "metadata": {"phase": "independent_policy_audit"}, "physical_attempts": [{"status": "failed"}]})


class ContinualAnalysisTests(unittest.TestCase):
    def test_fixed_stream_bootstrap_and_exact_sign_permutations(self):
        pairs = [{"stream": 1, "left": .75, "right": .5}, {"stream": 2, "left": .5, "right": .25}]
        first = paired_statistics(pairs)
        self.assertEqual(first, paired_statistics(pairs))
        self.assertEqual(first["mean_difference"], .25)
        self.assertEqual(first["bootstrap_percentile_95_ci"], [.25, .25])
        self.assertEqual(first["sign_flip_assignments"], 4)
        self.assertEqual(first["exact_sign_flip_two_sided_p"], .5)
        self.assertIsNone(paired_statistics([])["mean_difference"])
        zero = paired_statistics([{"stream": 1, "left": 0, "right": 0}])
        self.assertEqual(zero["exact_sign_flip_two_sided_p"], 1.)

    def test_memory_chain_requires_actual_links_and_separates_task_success(self):
        fixture = experience_fixture()
        report = memory_chain(fixture, stream=1, arm="joint", round_index=0, path="fixture.json")
        self.assertTrue(report["structural_chain_complete"])
        self.assertTrue(report["effective_closed_loop"])
        self.assertEqual(report["chains"][0]["source_family"], "rule-lineage")
        # The linked fact is a source policy, not a token: no expected-source shortcut.
        fixture["traces"][1]["feedback"]["passed"] = False
        report = memory_chain(fixture, stream=1, arm="joint", round_index=0, path="fixture.json")
        self.assertTrue(report["structural_chain_complete"])
        self.assertFalse(report["all_four_tasks_passed"])
        self.assertFalse(report["effective_closed_loop"])
        fixture["traces"][2]["trace"]["write_events"] = []
        report = memory_chain(fixture, stream=1, arm="joint", round_index=0, path="fixture.json")
        self.assertFalse(report["structural_chain_complete"])
        self.assertFalse(report["chains"][0]["replacement_observed"])

    def test_missing_step_or_lineage_cannot_be_invented(self):
        fixture = experience_fixture()
        fixture["traces"][3]["trace"]["selected_memories"][0]["source_family"] = "different-lineage"
        report = memory_chain(fixture, stream=1, arm="joint", round_index=0, path="fixture.json")
        self.assertFalse(report["structural_chain_complete"])
        fixture["traces"] = fixture["traces"][:3]
        report = memory_chain(fixture, stream=1, arm="joint", round_index=0, path="fixture.json")
        self.assertFalse(report["four_steps_present"])
        self.assertFalse(report["effective_closed_loop"])

    def test_full_fixture_outputs_all_versions_and_keeps_negative_independent_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_experiment_fixture(root)
            result = analyze(root)
            self.assertEqual(result["status"], "completed_readout")
            self.assertEqual(len(result["versions"]), 18)
            self.assertEqual(result["terminal_joint_minus_fixed_p"]["acceptance"]["mean_difference"], .25)
            self.assertEqual(result["independent_policy_audit"]["primary"]["mean_difference"], -.25)
            self.assertFalse(result["independent_policy_audit"]["meta_development_used_as_independent"])
            self.assertEqual(result["adoptions"]["101/fixed_mechanism"]["mechanism_adoptions"], 0)
            self.assertEqual(result["adoptions"]["101/joint"]["mechanism_adoptions"], 2)
            self.assertEqual(result["adoptions"]["101/joint"]["policy_adoptions"], 2)
            self.assertEqual(result["current_minus_wide_context_baseline"]["joint"]["mean_difference"], .25)
            self.assertFalse(any("hash mismatch" in warning for warning in result["warnings"]))
            calls = result["calls"]
            self.assertEqual(calls["totals"]["physical_attempts"], 3)
            self.assertEqual(calls["totals"]["total_tokens"], 35)
            self.assertEqual(calls["totals"]["attempts_without_usage"], 1)
            self.assertIn("shared_policy_audit", calls["by_arm_and_purpose"])
            self.assertTrue(any(row["status"] == "invalid_candidate" for row in result["diagnostics"]))
            for name in ("analysis.json", "RESULTS.md", "index.html", "memory-chain.json"):
                self.assertTrue((root / name).exists())
                self.assertNotIn("SYNTHETIC_PRIVATE_CONTENT", (root / name).read_text())
            markup = (root / "index.html").read_text()
            self.assertNotIn("</script><script>NOT_EXECUTABLE", markup)
            self.assertIn("\\u003c/script", markup)
            self.assertIn("structural fixture", result["source_scope"])

    def test_missing_readout_remains_unavailable_not_zero_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "manifest.json", {"rounds": 2, "seeds": [1], "arms": list(ARMS), "source_scope": "fixture"})
            result = analyze(root)
            self.assertEqual(result["status"], "partial_readout")
            self.assertEqual(result["observed_independent_versions"], 0)
            self.assertIsNone(result["terminal_joint_minus_fixed_p"]["acceptance"]["mean_difference"])
            self.assertIsNone(result["curves"]["acceptance"]["joint"][0]["mean_stream_rate"])
            self.assertIsNone(result["independent_policy_audit"]["primary"])

    def test_duplicate_observation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_experiment_fixture(root)
            source = read_json(root / "independent.json")
            source["versions"].append(deepcopy(source["versions"][0]))
            write_json(root / "independent.json", source)
            with self.assertRaisesRegex(ValueError, "Duplicate independent version"):
                analyze(root)

    def test_invalid_policy_pair_retains_operational_outcome_without_effect_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_experiment_fixture(root)
            source = read_json(root / "independent.json")
            source["policy_audits"][0].update(valid_search_pair=False, future_delta=None,
                raw_future_delta=.75, new_passed=4, old_passed=1)
            write_json(root / "independent.json", source)
            primary = analyze(root)["independent_policy_audit"]["primary"]
            self.assertEqual(primary["n_valid"], 1)
            self.assertEqual(primary["total_observed"], 2)
            self.assertEqual(primary["invalid_pairs"], 1)
            self.assertEqual(primary["mean_difference"], -.25)
            self.assertEqual(primary["all_attempt_operational_raw_outcomes"]["mean_difference"], .25)
            self.assertIsNone(primary["observations"][0]["future_delta"])

    def test_identical_policy_positive_calibration_is_not_evolved_policy_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_experiment_fixture(root)
            source = read_json(root / "independent.json")
            for audit in source["policy_audits"]:
                audit.update(policy_distinct=False, old_policy_hash="same-policy", new_policy_hash="same-policy",
                             future_delta=.75, raw_future_delta=.75, old_passed=1, new_passed=4,
                             distinct_selected_mechanisms=True)
            write_json(root / "independent.json", source)
            primary = analyze(root)["independent_policy_audit"]["primary"]
            self.assertEqual(primary["mean_difference"], .75)
            self.assertEqual(primary["same_policy_calibration"]["n"], 2)
            self.assertEqual(primary["same_policy_calibration"]["mean_difference"], .75)
            self.assertEqual(primary["valid_and_distinct_policy_statistics"]["n"], 0)
            self.assertFalse(primary["evolved_policy_effect_evidence_available"])
            self.assertEqual(primary["evolved_policy_inference_status"], "no_distinct_policy_evidence")
            self.assertIn("no_distinct_policy_evidence", (root / "RESULTS.md").read_text())

    def test_secondary_diagnostic_uses_visible_required_token_and_policy_sources(self):
        report = _secondary_report(diagnostic_fixture(), path="fixture.json")
        self.assertEqual(report["status"], "partially_available")
        self.assertEqual(report["metrics"]["answer_ok"]["passed"], 1)
        self.assertEqual(report["metrics"]["answer_ok"]["observed"], 3)
        self.assertEqual(report["metrics"]["evidence_ok"]["passed"], 1)
        support = report["metrics"]["visible_support_sufficient"]
        self.assertEqual((support["passed"], support["observed"], support["unknown"], support["not_required"]), (1, 2, 1, 1))
        self.assertTrue(report["case_checks"][0]["visible_support_sufficient"])
        self.assertFalse(report["case_checks"][0]["answer_ok"])
        self.assertEqual(report["case_checks"][1]["missing_source_ids"], ["policy-source"])
        self.assertFalse(report["case_checks"][1]["visible_support_sufficient"])
        self.assertEqual(report["case_checks"][2]["support_status"], "not_required")

    def test_secondary_missing_raw_is_unavailable_not_zero(self):
        missing = _secondary_report(None, path=None)
        self.assertEqual(missing["status"], "unavailable")
        self.assertIsNone(missing["metrics"]["answer_ok"]["passed"])
        self.assertIsNone(missing["metrics"]["visible_support_sufficient"]["rate"])
        pooled = _aggregate_secondary([missing, _secondary_report(diagnostic_fixture(), path="fixture.json")])
        self.assertEqual(pooled["streams_with_raw_traces"], 1)
        self.assertEqual(pooled["streams_without_raw_traces"], 1)
        self.assertEqual(pooled["metrics"]["visible_support_sufficient"]["rate"], .5)
        empty = _aggregate_secondary([missing, missing])
        self.assertIsNone(empty["metrics"]["answer_ok"]["passed"])
        self.assertIsNone(empty["observed_traces"])

    def test_secondary_addition_does_not_change_primary_policy_or_adoption_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_experiment_fixture(root)
            before = analyze(root)
            self.assertTrue(all(row["status"] == "unavailable"
                                for row in before["secondary_pre_readout_diagnostics"]["terminal"]))
            path = root / "independent/101/joint/g2.json"
            raw = read_json(path)
            diagnostic = diagnostic_fixture()
            diagnostic["mechanism_hash"] = raw["acceptance"]["mechanism_hash"]
            raw["acceptance"] = diagnostic
            write_json(path, raw)
            after = analyze(root)
            self.assertEqual(before["terminal_joint_minus_fixed_p"], after["terminal_joint_minus_fixed_p"])
            self.assertEqual(before["independent_policy_audit"], after["independent_policy_audit"])
            self.assertEqual(before["adoptions"], after["adoptions"])
            secondary = after["secondary_pre_readout_diagnostics"]
            self.assertFalse(secondary["primary_substitution_allowed"])
            self.assertFalse(secondary["version_selection_allowed"])
            terminal = next(row for row in secondary["terminal"] if row["arm"] == "joint" and row["split"] == "acceptance")
            self.assertEqual(terminal["streams_with_raw_traces"], 1)
            self.assertEqual(terminal["metrics"]["visible_support_sufficient"]["passed"], 1)
            self.assertIn("Secondary pre-readout diagnostics", (root / "RESULTS.md").read_text())


class ResumeReceiptCostTests(unittest.TestCase):
    def test_nested_receipts_included_and_duplicate_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = {"id": "original", "status": "completed", "physical_attempts": [
                {"status": "completed", "usage": {"total_tokens": 10}}]}
            write_json(root / "model-calls/original.json", receipt)
            receipt["id"] = "resumed"
            write_json(root / "model-calls/resume-id/new.json", receipt)
            self.assertEqual(_call_statistics(root)["totals"]["total_tokens"], 20)
            write_json(root / "model-calls/another-resume/duplicate.json", receipt)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                _call_statistics(root)

    def test_receipt_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "outside.json", {"id": "outside"})
            (root / "model-calls").mkdir()
            (root / "model-calls/leak.json").symlink_to(root / "outside.json")
            with self.assertRaisesRegex(ValueError, "evidence tree"):
                _call_statistics(root)


if __name__ == "__main__":
    unittest.main()
