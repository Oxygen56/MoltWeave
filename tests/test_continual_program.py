"""Offline contracts; no model or benchmark outcomes are fabricated."""
import copy
import math
import unittest

from moltweave.continual_program import (MEMORY_FEATURES, baseline_mechanism, evaluate,
                                        validate_expression, validate_mechanism)


class ContinualProgramTests(unittest.TestCase):
    def test_baseline_has_exact_shared_schema_and_valid_independent_trees(self):
        mechanism = baseline_mechanism()
        self.assertEqual(set(mechanism), {"memory_score", "memory_write", "memory_top_k", "rag_score",
                                         "rag_top_k", "tool_score", "retry", "max_attempts", "prompt"})
        validate_mechanism(mechanism)
        self.assertIsNot(mechanism["memory_score"], mechanism["rag_score"])

    def test_verified_write_avoids_duplicates_and_stale_conflicts(self):
        rule = baseline_mechanism()["memory_write"]
        self.assertTrue(evaluate(rule, {"verified": 1}))
        for features in [{"verified": 0}, {"verified": 1, "duplicate": 1},
                         {"verified": 1, "conflict": 1, "is_newer": 0}]:
            self.assertFalse(evaluate(rule, features))
        self.assertTrue(evaluate(rule, {"verified": 1, "conflict": 1, "is_newer": 1}))

    def test_baseline_ranks_current_authoritative_entity_and_key_evidence(self):
        mechanism = baseline_mechanism()
        for name in ("memory_score", "rag_score"):
            expr = mechanism[name]
            strong = {"overlap": 0.8, "entity_match": 1, "key_match": 1, "authority": 1,
                      "verified": 1, "source_match": 1, "scope_match": 1, "age": 0}
            for change in [{"age": 100}, {"authority": 0}, {"entity_match": 0},
                           {"key_match": 0}, {"deprecated": 1}]:
                weaker = dict(strong, **change)
                self.assertGreater(evaluate(expr, strong), evaluate(expr, weaker))

    def test_available_read_only_tools_and_transient_retry_are_real_baselines(self):
        mechanism = baseline_mechanism()
        self.assertGreater(evaluate(mechanism["tool_score"], {"available": 1, "read_only": 1}),
                           evaluate(mechanism["tool_score"], {"available": 0, "read_only": 0}))
        self.assertTrue(evaluate(mechanism["retry"], {"attempt": 1, "error_retryable": 1}))
        self.assertFalse(evaluate(mechanism["retry"], {"attempt": 1, "error_retryable": 1, "error_permanent": 1}))
        self.assertFalse(evaluate(mechanism["retry"], {"attempt": 3, "error_retryable": 1}))

    def test_ir_rejects_code_unknown_features_wrong_arity_and_excess(self):
        bad = ["__import__('os').system('x')", {"op": "exec", "args": [1]},
               {"var": "secret"}, {"var": "age", "eval": "x"},
               {"op": "if", "args": [1, 2]}, float("nan"), float("inf"), 10**1000,
               {"op": "add", "args": list(range(13))}]
        nested = 0
        for _ in range(14):
            nested = {"op": "neg", "args": [nested]}
        bad.append(nested)
        for expr in bad:
            with self.subTest(expr=str(expr)[:80]), self.assertRaises(ValueError):
                validate_expression(expr)
        with self.assertRaises(ValueError):
            validate_expression({"var": "attempt"}, MEMORY_FEATURES)
        validate_expression({"var": "key_match"}, MEMORY_FEATURES)

    def test_mechanism_contract_rejects_authority_changes_and_boolean_budgets(self):
        baseline = baseline_mechanism()
        for changes in [{"permissions": "all"}, {"schema": 2}, {"memory_top_k": True},
                        {"max_attempts": 100}, {"retry": {"var": "authority"}},
                        {"memory_score": {"var": "failure_count"}}, {"prompt": ""}]:
            candidate = copy.deepcopy(baseline)
            candidate.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_mechanism(candidate)


if __name__ == "__main__":
    unittest.main()
