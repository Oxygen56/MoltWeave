# Evaluation protocol

Status: authored synthetic mechanism benchmark, version 2026-10-23. This document is a protocol and evidence boundary, not a claim that every experiment has completed. No official benchmark, real company data, business savings, or cross-system deployment result is represented by these tasks.

## 1. What is measured

The executor calls a real model with the context selected by its loaded mechanism program. The fixed host scores its sealed response, selected tool and actual tool-attempt sequence. Candidate generation and P updates must also be real model calls with original receipts.

There are three distinct claims:
1. Engineering: a legal program was loaded and executed.
2. Mechanism: an automatically proposed P/M program changed later decisions or evidence selection.
3. Benefit: independent outcomes support a gain relative to a matched control.

A changed program, changed module order or positive development score alone establishes neither generalization nor a causal P benefit.

Here M denotes bounded mechanism fields: memory/RAG/tool scoring expressions, retry logic, top-k and prompt. P is the executable module-exploration policy selecting future improvement targets. Numeric expression IR is a real executable program, but is not arbitrary Python-source rewriting, model-weight training or self-rewriting of the entire outer driver.

## 2. API and data

build_suite(split, seed=17, *, per_family=None) returns fresh task dictionaries. Supported splits are train/dev/guard/final/transfer. Default counts are respectively 21/21/14/14/14; the frozen independent readout uses per_family=10, hence 70 final and 70 transfer cases.

A task contains id, family, entity, user_id, query, memories, documents, tools and host-only expected. Records contain id/text/entity/age/trusted/scope/source_id. age=0 is newest. IDs and fact values are generated from separate hash purposes, not answer-bearing ID prefixes.

Tools have name/description/entity/kind/deprecated/available/outcomes. outcomes is an authored deterministic state sequence. Each actual invocation advances its attempt state and exposes only that attempt's receipt:
- ok: current text and supporting receipt evidence IDs;
- transient_error: no business evidence, retryable explicitly indicates whether another read attempt is permitted;
- permanent_error: no business evidence, unchanged retry is not justified.

ToolSession is a local reference simulator, not a network service. The main runtime implements the same current-receipt semantics. A synthetic timeout is a genuine simulator state transition, not an injected model score; it is not a measured production timeout.

expected contains answer, tool, evidence_ids and tool_attempts. expected.evidence_ids is the required minimum support set. Additional citations are permitted only when actually visible in selected memory/documents or a successful current/past receipt. Future receipts and failed receipts cannot support an answer.

The request never includes its generated fact answer. UNKNOWN is a common conditional fallback contract on all queries, not disclosure that a particular lookup will fail.

## 3. Families and attribution limits

| Family | Intended challenge |
|---|---|
| memory_temporal | Current vs older conflicting assignment, with entity distractors |
| memory_scope | Current user's assignment vs global default/other entities; foreign-user records test fixed host isolation |
| rag_authority | Authoritative current bulletin vs untrusted, superseded or other-entity text |
| tool_routing | Appropriate current/read/available endpoint vs deprecated, unavailable, write or other-entity endpoints |
| tool_recovery | Retryable read failure followed by success; permanent rejection must not be retried |
| composition | Combine current memory, authoritative policy and live receipt; some cases also require retry |
| clean | Straightforward live-tool path, protecting basic behavior |

Foreign-user private records MUST be filtered by the fixed host before ranking. Tenant isolation is not an evolvable preference, and improvements must not be described as learning authorization. Current-user vs global applicability is a retrieval/personalization choice within the admitted scope.

The runtime's fixed family-to-module association is diagnostic scaffolding, not proven causal credit assignment. In particular composition can fail because of memory, RAG, routing, retry or prompt behavior. Claiming cross-module causality requires actual interventions and re-execution, not just a family label or a Trace inspection.

clean currently checks the basic tool path. Memory/RAG regression is covered by their guard families; this does not establish arbitrary drift resilience or memory-write/forgetting evolution. Those are future protocol expansions, not results of this suite.

## 4. Split contract

train is optimization data; its sealed failures, outcomes and expected support may enter the proposer after execution. dev determines candidate selection. guard participates in candidate acceptance, so guard is also optimization data even when its individual labels are withheld from the proposer. Repeated use of either is not independent evaluation.

