"""Authored structural fixtures only: no model, billing, or formal experiment."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("continual_resume_wrapper", ROOT / "scripts/resume_continual.py")
resume = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resume)
guard = resume.guard


class ContinualResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "interrupted-synthetic-fixture"
        package = self.root / "frozen-source/moltweave"
        package.mkdir(parents=True)
        self.loop_source = "def run_lane(output, client, seed, arm, rounds):\n    for r in range(rounds):\n        seen.append((seed, arm, r))\n"
        sources = {}
        for name in guard.SOURCES:
            text = self.loop_source if name == "continual.py" else "# Unexecuted synthetic fixture source.\n"
            if name == "continual_program.py":
                text = "def baseline_mechanism(): return {'fixture_m': 0}\ndef validate_mechanism(v):\n    if not isinstance(v, dict) or not ('fixture_m' in v or 'rejected' in v): raise ValueError('invalid fixture M')\n"
            elif name == "continual_policy.py":
                text = "def baseline_policy(): return {'fixture_p': 0}\ndef validate_policy(v):\n    if not isinstance(v, dict) or 'fixture_p' not in v: raise ValueError('invalid fixture P')\n"
            elif name == "continual_memory.py":
                text = "class ContinualMemory:\n    def __init__(self, state=None): self.state = {'fixture_round': 0} if state is None else state\n    def snapshot(self): return self.state\n"
            (package / name).write_text(text)
            sources[name] = guard.digest(text)
        (package / "__init__.py").write_text(guard.INIT)
        self.manifest = {"schema": 2, "rounds": 2, "seeds": [101], "arms": list(guard.ARMS),
            "model": "synthetic-never-called", "provider_base": "https://synthetic.example.invalid",
            "request_contract": {}, "sources": sources, "source_scope": "structural unit fixture",
            "protocol": {}, "partition_hashes": {"101": {}}}
        self.dump(self.root / "manifest.json", self.manifest)
        self.dump(self.root / "summary.json", {"status": "aborted_measurement_incomplete", "completed": [],
            "errors": [{"fixture": "operator reported HTTP402; no actual provider call"}]})
        self.dump(self.root / "model-calls/old.json", {"id": "synthetic-old-call", "fixture": True})
        self.dump(self.root / "interruption-diagnosis.json", {"fixture": True, "http_status": 402})
        for arm, checkpoint in (("fixed_mechanism", 2), ("fixed_p", 1), ("joint", 0)):
            self.dump(self.lane(arm) / "versions/g0.json", self.state(0))
            for round_index in range(checkpoint):
                self.write_round(arm, round_index)
            if checkpoint < 2:
                self.dump(self.lane(arm) / "rounds" / f"r{checkpoint:02d}" / "experience.json",
                          {"partial_score": 999 if arm == "fixed_p" else 0, "uncommitted": True})
                self.dump(self.lane(arm) / "ABORTED.json", {"fixture": "original-aborted-do-not-rewrite"})

    @staticmethod
    def dump(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n")

    def lane(self, arm):
        return self.root / "streams/101" / arm

    @staticmethod
    def state(generation):
        return {"mechanism": {"fixture_m": generation}, "policy": {"fixture_p": generation},
                "memory": {"fixture_round": generation}, "history": [] if generation == 0 else [{"committed": generation}], "round": generation}

    def write_round(self, arm, round_index, *, rejects=True):
        folder = self.lane(arm)
        before, after = self.state(round_index), self.state(round_index + 1)
        dest = folder / "rounds" / f"r{round_index:02d}"
        self.dump(dest / "experience.json", {"final_memory": after["memory"], "fixture": "committed observation"})
        self.dump(dest / "transition.json", {"status": "completed", "parent_m": guard.digest(before["mechanism"]),
            "parent_p": guard.digest(before["policy"]), "loaded_m_next": guard.digest(after["mechanism"]),
            "loaded_p_next": guard.digest(after["policy"])})
        self.dump(folder / "versions" / f"g{round_index + 1}.json", after)
        if arm != "fixed_mechanism":
            trials = [{"status": "executed", "mechanism": after["mechanism"],
                       "evaluation": {"passed": 3, "guard_passed": 1}}]
            if rejects:
                trials += [{"status": "executed", "mechanism": {"rejected": "unsafe-high-score"},
                            "evaluation": {"passed": 999, "guard_passed": 0}},
                           {"status": "executed", "mechanism": {"rejected": "safe-lower-score"},
                            "evaluation": {"passed": 2, "guard_passed": 1}}]
            self.dump(dest / "mechanism-search.json", {"selected_mechanism": after["mechanism"],
                "baseline": {"guard_passed": 1}, "trials": trials})

    def archive(self):
        return guard.verify_archive(self.root)

    def test_default_check_preserves_all_evidence_and_never_spawns_provider(self):
        before = resume.inventory(self.root)
        with patch.object(resume.subprocess, "run", side_effect=AssertionError("check must not spawn")), patch("builtins.print"):
            self.assertEqual(resume.main(["--experiment", str(self.root), "--check"]), 0)
        self.assertEqual(resume.inventory(self.root), before)
        plan = resume.build_plan(self.archive())
        self.assertEqual((plan["completed_lane_count"], plan["pending_lane_count"]), (1, 2))
        self.assertFalse(plan["exactly_once"])

    def test_round_body_is_unchanged_and_completed_rounds_are_not_replayed(self):
        module, body_hash = resume.round_loop(self.loop_source)
        original = ast.parse(self.loop_source).body[0].body[0]
        self.assertEqual(ast.dump(ast.Module(body=original.body, type_ignores=[]), include_attributes=False),
                         ast.dump(ast.Module(body=module.body[0].body, type_ignores=[]), include_attributes=False))
        namespace = {"seen": [], "seed": 101, "arm": "joint", "start_round": 1, "rounds": 3}
        exec(compile(module, "<synthetic-structural-loop-only>", "exec"), namespace, namespace)
        self.assertEqual(namespace["seen"], [(101, "joint", 1), (101, "joint", 2)])
        self.assertEqual(len(body_hash), 64)

    def test_rejected_state_is_rebuilt_with_original_protection_priority_and_sticks(self):
        self.write_round("fixed_p", 1, rejects=False)
        inspected = resume.inspect_lane(self.root, 101, "fixed_p", 2)
        self.assertEqual(inspected["rejected"], {"rejected": "safe-lower-score"})
        self.assertEqual([row["round"] for row in inspected["rejected_provenance"]], [0])
        self.assertEqual(inspected["start_round"], 2)

    def test_missing_checkpoint_or_changed_parent_chain_is_rejected(self):
        (self.lane("fixed_mechanism") / "versions/g1.json").unlink()
        with self.assertRaisesRegex(ValueError, "gap"):
            resume.build_plan(self.archive())
        self.dump(self.lane("fixed_mechanism") / "versions/g1.json", self.state(1))
        path = self.lane("fixed_mechanism") / "rounds/r01/transition.json"
        value = json.loads(path.read_text())
        value["parent_p"] = "0" * 64
        self.dump(path, value)
        with self.assertRaisesRegex(ValueError, "parent chain"):
            resume.build_plan(self.archive())

    def test_changed_frozen_source_and_started_readout_block_resume(self):
        source = self.root / "frozen-source/moltweave/llm.py"
        original = source.read_text()
        source.write_text(original + "# changed\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.archive()
        source.write_text(original)
        (self.root / "independent").mkdir()
        with self.assertRaisesRegex(ValueError, "readout"):
            resume.build_plan(self.archive())

    def test_diagnosis_is_not_invented_and_g0_must_be_frozen_empty_baseline(self):
        (self.root / "interruption-diagnosis.json").unlink()
        plan = resume.build_plan(self.archive())
        self.assertIsNone(plan["interruption_reason"]["http_status"])
        self.assertEqual(plan["interruption_reason"]["category"], "unknown_interruption")
        self.dump(self.root / "interruption-diagnosis.json", {"http_status": 503})
        self.assertEqual(resume.build_plan(self.archive())["interruption_reason"]["http_status"], 503)
        altered = self.state(0)
        altered["history"] = [{"unearned": "history"}]
        self.dump(self.lane("joint") / "versions/g0.json", altered)
        with self.assertRaisesRegex(ValueError, "g0 must equal"):
            resume.build_plan(self.archive())

    def current_failure(self, *, actual="JSONDecodeError", claimed="JSONDecodeError", round_index=1):
        receipt_id = "a" * 32
        self.dump(self.root / "model-calls/resume-structural" / (receipt_id + ".json"), {
            "id": receipt_id, "status": "failed", "error_type": actual,
            "metadata": {"stream": 101, "arm": "fixed_p", "round": round_index},
            "physical_attempts": [{"status": "failed", "error_type": actual} for _ in range(3)]})
        summary = {"status": "aborted_measurement_incomplete", "completed": [],
            "resume_ledger": "resume-history/structural/plan.json", "errors": [{"seed": 101, "arm": "fixed_p",
                "error_type": "RuntimeError", "error": f"Model call failed ({claimed}); see local receipt {receipt_id}"}]}
        self.dump(self.root / "summary.json", summary)
        return receipt_id

    def test_current_parse_receipt_overrides_historical_402_without_changing_replay_rule(self):
        before = resume.build_plan(self.archive())
        receipt_id = self.current_failure()
        inventory = resume.inventory(self.root)
        plan = resume.build_plan(self.archive())
        reason = plan["interruption_reason"]
        self.assertEqual(reason["category"], "model_json_parse_measurement_exhausted")
        self.assertIsNone(reason["http_status"])
        self.assertEqual(reason["failures"][0]["receipt_id"], receipt_id)
        self.assertEqual(reason["failures"][0]["physical_attempts"], 3)
        self.assertEqual(plan["historical_interruption_reasons"][0]["http_status"], 402)
        self.assertEqual(plan["commit_rule"], before["commit_rule"])
        self.assertEqual(plan["round_body_ast_hash"], before["round_body_ast_hash"])
        self.assertEqual(plan["lanes"], before["lanes"])
        self.assertEqual(resume.inventory(self.root), inventory)

    def test_current_cause_uses_receipt_not_exception_text_and_never_inherits_old_http_status(self):
        self.current_failure(actual="HTTPError", claimed="JSONDecodeError")
        reason = resume.build_plan(self.archive())["interruption_reason"]
        self.assertEqual(reason["category"], "provider_http_error")
        self.assertIsNone(reason["http_status"])
        self.current_failure(round_index=0)
        reason = resume.build_plan(self.archive())["interruption_reason"]
        self.assertEqual(reason["category"], "unknown_interruption")
        self.assertFalse(reason["failures"][0]["verified"])
        self.assertIsNone(reason["http_status"])

    def test_unavailable_or_duplicate_current_receipt_does_not_become_historical_402(self):
        receipt_id = self.current_failure()
        path = self.root / "model-calls/resume-structural" / (receipt_id + ".json")
        original = json.loads(path.read_text())
        path.unlink()
        reason = resume.build_plan(self.archive())["interruption_reason"]
        self.assertEqual(reason["category"], "unknown_interruption")
        self.assertIsNone(reason["http_status"])
        self.dump(path, original)
        self.dump(self.root / "model-calls/duplicate" / (receipt_id + ".json"), original)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            resume.build_plan(self.archive())

    def test_resumed_error_without_receipt_does_not_reuse_old_provider_diagnosis(self):
        self.dump(self.root / "summary.json", {"status": "aborted_measurement_incomplete", "completed": [],
            "resume_ledger": "resume-history/structural/plan.json", "errors": [{"seed": 101, "arm": "fixed_p", "error_type": "RuntimeError"}]})
        reason = resume.build_plan(self.archive())["interruption_reason"]
        self.assertEqual(reason["category"], "unknown_interruption")
        self.assertIsNone(reason["http_status"])

    def test_symlinked_stream_version_round_and_ledger_parents_are_rejected(self):
        for name in ("streams", "streams/101/fixed_p/versions", "streams/101/fixed_p/rounds", "resume-history"):
            with self.subTest(path=name):
                path = self.root / name
                saved = path.with_name(path.name + "-original")
                existed = path.exists()
                if existed:
                    path.rename(saved)
                path.symlink_to(saved if existed else self.root / "elsewhere", target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "Symlink"):
                    resume.build_plan(self.archive())
                path.unlink()
                if existed:
                    saved.rename(path)

    def test_lock_and_failed_provider_preflight_do_not_move_partial_evidence(self):
        archive = self.archive()
        lock = self.root / ".continual-resume.lock"
        guard.write_exclusive(lock, {"id": "another-controller"})
        with patch.object(resume.subprocess, "run", side_effect=AssertionError("locked")), self.assertRaises(FileExistsError):
            resume.execute_resume(archive)
        self.assertEqual(guard.read_json(lock)["id"], "another-controller")
        lock.unlink()
        before = resume.inventory(self.root)
        with patch.object(resume.subprocess, "run", return_value=SimpleNamespace(returncode=2)), \
                self.assertRaisesRegex(ValueError, "preflight"):
            resume.execute_resume(archive)
        self.assertFalse(lock.exists())
        self.assertEqual(resume.inventory(self.root), before)

    def test_full_controller_preserves_commits_aborts_and_calls_archives_all_partial_scores(self):
        archive = self.archive()
        original_summary = (self.root / "summary.json").read_bytes()
        old_call = (self.root / "model-calls/old.json").read_bytes()
        fixed_bytes = {str(path.relative_to(self.root)): path.read_bytes() for path in self.lane("fixed_mechanism").rglob("*.json")}
        aborts = {arm: (self.lane(arm) / "ABORTED.json").read_bytes() for arm in ("fixed_p", "joint")}
        observed = []

        def fake_process(argv, **kwargs):
            self.assertIsInstance(argv, list)
            self.assertFalse(kwargs.get("shell", False))
            if "--worker-plan" not in argv:
                return SimpleNamespace(returncode=0)
            plan_path = Path(argv[argv.index("--worker-plan") + 1])
            job = guard.read_json(plan_path)
            observed.append(job)
            self.assertTrue((plan_path.parent / "archive-completed.json").is_file())
            pending = [lane for lane in job["plan"]["lanes"] if not lane["completed"]]
            self.assertEqual({lane["arm"] for lane in pending}, {"fixed_p", "joint"})
            for lane in pending:
                self.assertFalse((self.root / lane["partial_round"]).exists())
                for round_index in range(lane["start_round"], 2):
                    self.write_round(lane["arm"], round_index)
            self.dump(self.root / job["new_receipt_directory"] / "new.json", {"id": "synthetic-new-call"})
            guard.write_exclusive(plan_path.parent / "worker-result.json", {"completed": [], "errors": []})
            return SimpleNamespace(returncode=0)

        with patch.object(resume.subprocess, "run", side_effect=fake_process):
            result = resume.execute_resume(archive, concurrency=2)
        self.assertEqual(result["status"], "all_versions_frozen_pending_readout")
        job = observed[0]
        ledger = self.root / result["resume_ledger"]
        self.assertEqual((ledger.parent / "original-summary.json").read_bytes(), original_summary)
        self.assertEqual((self.root / "model-calls/old.json").read_bytes(), old_call)
        for name, data in fixed_bytes.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        for arm, data in aborts.items():
            self.assertEqual((self.lane(arm) / "ABORTED.json").read_bytes(), data)
        moved = guard.read_json(ledger.parent / "archive-completed.json")["moved"]
        scores = [guard.read_json(self.root / row["archived_path"] / "experience.json")["partial_score"] for row in moved]
        self.assertEqual(sorted(scores), [0, 999])
        self.assertTrue(all(row["used_for_score_or_selection"] is False for row in moved))
        self.assertFalse(job["exactly_once"])
        self.assertEqual(len(guard.read_json(self.root / "summary.json")["frozen_versions"]), 9)
        self.assertFalse((self.root / ".continual-resume.lock").exists())

    def test_all_committed_lanes_can_finalize_summary_without_any_provider_process(self):
        self.write_round("fixed_p", 1)
        self.write_round("joint", 0)
        self.write_round("joint", 1)
        with patch.object(resume.subprocess, "run", side_effect=AssertionError("completed lanes must not rerun")):
            result = resume.execute_resume(self.archive())
        self.assertEqual(result["completed_lanes"], 3)
        with patch.object(resume.subprocess, "run", side_effect=AssertionError("nothing to resume")):
            self.assertEqual(resume.execute_resume(self.archive())["status"], "nothing_to_resume")


if __name__ == "__main__":
    unittest.main()
