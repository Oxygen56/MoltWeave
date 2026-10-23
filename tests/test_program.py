import copy
import unittest
from moltweave.program import baseline, validate_program, evaluate, choose_modules
from moltweave.runtime import run_task


class ProgramTests(unittest.TestCase):
    def test_ir_cannot_execute_strings_or_import(self):
        for expr in ({"python": "open('/etc/passwd')"}, {"var": "__import__"}, "1+1", {"op": "call", "args": [1]}):
            program = baseline()
            program["memory_score"] = expr
            with self.assertRaises(ValueError):
                validate_program(program)

    def test_bounded_algorithm_really_executes(self):
        expression = {"op": "if", "args": [{"var": "trusted"}, {"op": "sub", "args": [10, {"var": "age"}]}, -100]}
        self.assertEqual(evaluate(expression, {"trusted": 1, "age": 2}), 8)
        self.assertEqual(evaluate(expression, {"trusted": 0, "age": 0}), -100)

    def test_policy_changes_actual_branch_decision(self):
        program = baseline()
        state = {"memory": {"failure_rate": .9, "stagnation": 2}, "rag": {"failure_rate": .8}}
        before = choose_modules(program, state)
        program["policy"]["score"] = {"op": "sub", "args": [{"var": "failure_rate"}, {"var": "stagnation"}]}
        after = choose_modules(program, state)
        self.assertNotEqual(before[0]["module"], after[0]["module"])

    def test_scope_is_fixed_and_future_tool_result_is_hidden(self):
        class Recorder:
            def complete(self, messages, **kwargs):
                self.messages = str(messages)
                return {"answer": "missing", "evidence_ids": []}
        client = Recorder()
        task = {"id": "test", "family": "tool_recovery", "user_id": "alice", "query": "lookup",
                "memories": [{"id": "private", "text": "BOB_SECRET", "scope": "bob"}], "documents": [],
                "tools": [{"name": "lookup", "description": "lookup", "outcomes": [
                    {"status": "transient_error", "retryable": True},
                    {"status": "ok", "text": "FUTURE_RESULT", "evidence_ids": ["future"]}]}],
                "expected": {"answer": "FUTURE_RESULT", "tool": "lookup", "tool_attempts": 2, "evidence_ids": ["future"]}}
        trace = run_task(task, baseline(), client)
        self.assertNotIn("BOB_SECRET", client.messages)
        self.assertNotIn("FUTURE_RESULT", client.messages)
        self.assertFalse(trace["passed"])


if __name__ == "__main__":
    unittest.main()
