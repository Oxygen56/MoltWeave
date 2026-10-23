# Experiment results and evidence boundaries

All figures below come from retained real model calls. Tasks in the core and component experiments are authored synthetic cases. Model identifier: `deepseek-flash`; no model weights were trained. Exact API/request/host conditions and all physical attempts are recorded in each manifest and call receipt.

## v0.2 formal continuous experiment

The [v0.2 protocol](docs/v0.2-protocol.md) predeclares 20 rounds, seeds 101–110 and three arms, plus all 21 frozen-version readouts, terminal memory/context controls and independent future-search audits of P. The engine uses actual persistent factual writes and corrections, revisits entities, and tests cross-round/delayed recall. No private or business data is included.

The formal run and independent readout are complete: **600 committed transitions, 630 sealed states, 630 complete version reports, 50 P audits, 30 memory-disabled controls, 30 wide-context controls and ten shared audit inputs**. The retained [analysis](experiments/continual-v02-main/analysis.json) reports `completed_readout`, completeness true and no warnings. Complete observation coverage does not make an invalid search pair a valid effect measurement.

**Joint evolution does not beat fixed P at the predeclared terminal endpoint, and it underperforms the corresponding wide-context baseline by 14.23 percentage points. An independent benefit from evolving P is not established.**

| Arm | Independent g0 | Independent g20 | Namespace transfer g20 |
|---|---:|---:|---:|
| Fixed M/P, accumulating memory | 141/260 | 146/260 | 0/40 |
| Evolving M, fixed P | 142/260 | 191/260 | 29/40 |
| Joint M/P | 142/260 | 177/260 | 30/40 |

The main terminal joint-minus-fixed-P contrast is **−5.38 pp**, n=10 paired streams, descriptive 95% bootstrap interval **[−23.46, +10.77] pp**, exact two-sided sign-flip p=0.596. The joint g0→g20 increase is an observed version contrast, not proof that evolving P helped: fixed P is stronger at the endpoint. Namespace transfer is 30/40 versus 29/40 (+2.50 pp, interval [−27.50, +27.50] pp); it is secondary and shares the authored synthetic generation grammar, rather than testing a separate real-world system.

### Memory and context controls

| Joint-arm comparison | Actual successes | Enabled/current minus control |
|---|---|---:|
| Terminal M versus memory disabled | 177/260 versus 96/260 | +31.15 pp |
| Terminal M versus fixed wide-context baseline | 177/260 versus **214/260** | **−14.23 pp** |

The memory-disabled run turns both factual reads and writes off. It demonstrates a difference under that combined intervention, not the isolated contribution of an evolved write program. The wide-context control retains baseline mechanisms and sets memory/retrieval top-k to six. Its higher score is material evidence against attributing the result to superior evolved mechanisms; the corresponding joint-arm baseline sample must not be replaced with a more favorable arm's independently sampled baseline result. All these comparisons use one retained model sample per execution.

### Independent P audit: positive primary mean is entirely same-P

The predeclared P primary includes **all valid terminal P-versus-P0 search pairs**, including unchanged-P pairs. Five of ten are valid: streams 102/103/105/108/110. Their mean is **+30 pp**, descriptive 95% bootstrap interval **[0, +70] pp**, exact sign-flip p=**0.50**. This conditional result cannot be presented as a positive evolved-policy effect:

| Audit view | Streams | Result and interpretation |
|---|---|---|
| Valid, actually changed P; explanatory subset | 102, 103, 105 (n=3) | Each has 0/4 versus 0/4 future success; mean difference 0 pp |
| Valid, unchanged P; calibration subset | 108, 110 (n=2) | 0/4→2/4 and 0/4→4/4; mean +75 pp, supplying the entire positive primary difference |
| Invalid terminal search pairs | 101, 104, 106, 107, 109 (n=5) | Search effects unknown, not zero and not dropped from attempt accounting |
| All-attempt operational outcomes | All ten | +22.5 pp, interval [−7.5, +55] pp; a separate fallback-outcome measure, not P-evolution benefit |
| g0 same-P calibration | Six valid pairs | +4.17 pp; not subtracted from terminal results |

