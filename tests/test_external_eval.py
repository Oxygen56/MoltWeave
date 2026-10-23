"""External adapter contracts; no model calls and no downloads."""
from copy import deepcopy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from moltweave.external_eval import (
    SOURCE_SHA256, SOURCE_SIZE, answer_metrics, build_probe, load_official_data,
    normalize_answer, token_f1,
)


def fixture():
    paragraphs = []
    for index in range(8):
        context = f"Record {index} contains token{index} and alternate{index}."
        answer = f"token{index}"
        paragraphs.append({"context": context, "qas": [{
            "id": f"question-{index}", "question": "Which token does the record contain?",
            "answers": [{"text": answer, "answer_start": context.index(answer)}],
        }]})
    return {"version": "1.1", "data": [{"title": "Fixture", "paragraphs": paragraphs}]}


class ExternalEvaluationTests(unittest.TestCase):
    def test_classic_v11_metric_conventions(self):
        self.assertEqual(normalize_answer(" The, CAT! "), "cat")
        self.assertEqual(answer_metrics("cat", ["the cat", "a feline"]),
                         {"exact_match": 1.0, "f1": 1.0})
        self.assertAlmostEqual(token_f1("red red blue", "red blue blue"), 2 / 3)
        self.assertEqual(token_f1("wrong", "right"), 0.0)
        # The v1.1 convention has zero F1 for zero token overlap, including empty.
        self.assertEqual(token_f1("the", "a"), 0.0)
        self.assertEqual(answer_metrics("the", ["a"])["exact_match"], 1.0)
        with self.assertRaises(ValueError):
            answer_metrics("answer", [])

    def test_hash_selection_and_pools_ignore_answer_choice(self):
        source = fixture()
        original = deepcopy(source)
        first = build_probe(source, count=4)
        self.assertEqual(first, build_probe(source, count=4))
        self.assertEqual(source, original)
        for paragraph in source["data"][0]["paragraphs"]:
            qa = paragraph["qas"][0]
            alternate = qa["answers"][0]["text"].replace("token", "alternate")
            qa["answers"] = [{"text": alternate,
                              "answer_start": paragraph["context"].index(alternate)}]
        changed = build_probe(source, count=4)
        self.assertEqual([x["id"] for x in first], [x["id"] for x in changed])
        self.assertEqual([x["documents"] for x in first], [x["documents"] for x in changed])
        for task in first:
            self.assertEqual(len(task["documents"]), 5)
            self.assertEqual(len({x["id"] for x in task["documents"]}), 5)
            self.assertIn(task["gold_paragraph_id"], {x["id"] for x in task["documents"]})
            self.assertTrue(all(x["scope"] == "global" and x["trusted"] == 1
                                and x["entity"] == "" for x in task["documents"]))
            self.assertTrue(all("answers" not in x and "gold_paragraph_id" not in x
                                for x in task["documents"]))

    def test_invalid_original_span_fails_without_selective_replacement(self):
        source = fixture()
        source["data"][0]["paragraphs"][0]["qas"][0]["answers"][0]["answer_start"] = 0
        with self.assertRaisesRegex(ValueError, "answer-span"):
            build_probe(source, count=8)

    def test_fixed_source_from_existing_cache_without_network(self):
        # Optional actual-source regression. A clean checkout skips this test;
        # it never downloads licensed data merely to run the offline suite.
        directory = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "moltweave" / "squad11"
        path = directory / f"dev-v1.1-{SOURCE_SHA256[:12]}.json"
        if not path.exists():
            self.skipTest("Pinned official source is not already cached")
        with patch("moltweave.external_eval.urllib.request.urlopen",
                   side_effect=AssertionError("Offline tests must not download")):
            dataset, metadata = load_official_data(directory)
        questions = [qa for article in dataset["data"] for paragraph in article["paragraphs"]
                     for qa in paragraph["qas"]]
        self.assertEqual(len(questions), 10570)
        self.assertEqual(len({qa["id"] for qa in questions}), 10570)
        self.assertEqual(metadata["bytes"], SOURCE_SIZE)
        self.assertEqual(metadata["sha256"], SOURCE_SHA256)
        # Exercise all selected annotations and actual 24-question pool building.
        self.assertEqual(len(build_probe(dataset)), 24)


if __name__ == "__main__":
    unittest.main()
