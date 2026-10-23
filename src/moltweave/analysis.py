"""Paired descriptive analysis; does not select or modify frozen versions."""
from __future__ import annotations
import math
from pathlib import Path
from .common import read_json, write_json


def paired(before: dict, after: dict) -> dict:
    left = {x["task_id"]: x for x in before["traces"]}
    right = {x["task_id"]: x for x in after["traces"]}
    if left.keys() != right.keys():
        raise ValueError("Paired analysis requires exactly the same task identities")
    gains = sum(not left[k]["passed"] and right[k]["passed"] for k in left)
    losses = sum(left[k]["passed"] and not right[k]["passed"] for k in left)
    n = gains + losses
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(gains, losses) + 1)) / 2 ** n) if n else 1.0
    return {"tasks": len(left), "improved": gains, "regressed": losses,
            "both_correct": sum(left[k]["passed"] and right[k]["passed"] for k in left),
            "both_wrong": sum(not left[k]["passed"] and not right[k]["passed"] for k in left),
            "delta_percentage_points": 100 * (gains - losses) / max(1, len(left)),
            "exact_mcnemar_two_sided_p": p,
            "inference_limit": "One run per task; authored correlated templates, one provider. The p-value does not establish open-world generality or independent P benefit."}


def summarize_cost(folder: Path) -> dict:
    calls = list((folder / "model-calls").glob("*.json"))
    usage = {"logical_calls": len(calls), "physical_attempts": 0, "prompt_tokens": 0,
             "completion_tokens": 0, "failed_physical_attempts": 0, "by_purpose": {}}
    for path in calls:
        data = read_json(path)
        attempts = data.get("physical_attempts", [])
        usage["by_purpose"][data["purpose"]] = usage["by_purpose"].get(data["purpose"], 0) + len(attempts)
        for attempt in attempts:
            usage["physical_attempts"] += 1
            usage["failed_physical_attempts"] += int(attempt.get("status") != "completed")
            for name in ("prompt_tokens", "completion_tokens"):
                usage[name] += attempt.get("usage", {}).get(name, 0)
    usage["money"] = "Not estimated: preserve provider usage; pricing/caching should be applied from the actual invoice."
    return usage


def analyze(folder: Path) -> dict:
    summary = read_json(folder / "summary.json")
    last = f"g{len(summary['transitions'])}"
    result = {"cost": summarize_cost(folder), "paired": {}, "posthoc_execution_conditions": {}}
    from .benchmarks import build_suite
    manifest = read_json(folder / "manifest.json")
    for split in ("final", "transfer"):
        first, final = folder / "independent" / split / "g0.json", folder / "independent" / split / f"{last}.json"
        if first.exists() and final.exists():
            result["paired"][split] = paired(read_json(first), read_json(final))
            tasks = {t["id"]: t for t in build_suite(split, seed=manifest["seed"], per_family=manifest["acceptance_per_family"])}
            conditions = {}
            for path in sorted((folder / "independent" / split).glob("g*.json")):
                count = 0
                for trace in read_json(path)["traces"]:
                    context = trace.get("context", {})
                    visible = {r["id"] for r in context.get("memories", []) + context.get("documents", [])}
                    for event in context.get("tool_events", []):
                        if event["result"].get("status") == "ok":
                            visible.update(event["result"].get("evidence_ids", []))
                    expected = tasks[trace["task_id"]]["expected"]
                    checks = trace.get("checks", {})
                    count += int(set(expected["evidence_ids"]) <= visible and checks.get("tool", False) and checks.get("attempts", False))
                conditions[path.stem] = {"sufficient_visible_support_and_correct_tool_sequence": count, "total": len(tasks)}
            result["posthoc_execution_conditions"][split] = conditions
    result["posthoc_condition_scope"] = "Diagnostic after readout: supporting evidence present and actual tool path/attempts correct. Not a replacement for end-to-end answer score, no optimization feedback."
    write_json(folder / "analysis.json", result)
    return result
