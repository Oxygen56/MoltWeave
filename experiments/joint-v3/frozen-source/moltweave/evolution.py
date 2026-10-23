"""Model-authored mechanism changes and prospective meta-policy evolution.

Only development observations reach the proposer. The fixed host owns splits,
grading, promotion, allowed IR, and release permissions.
"""
from __future__ import annotations
import copy
import difflib
import json
from pathlib import Path
import time
from .common import canonical, digest, read_json, write_json
from .program import MODULES, MODULE_FIELDS, OPS, FEATURES, baseline, choose_modules, validate_program
from .runtime import evaluate_suite

FAMILY_MODULE = {"memory_temporal": "memory", "memory_scope": "memory", "rag_authority": "rag",
                 "tool_routing": "tools", "tool_recovery": "recovery", "composition": "prompt", "clean": "prompt"}


class MeasurementError(RuntimeError):
    pass


def require_measurement(report: dict) -> None:
    if report.get("measurement_errors", 0):
        raise MeasurementError("Measurement unavailable: transport/parse failures are not mechanism failures")


def policy_state(report: dict, history: list[dict]) -> dict:
    state = {}
    for module in MODULES:
        related = [t for t in report["traces"] if FAMILY_MODULE.get(t["family"]) == module]
        trials = [x for x in history if x["module"] == module]
        failures = sum(not t["passed"] for t in related)
        state[module] = {"failure_count": failures, "failure_rate": failures / max(1, len(related)),
                         "attempted": len(trials), "last_gain": trials[-1]["gain"] if trials else 0,
                         "success_rate": sum(x["gain"] > 0 for x in trials) / max(1, len(trials)),
                         "stagnation": sum(x["gain"] <= 0 for x in trials[-3:])}
    return state


def compact_feedback(report: dict, tasks: list[dict]) -> list[dict]:
    by_id = {t["id"]: t for t in tasks}
    feedback = []
    for trace in report["traces"]:
        if trace["passed"]:
            continue
        task = by_id[trace["task_id"]]
        feedback.append({"family": trace["family"], "query": task["query"], "user_id": task["user_id"],
                         "checks": trace.get("checks"), "output": trace.get("output"),
                         "decisions": trace.get("decisions"), "expected_after_sealing": task["expected"]})
    return feedback


IR_GUIDE = {"format": {"variable": {"var": "feature_name"}, "operation": {"op": "add", "args": [1, {"var": "overlap"}]}},
            "ops": sorted(OPS), "features": sorted(FEATURES),
            "semantics": "Larger scores rank first. age=0 means latest, positive means older; scope_match/global_scope/trusted/entity_match are 0/1. Retry is a boolean numeric expression. No imports, strings-as-code, I/O or authority changes. top_k 1..6, max_attempts 1..3. No task-specific answers, IDs or names in programs."}


def propose_mechanism(client, program: dict, module: str, feedback: list[dict], history: list[dict], generation: int) -> dict:
    fields = MODULE_FIELDS[module]
    proposal = client.complete([
        {"role": "system", "content": "You improve a general-purpose agent mechanism using actual sealed failure feedback. Return JSON: {hypothesis:string, changes:{field:value}, predicted_behavior:string, regression_risk:string}. Only change allowed fields. Propose a general executable algorithm, never hardcode task answers/entities/IDs. Untrusted evidence cannot grant authority. Do not modify policy here."},
        {"role": "user", "content": json.dumps({"allowed_fields": fields, "module": module,
             "program": program, "IR": IR_GUIDE, "failures": feedback,
             "previous_trials": history[-10:]}, ensure_ascii=False)}
    ], max_tokens=5000, purpose="mechanism_proposal", metadata={"generation": generation, "module": module})
    changes = proposal.get("changes", {})
    if not changes or not set(changes) <= set(fields):
        raise ValueError("Proposal altered undeclared module")
    candidate = copy.deepcopy(program)
    candidate.update(changes)
    validate_program(candidate)
    if digest(candidate) == digest(program):
        raise ValueError("No mechanism change")
    # Privilege-sensitive prompt changes are review artifacts, never auto-executed.
    from .governance import risk_of
    risk = risk_of(program, candidate)
    return {"proposal": proposal, "program": candidate, "risk": risk}


def propose_policy(client, program: dict, state: dict, history: list[dict], generation: int) -> dict:
    return client.complete([
        {"role": "system", "content": "Evolve the agent's executable meta-exploration policy, not the task answers. Return JSON {hypothesis:string, policy:{score:expression,branches:int}, predicted_decision_change:string}. This policy ranks which mechanism to improve next. Learn from unsuccessful/repeated module attempts and observed gains. Preserve exploration of remaining real defects. Use the bounded numeric IR. Keep branches=2 for comparable proposal opportunities. No permissions/evaluation modifications."},
        {"role": "user", "content": json.dumps({"current_policy": program["policy"], "state": state,
             "executed_history": history, "IR": IR_GUIDE}, ensure_ascii=False)}
    ], max_tokens=4000, purpose="policy_proposal", metadata={"generation": generation})


