# Iteration plan and completion evidence

This plan keeps the complete project in scope. A completed implementation item is distinct from a measured effect. Dates and performance targets are not invented.

| Iteration | Deliverable | Acceptance evidence | Current evidence status |
|---|---|---|---|
| 1 · Fixed execution contract | H0, executable IR, real model client, traces, fixed scorer and partition manifest | Fresh real calls; scoped context; exact program identities; rejected unsafe programs | Implemented; real runs and offline contracts verified |
| 2 · Multi-generation mechanism evolution | Model proposals, actual candidate executions, protection gate, P0→P1→P2 and beyond | Each transition connects failure→diff→load→new decision→fresh outcome; failed generations retained | Historical v3/v4 complete. v0.2 completes 20 rounds × ten streams × three arms; joint adopts 33 M and seven P changes, fixed-P adopts 29 M changes. Adoption proves recorded changes, not benefit |
| 3 · Attribution and independent effects | Frozen baseline/P controls, unseen cases, separate transfer readout and uncertainty | Comparable model/tools/feedback/opportunities; final results never select versions; P benefit kept distinct from M benefit | v0.2 independent readout complete: terminal joint 177/260 versus fixed-P 191/260; paired difference −5.38 pp, 95% CI [−23.46, 10.77]. Isolated P benefit unproven. Historical external SQuAD remains flat |
| 4 · Memory lifecycle and joint mechanisms | Durable factual memory writes, correction, quarantine, read/write programs, compatibility | Correct harmful experience and its production mechanism; retain useful old knowledge; compare joint vs isolated changes | Implemented and actually executed. Terminal joint with memory 177/260 versus reads/writes disabled 96/260; +31.15 pp measures their combined availability. Evolved-write benefit is not isolated; corresponding wider-context fixed baseline reaches 214/260 |
| 5 · External research learns to judge | Daily-capable discovery, versioned deep-read evidence, context/reason/effect records; evolvable research policy | Real accessible sources; human decisions recorded as such; chronological/family holdouts and downstream candidate effects | Discovery/deep-read/opt-in decision context implemented; real Dream-RSI full-text model call; judgment/P improvement unmeasured |
| 6 · Optional community evolution | Complete scoped traces, opt-in transport, private evolution and authorized generic proposals | Local-only usable; end-to-end consent/upload/revoke; tenant isolation; held-out user benefit and negative transfer | Transport/governance/trace-to-candidate implemented; two real synthetic-feedback model calls; personal/global benefit unmeasured |
| 7 · Long-horizon defenses | Injection, Sybil/duplicate sources, low-dose poisoning, invalidation and recovery | Multiple rounds; measured attack/benign outcomes; exact approval and replay denial; withdrawal derivative cleanup | Structural attacks and revocation tested; sustained model poisoning and Sybil effectiveness unmeasured |
| 8 · Open-source distribution | Installable package, bilingual README, architecture, examples, reproducible runs, evidence explorer, CI, license/security/contribution policy | Clean public export, fresh clone installation/run, actual public repository receipt | Stable [v0.2.0](https://github.com/Oxygen56/MoltWeave/releases/tag/v0.2.0) published at commit d874e95 with six verified assets. Exact-target hosted CI, fresh public-clone 229 tests, isolated installed CLI and full evidence verification pass; see the [publication receipt](docs/verification/v02-stable-publication.json). Historical v0.1 and preview receipts stay separate |
| 9 · External and ecosystem validation | Official benchmark adapters; other model/provider; plugin interface | Actual source/version/license checked, native run receipts and unmodified metrics; independent reproduction | Planned |

## Core experiment procedure

The authorized v0.2 implementation and formal continuous experiment follow the [pre-readout protocol](docs/v0.2-protocol.md). Implementation, the four-round engineering preflight and the formal readout are complete. Verified recovery after two provider-balance interruptions retained prior committed bytes, failed calls and unsealed partial work. All 600 transitions and 630 version readouts, 50 independent P audits, 30 no-memory controls, 30 wider-context controls and ten common audit inputs are now observed. This is a recovered continuous experiment, not an uninterrupted or exactly-once run. See the [Chinese results and next decisions](docs/v0.2-results.zh-CN.md), [full analysis](experiments/continual-v02-main/analysis.json) and [retained report](experiments/continual-v02-main/RESULTS.md).

The independent primary comparison is negative: joint g20 is 177/260 versus fixed-P 191/260. Joint improves from its observed g0 142/260, but that before/after change does not establish an advantage over fixed P or the corresponding wider-context baseline (214/260). The terminal P audit has five valid pairs out of ten attempts and an all-valid contrast of +30 pp. Its three valid, actually distinct-P pairs select the same descendant M on both sides and all have 0/4 versus 0/4 future success; the other two valid pairs use identical P and contribute +75 pp. The five invalid attempts retain unknown search effects. These findings do not establish evolved-P benefit.

Freeze the dataset generator, all split hashes, scoring implementation and baseline before optimization. Use disjoint factual namespaces, users, entities and source IDs for optimization, development, protection, final and transfer. The current partitions vary prefixes/wording but share task families and generation grammar; namespace transfer is not held-out template-family or real-system transfer. Optimization-task labels are exposed only after each output is sealed; final and transfer examples are never sent to the proposer. Model weights are not trained in this experiment.

Run several bounded generations with the same model and tool permissions. Preserve candidate rejection and execution failures. Compare the evolving P/M run with a frozen-P run under the same opportunity budget. Report mechanism and policy behavior changes separately. Evaluate all frozen generations once on final and transfer; do not choose a winner using that readout or silently restart optimization after observing it.

If the result is flat or regresses, publish the result and diagnose with development data in a new experiment contract. Do not alter an existing result, handwrite the desired candidate, or rebrand a unit test as model improvement.

## Required public evidence

- Architecture and fixed/evolvable boundary.
- General mechanism diffs and model proposal receipts.
- Loaded hashes and actual branch/ranking/retry decisions.
- Per-generation numerators, denominators, failures and held-out results.
- Separate status for implemented infrastructure, structural tests, actual model effects, external reproduction and hosted deployment.
- Fair control costs and all candidate opportunities, not only the accepted branch.

## Human approval

Ordinary bounded benchmark expression proposals are within the authorized experiment scope. New permission/data-sharing/trust boundaries, sensitive capabilities, and shared releases require the owner's exact-artifact approval before execution. Learning owner preferences cannot mint approval. Project publication does not authorize collecting anyone's traces or running a hosted upload service.

## v0.2 delivery checklist

| Item | Implementation / actual evidence | Remaining acceptance |
|---|---|---|
| Durable memory loop | Separate actual writer; fixed provenance gate; M write/read programs; correction and recall. Independent joint read/write availability contrast +31.15 pp | Contribution of evolved writing versus reading is unisolated; joint does not beat the stronger wider-context control |
| Evolvable improvement policy | Actual P prompts/scorer/operators/parent choices and seven joint P adoptions; all 50 independent audits retained | Terminal valid pairs only 5/10; three distinct-P valid pairs show zero difference at a 0/4 floor. Independent P benefit remains unproven |
| Continuous experiment | All 600 transitions and 630 frozen states complete; all original interruptions, unsealed attempts and recovery ledgers retained | Completed protocol; no more optimization or selected restart under this final set |
| Independent measurements | 630/630 version readouts, 50/50 P audits, 30/30 no-memory, 30/30 wider-context, 10/10 common inputs; terminal endpoint and every generation retained | Completed readout. New hypotheses require a new protocol and new final set, not a favorable checkpoint selected here |
| Evidence and distribution | Physical receipts, hashes, actual changes, offline explorer, recovery and complete-pack tools; public source/preview and 229-test engineering checks | Exact stable artifact hashes, full archive inventory and final fresh-clone checks are recorded in the [separate publication receipt](https://github.com/Oxygen56/MoltWeave/blob/main/docs/verification/v02-stable-publication.json); distribution success never establishes model benefit |
| Interruption recovery | Verified checkpoints reused; unsealed work archived independently of score; both evolution and readout finish | Historical failure/partial evidence stays public; no uninterrupted-run or exactly-once claim |

Implementation, actual mechanism changes, independent effects, external validation and publication are separate statuses. The completed formal readout resolves the earlier unavailable measurement; it does not turn a negative comparison or an invalid search effect into a positive result. CI and tests validate engineering contracts, not model benefit.

## Next experimental cycle: diagnose before expanding

Preserve v0.2 as a completed result. Its final set cannot select the next mechanism, tune a proposal, retrain a model or promote another P. The observed failures motivate hypotheses only. Test changes on new development/protection data, predeclare a new protocol and freeze a new independent final set before the next optimization/readout cycle.

1. **Resolve the stronger wider-context baseline first.** On new development cases, separate evidence visibility, top-k allocation, ranking and source-of-truth use with comparable model/opportunity rules. The current joint configuration loses 14.23 pp to its corresponding wider-context control; more adopted code does not resolve that gap.
2. **Make P audits valid and discriminating.** Diagnose invalid diagnostics, invalid/no-action candidates, actual parent/operator use and future-task difficulty. All three valid changed-P terminal comparisons select the same M and hit 0/4 on both sides. This motivates a discrimination hypothesis, not a verified cause. In the new protocol, establish usable development success ranges and predeclared validity coverage; never replace invalid effects with zero or improve coverage by selecting on final outcomes.
3. **Calibrate same-P variation.** Repeat P0-versus-P0 searches on new development data, reporting the whole search/write/answer pipeline, not just answer sampling. Predeclare independent repetitions and inference before the next final readout. The current two same-P terminal pairs contribute +75 pp; do not subtract that observed calibration after the fact.
4. **Reduce proposal contract failures.** Distinguish malformed diagnoses, candidate IR/schema failures, invalid P, no action and unavailable model measurements. Improve schema guidance/validation on new development traces; retain every failed opportunity and physical attempt. A valid proposal is still not a better search policy.

Only after these checks should the project expand the same evidence discipline to research judgment and optional user traces. The v0.3/v0.4/v0.5 product and research scope below remains in the plan; these next-cycle diagnostics take priority over adding more ingestion or community features.

## Planned versions after v0.2

- **v0.3 — improve research judgment through actual outcomes.** Track daily paper/project versions and read architecture, methods, experiments and implementation evidence. Store each human decision with context and reasons; maintain a separate record of later implemented candidate outcomes. Evolve the research selection/reading/recommendation policy only from past available evidence. Compare against fixed-policy discovery on chronological and paper-family holdouts, and measure whether approved ideas produce better later agent mechanisms. Agreement with the owner is one metric; demonstrated downstream effects are another. Downloading papers or remembering approvals alone does not pass.
- **v0.4 — personal evolution with optional community evidence.** Keep local-only use complete. Participants may opt into complete scoped trace processing with explicit withdrawal. Evaluate personal changes on each participant's later tasks before considering a separately authorized generic candidate. Test negative transfer, source duplication/Sybil attempts, low-dose poisoning over many rounds, forged approvals, malicious instructions and revocation of derived artifacts. No raw participant traces enter public releases. Approval and permissions remain fixed outer authority.
- **v0.5 — independent external and cross-model reproduction.** Select version-pinned public benchmark adapters that actually exercise memory, retrieval, tool choice and failure recovery. Run native official scoring where available, retain unchanged metrics and failed installations, and distinguish adapted tasks from official benchmark runs. Repeat frozen opportunity rules on another requested model/provider and compare physical calls, tokens and elapsed time, without promising deterministic model outputs.

Terminal joint M/P did not beat fixed P on the predeclared v0.2 mechanism endpoint, and isolated independent P benefit is unproven. The next cycle therefore follows the diagnostic order above under a new contract. It must not retrofit the v0.2 final set, hide unsuccessful runs, or treat more elaborate prompts as proven recursive improvement. Any future positive result also requires independent repetition before a broad superiority claim.
