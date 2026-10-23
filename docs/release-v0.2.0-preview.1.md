# v0.2 evidence preview — 501/600 rounds, independent acceptance pending

This is a **prerelease evidence snapshot**, not a completed v0.2 acceptance result. The formal run stopped twice when the model provider returned HTTP 402 (insufficient balance). Stable v0.2.0 remains unreleased.

## Implemented and actually executed

- Durable factual extraction, grounded write decisions, source-lineage correction, memory-only recall, cross-round and delayed recall.
- P evolves diagnosis/proposal prompts, action scoring, operators and parent selection. Actual paired future searches gate promotion; fixed P runs the same shadow probes without adoption.
- Frozen three-arm protocol: 20 rounds × ten streams. Every generation, invalid/rejected candidate and physical request remains inspectable.
- Empty-memory independent version readouts, memory-disabled and wide-context controls, future-search P audits and same-P calibration are implemented. **They have not been run for this formal experiment.**

## Actual snapshot, including failures

| Arm | Committed rounds | M adoption events | P adoption events |
|---|---:|---:|---:|
| Fixed M/P with accumulating memory | 200/200 | 0 | 0 |
| Evolving M, fixed P | 147/200 | 24 | 0 |
| Joint M/P | 154/200 | 27 | 7 |

A three-descendant P chain actually loaded its new policies in subsequent searches. These are execution and meta-development observations, **not proof that evolving P beats fixed P**. Different hashes alone do not establish different semantics or improvement.

The original 421 committed rounds were preserved by verified recovery. Every unsealed partial round was uniformly archived and replayed, regardless of its observed scores. Recovery reached 501 committed rounds before another provider balance rejection. It is not an uninterrupted or exactly-once run. Both failures, discarded partial work and their costs remain retained. Independent effects remain unavailable, not zero.

Engineering preflights are separate: one four-round, three-arm pipeline and all its readouts finished, while earlier writer-schema and malformed-JSON failures remain archived. Those pilot numbers are not pooled into formal acceptance.

## Full original evidence

The `moltweave-v02-interrupted-501-evidence.tar.gz` asset contains all six `experiments/continual-*` directories: 30,825 ordinary files, including raw physical model receipts, completed and partial rounds, recovery history, frozen execution sources, reports and negative preflights. Expanded source files total 3,665,008,134 bytes. Original bytes are unchanged. The standalone JSONL inventory and SHA256 checksum are provided as separate assets.

Current configured credentials, their encoded forms and common provider-secret patterns were scanned before packaging. This is a credential-pattern check, not a general security certification. Only authored public synthetic data was used; no real participants or business data were collected.

Verify before extracting into a **fresh repository clone**:

```bash
python3 scripts/package_v02_evidence.py --verify moltweave-v02-interrupted-501-evidence.tar.gz
```

Extraction at the repository root restores the original relative paths. `scripts/reproduce_continual.py --check` and `scripts/resume_continual.py --check` are offline. Explicit execution modes require the original requested model/provider and real API credit. See the repository's protocol, recovery and reproduction documents.

## Verification and limits

Public commit `cad42b4deb2c16e539ab0e5efad12f14bdd48b04` passes hosted Python 3.11/3.12/3.13 CI. A separate fresh public clone passes 225 source checks; an isolated Python 3.13 wheel installation passes CLI checks. These are software/distribution checks, not model-effect measurements.

All core tasks are authored synthetic events with shared generation grammar and deterministic local tool simulators. The model is real and its weights stay fixed; no native external benchmark or production-business improvement is claimed. Research/community infrastructure has not supplied a measured downstream benefit in this experiment.

Next acceptance remains fixed: finish the remaining 99 rounds; seal all 630 states; read all versions once; complete 50 P audits, 30 memory-disabled controls, 30 wide-context controls and ten shared audit inputs; publish terminal endpoints, uncertainty, all failures and regressions without selecting a winning generation.
