# Experiment results and evidence boundaries

All figures below come from retained real model calls. Tasks in the core and component experiments are authored synthetic cases. Model identifier: `deepseek-flash`; no model weights were trained. Exact API/request/host conditions and all physical attempts are recorded in each manifest and call receipt.

## Two frozen protocols

v3 uses seed 17. v4 uses fresh seed 29 and a conventional host fix: one model-authored IR repair, with API failures and unobserved candidate effects separated. This host fix is not an automatically evolved P/M change. The protocols are distinct experiments, not repeated identical trials. Both arms receive the same rules within a protocol.

| Protocol | Joint final g0 → g4 | Joint namespace transfer g0 → g4 | Fixed-P final g0 → g4 | Fixed-P namespace transfer g0 → g4 |
|---|---|---|---|---|
| v3 | 38/70 → 58/70 (+28.6 pp) | 39/70 → 54/70 (+21.4 pp) | 33/70 → 55/70 (+31.4 pp) | 37/70 → 50/70 (+18.6 pp) |
| v4 | 39/70 → 65/70 (+37.1 pp) | 38/70 → 60/70 (+31.4 pp) | 33/70 → 67/70 (+48.6 pp) | 33/70 → 65/70 (+45.7 pp) |

The fixed-P arm is stronger at the v4 endpoint. Neither protocol establishes an isolated benefit from P evolution. The identical g0 program already varies across arms: 38 vs 33 in v3 and 39 vs 33 in v4. Different generated M candidates and stochastic model responses are material confounds. Extra policy calls, invalid proposals, repairs and actual execution counts are all reported, rather than claiming equal total compute.

## Every joint generation

| Protocol/version | Changed fields producing this version | Independent final | Namespace transfer |
|---|---|---|---|
| v3/g0 | baseline | 38/70 | 39/70 |
| v3/g1 | memory_score, memory_top_k, policy | 53/70 | 49/70 |
| v3/g2 | policy | 51/70 | 49/70 |
| v3/g3 | tool_score, policy | 53/70 | 52/70 |
| v3/g4 | memory_score, memory_top_k, policy | 58/70 | 54/70 |
| v4/g0 | baseline | 39/70 | 38/70 |
| v4/g1 | policy | 34/70 | 32/70 |
| v4/g2 | memory_score, memory_top_k, policy | 52/70 | 44/70 |
| v4/g3 | rag_score, rag_top_k | 54/70 | 48/70 |
| v4/g4 | retry, policy | 65/70 | 60/70 |

v4 g0 and g1 have identical task mechanisms; only P changes. P does not execute during final question answering, so their final 39→34 and transfer 38→32 differences show model variability, not a causal policy regression. Flat and negative observations remain in the table.

The v3 P0→P1→P2→P3 search chain actually executed; P4 was generated and sealed after the last search and remains prospective. In v4 a policy proposal was rejected in one round, so the prior policy was reused. Version numbers alone are not evidence of distinct or better policies. See each `policy-decision.json`, `policy-proposal.json`, `changes.diff` and `evidence-chain.json`.

## Mechanism execution, separate from model sampling

A post-readout diagnostic checks whether the actually selected evidence contains the required support and the actual tool/attempt sequence is correct. In v4 this rises from 40/70 to 67/70 on both held-out partitions. It verifies changed execution conditions and does not replace the end-to-end answer metric. Detailed per-generation counts are in `experiments/joint-v4/analysis.json`.

The [terminal recovery witnesses](docs/verification/terminal-recovery-witnesses.json) derive g3/g4 tool-event comparisons from those original reports, with source hashes. They show actual stop/retry decisions and subsequent tool results; they are post-readout inspection, not an extra experiment or evidence that the terminal P4 drove a fifth search.

## Component intervention on fresh seed 41

Five variants were frozen before 350 real calls on 70 new cases. All outcomes are retained.

| Variant | Success |
|---|---|
| baseline | 39/70 |
| memory_top_k_only | 44/70 |
| memory_score_only | 46/70 |
| tool_score_only | 34/70 |
| full_g4 | 56/70 |

Reading more memory is one source of gain; unchanged-k memory scoring also shows a descriptive gain in this readout. These single stochastic readouts do not identify an exact net causal contribution or prove synergy. Tool-only fixes all three routing errors, but eight regressed answers came from requests with exactly the same request hash as baseline. Their aggregate decline must not be called a harmful tool-algorithm effect. See [component attribution](docs/component-attribution.md) and its context-variance audit.

## External public-data check

SQuAD 1.1: a predeclared 24-question RAG/prompt adaptation using pinned official data and same-article distractors. v3 g0 and g4 both obtain EM 66.67%, F1 77.61, gold-paragraph recall 91.67%. Improvement is zero. v3 did not change its RAG/prompt program; this does not establish transfer to a new business system or native/full SQuAD performance. [Protocol](docs/external-evaluation.md), [actual result](experiments/external-squad-v2/result.json), [dataset license](THIRD_PARTY_NOTICES.md).

The first external attempt failed an incorrect question-count assertion before any model call; it remains as `external-squad-v1`. The second run corrected that data-integrity assertion and preserves the fixed selection.

## Research and community paths

- Actual public discovery: three papers/versions, second fetch adds zero duplicates.
- Actual Dream-RSI v2 HTML model review: 122,299 characters, 40,414 input and 2,696 output tokens. It is author-claim analysis; no source-code reproduction or experimental correctness claim.
- Actual authorized synthetic Trace → analysis → mechanism candidate: two model calls, 2,750 tokens. The candidate is not executed/adopted and contains a potentially equivalent scoring expression. Legal schema is not evidence of improvement.
- Human-decision context is explicit opt-in. No human choices were fabricated to claim learned judgment. Personal/global community benefit and long-horizon poisoning effectiveness remain unmeasured.

## Reproducibility and limits

Core manifests freeze source/data identities and all versions before one-time readout. v3/v4 exact host sources are retained under each run’s `frozen-source/`; subsequent conventional security fixes in the distributed client are separately documented. Historical source snapshots are audit evidence. Use the current maintained client for new experiments. `scripts/reproduce_frozen.py` is an explicit historical-host reproduction tool; model/API aliases and stochastic sampling preclude a promise of numerically identical results.

Core preflights v1/v2 were aborted for provider output truncation and are not mechanism effects. Full paper text and private stores are gitignored; public research examples are limited projections with original hashes. Participant data was not collected. No business money/hour estimates or official benchmark superiority are claimed.