In all three valid changed-P pairs, the two searches also select the same descendant M, and both future runs score 0/4. This is a diagnostic clue about the sampled search outcomes, not a replacement primary endpoint or proof of general semantic equivalence. The unchanged-P positive differences expose variation in the search/candidate/write/answer pipeline. The distinct-P subset cannot replace the predeclared all-valid primary after seeing its result, and the operational fallback contrast cannot be relabeled a valid changed-P effect. Report invalidity and the exact conditional denominator alongside the mean. Across all checkpoints, 22 of 50 audit pairs are invalid; all 50 reports are present.

### Actual evolution and retained negative evidence

Joint adopted **33 M changes and seven P changes**; evolving M with fixed P adopted **29 M changes**. New versions actually loaded and altered subsequent decisions. The [M witnesses](docs/v0.2-mechanism-walkthrough.md) retain failures and explicitly label old-IR comparisons as deterministic post-hoc diagnostics, not additional model experiments or independent effects.

Online effective four-step memory loops were **60/200 joint, 76/200 fixed P and 54/200 fixed M/P**. These are optimization-time observations from the committed trajectory, not held-out endpoints. The report preserves **157 adjacent-generation score decreases** across acceptance/transfer; a lower sampled score, including under an unchanged program, does not identify a causal mechanism regression. No favorable intermediate version replaces g20.

The formal tree retains 64,321 logical requests and 64,930 physical attempts, with 148,342,048 provider-reported tokens. Usage is missing for 634 attempts and remains unknown, not free. Accounting recursively includes failed requests and archived partial-round work; shared independent P-audit costs are separate from joint-arm costs. Different actual request/token counts are not described as equal compute.

### Recovery and release history

The first formal execution stopped after **421/600** committed transitions; a separate post-stop check returned HTTP 402 `insufficient_balance_error`, while original experiment calls retain their original HTTPError records. At that point all ten fixed-M lanes were complete and evolving lanes had unsealed tails. Verified recovery reached **501/600** before another HTTP 402, then **594/600** before two contrastive mechanism-proposal JSON failures in policy meta-probes. The final recovery completed **600/600**, after which all frozen versions received the independent readout above.

Previously committed bytes remain unchanged. Every unsealed partial round was uniformly archived and replayed without selecting by score; original calls, aborts, partial measurements and their costs remain inspectable. This was **not an uninterrupted or exactly-once experiment**. The [first diagnostic](experiments/continual-v02-main/interruption-diagnosis.json), [second diagnostic](experiments/continual-v02-main/provider-diagnostics/second-interruption.json), [594-round parse inspection](docs/verification/v02-parse-interruption.json), [recovery procedure](docs/v0.2-resume.md) and [engineering preflights](docs/v0.2-preflights.md) preserve those boundaries. The preflights are not pooled into formal effects.

[Full formal report](experiments/continual-v02-main/RESULTS.md) · [Chinese interpretation](docs/v0.2-results.zh-CN.md) · [v0.2.0 result/release materials](https://github.com/Oxygen56/MoltWeave/releases/tag/v0.2.0) (planned release target; publication requires an actual receipt) · [Historical 501-round preview](https://github.com/Oxygen56/MoltWeave/releases/tag/v0.2.0-preview.1) (acceptance was incomplete at that snapshot; its original numbers and archive remain unchanged)

Statistics are descriptive paired-stream summaries: bootstrap intervals use 10,000 resamples; sign-flip inference assumes exchangeability. Ten namespaces with shared authored grammar are not ten independent business systems. Temperature zero and a stable requested model alias do not ensure identical outputs or immutable backend weights. No business-value, native benchmark superiority or production-security conclusion follows.

## Historical v0.1 protocols

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