final is reporting-only, after every version and selection rule is frozen. transfer uses new entities, users, sources, fact values, prefix vocabulary and query phrasing. It shares mechanisms, schema, evidence-construction grammar and core task semantics with development. Therefore report it as synthetic surface/namespace transfer, not a new professional domain or a real unseen system.

Partitions do not reuse exact fact values, task/evidence IDs, users, entity IDs or sources. Some structural words, tool names and semantic templates intentionally recur. Namespace separation reduces direct memorization; it is not a claim of complete distributional independence.

The generator is public source. Blindness is enforced by the experiment's host-to-proposer message boundary: no final examples, answers, traces or diagnostic feedback may be sent to the optimizer. The proposer has no filesystem/browser tools that could read the generator or acceptance artifacts. Public source and a documented seed are not a cryptographic secrecy mechanism.

## 5. Frozen initial data recipe

Generator version: moltweave-synthetic-v1. Seed: 17. SHA-256 uses UTF-8 JSON with sorted keys, compact separators and ensure_ascii=False.

| Split | Per family | Tasks | Data SHA-256 |
|---|---:|---:|---|
| train | 3 | 21 | 0296f2e933a40d4933a144e92a7cf254c9846f33790c504cd257aaf1e1c92e0c |
| dev | 3 | 21 | 33df229b73cafba638ccd84f6a5bffa44cdc9149d588c9609a0d9bfd00628114 |
| guard | 2 | 14 | 9955ea822793af1840c48f69d465e9a23784081576cdf803b236b796ae4ebb5c |
| final | 10 | 70 | 4ba276f641a7ce80cda2ea5de6ec1d5394dc40d9af0013f6a55574e879acf023 |
| transfer | 10 | 70 | 82e088127dde55855b127afd66dc754256956f3dbe0a0c9c0fcc5481839a9f51 |

The host generated final/transfer only to hash them; the benchmark author did not execute model acceptance tasks or print their samples. Importing benchmarks does not generate or execute a suite.

Changing GENERATOR_VERSION, seed, size or generator logic changes the experiment contract. A package/brand rename that changes the generator version must recompute these values and the frozen hash tests before the next official run; old experiment receipts remain historical evidence.

## 6. Model/measurement failures

Freeze the actual model/returned identifier, provider host, temperature, thinking setting, token budget, request format and timeout/retry policy. A response cut off by an inadequate token cap or unavailable HTTP/protocol measurement must not silently become a module defect or positive learning signal.

Preserve each physical API attempt, including failed/truncated raw content, finish reason, usage and timing. A logical request with three attempts is not one physical call. Measurement-unavailable batches cannot promote candidates or train P from an invented failure. Normal valid model answers that are wrong remain genuine task failures.

Keep interface pre-experiments separate from official mechanism experiments. Increasing a token cap after identifying truncation is a new frozen execution contract, not a task mechanism improvement.

## 7. Evolution and independent readout

Freeze the full host implementation (generator, IR, runtime/grader, model adapter, evolution/promotion driver, governance and serialization), data hashes and execution parameters before evolution. Every transition must link parent/next program hashes, actual loaded program, proposal input/output, source/IR diff, branch decisions, candidate real runs and promotion/rejection reasons.

P adoption may initially be prospective: a legal automatically proposed policy is used in later generations. This permits testing its effect; it is not evidence that the new P is already better. Store the next generation's actual branch choices, not just choices recomputed on an old state.

Compare joint P/M evolution with fixed-P M evolution under the same task partitions, initial program, execution settings and mechanism-proposal opportunities. Report policy-generation calls and all costs as well. A single pair of runs is descriptive evidence, not a stable effect estimate; preplanned repeated development seeds/runs are needed for stronger attribution.

Before independent readout, require a completed frozen summary, expected generation count and an intact program/transition hash chain. Reject any version replaced after freezing. Evaluate all predeclared generations as a trajectory, not as candidates from which to choose the best final score. Do not resume optimization, select a publication version or tune prompts after viewing final/transfer. A later improvement experiment needs a fresh independent partition and must retain the previous result.

## 8. Reporting

Report exact numerator/denominator per family and split, all failures, measurement exclusions, actual P and M changes, rejected/sensitive proposals, original calls and total costs. Explain unknowns and negative transfer. Do not multiply these synthetic success rates into business hours or money.

Unit contract checks verify deterministic generation, disjoint namespaces, evidence reachability, stateful tool transitions and frozen data hashes. They do not substitute for model-backed execution, multi-generation P adoption or independent improvement.

