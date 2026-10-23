# Continual experiment readout

Analysis status: **completed_readout**. Run status: **all_versions_frozen_pending_readout**. Source: authored public synthetic event streams; shared generation grammar

All numbers below come from retained observations. Structural tests are not model-effect measurements. Missing data is unavailable, not zero.

## Readout completeness

| Planned component | Observed / expected | Complete |
|---|---:|---|
| mechanism_readouts | 630/630 | True |
| independent_policy_audits | 50/50 | True |
| terminal_no_memory | 30/30 | True |
| terminal_wide_context_baseline | 30/30 | True |
| shared_audit_inputs | 10/10 | True |

Completion requires independent status completed and every planned mechanism readout, P audit, terminal control and shared audit input. An invalid P trial is an observed attempt whose effect is unknown; it is not a missing observation or a zero effect.

## Terminal mechanism comparison

| Partition | Paired streams | Joint − fixed-P (pp) | 95% stream bootstrap CI (pp) | Exact sign-flip p |
|---|---:|---:|---|---:|
| acceptance | 10 | -5.38 | -23.46, 10.77 | 0.5957 |
| transfer | 10 | 2.50 | -27.50, 27.50 | 1.0000 |

The unit is the stream, not each question. Bootstrap seed 20261023, 10,000 resamples. Exact two-sided sign-flip enumeration is descriptive and assumes exchangeability. These comparisons do not establish P's isolated benefit.

## Every frozen generation

