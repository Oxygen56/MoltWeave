MoltWeave is an evidence-first research implementation of continual mechanism evolution for agents. It evolves bounded memory/retrieval/tool/retry/prompt programs and the policy choosing later improvement branches, while keeping the permission, approval and scoring host fixed.

This release includes two frozen four-round protocols with fixed-P controls, exact source snapshots, original model receipts, per-generation diffs/decisions, independent readouts and an offline evidence explorer. The latest joint synthetic run improves from 39/70 to 65/70 on held-out cases and 38/70 to 60/70 on namespace transfer. The fixed-P control reaches 67/70 and 65/70, so isolated P benefit is unproven.

A 24-question public SQuAD adaptation shows zero gain. Five component interventions retain all outcomes and expose same-request model variability. No real-business savings or native benchmark superiority is claimed.

Research discovery/full-text model analysis, explicit human-decision context, opt-in complete Trace transport, trace-to-candidate analysis and owner approval primitives are runnable. Their downstream judgment/community benefit and long-horizon poisoning effectiveness are not established. Post-experiment transport hardening is ordinary maintenance and is separated from the retained historical experiment hosts.

Python 3.11+, no runtime dependencies. Original code is Apache-2.0; selected SQuAD experiment content retains CC BY-SA 4.0 attribution. See README, EXPERIMENTS.md, ITERATION_PLAN.md and SECURITY.md before running real API calls or hosting a collector.
