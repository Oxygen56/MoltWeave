# Iteration plan and completion evidence

This plan keeps the complete project in scope. A completed implementation item is distinct from a measured effect. Dates and performance targets are not invented.

| Iteration | Deliverable | Acceptance evidence | Status at release |
|---|---|---|---|
| 1 · Fixed execution contract | H0, executable IR, real model client, traces, fixed scorer and partition manifest | Fresh real calls; scoped context; exact program identities; rejected unsafe programs | Implemented; real runs and offline contracts verified |
| 2 · Multi-generation mechanism evolution | Model proposals, actual candidate executions, protection gate, P0→P1→P2 and beyond | Each transition connects failure→diff→load→new decision→fresh outcome; failed generations retained | v3/v4 complete: two protocols, joint/fixed-P arms, four transitions each; joint runs each adopt three M changes |
| 3 · Attribution and independent effects | Frozen baseline/P controls, unseen cases, separate transfer readout and uncertainty | Comparable model/tools/feedback/opportunities; final results never select versions; P benefit kept distinct from M benefit | Both protocols/readouts complete; external SQuAD flat; five-variant component intervention complete; isolated P benefit unproven |
| 4 · Memory lifecycle and joint mechanisms | Durable factual memory writes, correction, quarantine, read/write programs, compatibility | Correct harmful experience and its production mechanism; retain useful old knowledge; compare joint vs isolated changes | v0.2 implemented: actual writer calls, provenance-grounded write program, correction/revocation, delayed recall; formal independent effects pending |
| 5 · External research learns to judge | Daily-capable discovery, versioned deep-read evidence, context/reason/effect records; evolvable research policy | Real accessible sources; human decisions recorded as such; chronological/family holdouts and downstream candidate effects | Discovery/deep-read/opt-in decision context implemented; real Dream-RSI full-text model call; judgment/P improvement unmeasured |
| 6 · Optional community evolution | Complete scoped traces, opt-in transport, private evolution and authorized generic proposals | Local-only usable; end-to-end consent/upload/revoke; tenant isolation; held-out user benefit and negative transfer | Transport/governance/trace-to-candidate implemented; two real synthetic-feedback model calls; personal/global benefit unmeasured |
| 7 · Long-horizon defenses | Injection, Sybil/duplicate sources, low-dose poisoning, invalidation and recovery | Multiple rounds; measured attack/benign outcomes; exact approval and replay denial; withdrawal derivative cleanup | Structural attacks and revocation tested; sustained model poisoning and Sybil effectiveness unmeasured |
| 8 · Open-source distribution | Installable package, bilingual README, architecture, examples, reproducible runs, evidence explorer, CI, license/security/contribution policy | Clean public export, fresh clone installation/run, actual public repository receipt | Published; fresh public clone installation and 96 tests pass; GitHub Python 3.11/3.12/3.13 CI passes; see docs/verification/publication.json |
| 9 · External and ecosystem validation | Official benchmark adapters; other model/provider; plugin interface | Actual source/version/license checked, native run receipts and unmodified metrics; independent reproduction | Planned |

## Core experiment procedure

The authorized v0.2 implementation and formal continuous experiment follow the [pre-readout protocol](docs/v0.2-protocol.md). It adds actual persistent-memory extraction/correction and broader P-driven diagnosis/operators, with 20 rounds across ten streams. Implementation and the four-round end-to-end engineering preflight are complete. The formal 20-round, ten-stream run started from frozen sources; a provider HTTP 402 interrupted the evolving arms before all descendants were sealed. Original calls and partial rounds remain retained. No formal independent-effect claim is available until the run is completed and independently read out. The public architecture and protocol describe this boundary explicitly.

Freeze the dataset generator, all split hashes, scoring implementation and baseline before optimization. Use disjoint factual namespaces, users, entities and source IDs for training, development, protection, final and transfer. The current partitions vary prefixes/wording but share task families and generation grammar; namespace transfer is not held-out template-family or real-system transfer. Train labels are exposed only after each output is sealed; final and transfer examples are never sent to the proposer.

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
| Durable memory loop | Separate real extraction calls; grounded writes; source-lineage correction; actual memory-only recalls and delayed recalls | Complete formal independent sequence and terminal memory-disabled comparison |
| Evolvable improvement policy | Diagnosis/proposal prompts, action scorer, operators and parent choice; actual paired search promotion | Complete held-out future-search audits; compare distinct P with same-P calibration |
| Continuous experiment | Frozen 20 rounds × ten streams × three arms; all observed candidates and original errors retained | Complete all 600 transitions and seal 630 version states before readout |
| Independent measurements | Empty-memory per-version execution, namespace transfer, terminal no-memory and wide-context controls implemented | Read every planned version once; report terminal g20, not the best observed generation |
| Evidence and distribution | Per-call physical attempts, hashes, differences, actual search actions, offline explorer, verified frozen-host reproduction | Full raw release archive, checksum inventory, fresh public-clone verification and exact release receipt |
| Interruption recovery | Preserve valid checkpoints and all failed receipts; archive unsealed work explicitly | No silent overwrite, no selected restart by outcome, no exactly-once claim for replayed unsealed rounds |

Implementation, offline contracts, development smoke and formal independent effects are separate statuses. A provider-funding interruption is an external prerequisite; it does not waive the independent acceptance or change the frozen mechanism protocol.

## Planned versions after v0.2

- **v0.3 — improve research judgment through actual outcomes.** Track daily paper/project versions and read architecture, methods, experiments and implementation evidence. Store each human decision with context and reasons; maintain a separate record of later implemented candidate outcomes. Evolve the research selection/reading/recommendation policy only from past available evidence. Compare against fixed-policy discovery on chronological and paper-family holdouts, and measure whether approved ideas produce better later agent mechanisms. Agreement with the owner is one metric; demonstrated downstream effects are another. Downloading papers or remembering approvals alone does not pass.
- **v0.4 — personal evolution with optional community evidence.** Keep local-only use complete. Participants may opt into complete scoped trace processing with explicit withdrawal. Evaluate personal changes on each participant's later tasks before considering a separately authorized generic candidate. Test negative transfer, source duplication/Sybil attempts, low-dose poisoning over many rounds, forged approvals, malicious instructions and revocation of derived artifacts. No raw participant traces enter public releases. Approval and permissions remain fixed outer authority.
- **v0.5 — independent external and cross-model reproduction.** Select version-pinned public benchmark adapters that actually exercise memory, retrieval, tool choice and failure recovery. Run native official scoring where available, retain unchanged metrics and failed installations, and distinguish adapted tasks from official benchmark runs. Repeat frozen opportunity rules on another requested model/provider and compare physical calls, tokens and elapsed time, without promising deterministic model outputs.

If terminal evolving P does not beat fixed P, v0.3 must first diagnose search validity, actual parent/operator use, sampling variance and future-task discrimination using development data under a new protocol. It must not retrofit the v0.2 final set, hide unsuccessful runs, or treat more elaborate prompts as proven recursive improvement. A positive result also requires an independently repeated protocol before any broad superiority claim.
