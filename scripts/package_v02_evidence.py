#!/usr/bin/env python3
"""Stream complete continual-* evidence into a deterministic, verifiable archive.

This script never calls a model, publishes, extracts an archive, deletes source
evidence or changes raw bytes. Run only after all evidence writers have stopped.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile
from typing import Iterator
from urllib.parse import quote


CHUNK = 1024 * 1024
META_DIR = "__moltweave_evidence__"
MANIFEST_MEMBER = META_DIR + "/manifest.jsonl"
PACKAGE_MEMBER = META_DIR + "/package.json"
MAX_ENTRIES = 100_000
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_LINE = 32 * 1024
FORMAT = "moltweave-continual-evidence-v1"
ENV_SECRET_NAME = re.compile(r"(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|CLIENT_SECRET|PASSWORD|SECRET_KEY|PRIVATE_KEY|TOKEN)$", re.I)
SECRET_RULES = {
    "provider_sk_key": re.compile(rb"\bsk-(?:proj-|svcacct-|ant-)?[A-Za-z0-9_-]{20,}"),
    "google_api_key": re.compile(rb"\bAIza[A-Za-z0-9_-]{30,}"),
    "google_oauth_token": re.compile(rb"\bya29\.[A-Za-z0-9_-]{20,}"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "bearer_credential": re.compile(rb"\bBearer[ \t]{1,8}[A-Za-z0-9._~+/=-]{20,}", re.I),
    "credential_field": re.compile(rb'''["'](?:api[_-]?key|x-api-key|access_token|client_secret)["'][ \t]{0,32}:[ \t]{0,32}["'][A-Za-z0-9._~+/=-]{16,}''', re.I),
}


class EvidenceError(ValueError):
    """A safe-to-print failure message that never contains secret values."""


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def valid_path(name: str) -> bool:
    return (isinstance(name, str) and bool(name) and not re.search(r"[\x00-\x1f\x7f\\]", name)
            and not name.startswith("/") and all(part not in {"", ".", ".."} for part in name.split("/"))
            and PurePosixPath(name).as_posix() == name)


def run_name(name: str) -> bool:
    return valid_path(name) and "/" not in name and name.startswith("continual-") and len(name) > len("continual-")


class SecretScanner:
    """Bounded overlapping raw-byte scans; no document-controlled exceptions."""
    def __init__(self, environ=None, extra_env=()):
        environ = os.environ if environ is None else environ
        for name in extra_env:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name):
                raise EvidenceError("Invalid secret environment-variable name")
            if not environ.get(name):
                raise EvidenceError("An explicitly requested secret environment variable is missing or empty")
        names = sorted({name for name, value in environ.items() if value and ENV_SECRET_NAME.search(name)} | set(extra_env))
        variants = set()
        for name in names:
            value = environ[name]
            encoded = value.encode()
            if len(encoded) > 65_536:
                raise EvidenceError("A configured secret exceeds the scanner input bound")
            variants.update((encoded, json.dumps(value, ensure_ascii=True)[1:-1].encode(),
                             json.dumps(value, ensure_ascii=False)[1:-1].encode(),
                             base64.b64encode(encoded), base64.urlsafe_b64encode(encoded), quote(value, safe="").encode()))
        self.exact = tuple(sorted(variants, key=len, reverse=True))
        self.configured_secret_count = len(names)
        self.overlap = max([256, *(len(value) + 128 for value in self.exact)])

    def inspect(self, data: bytes) -> None:
        if any(value and value in data for value in self.exact):
            raise EvidenceError("Configured secret detected; no value or source excerpt was printed")
        for name, pattern in SECRET_RULES.items():
            if pattern.search(data):
                raise EvidenceError(f"Secret-like data detected by {name}; no value or source excerpt was printed")

    def state(self):
        return _ScanState(self)


class _ScanState:
    def __init__(self, scanner):
        self.scanner, self.tail = scanner, b""

    def feed(self, chunk: bytes) -> None:
        combined = self.tail + chunk
        self.scanner.inspect(combined)
        self.tail = combined[-self.scanner.overlap:]


def fingerprint(value: os.stat_result) -> tuple:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


@dataclass(frozen=True)
class Source:
    path: str
    kind: str
    size: int
    fingerprint: tuple


def repository(path: str | Path) -> Path:
    supplied = Path(path).expanduser()
    if supplied.is_symlink():
        raise EvidenceError("Repository root must not be a symlink")
    try:
        root = supplied.resolve(strict=True)
    except OSError as exc:
        raise EvidenceError("Repository root is unavailable") from exc
    if not root.is_dir():
        raise EvidenceError("Repository root must be a directory")
    return root


def selected_runs(root: Path, names=()) -> list[str]:
    experiments = root / "experiments"
    if experiments.is_symlink() or not experiments.is_dir():
        raise EvidenceError("experiments must be a real repository directory")
    selected = sorted(set(names) if names else (item.name for item in experiments.iterdir() if item.name.startswith("continual-")))
    if not selected:
        raise EvidenceError("No concrete experiments/continual-* directories were selected")
    for name in selected:
        if not run_name(name):
            raise EvidenceError("Only direct concrete continual-* directory names are allowed")
        candidate = experiments / name
        if candidate.is_symlink() or not candidate.is_dir():
            raise EvidenceError("Selected evidence root must be a real directory, never a symlink")
    return ["experiments/" + name for name in selected]


def inventory(root: Path, roots: list[str]) -> list[Source]:
    result = []
    def visit(relative: str):
        if not valid_path(relative):
            raise EvidenceError("Unsafe evidence member path")
        path = root / relative
        if not path.resolve(strict=True).is_relative_to(root):
            raise EvidenceError("Evidence path escaped the repository")
        value = path.lstat()
        if stat.S_ISLNK(value.st_mode):
            raise EvidenceError("Symlinks are forbidden anywhere in selected evidence")
        if stat.S_ISDIR(value.st_mode):
            result.append(Source(relative, "directory", 0, fingerprint(value)))
            with os.scandir(path) as items:
                children = sorted(item.name for item in items)
            for name in children:
                visit(relative + "/" + name)
        elif stat.S_ISREG(value.st_mode):
            result.append(Source(relative, "file", value.st_size, fingerprint(value)))
        else:
            raise EvidenceError("Only regular files and directories may be archived")
        if len(result) > MAX_ENTRIES:
            raise EvidenceError("Evidence exceeds the bounded manifest entry count")
    for relative in roots:
        visit(relative)
    return sorted(result, key=lambda source: source.path)


@contextmanager
def open_source(root: Path, source: Source) -> Iterator:
    path = root / source.path
    if not path.resolve(strict=True).is_relative_to(root):
        raise EvidenceError("Evidence path escaped the repository")
    # fstat must match the scan before any source bytes are read. O_NOFOLLOW
    # also rejects a final-component link swapped in after inventory.
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        if fingerprint(os.fstat(stream.fileno())) != source.fingerprint:
            raise EvidenceError("Source changed before reading; stop all writers and restart packaging")
        yield stream
        if fingerprint(os.fstat(stream.fileno())) != source.fingerprint:
            raise EvidenceError("Source changed during reading; no archive was published")


def assert_unchanged(root: Path, roots: list[str], expected: list[Source], *, all_runs=False) -> None:
    if all_runs and selected_runs(root) != roots:
        raise EvidenceError("Continual run selection changed; stop all writers and restart packaging")
    if inventory(root, roots) != expected:
        raise EvidenceError("Source tree changed; stop all writers and restart packaging")


def scan_to_manifest(root: Path, roots: list[str], manifest: Path, scanner: SecretScanner, *, all_runs=False) -> tuple[list[Source], dict]:
    sources = inventory(root, roots)
    count = total = 0
    with manifest.open("wb") as output:
        for source in sources:
            scanner.inspect(source.path.encode())
            row = {"path": source.path, "type": source.kind, "size": source.size}
            if source.kind == "file":
                digest = hashlib.sha256()
                state = scanner.state()
                size = 0
                with open_source(root, source) as stream:
                    while chunk := stream.read(CHUNK):
                        try:
                            state.feed(chunk)
                        except EvidenceError as exc:
                            # The relative path itself already passed the same
                            # scanner, so this identifies the file without
                            # exposing an excerpt or a path-embedded credential.
                            raise EvidenceError(str(exc) + "; source_path=" + source.path) from None
                        digest.update(chunk)
                        size += len(chunk)
                if size != source.size:
                    raise EvidenceError("Source size changed during secret scan")
                row["sha256"] = digest.hexdigest()
                count += 1
                total += size
            output.write(canonical(row))
    assert_unchanged(root, roots, sources, all_runs=all_runs)
    return sources, {"file_count": count, "entry_count": len(sources), "total_file_bytes": total}


def tar_info(name: str, size: int = 0, *, directory=False) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    info.mode = 0o755 if directory else 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    info.size = 0 if directory else size
    return info


class _HashReader:
    def __init__(self, stream):
        self.stream, self.digest, self.size = stream, hashlib.sha256(), 0

    def read(self, size=-1):
        chunk = self.stream.read(size)
        self.digest.update(chunk)
        self.size += len(chunk)
        return chunk


def output_path(root: Path, supplied: str | Path) -> Path:
    target = Path(supplied).expanduser()
    target = target if target.is_absolute() else root / target
    if target.is_symlink():
        raise EvidenceError("Output must not be a symlink")
    dist = root / "dist"
    if dist.is_symlink():
        raise EvidenceError("dist must not be a symlink")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(dist):
        raise EvidenceError("Output must be inside the repository's ignored dist directory")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz", target.name):
        raise EvidenceError("Output filename must be a simple .tar.gz filename")
    current = root
    for part in target.relative_to(root).parts[:-1]:
        current /= part
        if current.is_symlink():
            raise EvidenceError("Output ancestors must not be symlinks")
    resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return resolved


def package(repo_root: str | Path, output: str | Path, *, runs=(), scanner=None) -> dict:
    root, scanner = repository(repo_root), scanner or SecretScanner()
    runs = tuple(runs)
    roots = selected_runs(root, runs)
    all_runs = not runs
    target = output_path(root, output)
    destinations = [target, Path(str(target) + ".manifest.jsonl"), Path(str(target) + ".sha256")]
    if any(path.exists() or path.is_symlink() for path in destinations):
        raise EvidenceError("Output or checksum/manifest already exists; overwriting is forbidden")
    created = []
    with tempfile.TemporaryDirectory(prefix=".evidence-stage-", dir=target.parent) as temporary:
        stage = Path(temporary)
        manifest = stage / "manifest.jsonl"
        sources, counts = scan_to_manifest(root, roots, manifest, scanner, all_runs=all_runs)
        manifest_sha = sha256_file(manifest)
        metadata = {"format": FORMAT, "roots": roots, **counts, "manifest_sha256": manifest_sha,
                    "selection_mode": "all_continual_directories" if all_runs else "explicit_runs",
                    "tar_metadata": {"mtime": 0, "uid": 0, "gid": 0, "file_mode": "0644", "directory_mode": "0755"},
                    "gzip_mtime": 0, "excluded_source_paths": [],
                    "secret_scanner": {"version": 1, "rules": sorted(SECRET_RULES), "document_controlled_exemptions": False}}
        metadata_path = stage / "package.json"
        metadata_path.write_bytes(canonical(metadata))
        archive = stage / "archive.tar.gz"
        with archive.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                tar.addfile(tar_info(META_DIR, directory=True))
                for name, path in [(PACKAGE_MEMBER, metadata_path), (MANIFEST_MEMBER, manifest)]:
                    with path.open("rb") as stream:
                        tar.addfile(tar_info(name, path.stat().st_size), stream)
                with manifest.open("rb") as rows:
                    for source, line in zip(sources, rows):
                        expected = json.loads(line)
                        if source.kind == "directory":
                            tar.addfile(tar_info(source.path, directory=True))
                        else:
                            with open_source(root, source) as stream:
                                reader = _HashReader(stream)
                                tar.addfile(tar_info(source.path, source.size), reader)
                                if reader.size != source.size or reader.digest.hexdigest() != expected["sha256"]:
                                    raise EvidenceError("Source bytes changed between scan and archive; no archive was published")
        assert_unchanged(root, roots, sources, all_runs=all_runs)
        archive_sha = sha256_file(archive)
        checksum = stage / "archive.sha256"
        checksum.write_text(archive_sha + "  " + target.name + "\n", encoding="ascii")
        # Same-filesystem links provide no-overwrite publication. A collision or
        # failure removes only files created by this invocation, never originals.
        try:
            for staged, final in zip([archive, manifest, checksum], destinations):
                os.link(staged, final)
                created.append(final)
        except BaseException as exc:
            for path in reversed(created):
                path.unlink()
            if not isinstance(exc, OSError):
                raise
            raise EvidenceError("Could not publish complete archive sidecars without overwriting") from exc
    return {"status": "packaged", "archive": str(target), "archive_sha256": archive_sha,
            "manifest": str(destinations[1]), "checksum": str(destinations[2]), "roots": roots, **counts,
            "configured_exact_secret_count": scanner.configured_secret_count,
            "source_files_deleted": False, "source_bytes_modified": False}


def _bounded_member(tar, member, maximum) -> bytes:
    if not member.isfile() or member.size > maximum:
        raise EvidenceError("Archive metadata exceeds its bounded regular-file contract")
    with tar.extractfile(member) as stream:
        data = stream.read(maximum + 1)
    if len(data) != member.size:
        raise EvidenceError("Archive metadata size mismatch")
    return data


def _normalized_member(member) -> None:
    if (not valid_path(member.name) or member.type not in {tarfile.REGTYPE, tarfile.DIRTYPE}
            or member.linkname or member.uid != 0 or member.gid != 0 or member.uname or member.gname
            or member.mtime != 0 or member.mode != (0o755 if member.isdir() else 0o644)
            or set(member.pax_headers) - {"path", "size"} or getattr(member, "sparse", None) is not None):
        raise EvidenceError("Unsafe path, link, special file or non-normalized tar metadata")


def verify(archive: str | Path, *, sha256_path=None, manifest_path=None, scanner=None) -> dict:
    archive = Path(archive).expanduser()
    if archive.is_symlink() or not archive.is_file():
        raise EvidenceError("Archive must be a regular file, never a symlink")
    checksum = Path(sha256_path) if sha256_path else Path(str(archive) + ".sha256")
    if checksum.is_symlink() or not checksum.is_file() or checksum.stat().st_size > 4096:
        raise EvidenceError("A bounded independent archive .sha256 sidecar is required")
    line = checksum.read_text(encoding="ascii").strip()
    match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz)", line)
    if not match or match[2] != archive.name:
        raise EvidenceError("Checksum sidecar must identify this exact archive filename")
    archive_sha = sha256_file(archive)
    if archive_sha != match[1]:
        raise EvidenceError("Independent archive SHA256 mismatch")
    scanner = scanner or SecretScanner()
    seen, expected, metadata = set(), None, None
    manifest_sha = None
    files = total = 0
    with tarfile.open(archive, mode="r|gz") as tar:
        for index, member in enumerate(tar):
            _normalized_member(member)
            if member.name in seen:
                raise EvidenceError("Duplicate archive member")
            seen.add(member.name)
            if index == 0:
                if member.name != META_DIR or not member.isdir():
                    raise EvidenceError("Missing evidence metadata directory")
                continue
            if index == 1:
                if member.name != PACKAGE_MEMBER:
                    raise EvidenceError("Missing evidence package contract")
                data = _bounded_member(tar, member, CHUNK)
                scanner.inspect(data)
                metadata = json.loads(data)
                roots = metadata.get("roots")
                if (metadata.get("format") != FORMAT or not isinstance(roots, list) or not roots
                        or len(set(roots)) != len(roots) or any(not isinstance(x, str) or not x.startswith("experiments/")
                            or not run_name(x[len("experiments/"):]) for x in roots)):
                    raise EvidenceError("Invalid selected-run contract")
                continue
            if index == 2:
                if member.name != MANIFEST_MEMBER:
                    raise EvidenceError("Missing embedded JSONL manifest")
                data = _bounded_member(tar, member, MAX_MANIFEST_BYTES)
                scanner.inspect(data)
                manifest_sha = hashlib.sha256(data).hexdigest()
                if manifest_sha != metadata.get("manifest_sha256"):
                    raise EvidenceError("Embedded manifest SHA256 mismatch")
                expected = {}
                for line in data.splitlines():
                    if not line or len(line) > MAX_MANIFEST_LINE:
                        raise EvidenceError("Invalid manifest row length")
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise EvidenceError("Manifest entries must be JSON objects")
                    name, kind, size = row.get("path"), row.get("type"), row.get("size")
                    if (not valid_path(name) or not any(name == root or name.startswith(root + "/") for root in metadata["roots"])
                            or name in expected or type(size) is not int or size < 0
                            or kind not in {"file", "directory"}):
                        raise EvidenceError("Manifest path/type/size violates selected evidence scope")
                    keys = {"path", "type", "size", "sha256"} if kind == "file" else {"path", "type", "size"}
                    if (set(row) != keys or (kind == "directory" and size != 0)
                            or (kind == "file" and (not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"])))):
                        raise EvidenceError("Malformed file hash or directory manifest row")
                    expected[name] = row
                    if len(expected) > MAX_ENTRIES:
                        raise EvidenceError("Manifest exceeds the entry-count bound")
                for name in expected:
                    parent = str(PurePosixPath(name).parent)
                    if parent != "experiments" and (parent not in expected or expected[parent]["type"] != "directory"):
                        raise EvidenceError("Manifest has a missing or non-directory parent")
                if any(root not in expected or expected[root]["type"] != "directory" for root in metadata["roots"]):
                    raise EvidenceError("Manifest omitted a selected run directory")
                continue
            if expected is None or member.name not in expected:
                raise EvidenceError("Archive contains an undeclared member")
            row = expected[member.name]
            scanner.inspect(member.name.encode())
            if member.isdir():
                if row["type"] != "directory" or member.size != 0:
                    raise EvidenceError("Directory entry disagrees with the manifest")
            else:
                if row["type"] != "file" or member.size != row["size"]:
                    raise EvidenceError("File size/type disagrees with the manifest")
                digest, state, count = hashlib.sha256(), scanner.state(), 0
                with tar.extractfile(member) as stream:
                    while chunk := stream.read(CHUNK):
                        digest.update(chunk)
                        state.feed(chunk)
                        count += len(chunk)
                if count != row["size"] or digest.hexdigest() != row["sha256"]:
                    raise EvidenceError("Archived file SHA256 mismatch")
                files += 1
                total += count
    if expected is None or seen - {META_DIR, PACKAGE_MEMBER, MANIFEST_MEMBER} != set(expected):
        raise EvidenceError("Archive is incomplete")
    if (files != metadata.get("file_count") or total != metadata.get("total_file_bytes")
            or len(expected) != metadata.get("entry_count")):
        raise EvidenceError("Archive count contract mismatch")
    external = Path(manifest_path) if manifest_path else Path(str(archive) + ".manifest.jsonl")
    checked_external = external.exists() or external.is_symlink()
    if manifest_path and not checked_external:
        raise EvidenceError("Explicit external manifest is missing")
    if checked_external and (external.is_symlink() or not external.is_file() or sha256_file(external) != manifest_sha):
        raise EvidenceError("External manifest does not match the embedded manifest")
    return {"status": "verified", "archive": str(archive), "archive_sha256": archive_sha,
            "file_count": files, "entry_count": len(expected), "total_file_bytes": total,
            "external_manifest_checked": checked_external, "roots": metadata["roots"],
            "extracted": False, "configured_exact_secret_count": scanner.configured_secret_count}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", metavar="ARCHIVE", help="verify independent SHA256, manifest, every member and secret patterns; never extract")
    mode.add_argument("--check", action="store_true", help="scan inputs only, without publishing an archive")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path, help="required for packaging; relative paths are relative to repo-root, inside dist/")
    parser.add_argument("--run", action="append", default=[], help="optional direct continual-* directory name; repeat to select explicit runs")
    parser.add_argument("--secret-env", action="append", default=[], help="additional environment variable containing an exact secret to block; never pass its value")
    parser.add_argument("--sha256-file", type=Path, help="optional independent checksum path for --verify")
    parser.add_argument("--manifest", type=Path, help="optional external JSONL manifest path for --verify")
    args = parser.parse_args(argv)
    try:
        scanner = SecretScanner(extra_env=args.secret_env)
        if args.verify:
            if args.repo_root or args.output or args.run:
                raise EvidenceError("--verify does not accept packaging inputs")
            result = verify(args.verify, sha256_path=args.sha256_file, manifest_path=args.manifest, scanner=scanner)
        else:
            if not args.repo_root or (not args.check and not args.output) or args.sha256_file or args.manifest:
                raise EvidenceError("Packaging requires --repo-root and --output; --check requires --repo-root")
            if args.check:
                root = repository(args.repo_root)
                roots = selected_runs(root, args.run)
                with tempfile.TemporaryDirectory(prefix="moltweave-evidence-check-") as temp:
                    _, counts = scan_to_manifest(root, roots, Path(temp) / "manifest.jsonl", scanner, all_runs=not args.run)
                result = {"status": "checked", "roots": roots, **counts,
                          "configured_exact_secret_count": scanner.configured_secret_count, "archive_created": False}
            else:
                result = package(args.repo_root, args.output, runs=args.run, scanner=scanner)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        # Third-party parser/OS messages can contain file bytes or path secrets.
        # Only controlled EvidenceError messages are exposed; no traceback/value.
        message = str(exc) if isinstance(exc, EvidenceError) else "Evidence operation failed; no source bytes or exception details were printed"
        print(json.dumps({"status": "refused", "error_type": type(exc).__name__, "message": message}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
