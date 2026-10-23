"""Offline resume plan, or explicitly resume committed v0.2 checkpoints.

The frozen nine-file host is never edited. Its original per-round AST body is
executed with checkpoint locals and a later range start. This is maintained host
recovery code, never model-authored Python or an automatically evolved program.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from types import ModuleType


_SPEC = importlib.util.spec_from_file_location("_continual_reproduction_guard", Path(__file__).with_name("reproduce_continual.py"))
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)


def raw_sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def within_root(root, path):
    """Reject a symlink in any evidence parent, including not-yet-made ledgers."""
    original_root, path = Path(root).absolute(), Path(path).absolute()
    try:
        relative = path.relative_to(original_root)
    except ValueError:
        raise ValueError("Evidence path is outside experiment root") from None
    root = original_root.resolve()
    current = root
    for part in relative.parts:
        if part == "..":
            raise ValueError("Evidence path escapes experiment root")
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink in experiment evidence or ledger path")
    if not current.resolve().is_relative_to(root):
        raise ValueError("Resolved evidence path is outside experiment root")
    return current


def validate_checkpoint_programs(archive, lanes):
    """Load only staged pure validators/baselines; never load the model client."""
    prefix = "_moltweave_resume_validation_" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="moltweave-resume-validation-") as temporary:
        staging = Path(temporary)
        guard.stage_archive(archive, staging)
        package = ModuleType(prefix)
        package.__path__ = [str(staging / "moltweave")]
        package.__package__ = prefix
        sys.modules[prefix] = package
        try:
            programs = importlib.import_module(prefix + ".continual_program")
            policies = importlib.import_module(prefix + ".continual_policy")
            memories = importlib.import_module(prefix + ".continual_memory")
            baseline = {"mechanism": programs.baseline_mechanism(), "policy": policies.baseline_policy(),
                        "memory": memories.ContinualMemory().snapshot(), "history": [], "round": 0}
            for lane in lanes:
                folder = archive["experiment"] / "streams" / str(lane["seed"]) / lane["arm"]
                if guard.digest(guard.read_json(folder / "versions/g0.json")) != guard.digest(baseline):
                    raise ValueError("g0 must equal frozen baseline M/P, empty memory and empty history")
                for generation in range(lane["start_round"] + 1):
                    state = guard.read_json(folder / "versions" / f"g{generation}.json")
                    programs.validate_mechanism(state["mechanism"])
                    policies.validate_policy(state["policy"])
                    memories.ContinualMemory(state["memory"])
                if lane["rejected"] is not None:
                    programs.validate_mechanism(lane["rejected"])
            if prefix + ".llm" in sys.modules:
                raise ValueError("Offline validation unexpectedly imported a model client")
        finally:
            for name in list(sys.modules):
                if name == prefix or name.startswith(prefix + "."):
                    del sys.modules[name]


def round_loop(source):
    """Only change range start; retain the exact parsed frozen round body."""
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_lane"]
    if len(functions) != 1:
        raise ValueError("Expected one frozen run_lane")
    loops = [node for node in functions[0].body if isinstance(node, ast.For)
             and isinstance(node.target, ast.Name) and node.target.id == "r"]
    if len(loops) != 1 or ast.unparse(loops[0].iter) != "range(rounds)" or loops[0].orelse:
        raise ValueError("Unsupported frozen run_lane loop shape")
    original = loops[0]
    body_hash = guard.digest(ast.dump(ast.Module(body=original.body, type_ignores=[]), include_attributes=False))
    resumed = copy.deepcopy(original)
    resumed.iter = ast.Call(func=ast.Name(id="range", ctx=ast.Load()),
                            args=[ast.Name(id="start_round", ctx=ast.Load()), ast.Name(id="rounds", ctx=ast.Load())], keywords=[])
    module = ast.fix_missing_locations(ast.Module(body=[resumed], type_ignores=[]))
    return module, body_hash


def inventory(folder):
    if not folder.exists():
        return []
    result = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Evidence inventory must not contain symlinks")
        if path.is_file():
            result.append({"path": str(path.relative_to(folder)), "size": path.stat().st_size, "sha256": raw_sha(path)})
    return result


def verify_inventory(folder, entries):
    for entry in entries:
        path = folder / entry["path"]
        if path.is_symlink() or not path.is_file() or raw_sha(path) != entry["sha256"]:
            raise ValueError("Previously retained evidence changed")


def rejected_from_completed(folder, states, arm):
    rejected, provenance = None, []
    if arm == "fixed_mechanism":
        return rejected, provenance
    for round_index in range(len(states) - 1):
        path = folder / "rounds" / f"r{round_index:02d}" / "mechanism-search.json"
        search = guard.read_json(path)
        if guard.digest(search["selected_mechanism"]) != guard.digest(states[round_index + 1]["mechanism"]):
            raise ValueError("Committed search selection differs from checkpoint")
        candidates = [trial for trial in search["trials"] if trial["status"] == "executed"
                      and guard.digest(trial["mechanism"]) != guard.digest(search["selected_mechanism"])]
        if candidates:
            # Exactly the frozen run_lane rule. Rejected persists if none occur.
            rejected = max(candidates, key=lambda trial: (
                trial["evaluation"]["guard_passed"] >= search["baseline"]["guard_passed"],
                trial["evaluation"]["passed"], trial["evaluation"]["guard_passed"]))["mechanism"]
            provenance.append({"round": round_index, "search_sha256": raw_sha(path), "rejected_hash": guard.digest(rejected)})
    return rejected, provenance


def inspect_lane(root, seed, arm, rounds):
    root = Path(root).resolve()
    folder = within_root(root, root / "streams" / str(seed) / arm)
    within_root(root, folder / "versions")
    within_root(root, folder / "rounds")
    paths = list((folder / "versions").glob("g*.json"))
    if not paths:
        raise ValueError("Every interrupted lane needs its original g0 checkpoint")
    names = {path.name for path in paths}
    generations = sorted(int(path.stem[1:]) for path in paths)
    if (generations != list(range(generations[-1] + 1)) or generations[-1] > rounds
            or names != {f"g{g}.json" for g in generations}):
        raise ValueError("Checkpoint sequence has a gap or unexpected generation")
    states, hashes = [], {}
    for generation in generations:
        path = folder / "versions" / f"g{generation}.json"
        state = guard.read_json(path)
        if state.get("round") != generation or not {"mechanism", "policy", "memory", "history"} <= set(state):
            raise ValueError("Invalid committed checkpoint")
        if generation:
            prior = states[-1]
            transition = guard.read_json(folder / "rounds" / f"r{generation-1:02d}" / "transition.json")
            if (transition.get("status") != "completed" or transition.get("parent_m") != guard.digest(prior["mechanism"])
                    or transition.get("parent_p") != guard.digest(prior["policy"])
                    or transition.get("loaded_m_next") != guard.digest(state["mechanism"])
                    or transition.get("loaded_p_next") != guard.digest(state["policy"])):
                raise ValueError("Committed checkpoint parent chain mismatch")
            experience = guard.read_json(folder / "rounds" / f"r{generation-1:02d}" / "experience.json")
            if guard.digest(experience["final_memory"]) != guard.digest(state["memory"]):
                raise ValueError("Committed factual memory differs from its observed experience")
        states.append(state)
        hashes[f"{seed}/{arm}/g{generation}"] = guard.digest(state)
    start = generations[-1]
    for path in (folder / "rounds").glob("r*"):
        if not path.is_dir() or path.is_symlink() or path.name != f"r{int(path.name[1:]):02d}":
            raise ValueError("Unexpected round evidence path")
        if int(path.name[1:]) > start or int(path.name[1:]) >= rounds:
            raise ValueError("Evidence exists beyond the next uncommitted round")
    rejected, provenance = rejected_from_completed(folder, states, arm)
    partial = folder / "rounds" / f"r{start:02d}"
    return {"seed": seed, "arm": arm, "start_round": start, "completed": start == rounds,
            "checkpoint": str((folder / "versions" / f"g{start}.json").relative_to(root)),
            "checkpoint_sha256": raw_sha(folder / "versions" / f"g{start}.json"),
            "checkpoint_hash": guard.digest(states[-1]), "version_hashes": hashes,
            "rejected": rejected, "rejected_provenance": provenance,
            "partial_round": str(partial.relative_to(root)) if partial.exists() else None,
            "partial_inventory": inventory(partial) if partial.exists() else []}


def build_plan(archive):
    root, manifest = archive["experiment"], archive["manifest"]
    for name in ("streams", "resume-history", "model-calls", "interruption-diagnosis.json"):
        within_root(root, root / name)
    if any((root / name).exists() or (root / name).is_symlink() for name in guard.READOUT_PATHS):
        raise ValueError("Do not resume after independent readout has begun")
    summary = guard.read_json(root / "summary.json")
    if summary.get("status") not in {"aborted_measurement_incomplete", "all_versions_frozen_pending_readout"}:
        raise ValueError("Run must be stopped with a retained summary before resume")
    _, body_hash = round_loop(archive["texts"]["continual.py"])
    lanes = [inspect_lane(root, seed, arm, manifest["rounds"]) for seed in manifest["seeds"] for arm in guard.ARMS]
    validate_checkpoint_programs(archive, lanes)
    diagnosis = root / "interruption-diagnosis.json"
    diagnostic = guard.read_json(diagnosis) if diagnosis.is_file() else {}
    http_status = diagnostic.get("http_status")
    if type(http_status) is not int:
        http_status = None
    return {"schema": 1, "source_manifest_sha256": archive["manifest_sha256"],
            "sources": manifest["sources"], "summary_sha256": raw_sha(root / "summary.json"),
            "round_body_ast_hash": body_hash, "rounds": manifest["rounds"], "lanes": lanes,
            "completed_lane_count": sum(lane["completed"] for lane in lanes),
            "pending_lane_count": sum(not lane["completed"] for lane in lanes),
            "diagnosis_sha256": raw_sha(diagnosis) if diagnosis.is_file() and not diagnosis.is_symlink() else None,
            "interruption_reason": {"http_status": http_status,
                "category": "provider_http402" if http_status == 402 else ("provider_http_error" if http_status else "unknown_interruption"),
                "evidence": "Retained interruption-diagnosis.json numeric http_status only; no inferred cause or rewritten exception"},
            "commit_rule": "Only g(r+1) commits round r. Entire partial r is discarded from selection and replayed.",
            "exactly_once": False}


def atomic_json(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=".resume-write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def archive_partial(root, ledger, plan):
    shutil.copy2(root / "summary.json", ledger / "original-summary.json")
    moved = []
    for lane in plan["lanes"]:
        if lane["completed"]:
            continue
        folder = root / "streams" / str(lane["seed"]) / lane["arm"]
        historical = ledger / "historical-lane-metadata" / str(lane["seed"]) / lane["arm"]
        historical.mkdir(parents=True)
        for name in ("ABORTED.json", "progress.json"):
            if (folder / name).is_file():
                shutil.copy2(folder / name, historical / name)
        if lane["partial_round"]:
            source = root / lane["partial_round"]
            destination = ledger / "discarded-partial-rounds" / str(lane["seed"]) / lane["arm"] / source.name
            destination.parent.mkdir(parents=True)
            verify_inventory(source, lane["partial_inventory"])
            shutil.move(str(source), str(destination))
            moved.append({"old_path": lane["partial_round"], "archived_path": str(destination.relative_to(root)),
                          "used_for_score_or_selection": False, "replay_from_checkpoint": lane["checkpoint"]})
    return moved


def worker(plan_path, staging):
    """Internal child entry; executes only verified frozen per-round statements."""
    job = guard.read_json(Path(plan_path))
    root = Path(job["experiment"])
    if raw_sha(Path(guard.__file__)) != job["guard_sha256"]:
        raise ValueError("Maintained reproduction safety guard changed after planning")
    if (Path(plan_path).resolve() != root / "resume-history" / job["id"] / "plan.json"
            or guard.read_json(root / ".continual-resume.lock").get("id") != job["id"]):
        raise ValueError("Resume worker requires its active controller lock and original ledger")
    archive = guard.verify_archive(root, job["plan"]["source_manifest_sha256"])
    archived = guard.read_json(Path(plan_path).parent / "archive-completed.json")
    for item in archived["moved"]:
        lane = next(lane for lane in job["plan"]["lanes"] if lane["partial_round"] == item["old_path"])
        if (root / item["old_path"]).exists():
            raise ValueError("A replay round has new unarchived evidence")
        verify_inventory(root / item["archived_path"], lane["partial_inventory"])
    pending = [lane for lane in job["plan"]["lanes"] if not lane["completed"]]
    for lane in pending:
        current = inspect_lane(root, lane["seed"], lane["arm"], job["plan"]["rounds"])
        if current["start_round"] != lane["start_round"] or current["partial_round"] is not None:
            raise ValueError("Lane advanced or acquired evidence after planning")
    receipt_folder = root / job["new_receipt_directory"]
    if receipt_folder != root / "model-calls" / f"resume-{job['id']}" or receipt_folder.exists():
        raise ValueError("Resume receipts require their fresh ledger-specific subdirectory")
    guard.write_exclusive(Path(plan_path).parent / "worker-started.json", {"pid": os.getpid(), "started_at": time.time()})
    receipt_folder.mkdir(parents=True)
    import moltweave.continual as host
    from moltweave.continual_memory import ContinualMemory
    from moltweave.continual_policy import propose_policy
    from moltweave.llm import ModelClient
    if Path(host.__file__).resolve() != Path(staging).resolve() / "moltweave/continual.py":
        raise ValueError("Resume worker did not load staged frozen host")
    if host.frozen_sources() != archive["manifest"]["sources"]:
        raise ValueError("Resume worker source contract mismatch")
    loop, body_hash = round_loop(archive["texts"]["continual.py"])
    if body_hash != job["plan"]["round_body_ast_hash"]:
        raise ValueError("Frozen round body changed")
    code = compile(loop, "<verified-frozen-run_lane-round-loop>", "exec")
    client = ModelClient(receipt_folder)
    if client.model != archive["manifest"]["model"] or client.base_url != archive["manifest"]["provider_base"]:
        raise ValueError("Resume model/provider differs from frozen contract")
    client = host.LimitedClient(client, job["concurrency"])

    def one(lane):
        checkpoint = root / lane["checkpoint"]
        if raw_sha(checkpoint) != lane["checkpoint_sha256"]:
            raise ValueError("Checkpoint changed after resume planning")
        state = guard.read_json(checkpoint)
        namespace = dict(vars(host))
        namespace.update({"output": root, "client": client, "seed": lane["seed"], "arm": lane["arm"],
            "rounds": job["plan"]["rounds"], "start_round": lane["start_round"],
            "folder": root / "streams" / str(lane["seed"]) / lane["arm"],
            "mechanism": copy.deepcopy(state["mechanism"]), "policy": copy.deepcopy(state["policy"]),
            "memory": ContinualMemory(copy.deepcopy(state["memory"])), "history": copy.deepcopy(state["history"]),
            "rejected": copy.deepcopy(lane["rejected"]), "propose_policy": propose_policy})
        exec(code, namespace, namespace)  # Audited frozen host AST; never model-supplied Python.
        return {"seed": lane["seed"], "arm": lane["arm"], "rounds": job["plan"]["rounds"], "status": "versions_frozen"}

    completed, errors = [], []
    with ThreadPoolExecutor(max_workers=max(1, len(pending))) as pool:
        futures = {pool.submit(one, lane): lane for lane in pending}
        for future in as_completed(futures):
            lane = futures[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                error = {"seed": lane["seed"], "arm": lane["arm"], "error_type": type(exc).__name__, "error": str(exc)}
                errors.append(error)
                guard.write_exclusive(Path(plan_path).parent / f"ABORTED-{lane['seed']}-{lane['arm']}.json", error)
    guard.write_exclusive(Path(plan_path).parent / "worker-result.json", {"completed": completed, "errors": errors})
    return 0


def execute_resume(archive, *, concurrency=32):
    if type(concurrency) is not int or not 1 <= concurrency <= 128:
        raise ValueError("Concurrency must be 1..128")
    root = archive["experiment"]
    initial = build_plan(archive)
    if not initial["pending_lane_count"] and guard.read_json(root / "summary.json")["status"] == "all_versions_frozen_pending_readout":
        return {"status": "nothing_to_resume", "network_requests": 0}
    identifier = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
    lock = root / ".continual-resume.lock"
    guard.write_exclusive(lock, {"id": identifier, "pid": os.getpid()})
    try:
        plan = build_plan(archive)
        if guard.digest(plan) != guard.digest(initial):
            raise ValueError("Experiment changed while acquiring resume lock")
        with tempfile.TemporaryDirectory(prefix="moltweave-v02-resume-") as temporary:
            staging = Path(temporary)
            expected = guard.stage_archive(archive, staging)
            env = guard.isolated_environment(staging)
            if plan["pending_lane_count"]:
                checked = subprocess.run([sys.executable, "-B", "-S", "-P", "-c", guard.PREFLIGHT, str(staging), str(expected)],
                                         cwd=staging, env=env, capture_output=True, text=True, check=False)
                if checked.returncode:
                    raise ValueError("Frozen provider preflight failed; no replay started")
            ledger = root / "resume-history" / identifier
            within_root(root, ledger)
            ledger.mkdir(parents=True)
            old_calls = inventory(root / "model-calls")
            guard.write_exclusive(ledger / "previous-model-calls.json", {"files": old_calls})
            receipt_directory = f"model-calls/resume-{identifier}"
            job = {"schema": 1, "id": identifier, "experiment": str(root), "plan": plan,
                   "concurrency": concurrency, "new_receipt_directory": receipt_directory,
                   "partial_treatment": "Archive whole uncommitted round before replay; never select from partial scores",
                   "exactly_once": False,
                   "wrapper_sha256": raw_sha(Path(__file__)), "guard_sha256": raw_sha(Path(guard.__file__)),
                   "started_at": time.time()}
            job_path = ledger / "plan.json"
            guard.write_exclusive(job_path, job)
            moved = archive_partial(root, ledger, plan)
            guard.write_exclusive(ledger / "archive-completed.json", {"moved": moved,
                "original_summary_sha256": raw_sha(ledger / "original-summary.json")})
            if plan["pending_lane_count"]:
                result = subprocess.run([sys.executable, "-B", "-S", "-P", str(Path(__file__).resolve()),
                    "--worker-plan", str(job_path), "--staging", str(staging)], cwd=staging, env=env, check=False)
                if result.returncode:
                    raise ValueError("Resume child failed; preserve ledger and any new partial evidence")
            else:
                guard.write_exclusive(ledger / "worker-result.json", {"completed": [], "errors": []})
            verify_inventory(root / "model-calls", old_calls)
            after = build_plan(archive)
            completed = [{"seed": lane["seed"], "arm": lane["arm"], "rounds": plan["rounds"], "status": "versions_frozen"}
                         for lane in after["lanes"] if lane["completed"]]
            failures = guard.read_json(ledger / "worker-result.json")["errors"]
            all_done = not after["pending_lane_count"]
            summary = {"status": "all_versions_frozen_pending_readout" if all_done else "aborted_measurement_incomplete",
                "completed": completed, "errors": [] if all_done else failures, "finished_at": time.time(),
                "resume_ledger": str(job_path.relative_to(root)), "original_summary": str((ledger / "original-summary.json").relative_to(root)),
                "exactly_once": False, "partial_measurements_used_for_selection": False}
            if all_done:
                summary["frozen_versions"] = {key: value for lane in after["lanes"] for key, value in lane["version_hashes"].items()}
            if raw_sha(root / "summary.json") != plan["summary_sha256"]:
                raise ValueError("Current summary changed outside the resume controller")
            atomic_json(root / "summary.json", summary)
            guard.write_exclusive(ledger / "completion.json", {"status": summary["status"], "summary_sha256": raw_sha(root / "summary.json"),
                "old_model_calls_verified_unchanged": len(old_calls), "completed_lanes": len(completed), "exactly_once": False})
            return {"status": summary["status"], "resume_ledger": str(job_path.relative_to(root)), "completed_lanes": len(completed)}
    finally:
        if lock.is_file() and guard.read_json(lock).get("id") == identifier:
            lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path(__file__).resolve().parents[1] / "experiments/continual-v02-main")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Offline and read-only; default")
    modes.add_argument("--execute", action="store_true", help="Replay uncommitted rounds with real API calls")
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--worker-plan", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--staging", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker_plan:
        if args.staging is None:
            parser.error("Internal worker needs staging")
        return worker(args.worker_plan, args.staging)
    try:
        archive = guard.verify_archive(args.experiment)
        if args.execute:
            result = execute_resume(archive, concurrency=args.concurrency)
        else:
            plan = build_plan(archive)
            result = {"status": "checked", "network_requests": 0, "completed_lanes": plan["completed_lane_count"],
                "pending_lanes": plan["pending_lane_count"], "rounds": plan["rounds"], "exactly_once": False,
                "next_rounds": [{"seed": lane["seed"], "arm": lane["arm"], "start_round": lane["start_round"]}
                                for lane in plan["lanes"] if not lane["completed"]]}
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Resume rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
