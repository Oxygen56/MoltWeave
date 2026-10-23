# Open-source presentation and organization references

Read-only review date: 2026-10-23. These are primary repository/README observations, not an adoption study, license audit or reproduction of their results. No code or assets were copied. Mutable main-branch URLs should be pinned to commits before citing a released comparison.

## 1. Four useful examples

| Repository | What its current first page does | What MoltWeave can borrow |
|---|---|---|
| [GEPA](https://github.com/gepa-ai/gepa) | States the optimizable artifact and feedback loop, then offers installation, a short executable example, broader adapters, docs and contribution links. | Lead with the actual executable P/M boundary; show one trace-to-program transition; link exact evaluation protocol and receipts. Keep research context separate from a beginner's first run. |
| [Mem0](https://github.com/mem0ai/mem0) | Explains the memory layer and offers library, self-hosted and managed-platform choices. Its current README explicitly distinguishes managed-platform benchmark numbers from OSS SDK behavior. | Separate local stdlib prototype, optional service capabilities and measured experiment scope; never attach future hosted/personalization claims to local results. |
| [OpenHands](https://github.com/OpenHands/OpenHands) | Its current README presents Agent Canvas, supported backends, a visual product entry, quickstart, self-hosting and community/docs. The identity and repository structure have evolved; older summaries can be stale. | Explain who owns execution, evolution and the control plane; provide a simple entry before architecture detail. A demo should show real version/decision evidence, not an animated claim of improvement. |
| [OpenClaw](https://github.com/openclaw/openclaw) | Starts with the assistant use case, install/onboarding, architecture, security boundaries, docs and contribution entry points. | Give readers a complete first-result chain and explicit boundaries for untrusted input, opt-in data and privileged changes. Do not imitate its many integration surfaces before they exist. |

Primary README links: [GEPA source](https://raw.githubusercontent.com/gepa-ai/gepa/main/README.md), [Mem0 source](https://raw.githubusercontent.com/mem0ai/mem0/main/README.md), [OpenHands source](https://raw.githubusercontent.com/OpenHands/OpenHands/main/README.md), [OpenClaw source](https://raw.githubusercontent.com/openclaw/openclaw/main/README.md).

These projects do not establish that a README shape causes popularity. The recommendations below are engineering/editorial judgments based on how they expose capabilities and reduce the steps to a real result.

## Mechanism references and actual overlap

- [Dream-RSI](https://github.com/google-research/dream-rsi) informs executable exploration-policy changes. MoltWeave has actual P-driven later searches, but its fixed-P controls do not establish isolated policy benefit.
- [Harness²](https://github.com/google-research/harness2) informs persistent improvement components and comparisons. The current implementation uses bounded expression programs, not an unrestricted source-code editor or a native reproduction.
- [DuplexAgent-RSI v1, sections 3.3–3.4](https://arxiv.org/html/2610.11299v1#S3.SS3) informs module-targeted diagnosis and candidate/protection comparisons. The [official demo snapshot](https://github.com/AmphionTeam/DuplexAgent-RSI-Demo/tree/21301d9795588e8a24bccd78c12e821cb8d9be52) still says **Code coming soon** on 2026-10-23; it is a website/assets repository, not a confirmed release of the core implementation. No core code was reused. MoltWeave's core experiment maps task families to modules; its separate feedback path asks the model for Trace-pointer attribution. It does not reproduce the complete Diagnoser, adaptive Exam Planner, six-module speech system, or per-case wins/losses/cause-regression promotion rule. The paper alone does not establish recursive rewriting of the Exam Planner or Harness Editor programs.

These are specific design correspondences, not claims of identical algorithms, original invention or superior benchmark results.

## 2. Proposed first page

1. One sentence: a continuously evolving agent whose bounded executable memory/retrieval/tool/recovery mechanisms and exploration policy produce versioned descendants.
2. A short real demonstration: failure, model-authored program diff, actual next-generation decision, real task result, rejection or regression if present.
3. One local command and one model-backed command, with exact prerequisites and what is/is not measured.
4. A compact result table linking model/configuration, synthetic suite/data hash, fixed-P control, generation lineage and independent readout. Keep incomplete/aborted runs visible.
5. The three boundaries: mechanism execution, mechanism evolution and independent benefit.
6. Architecture, evaluation protocol, governance/consent, current limitations and contribution routes.
7. Research references and honest overlap: executable artifact optimization, memory architecture evolution and harness self-modification already exist. Integration plus reproducible P evidence is the project's engineering contribution; do not claim first invention.

No badges claiming passing CI, published package, release, security certification or production deployment before an actual corresponding receipt exists. A local test result is not hosted CI.

## 3. Repository organization to make claims reviewable

The initial package already separates executable runtime/program/evolution from governance, research and community features. Keep examples small enough to run, and original model receipts immutable in experiment folders. Publish sanitized manifests and results, not credentials, raw opted-in user data or hidden acceptance labels.

Useful public surfaces, to add only when supported:
- LICENSE with a deliberately selected OSI license; cite third-party material and preserve its license. Current GEPA/OpenHands/OpenClaw repository pages display MIT and Mem0 displays Apache-2.0; that alone does not audit every subdirectory or dependency.
- CONTRIBUTING: reproduce a bug with a development fixture; avoid final-set examples in issues/proposals; distinguish a benchmark change from a mechanism change.
- SECURITY: private reporting route and boundaries for arbitrary-code execution, injection, trace uploads and ownership approval. Do not promise complete injection prevention.
- Issue templates: execution failure, invalid evidence/measurement, regression, integration request and benchmark-contract defect.
- Pull request evidence: contract affected, code/IR diff, actual run receipt, limitations; protocol changes require new experiment manifests.
- Releases/changelog: immutable tags, supported Python versions, exact current capability and breaking changes. A roadmap is not a completed release.

A small maintained core and clear extension points are compatible with an ambitious product. A repository that can reproduce real P/M generations is more credible than a broad list of connectors marked completed.

