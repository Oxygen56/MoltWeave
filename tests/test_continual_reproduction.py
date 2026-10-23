"""Offline guard tests. Synthetic complete-run fixtures are not model results."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("continual_reproduction_wrapper", ROOT / "scripts/reproduce_continual.py")
repro = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repro)


class ContinualReproductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prior = self.root / "original"
        self.prior.mkdir()
        package = self.prior / "frozen-source/moltweave"
        package.mkdir(parents=True)
        # Copy only project source into a private fixture. No original evidence
        # or live module is changed, imported, or executed by these guard tests.
        texts = {}
        for name in repro.SOURCES:
            text = (ROOT / "src/moltweave" / name).read_text()
            (package / name).write_text(text)
            texts[name] = repro.digest(text)
        (package / "__init__.py").write_text(repro.INIT)
        self.manifest = {"schema": 2, "rounds": 1, "seeds": [101], "arms": list(repro.ARMS),
            "model": "synthetic-not-called", "provider_base": "https://synthetic.example.invalid",
            "request_contract": {"fixture": "offline guard checks only"}, "sources": texts,
            "source_scope": "synthetic unit fixture", "protocol": {"fixture": True},
            "partition_hashes": {"101": {"fixture": "not a model measurement"}}}
        self.dump(self.prior / "manifest.json", self.manifest)

    @staticmethod
    def dump(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def archive(self):
        return repro.verify_archive(self.prior)

    def complete_fixture(self, target, *, marker=True):
        """Authored receipts for guard paths, never reported as real run output."""
        target.mkdir(parents=True)
        self.dump(target / "manifest.json", self.manifest)
        versions, completed = {}, []
        for arm in repro.ARMS:
            previous = None
            for generation in range(2):
                state = {"mechanism": {"fixture_m": generation}, "policy": {"fixture_p": generation},
                         "memory": {"fixture": True}, "history": [], "round": generation}
                folder = target / "streams/101" / arm
                self.dump(folder / "versions" / f"g{generation}.json", state)
                versions[f"101/{arm}/g{generation}"] = repro.digest(state)
                if previous is not None:
                    self.dump(folder / "rounds/r00/transition.json", {"status": "completed",
                        "parent_m": repro.digest(previous["mechanism"]), "parent_p": repro.digest(previous["policy"]),
                        "loaded_m_next": repro.digest(state["mechanism"]), "loaded_p_next": repro.digest(state["policy"])})
                previous = state
            completed.append({"seed": 101, "arm": arm, "rounds": 1, "status": "versions_frozen"})
        self.dump(target / "summary.json", {"status": "all_versions_frozen_pending_readout",
            "errors": [], "completed": completed, "frozen_versions": versions})
        if marker:
            archive = self.archive()
            repro.write_exclusive(repro.sidecar(target, "run"), {"phase": "run", "output": str(target.resolve()),
                "source_manifest_sha256": archive["manifest_sha256"], "sources": self.manifest["sources"]})

    def test_default_check_is_offline_does_not_instantiate_or_execute_frozen_host(self):
        with patch.object(repro.subprocess, "run", side_effect=AssertionError("offline check spawned process")), \
                patch("builtins.print"):
            self.assertEqual(repro.main(["--experiment", str(self.prior)]), 0)
        self.assertEqual(set(path.name for path in self.prior.iterdir()), {"manifest.json", "frozen-source"})

    def test_source_change_and_manifest_hash_change_each_fail_before_execution(self):
        path = self.prior / "frozen-source/moltweave/llm.py"
        original = path.read_text()
        path.write_text(original + "\n# changed source\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.archive()
        path.write_text(original)
        altered = deepcopy(self.manifest)
        altered["sources"]["llm.py"] = "0" * 64
        self.dump(self.prior / "manifest.json", altered)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.archive()

    def test_init_code_and_manifest_path_traversal_are_never_executed(self):
        marker = self.root / "should-not-exist"
        init = self.prior / "frozen-source/moltweave/__init__.py"
        init.write_text(f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')\n")
        with self.assertRaisesRegex(ValueError, "docstring"):
            self.archive()
        self.assertFalse(marker.exists())
        init.write_text(repro.INIT)
        altered = deepcopy(self.manifest)
        altered["sources"]["../outside.py"] = altered["sources"].pop("llm.py")
        self.dump(self.prior / "manifest.json", altered)
        with self.assertRaisesRegex(ValueError, "nine-source"):
            self.archive()

    def test_provider_contract_rejects_http_userinfo_query_and_fragment_offline(self):
        for base in ("http://127.0.0.1:9000", "https://synthetic-user:synthetic-pass@example.invalid",
                     "https://example.invalid?credential=synthetic", "https://example.invalid#fragment"):
            with self.subTest(category="unsafe-provider"):
                altered = {**self.manifest, "provider_base": base}
                self.dump(self.prior / "manifest.json", altered)
                with self.assertRaises(ValueError):
                    self.archive()

    def test_output_alias_original_ancestors_existing_and_sidecars_are_protected(self):
        archive = self.archive()
        for output in (self.prior, self.prior / "nested", self.root):
            with self.subTest(path=output.name), self.assertRaises(ValueError):
                repro.verify_output(archive, output, "run")
        alias = self.root / "alias"
        alias.symlink_to(self.prior, target_is_directory=True)
        with self.assertRaises(ValueError):
            repro.verify_output(archive, alias, "run")
        target = self.root / "existing-evidence"
        target.mkdir()
        sentinel = target / "raw.json"
        sentinel.write_text("unaltered evidence")
        with self.assertRaises(ValueError):
            repro.verify_output(archive, target, "run")
        self.assertEqual(sentinel.read_text(), "unaltered evidence")
        fresh = self.root / "failed-attempt"
        repro.write_exclusive(repro.sidecar(fresh, "run"), {"retained_failure": True})
        with self.assertRaises(ValueError):
            repro.verify_output(archive, fresh, "run")

    def test_evaluate_requires_complete_matching_new_run_and_preserves_partial_readout(self):
        archive = self.archive()
        target = self.root / "reproduction"
        self.complete_fixture(target)
        self.assertEqual(repro.verify_output(archive, target, "evaluate"), target.resolve())
        (target / "independent").mkdir()
        sentinel = target / "independent/partial.json"
        sentinel.write_text("original partial evidence")
        with self.assertRaisesRegex(ValueError, "partial readout"):
            repro.verify_output(archive, target, "evaluate")
        self.assertEqual(sentinel.read_text(), "original partial evidence")

    def test_evaluate_detects_state_tamper_and_parent_chain_tamper(self):
        archive = self.archive()
        target = self.root / "reproduction"
        self.complete_fixture(target)
        state = target / "streams/101/joint/versions/g1.json"
        original = state.read_text()
        self.dump(state, {"round": 1, "mechanism": {"tampered": True}})
        with self.assertRaisesRegex(ValueError, "state hash"):
            repro.verify_output(archive, target, "evaluate")
        state.write_text(original)
        transition = target / "streams/101/joint/rounds/r00/transition.json"
        value = json.loads(transition.read_text())
        value["parent_p"] = "0" * 64
        self.dump(transition, value)
        with self.assertRaisesRegex(ValueError, "parent/descendant"):
            repro.verify_output(archive, target, "evaluate")

    def test_broken_readout_symlink_does_not_bypass_output_protection(self):
        archive = self.archive()
        target = self.root / "reproduction"
        self.complete_fixture(target)
        (target / "independent").symlink_to(self.root / "missing-destination", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "partial readout"):
            repro.verify_output(archive, target, "evaluate")

    def test_staging_excludes_cached_bytecode_and_environment_cannot_select_live_package(self):
        cache = self.prior / "frozen-source/moltweave/__pycache__"
        cache.mkdir()
        (cache / "llm.cpython-315.pyc").write_bytes(b"untrusted cached fixture")
        archive = self.archive()
        staging = self.root / "staging"
        staging.mkdir()
        repro.stage_archive(archive, staging)
        self.assertEqual({path.name for path in (staging / "moltweave").iterdir()}, repro.SOURCES | {"__init__.py"})
        with patch.dict(os.environ, {"PYTHONPATH": "/untrusted/live/src", "PYTHONHOME": "/untrusted/home",
                "HTTPS_PROXY": "http://127.0.0.1:9", "MOLTWEAVE_API_KEY": "synthetic-not-used"}, clear=True):
            env = repro.isolated_environment(staging)
        self.assertEqual(env["PYTHONPATH"], str(staging))
        self.assertNotIn("PYTHONHOME", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertEqual(env["MOLTWEAVE_API_KEY"], "synthetic-not-used")

    def test_manifest_pin_and_untracked_python_module_are_checked(self):
        archive = self.archive()
        self.assertEqual(repro.verify_archive(self.prior, archive["manifest_sha256"])["manifest_sha256"],
                         archive["manifest_sha256"])
        with self.assertRaisesRegex(ValueError, "pin mismatch"):
            repro.verify_archive(self.prior, "0" * 64)
        (self.prior / "frozen-source/moltweave/continual_analysis.py").write_text("raise RuntimeError('not frozen')\n")
        with self.assertRaisesRegex(ValueError, "Unexpected Python"):
            self.archive()

    def test_explicit_run_handoff_uses_argument_lists_and_isolated_verified_source(self):
        archive = self.archive()
        target = self.root / "new repro ; $(never-execute-shell)"
        calls = []
        def fake_subprocess(argv, **kwargs):
            self.assertIsInstance(argv, list)
            self.assertFalse(kwargs.get("shell", False))
            self.assertIn("-S", argv)
            self.assertIn("-P", argv)
            staging = Path(kwargs["cwd"])
            self.assertEqual((staging / "moltweave/llm.py").read_text(), archive["texts"]["llm.py"])
            self.assertEqual(kwargs["env"]["PYTHONPATH"], str(staging))
            calls.append((argv, kwargs))
            if "-m" in argv:
                self.assertEqual(argv[argv.index("-m") + 1:argv.index("-m") + 3], ["moltweave.continual", "run"])
                self.assertEqual(argv[argv.index("--output") + 1], str(target.resolve()))
                self.complete_fixture(target, marker=False)
            return SimpleNamespace(returncode=0)
        with patch.object(repro.subprocess, "run", side_effect=fake_subprocess):
            self.assertEqual(repro.execute_phase(archive, target, "run", 2), 0)
        self.assertEqual(len(calls), 2)
        self.assertFalse(Path(calls[0][1]["cwd"]).exists())
        self.assertTrue(repro.sidecar(target, "run").exists())
        self.assertEqual(repro.verify_output(archive, target, "evaluate"), target.resolve())


if __name__ == "__main__":
    unittest.main()