| Split | Arm | Generation | Observed streams | Passed / total | Mean stream success |
|---|---|---:|---:|---:|---:|
| acceptance | fixed_mechanism | 0 | 10 | 141/260 | 54.23% |
| acceptance | fixed_mechanism | 1 | 10 | 146/260 | 56.15% |
| acceptance | fixed_mechanism | 2 | 10 | 149/260 | 57.31% |
| acceptance | fixed_mechanism | 3 | 10 | 148/260 | 56.92% |
| acceptance | fixed_mechanism | 4 | 10 | 147/260 | 56.54% |
| acceptance | fixed_mechanism | 5 | 10 | 143/260 | 55.00% |
| acceptance | fixed_mechanism | 6 | 10 | 146/260 | 56.15% |
| acceptance | fixed_mechanism | 7 | 10 | 148/260 | 56.92% |
| acceptance | fixed_mechanism | 8 | 10 | 142/260 | 54.62% |
| acceptance | fixed_mechanism | 9 | 10 | 142/260 | 54.62% |
| acceptance | fixed_mechanism | 10 | 10 | 145/260 | 55.77% |
| acceptance | fixed_mechanism | 11 | 10 | 147/260 | 56.54% |
| acceptance | fixed_mechanism | 12 | 10 | 144/260 | 55.38% |
| acceptance | fixed_mechanism | 13 | 10 | 148/260 | 56.92% |
| acceptance | fixed_mechanism | 14 | 10 | 146/260 | 56.15% |
| acceptance | fixed_mechanism | 15 | 10 | 141/260 | 54.23% |
| acceptance | fixed_mechanism | 16 | 10 | 144/260 | 55.38% |
| acceptance | fixed_mechanism | 17 | 10 | 144/260 | 55.38% |
| acceptance | fixed_mechanism | 18 | 10 | 140/260 | 53.85% |
| acceptance | fixed_mechanism | 19 | 10 | 143/260 | 55.00% |
| acceptance | fixed_mechanism | 20 | 10 | 146/260 | 56.15% |
| acceptance | fixed_p | 0 | 10 | 142/260 | 54.62% |
| acceptance | fixed_p | 1 | 10 | 147/260 | 56.54% |
| acceptance | fixed_p | 2 | 10 | 138/260 | 53.08% |
| acceptance | fixed_p | 3 | 10 | 137/260 | 52.69% |
| acceptance | fixed_p | 4 | 10 | 147/260 | 56.54% |
| acceptance | fixed_p | 5 | 10 | 147/260 | 56.54% |
| acceptance | fixed_p | 6 | 10 | 147/260 | 56.54% |
| acceptance | fixed_p | 7 | 10 | 149/260 | 57.31% |
| acceptance | fixed_p | 8 | 10 | 164/260 | 63.08% |
| acceptance | fixed_p | 9 | 10 | 166/260 | 63.85% |
| acceptance | fixed_p | 10 | 10 | 165/260 | 63.46% |
| acceptance | fixed_p | 11 | 10 | 188/260 | 72.31% |
| acceptance | fixed_p | 12 | 10 | 192/260 | 73.85% |
| acceptance | fixed_p | 13 | 10 | 196/260 | 75.38% |
| acceptance | fixed_p | 14 | 10 | 191/260 | 73.46% |
| acceptance | fixed_p | 15 | 10 | 193/260 | 74.23% |
| acceptance | fixed_p | 16 | 10 | 194/260 | 74.62% |
| acceptance | fixed_p | 17 | 10 | 194/260 | 74.62% |
| acceptance | fixed_p | 18 | 10 | 198/260 | 76.15% |
| acceptance | fixed_p | 19 | 10 | 198/260 | 76.15% |
| acceptance | fixed_p | 20 | 10 | 191/260 | 73.46% |
| acceptance | joint | 0 | 10 | 142/260 | 54.62% |
| acceptance | joint | 1 | 10 | 145/260 | 55.77% |
| acceptance | joint | 2 | 10 | 136/260 | 52.31% |
| acceptance | joint | 3 | 10 | 143/260 | 55.00% |
| acceptance | joint | 4 | 10 | 164/260 | 63.08% |
| acceptance | joint | 5 | 10 | 160/260 | 61.54% |
| acceptance | joint | 6 | 10 | 159/260 | 61.15% |
| acceptance | joint | 7 | 10 | 152/260 | 58.46% |
| acceptance | joint | 8 | 10 | 167/260 | 64.23% |
| acceptance | joint | 9 | 10 | 168/260 | 64.62% |
| acceptance | joint | 10 | 10 | 166/260 | 63.85% |
| acceptance | joint | 11 | 10 | 180/260 | 69.23% |
| acceptance | joint | 12 | 10 | 178/260 | 68.46% |
| acceptance | joint | 13 | 10 | 181/260 | 69.62% |
| acceptance | joint | 14 | 10 | 179/260 | 68.85% |
| acceptance | joint | 15 | 10 | 185/260 | 71.15% |
| acceptance | joint | 16 | 10 | 182/260 | 70.00% |
| acceptance | joint | 17 | 10 | 185/260 | 71.15% |
| acceptance | joint | 18 | 10 | 174/260 | 66.92% |
| acceptance | joint | 19 | 10 | 177/260 | 68.08% |
| acceptance | joint | 20 | 10 | 177/260 | 68.08% |
| transfer | fixed_mechanism | 0 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 1 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 2 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 3 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 4 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 5 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 6 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 7 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 8 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 9 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 10 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 11 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 12 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 13 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 14 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 15 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 16 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 17 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 18 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 19 | 10 | 0/40 | 0.00% |
| transfer | fixed_mechanism | 20 | 10 | 0/40 | 0.00% |
| transfer | fixed_p | 0 | 10 | 0/40 | 0.00% |
| transfer | fixed_p | 1 | 10 | 0/40 | 0.00% |
| transfer | fixed_p | 2 | 10 | 0/40 | 0.00% |
| transfer | fixed_p | 3 | 10 | 2/40 | 5.00% |
| transfer | fixed_p | 4 | 10 | 4/40 | 10.00% |
| transfer | fixed_p | 5 | 10 | 4/40 | 10.00% |
| transfer | fixed_p | 6 | 10 | 3/40 | 7.50% |
| transfer | fixed_p | 7 | 10 | 5/40 | 12.50% |
| transfer | fixed_p | 8 | 10 | 12/40 | 30.00% |
| transfer | fixed_p | 9 | 10 | 13/40 | 32.50% |
| transfer | fixed_p | 10 | 10 | 12/40 | 30.00% |
| transfer | fixed_p | 11 | 10 | 27/40 | 67.50% |
| transfer | fixed_p | 12 | 10 | 25/40 | 62.50% |
| transfer | fixed_p | 13 | 10 | 26/40 | 65.00% |
| transfer | fixed_p | 14 | 10 | 25/40 | 62.50% |
| transfer | fixed_p | 15 | 10 | 29/40 | 72.50% |
| transfer | fixed_p | 16 | 10 | 30/40 | 75.00% |
| transfer | fixed_p | 17 | 10 | 31/40 | 77.50% |
| transfer | fixed_p | 18 | 10 | 30/40 | 75.00% |
| transfer | fixed_p | 19 | 10 | 29/40 | 72.50% |
| transfer | fixed_p | 20 | 10 | 29/40 | 72.50% |
| transfer | joint | 0 | 10 | 0/40 | 0.00% |
| transfer | joint | 1 | 10 | 0/40 | 0.00% |
| transfer | joint | 2 | 10 | 0/40 | 0.00% |
| transfer | joint | 3 | 10 | 2/40 | 5.00% |
| transfer | joint | 4 | 10 | 12/40 | 30.00% |
| transfer | joint | 5 | 10 | 9/40 | 22.50% |
| transfer | joint | 6 | 10 | 10/40 | 25.00% |
| transfer | joint | 7 | 10 | 14/40 | 35.00% |
| transfer | joint | 8 | 10 | 24/40 | 60.00% |
| transfer | joint | 9 | 10 | 20/40 | 50.00% |
| transfer | joint | 10 | 10 | 21/40 | 52.50% |
| transfer | joint | 11 | 10 | 27/40 | 67.50% |
| transfer | joint | 12 | 10 | 28/40 | 70.00% |
| transfer | joint | 13 | 10 | 27/40 | 67.50% |
| transfer | joint | 14 | 10 | 25/40 | 62.50% |
| transfer | joint | 15 | 10 | 25/40 | 62.50% |
| transfer | joint | 16 | 10 | 27/40 | 67.50% |
| transfer | joint | 17 | 10 | 26/40 | 65.00% |
| transfer | joint | 18 | 10 | 28/40 | 70.00% |
| transfer | joint | 19 | 10 | 28/40 | 70.00% |
| transfer | joint | 20 | 10 | 30/40 | 75.00% |

