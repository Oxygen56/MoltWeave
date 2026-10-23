"""Discover and optionally read public papers; retain reviewable evidence only."""
import argparse
import json
from pathlib import Path
from moltweave.common import write_json
from moltweave.research import ResearchStore, discover, review

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--store", default="state/research")
parser.add_argument("--query", default='all:"recursive self-improvement" OR (all:agent AND all:evaluation)')
parser.add_argument("--discover-count", type=int, default=30)
parser.add_argument("--review-count", type=int, default=3)
parser.add_argument("--model", action="store_true", help="Explicitly send accessible public paper text to the configured model")
args = parser.parse_args()
store = ResearchStore(args.store)
result = discover(args.query, store, max_results=args.discover_count)
client = None
if args.model:
    from moltweave.llm import ModelClient
    client = ModelClient(Path(args.store) / "model-calls")
packets = []
for paper in store.papers(limit=args.review_count):
    packets.append(review(paper["paper_id"], store, client=client, full_text=True))
report = {"discovery": result, "packets": packets,
          "status": "awaiting_human_review", "mechanism_execution": "none",
          "code_inspection": "not_implemented", "experiment_reproduction": "not_performed",
          "decision_context_sent": False}
write_json(Path(args.store) / "daily-report.json", report)
print(json.dumps({"status": report["status"], "packets": len(packets), "model_assisted": bool(client)}, ensure_ascii=False))
