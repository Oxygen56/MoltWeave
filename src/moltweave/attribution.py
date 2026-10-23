"""Reporting-only component attribution for a frozen v3 mechanism program.

This module neither proposes candidates nor selects versions. The five declared
variants are all evaluated, including zero gains and regressions.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import urllib.parse

from .benchmarks import build_suite, suite_hash
from .common import digest, read_json, write_json
from .program import validate_program
from .runtime import evaluate_suite

ADAPTER_VERSION = "frozen-v3-component-attribution-v1"
VARIANT_ORDER = ("baseline", "memory_top_k_only", "memory_score_only", "tool_score_only", "full_g4")


def _function_ast(source: str, name: str) -> str:
    tree = ast.parse(source)
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.dump(function, include_attributes=False)


def load_variants(experiment: Path) -> tuple[dict, dict, dict[str, dict]]:
    """Verify archived v3 provenance and live execution equivalence before use."""
    manifest, summary = read_json(experiment / "manifest.json"), read_json(experiment / "summary.json")
    if manifest["generations_requested"] != 4 or summary.get("status") != "versions_frozen_pending_independent_evaluation":
        raise ValueError("This declared component readout requires a completed frozen four-generation source run")
    archive = experiment / "frozen-source" / "moltweave"
    current = Path(__file__).resolve().parent
    archive_checks, current_checks = {}, {}
    for filename, expected in manifest["frozen_code"].items():
        archived_hash = digest((archive / filename).read_text())
        if archived_hash != expected:
            raise ValueError("Archived v3 source hash mismatch: " + filename)
        archive_checks[filename] = archived_hash
        current_checks[filename] = digest((current / filename).read_text())
    # These files implement data generation, actual model execution and scoring.
    # evolution.py is not imported by this reporting adapter.
    for filename in ("benchmarks.py", "runtime.py", "llm.py", "common.py"):
        if current_checks[filename] != archive_checks[filename]:
            raise ValueError("Live execution differs from the archived v3 contract: " + filename)
    if _function_ast((archive / "program.py").read_text(), "evaluate") != _function_ast((current / "program.py").read_text(), "evaluate"):
        raise ValueError("Mechanism expression evaluator changed")
    programs = []
    for index in range(5):
        program = read_json(experiment / "generations" / f"g{index}" / "program.json")
        validate_program(program)
        if index:
            transition = read_json(experiment / "generations" / f"g{index-1}" / "transition.json")
            if transition["parent_hash"] != digest(programs[-1]) or transition["next_hash"] != digest(program):
                raise ValueError("Frozen program lineage changed")
        programs.append(program)
    if summary["final_program_hash"] != digest(programs[-1]):
        raise ValueError("Terminal program does not match frozen summary")
    baseline, terminal = programs[0], programs[-1]
    if baseline["memory_top_k"] != 2:
        raise ValueError("The predeclared fixed-k score transplant requires baseline k=2")
    variants = {name: deepcopy(baseline) for name in VARIANT_ORDER}
    variants["memory_top_k_only"]["memory_top_k"] = terminal["memory_top_k"]
    variants["memory_score_only"]["memory_score"] = deepcopy(terminal["memory_score"])
    variants["tool_score_only"]["tool_score"] = deepcopy(terminal["tool_score"])
    variants["full_g4"] = deepcopy(terminal)
    for variant in variants.values():
        validate_program(variant)
    provenance = {"archive": str(archive.resolve()), "archived_source_hashes": archive_checks,
                  "live_source_hashes": current_checks, "runtime_exact_match": True,
                  "expression_evaluator_ast_equal": True,
                  "program_validation_note": "Current stricter validation only; unchanged candidate programs and identical evaluator AST",
                  "source_g0_hash": digest(baseline), "source_g4_hash": digest(terminal),
                  "source_run_seed": manifest["seed"],
                  "source_run_final_used_for_selection": False}
    return manifest, provenance, variants


def _receipt_totals(directory: Path) -> dict:
    totals = {"logical_calls": 0, "physical_attempts": 0, "completed_logical_calls": 0,
              "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
              "physical_attempts_with_usage": 0}
    for path in sorted(directory.glob("*.json")):
        receipt = read_json(path)
        totals["logical_calls"] += 1
        totals["completed_logical_calls"] += receipt.get("status") == "completed"
        attempts = receipt.get("physical_attempts", [])
        totals["physical_attempts"] += len(attempts)
        # Count each physical attempt, including failed parses with billed usage.
        for attempt in attempts:
            usage = attempt.get("usage", {})
            totals["physical_attempts_with_usage"] += bool(usage)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                totals[key] += usage.get(key, 0) or 0
    return totals


def _metrics(report: dict, baseline: dict) -> dict:
    traces, base = report["traces"], {x["task_id"]: x for x in baseline["traces"]}
    improved = sum(bool(x["passed"]) and not base[x["task_id"]]["passed"] for x in traces)
    regressed = sum(not x["passed"] and bool(base[x["task_id"]]["passed"]) for x in traces)
    return {"passed": report["passed"], "total": report["total"], "rate": report["rate"],
            "families": report["families"], "gain_vs_baseline_count": report["passed"] - baseline["passed"],
            "gain_vs_baseline_percentage_points": 100 * (report["rate"] - baseline["rate"]),
            "paired_improved": improved, "paired_regressed": regressed,
            "check_failures": {check: sum(not x["checks"][check] for x in traces)
                               for check in ("answer", "evidence", "tool", "attempts")},
            "average_selected_memory_records": sum(len(x["context"]["memories"]) for x in traces) / len(traces),
            "average_selected_document_records": sum(len(x["context"]["documents"]) for x in traces) / len(traces),
            "average_context_characters": sum(len(json.dumps(x["context"], ensure_ascii=False)) for x in traces) / len(traces)}


def run_attribution(experiment_dir: str | Path, output_dir: str | Path, *,
                    seed: int = 41, per_family: int = 10, workers: int = 10, client=None) -> dict:
    experiment, output = Path(experiment_dir), Path(output_dir)
    source_manifest, provenance, variants = load_variants(experiment)
    tasks = build_suite("final", seed, per_family=per_family)
    if seed == source_manifest["seed"]:
        raise ValueError("The component readout requires new facts, not the original final set")
    output.mkdir(parents=True, exist_ok=False)
    if client is None:
        from .llm import ModelClient
        client = ModelClient(output / "calls", model=source_manifest["model"])
    if not getattr(client, "output_dir", None) or client.model != source_manifest["model"]:
        raise ValueError("A matching real ModelClient with retained physical receipts is required")
    manifest = {"adapter": ADAPTER_VERSION,
                "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "source_experiment": str(experiment.resolve()), "source_manifest_hash": digest(source_manifest),
                "provenance": provenance, "status": "prepared", "started_at": time.time(),
                "data": {"kind": "author_synthetic_component_readout", "generator_split": "final",
                         "seed": seed, "per_family": per_family, "questions": len(tasks),
                         "suite_hash": suite_hash(tasks), "task_ids": [x["id"] for x in tasks],
                         "original_final_reused": False},
                "variant_order": list(VARIANT_ORDER),
                "program_hashes": {label: digest(program) for label, program in variants.items()},
                "changes_vs_baseline": {label: [key for key in program if program[key] != variants["baseline"][key]]
                                        for label, program in variants.items()},
                "model": client.model, "endpoint_host": urllib.parse.urlparse(getattr(client, "base_url", "")).hostname,
                "workers": workers, "max_tokens": 2048, "temperature_requested": 0,
                "planned_logical_calls": len(tasks) * len(variants),
                "selection_allowed": False, "optimization_feedback_allowed": False,
                "policy_executed": False, "policy_advantage_estimated": False,
                "execution_order_note": "Declared variant blocks, shared fixed task order, ten workers; one noisy readout, not repeated causal estimation"}
    for label, program in variants.items():
        write_json(output / "programs" / f"{label}.json", program)
    # All variants, source hashes and the new data hash are sealed before any call.
    write_json(output / "manifest.json", manifest)
    reports = {}
    try:
        manifest["status"] = "running"
        write_json(output / "manifest.json", manifest)
        for label in VARIANT_ORDER:
            report = evaluate_suite(tasks, variants[label], client, label, workers=workers)
            reports[label] = report
            write_json(output / "reports" / f"{label}.json", report)
            if report.get("measurement_errors"):
                raise RuntimeError("Incomplete model/API/parse measurement; no mechanism conclusion")
            print(json.dumps({"variant_completed": label, "passed": report["passed"], "total": report["total"]}), flush=True)
        metrics = {label: _metrics(report, reports["baseline"]) for label, report in reports.items()}
        result = {"status": "completed", "metrics": metrics,
                  "calls": _receipt_totals(Path(client.output_dir)), "finished_at": time.time(),
                  "selection_allowed": False, "optimization_feedback_allowed": False,
                  "claim_scope": "One predeclared five-variant component readout on 70 new authored synthetic cases; no P causal estimate, no real-business claim",
                  "context_interpretation": "memory_top_k_only isolates more lexical memory context; memory_score_only keeps k=2; full_g4 includes multiple changed mechanisms and their interactions",
                  "uncertainty": "One stochastic model readout per task/variant; retain all zero gains and regressions, do not choose or tune a version"}
        write_json(output / "result.json", result)
        manifest.update({"status": "completed", "finished_at": time.time()})
        write_json(output / "manifest.json", manifest)
        return result
    except Exception as error:
        manifest.update({"status": "measurement_incomplete", "finished_at": time.time()})
        write_json(output / "manifest.json", manifest)
        write_json(output / "failed.json", {"status": "measurement_incomplete", "error_type": type(error).__name__,
                                           "completed_variants": list(reports),
                                           "measurement_errors": {label: report.get("measurement_errors", 0)
                                                                  for label, report in reports.items()},
                                           "calls": _receipt_totals(Path(client.output_dir)),
                                           "optimization_feedback_allowed": False})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("output")
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--per-family", type=int, default=10)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    result = run_attribution(args.experiment, args.output, seed=args.seed,
                             per_family=args.per_family, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
