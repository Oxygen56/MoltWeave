<div align="center">

![MoltWeave](docs/brand.svg)

**An agent that evolves its mechanisms—and leaves evidence for every change.**

[中文](README.zh-CN.md) · [Architecture](docs/v0.2-architecture.md) · [Iteration plan](ITERATION_PLAN.md) · [Evaluation](docs/v0.2-protocol.md)

[![Tests](https://github.com/Oxygen56/MoltWeave/actions/workflows/tests.yml/badge.svg)](https://github.com/Oxygen56/MoltWeave/actions/workflows/tests.yml)

</div>

MoltWeave explores continual mechanism-level recursive self-improvement. It learns from actual executions, external research, and optionally authorized usage traces to propose changes to memory, retrieval, tool routing, recovery, prompts, and the exploration policy that chooses future improvements.

Model weights and the outer permission, approval and evaluation boundaries stay fixed. The initial implementation executes a bounded expression IR rather than arbitrary generated Python.

## Follow the evidence

```text
observed failure → model-authored mechanism diff → actual loaded version
                → changed later decision → fresh execution → independent outcome
```

The project preserves rejected candidates and flat/regressing generations. A policy version number, more memories, or an owner approval is not an improvement result. P1 must run, collect new history, and support P2 before we call a run multi-generation recursion.

## v0.2: continual memory and prospective policy tests

The new engine repeatedly revisits entities, corrects remembered facts and recalls previous and delayed events. A separate factual writer proposes grounded memories; executable M controls writing and reading. Evolving P changes diagnosis, candidate prompts, selection and improvement operators. A P promotion must win an actual paired future search; every frozen checkpoint is audited again on independent future searches.

The formal contract is **20 rounds × 10 streams × three arms**: ordinary accumulating memory with fixed M/P, evolving M with fixed P, and joint M/P. Every one of the 21 versions is scheduled for an empty-memory independent readout. Terminal memory-disabled and wide-context controls separate durable recall and context width from mechanism improvement.

Implementation and the four-round engineering preflight are complete. The formal run reached 421 committed rounds before provider HTTP 402 (insufficient balance). Verified recovery retained those bytes and reached **501/600** committed rounds before a second balance rejection. Its independent results are **unavailable**, not zero. Original receipts and partial rounds are retained. See the [protocol](docs/v0.2-protocol.md), [architecture](docs/v0.2-architecture.md), [an actual execution walkthrough](docs/v0.2-walkthrough.md), and [current formal evidence](experiments/continual-v02-main/RESULTS.md).

## Historical v0.1 results

Two frozen four-round protocols retain every generation and a fixed-P control. In the latest joint run, held-out success increases **39/70 → 65/70**, and namespace transfer **38/70 → 60/70**. The fixed-P control reaches **67/70** and **65/70**, so **isolated P benefit is not established**. Intermediate flat/regressing generations are preserved.

The external 24-question SQuAD check shows **zero gain**. Component interventions separate increased context from ranking changes and expose same-request model variability. These are authored synthetic mechanism results and a small adapted external readout, with no business-value extrapolation.

[All results and limits](EXPERIMENTS.md) · [Latest evidence page](experiments/joint-v4/index.html) · [Per-generation evidence chain](experiments/joint-v4/evidence-chain.json)

## What runs today

- A real model agent with executable memory/RAG/tool ranking, retry logic, scoped context and model prompts.
- Model-authored mechanism proposals, actual candidate runs, protection comparisons, and prospective exploration-policy evolution.
- Immutable experiment folders containing program hashes, decisions, diffs, physical model-attempt receipts and one-time held-out readouts.
- Research discovery, evidence packs, contextual human-decision memory and separate measured-effect records.
- A self-hosted, opt-in complete-trace path with tenant authentication, quarantine, scoped derivatives and withdrawal.
- Exact-artifact owner approval tickets with signature, expiry, action/scope/dependency binding and replay denial.
- Durable memory quarantine/correction and an offline generation evidence explorer.

Research/community infrastructure tests do not establish downstream RSI benefits. The continual writer/read mechanism is implemented in v0.2; its formal independent benefit remains pending. Long-horizon poisoning evaluation, cross-model reproduction, official external benchmark runs and hosted production service remain roadmap items. See the [iteration plan](ITERATION_PLAN.md) for explicit status.

[Historical v0.1 publication verification](docs/verification/publication.json) records that release's hosted checks and 96-test installation check. [v0.2 verification](docs/verification/v02-publication.json) keeps current code checks separate from unfinished model acceptance.

## Quick start

Python 3.11+; no runtime dependencies.

```bash
git clone https://github.com/Oxygen56/MoltWeave.git
cd MoltWeave
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Offline tests require no key and do not generate model-effect claims. To run an actual experiment, configure a compatible API:

```bash
export MOLTWEAVE_API_BASE=https://api.deepseek.com
export MOLTWEAVE_MODEL=deepseek-flash
export MOLTWEAVE_API_KEY='your-key'
moltweave evolve --output experiments/my-run --generations 4
moltweave evaluate --experiment experiments/my-run
moltweave report --experiment experiments/my-run
```

Use a fresh output folder. Evolution refuses to overwrite existing evidence. Evaluation checks frozen source and version hashes and does not feed final results back into optimization. Review provider billing before an experiment; all physical attempts are retained. DeepSeek thinking mode is explicitly disabled for this initial protocol; model settings are part of the experiment, not an optimizer-controlled variable.

For the v0.2 protocol, use a fresh folder:

```bash
moltweave continual run --output experiments/my-continual-run --rounds 20 --streams 10 --concurrency 32
moltweave continual evaluate --output experiments/my-continual-run --concurrency 32
moltweave continual analyze --output experiments/my-continual-run
```

The run stage must finish all planned lanes before independent evaluation. Do not interpret development adoption as an independent improvement.

## Architecture

`P` selects future improvement branches. `M` holds adopted mechanisms and reusable experience. A common `H0` loads the current mechanisms and starts each case with fresh transient state. External papers and participant traces enter as untrusted evidence and hypotheses; they do not grant code-execution or release authority.

The authored benchmark exercises stale memory, personal scope, source authority, tool routing, transient/permanent failures, combined evidence and basic regression. Its namespace-transfer split changes users, facts, entities and query wording; it is **not** a separate real-world business-system benchmark.

## Research and trace participation

Research CLI: `python -m moltweave.research --help`. The community Python API, local HTTP server and consent examples are documented in [community and governance](docs/community-and-governance.md). Participation is optional; local use does not require uploading anything. Do not contribute company data or private traces to GitHub.

The daily GitHub workflow discovers papers, preserves version deduplication state, and prepares accessible-text evidence packs. Adding a repository `MOLTWEAVE_API_KEY` secret enables optional model-assisted reading; without it, no model calls occur. It never runs paper code or adopts mechanisms. Full PDF/figure/code inspection and experiment reproduction are separate, unfinished capabilities. Run `python scripts/daily_research.py --help` for local scheduling.

Sensitive proposals wait for owner approval before loading or execution. A learned preference cannot issue a ticket. Raw participant data never becomes public project data by default.

## Inspiration and comparison

The design is informed by [Dream-RSI](https://www.dream-rsi.com/), [Harness²](https://github.com/google-research/harness2), the [DuplexAgent-RSI paper](https://arxiv.org/abs/2610.11299v1), module-oriented self-improvement research, and evidence-driven evaluation. References inspire mechanisms; this repository does not claim to reproduce their native results or outperform them. DuplexAgent-RSI's public demo still says “Code coming soon” at this release; no core implementation was reused. See [source and presentation references](docs/open-source-references.md).

## Contribute

Read [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), and [Apache-2.0](LICENSE). Useful contributions include reproducible failures, new bounded mechanism interfaces, external benchmark adapters, leakage checks and independently run experiments.