## Independent terminal P audit

Primary: all valid terminal P-versus-P0 search pairs, including identical-P calibration. Distinct-P statistics explain a subset and never replace the primary; g0 is not subtracted after observation. All-attempt raw outcomes remain a separate operational comparison.
Fresh future-search audit: valid executed pairs=5/10 observed (10 planned); invalid=5, unknown validity/effect=0. All-valid-pair execution contrast = 30.00 pp.
Valid and actually distinct P: n=3, contrast=0.00 pp. Identical-P calibration: n=2, contrast=75.00 pp. Unknown policy identity among valid pairs=0.
Evolved-P evidence status: **descriptive_distinct_policy_readout**. Same-policy positive scores cannot establish evolved-P benefit.
All-attempt operational raw outcome difference = 22.50 pp. This includes invalid/fallback attempts and is not evidence of a successful changed P search. Distinct selected mechanisms in 5 observed streams.
Nonzero differences with the same selected mechanism: 0. This is sampling variation, not proof of changed search mechanisms.

All independent checkpoints, stream pairs, confidence intervals and exact p-values are retained in analysis.json. No checkpoint or winning generation is selected.

## Terminal memory ablation

| Arm | Paired streams | Current M with memory − same M without reads/writes (pp) |
|---|---:|---:|
| fixed_mechanism | 10 | 34.62 |
| fixed_p | 10 | 36.54 |
| joint | 10 | 31.15 |

This measures combined memory-read/write availability, not the isolated benefit of the evolved write policy.

## Wide-context baseline

