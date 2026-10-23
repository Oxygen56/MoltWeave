# v0.2.0 — continual memory, completed experiments, no isolated P benefit

MoltWeave can change executable agent mechanisms M and the policy P that proposes later changes. This release completes the predeclared **20 rounds × 10 streams × 3 arms**: 600 committed transitions, all 630 frozen-version readouts, 50 independent P audits, 30 memory-disabled controls, 30 wide-context controls and 10 shared audit inputs. All tasks use authored public synthetic data and real model calls.

The result is mixed. Persistent memory supports actual correction and recall, but **evolving P did not establish an independent improvement over fixed P**. More adopted changes did not produce a better terminal agent.

| Terminal independent measurement | Result |
|---|---|
| Joint M/P, empty-memory acceptance | 177/260 (68.08%); initial joint M was 142/260 |
| Evolving M with fixed P | 191/260 (73.46%) |
| Predeclared joint − fixed-P endpoint | −5.38 pp; 95% stream bootstrap CI [−23.46, +10.77], n=10 |
| Namespace transfer | Joint 30/40; fixed-P 29/40; shared generation grammar, not a new business system |
| Joint M with memory disabled | 96/260; enabling reads and writes together gives +31.15 pp, not an isolated evolved-write-policy effect |
| Wider-context fixed baseline in the joint control run | 214/260, above joint by 14.23 pp |

**P audit interpretation matters.** Only 5/10 terminal search pairs were valid. The predeclared all-valid contrast is +30 pp, but all positive differences came from the two streams whose P was unchanged (same-P mean +75 pp). The three valid, actually changed-P pairs each scored 0/4 versus 0/4, a zero difference with a severe floor effect. Five invalid pairs have unknown search effects. All-attempt operational outcomes are +22.5 pp, including fallbacks; this is not a changed-P benefit. No favorable checkpoint or g0 subtraction replaces the primary endpoint.

The joint arm adopted 33 M changes and seven P changes; one stream produced P0→P1→P2→P3 and used descendants in later searches. These are actual execution changes, separately documented from benefit. Online effective memory loops were 60/200 joint, 76/200 fixed-P and 54/200 fixed-mechanism; these are optimization observations. All 157 adjacent independent score decreases remain visible, including comparisons where M did not change; these are score decreases, not 157 causally established mechanism regressions.

## What ships

- Separate real factual extraction, provenance-grounded executable memory writes/reads, source-lineage corrections and delayed recall.
- Model-proposed diagnosis, bounded mechanism programs, actual candidate execution, policy operators and paired future-search promotion.
- Every-generation differences, loaded identities, memory/source chains, independent results and an offline evidence explorer.
- Frozen-source reproduction, checkpoint/readout recovery, full raw evidence packaging, per-file inventories and checksums.
- Wheel and source distribution; source and CI checks remain distinct from model-effect results.

The original run stopped at 421 transitions for provider balance exhaustion. Recovery reached 501 before a second balance rejection, then 594 before two JSON-parsing measurement failures. A final recovery completed 600. Entire uncommitted rounds were uniformly archived and replayed regardless of score. All original receipts, failed repair attempts, recovery ledgers and costs are retained. This is a recovered experiment, not uninterrupted or exactly-once execution. The final independent readout completed without interruption.

The full evidence archive includes all six continual experiment directories, including negative engineering preflights. Verify its checksum and inventory with `scripts/package_v02_evidence.py --verify` before restoring paths in a fresh checkout. `SHA256SUMS` also covers the installable packages. The earlier [501-round preview](https://github.com/Oxygen56/MoltWeave/releases/tag/v0.2.0-preview.1) remains an immutable historical snapshot.

Formal receipts contain 64,321 logical requests and 64,930 physical attempts, with 148,342,048 provider-reported tokens. Another 634 attempts lack usage; their cost is unknown. These counts include failed and replayed formal work, with engineering preflights separately retained.

This is bounded mechanism evolution, not weight training or arbitrary generated Python execution. Research judgment improvement, real participant benefit, sustained poisoning resistance, native external benchmarks and cross-model reproduction remain unmeasured. The next iteration first diagnoses the stronger wide-context baseline, search validity, floor effects and same-P variability under a new protocol and fresh acceptance data.

[完整中文结论](https://github.com/Oxygen56/MoltWeave/blob/v0.2.0/docs/v0.2-results.zh-CN.md) · [All results](https://github.com/Oxygen56/MoltWeave/blob/v0.2.0/experiments/continual-v02-main/RESULTS.md) · [Protocol](https://github.com/Oxygen56/MoltWeave/blob/v0.2.0/docs/v0.2-protocol.md) · [Iteration plan](https://github.com/Oxygen56/MoltWeave/blob/v0.2.0/ITERATION_PLAN.md)