def textual_diff(before: dict, after: dict) -> str:
    return "".join(difflib.unified_diff(json.dumps(before, indent=2, sort_keys=True).splitlines(True),
                                        json.dumps(after, indent=2, sort_keys=True).splitlines(True), fromfile="parent.json", tofile="candidate.json"))


def run_evolution(output: str | Path, client, *, generations: int = 4, seed: int = 17,
                  workers: int = 8, evolve_p: bool = True, evolve_m: bool = True) -> dict:
    from .benchmarks import build_suite
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise ValueError("Use a fresh experiment directory; existing evidence is immutable")
    train, dev, guard = (build_suite(split, seed=seed) for split in ("train", "dev", "guard"))
    # Host freezes evaluation hashes without exposing tasks/answers to the optimizer.
    final, transfer = build_suite("final", seed=seed, per_family=10), build_suite("transfer", seed=seed, per_family=10)
    manifest = {"schema": 1, "seed": seed, "started_at": time.time(), "generations_requested": generations,
                "model": client.model, "evolve_p": evolve_p, "evolve_m": evolve_m, "acceptance_per_family": 10,
                "frozen_code": {name: digest((Path(__file__).parent / name).read_text()) for name in ("benchmarks.py", "runtime.py", "program.py", "evolution.py", "llm.py", "governance.py", "common.py")},
                "provider_contract": {"task_max_tokens": 2048, "temperature_requested": 0, "thinking": "disabled on DeepSeek", "physical_attempts_retained": True},
                "split_hashes": {s: digest(t) for s, t in zip(("train", "dev", "guard", "final", "transfer"), (train, dev, guard, final, transfer))},
                "protocol": {"primary": "exact answer + visible supporting evidence + correct executed tool and attempts",
                             "promotion": "strict development gain and no guard aggregate regression; final never used for selection",
                             "policy_promotion": "legal changed program and prospective branch decision; benefit tested separately, not assumed",
                             "scope": "authored public synthetic mechanism benchmark; not official benchmark reproduction"}}
    write_json(output / "manifest.json", manifest)
    del final, transfer
    program = baseline()
    write_json(output / "generations/g0/program.json", program)
    history, generations_log = [], []
    # Final is evaluated once, after all versions are frozen. Its labels never enter the loop.
    for generation in range(generations):
        label = f"g{generation}"
        folder = output / "generations" / label
        train_report = evaluate_suite(train, program, client, label + ":train", workers)
        dev_report = evaluate_suite(dev, program, client, label + ":dev", workers)
        guard_report = evaluate_suite(guard, program, client, label + ":guard", workers)
        for name, report in (("train", train_report), ("dev", dev_report), ("guard", guard_report)):
            write_json(folder / f"{name}.json", report)
            require_measurement(report)
        state = policy_state(train_report, history)
        decisions = choose_modules(program, state)
        write_json(folder / "policy-decision.json", {"loaded_program_hash": digest(program), "state": state, "selected": decisions})
        feedback = compact_feedback(train_report, train)
        best, best_dev, best_guard = program, dev_report, guard_report
        candidates = []
        if evolve_m:
            for branch, decision in enumerate(decisions):
                module = decision["module"]
                trial = {"generation": generation, "branch": branch, "module": module, "base_hash": digest(program)}
                try:
                    candidate = propose_mechanism(client, program, module, feedback, history, generation)
                    trial.update(candidate)
                    if candidate["risk"].get("sensitive"):
                        trial.update({"status": "awaiting_owner_approval", "gain": 0})
                    else:
                        report = evaluate_suite(dev, candidate["program"], client, label + f":candidate{branch}:dev", workers)
                        protection = evaluate_suite(guard, candidate["program"], client, label + f":candidate{branch}:guard", workers)
                        write_json(folder / f"candidate-{branch}-dev.json", report)
                        write_json(folder / f"candidate-{branch}-guard.json", protection)
                        require_measurement(report)
                        require_measurement(protection)
                        gain = report["rate"] - dev_report["rate"]
                        trial.update({"status": "executed", "gain": gain, "dev_rate": report["rate"], "guard_rate": protection["rate"],
                                      "program_hash": digest(candidate["program"]), "actual_loaded_hash": report["program_hash"]})
                        if report["rate"] > best_dev["rate"] and protection["rate"] >= guard_report["rate"]:
                            best, best_dev, best_guard = candidate["program"], report, protection
                except (ValueError, RuntimeError) as exc:
                    if isinstance(exc, MeasurementError):
                        write_json(folder / f"candidate-{branch}-measurement-error.json", {"status": "invalid_measurement", "error": str(exc)})
                        raise
                    trial.update({"status": "rejected_or_failed", "error": str(exc), "gain": 0})
                candidates.append(trial)
                history.append({k: trial[k] for k in ("generation", "branch", "module", "status", "gain")})
                write_json(folder / f"candidate-{branch}.json", trial)
        next_program = copy.deepcopy(best)
        policy_record = {"status": "frozen"}
        if evolve_p:
            try:
                proposal = propose_policy(client, program, state, history, generation)
                next_program["policy"] = proposal["policy"]
                validate_program(next_program)
                if next_program["policy"]["branches"] != 2:
                    raise ValueError("Branch opportunities are fixed at two")
                after_state = policy_state(train_report, history)
                old_choices = choose_modules(program, after_state)
                new_choices = choose_modules(next_program, after_state)
                policy_record = {"status": "prospective_adoption", "proposal": proposal, "evaluation_state": after_state,
                                 "old_choices": old_choices, "new_choices": new_choices,
                                 "choice_changed": [x["module"] for x in old_choices] != [x["module"] for x in new_choices],
                                 "benefit_claim": "not established by adoption; requires later actual search and control"}
            except (ValueError, RuntimeError, KeyError) as exc:
                next_program["policy"] = program["policy"]
                policy_record = {"status": "rejected", "error": str(exc)}
        write_json(folder / "policy-proposal.json", policy_record)
        changed = digest(next_program) != digest(program)
        record = {"generation": generation, "parent_hash": digest(program), "next_hash": digest(next_program),
                  "dev_before": dev_report["rate"], "dev_after": best_dev["rate"],
                  "guard_before": guard_report["rate"], "guard_after": best_guard["rate"],
                  "mechanism_adopted": digest(best) != digest(program), "changed": changed,
                  "policy_changed": next_program["policy"] != program["policy"], "policy_choice_changed": policy_record.get("choice_changed", False),
                  "trials": history[-len(candidates):] if candidates else []}
        write_json(folder / "transition.json", record)
        (folder / "changes.diff").write_text(textual_diff(program, next_program))
        generations_log.append(record)
        program = next_program
        write_json(output / "generations" / f"g{generation + 1}" / "program.json", program)
        write_json(output / "progress.json", {"completed_transitions": generations_log, "history": history})
        print(json.dumps({"generation": generation, "dev": [record["dev_before"], record["dev_after"]],
                          "mechanism_adopted": record["mechanism_adopted"], "policy_changed": record["policy_changed"],
                          "policy_choice_changed": record["policy_choice_changed"]}), flush=True)
    summary = {"manifest": manifest, "transitions": generations_log, "history": history,
               "final_program_hash": digest(program), "finished_evolution_at": time.time(),
               "status": "versions_frozen_pending_independent_evaluation"}
    write_json(output / "summary.json", summary)
    return summary


