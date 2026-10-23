import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from moltweave.common import write_json, digest
from moltweave.evolution import require_measurement, MeasurementError, independent_evaluation, policy_state
from moltweave.program import baseline
from moltweave.evolution import propose_mechanism


class EvolutionContractTests(unittest.TestCase):
    def test_unobserved_candidate_effect_is_not_zero_gain(self):
        history = [{"module": "memory", "status": "awaiting_owner_approval", "gain": None},
                   {"module": "memory", "status": "invalid_candidate", "gain": None}]
        state = policy_state({"traces": []}, history)["memory"]
        self.assertEqual(state["stagnation"], 0)
        self.assertEqual(state["has_gain"], 0)
        self.assertEqual(state["blocked_count"], 1)
        self.assertEqual(state["invalid_count"], 1)

    def test_invalid_program_is_repaired_by_a_second_model_request(self):
        class FixtureClient:
            def __init__(self): self.calls = []
            def complete(self, messages, **kwargs):
                self.calls.append((list(messages), kwargs))
                return {"changes": {"retry": "retry on temporary" if len(self.calls) == 1 else {"var": "error_retryable"}}}
        fixture = FixtureClient()
        result = propose_mechanism(fixture, baseline(), "recovery", [], [], 0)
        self.assertEqual(result["program"]["retry"], {"var": "error_retryable"})
        self.assertEqual(fixture.calls[1][1]["purpose"], "mechanism_repair")
        self.assertIn("validation_error", fixture.calls[1][0][-1]["content"])

    def test_measurement_failures_are_not_mechanism_failures(self):
        with self.assertRaises(MeasurementError):
            require_measurement({"measurement_errors": 1})
        require_measurement({"measurement_errors": 0, "passed": 0})

    def test_unfrozen_run_cannot_read_final(self):
        with tempfile.TemporaryDirectory() as directory:
            write_json(Path(directory) / "manifest.json", {"generations_requested": 1})
            write_json(Path(directory) / "summary.json", {"status": "still_running"})
            with self.assertRaisesRegex(ValueError, "frozen"):
                independent_evaluation(directory, object())

    def test_modified_frozen_generation_cannot_read_final(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = baseline()
            write_json(root / "manifest.json", {"generations_requested": 1})
            write_json(root / "summary.json", {"status": "versions_frozen_pending_independent_evaluation",
                     "transitions": [{"parent_hash": digest(program), "next_hash": digest(program)}], "final_program_hash": digest(program)})
            write_json(root / "generations/g0/program.json", program)
            tampered = copy.deepcopy(program)
            tampered["prompt"] += "modified"
            write_json(root / "generations/g1/program.json", tampered)
            with self.assertRaisesRegex(ValueError, "modified"):
                independent_evaluation(root, object())


if __name__ == "__main__":
    unittest.main()
