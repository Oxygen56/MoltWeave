"""Check a v0.2 archive offline; explicitly run/evaluate in a new reproduction."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


SOURCES = {"continual.py", "continual_environment.py", "continual_runtime.py", "continual_memory.py",
           "continual_program.py", "continual_policy.py", "program.py", "common.py", "llm.py"}
ARMS = ("fixed_mechanism", "fixed_p", "joint")
INIT = '"""Frozen v0.2 experiment host."""\n'
READOUT_PATHS = ("independent.json", "independent", "policy-audits", "policy-audit-inputs")
CONTRACT_FIELDS = ("schema", "rounds", "seeds", "arms", "model", "provider_base", "request_contract",
                   "sources", "source_scope", "protocol", "partition_hashes")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or symlinked evidence file: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an evidence object: {path.name}")
    return value


def clean_https(value):
    if not isinstance(value, str) or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise ValueError("Provider contract requires a clean HTTPS URL")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        raise ValueError("Invalid provider URL") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("Provider contract requires HTTPS without userinfo, query, or fragment")


def verify_archive(experiment, expected_manifest_sha256=None):
    prior = Path(experiment).resolve()
    manifest_path = prior / "manifest.json"
    manifest = read_json(manifest_path)
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if expected_manifest_sha256 is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_manifest_sha256) or manifest_sha != expected_manifest_sha256.lower():
            raise ValueError("Manifest SHA256 pin mismatch")
    if (any(field not in manifest for field in CONTRACT_FIELDS) or manifest.get("schema") != 2
            or not isinstance(manifest.get("sources"), dict) or set(manifest["sources"]) != SOURCES):
        raise ValueError("Expected the exact nine-source v0.2 host contract")
    rounds, seeds = manifest.get("rounds"), manifest.get("seeds")
    if (type(rounds) is not int or not 1 <= rounds <= 100 or not isinstance(seeds, list)
            or not 1 <= len(seeds) <= 100 or any(type(seed) is not int for seed in seeds)
            or seeds != list(range(seeds[0], seeds[0] + len(seeds)))
            or manifest.get("arms") != list(ARMS)):
        raise ValueError("Invalid rounds, consecutive seed list, or arm contract")
    if not isinstance(manifest.get("model"), str) or not manifest["model"]:
        raise ValueError("Missing requested model contract")
    clean_https(manifest.get("provider_base"))
    source_root = prior / "frozen-source"
    package = source_root / "moltweave"
    if source_root.is_symlink() or package.is_symlink() or not package.is_dir():
        raise ValueError("Frozen source must be a real package directory")
    allowed = {Path("moltweave") / name for name in SOURCES | {"__init__.py"}}
    for path in source_root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed inside frozen source")
        if path.is_file() and path.suffix == ".py" and path.relative_to(source_root) not in allowed:
            raise ValueError("Unexpected Python source inside frozen package")
    texts = {}
    for name in SOURCES:
        path = package / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing frozen source: {name}")
        text = path.read_text(encoding="utf-8")
        if digest(text) != manifest["sources"][name]:
            raise ValueError(f"Frozen source digest mismatch: {name}")
        texts[name] = text
    init_path = package / "__init__.py"
    if init_path.is_symlink() or not init_path.is_file() or init_path.read_text(encoding="utf-8") != INIT:
        raise ValueError("Frozen __init__ must contain only the declared v0.2 docstring")
    texts["__init__.py"] = INIT
    return {"experiment": prior, "manifest": manifest, "manifest_sha256": manifest_sha, "texts": texts}


def sidecar(output, phase):
    return output.with_name(f".{output.name}.continual-reproduction-{phase}.json")


def protect_output(archive, output):
    target = Path(output)
    if target.is_symlink():
        raise ValueError("Output itself must not be a symlink")
    target = target.resolve()
    prior = archive["experiment"]
    if target == prior or target.is_relative_to(prior) or prior.is_relative_to(target):
        raise ValueError("Output must be separate from the original experiment and its ancestors")
    return target


def verify_complete_run(archive, output):
    manifest = read_json(output / "manifest.json")
    if any(manifest.get(field) != archive["manifest"].get(field) for field in CONTRACT_FIELDS):
        raise ValueError("Reproduction run differs from the original immutable contract")
    summary = read_json(output / "summary.json")
    if summary.get("status") != "all_versions_frozen_pending_readout" or summary.get("errors") != []:
        raise ValueError("Reproduction run has not completed every lane")
    rounds, seeds = manifest["rounds"], manifest["seeds"]
    expected_lanes = {(seed, arm, rounds, "versions_frozen") for seed in seeds for arm in ARMS}
    completed = summary.get("completed", [])
    if (not isinstance(completed, list) or any(not isinstance(row, dict) for row in completed)
            or len(completed) != len(expected_lanes)
            or {(row.get("seed"), row.get("arm"), row.get("rounds"), row.get("status"))
                for row in completed} != expected_lanes):
        raise ValueError("Complete lane receipts are required")
    versions = summary.get("frozen_versions", {})
    expected_keys = {f"{seed}/{arm}/g{g}" for seed in seeds for arm in ARMS for g in range(rounds + 1)}
    if not isinstance(versions, dict) or set(versions) != expected_keys:
        raise ValueError("Full frozen version inventory is required")
    for seed in seeds:
        for arm in ARMS:
            previous = None
            for generation in range(rounds + 1):
                folder = output / "streams" / str(seed) / arm
                state = read_json(folder / "versions" / f"g{generation}.json")
                if digest(state) != versions[f"{seed}/{arm}/g{generation}"] or state.get("round") != generation:
                    raise ValueError("Frozen reproduction state hash or round changed")
                if previous is not None:
                    transition = read_json(folder / "rounds" / f"r{generation-1:02d}" / "transition.json")
                    if (transition.get("status") != "completed"
                            or transition.get("parent_m") != digest(previous["mechanism"])
                            or transition.get("parent_p") != digest(previous["policy"])
                            or transition.get("loaded_m_next") != digest(state["mechanism"])
                            or transition.get("loaded_p_next") != digest(state["policy"])):
                        raise ValueError("Frozen reproduction parent/descendant chain changed")
                previous = state


def verify_output(archive, output, phase):
    target = protect_output(archive, output)
    if phase == "run":
        if target.exists() or sidecar(target, "run").exists() or sidecar(target, "evaluate").exists():
            raise ValueError("Run requires a fresh output and no previous reproduction sidecar")
    elif phase == "evaluate":
        if not target.is_dir() or any((target / name).exists() or (target / name).is_symlink() for name in READOUT_PATHS):
            raise ValueError("Evaluate requires a complete new run with no existing or partial readout")
        if sidecar(target, "evaluate").exists():
            raise ValueError("An evaluate attempt already exists; preserve it rather than overwriting")
        marker = read_json(sidecar(target, "run"))
        if (marker.get("phase") != "run" or marker.get("output") != str(target)
                or marker.get("source_manifest_sha256") != archive["manifest_sha256"]
                or marker.get("sources") != archive["manifest"]["sources"]):
            raise ValueError("Evaluate target must be a run created by this reproduction contract")
        verify_complete_run(archive, target)
    else:
        raise ValueError("Unknown reproduction phase")
    return target


def isolated_environment(staging):
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
           and key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}}
    env.update(PYTHONPATH=str(staging), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONSAFEPATH="1")
    return env


def stage_archive(archive, staging):
    package = staging / "moltweave"
    package.mkdir()
    for name, text in archive["texts"].items():
        (package / name).write_text(text, encoding="utf-8")
    contract = staging / "expected-provider.json"
    contract.write_text(json.dumps(archive["manifest"]), encoding="utf-8")
    return contract


# This constructor performs no request. It uses only the staged frozen host's
# own credential/base pairing and verifies the same destination for both phases.
PREFLIGHT = """
import json, pathlib, sys, urllib.parse, urllib.request
try:
    import moltweave.llm as llm
    root = pathlib.Path(sys.argv[1]).resolve()
    assert pathlib.Path(llm.__file__).resolve() == root / 'moltweave' / 'llm.py'
    expected = json.loads(pathlib.Path(sys.argv[2]).read_text())
    client = llm.ModelClient()
    parsed = urllib.parse.urlsplit(client.base_url)
    assert client.model == expected['model'] and client.base_url == expected['provider_base']
    assert parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
    assert not parsed.fragment and not parsed.query
    assert client.allow_env_proxy is False and client.allow_http_loopback is False
    assert any(isinstance(h, llm._NoRedirect) for h in client._opener.handlers)
    assert all(not h.proxies for h in client._opener.handlers if isinstance(h, urllib.request.ProxyHandler))
    import moltweave.continual as host
    assert host.frozen_sources() == expected['sources']
    for seed in expected['seeds']:
        assert host.partition_contract(seed, expected['rounds']) == expected['partition_hashes'][str(seed)]
