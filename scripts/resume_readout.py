"""Resume frozen continual independent readout without replacing valid evidence.

Default CLI mode is an offline check. --execute explicitly performs remaining
real requests. No shell or archive-supplied additional Python is executed.
Execution locking is currently supported on Linux/macOS (fcntl); Windows
readout-resume execution is neither implemented nor tested. Offline checks do
not acquire a lock. This does not change the core package's platform support.
"""
from __future__ import annotations

import argparse
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_readout_archive_verifier", Path(__file__).with_name("reproduce_continual.py"))
_verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_verifier)
canonical, digest, read_json = _verifier.canonical, _verifier.digest, _verifier.read_json
ARMS = _verifier.ARMS
PROBE_KEYS = {"scope", "initial_snapshot_hash", "search_opportunities_per_fork", "baseline", "forks",
              "policy_distinct", "valid_search_pair", "future_delta", "raw_future_delta",
              "distinct_selected_mechanisms", "promotion_eligible", "sampling_note", "audit_input_hash", "checkpoint"}
INPUT_KEYS = {"mechanism", "memory", "observations", "history", "experience", "input_hash"}


def safe_path(output, path):
    output, path = Path(output), Path(path)
    path.relative_to(output)
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("Symlinked evidence paths are forbidden")
        if candidate == output:
            return path
    raise ValueError("Evidence path is outside the experiment")


