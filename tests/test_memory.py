import tempfile
import unittest
from pathlib import Path
from moltweave.memory import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_quarantine_correction_and_tenant_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.db")
            args = {"tenant": "t", "owner": "a", "entity": "project", "source": "authorized-source"}
            old = store.propose(text="old fact", **args)
            self.assertEqual(store.read(tenant="t", owner="a", query="project", score=1), [])
            store.review(old, tenant="t", owner="a", reviewer="owner", accept=True)
            new = store.propose(text="correct fact", supersedes=old, **args)
            store.review(new, tenant="t", owner="a", reviewer="owner", accept=True)
            active = store.read(tenant="t", owner="a", query="project", score=1)
            self.assertEqual([r["text"] for r in active], ["correct fact"])
            self.assertEqual(store.read(tenant="another", owner="a", query="project", score=1), [])
            self.assertEqual(store.revoke_source("authorized-source", tenant="t", owner="a", actor="owner"), 2)
            self.assertEqual(store.read(tenant="t", owner="a", query="project", score=1), [])


if __name__ == "__main__":
    unittest.main()