| Arm | Paired streams | Current M − fixed baseline with wider context (pp) |
|---|---:|---:|
| fixed_mechanism | 10 | -28.08 |
| fixed_p | 10 | -7.31 |
| joint | 10 | -14.23 |

This is a separate fixed-mechanism context-size control; it has its own recorded mechanism hash and is not treated as the current M.

## Secondary pre-readout diagnostics · terminal versions

These checks were defined before the formal independent readout. They never replace strict primary success and never select versions. answer_ok/evidence_ok are retained host feedback; visible_support_sufficient means only that every required source_id/policy_source_id appears in the actual visible_facts, not that the model used it correctly or the mechanism caused an improvement.

| Arm | Split | Streams with raw traces | Answer OK | Evidence OK | Visible required support |
|---|---|---:|---|---|---|
| fixed_mechanism | acceptance | 10/10 | 149/260 | 146/260 | 151/260 |
| fixed_p | acceptance | 10/10 | 193/260 | 191/260 | 196/260 |
| joint | acceptance | 10/10 | 178/260 | 177/260 | 188/260 |
| fixed_mechanism | no_memory | 10/10 | 60/260 | 56/260 | 60/260 |
| fixed_p | no_memory | 10/10 | 98/260 | 96/260 | 98/260 |
| joint | no_memory | 10/10 | 98/260 | 96/260 | 98/260 |
| fixed_mechanism | transfer | 10/10 | 0/40 | 0/40 | 0/40 |
| fixed_p | transfer | 10/10 | 29/40 | 29/40 | 30/40 |
| joint | transfer | 10/10 | 30/40 | 30/40 | 30/40 |
| fixed_mechanism | wide_context_baseline | 10/10 | 222/260 | 219/260 | 224/260 |
| fixed_p | wide_context_baseline | 10/10 | 214/260 | 210/260 | 217/260 |
| joint | wide_context_baseline | 10/10 | 218/260 | 214/260 | 221/260 |

Denominators contain known checks only; unknown fields and missing raw streams are explicit. Tasks requiring no source are not_required, not automatic support successes. Every arm/generation/split and each retained trace check remain in analysis.json.

## Actual adoption and memory chains

| Lane | Observed rounds | M changes | P changes |
|---|---:|---:|---:|
| 101/fixed_mechanism | 20 | 0 | 0 |
| 101/fixed_p | 20 | 2 | 0 |
| 101/joint | 20 | 4 | 1 |
| 102/fixed_mechanism | 20 | 0 | 0 |
| 102/fixed_p | 20 | 4 | 0 |
| 102/joint | 20 | 3 | 3 |
| 103/fixed_mechanism | 20 | 0 | 0 |
| 103/fixed_p | 20 | 2 | 0 |
| 103/joint | 20 | 2 | 1 |
| 104/fixed_mechanism | 20 | 0 | 0 |
| 104/fixed_p | 20 | 2 | 0 |
| 104/joint | 20 | 5 | 0 |
| 105/fixed_mechanism | 20 | 0 | 0 |
| 105/fixed_p | 20 | 2 | 0 |
| 105/joint | 20 | 3 | 1 |
| 106/fixed_mechanism | 20 | 0 | 0 |
| 106/fixed_p | 20 | 4 | 0 |
| 106/joint | 20 | 3 | 0 |
| 107/fixed_mechanism | 20 | 0 | 0 |
| 107/fixed_p | 20 | 3 | 0 |
| 107/joint | 20 | 4 | 1 |
| 108/fixed_mechanism | 20 | 0 | 0 |
| 108/fixed_p | 20 | 3 | 0 |
| 108/joint | 20 | 4 | 0 |
| 109/fixed_mechanism | 20 | 0 | 0 |
| 109/fixed_p | 20 | 2 | 0 |
| 109/joint | 20 | 3 | 0 |
| 110/fixed_mechanism | 20 | 0 | 0 |
| 110/fixed_p | 20 | 5 | 0 |
| 110/joint | 20 | 2 | 0 |

