"""Public CLI. Offline tests never masquerade as model experiments."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .common import write_json, read_json


def main() -> None:
    parser = argparse.ArgumentParser(prog="moltweave")
    sub = parser.add_subparsers(dest="command", required=True)
    evolve = sub.add_parser("evolve", help="Run real model-authored multi-generation evolution")
    evolve.add_argument("--output", required=True)
    evolve.add_argument("--generations", type=int, default=4)
    evolve.add_argument("--workers", type=int, default=8)
    evolve.add_argument("--seed", type=int, default=17)
    evolve.add_argument("--freeze-p", action="store_true")
    accept = sub.add_parser("evaluate", help="Read out frozen final/transfer sets once")
    accept.add_argument("--experiment", required=True)
    accept.add_argument("--workers", type=int, default=8)
    report = sub.add_parser("report", help="Render an experiment's actual evidence")
    report.add_argument("--experiment", required=True)
    args = parser.parse_args()
    if args.command == "report":
        from .report import render_report
        print(render_report(Path(args.experiment)))
        return
    from .llm import ModelClient
    folder = Path(args.output if args.command == "evolve" else args.experiment)
    client = ModelClient(folder / "model-calls")
    if args.command == "evolve":
        from .evolution import run_evolution
        result = run_evolution(folder, client, generations=args.generations, seed=args.seed, workers=args.workers,
                               evolve_p=not args.freeze_p, evolve_m=True)
        print(json.dumps({"status": result["status"], "output": str(folder)}, ensure_ascii=False))
    else:
        from .evolution import independent_evaluation
        result = independent_evaluation(folder, client, workers=args.workers)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