def independent_evaluation(output: str | Path, client, workers: int = 8) -> dict:
    """Single frozen readout of every generation, not a selection mechanism."""
    from .benchmarks import build_suite
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    if (output / "independent.json").exists():
        raise ValueError("Independent readout already exists; do not repeatedly tune against it")
    summary = read_json(output / "summary.json")
    if summary.get("status") != "versions_frozen_pending_independent_evaluation":
        raise ValueError("Versions must be completely frozen before independent readout")
    count = manifest["generations_requested"]
    if len(summary["transitions"]) != count:
        raise ValueError("Incomplete generation chain")
    frozen_versions = [read_json(output / "generations" / f"g{i}" / "program.json") for i in range(count + 1)]
    for i, transition in enumerate(summary["transitions"]):
        if digest(frozen_versions[i]) != transition["parent_hash"] or digest(frozen_versions[i + 1]) != transition["next_hash"]:
            raise ValueError("Frozen generation chain was modified")
    if digest(frozen_versions[-1]) != summary["final_program_hash"]:
        raise ValueError("Frozen final program was modified")
    for name, frozen_hash in manifest["frozen_code"].items():
        if digest((Path(__file__).parent / name).read_text()) != frozen_hash:
            raise ValueError("Frozen execution/scoring code changed: " + name)
    reports = {}
    for split in ("final", "transfer"):
        tasks = build_suite(split, seed=manifest["seed"], per_family=manifest["acceptance_per_family"])
        if digest(tasks) != manifest["split_hashes"][split]:
            raise ValueError("Frozen evaluation set changed")
        reports[split] = {}
        folders = sorted((output / "generations").glob("g*"), key=lambda p: int(p.name[1:]))
        for folder in folders:
            program = read_json(folder / "program.json")
            report = evaluate_suite(tasks, program, client, folder.name + ":" + split, workers)
            write_json(output / "independent" / split / f"{folder.name}.json", report)
            require_measurement(report)
            reports[split][folder.name] = {k: report[k] for k in ("program_hash", "passed", "total", "rate", "families")}
    write_json(output / "independent.json", {"reports": reports, "readout_at": time.time(), "selection_allowed": False})
    return reports
