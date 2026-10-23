"""Run a new experiment using the exact archived host of an earlier experiment."""
import argparse
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request
import urllib.error
import hashlib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--experiment", required=True, help="Earlier run with frozen-source/")
parser.add_argument("--output", required=True, help="Fresh output folder; real API calls")
parser.add_argument("--workers", type=int, default=8)
parser.add_argument("--external-only", action="store_true", help="Reproduce the archived 24-question external adapter only")
args = parser.parse_args()
prior = Path(args.experiment).resolve()
source = prior / "frozen-source"
if not (source / "moltweave/evolution.py").is_file():
    raise SystemExit("No archived execution source in this experiment")
sys.path.insert(0, str(source))
from moltweave.llm import ModelClient
from moltweave.evolution import run_evolution, independent_evaluation

manifest = json.loads((prior / "manifest.json").read_text())
client = ModelClient(Path(args.output) / "model-calls", model=manifest["model"])
parsed = urllib.parse.urlsplit(client.base_url)
if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
    raise SystemExit("Historical reproduction requires a clean HTTPS model endpoint")

class DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError("Redirect blocked by maintained reproduction safety wrapper")

# Historical files remain exact audit evidence. The maintained wrapper adds a
# declared transport-only safety overlay, without changing grading/search logic.
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({}), DenyRedirect()))
output = Path(args.output)
if output.exists():
    raise SystemExit("Use a fresh output directory")
output.parent.mkdir(parents=True, exist_ok=True)
overlay = output.with_name(output.name + "-transport-safety-overlay.json")
with overlay.open("x") as stream:
    stream.write(json.dumps({
    "redirects": "denied", "environment_proxies": "disabled", "https_required": True,
    "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scope": "Historical scoring/search source with maintained transport overlay; a new declared reproduction contract, not bit-for-bit original transport."
    }, indent=2) + "\n")
if args.external_only:
    from moltweave.external_eval import run_external_pair
    print(json.dumps(run_external_pair(prior, output, last_generation="g4", client=client), indent=2))
    raise SystemExit(0)
run_evolution(args.output, client, generations=manifest["generations_requested"], seed=manifest["seed"],
              workers=args.workers, evolve_p=manifest["evolve_p"], evolve_m=manifest["evolve_m"])
print(json.dumps(independent_evaluation(args.output, client, args.workers), indent=2))
