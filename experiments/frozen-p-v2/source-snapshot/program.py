"""Bounded executable mechanism IR. Expressions cannot import, access files or call tools."""
from __future__ import annotations
import math
from typing import Any
from .common import digest

OPS = {"add", "sub", "mul", "div", "min", "max", "gt", "ge", "lt", "eq", "and", "or", "not", "if", "neg", "abs", "log1p"}
FEATURES = {"overlap", "age", "trusted", "scope_match", "global_scope", "entity_match", "deprecated", "available", "read_only",
            "attempt", "error_retryable", "error_permanent", "failure_rate", "failure_count", "attempted", "last_gain", "success_rate",
            "is_memory", "is_rag", "is_tools", "is_recovery", "is_prompt", "stagnation"}


def validate_expr(expr: Any, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("Expression nesting exceeds limit")
    if isinstance(expr, (bool, int, float)):
        if not math.isfinite(expr) or abs(expr) > 1e6:
            raise ValueError("Non-finite or excessive constant")
        return
    if not isinstance(expr, dict):
        raise ValueError("Expressions must be constants, variables or operators")
    if set(expr) == {"var"} and expr["var"] in FEATURES:
        return
    if set(expr) != {"op", "args"} or expr["op"] not in OPS:
        raise ValueError("Unsupported expression")
    args = expr["args"]
    if not isinstance(args, list) or not 1 <= len(args) <= 12:
        raise ValueError("Operator requires 1..12 operands")
    op = expr["op"]
    n = len(args)
    if (op in {"if"} and n != 3) or (op in {"not", "neg", "abs", "log1p"} and n != 1) or (op in {"sub", "div", "gt", "ge", "lt", "eq"} and n != 2):
        raise ValueError("Incorrect operator arity")
    for arg in args:
        validate_expr(arg, depth + 1)


def evaluate(expr: Any, features: dict[str, float]) -> float:
    if isinstance(expr, (int, float, bool)):
        return float(expr)
    if "var" in expr:
        return float(features.get(expr["var"], 0))
    op, nodes = expr["op"], expr["args"]
    if op == "if":
        return evaluate(nodes[1] if evaluate(nodes[0], features) else nodes[2], features)
    args = [evaluate(node, features) for node in nodes]
    match op:
        case "add": value = sum(args)
        case "sub": value = args[0] - args[1]
        case "mul":
            value = 1.0
            for arg in args: value *= arg
        case "div": value = args[0] / args[1] if abs(args[1]) > 1e-9 else 0.0
        case "min": value = min(args)
        case "max": value = max(args)
        case "gt": value = float(args[0] > args[1])
        case "ge": value = float(args[0] >= args[1])
        case "lt": value = float(args[0] < args[1])
        case "eq": value = float(args[0] == args[1])
        case "and": value = float(all(args))
        case "or": value = float(any(args))
        case "not": value = float(not args[0])
        case "neg": value = -args[0]
        case "abs": value = abs(args[0])
        case "log1p": value = math.log1p(max(0, args[0]))
        case _: raise ValueError("Unknown opcode")
    if not math.isfinite(value):
        raise ValueError("Program produced non-finite value")
    return max(-1e12, min(1e12, value))


def baseline() -> dict:
    """Ordinary lexical top-k harness. All later changes must come from model proposals."""
    return {"schema": 1,
            "memory_score": {"var": "overlap"}, "rag_score": {"var": "overlap"},
            "tool_score": {"var": "overlap"}, "retry": 0,
            "memory_top_k": 2, "rag_top_k": 2, "max_attempts": 3,
            "prompt": "Answer the user using the supplied evidence and tool results. Return JSON with answer (string), evidence_ids (list of IDs). Do not invent facts.",
            "policy": {"score": {"var": "failure_rate"}, "branches": 2}}


def validate_program(program: dict) -> None:
    if set(program) != set(baseline()):
        raise ValueError("Fixed program schema may not be altered")
    if program["schema"] != 1:
        raise ValueError("Unsupported schema")
    for name in ("memory_score", "rag_score", "tool_score", "retry"):
        validate_expr(program[name])
    for name in ("memory_top_k", "rag_top_k"):
        if type(program[name]) is not int or not 1 <= program[name] <= 6:
            raise ValueError("Context top-k must be 1..6")
    if type(program["max_attempts"]) is not int or not 1 <= program["max_attempts"] <= 3:
        raise ValueError("Retry budget must be 1..3")
    if not isinstance(program["prompt"], str) or not 1 <= len(program["prompt"]) <= 5000:
        raise ValueError("Invalid prompt")
    if set(program["policy"]) != {"score", "branches"}:
        raise ValueError("Fixed policy interface")
    validate_expr(program["policy"]["score"])
    if type(program["policy"]["branches"]) is not int or not 1 <= program["policy"]["branches"] <= 3:
        raise ValueError("Policy branches must be 1..3")


MODULES = ("memory", "rag", "tools", "recovery", "prompt")
MODULE_FIELDS = {"memory": ("memory_score", "memory_top_k"), "rag": ("rag_score", "rag_top_k"),
                 "tools": ("tool_score",), "recovery": ("retry", "max_attempts"), "prompt": ("prompt",)}


def choose_modules(program: dict, state: dict) -> list[dict]:
    choices = []
    for module in MODULES:
        features = dict(state.get(module, {}))
        for name in MODULES:
            features[f"is_{name}"] = float(module == name)
        choices.append({"module": module, "score": evaluate(program["policy"]["score"], features), "features": features})
    return sorted(choices, key=lambda x: (-x["score"], MODULES.index(x["module"])))[:program["policy"]["branches"]]


def program_id(program: dict) -> str:
    validate_program(program)
    return digest(program)