Online curves and the primary memory-chain summary include committed rounds only: a completed transition, matching parent/next M/P hashes, and g(r+1) present. Uncommitted experiences remain below and in memory-chain.json; their calls/costs are retained. Online experience is optimization data.

| Arm | Committed episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 200 | 103 | 54 | 54 |
| fixed_p | 200 | 122 | 76 | 76 |
| joint | 200 | 103 | 60 | 60 |

Uncommitted observations (excluded from primary online/chain statistics; never discarded):

| Arm | Uncommitted episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 0 | 0 | 0 | 0 |
| fixed_p | 0 | 0 | 0 | 0 |
| joint | 0 | 0 | 0 | 0 |

Diagnostic statuses (main search and meta forks, scopes retained separately in JSON): {'invalid_diagnosis': 79, 'executed': 1084, 'invalid_candidate': 371, 'no_action': 53, 'invalid_policy': 15}.
Observed adjacent-version regressions: 157; every regression is retained in analysis.json.

## Physical requests and costs

```json
{
  "totals": {
    "logical_requests": 64321,
    "completed_requests": 64151,
    "failed_requests": 170,
    "physical_attempts": 64930,
    "attempts_with_usage": 64296,
    "attempts_without_usage": 634,
    "failed_physical_attempts": 779,
    "prompt_tokens": 141536176,
    "completion_tokens": 6805872,
    "total_tokens": 148342048
  },
  "by_arm_and_purpose": {
    "fixed_p": {
      "continual_memory_extraction": {
        "logical_requests": 7312,
        "completed_requests": 7291,
        "failed_requests": 21,
        "physical_attempts": 7369,
        "attempts_with_usage": 7291,
        "attempts_without_usage": 78,
        "failed_physical_attempts": 78,
        "prompt_tokens": 4657521,
        "completion_tokens": 834875,
        "total_tokens": 5492396
      },
      "continual_diagnosis": {
        "logical_requests": 633,
        "completed_requests": 633,
        "failed_requests": 0,
        "physical_attempts": 634,
        "attempts_with_usage": 634,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 1,
        "prompt_tokens": 12859550,
        "completion_tokens": 724938,
        "total_tokens": 13584488
      },
      "continual_task": {
        "logical_requests": 16603,
        "completed_requests": 16564,
        "failed_requests": 39,
        "physical_attempts": 16734,
        "attempts_with_usage": 16564,
        "attempts_without_usage": 170,
        "failed_physical_attempts": 170,
        "prompt_tokens": 17120129,
        "completion_tokens": 447103,
        "total_tokens": 17567232
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 319,
        "completed_requests": 317,
        "failed_requests": 2,
        "physical_attempts": 339,
        "attempts_with_usage": 326,
        "attempts_without_usage": 13,
        "failed_physical_attempts": 22,
        "prompt_tokens": 8857745,
        "completion_tokens": 244922,
        "total_tokens": 9102667
      },
      "continual_mechanism_proposal": {
        "logical_requests": 803,
        "completed_requests": 790,
        "failed_requests": 13,
        "physical_attempts": 885,
        "attempts_with_usage": 860,
        "attempts_without_usage": 25,
        "failed_physical_attempts": 95,
        "prompt_tokens": 20828241,
        "completion_tokens": 655163,
        "total_tokens": 21483404
      },
      "continual_policy_proposal": {
        "logical_requests": 214,
        "completed_requests": 209,
        "failed_requests": 5,
        "physical_attempts": 224,
        "attempts_with_usage": 209,
        "attempts_without_usage": 15,
        "failed_physical_attempts": 15,
        "prompt_tokens": 707896,
        "completion_tokens": 127515,
        "total_tokens": 835411
      }
    },
    "joint": {
      "continual_memory_extraction": {
        "logical_requests": 7083,
        "completed_requests": 7070,
        "failed_requests": 13,
        "physical_attempts": 7128,
        "attempts_with_usage": 7070,
        "attempts_without_usage": 58,
        "failed_physical_attempts": 58,
        "prompt_tokens": 4537239,
        "completion_tokens": 813014,
        "total_tokens": 5350253
      },
      "continual_policy_proposal": {
        "logical_requests": 210,
        "completed_requests": 210,
        "failed_requests": 0,
        "physical_attempts": 212,
        "attempts_with_usage": 210,
        "attempts_without_usage": 2,
        "failed_physical_attempts": 2,
        "prompt_tokens": 707867,
        "completion_tokens": 144548,
        "total_tokens": 852415
      },
      "continual_task": {
        "logical_requests": 16162,
        "completed_requests": 16114,
        "failed_requests": 48,
        "physical_attempts": 16304,
        "attempts_with_usage": 16114,
        "attempts_without_usage": 190,
        "failed_physical_attempts": 190,
        "prompt_tokens": 16421786,
        "completion_tokens": 434387,
        "total_tokens": 16856173
      },
      "continual_diagnosis": {
        "logical_requests": 604,
        "completed_requests": 603,
        "failed_requests": 1,
        "physical_attempts": 611,
        "attempts_with_usage": 604,
        "attempts_without_usage": 7,
        "failed_physical_attempts": 8,
        "prompt_tokens": 11964245,
        "completion_tokens": 722566,
        "total_tokens": 12686811
      },
      "continual_mechanism_proposal": {
        "logical_requests": 776,
        "completed_requests": 755,
        "failed_requests": 21,
        "physical_attempts": 863,
        "attempts_with_usage": 810,
        "attempts_without_usage": 53,
        "failed_physical_attempts": 108,
        "prompt_tokens": 19269945,
        "completion_tokens": 622457,
        "total_tokens": 19892402
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 301,
        "completed_requests": 294,
        "failed_requests": 7,
        "physical_attempts": 321,
        "attempts_with_usage": 298,
        "attempts_without_usage": 23,
        "failed_physical_attempts": 27,
        "prompt_tokens": 8018229,
        "completion_tokens": 228520,
        "total_tokens": 8246749
      }
    },
    "fixed_mechanism": {
      "continual_task": {
        "logical_requests": 7980,
        "completed_requests": 7980,
        "failed_requests": 0,
        "physical_attempts": 7980,
        "attempts_with_usage": 7980,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 7900766,
        "completion_tokens": 169625,
        "total_tokens": 8070391
      },
      "continual_memory_extraction": {
        "logical_requests": 3020,
        "completed_requests": 3020,
        "failed_requests": 0,
        "physical_attempts": 3020,
        "attempts_with_usage": 3020,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1792234,
        "completion_tokens": 332561,
        "total_tokens": 2124795
      }
    },
    "shared_policy_audit": {
      "continual_task": {
        "logical_requests": 1390,
        "completed_requests": 1390,
        "failed_requests": 0,
        "physical_attempts": 1390,
        "attempts_with_usage": 1390,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1109889,
        "completion_tokens": 27790,
        "total_tokens": 1137679
      },
      "continual_memory_extraction": {
        "logical_requests": 695,
        "completed_requests": 695,
        "failed_requests": 0,
        "physical_attempts": 695,
        "attempts_with_usage": 695,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 404435,
        "completion_tokens": 72272,
        "total_tokens": 476707
      },
      "continual_diagnosis": {
        "logical_requests": 100,
        "completed_requests": 100,
        "failed_requests": 0,
        "physical_attempts": 100,
        "attempts_with_usage": 100,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1764950,
        "completion_tokens": 114698,
        "total_tokens": 1879648
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 22,
        "completed_requests": 22,
        "failed_requests": 0,
        "physical_attempts": 22,
        "attempts_with_usage": 22,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 505773,
        "completion_tokens": 13999,
        "total_tokens": 519772
      },
      "continual_mechanism_proposal": {
        "logical_requests": 94,
        "completed_requests": 94,
        "failed_requests": 0,
        "physical_attempts": 99,
        "attempts_with_usage": 99,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 5,
        "prompt_tokens": 2107736,
        "completion_tokens": 74919,
        "total_tokens": 2182655
      }
    }
  },
  "by_phase": {
    "online": {
      "logical_requests": 5010,
      "completed_requests": 5008,
      "failed_requests": 2,
      "physical_attempts": 5018,
      "attempts_with_usage": 5008,
      "attempts_without_usage": 10,
      "failed_physical_attempts": 10,
      "prompt_tokens": 5205898,
      "completion_tokens": 232699,
      "total_tokens": 5438597
    },
    "mechanism-search": {
      "logical_requests": 11010,
      "completed_requests": 10932,
      "failed_requests": 78,
      "physical_attempts": 11295,
      "attempts_with_usage": 10991,
      "attempts_without_usage": 304,
      "failed_physical_attempts": 363,
      "prompt_tokens": 44921866,
      "completion_tokens": 1868749,
      "total_tokens": 46790615
    },
    "policy-meta-probe": {
      "logical_requests": 17256,
      "completed_requests": 17171,
      "failed_requests": 85,
      "physical_attempts": 17555,
      "attempts_with_usage": 17252,
      "attempts_without_usage": 303,
      "failed_physical_attempts": 384,
      "prompt_tokens": 55682088,
      "completion_tokens": 2654421,
      "total_tokens": 58336509
    },
    "policy-proposal": {
      "logical_requests": 424,
      "completed_requests": 419,
      "failed_requests": 5,
      "physical_attempts": 436,
      "attempts_with_usage": 419,
      "attempts_without_usage": 17,
      "failed_physical_attempts": 17,
      "prompt_tokens": 1415763,
      "completion_tokens": 272063,
      "total_tokens": 1687826
    },
    "independent": {
      "logical_requests": 26460,
      "completed_requests": 26460,
      "failed_requests": 0,
      "physical_attempts": 26460,
      "attempts_with_usage": 26460,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 26589458,
      "completion_tokens": 1392777,
      "total_tokens": 27982235
    },
    "independent_policy_audit_observations": {
      "logical_requests": 60,
      "completed_requests": 60,
      "failed_requests": 0,
      "physical_attempts": 60,
      "attempts_with_usage": 60,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 51050,
      "completion_tokens": 2807,
      "total_tokens": 53857
    },
    "independent_policy_audit": {
      "logical_requests": 2241,
      "completed_requests": 2241,
      "failed_requests": 0,
      "physical_attempts": 2246,
      "attempts_with_usage": 2246,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 5,
      "prompt_tokens": 5841733,
      "completion_tokens": 300871,
      "total_tokens": 6142604
    },
    "independent_wide_context": {
      "logical_requests": 1080,
      "completed_requests": 1080,
      "failed_requests": 0,
      "physical_attempts": 1080,
      "attempts_with_usage": 1080,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 1362845,
      "completion_tokens": 66766,
      "total_tokens": 1429611
    },
    "independent_memory_ablation": {
      "logical_requests": 780,
      "completed_requests": 780,
      "failed_requests": 0,
      "physical_attempts": 780,
      "attempts_with_usage": 780,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 465475,
      "completion_tokens": 14719,
      "total_tokens": 480194
    }
  },
  "usage_note": "Provider-reported usage summed once per physical attempt; missing usage is unknown, not free. Shared independent P-audit costs are not assigned to the joint arm. Nested resume receipt directories and discarded partial-round requests are included."
}
```

## Limits and missing evidence

- Shared authored synthetic generation grammar, not independent real-business validation
- One model sample per retained execution; temperature zero does not remove sampling variation
- Stream-paired descriptive confidence intervals and p-values do not establish causal superiority
- Meta-development policy promotions are optimization observations, never independent P evidence
- Terminal memory ablation changes reads and writes together; it does not isolate the write-policy contribution

[Interactive offline evidence](index.html) · [Full analysis](analysis.json) · [Memory chains](memory-chain.json) · [Independent inputs](independent.json)
