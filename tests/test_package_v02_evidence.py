"""Micro-fixture archive tests only; never inspect the real experiment tree."""
from contextlib import redirect_stdout
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts import package_v02_evidence as p


class EvidencePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / "experiments/continual-unit-fixture"
        (self.run / "model-calls").mkdir(parents=True)
        (self.run / "empty-directory").mkdir()
        (self.run / "model-calls/one.json").write_bytes(b'{"kind":"synthetic archive fixture","value":1}\n')
        (self.run / "binary.bin").write_bytes(bytes(range(256)) * 128)
        (self.root / "experiments/unrelated").mkdir()
        (self.root / "experiments/unrelated/omit.txt").write_text("unrelated")
        (self.root / "private").mkdir()
        (self.root / "private/do-not-package.txt").write_text("not selected")
        self.scanner = p.SecretScanner(environ={})

    def package(self, name="evidence.tar.gz", **kwargs):
        return p.package(self.root, "dist/" + name, scanner=self.scanner, **kwargs)

    def test_complete_archive_preserves_bytes_empty_directories_and_only_selected_roots(self):
        originals = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.run.rglob("*") if path.is_file()}
        result = self.package()
        archive = Path(result["archive"])
        self.assertEqual(result["file_count"], len(originals))
        self.assertFalse(result["source_files_deleted"])
        self.assertFalse(result["source_bytes_modified"])
        with tarfile.open(archive, "r:gz") as tar:
            names = set(tar.getnames())
            self.assertIn("experiments/continual-unit-fixture/empty-directory", names)
            for name, original in originals.items():
                self.assertEqual(tar.extractfile(name).read(), original)
                self.assertEqual((self.root / name).read_bytes(), original)
            self.assertFalse(any(name.startswith(("private/", "experiments/unrelated")) for name in names))
            embedded = tar.extractfile(p.MANIFEST_MEMBER).read()
        self.assertEqual(embedded, Path(result["manifest"]).read_bytes())
        self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
        verified = p.verify(archive, scanner=self.scanner)
        self.assertEqual(verified["status"], "verified")
        self.assertTrue(verified["external_manifest_checked"])
        self.assertFalse(verified["extracted"])

    def test_archive_is_deterministic_despite_input_mtime_and_mode_changes(self):
        first = self.package("first.tar.gz")
        file = self.run / "binary.bin"
        os.utime(file, (100000, 100000))
        file.chmod(0o600)
        second = self.package("second.tar.gz")
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(Path(first["manifest"]).read_bytes(), Path(second["manifest"]).read_bytes())
        with gzip.open(first["archive"], "rb") as uncompressed:
            self.assertTrue(uncompressed.read(1024))
        with Path(first["archive"]).open("rb") as raw:
            self.assertEqual(raw.read(8)[4:8], b"\0" * 4)

    def test_output_and_sidecar_collisions_never_overwrite(self):
        result = self.package()
        old = Path(result["archive"]).read_bytes()
        with self.assertRaises(p.EvidenceError):
            self.package()
        self.assertEqual(Path(result["archive"]).read_bytes(), old)
        sidecar = self.root / "dist/blocked.tar.gz.manifest.jsonl"
        sidecar.write_text("retain this existing file")
        with self.assertRaises(p.EvidenceError):
            self.package("blocked.tar.gz")
        self.assertEqual(sidecar.read_text(), "retain this existing file")
        self.assertFalse((self.root / "dist/blocked.tar.gz").exists())

    def test_explicit_selection_and_output_boundary(self):
        another = self.root / "experiments/continual-other"
        another.mkdir()
        (another / "content").write_text("second fixture")
        result = self.package(runs=[self.run.name])
        self.assertEqual(result["roots"], ["experiments/continual-unit-fixture"])
        for selected in ["../private", "continual-unit-fixture/../../private", "unrelated"]:
            with self.subTest(selected=selected), self.assertRaises(p.EvidenceError):
                self.package("selected.tar.gz", runs=[selected])
        with self.assertRaises(p.EvidenceError):
            p.package(self.root, self.root.parent / "outside.tar.gz", scanner=self.scanner)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_input_and_output_symlinks_are_rejected(self):
        link = self.run / "linked"
        for target in [self.run / "binary.bin", self.root / "private", self.root.parent]:
            link.symlink_to(target, target_is_directory=target.is_dir())
            with self.assertRaises(p.EvidenceError):
                self.package()
            link.unlink()
        (self.root / "experiments/continual-link").symlink_to(self.run, target_is_directory=True)
        with self.assertRaises(p.EvidenceError):
            self.package()
        (self.root / "experiments/continual-link").unlink()
        dist = self.root / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "link.tar.gz").symlink_to(dist / "uncreated.tar.gz")
        with self.assertRaises(p.EvidenceError):
            self.package("link.tar.gz")

    def test_exact_configuration_secret_detected_across_chunk_boundary_without_printing_value(self):
        secret = "unit-configured-credential-value-0123456789"
        source = self.run / "secret-fixture.txt"
        source.write_text("x" * 56 + secret)
        scanner = p.SecretScanner(environ={"UNIT_CONFIG": secret}, extra_env=["UNIT_CONFIG"])
        with patch.object(p, "CHUNK", 64), self.assertRaises(p.EvidenceError) as raised:
            p.package(self.root, "dist/blocked.tar.gz", scanner=scanner)
        self.assertNotIn(secret, str(raised.exception))
        self.assertFalse((self.root / "dist/blocked.tar.gz").exists())
        self.assertIn(secret, source.read_text())
        output = io.StringIO()
        with patch.dict(os.environ, {"UNIT_CONFIG": secret}, clear=True), redirect_stdout(output):
            code = p.main(["--repo-root", str(self.root), "--output", "dist/blocked.tar.gz", "--secret-env", "UNIT_CONFIG"])
        self.assertEqual(code, 2)
        self.assertNotIn(secret, output.getvalue())

    def test_provider_patterns_and_base64_configuration_secret_are_blocked(self):
        examples = [b"sk-" + b"A" * 40, b"AIza" + b"B" * 35,
                    b"Bearer " + b"C" * 30, b"-----BEGIN PRIVATE KEY-----"]
        for value in examples:
            with self.subTest(pattern=value[:8]), self.assertRaises(p.EvidenceError):
                self.scanner.inspect(value)
        secret = "unit-configured-credential-value-0123456789"
        scanner = p.SecretScanner(environ={"OPENAI_API_KEY": secret})
        with self.assertRaises(p.EvidenceError):
            scanner.inspect(p.base64.b64encode(secret.encode()))
        with self.assertRaises(p.EvidenceError):
            p.SecretScanner(environ={}, extra_env=["MISSING_EXPLICIT_KEY"])

    def test_source_change_during_archive_refuses_publication_and_keeps_source(self):
        original = p._HashReader.read
        mutated = False
        def mutate(reader, size=-1):
            nonlocal mutated
            data = original(reader, size)
            if not mutated:
                mutated = True
                (self.run / "late-arrival.json").write_text('{"new":"fixture"}')
            return data
        with patch.object(p._HashReader, "read", mutate), self.assertRaises(p.EvidenceError):
            self.package()
        self.assertFalse((self.root / "dist/evidence.tar.gz").exists())
        self.assertTrue((self.run / "late-arrival.json").exists())
        self.assertTrue((self.run / "binary.bin").exists())

    def test_new_continual_run_during_default_pack_refuses_incomplete_full_selection(self):
        original, changed = p._HashReader.read, False
        def mutate(reader, size=-1):
            nonlocal changed
            data = original(reader, size)
            if not changed:
                changed = True
                (self.root / "experiments/continual-new-arrival").mkdir()
            return data
        with patch.object(p._HashReader, "read", mutate), self.assertRaisesRegex(p.EvidenceError, "selection changed"):
            self.package()
        self.assertFalse((self.root / "dist/evidence.tar.gz").exists())

    def test_incomplete_publication_removes_only_its_own_outputs(self):
        original, calls = os.link, 0
        def failed_link(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic publication failure")
            original(source, target)
        with patch.object(p.os, "link", failed_link), self.assertRaises(p.EvidenceError):
            self.package()
        self.assertFalse((self.root / "dist/evidence.tar.gz").exists())
        self.assertFalse((self.root / "dist/evidence.tar.gz.manifest.jsonl").exists())
        self.assertTrue((self.run / "binary.bin").exists())

    def test_large_fixture_source_reads_are_bounded(self):
        (self.run / "larger-fixture.bin").write_bytes(b"\x00\x01\x02\x03" * (300 * 1024))
        original = p._HashReader.read
        sizes = []
        def inspect(reader, size=-1):
            sizes.append(size)
            self.assertGreater(size, 0)
            self.assertLessEqual(size, p.CHUNK)
            return original(reader, size)
        with patch.object(p._HashReader, "read", inspect):
            result = self.package()
        self.assertGreater(len(sizes), 1)
        self.assertEqual(p.verify(result["archive"], scanner=self.scanner)["file_count"], 3)

    def rewrite(self, original, name, mutate):
        """Rewrite only this tiny test archive, with a fresh external checksum."""
        target = self.root / "dist" / name
        with tarfile.open(original, "r:gz") as source, target.open("wb") as raw, \
             gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gzip_stream, \
             tarfile.open(fileobj=gzip_stream, mode="w|", format=tarfile.PAX_FORMAT) as output:
            for member in source:
                data = source.extractfile(member).read() if member.isfile() else None
                for changed, body in mutate(member, data):
                    output.addfile(changed, io.BytesIO(body) if body is not None else None)
        Path(str(target) + ".sha256").write_text(p.sha256_file(target) + "  " + target.name + "\n")
        return target

    def test_archive_checksum_and_external_manifest_corruption_are_detected(self):
        result = self.package()
        archive = Path(result["archive"])
        original = archive.read_bytes()
        archive.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        with self.assertRaisesRegex(p.EvidenceError, "archive SHA256 mismatch"):
            p.verify(archive, scanner=self.scanner)
        archive.write_bytes(original)
        Path(result["manifest"]).write_text("changed manifest")
        with self.assertRaisesRegex(p.EvidenceError, "External manifest"):
            p.verify(archive, scanner=self.scanner)

    def test_member_hash_traversal_link_duplicate_and_omission_are_detected(self):
        result = self.package()
        target_name = "experiments/continual-unit-fixture/binary.bin"
        for attack in ["hash", "traversal", "symlink", "duplicate", "omission"]:
            def mutate(member, body):
                if member.name != target_name:
                    return [(member, body)]
                if attack == "hash":
                    return [(member, b"!" * len(body))]
                if attack == "traversal":
                    member.name = "../escaped"
                if attack == "symlink":
                    member.type, member.linkname, member.size = tarfile.SYMTYPE, "/private", 0
                    body = None
                if attack == "duplicate":
                    return [(member, body), (member, body)]
                if attack == "omission":
                    return []
                return [(member, body)]
            malicious = self.rewrite(result["archive"], attack + ".tar.gz", mutate)
            with self.subTest(attack=attack), self.assertRaises(p.EvidenceError):
                p.verify(malicious, scanner=self.scanner)
        self.assertFalse((self.root.parent / "escaped").exists())

    def test_archive_verifies_independently_without_extraction_or_repo_argument(self):
        result = self.package()
        with tempfile.TemporaryDirectory() as download:
            destination = Path(download)
            for key in ["archive", "manifest", "checksum"]:
                path = Path(result[key])
                shutil.copyfile(path, destination / path.name)
            archive = destination / Path(result["archive"]).name
            output = io.StringIO()
            with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
                code = p.main(["--verify", str(archive)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "verified")
            self.assertFalse((destination / "experiments").exists())

    def test_check_only_does_not_create_archive_or_dist(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            code = p.main(["--repo-root", str(self.root), "--check"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "checked")
        self.assertFalse((self.root / "dist").exists())


if __name__ == "__main__":
    unittest.main()