except Exception as exc:
    print(json.dumps({'status': 'rejected', 'error_type': type(exc).__name__}))
    raise SystemExit(2)
print(json.dumps({'status': 'matched', 'network_requests': 0}))
"""


def command_for(archive, output, phase, concurrency):
    command = [sys.executable, "-B", "-S", "-P", "-m", "moltweave.continual", phase,
               "--output", str(output), "--concurrency", str(concurrency)]
    if phase == "run":
        manifest = archive["manifest"]
        command += ["--rounds", str(manifest["rounds"]), "--streams", str(len(manifest["seeds"])),
                    "--first-seed", str(manifest["seeds"][0])]
    return command


def write_exclusive(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def execute_phase(archive, output, phase, concurrency):
    if sys.version_info < (3, 11):
        raise ValueError("Reproduction requires Python 3.11 or newer")
    if type(concurrency) is not int or not 1 <= concurrency <= 128:
        raise ValueError("Concurrency must be 1..128")
    target = verify_output(archive, output, phase)
    with tempfile.TemporaryDirectory(prefix="moltweave-v02-reproduction-") as folder:
        staging = Path(folder)
        provider = stage_archive(archive, staging)
        env = isolated_environment(staging)
        checked = subprocess.run([sys.executable, "-B", "-S", "-P", "-c", PREFLIGHT, str(staging), str(provider)],
                                 cwd=staging, env=env, capture_output=True, text=True, check=False)
        if checked.returncode:
            # Do not print captured provider/configuration details or credentials.
            raise ValueError("Frozen provider preflight failed; set the matching model and paired HTTPS credentials")
        command = command_for(archive, target, phase, concurrency)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Recheck after preflight, and keep an immutable attempt marker even if
        # the child is interrupted or its measurements later fail.
        verify_output(archive, target, phase)
        write_exclusive(sidecar(target, phase), {"schema": 1, "phase": phase, "output": str(target),
            "source_experiment": str(archive["experiment"]), "source_manifest_sha256": archive["manifest_sha256"],
            "sources": archive["manifest"]["sources"], "argv": command, "concurrency": concurrency,
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "transport": {"https_required": True, "redirects_allowed": False, "environment_proxies": False},
            "source_execution": "only verified text copied to isolated temporary package; no cached bytecode or live src"})
        completed = subprocess.run(command, cwd=staging, env=env, check=False)
        if completed.returncode:
            return completed.returncode
        if phase == "run":
            verify_complete_run(archive, target)
        elif read_json(target / "independent.json").get("status") != "completed":
            raise ValueError("Readout did not complete; preserve all partial evidence")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path(__file__).resolve().parents[1] / "experiments/continual-v02-main")
    parser.add_argument("--output", type=Path, help="A new user reproduction, never the source experiment")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Offline only; the default when no phase is supplied")
    mode.add_argument("--phase", choices=["run", "evaluate"], help="Explicitly authorize real API-backed execution")
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--manifest-sha256", help="Optional manifest pin obtained from a trusted release checksum")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.concurrency <= 128:
            raise ValueError("Concurrency must be 1..128")
        archive = verify_archive(args.experiment, args.manifest_sha256)
        if args.phase is None:
            if args.output is not None:
                candidate = protect_output(archive, args.output)
                verify_output(archive, candidate, "evaluate" if candidate.exists() else "run")
            print(json.dumps({"status": "checked", "network_requests": 0,
                "manifest_sha256": archive["manifest_sha256"], "verified_source_files": 10,
                "rounds": archive["manifest"]["rounds"], "seeds": archive["manifest"]["seeds"],
                "provider_configuration": "not instantiated in offline check; validated by frozen host for explicit phase"}))
            return 0
        if args.output is None:
            raise ValueError("Explicit phases require --output")
        return execute_phase(archive, args.output, args.phase, args.concurrency)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Reproduction rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
