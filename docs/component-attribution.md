# Frozen v3 component attribution

This reporting-only experiment separates increased memory context from executable memory/tool ranking changes. It does not propose or select candidates, and its outcomes must not return to optimization. Results, including zero gains and regressions, remain in `experiments/component-attribution-v1`.

## Declared comparison

All five variants derive from the frozen `joint-v3` g0 and g4 programs. They are fixed before the first model call:

| Variant | Changes relative to frozen g0 |
| --- | --- |
| baseline | None; ordinary lexical routing, memory k=2 |
| memory_top_k_only | Only memory_top_k=4, copied from g4; lexical memory scoring unchanged |
| memory_score_only | Only g4's executable memory_score; memory k remains 2 |
| tool_score_only | Only g4's executable tool_score |
| full_g4 | The exact frozen g4 program, including combined changes |

The full program also contains a policy P, but runtime task execution does not invoke P. This readout cannot establish P's advantage. The complete g4 program is not an additive sum of isolated effects; interactions and model variation may matter.

Data: `build_suite('final', seed=41, per_family=10)`, 70 new authored synthetic cases across seven families. The generator split name is `final`, but this is a separate component readout with new facts, not a reuse or extension of the original seed17 final result. It is not an official benchmark or real-business deployment.

Each of five variant blocks uses `evaluate_suite(..., workers=10)` and the same task order. The model is the frozen v3 model (`deepseek-flash`), temperature requested 0, task completion limit 2,048 tokens. All 350 logical calls are real. Every physical attempt, including parse/transport retries and token usage where returned, is retained. No model mocks or fixed answer responses contribute performance evidence.

## Source and version integrity

The original v3 source is archived under `experiments/joint-v3/frozen-source/moltweave`. Before execution, the runner verifies all seven archived files against the original v3 manifest, all intermediate program transitions and the terminal program hash. Current `benchmarks.py`, `runtime.py`, `llm.py` and `common.py` must still match the archived hashes exactly. The expression evaluator in current `program.py` must have an identical AST to the archived evaluator. Current program validation has stricter syntax/size bounds and expanded legal policy features, but the saved candidates are not rewritten. The optimizer `evolution.py` is not used by this runner.

The adapter creates a fresh output directory and records its own source hash, archived/live source hashes, data hash, task IDs, all five program hashes and exact changed fields before any model call. Frozen v3 core files are never edited by this experiment.

## Outputs and interpretation

- `manifest.json`: the advance contract and execution status.
- `programs/`: all five unchanged or mechanically transplanted programs.
- `calls/`: original model requests/responses and physical-attempt receipts.
- `reports/`: full per-case outcomes, selected context and execution decisions.
- `result.json`: overall/per-family success, paired improvements/regressions, answer/evidence/tool/attempt failures, average context size and total call/token usage.
- `context-variance-audit.json`: post-readout comparison of identical serialized model requests, with no additional model calls; identifies output variation where a mechanism did not change the model input.
- `failed.json`: retained incomplete measurement if any API/parse batch fails; no mechanism conclusion is produced from that batch.

`memory_top_k_only` asks whether simply seeing more lexical memory records is enough. `memory_score_only` asks whether the executable ranking change helps at the original k=2. `tool_score_only` tests the frozen tool-ranking transplant. `full_g4` measures the combined frozen mechanism on this new set. Comparisons use the same fixed cases, and differences are descriptive single-run estimates. Zero temperature does not guarantee deterministic model outputs. Fixed variant blocks may also experience provider-time effects; one readout does not establish a precise causal effect or a statistically reliable ranking.

No winner is selected after the readout. Original final/transfer results, this new component readout and the SQuAD public-material readout remain separate evidence. None of these results measures the causal benefit of evolving P.

## Reproduction

Use a fresh output directory and the source versions named in the manifest:

```sh
PYTHONPATH=src python3 -m moltweave.attribution \
  experiments/joint-v3 experiments/component-attribution-v1 \
  --seed 41 --per-family 10 --workers 10
```

Credentials come from the existing ModelClient environment and never enter the command, manifest or receipts.

## Recorded result

Completed with data hash `09c280299afe5e5449c205bd7cb8fdff3a236cddc7e7c6c71af57fca6932b122` and all five advance-frozen variants. No variants were selected or rerun based on results.

| Variant | Passed / 70 | Success | Difference from baseline | Paired improved / regressed |
| --- | ---: | ---: | ---: | ---: |
| baseline | 39 | 55.71% | 0 | 0 / 0 |
| memory_top_k_only | 44 | 62.86% | +5 cases | 7 / 2 |
| memory_score_only | 46 | 65.71% | +7 cases | 13 / 6 |
| tool_score_only | 34 | 48.57% | −5 cases | 3 / 8 |
| full_g4 | 56 | 80.00% | +17 cases | 19 / 2 |

Per-family results (each denominator is 10):

| Family | Baseline | More memory only | Memory score only | Tool score only | Full g4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| memory_temporal | 0 | 2 | 8 | 0 | 10 |
| memory_scope | 9 | 10 | 5 | 3 | 10 |
| rag_authority | 10 | 8 | 8 | 8 | 8 |
| tool_routing | 7 | 7 | 7 | 10 | 10 |
| tool_recovery | 3 | 3 | 3 | 3 | 3 |
| composition | 0 | 4 | 5 | 0 | 5 |
| clean | 10 | 10 | 10 | 10 | 10 |

Increasing lexical memory k from 2 to 4 produced +5 observed successes. Transplanting memory_score while retaining k=2 produced +7, with average selected memory count identical to baseline (1.429 records across all 70 cases; some families have no memory). Average serialized context length was 1,358 characters versus baseline 1,361; the observed score change does not require more memory records. The complete mechanism scored +17 but combines ranking, context size and interactions. These one-run contrasts do not establish stable effect sizes or additive contributions.

The tool-score transplant corrected all three host tool-selection errors: tool-routing successes rose from 7/10 to 10/10. Its aggregate score nevertheless fell by five. Post-readout receipt comparison found all eight regressions outside tool routing had exactly the same `request_hash` as baseline (six memory_scope and two rag_authority cases): the actual serialized request, model and request parameters were identical. These are observed output variation on unchanged inputs, so the aggregate −5 must not be described as a causal harm from the tool-ranking program. The original scores and receipts remain unchanged. No new calls were made to obtain a cleaner result.

The same diagnostic found two rag_authority regressions on identical baseline requests in each other variant as well. All five variants retained tool_recovery=3/10; v3's retry mechanism was unchanged. Both findings remain visible rather than being hidden by the combined total.

All 350 logical requests completed in 350 physical attempts, with `finish_reason=stop` throughout and no API/parse measurement errors. The returned model label was `deepseek-flash` for all 350. Provider-reported usage totaled 207,621 prompt tokens and 13,247 completion tokens (220,868 total). Full receipts are retained locally; the use of requested temperature zero did not remove output variation.

Supported claim: the frozen executable ranking mechanisms genuinely alter selection, and this fixed new synthetic readout observed improvements beyond the quantity-only variant, with explicit regressions and substantial model variation. Unsupported claims include a precise causal contribution for each component, stable superiority, P's advantage, real-business value or reproduction of an official benchmark.
