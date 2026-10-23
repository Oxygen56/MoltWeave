"""Version 0.2: continuous experience, paired future-search probes, frozen audits.

All policy probes and candidate executions use real model calls. No sampled score
is fabricated, and unavailable measurements never become zero-valued outcomes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import json
from pathlib import Path
import threading
import time

from .common import digest, read_json, write_json
from .continual_environment import episode, protection
from .continual_runtime import execute_episode


ARMS = ("fixed_mechanism", "fixed_p", "joint")


def acceptance_tasks(seed, split="acceptance"):
    rounds = list(range(5)) if split == "acceptance" else [7]
    return [t for r in rounds for t in episode(seed, r, split, retain_previous=r > rounds[0])]


class LimitedClient:
    def __init__(self, client, concurrency: int):
        self.client, self.semaphore = client, threading.BoundedSemaphore(concurrency)
        self.model = client.model

    def complete(self, *args, **kwargs):
        with self.semaphore:
            return self.client.complete(*args, **kwargs)


def evaluate_partition(seed, r, split, mechanism, snapshot, client, metadata, *, include_guard=True):
    from .continual_memory import ContinualMemory
    memory = ContinualMemory(copy.deepcopy(snapshot))
    report = execute_episode(episode(seed, r, split), mechanism, memory, client, metadata=metadata)
    guard = execute_episode(protection(seed, r, split + "-guard"), mechanism,
                            ContinualMemory(copy.deepcopy(snapshot)), client,
                            metadata={**metadata, "part": "protection"}) if include_guard else None
    return {"development": report, "protection": guard,
            "passed": report["passed"], "total": report["total"],
            "guard_passed": guard["passed"] if guard else 0}


def observations_from(report):
    return [{"trace_id": t["trace_id"], "trace": t["trace"], "feedback": {**t["feedback"], "sealed": True}}
            for t in report["traces"]]


def parent_options(mechanism, rejected):
    result = {"current": {"hash": digest(mechanism), "mechanism": mechanism}}
    if rejected is not None:
        result["best_rejected"] = {"hash": digest(rejected), "mechanism": rejected}
    return result


def candidate_trial(client, mechanism, policy, action, observations, history, snapshot, *, seed, r, split, metadata):
    from .continual_policy import propose_mechanism
    try:
        parent = action.get("parent_mechanism", mechanism)
        proposal = propose_mechanism(client, parent, policy, action, observations, history, metadata=metadata)
        candidate = proposal["mechanism"]
        # Fixed export restriction: no factual answers or case/source IDs in
        # mechanism instructions. These are programs, not per-case answer caches.
        import re
        if re.search(r"\bV[0-9A-F]{12}\b|(?:case|src)-[0-9a-f]{12,}", json.dumps(candidate)):
            raise ValueError("Mechanism contains case-specific factual material")
        result = evaluate_partition(seed, r, split, candidate, snapshot, client, metadata)
        return {"status": "executed", "action": action, "proposal": proposal, "mechanism": candidate,
                "mechanism_hash": digest(candidate), "evaluation": result}
    except (ValueError, TypeError, KeyError) as exc:
        return {"status": "invalid_candidate", "action": action, "error": str(exc), "effect": None}


def search_once(client, mechanism, policy, observations, history, snapshot, *, seed, r, split,
                metadata, rejected=None, limit=2):
    from .continual_policy import diagnose, select_actions
    base = evaluate_partition(seed, r, split, mechanism, snapshot, client,
                              {**metadata, "purpose_detail": "baseline"})
    try:
        diagnosis = diagnose(client, policy, observations, history,
                             metadata={**metadata, "parent_options": parent_options(mechanism, rejected)})
        actions = select_actions(policy, diagnosis, history, limit=limit)
    except (ValueError, TypeError, KeyError) as exc:
        diagnosis = {"status": "invalid_diagnosis", "error": str(exc), "effect": None}
        actions = []
    trials = []
    with ThreadPoolExecutor(max_workers=max(1, limit)) as pool:
        futures = [(i, pool.submit(candidate_trial, client, mechanism, policy, a, observations, history, snapshot,
                                   seed=seed, r=r, split=split,
                                   metadata={**metadata, "candidate": i})) for i, a in enumerate(actions)]
        for i, future in futures:
            trial = future.result()
            trial["opportunity"] = i
            trials.append(trial)
    selected, best_passed = mechanism, base["passed"]
    selected_trial = None
    for i, trial in enumerate(trials):
        if trial["status"] != "executed":
            continue
        e = trial["evaluation"]
        trial["gain"] = (e["passed"] - base["passed"]) / base["total"]
        if e["passed"] > best_passed and e["guard_passed"] >= base["guard_passed"]:
            selected, best_passed, selected_trial = trial["mechanism"], e["passed"], i
    return {"initial_mechanism_hash": digest(mechanism), "initial_memory_hash": digest(snapshot),
            "policy_hash": digest(policy), "baseline": base, "diagnosis": diagnosis, "actions": actions,
            "trials": trials, "selected_mechanism": selected, "selected_mechanism_hash": digest(selected),
            "selected_trial": selected_trial, "mechanism_adopted": digest(selected) != digest(mechanism)}


def paired_probe(client, mechanism, old_policy, new_policy, observations, history, snapshot,
                 *, seed, r, split, metadata, rejected=None):
    """Both forks start identically. Probe states/descendants never merge back.

    Each policy gets one actual search opportunity and then a fresh future
    readout. Both use the fixed engine, model and data; prompts/operators are
    legitimate treatment variables. Meta-dev is optimization data, not final.
    """
    from .continual_policy import diagnose, select_actions
    baseline = evaluate_partition(seed, r, split + "-search", mechanism, snapshot, client,
                                  {**metadata, "fork": "shared-baseline"})
    def one(label, policy):
        meta = {**metadata, "fork": label, "parent_options": parent_options(mechanism, rejected)}
        try:
            diagnosis = diagnose(client, policy, observations, history, metadata=meta)
            actions = select_actions(policy, diagnosis, history, limit=1)
        except (ValueError, TypeError, KeyError) as exc:
            diagnosis = {"status": "invalid_diagnosis", "error": str(exc), "effect": None}
            actions = []
        trial = (candidate_trial(client, mechanism, policy, actions[0], observations, history, snapshot,
                                 seed=seed, r=r, split=split + "-search", metadata=meta)
                 if actions else {"status": "no_action", "effect": None})
        selected = mechanism
        if trial["status"] == "executed":
            e = trial["evaluation"]
            if e["passed"] > baseline["passed"] and e["guard_passed"] >= baseline["guard_passed"]:
                selected = trial["mechanism"]
        future = evaluate_partition(seed, r, split + "-future", selected, snapshot, client,
                                    {**meta, "purpose_detail": "future-readout"})
        return {"policy_hash": digest(policy), "initial_mechanism_hash": digest(mechanism),
                "initial_memory_hash": digest(snapshot), "history_hash": digest(history),
                "diagnosis": diagnosis, "action": actions, "trial": trial,
                "selected_mechanism_hash": digest(selected), "future": future}
    # Actual order varies across predefined streams/rounds; neither fork sees
    # the other fork's history or measurements.
    ordered = [("old", old_policy), ("new", new_policy)]
    if (seed + r) % 2:
        ordered.reverse()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(one, name, p) for name, p in ordered}
        forks = {name: f.result() for name, f in futures.items()}
    old, new = forks["old"], forks["new"]
    distinct_m = old["selected_mechanism_hash"] != new["selected_mechanism_hash"]
    valid_pair = old["trial"]["status"] == "executed" and new["trial"]["status"] == "executed"
    promote = (valid_pair and digest(old_policy) != digest(new_policy) and distinct_m
               and new["future"]["passed"] > old["future"]["passed"]
               and new["future"]["guard_passed"] >= old["future"]["guard_passed"])
    return {"scope": "meta-development" if metadata.get("phase") != "independent_policy_audit" else "independent_policy_audit",
            "initial_snapshot_hash": digest({"mechanism": mechanism, "memory": snapshot, "history": history}),
            "search_opportunities_per_fork": 1, "baseline": baseline, "forks": forks,
            "valid_search_pair": valid_pair,
            "future_delta": (new["future"]["passed"] - old["future"]["passed"]) / old["future"]["total"] if valid_pair else None,
            "raw_future_delta": (new["future"]["passed"] - old["future"]["passed"]) / old["future"]["total"],
            "distinct_selected_mechanisms": distinct_m, "promotion_eligible": bool(promote),
            "sampling_note": "Single fork readouts are noisy; independent stream-level audits are separate."}


def summarize_trial(trial, r):
    action = trial.get("action", {})
    return {"round": r, "modules": action.get("modules", []), "operator": action.get("operator"),
            "parent": action.get("parent"), "status": trial["status"], "gain": trial.get("gain"),
            "mechanism_hash": trial.get("mechanism_hash")}


def run_lane(output, client, seed, arm, rounds):
    from .continual_memory import ContinualMemory
    from .continual_program import baseline_mechanism
    from .continual_policy import baseline_policy, propose_policy
    folder = output / "streams" / str(seed) / arm
    mechanism, policy, memory, history = baseline_mechanism(), baseline_policy(), ContinualMemory(), []
    rejected = None
    initial = {"mechanism": mechanism, "policy": policy, "memory": memory.snapshot(), "history": [], "round": 0}
    write_json(folder / "versions/g0.json", initial)
    for r in range(rounds):
        start = time.time()
        dest = folder / "rounds" / f"r{r:02d}"
        meta = {"stream": seed, "arm": arm, "round": r, "phase": "online"}
        before_m, before_p = copy.deepcopy(mechanism), copy.deepcopy(policy)
        experience = execute_episode(episode(seed, r, "experience", retain_previous=True), mechanism, memory,
                                     client, metadata=meta)
        write_json(dest / "experience.json", experience)
        observations = observations_from(experience)
        search, probe, policy_proposal = None, None, None
        if arm != "fixed_mechanism":
            search = search_once(client, mechanism, policy, observations, history, memory.snapshot(),
                                 seed=seed, r=r, split="development", metadata={**meta, "phase": "mechanism-search"}, rejected=rejected)
            write_json(dest / "mechanism-search.json", search)
            mechanism = search["selected_mechanism"]
            for t in search["trials"]:
                history.append(summarize_trial(t, r))
            rejected_trials = [t for t in search["trials"] if t["status"] == "executed" and digest(t["mechanism"]) != digest(mechanism)]
            if rejected_trials:
                rejected = max(rejected_trials, key=lambda t: (t["evaluation"]["guard_passed"] >= search["baseline"]["guard_passed"],
                                                              t["evaluation"]["passed"], t["evaluation"]["guard_passed"]))["mechanism"]
            try:
                policy_proposal = propose_policy(client, policy, history, metadata={**meta, "phase": "policy-proposal"})
                new_policy = policy_proposal["policy"]
                probe = paired_probe(client, mechanism, policy, new_policy, observations, history, memory.snapshot(),
                                     seed=seed, r=r, split="meta-development", metadata={**meta, "phase": "policy-meta-probe"}, rejected=rejected)
                probe["adopted"] = arm == "joint" and probe["promotion_eligible"]
                probe["arm_rule"] = "shadow only: P frozen" if arm == "fixed_p" else "strict future gain; protection nonregression; distinct selected M"
                if probe["adopted"]:
                    policy = new_policy
                history.append({"round": r, "status": "policy_probe", "future_delta": probe["future_delta"],
                                "policy_adopted": probe["adopted"], "new_policy_hash": digest(new_policy),
                                "old_policy_hash": digest(before_p)})
            except (ValueError, TypeError, KeyError) as exc:
                policy_proposal = {"status": "invalid_policy", "error": str(exc), "effect": None}
            write_json(dest / "policy-proposal.json", policy_proposal)
            if probe is not None:
                write_json(dest / "policy-probe.json", probe)
        transition = {"stream": seed, "arm": arm, "round": r, "parent_m": digest(before_m), "loaded_m_next": digest(mechanism),
                      "parent_p": digest(before_p), "loaded_p_next": digest(policy),
                      "mechanism_changed": digest(before_m) != digest(mechanism), "policy_changed": digest(before_p) != digest(policy),
                      "changed_m_fields": [k for k in mechanism if mechanism[k] != before_m[k]],
                      "changed_p_fields": [k for k in policy if policy[k] != before_p[k]],
                      "online_passed": experience["passed"], "online_total": experience["total"],
                      "elapsed_seconds": round(time.time() - start, 3), "status": "completed"}
        write_json(dest / "transition.json", transition)
        write_json(folder / "versions" / f"g{r+1}.json", {"mechanism": mechanism, "policy": policy,
                   "memory": memory.snapshot(), "history": history, "round": r + 1})
        write_json(folder / "progress.json", transition)
        print(json.dumps({k: transition[k] for k in ("stream", "arm", "round", "mechanism_changed", "policy_changed", "online_passed", "online_total")}), flush=True)
    return {"seed": seed, "arm": arm, "rounds": rounds, "status": "versions_frozen"}


def frozen_sources():
    names = ["continual.py", "continual_environment.py", "continual_runtime.py", "continual_memory.py",
             "continual_program.py", "continual_policy.py", "program.py", "common.py", "llm.py"]
    return {n: digest((Path(__file__).parent / n).read_text()) for n in names}


def partition_contract(seed, rounds):
    """Hash exactly the task sequences actually consumed by the fixed host."""
    result = {}
    for split in ["experience", "development", "meta-development-search", "meta-development-future"]:
        for r in range(rounds):
            result[f"{split}/r{r}"] = digest(episode(seed, r, split, retain_previous=split == "experience"))
            if split != "experience":
                result[f"{split}/r{r}/guard"] = digest(protection(seed, r, split + "-guard"))
    for split in ["audit-search", "audit-future"]:
        result[split] = digest(episode(seed, 3, split))
        result[split + "/guard"] = digest(protection(seed, 3, split + "-guard"))
    result["audit-observations"] = digest(episode(seed, 3, "audit-observations"))
    for split in ["acceptance", "transfer"]:
        result[split] = digest(acceptance_tasks(seed, split))
    return result


def run_experiment(output: Path, *, rounds=20, streams=10, first_seed=101, concurrency=32):
    from .llm import ModelClient
    output = Path(output)
    if output.exists():
        raise ValueError("Use a fresh output directory; retained evidence must not be overwritten")
    output.mkdir(parents=True)
    client = LimitedClient(ModelClient(output / "model-calls"), concurrency)
    seeds = list(range(first_seed, first_seed + streams))
    manifest = {"schema": 2, "started_at": time.time(), "rounds": rounds, "seeds": seeds, "arms": ARMS,
                "model": client.model, "provider_base": client.client.base_url,
                "sources": frozen_sources(), "source_scope": "authored public synthetic event streams; shared generation grammar",
                "protocol": {"main_search_opportunities": 2, "paired_policy_search_opportunities": 1,
                    "fixed_p_shadow": "same policy-proposal and paired-probe engine, never adopts P",
                    "primary_endpoint": f"g{rounds} joint minus fixed_p on independent primary episodes, paired by stream",
                    "policy_primary_endpoint": f"g{rounds} P versus P0 in fresh independent future-search audits",
                    "policy_audit_checkpoints": sorted(set([0, rounds // 4, rounds // 2, 3 * rounds // 4, rounds])),
                    "policy_promotion": "strict future meta-dev gain plus protection nonregression and distinct M; no merge of fork M/memory",
                    "acceptance": "all versions frozen before readout; same empty memory and new event sequence for every M version; primary rounds 0..4 revisits entities/revisions and tests 3-round delayed recall; transfer round 7",
                    "memory_ablation": "terminal M on same independent sequence with memory reads/writes disabled",
                    "unavailable_measurements": "abort lane/run, retain receipts; never converted to task failure",
                    "sampling": "temperature 0 is not deterministic; stream is the unit of comparison; all failures retained",
                    "independence_limit": "factual/event namespace holdout, not held-out task grammar or external business system"},
                "partition_hashes": {str(seed): partition_contract(seed, rounds) for seed in seeds}}
    write_json(output / "manifest.json", manifest)
    for name in manifest["sources"]:
        path = output / "frozen-source" / "moltweave" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((Path(__file__).parent / name).read_text())
    (output / "frozen-source/moltweave/__init__.py").write_text('"""Frozen v0.2 experiment host."""\n')
    completed, errors = [], []
    with ThreadPoolExecutor(max_workers=len(seeds) * len(ARMS)) as pool:
        pending = {pool.submit(run_lane, output, client, seed, arm, rounds): (seed, arm) for seed in seeds for arm in ARMS}
        for future in as_completed(pending):
            seed, arm = pending[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                error = {"seed": seed, "arm": arm, "error_type": type(exc).__name__, "error": str(exc)}
                errors.append(error)
                write_json(output / "streams" / str(seed) / arm / "ABORTED.json", error)
                print(json.dumps({"aborted": error}), flush=True)
    status = "aborted_measurement_incomplete" if errors else "all_versions_frozen_pending_readout"
    summary = {"status": status, "completed": completed, "errors": errors, "finished_at": time.time()}
    if not errors:
        summary["frozen_versions"] = {f"{seed}/{arm}/g{g}": digest(read_json(output / "streams" / str(seed) / arm / "versions" / f"g{g}.json"))
                                      for seed in seeds for arm in ARMS for g in range(rounds + 1)}
    write_json(output / "summary.json", summary)
    return summary


def independent_readout(output: Path, *, concurrency=32):
    from .llm import ModelClient
    from .continual_memory import ContinualMemory
    from .continual_policy import baseline_policy
    from .continual_program import baseline_mechanism
    output = Path(output)
    manifest, summary = read_json(output / "manifest.json"), read_json(output / "summary.json")
    if summary["status"] != "all_versions_frozen_pending_readout":
        raise ValueError("Every planned lane must finish before independent readout")
    if manifest["sources"] != frozen_sources():
        raise ValueError("Frozen source contract changed; do not read out with a different host")
    if (output / "independent.json").exists():
        raise ValueError("Independent readout is immutable")
    client = LimitedClient(ModelClient(output / "model-calls"), concurrency)
    if client.model != manifest["model"] or client.client.base_url != manifest["provider_base"]:
        raise ValueError("Independent readout must use the frozen requested model and endpoint")
    for seed in manifest["seeds"]:
        if partition_contract(seed, manifest["rounds"]) != manifest["partition_hashes"][str(seed)]:
            raise ValueError("Frozen task sequence contract changed")
        for arm in ARMS:
            for g in range(manifest["rounds"] + 1):
                path = output / "streams" / str(seed) / arm / "versions" / f"g{g}.json"
                state = read_json(path)
                if digest(state) != summary["frozen_versions"][f"{seed}/{arm}/g{g}"]:
                    raise ValueError("Frozen version state changed")
                if g:
                    previous = read_json(path.with_name(f"g{g-1}.json"))
                    transition = read_json(path.parent.parent / "rounds" / f"r{g-1:02d}" / "transition.json")
                    if (transition["parent_m"] != digest(previous["mechanism"]) or transition["parent_p"] != digest(previous["policy"])
                            or transition["loaded_m_next"] != digest(state["mechanism"]) or transition["loaded_p_next"] != digest(state["policy"])):
                        raise ValueError("Frozen parent/descendant chain changed")
    def version(seed, arm, g):
        state = read_json(output / "streams" / str(seed) / arm / "versions" / f"g{g}.json")
        reports = {}
        for split in ["acceptance", "transfer"]:
            memory = ContinualMemory()
            reports[split] = execute_episode(acceptance_tasks(seed, split),
                state["mechanism"], memory, client, metadata={"phase": "independent", "stream": seed, "arm": arm, "version": g, "split": split})
        if g == manifest["rounds"]:
            reports["no_memory"] = execute_episode(acceptance_tasks(seed),
                state["mechanism"], ContinualMemory(), client,
                metadata={"phase": "independent_memory_ablation", "stream": seed, "arm": arm, "version": g},
                use_memory=False, write_memory=False)
            wide = baseline_mechanism()
            wide.update(memory_top_k=6, rag_top_k=6)
            reports["wide_context_baseline"] = execute_episode(acceptance_tasks(seed), wide, ContinualMemory(), client,
                metadata={"phase": "independent_wide_context", "stream": seed, "arm": arm, "version": g})
        write_json(output / "independent" / str(seed) / arm / f"g{g}.json", reports)
        return {"stream": seed, "arm": arm, "generation": g,
                "reports": {k: {"passed": v["passed"], "total": v["total"], "mechanism_hash": v["mechanism_hash"]} for k, v in reports.items()}}
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        pending = [pool.submit(version, seed, arm, g) for seed in manifest["seeds"] for arm in ARMS for g in range(manifest["rounds"] + 1)]
        for f in as_completed(pending):
            results.append(f.result())
    # Held-out P audits are never used for promotion or new optimization. Their
    # state is common across P versions: baseline M, a fixed-P terminal factual
    # memory/history snapshot, and new sealed audit observations.
    def policy_audit(seed, g):
        common = read_json(output / "streams" / str(seed) / "fixed_p" / "versions" / f"g{manifest['rounds']}.json")
        state = read_json(output / "streams" / str(seed) / "joint" / "versions" / f"g{g}.json")
        m = baseline_mechanism()
        audit_experience = execute_episode(episode(seed, 3, "audit-observations"), m, ContinualMemory(common["memory"]), client,
                                           metadata={"phase": "independent_policy_audit_observations", "stream": seed, "version": g})
        result = paired_probe(client, m, baseline_policy(), state["policy"], observations_from(audit_experience), common["history"], common["memory"],
                              seed=seed, r=3, split="audit", metadata={"phase": "independent_policy_audit", "stream": seed, "version": g})
        result["checkpoint"] = g
        write_json(output / "policy-audits" / str(seed) / f"g{g}.json", result)
        return {"stream": seed, "generation": g, "future_delta": result["future_delta"],
                "raw_future_delta": result["raw_future_delta"], "valid_search_pair": result["valid_search_pair"],
                "distinct_selected_mechanisms": result["distinct_selected_mechanisms"],
                "old_passed": result["forks"]["old"]["future"]["passed"], "new_passed": result["forks"]["new"]["future"]["passed"],
                "total": result["forks"]["old"]["future"]["total"]}
    audits = []
    with ThreadPoolExecutor(max_workers=min(20, concurrency)) as pool:
        pending = [pool.submit(policy_audit, seed, g) for seed in manifest["seeds"] for g in manifest["protocol"]["policy_audit_checkpoints"]]
        for f in as_completed(pending):
            audits.append(f.result())
    result = {"status": "completed", "readout_at": time.time(), "versions": results, "policy_audits": audits,
              "selection_allowed": False, "primary_endpoint_generation": manifest["rounds"]}
    write_json(output / "independent.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "evaluate"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--streams", type=int, default=10)
    parser.add_argument("--first-seed", type=int, default=101)
    parser.add_argument("--concurrency", type=int, default=32)
    args = parser.parse_args(argv)
    result = (run_experiment(args.output, rounds=args.rounds, streams=args.streams, first_seed=args.first_seed, concurrency=args.concurrency)
              if args.command == "run" else independent_readout(args.output, concurrency=args.concurrency))
    print(json.dumps({"status": result["status"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