def write_exclusive(path, value):
    """Atomic publication, failing rather than replacing any existing byte."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".readout-write-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def readout_lock(output):
    # flock is released by the OS even after a killed process; the persistent
    # file is not an inode-racy "delete stale lock" mechanism.
    try:
        import fcntl
    except ImportError:
        raise ValueError("Readout-resume execution locking currently requires Linux/macOS fcntl") from None
    path = safe_path(output, output / ".readout-resume.lock")
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another readout resume currently holds the experiment lock") from None
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def maintained_host(archive):
    import ast
    package = ROOT / "src/moltweave"
    for name, expected in archive["manifest"]["sources"].items():
        path = package / name
        if path.is_symlink() or not path.is_file() or digest(path.read_text()) != expected:
            raise ValueError("Maintained host differs from the frozen source contract: " + name)
    # The maintained package initializer may declare only a docstring/version.
    init = ast.parse((package / "__init__.py").read_text())
    for node in init.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "__version__" and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            continue
        raise ValueError("Maintained initializer contains undeclared executable code")
    sys.path.insert(0, str(ROOT / "src"))
    try:
        modules = {name[:-3]: importlib.import_module("moltweave." + name[:-3]) for name in archive["manifest"]["sources"]}
    finally:
        sys.path.pop(0)
    for name, module in modules.items():
        if Path(module.__file__).resolve() != (package / (name + ".py")).resolve():
            raise ValueError("A different installed module shadows the maintained frozen host")
    host = SimpleNamespace(engine=modules["continual"], runtime=modules["continual_runtime"],
        memory=modules["continual_memory"], program=modules["continual_program"],
        policy=modules["continual_policy"], llm=modules["llm"])
    if host.engine.frozen_sources() != archive["manifest"]["sources"]:
        raise ValueError("Imported host source contract mismatch")
    return host


def load_contract(output, expected_manifest_sha256=None):
    path = Path(output)
    if path.is_symlink():
        raise ValueError("Experiment root must not be a symlink")
    archive = _verifier.verify_archive(path, expected_manifest_sha256)
    output = archive["experiment"]
    for name in ("streams", "model-calls", "independent", "policy-audits", "policy-audit-inputs", "readout-resume"):
        base = safe_path(output, output / name)
        if base.exists():
            for child in base.rglob("*"):
                safe_path(output, child)
    _verifier.verify_complete_run(archive, output)
    host = maintained_host(archive)
    manifest = archive["manifest"]
    checkpoints = manifest["protocol"].get("policy_audit_checkpoints")
    if (not isinstance(checkpoints, list) or checkpoints != sorted(set(checkpoints))
            or any(type(g) is not int or not 0 <= g <= manifest["rounds"] for g in checkpoints)):
        raise ValueError("Invalid predeclared policy audit checkpoints")
    states = {}
    for seed in manifest["seeds"]:
        if host.engine.partition_contract(seed, manifest["rounds"]) != manifest["partition_hashes"][str(seed)]:
            raise ValueError("Frozen independent partition contract changed")
        for arm in ARMS:
            for g in range(manifest["rounds"] + 1):
                state = read_json(output / "streams" / str(seed) / arm / "versions" / f"g{g}.json")
                host.program.validate_mechanism(state["mechanism"])
                host.policy.validate_policy(state["policy"])
                host.memory.ContinualMemory(state["memory"])
                states[(seed, arm, g)] = state
    return archive, host, states


class ReplayClient:
    """Return sealed historical outputs only; no requests, retries or scoring choices."""
    def __init__(self, report):
        self.by_id = {row["trace_id"]: row for row in report["traces"]}
        self.used = set()

    def complete(self, messages, *, purpose, metadata, **kwargs):
        key = (metadata["task_id"], purpose)
        if key in self.used or metadata["task_id"] not in self.by_id:
            raise ValueError("Duplicate or unexpected historical task invocation")
        self.used.add(key)
        trace = self.by_id[metadata["task_id"]]["trace"]
        if purpose == "continual_task":
            return deepcopy(trace["output"])
        if purpose == "continual_memory_extraction" and isinstance(trace.get("writer_proposal"), dict):
            return deepcopy(trace["writer_proposal"])
        raise ValueError("Historical task lacks the expected sealed model output")


def validate_report(host, report, tasks, mechanism, snapshot=None, *, use_memory=True, write_memory=True):
    fields = {"initial_memory_hash", "final_memory_hash", "mechanism_hash", "passed", "total", "traces", "final_memory"}
    if (not isinstance(report, dict) or set(report) != fields or type(report.get("passed")) is not int
            or type(report.get("total")) is not int or not isinstance(report.get("traces"), list)
            or report["total"] != len(tasks) or report["mechanism_hash"] != digest(mechanism)):
        raise ValueError("Retained report schema/task count/mechanism hash mismatch")
    expected_ids = [task["id"] for task in tasks]
    if [row.get("trace_id") for row in report["traces"]] != expected_ids or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("Retained report task IDs/order mismatch")
    replay = host.runtime.execute_episode(tasks, mechanism, host.memory.ContinualMemory(deepcopy(snapshot)),
        ReplayClient(report), metadata={}, use_memory=use_memory, write_memory=write_memory)
    if digest(replay) != digest(report):
        raise ValueError("Retained report differs from deterministic replay of its sealed outputs")


def version_specs(host, manifest, seed, state, generation):
    specs = {split: (host.engine.acceptance_tasks(seed, split), state["mechanism"], True, True)
             for split in ("acceptance", "transfer")}
    if generation == manifest["rounds"]:
        specs["no_memory"] = (host.engine.acceptance_tasks(seed), state["mechanism"], False, False)
        wide = host.program.baseline_mechanism()
        wide.update(memory_top_k=6, rag_top_k=6)
        specs["wide_context_baseline"] = (host.engine.acceptance_tasks(seed), wide, True, True)
    return specs


def validate_version(host, specs, value, *, allow_partial=False):
    if not isinstance(value, dict) or not set(value) <= set(specs) or (not allow_partial and set(value) != set(specs)):
        raise ValueError("Unexpected independent version split schema")
    for split, report in value.items():
        tasks, mechanism, use_memory, write_memory = specs[split]
        validate_report(host, report, tasks, mechanism, use_memory=use_memory, write_memory=write_memory)
    return set(value) == set(specs)


def validate_input(host, value, seed, terminal_fixed):
    if not isinstance(value, dict) or set(value) != INPUT_KEYS:
        raise ValueError("Invalid retained policy-audit input schema")
    unsigned = {key: item for key, item in value.items() if key != "input_hash"}
    if (value["input_hash"] != digest(unsigned) or value["mechanism"] != host.program.baseline_mechanism()
            or value["history"] != terminal_fixed["history"]):
        raise ValueError("Policy-audit input binding changed")
    validate_report(host, value["experience"], host.engine.episode(seed, 3, "audit-observations"),
                    value["mechanism"], terminal_fixed["memory"])
    if (value["memory"] != value["experience"]["final_memory"]
            or value["observations"] != host.engine.observations_from(value["experience"])):
        raise ValueError("Policy-audit observations/memory are not the sealed common input")


def validate_partition(host, value, seed, split, mechanism, snapshot):
    if not isinstance(value, dict) or set(value) != {"development", "protection", "passed", "total", "guard_passed"}:
        raise ValueError("Invalid retained search/future partition schema")
    validate_report(host, value["development"], host.engine.episode(seed, 3, split), mechanism, snapshot)
    validate_report(host, value["protection"], host.engine.protection(seed, 3, split + "-guard"), mechanism, snapshot)
    if (value["passed"] != value["development"]["passed"] or value["total"] != value["development"]["total"]
            or value["guard_passed"] != value["protection"]["passed"]):
        raise ValueError("Search/future aggregate differs from retained traces")


def validate_audit(host, value, seed, generation, common, policy):
    if not isinstance(value, dict) or set(value) != PROBE_KEYS:
        raise ValueError("Invalid retained policy audit schema")
    mechanism, snapshot, history = common["mechanism"], common["memory"], common["history"]
    initial = digest({"mechanism": mechanism, "memory": snapshot, "history": history})
    if (value["scope"] != "independent_policy_audit" or value["checkpoint"] != generation
            or value["audit_input_hash"] != common["input_hash"] or value["initial_snapshot_hash"] != initial
            or value["search_opportunities_per_fork"] != 1 or set(value["forks"]) != {"old", "new"}):
        raise ValueError("Policy audit checkpoint/common-input binding changed")
    validate_partition(host, value["baseline"], seed, "audit-search", mechanism, snapshot)
    for label, expected_policy in (("old", host.policy.baseline_policy()), ("new", policy)):
        fork = value["forks"][label]
        keys = {"policy_hash", "initial_mechanism_hash", "initial_memory_hash", "history_hash", "diagnosis", "action", "trial", "selected_mechanism_hash", "future"}
        if (not isinstance(fork, dict) or set(fork) != keys or fork["policy_hash"] != digest(expected_policy)
                or fork["initial_mechanism_hash"] != digest(mechanism) or fork["initial_memory_hash"] != digest(snapshot)
                or fork["history_hash"] != digest(history) or not isinstance(fork["action"], list) or len(fork["action"]) > 1):
            raise ValueError("Policy fork model/state/history binding changed")
        diagnosis = fork["diagnosis"]
        if diagnosis.get("status") == "hypotheses_not_verified":
            class DiagnosisReplay:
                def complete(self, *args, **kwargs):
                    return deepcopy(diagnosis["raw_proposal"])
            checked = host.policy.diagnose(DiagnosisReplay(), expected_policy, common["observations"], history,
                metadata={"phase": "independent_policy_audit", "stream": seed, "version": generation, "fork": label,
                          "parent_options": host.engine.parent_options(mechanism, None)})
            if (digest(checked) != digest(diagnosis)
                    or digest(host.policy.select_actions(expected_policy, checked, history, limit=1)) != digest(fork["action"])):
                raise ValueError("Policy audit diagnosis/source references/selected action changed")
        elif diagnosis.get("status") != "invalid_diagnosis" or fork["action"] or diagnosis.get("effect") is not None:
            raise ValueError("Unknown or contradictory audit diagnosis")
        trial, selected = fork["trial"], mechanism
        if trial.get("status") == "executed":
            candidate = trial["mechanism"]
            host.program.validate_mechanism(candidate)
            if (len(fork["action"]) != 1 or trial["action"] != fork["action"][0]
                    or trial["mechanism_hash"] != digest(candidate)
                    or trial["proposal"]["mechanism"] != candidate
                    or trial["proposal"]["action"] != trial["action"]
                    or trial["proposal"]["parent_hash"] != digest(mechanism)
                    or trial["proposal"]["mechanism_hash"] != digest(candidate)):
                raise ValueError("Executed audit candidate identity changed")
            action = trial["action"]
            if action.get("parent") != "current" or action.get("parent_hash") != digest(mechanism):
                raise ValueError("Independent audit candidate has an undeclared parent")
            allowed = {field for module in action["modules"] for field in host.program.MODULE_FIELDS[module]}
            if not {key for key in candidate if candidate[key] != mechanism[key]} <= allowed:
                raise ValueError("Audit candidate changed an undeclared mechanism field")
            if re.search(r"\bV[0-9A-F]{12}\b|(?:case|src)-[0-9a-f]{12,}", json.dumps(candidate)):
                raise ValueError("Audit candidate contains case-specific factual material")
            validate_partition(host, trial["evaluation"], seed, "audit-search", candidate, snapshot)
            if (trial["evaluation"]["passed"] > value["baseline"]["passed"]
                    and trial["evaluation"]["guard_passed"] >= value["baseline"]["guard_passed"]):
                selected = candidate
        elif trial.get("status") == "invalid_candidate":
            if len(fork["action"]) != 1 or trial.get("effect") is not None:
                raise ValueError("Invalid candidate must remain an unknown-effect attempt")
        elif trial.get("status") == "no_action":
            if fork["action"] or trial.get("effect") is not None:
                raise ValueError("No-action audit must retain the unchanged fallback")
        else:
            raise ValueError("Unknown retained audit trial status")
        if fork["selected_mechanism_hash"] != digest(selected):
            raise ValueError("Audit selected mechanism differs from the declared promotion rule")
        validate_partition(host, fork["future"], seed, "audit-future", selected, snapshot)
    old, new = value["forks"]["old"], value["forks"]["new"]
    valid = old["trial"]["status"] == new["trial"]["status"] == "executed"
    distinct_p = old["policy_hash"] != new["policy_hash"]
    distinct_m = old["selected_mechanism_hash"] != new["selected_mechanism_hash"]
    raw = (new["future"]["passed"] - old["future"]["passed"]) / old["future"]["total"]
    promote = bool(valid and distinct_p and distinct_m and new["future"]["passed"] > old["future"]["passed"]
                   and new["future"]["guard_passed"] >= old["future"]["guard_passed"])
    expected = {"valid_search_pair": valid, "policy_distinct": distinct_p, "distinct_selected_mechanisms": distinct_m,
                "future_delta": raw if valid else None, "raw_future_delta": raw, "promotion_eligible": promote}
    if any(canonical(value[key]) != canonical(item) for key, item in expected.items()):
        raise ValueError("Policy audit effects/validity do not match the executed fork reports")


def version_summary(seed, arm, g, reports):
    return {"stream": seed, "arm": arm, "generation": g,
            "reports": {key: {field: report[field] for field in ("passed", "total", "mechanism_hash")}
                        for key, report in reports.items()}}


def audit_summary(seed, g, report):
    old, new = report["forks"]["old"], report["forks"]["new"]
    return {"stream": seed, "generation": g, **{key: report[key] for key in
            ("future_delta", "raw_future_delta", "valid_search_pair", "policy_distinct", "distinct_selected_mechanisms")},
            "old_policy_hash": old["policy_hash"], "new_policy_hash": new["policy_hash"],
            "old_passed": old["future"]["passed"], "new_passed": new["future"]["passed"], "total": old["future"]["total"]}


def inventory(output, manifest):
    found, by_unit = {}, {}
    for path in sorted((output / "model-calls").rglob("*.json")):
        safe_path(output, path)
        receipt = read_json(path)
        identity = receipt.get("id")
        if not isinstance(identity, str) or not identity or identity in found:
            raise ValueError("Missing or duplicated logical model-call receipt ID")
        if receipt.get("model_requested") != manifest["model"] or receipt.get("endpoint_host") != urlsplit(manifest["provider_base"]).hostname:
            raise ValueError("Historical receipt model/provider differs from the frozen contract")
        relative = str(path.relative_to(output))
        found[identity] = relative
        meta = receipt.get("metadata", {})
        phase, seed = meta.get("phase"), meta.get("stream")
        if phase in {"independent", "independent_memory_ablation", "independent_wide_context"}:
            unit = f"version/{seed}/{meta.get('arm')}/g{meta.get('version')}"
        elif phase == "independent_policy_audit_observations":
            unit = f"input/{seed}"
        elif phase == "independent_policy_audit":
            unit = f"audit/{seed}/g{meta.get('version')}"
        else:
            continue
        by_unit.setdefault(unit, []).append(relative)
    return by_unit


class Ledger:
    def __init__(self, output, archive, concurrency):
        self.output = output
        self.id = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex[:12]
        self.folder = output / "readout-resume" / self.id
        self.folder.mkdir(parents=True, exist_ok=False)
        self.path = self.folder / "ledger.json"
        self.lock = threading.Lock()
        self.value = {"schema": 1, "attempt": self.id, "status": "running", "started_at": time.time(),
            "manifest_sha256": archive["manifest_sha256"], "source_hashes": archive["manifest"]["sources"],
            "model": archive["manifest"]["model"], "provider_base": archive["manifest"]["provider_base"],
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "concurrency": concurrency,
            "retry_rule": "reuse every complete validated original byte; rerun a missing/incomplete whole version or whole audit independent of score",
            "selection_allowed": False, "events": []}
        self.flush()

    def flush(self):
        fd, temp = tempfile.mkstemp(dir=self.folder, prefix=".ledger-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(self.value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        finally:
            Path(temp).unlink(missing_ok=True)

    def event(self, unit, action, **fields):
        with self.lock:
            self.value["events"].append({"unit": unit, "action": action, "at": time.time(), **fields})
            self.flush()

    def finish(self, status, **fields):
        with self.lock:
            self.value.update(status=status, finished_at=time.time(), **fields)
            self.flush()


class UnitClient:
    def __init__(self, client, unit, attempt):
        self.client, self.unit, self.attempt = client, unit, attempt

    def complete(self, *args, **kwargs):
        kwargs["metadata"] = {**dict(kwargs.get("metadata") or {}), "readout_resume_unit": self.unit,
                              "readout_resume_attempt": self.attempt}
        return self.client.complete(*args, **kwargs)


def new_client(host, manifest, path, concurrency):
    physical = host.llm.ModelClient(path)
    if (physical.model != manifest["model"] or physical.base_url != manifest["provider_base"]
            or physical.allow_env_proxy or physical.allow_http_loopback):
        raise ValueError("Resume requires the exact frozen model/provider and protected transport")
    return host.engine.LimitedClient(physical, concurrency)


def plan_readout(output, manifest, host, states):
    versions, partial, inputs, audits = {}, {}, {}, {}
    for seed in manifest["seeds"]:
        for arm in ARMS:
            for g in range(manifest["rounds"] + 1):
                key = (seed, arm, g)
                path = safe_path(output, output / "independent" / str(seed) / arm / f"g{g}.json")
                if path.exists():
                    value = read_json(path)
                    specs = version_specs(host, manifest, seed, states[key], g)
                    if validate_version(host, specs, value, allow_partial=True):
                        versions[key] = value
                    else:
                        partial[f"version/{seed}/{arm}/g{g}"] = path
        input_path = safe_path(output, output / "policy-audit-inputs" / f"{seed}.json")
        if input_path.exists():
            value = read_json(input_path)
            if set(value) < INPUT_KEYS:
                if ("mechanism" in value and value["mechanism"] != host.program.baseline_mechanism()
                        or "history" in value and value["history"] != states[(seed, "fixed_p", manifest["rounds"])]["history"]):
                    raise ValueError("Partial audit input contradicts its fixed initial snapshot")
                partial[f"input/{seed}"] = input_path
            else:
                inputs[seed] = value
                validate_input(host, value, seed, states[(seed, "fixed_p", manifest["rounds"])])
        for g in manifest["protocol"]["policy_audit_checkpoints"]:
            path = safe_path(output, output / "policy-audits" / str(seed) / f"g{g}.json")
            if path.exists():
                if seed not in inputs:
                    raise ValueError("Retained policy audit has no preserved common input; never regenerate its input")
                value = read_json(path)
                if set(value) < PROBE_KEYS:
                    bindings = {"checkpoint": g, "scope": "independent_policy_audit", "audit_input_hash": inputs[seed]["input_hash"]}
                    if any(key in value and value[key] != expected for key, expected in bindings.items()):
                        raise ValueError("Partial audit contradicts its retained input/checkpoint")
                    partial[f"audit/{seed}/g{g}"] = path
                else:
                    audits[(seed, g)] = value
                    validate_audit(host, value, seed, g, inputs[seed], states[(seed, "joint", g)]["policy"])
    return versions, partial, inputs, audits


def validate_final(value, manifest, versions, audits):
    expected_versions = len(manifest["seeds"]) * len(ARMS) * (manifest["rounds"] + 1)
    expected_audits = len(manifest["seeds"]) * len(manifest["protocol"]["policy_audit_checkpoints"])
    if (set(value) != {"status", "readout_at", "versions", "policy_audits", "selection_allowed", "primary_endpoint_generation"}
            or value["status"] != "completed" or value["selection_allowed"] is not False
            or type(value["readout_at"]) not in (int, float) or not math.isfinite(value["readout_at"])
            or value["primary_endpoint_generation"] != manifest["rounds"]
            or len(versions) != expected_versions or len(audits) != expected_audits):
        raise ValueError("Existing immutable independent summary is incomplete or incompatible")
    expected_v = {(s, a, g): version_summary(s, a, g, report) for (s, a, g), report in versions.items()}
    actual_v = {(row["stream"], row["arm"], row["generation"]): row for row in value["versions"]}
    expected_p = {(s, g): audit_summary(s, g, report) for (s, g), report in audits.items()}
    actual_p = {(row["stream"], row["generation"]): row for row in value["policy_audits"]}
    if (len(actual_v) != len(value["versions"]) or len(actual_p) != len(value["policy_audits"])
            or set(actual_v) != set(expected_v) or set(actual_p) != set(expected_p)
            or any(canonical(actual_v[key]) != canonical(expected_v[key]) for key in expected_v)
            or any(canonical(actual_p[key]) != canonical(expected_p[key]) for key in expected_p)):
        raise ValueError("Immutable independent summary differs from the preserved raw artifacts")


def resume_readout(output, *, concurrency=32, check_only=False, expected_manifest_sha256=None):
    if type(concurrency) is not int or not 1 <= concurrency <= 128:
        raise ValueError("Concurrency must be 1..128")
    archive, host, states = load_contract(output, expected_manifest_sha256)
    output, manifest = archive["experiment"], archive["manifest"]
    versions, partial, inputs, audits = plan_readout(output, manifest, host, states)
    prior_calls = inventory(output, manifest)
    final_path = safe_path(output, output / "independent.json")
    if final_path.exists():
        result = read_json(final_path)
        validate_final(result, manifest, versions, audits)
        return result
    expected_v = len(manifest["seeds"]) * len(ARMS) * (manifest["rounds"] + 1)
    expected_p = len(manifest["seeds"]) * len(manifest["protocol"]["policy_audit_checkpoints"])
    if check_only:
        return {"status": "checked", "network_requests": 0, "complete_versions_reusable": len(versions),
                "pending_versions": expected_v - len(versions),
                "partial_versions_preserved_before_restart": sum(key.startswith("version/") for key in partial),
                "partial_units_preserved_before_restart": len(partial),
                "complete_inputs_reusable": len(inputs), "complete_audits_reusable": len(audits),
                "pending_audits": expected_p - len(audits), "manifest_sha256": archive["manifest_sha256"]}
    contract_pin = archive["manifest_sha256"]
    with readout_lock(output):
        # Recheck after obtaining the OS lock, before creating a client or request.
        archive, host, states = load_contract(output, contract_pin)
        versions, partial, inputs, audits = plan_readout(output, manifest, host, states)
        if final_path.exists():
            result = read_json(final_path)
            validate_final(result, manifest, versions, audits)
            return result
        ledger = Ledger(output, archive, concurrency)
        calls_path = safe_path(output, output / "model-calls" / ("readout-resume-" + ledger.id))
        try:
            client, client_lock = None, threading.Lock()
            def get_client():
                nonlocal client
                with client_lock:
                    if client is None:
                        client = new_client(host, manifest, calls_path, concurrency)
                return client
            def publish_unit(unit, path, calculate, validate, *, partial_path=None):
                prior = prior_calls.get(unit, [])
                ledger.event(unit, "started", prior_call_receipts=prior, receipts_directory=str(calls_path.relative_to(output)),
                             restart_rule="entire unit; no score-conditioned retries")
                try:
                    if partial_path is not None:
                        saved = ledger.folder / "preserved-partial" / path.relative_to(output)
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        os.rename(partial_path, saved)
                        ledger.event(unit, "partial_bytes_preserved", path=str(saved.relative_to(output)), sha256=hashlib.sha256(saved.read_bytes()).hexdigest())
                    result = calculate(UnitClient(get_client(), unit, ledger.id))
                    validate(result)
                    write_exclusive(path, result)
                    ledger.event(unit, "completed", path=str(path.relative_to(output)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    return result
                except Exception as exc:
                    ledger.event(unit, "measurement_or_integrity_failure", error_type=type(exc).__name__)
                    raise
            def parallel(jobs):
                errors = []
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures = {pool.submit(function): key for key, function in jobs}
                    for future in as_completed(futures):
                        try:
                            yield futures[future], future.result()
                        except CancelledError:
                            ledger.event(str(futures[future]), "cancelled_before_execution")
                        except Exception as exc:
                            errors.append(exc)
                            for pending in futures:
                                if not pending.done():
                                    pending.cancel()
                if errors:
                    raise RuntimeError("Readout units incomplete; retained artifacts and calls are reusable") from errors[0]
            jobs = []
            for key, state in states.items():
                seed, arm, g = key
                path = output / "independent" / str(seed) / arm / f"g{g}.json"
                unit = f"version/{seed}/{arm}/g{g}"
                if key in versions:
                    ledger.event(unit, "reused_original_bytes", path=str(path.relative_to(output)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    continue
                specs = version_specs(host, manifest, seed, state, g)
                def job(key=key, path=path, unit=unit, specs=specs):
                    seed, arm, g = key
                    def calculate(c):
                        reports = {}
                        for split, (tasks, mechanism, use_memory, write_memory) in specs.items():
                            phase = "independent_memory_ablation" if split == "no_memory" else "independent_wide_context" if split == "wide_context_baseline" else "independent"
                            reports[split] = host.runtime.execute_episode(tasks, mechanism, host.memory.ContinualMemory(), c,
                                metadata={"phase": phase, "stream": seed, "arm": arm, "version": g, **({"split": split} if phase == "independent" else {})},
                                use_memory=use_memory, write_memory=write_memory)
                        return reports
                    return publish_unit(unit, path, calculate, lambda r: validate_version(host, specs, r), partial_path=partial.get(unit))
                jobs.append((key, job))
            for key, report in parallel(jobs):
                versions[key] = report
            jobs = []
            for seed in manifest["seeds"]:
                path = output / "policy-audit-inputs" / f"{seed}.json"
                if seed in inputs:
                    ledger.event(f"input/{seed}", "reused_original_bytes", path=str(path.relative_to(output)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    continue
                terminal = states[(seed, "fixed_p", manifest["rounds"])]
                def job(seed=seed, path=path, terminal=terminal):
                    def calculate(c):
                        mechanism = host.program.baseline_mechanism()
                        memory = host.memory.ContinualMemory(deepcopy(terminal["memory"]))
                        report = host.runtime.execute_episode(host.engine.episode(seed, 3, "audit-observations"), mechanism, memory, c,
                            metadata={"phase": "independent_policy_audit_observations", "stream": seed})
                        value = {"mechanism": mechanism, "memory": memory.snapshot(), "observations": host.engine.observations_from(report),
                                 "history": terminal["history"], "experience": report}
                        value["input_hash"] = digest(value)
                        return value
                    return publish_unit(f"input/{seed}", path, calculate, lambda r: validate_input(host, r, seed, terminal), partial_path=partial.get(f"input/{seed}"))
                jobs.append((seed, job))
            for seed, common in parallel(jobs):
                inputs[seed] = common
            jobs = []
            for seed in manifest["seeds"]:
                for g in manifest["protocol"]["policy_audit_checkpoints"]:
                    path = output / "policy-audits" / str(seed) / f"g{g}.json"
                    if (seed, g) in audits:
                        ledger.event(f"audit/{seed}/g{g}", "reused_original_bytes", path=str(path.relative_to(output)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                        continue
                    common, policy = inputs[seed], states[(seed, "joint", g)]["policy"]
                    def job(seed=seed, g=g, path=path, common=common, policy=policy):
                        def calculate(c):
                            result = host.engine.paired_probe(c, common["mechanism"], host.policy.baseline_policy(), policy,
                                common["observations"], common["history"], common["memory"], seed=seed, r=3, split="audit",
                                metadata={"phase": "independent_policy_audit", "stream": seed, "version": g})
                            result.update(audit_input_hash=common["input_hash"], checkpoint=g)
                            return result
                        return publish_unit(f"audit/{seed}/g{g}", path, calculate, lambda r: validate_audit(host, r, seed, g, common, policy), partial_path=partial.get(f"audit/{seed}/g{g}"))
                    jobs.append(((seed, g), job))
            for key, report in parallel(jobs):
                audits[key] = report
            result = {"status": "completed", "readout_at": time.time(),
                "versions": [version_summary(seed, arm, g, versions[(seed, arm, g)]) for seed in manifest["seeds"] for arm in ARMS for g in range(manifest["rounds"] + 1)],
                "policy_audits": [audit_summary(seed, g, audits[(seed, g)]) for seed in manifest["seeds"] for g in manifest["protocol"]["policy_audit_checkpoints"]],
                "selection_allowed": False, "primary_endpoint_generation": manifest["rounds"]}
            validate_final(result, manifest, versions, audits)
            write_exclusive(final_path, result)
            ledger.finish("completed", independent_sha256=hashlib.sha256(final_path.read_bytes()).hexdigest(),
                          new_call_receipts=[str(p.relative_to(output)) for p in sorted(calls_path.rglob("*.json"))])
            return result
        except Exception as exc:
            ledger.finish("measurement_incomplete", error_type=type(exc).__name__,
                          retained_new_call_receipts=[str(p.relative_to(output)) for p in sorted(calls_path.rglob("*.json"))])
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--manifest-sha256")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Perform remaining real model requests")
    mode.add_argument("--check", action="store_true", help="Offline verification only (default)")
    args = parser.parse_args(argv)
    try:
        result = resume_readout(args.experiment, concurrency=args.concurrency, check_only=not args.execute,
                                expected_manifest_sha256=args.manifest_sha256)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        # Model-client errors may include opaque local receipt IDs, not secrets.
        parser.exit(2, f"Readout not completed ({type(exc).__name__}); preserve evidence and inspect the resume ledger.\n")
    print(json.dumps({"status": result["status"], "selection_allowed": False,
                      "mode": "execute" if args.execute else "offline_check"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
