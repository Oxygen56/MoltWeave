"""Offline analysis of retained continual experiments; never calls a model.

Stream-paired statistics are descriptive. Structural fixtures and partial runs
remain explicitly different from completed real-model effect measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import html
import itertools
import json
import math
from pathlib import Path
import random
from statistics import mean

from .common import digest, read_json, write_json

ARMS = ("fixed_mechanism", "fixed_p", "joint")
BOOTSTRAP_SEED = 20261023
BOOTSTRAP_REPLICATES = 10000


def paired_statistics(pairs: list[dict]) -> dict:
    """Each pair has stream,left,right rates. Never pool tasks as independent."""
    deltas = [float(row["left"]) - float(row["right"]) for row in pairs]
    n = len(deltas)
    result = {"unit": "stream", "n": n, "pairs": pairs,
              "mean_difference": mean(deltas) if n else None,
              "mean_difference_percentage_points": 100 * mean(deltas) if n else None,
              "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
              "bootstrap_percentile_95_ci": None, "exact_sign_flip_two_sided_p": None,
              "sign_flip_assignments": 0,
              "interpretation": "Descriptive paired stream comparison; sign-flip inference assumes exchangeability. No causal or population superiority claim."}
    if not n:
        return result
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n
                     for _ in range(BOOTSTRAP_REPLICATES))
    def percentile(p):
        position = (len(samples) - 1) * p
        lower = int(position)
        upper = min(lower + 1, len(samples) - 1)
        return samples[lower] + (samples[upper] - samples[lower]) * (position - lower)
    result["bootstrap_percentile_95_ci"] = [percentile(.025), percentile(.975)]
    if n <= 20:
        observed = abs(sum(deltas))
        extreme = sum(abs(sum(sign * value for sign, value in zip(signs, deltas))) >= observed - 1e-12
                      for signs in itertools.product((-1, 1), repeat=n))
        result["sign_flip_assignments"] = 2 ** n
        result["exact_sign_flip_two_sided_p"] = extreme / (2 ** n)
    else:
        result["exact_sign_flip_note"] = "Not enumerated above 20 streams; no approximate p-value substituted"
    return result


def _rate(report: dict | None) -> float | None:
    if report is None:
        return None
    passed, total = report["passed"], report["total"]
    if type(passed) is not int or type(total) is not int or not 0 <= passed <= total or total <= 0:
        raise ValueError("Invalid observed report numerator/denominator")
    return passed / total


def _diff(before: dict, after: dict) -> list[dict]:
    return [{"field": key, "before": before.get(key), "after": after.get(key)}
            for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]


def _relative(output: Path, path: Path) -> str | None:
    return str(path.relative_to(output)) if path.exists() else None


def memory_chain(experience: dict, *, stream, arm: str, round_index: int, path: str) -> dict:
    """Follow actual record/source IDs; never infer a missing write or recall."""
    traces = experience.get("traces", [])
    first = traces[:4]
    kinds = {}
    for item in traces:
        bucket = kinds.setdefault(item.get("kind", "unlabeled"), {"passed": 0, "total": 0, "unknown_outcome": 0})
        bucket["total"] += 1
        passed = item.get("feedback", {}).get("passed")
        bucket["passed"] += passed is True
        bucket["unknown_outcome"] += type(passed) is not bool
    result = {"stream": stream, "arm": arm, "round": round_index, "path": path,
              "observed_tasks": len(traces), "episode_passed": experience.get("passed"),
              "episode_total": experience.get("total"), "four_steps_present": len(first) == 4,
              "structural_chain_complete": False, "all_four_tasks_passed": False,
              "effective_closed_loop": False, "task_kinds": kinds, "chains": [], "missing": []}
    if len(first) != 4:
        result["missing"].append("fewer_than_four_observed_steps")
        return result
    steps = [item.get("trace", {}) for item in first]
    result["steps"] = [{"trace_id": item.get("trace_id"), "kind": item.get("kind"),
                        "passed": item.get("feedback", {}).get("passed"),
                        "mechanism_hash": item.get("trace", {}).get("mechanism_hash")}
                       for item in first]
    result["all_four_tasks_passed"] = all(item.get("feedback", {}).get("passed") is True for item in first)
    same_entity = len({step.get("entity") for step in steps}) == 1 and steps[0].get("entity") is not None
    kinds = [item.get("kind") for item in first]
    right_kinds = kinds[1] == kinds[3] == "recall" and kinds[0] == "observe" and kinds[2] in {"observe", "correction"}
    continuous = all(isinstance(steps[i].get("memory_after_hash"), str) and bool(steps[i]["memory_after_hash"])
                     and steps[i]["memory_after_hash"] == steps[i+1].get("memory_before_hash") for i in range(3))
    memory_only = all(not steps[i].get("ranked_documents") and not steps[i].get("tool_events") for i in (1, 3))
    for condition, reason in ((same_entity, "four_steps_do_not_share_entity"), (right_kinds, "observed_step_kinds_do_not_match"),
                              (continuous, "memory_hash_continuity_missing_or_broken"), (memory_only, "recall_has_external_documents_or_tools")):
        if not condition:
            result["missing"].append(reason)
    for event in steps[0].get("write_events", []):
        if event.get("type") not in {"written", "replaced"}:
            continue
        old_id = event.get("new_record_id", event.get("record_id"))
        if not isinstance(old_id, str) or not old_id or not isinstance(event.get("source_id"), str) or not event["source_id"]:
            continue
        old_reads = [row for row in steps[1].get("selected_memories", [])
                     if row.get("id") == old_id and row.get("source_id") == event["source_id"] and row.get("status") == "active"]
        replacements = [row for row in steps[2].get("write_events", []) if row.get("type") == "replaced"
                        and old_id in row.get("old_record_ids", [])
                        and isinstance(event.get("source_family"), str) and bool(event["source_family"])
                        and row.get("source_family") == event.get("source_family")
                        and isinstance(row.get("source_id"), str) and bool(row["source_id"])
                        and row.get("source_id") != event.get("source_id")]
        # Several correction records can exist in one four-step episode.
        for replacement in replacements or [None]:
            new_id = replacement.get("new_record_id", replacement.get("record_id")) if replacement else None
            new_reads = [row for row in steps[3].get("selected_memories", [])
                         if replacement and row.get("id") == new_id and row.get("source_id") == replacement.get("source_id")
                         and row.get("status") == "active"]
            lineage_ok = bool(old_reads and new_reads and all(isinstance(old_reads[0].get(key), str)
                and bool(old_reads[0][key]) and old_reads[0][key] == new_reads[0].get(key)
                for key in ("tenant", "owner", "entity", "key", "source_family")))
            chain = {"old_source_id": event["source_id"], "old_record_id": old_id,
                     "initial_write_event_id": event.get("id"), "source_family": event.get("source_family"),
                     "old_record_recalled": bool(old_reads), "replacement_observed": replacement is not None,
                     "replacement_event_id": replacement.get("id") if replacement else None,
                     "new_source_id": replacement.get("source_id") if replacement else None,
                     "new_record_id": new_id, "new_active_record_recalled": bool(new_reads),
                     "same_scoped_entity_key_lineage": lineage_ok,
                     "complete": bool(old_reads and replacement and new_reads and lineage_ok and not result["missing"])}
            result["chains"].append(chain)
    if not result["chains"]:
        result["missing"].append("no_committed_initial_source_record")
    result["structural_chain_complete"] = any(chain["complete"] for chain in result["chains"])
    result["effective_closed_loop"] = result["structural_chain_complete"] and result["all_four_tasks_passed"]
    return result


def _call_statistics(output: Path) -> dict:
    buckets = defaultdict(lambda: defaultdict(Counter))
    phases = defaultdict(Counter)
    totals = Counter()
    for path in sorted((output / "model-calls").glob("*.json")):
        receipt = read_json(path)
        metadata = receipt.get("metadata", {})
        phase = metadata.get("phase", "unassigned")
        arm = metadata.get("arm") or ("shared_policy_audit" if "independent_policy_audit" in phase else "unassigned")
        purpose = receipt.get("purpose", "unassigned")
        values = Counter(logical_requests=1, completed_requests=int(receipt.get("status") == "completed"),
                         failed_requests=int(receipt.get("status") != "completed"))
        attempts = receipt.get("physical_attempts")
        if isinstance(attempts, list):
            values["physical_attempts"] = len(attempts)
            for attempt in attempts:
                usage = attempt.get("usage", {})
                values["attempts_with_usage"] += bool(usage)
                values["attempts_without_usage"] += not bool(usage)
                values["failed_physical_attempts"] += attempt.get("status") == "failed"
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    values[key] += usage.get(key, 0) or 0
        else:
            values["requests_without_physical_attempt_array"] = 1
        buckets[str(arm)][str(purpose)].update(values)
        phases[str(phase)].update(values)
        totals.update(values)
    return {"totals": dict(totals), "by_arm_and_purpose": {a: {p: dict(c) for p, c in purposes.items()} for a, purposes in buckets.items()},
            "by_phase": {p: dict(c) for p, c in phases.items()},
            "usage_note": "Provider-reported usage summed once per physical attempt; missing usage is unknown, not free. Shared independent P-audit costs are not assigned to the joint arm."}


def _aggregate(rows: list[dict]) -> dict:
    observed = [row for row in rows if row is not None]
    return {"streams": len(observed), "passed": sum(row["passed"] for row in observed),
            "total": sum(row["total"] for row in observed),
            "mean_stream_rate": mean(_rate(row) for row in observed) if observed else None}


def analyze(output: Path) -> dict:
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    run_summary = read_json(output / "summary.json") if (output / "summary.json").exists() else {}
    independent = read_json(output / "independent.json") if (output / "independent.json").exists() else {}
    seeds, arms, rounds = manifest["seeds"], list(manifest.get("arms", ARMS)), manifest["rounds"]
    warnings = []
    reports = {}
    for version in independent.get("versions", []):
        key = (str(version["stream"]), version["arm"], int(version["generation"]))
        if key in reports:
            raise ValueError("Duplicate independent version observation")
        reports[key] = version["reports"]
        for report in version["reports"].values():
            _rate(report)
    version_rows, adoption, diagnostics, chains, probe_rows = [], {}, [], [], []
    online = defaultdict(list)
    for seed in seeds:
        for arm in arms:
            lane = output / "streams" / str(seed) / arm
            states = {}
            for g in range(rounds + 1):
                path = lane / "versions" / f"g{g}.json"
                if path.exists():
                    states[g] = read_json(path)
                else:
                    warnings.append(f"Missing version: {seed}/{arm}/g{g}")
            counts = Counter(rounds_observed=0, mechanism_adoptions=0, policy_adoptions=0)
            for g in range(rounds + 1):
                state = states.get(g)
                observed = reports.get((str(seed), arm, g), {})
                row = {"stream": seed, "arm": arm, "generation": g, "version_present": state is not None,
                       "version_path": _relative(output, lane / "versions" / f"g{g}.json"),
                       "independent_path": _relative(output, output / "independent" / str(seed) / arm / f"g{g}.json"),
                       "reports": observed, "mechanism_hash": digest(state["mechanism"]) if state else None,
                       "policy_hash": digest(state["policy"]) if state else None,
                       "memory_hash": digest(state["memory"]) if state and "memory" in state else None,
                       "mechanism_diff": _diff(states[g-1]["mechanism"], state["mechanism"]) if state and g-1 in states else [],
                       "policy_diff": _diff(states[g-1]["policy"], state["policy"]) if state and g-1 in states else []}
                for split, report in observed.items():
                    if split in {"acceptance", "transfer", "no_memory"} and row["mechanism_hash"] and report["mechanism_hash"] != row["mechanism_hash"]:
                        warnings.append(f"Independent mechanism hash mismatch: {seed}/{arm}/g{g}/{split}")
                folder = lane / "rounds" / f"r{g:02d}"
                row["round_paths"] = {name: _relative(output, folder / (name + ".json"))
                                      for name in ("experience", "transition", "mechanism-search", "policy-proposal", "policy-probe")}
                if (folder / "transition.json").exists() and g < rounds:
                    transition = read_json(folder / "transition.json")
                    counts["rounds_observed"] += 1
                    if g in states and g+1 in states:
                        m_changed = states[g]["mechanism"] != states[g+1]["mechanism"]
                        p_changed = states[g]["policy"] != states[g+1]["policy"]
                        counts["mechanism_adoptions"] += m_changed
                        counts["policy_adoptions"] += p_changed
                        for key, actual in (("parent_m", digest(states[g]["mechanism"])), ("loaded_m_next", digest(states[g+1]["mechanism"])),
                                            ("parent_p", digest(states[g]["policy"])), ("loaded_p_next", digest(states[g+1]["policy"]))):
                            if transition.get(key) != actual:
                                warnings.append(f"Transition {key} mismatch: {seed}/{arm}/r{g}")
                        if transition.get("mechanism_changed") != m_changed or transition.get("policy_changed") != p_changed:
                            warnings.append(f"Transition adoption flag mismatch: {seed}/{arm}/r{g}")
                    row["transition"] = transition
                if (folder / "experience.json").exists() and g < rounds:
                    experience = read_json(folder / "experience.json")
                    online[(arm, g)].append({"passed": experience["passed"], "total": experience["total"]})
                    chains.append(memory_chain(experience, stream=seed, arm=arm, round_index=g,
                                               path=str((folder / "experience.json").relative_to(output))))
                if (folder / "mechanism-search.json").exists() and g < rounds:
                    search = read_json(folder / "mechanism-search.json")
                    row["loaded_search"] = {key: search.get(key) for key in ("policy_hash", "initial_mechanism_hash", "initial_memory_hash", "selected_mechanism_hash", "selected_trial", "mechanism_adopted")}
                    diagnosis = search.get("diagnosis", {})
                    if diagnosis.get("status") == "invalid_diagnosis":
                        diagnostics.append({"stream": seed, "arm": arm, "round": g, "scope": "mechanism_search",
                                            "status": "invalid_diagnosis", "path": row["round_paths"]["mechanism-search"]})
                    for i, trial in enumerate(search.get("trials", [])):
                        diagnostics.append({"stream": seed, "arm": arm, "round": g, "scope": "mechanism_search",
                                            "trial": i, "status": trial["status"], "gain": trial.get("gain"),
                                            "selected": i == search.get("selected_trial"), "action": {k: trial.get("action", {}).get(k) for k in ("modules", "operator", "parent")},
                                            "path": row["round_paths"]["mechanism-search"]})
                if (folder / "policy-proposal.json").exists() and g < rounds:
                    proposal = read_json(folder / "policy-proposal.json")
                    if proposal.get("status") == "invalid_policy":
                        diagnostics.append({"stream": seed, "arm": arm, "round": g, "scope": "policy_proposal",
                                            "status": "invalid_policy", "path": row["round_paths"]["policy-proposal"]})
                if (folder / "policy-probe.json").exists() and g < rounds:
                    probe = read_json(folder / "policy-probe.json")
                    probe_rows.append({"stream": seed, "arm": arm, "round": g, "scope": probe.get("scope"),
                                       "future_delta": probe.get("future_delta"), "raw_future_delta": probe.get("raw_future_delta"),
                                       "valid_search_pair": probe.get("valid_search_pair"), "adopted": probe.get("adopted"),
                                       "policy_distinct": probe.get("policy_distinct"),
                                       "promotion_eligible": probe.get("promotion_eligible"), "arm_rule": probe.get("arm_rule"),
                                       "distinct_selected_mechanisms": probe.get("distinct_selected_mechanisms"),
                                       "path": row["round_paths"]["policy-probe"]})
                    row["probe_forks"] = {label: {key: fork.get(key) for key in ("policy_hash", "initial_mechanism_hash", "initial_memory_hash", "history_hash", "selected_mechanism_hash")}
                                          for label, fork in probe.get("forks", {}).items()}
                    for label, fork in probe.get("forks", {}).items():
                        if fork.get("diagnosis", {}).get("status") == "invalid_diagnosis":
                            diagnostics.append({"stream": seed, "arm": arm, "round": g, "scope": "meta_development_probe", "fork": label,
                                                "status": "invalid_diagnosis", "path": row["round_paths"]["policy-probe"]})
                        diagnostics.append({"stream": seed, "arm": arm, "round": g, "scope": "meta_development_probe", "fork": label,
                                            "status": fork.get("trial", {}).get("status", "missing_trial"), "path": row["round_paths"]["policy-probe"]})
                version_rows.append(row)
            adoption[f"{seed}/{arm}"] = dict(counts)
    curves = {}
    for split in ("acceptance", "transfer"):
        curves[split] = {arm: [{"generation": g, **_aggregate([reports.get((str(seed), arm, g), {}).get(split) for seed in seeds])}
                               for g in range(rounds + 1)] for arm in arms}
    curves["online"] = {arm: [{"generation": g, **_aggregate(online[(arm, g)])} for g in range(rounds)] for arm in arms}
    comparisons = {}
    for split in ("acceptance", "transfer"):
        pairs = []
        for seed in seeds:
            left = reports.get((str(seed), "joint", rounds), {}).get(split)
            right = reports.get((str(seed), "fixed_p", rounds), {}).get(split)
            if left is not None and right is not None:
                pairs.append({"stream": seed, "left": _rate(left), "right": _rate(right)})
        comparisons[split] = paired_statistics(pairs)
        comparisons[split]["missing_streams"] = [seed for seed in seeds if str(seed) not in {str(p["stream"]) for p in pairs}]
    ablation, wide_context = {}, {}
    for arm in arms:
        pairs = []
        for seed in seeds:
            row = reports.get((str(seed), arm, rounds), {})
            if "acceptance" in row and "no_memory" in row:
                pairs.append({"stream": seed, "left": _rate(row["acceptance"]), "right": _rate(row["no_memory"])})
        ablation[arm] = paired_statistics(pairs)
        wide_pairs = []
        for seed in seeds:
            row = reports.get((str(seed), arm, rounds), {})
            if "acceptance" in row and "wide_context_baseline" in row:
                wide_pairs.append({"stream": seed, "left": _rate(row["acceptance"]), "right": _rate(row["wide_context_baseline"])})
        wide_context[arm] = paired_statistics(wide_pairs)
    audits = independent.get("policy_audits", [])
    audit_keys = [(str(row["stream"]), row["generation"]) for row in audits]
    if len(audit_keys) != len(set(audit_keys)):
        raise ValueError("Duplicate independent policy audit")
    audit_by_checkpoint = {}
    for checkpoint in sorted({row["generation"] for row in audits}):
        rows = [row for row in audits if row["generation"] == checkpoint]
        all_pairs, valid_pairs, distinct_policy_pairs, same_policy_pairs = [], [], [], []
        policy_counts = Counter(distinct=0, identical=0, unknown=0)
        for row in rows:
            pair = {"stream": row["stream"], "left": _rate({"passed": row["new_passed"], "total": row["total"]}),
                    "right": _rate({"passed": row["old_passed"], "total": row["total"]})}
            all_pairs.append(pair)
            raw = pair["left"] - pair["right"]
            if row.get("raw_future_delta") is not None and abs(raw - row["raw_future_delta"]) > 1e-9:
                warnings.append(f"Policy audit raw delta mismatch: {row['stream']}/g{checkpoint}")
            measured = row.get("future_delta")
            old_hash, new_hash = row.get("old_policy_hash"), row.get("new_policy_hash")
            policy_distinct = None
            if isinstance(old_hash, str) and old_hash and isinstance(new_hash, str) and new_hash:
                policy_distinct = old_hash != new_hash
                if type(row.get("policy_distinct")) is bool and row["policy_distinct"] != policy_distinct:
                    warnings.append(f"Policy distinct flag/hash mismatch: {row['stream']}/g{checkpoint}")
            policy_counts["unknown" if policy_distinct is None else "distinct" if policy_distinct else "identical"] += 1
            if row.get("valid_search_pair") is True and type(measured) in (int, float) and math.isfinite(measured):
                if abs(raw - measured) > 1e-9:
                    warnings.append(f"Policy audit delta mismatch: {row['stream']}/g{checkpoint}")
                valid_pairs.append(pair)
                if policy_distinct is True:
                    distinct_policy_pairs.append(pair)
                elif policy_distinct is False:
                    same_policy_pairs.append(pair)
            elif row.get("valid_search_pair") is not True and measured is not None:
                warnings.append(f"Unvalidated policy audit has a measured effect field; excluded from valid-pair effect: {row['stream']}/g{checkpoint}")
        audit_by_checkpoint[str(checkpoint)] = {**paired_statistics(valid_pairs),
            "n_valid": len(valid_pairs), "total_observed": len(rows), "total_planned": len(seeds),
            "invalid_pairs": sum(row.get("valid_search_pair") is False for row in rows),
            "unknown_validity_or_effect": len(rows) - len(valid_pairs) - sum(row.get("valid_search_pair") is False for row in rows),
            "missing_streams": [seed for seed in seeds if str(seed) not in {str(row["stream"]) for row in rows}],
            "all_attempt_operational_raw_outcomes": paired_statistics(all_pairs),
            "policy_identity_counts": dict(policy_counts),
            "valid_and_distinct_policy_statistics": paired_statistics(distinct_policy_pairs),
            "same_policy_calibration": paired_statistics(same_policy_pairs),
            "valid_pairs_with_unknown_policy_identity": len(valid_pairs) - len(distinct_policy_pairs) - len(same_policy_pairs),
            "evolved_policy_effect_evidence_available": bool(distinct_policy_pairs),
            "evolved_policy_inference_status": "descriptive_distinct_policy_readout" if distinct_policy_pairs else "no_distinct_policy_evidence",
            "distinct_selected_mechanisms": sum(bool(row["distinct_selected_mechanisms"]) for row in rows),
            "nonzero_delta_with_same_selected_mechanism": sum(not row["distinct_selected_mechanisms"] and abs(pair["left"]-pair["right"]) > 1e-9 for row, pair in zip(rows, all_pairs)),
            "observations": rows,
            "validity_note": "Effect statistics use only explicitly valid executed search pairs; invalid/unknown attempts remain above and in all-attempt operational outcomes. Conditional valid-pair statistics may be selected; do not claim unconditional P superiority.",
            "paths": [_relative(output, output / "policy-audits" / str(row["stream"]) / f"g{checkpoint}.json") for row in rows]}
    memory_summary = {}
    for arm in arms:
        rows = [row for row in chains if row["arm"] == arm]
        kinds = defaultdict(Counter)
        for row in rows:
            for kind, values in row["task_kinds"].items():
                kinds[kind].update(values)
        memory_summary[arm] = {"episodes_observed": len(rows), "four_step_episodes": sum(row["four_steps_present"] for row in rows),
                               "structural_chains_complete": sum(row["structural_chain_complete"] for row in rows),
                               "four_tasks_all_passed": sum(row["all_four_tasks_passed"] for row in rows),
                               "effective_closed_loops": sum(row["effective_closed_loop"] for row in rows),
                               "task_kinds": {kind: dict(values) for kind, values in kinds.items()},
                               "observed_tasks_passed": sum(row.get("episode_passed") or 0 for row in rows),
                               "observed_tasks_total": sum(row.get("episode_total") or 0 for row in rows)}
    expected_versions = len(seeds) * len(arms) * (rounds + 1)
    expected_keys = {(str(seed), arm, g) for seed in seeds for arm in arms for g in range(rounds + 1)}
    if set(reports) - expected_keys:
        warnings.append("Unexpected independent version observations outside the declared streams/arms/generations")
    complete = (independent.get("status") == "completed" and set(reports) == expected_keys
                and all({"acceptance", "transfer"} <= set(report) for report in reports.values()))
    if not complete:
        warnings.append("Independent readout incomplete or unavailable; missing observations are not zero outcomes")
    regressions = []
    for seed in seeds:
        for arm in arms:
            for split in ("acceptance", "transfer"):
                for g in range(1, rounds + 1):
                    before = _rate(reports.get((str(seed), arm, g-1), {}).get(split))
                    after = _rate(reports.get((str(seed), arm, g), {}).get(split))
                    if before is not None and after is not None and after < before:
                        regressions.append({"stream": seed, "arm": arm, "split": split, "generation": g, "before": before, "after": after})
    result = {"schema": 1, "status": "completed_readout" if complete else "partial_readout",
              "run_status": run_summary.get("status", "summary_unavailable"),
              "source_scope": manifest.get("source_scope", "Unspecified; inspect original manifest"),
              "manifest_hash": digest(manifest), "independent_hash": digest(independent) if independent else None,
              "planned_streams": seeds, "arms": arms, "rounds": rounds,
              "observed_independent_versions": len(reports), "expected_independent_versions": expected_versions,
              "curves": curves, "terminal_joint_minus_fixed_p": comparisons,
              "independent_policy_audit": {"primary_checkpoint": rounds, "checkpoints": audit_by_checkpoint,
                                           "primary": audit_by_checkpoint.get(str(rounds)),
                                           "meta_development_used_as_independent": False},
              "memory_ablation_current_minus_disabled": ablation,
              "current_minus_wide_context_baseline": wide_context, "adoptions": adoption,
              "diagnostics": diagnostics, "meta_development_probes": probe_rows,
              "diagnostic_summary": {"statuses": dict(Counter(row["status"] for row in diagnostics)),
                                     "executed_main_candidates_not_selected": sum(row["scope"] == "mechanism_search" and row["status"] == "executed" and not row.get("selected") for row in diagnostics)},
              "regressions": regressions, "versions": version_rows,
              "memory_chain_summary": memory_summary, "calls": _call_statistics(output),
              "warnings": warnings, "selection_allowed": False,
              "limits": ["Shared authored synthetic generation grammar, not independent real-business validation",
                         "One model sample per retained execution; temperature zero does not remove sampling variation",
                         "Stream-paired descriptive confidence intervals and p-values do not establish causal superiority",
                         "Meta-development policy promotions are optimization observations, never independent P evidence",
                         "Terminal memory ablation changes reads and writes together; it does not isolate the write-policy contribution"]}
    write_json(output / "memory-chain.json", {"summary": memory_summary, "episodes": chains,
                                             "meaning": "Observed source/record-ID links and hash continuity; structural completion is separate from actual task success"})
    write_json(output / "analysis.json", result)
    (output / "RESULTS.md").write_text(_markdown(result), encoding="utf-8")
    (output / "index.html").write_text(_html(result), encoding="utf-8")
    return result


def _number(value, digits=2):
    return "unavailable" if value is None else f"{value:.{digits}f}"


def _markdown(result: dict) -> str:
    lines = ["# Continual experiment readout", "", f"Analysis status: **{result['status']}**. Run status: **{result['run_status']}**. Source: {result['source_scope']}", "",
             "All numbers below come from retained observations. Structural tests are not model-effect measurements. Missing data is unavailable, not zero.", "",
             "## Terminal mechanism comparison", "", "| Partition | Paired streams | Joint − fixed-P (pp) | 95% stream bootstrap CI (pp) | Exact sign-flip p |", "|---|---:|---:|---|---:|"]
    for split, stats in result["terminal_joint_minus_fixed_p"].items():
        ci = stats["bootstrap_percentile_95_ci"]
        lines.append(f"| {split} | {stats['n']} | {_number(stats['mean_difference_percentage_points'])} | {', '.join(_number(100*x) for x in ci) if ci else 'unavailable'} | {_number(stats['exact_sign_flip_two_sided_p'], 4)} |")
    lines += ["", "The unit is the stream, not each question. Bootstrap seed 20261023, 10,000 resamples. Exact two-sided sign-flip enumeration is descriptive and assumes exchangeability. These comparisons do not establish P's isolated benefit.", "", "## Every frozen generation", "", "| Split | Arm | Generation | Observed streams | Passed / total | Mean stream success |", "|---|---|---:|---:|---:|---:|"]
    for split in ("acceptance", "transfer"):
        for arm, points in result["curves"][split].items():
            for point in points:
                rate = point["mean_stream_rate"]
                lines.append(f"| {split} | {arm} | {point['generation']} | {point['streams']} | {point['passed']}/{point['total']} | {_number(100*rate if rate is not None else None)}% |")
    audit = result["independent_policy_audit"]["primary"]
    lines += ["", "## Independent terminal P audit", ""]
    if audit:
        distinct, calibration = audit["valid_and_distinct_policy_statistics"], audit["same_policy_calibration"]
        lines += [f"Fresh future-search audit: valid executed pairs={audit['n_valid']}/{audit['total_observed']} observed ({audit['total_planned']} planned); invalid={audit['invalid_pairs']}, unknown validity/effect={audit['unknown_validity_or_effect']}. All-valid-pair execution contrast = {_number(audit['mean_difference_percentage_points'])} pp.",
                  f"Valid and actually distinct P: n={distinct['n']}, contrast={_number(distinct['mean_difference_percentage_points'])} pp. Identical-P calibration: n={calibration['n']}, contrast={_number(calibration['mean_difference_percentage_points'])} pp. Unknown policy identity among valid pairs={audit['valid_pairs_with_unknown_policy_identity']}.",
                  f"Evolved-P evidence status: **{audit['evolved_policy_inference_status']}**. Same-policy positive scores cannot establish evolved-P benefit.",
                  f"All-attempt operational raw outcome difference = {_number(audit['all_attempt_operational_raw_outcomes']['mean_difference_percentage_points'])} pp. This includes invalid/fallback attempts and is not evidence of a successful changed P search. Distinct selected mechanisms in {audit['distinct_selected_mechanisms']} observed streams.",
                  f"Nonzero differences with the same selected mechanism: {audit['nonzero_delta_with_same_selected_mechanism']}. This is sampling variation, not proof of changed search mechanisms."]
    else:
        lines.append("Unavailable. Meta-development promotion results are not substituted.")
    lines += ["", "All independent checkpoints, stream pairs, confidence intervals and exact p-values are retained in analysis.json. No checkpoint or winning generation is selected.", "", "## Terminal memory ablation", "", "| Arm | Paired streams | Current M with memory − same M without reads/writes (pp) |", "|---|---:|---:|"]
    for arm, stats in result["memory_ablation_current_minus_disabled"].items():
        lines.append(f"| {arm} | {stats['n']} | {_number(stats['mean_difference_percentage_points'])} |")
    lines += ["", "This measures combined memory-read/write availability, not the isolated benefit of the evolved write policy.", "", "## Wide-context baseline", "", "| Arm | Paired streams | Current M − fixed baseline with wider context (pp) |", "|---|---:|---:|"]
    for arm, stats in result["current_minus_wide_context_baseline"].items():
        lines.append(f"| {arm} | {stats['n']} | {_number(stats['mean_difference_percentage_points'])} |")
    lines += ["", "This is a separate fixed-mechanism context-size control; it has its own recorded mechanism hash and is not treated as the current M.", "", "## Actual adoption and memory chains", "", "| Lane | Observed rounds | M changes | P changes |", "|---|---:|---:|---:|"]
    for lane, stats in result["adoptions"].items():
        lines.append(f"| {lane} | {stats['rounds_observed']} | {stats['mechanism_adoptions']} | {stats['policy_adoptions']} |")
    lines += ["", "| Arm | Episodes | Structural chains | All four tasks passed | Effective closed loops |", "|---|---:|---:|---:|---:|"]
    for arm, stats in result["memory_chain_summary"].items():
        lines.append(f"| {arm} | {stats['episodes_observed']} | {stats['structural_chains_complete']} | {stats['four_tasks_all_passed']} | {stats['effective_closed_loops']} |")
    counts = Counter(row["status"] for row in result["diagnostics"])
    lines += ["", f"Diagnostic statuses (main search and meta forks, scopes retained separately in JSON): {dict(counts)}.",
              f"Observed adjacent-version regressions: {len(result['regressions'])}; every regression is retained in analysis.json.", "", "## Physical requests and costs", "", "```json", json.dumps(result["calls"], indent=2), "```", "", "## Limits and missing evidence", ""]
    lines += ["- " + text for text in result["limits"] + result["warnings"]]
    lines += ["", "[Interactive offline evidence](index.html) · [Full analysis](analysis.json) · [Memory chains](memory-chain.json) · [Independent inputs](independent.json)", ""]
    return "\n".join(lines)


def _html(result: dict) -> str:
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace("&", "\\u0026")
    title = html.escape(str(result["source_scope"]))
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoltWeave · Continual evidence</title><style>
body{font:15px/1.6 system-ui,sans-serif;background:#0c111b;color:#e5edf8;margin:0}main{max-width:1180px;margin:auto;padding:32px}h1{font-size:32px;line-height:1.2}h2{margin-top:34px}p,.muted{color:#aebbd0}a{color:#86c3ff}section{background:#141d2b;border:1px solid #29374d;border-radius:16px;padding:22px;margin:18px 0}select,button{background:#223249;color:white;border:1px solid #4a617d;padding:8px;border-radius:7px;margin:4px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px;text-align:left;border-bottom:1px solid #29374d}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0c111b;padding:14px;border-radius:8px;font-size:12px;max-height:440px;overflow:auto}.scroll{overflow:auto;max-height:420px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.stat{padding:16px;background:#1b2940;border-radius:10px}svg{width:100%;height:auto}code{overflow-wrap:anywhere}.warning{color:#ffcf90}</style>
<main><h1>MoltWeave · Continuous improvement, inspectable</h1><p>Retained observations, every frozen generation, and separate independent policy evidence.</p><p>""" + title + """</p>
<p><a href="manifest.json">Manifest</a> · <a href="analysis.json">Full analysis</a> · <a href="RESULTS.md">Report</a> · <a href="memory-chain.json">Memory chains</a> · <a href="independent.json">Independent readout</a></p>
<div class="grid" id="summary"></div><section><h2>All versions · three arms</h2><select id="partition"><option>acceptance</option><option>transfer</option><option>online</option></select><p>Mean success across observed streams. Missing observations remain gaps. Online experience is optimization data.</p><div id="chart"></div><div class="scroll" id="curveTable"></div></section>
<section><h2>Inspect actual loaded versions and search choices</h2><select id="stream"></select><select id="arm"></select><select id="generation"></select><div id="version"></div></section>
<section><h2>Independent P audit</h2><p>Fresh future searches; meta-development promotion results are excluded. The terminal checkpoint is predeclared, rather than chosen after results.</p><pre id="audit"></pre></section>
<section><h2>Memory lifecycle and ablation</h2><p>A structural chain requires an observed write, recall of that exact record, a same-lineage replacement, and recall of the new active record, with continuous memory hashes. Four-task answer success is counted separately. No missing step is invented.</p><pre id="memory"></pre><a href="memory-chain.json">Inspect every complete and incomplete chain</a></section>
<section><h2>Rejected candidates, invalid diagnostics and regressions</h2><pre id="diagnostics"></pre><p>Full statuses, scopes, stream IDs and source paths remain in analysis.json.</p></section>
<section><h2>Actual physical calls and token usage</h2><pre id="cost"></pre></section><section><h2>Limits and missing evidence</h2><ul id="limits"></ul></section></main>
<script id="evidence" type="application/json">""" + payload + """</script><script>
const D=JSON.parse(document.getElementById('evidence').textContent), $=id=>document.getElementById(id);
const pct=x=>x==null?'unavailable':(100*x).toFixed(2)+'%', json=x=>JSON.stringify(x,null,2);
function text(parent,tag,value){const el=document.createElement(tag);el.textContent=value;parent.appendChild(el);return el}
function link(parent,path,label){if(!path)return;const a=document.createElement('a');a.href=path.split('/').map(encodeURIComponent).join('/');a.textContent=label;parent.appendChild(a);parent.append(' · ')}
function stat(label,value){const box=document.createElement('div');box.className='stat';text(box,'strong',label);text(box,'div',value);$('summary').appendChild(box)}
stat('Readout status',D.status+' · '+D.run_status);stat('Frozen version observations',D.observed_independent_versions+' / '+D.expected_independent_versions);stat('Terminal joint − fixed-P',pct(D.terminal_joint_minus_fixed_p.acceptance.mean_difference));stat('Physical attempts',D.calls.totals.physical_attempts??'unavailable');
const colors={fixed_mechanism:'#91a5be',fixed_p:'#6bdbbc',joint:'#83aaff'};
function inspect(arm,g){$('arm').value=arm;$('generation').value=g;version();$('version').scrollIntoView({behavior:'smooth',block:'start'})}
function chart(){
const split=$('partition').value,curves=D.curves[split],width=1000,height=300,pad=42,N=Math.max(1,D.rounds);
let svg='<svg viewBox="0 0 1000 300" role="img" aria-label="Observed success by generation">';
for(let y=0;y<=100;y+=25){const py=height-pad-(height-2*pad)*y/100;svg+='<line x1="42" x2="958" y1="'+py+'" y2="'+py+'" stroke="#2a3a50"/><text x="4" y="'+(py+5)+'" fill="#aebbd0" font-size="12">'+y+'%</text>'}
for(let ai=0;ai<D.arms.length;ai++){const arm=D.arms[ai];let segment=[];
const flush=()=>{if(segment.length)svg+='<polyline fill="none" stroke="'+colors[arm]+'" stroke-width="2.5" points="'+segment.join(' ')+'"/>';segment=[]};
for(const p of curves[arm]){if(p.mean_stream_rate==null){flush();continue}
const x=pad+(width-2*pad)*p.generation/N,y=height-pad-(height-2*pad)*p.mean_stream_rate;segment.push(x+','+y);
svg+='<circle data-arm-index="'+ai+'" data-generation="'+p.generation+'" cx="'+x+'" cy="'+y+'" r="4" fill="'+colors[arm]+'" style="cursor:pointer"/>'}flush()}
svg+='</svg>';$('chart').innerHTML=svg;
for(const circle of $('chart').querySelectorAll('circle'))circle.onclick=()=>inspect(D.arms[Number(circle.dataset.armIndex)],Number(circle.dataset.generation));
const holder=$('curveTable');holder.replaceChildren();const legend=text(holder,'p','');
for(const arm of D.arms){const label=text(legend,'span',arm+'   ');label.style.color=colors[arm]}
const table=text(holder,'table',''),head=text(table,'tr','');for(const h of ['Arm','Version','Streams','Passed / total · inspect','Mean stream success'])text(head,'th',h);
for(const arm of D.arms)for(const p of curves[arm]){const row=text(table,'tr','');for(const value of [arm,'g'+p.generation,p.streams])text(row,'td',value);
const cell=text(row,'td',''),button=text(cell,'button',p.passed+'/'+p.total);button.title='Inspect this generation; select a stream below';button.onclick=()=>inspect(arm,p.generation);text(row,'td',pct(p.mean_stream_rate))}}
function options(id,values){for(const value of values){const option=document.createElement('option');option.value=value;option.textContent=value;$(id).appendChild(option)}}
options('stream',D.planned_streams);options('arm',D.arms);options('generation',Array.from({length:D.rounds+1},(_,i)=>i));
function version(){const row=D.versions.find(v=>String(v.stream)===$('stream').value&&v.arm===$('arm').value&&String(v.generation)===$('generation').value),box=$('version');box.replaceChildren();if(!row){text(box,'p','No retained observation');return}text(box,'h3','Stream '+row.stream+' · '+row.arm+' · g'+row.generation);link(box,row.version_path,'Frozen version');link(box,row.independent_path,'Actual independent traces');for(const [name,path] of Object.entries(row.round_paths))link(box,path,name);text(box,'pre',json({mechanism_hash:row.mechanism_hash,policy_hash:row.policy_hash,memory_hash:row.memory_hash,reports:row.reports,loaded_search:row.loaded_search,probe_forks:row.probe_forks}));for(const [title,diff] of [['M field changes',row.mechanism_diff],['P field changes',row.policy_diff]]){const details=text(box,'details','');text(details,'summary',title+' ('+diff.length+')');text(details,'pre',json(diff))}}
$('partition').onchange=chart;for(const id of ['stream','arm','generation'])$(id).onchange=version;chart();version();$('audit').textContent=json(D.independent_policy_audit);$('memory').textContent=json({chains:D.memory_chain_summary,terminal_read_write_ablation:D.memory_ablation_current_minus_disabled,current_minus_wide_context_baseline:D.current_minus_wide_context_baseline});const counts={};for(const r of D.diagnostics)counts[r.scope+':'+r.status]=(counts[r.scope+':'+r.status]??0)+1;$('diagnostics').textContent=json({statuses:counts,adjacent_version_regressions:D.regressions.length,meta_development_probes:D.meta_development_probes.length});$('cost').textContent=json(D.calls);for(const warning of [...D.limits,...D.warnings])text($('limits'),'li',warning);
</script></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze(args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output), "warnings": len(result["warnings"])}))


if __name__ == "__main__":
    main()
