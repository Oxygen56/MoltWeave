# Continual experiment readout

Analysis status: **completed_readout**. Run status: **all_versions_frozen_pending_readout**. Source: authored public synthetic event streams; shared generation grammar

All numbers below come from retained observations. Structural tests are not model-effect measurements. Missing data is unavailable, not zero.

## Readout completeness

| Planned component | Observed / expected | Complete |
|---|---:|---|
| mechanism_readouts | 15/15 | True |
| independent_policy_audits | 5/5 | True |
| terminal_no_memory | 3/3 | True |
| terminal_wide_context_baseline | 3/3 | True |
| shared_audit_inputs | 1/1 | True |

Completion requires independent status completed and every planned mechanism readout, P audit, terminal control and shared audit input. An invalid P trial is an observed attempt whose effect is unknown; it is not a missing observation or a zero effect.

## Terminal mechanism comparison

| Partition | Paired streams | Joint − fixed-P (pp) | 95% stream bootstrap CI (pp) | Exact sign-flip p |
|---|---:|---:|---|---:|
| acceptance | 1 | 3.85 | 3.85, 3.85 | 1.0000 |
| transfer | 1 | 0.00 | 0.00, 0.00 | 1.0000 |

The unit is the stream, not each question. Bootstrap seed 20261023, 10,000 resamples. Exact two-sided sign-flip enumeration is descriptive and assumes exchangeability. These comparisons do not establish P's isolated benefit.

## Every frozen generation

| Split | Arm | Generation | Observed streams | Passed / total | Mean stream success |
|---|---|---:|---:|---:|---:|
| acceptance | fixed_mechanism | 0 | 1 | 15/26 | 57.69% |
| acceptance | fixed_mechanism | 1 | 1 | 16/26 | 61.54% |
| acceptance | fixed_mechanism | 2 | 1 | 15/26 | 57.69% |
| acceptance | fixed_mechanism | 3 | 1 | 15/26 | 57.69% |
| acceptance | fixed_mechanism | 4 | 1 | 15/26 | 57.69% |
| acceptance | fixed_p | 0 | 1 | 16/26 | 61.54% |
| acceptance | fixed_p | 1 | 1 | 16/26 | 61.54% |
| acceptance | fixed_p | 2 | 1 | 16/26 | 61.54% |
| acceptance | fixed_p | 3 | 1 | 16/26 | 61.54% |
| acceptance | fixed_p | 4 | 1 | 15/26 | 57.69% |
| acceptance | joint | 0 | 1 | 16/26 | 61.54% |
| acceptance | joint | 1 | 1 | 16/26 | 61.54% |
| acceptance | joint | 2 | 1 | 15/26 | 57.69% |
| acceptance | joint | 3 | 1 | 15/26 | 57.69% |
| acceptance | joint | 4 | 1 | 16/26 | 61.54% |
| transfer | fixed_mechanism | 0 | 1 | 0/4 | 0.00% |
| transfer | fixed_mechanism | 1 | 1 | 0/4 | 0.00% |
| transfer | fixed_mechanism | 2 | 1 | 0/4 | 0.00% |
| transfer | fixed_mechanism | 3 | 1 | 0/4 | 0.00% |
| transfer | fixed_mechanism | 4 | 1 | 0/4 | 0.00% |
| transfer | fixed_p | 0 | 1 | 0/4 | 0.00% |
| transfer | fixed_p | 1 | 1 | 0/4 | 0.00% |
| transfer | fixed_p | 2 | 1 | 0/4 | 0.00% |
| transfer | fixed_p | 3 | 1 | 0/4 | 0.00% |
| transfer | fixed_p | 4 | 1 | 0/4 | 0.00% |
| transfer | joint | 0 | 1 | 0/4 | 0.00% |
| transfer | joint | 1 | 1 | 0/4 | 0.00% |
| transfer | joint | 2 | 1 | 0/4 | 0.00% |
| transfer | joint | 3 | 1 | 0/4 | 0.00% |
| transfer | joint | 4 | 1 | 0/4 | 0.00% |

## Independent terminal P audit

Primary: all valid terminal P-versus-P0 search pairs, including identical-P calibration. Distinct-P statistics explain a subset and never replace the primary; g0 is not subtracted after observation. All-attempt raw outcomes remain a separate operational comparison.
Fresh future-search audit: valid executed pairs=0/1 observed (1 planned); invalid=1, unknown validity/effect=0. All-valid-pair execution contrast = unavailable pp.
Valid and actually distinct P: n=0, contrast=unavailable pp. Identical-P calibration: n=0, contrast=unavailable pp. Unknown policy identity among valid pairs=0.
Evolved-P evidence status: **no_distinct_policy_evidence**. Same-policy positive scores cannot establish evolved-P benefit.
All-attempt operational raw outcome difference = 0.00 pp. This includes invalid/fallback attempts and is not evidence of a successful changed P search. Distinct selected mechanisms in 0 observed streams.
Nonzero differences with the same selected mechanism: 0. This is sampling variation, not proof of changed search mechanisms.

All independent checkpoints, stream pairs, confidence intervals and exact p-values are retained in analysis.json. No checkpoint or winning generation is selected.

## Terminal memory ablation

| Arm | Paired streams | Current M with memory − same M without reads/writes (pp) |
|---|---:|---:|
| fixed_mechanism | 1 | 34.62 |
| fixed_p | 1 | 34.62 |
| joint | 1 | 38.46 |

This measures combined memory-read/write availability, not the isolated benefit of the evolved write policy.

## Wide-context baseline

| Arm | Paired streams | Current M − fixed baseline with wider context (pp) |
|---|---:|---:|
| fixed_mechanism | 1 | -38.46 |
| fixed_p | 1 | -30.77 |
| joint | 1 | -26.92 |

This is a separate fixed-mechanism context-size control; it has its own recorded mechanism hash and is not treated as the current M.

## Secondary pre-readout diagnostics · terminal versions

These checks were defined before the formal independent readout. They never replace strict primary success and never select versions. answer_ok/evidence_ok are retained host feedback; visible_support_sufficient means only that every required source_id/policy_source_id appears in the actual visible_facts, not that the model used it correctly or the mechanism caused an improvement.

| Arm | Split | Streams with raw traces | Answer OK | Evidence OK | Visible required support |
|---|---|---:|---|---|---|
| fixed_mechanism | acceptance | 1/1 | 15/26 | 15/26 | 16/26 |
| fixed_p | acceptance | 1/1 | 15/26 | 15/26 | 16/26 |
| joint | acceptance | 1/1 | 16/26 | 16/26 | 16/26 |
| fixed_mechanism | no_memory | 1/1 | 6/26 | 6/26 | 6/26 |
| fixed_p | no_memory | 1/1 | 6/26 | 6/26 | 6/26 |
| joint | no_memory | 1/1 | 6/26 | 6/26 | 6/26 |
| fixed_mechanism | transfer | 1/1 | 0/4 | 0/4 | 0/4 |
| fixed_p | transfer | 1/1 | 0/4 | 0/4 | 0/4 |
| joint | transfer | 1/1 | 0/4 | 0/4 | 0/4 |
| fixed_mechanism | wide_context_baseline | 1/1 | 25/26 | 25/26 | 25/26 |
| fixed_p | wide_context_baseline | 1/1 | 23/26 | 23/26 | 23/26 |
| joint | wide_context_baseline | 1/1 | 23/26 | 23/26 | 23/26 |

Denominators contain known checks only; unknown fields and missing raw streams are explicit. Tasks requiring no source are not_required, not automatic support successes. Every arm/generation/split and each retained trace check remain in analysis.json.

## Actual adoption and memory chains

| Lane | Observed rounds | M changes | P changes |
|---|---:|---:|---:|
| 951/fixed_mechanism | 4 | 0 | 0 |
| 951/fixed_p | 4 | 1 | 0 |
| 951/joint | 4 | 0 | 0 |

Online curves and the primary memory-chain summary include committed rounds only: a completed transition, matching parent/next M/P hashes, and g(r+1) present. Uncommitted experiences remain below and in memory-chain.json; their calls/costs are retained. Online experience is optimization data.

| Arm | Committed episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 4 | 3 | 2 | 2 |
| fixed_p | 4 | 4 | 2 | 2 |
| joint | 4 | 4 | 2 | 2 |

Uncommitted observations (excluded from primary online/chain statistics; never discarded):

| Arm | Uncommitted episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 0 | 0 | 0 | 0 |
| fixed_p | 0 | 0 | 0 | 0 |
| joint | 0 | 0 | 0 | 0 |

Diagnostic statuses (main search and meta forks, scopes retained separately in JSON): {'executed': 23, 'invalid_diagnosis': 3, 'invalid_candidate': 2, 'no_action': 1}.
Observed adjacent-version regressions: 3; every regression is retained in analysis.json.

## Physical requests and costs

```json
{
  "totals": {
    "logical_requests": 1668,
    "completed_requests": 1668,
    "failed_requests": 0,
    "physical_attempts": 1669,
    "attempts_with_usage": 1669,
    "attempts_without_usage": 0,
    "failed_physical_attempts": 1,
    "prompt_tokens": 2533378,
    "completion_tokens": 148459,
    "total_tokens": 2681837
  },
  "by_arm_and_purpose": {
    "fixed_mechanism": {
      "continual_memory_extraction": {
        "logical_requests": 78,
        "completed_requests": 78,
        "failed_requests": 0,
        "physical_attempts": 78,
        "attempts_with_usage": 78,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 46031,
        "completion_tokens": 8194,
        "total_tokens": 54225
      },
      "continual_task": {
        "logical_requests": 222,
        "completed_requests": 222,
        "failed_requests": 0,
        "physical_attempts": 222,
        "attempts_with_usage": 222,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 217320,
        "completion_tokens": 5083,
        "total_tokens": 222403
      }
    },
    "fixed_p": {
      "continual_task": {
        "logical_requests": 396,
        "completed_requests": 396,
        "failed_requests": 0,
        "physical_attempts": 396,
        "attempts_with_usage": 396,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 343693,
        "completion_tokens": 9110,
        "total_tokens": 352803
      },
      "continual_memory_extraction": {
        "logical_requests": 165,
        "completed_requests": 165,
        "failed_requests": 0,
        "physical_attempts": 165,
        "attempts_with_usage": 165,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 92413,
        "completion_tokens": 16163,
        "total_tokens": 108576
      },
      "continual_diagnosis": {
        "logical_requests": 12,
        "completed_requests": 12,
        "failed_requests": 0,
        "physical_attempts": 12,
        "attempts_with_usage": 12,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 168958,
        "completion_tokens": 14346,
        "total_tokens": 183304
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 3,
        "completed_requests": 3,
        "failed_requests": 0,
        "physical_attempts": 3,
        "attempts_with_usage": 3,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 54697,
        "completion_tokens": 2216,
        "total_tokens": 56913
      },
      "continual_policy_proposal": {
        "logical_requests": 4,
        "completed_requests": 4,
        "failed_requests": 0,
        "physical_attempts": 4,
        "attempts_with_usage": 4,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 4622,
        "completion_tokens": 2165,
        "total_tokens": 6787
      },
      "continual_mechanism_proposal": {
        "logical_requests": 14,
        "completed_requests": 14,
        "failed_requests": 0,
        "physical_attempts": 14,
        "attempts_with_usage": 14,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 246211,
        "completion_tokens": 9361,
        "total_tokens": 255572
      }
    },
    "joint": {
      "continual_task": {
        "logical_requests": 378,
        "completed_requests": 378,
        "failed_requests": 0,
        "physical_attempts": 378,
        "attempts_with_usage": 378,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 331398,
        "completion_tokens": 8905,
        "total_tokens": 340303
      },
      "continual_memory_extraction": {
        "logical_requests": 156,
        "completed_requests": 156,
        "failed_requests": 0,
        "physical_attempts": 156,
        "attempts_with_usage": 156,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 90543,
        "completion_tokens": 16058,
        "total_tokens": 106601
      },
      "continual_diagnosis": {
        "logical_requests": 12,
        "completed_requests": 12,
        "failed_requests": 0,
        "physical_attempts": 12,
        "attempts_with_usage": 12,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 167818,
        "completion_tokens": 12590,
        "total_tokens": 180408
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 2,
        "completed_requests": 2,
        "failed_requests": 0,
        "physical_attempts": 2,
        "attempts_with_usage": 2,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 39807,
        "completion_tokens": 2206,
        "total_tokens": 42013
      },
      "continual_policy_proposal": {
        "logical_requests": 4,
        "completed_requests": 4,
        "failed_requests": 0,
        "physical_attempts": 4,
        "attempts_with_usage": 4,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 4132,
        "completion_tokens": 2129,
        "total_tokens": 6261
      },
      "continual_mechanism_proposal": {
        "logical_requests": 11,
        "completed_requests": 11,
        "failed_requests": 0,
        "physical_attempts": 11,
        "attempts_with_usage": 11,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 194144,
        "completion_tokens": 11180,
        "total_tokens": 205324
      }
    },
    "shared_policy_audit": {
      "continual_task": {
        "logical_requests": 124,
        "completed_requests": 124,
        "failed_requests": 0,
        "physical_attempts": 124,
        "attempts_with_usage": 124,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 84172,
        "completion_tokens": 1818,
        "total_tokens": 85990
      },
      "continual_memory_extraction": {
        "logical_requests": 62,
        "completed_requests": 62,
        "failed_requests": 0,
        "physical_attempts": 62,
        "attempts_with_usage": 62,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 35721,
        "completion_tokens": 6342,
        "total_tokens": 42063
      },
      "continual_diagnosis": {
        "logical_requests": 10,
        "completed_requests": 10,
        "failed_requests": 0,
        "physical_attempts": 10,
        "attempts_with_usage": 10,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 133220,
        "completion_tokens": 11033,
        "total_tokens": 144253
      },
      "continual_mechanism_proposal": {
        "logical_requests": 10,
        "completed_requests": 10,
        "failed_requests": 0,
        "physical_attempts": 11,
        "attempts_with_usage": 11,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 1,
        "prompt_tokens": 185707,
        "completion_tokens": 6683,
        "total_tokens": 192390
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 5,
        "completed_requests": 5,
        "failed_requests": 0,
        "physical_attempts": 5,
        "attempts_with_usage": 5,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 92771,
        "completion_tokens": 2877,
        "total_tokens": 95648
      }
    }
  },
  "by_phase": {
    "independent": {
      "logical_requests": 630,
      "completed_requests": 630,
      "failed_requests": 0,
      "physical_attempts": 630,
      "attempts_with_usage": 630,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 541437,
      "completion_tokens": 28599,
      "total_tokens": 570036
    },
    "independent_wide_context": {
      "logical_requests": 108,
      "completed_requests": 108,
      "failed_requests": 0,
      "physical_attempts": 108,
      "attempts_with_usage": 108,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 137634,
      "completion_tokens": 6341,
      "total_tokens": 143975
    },
    "independent_memory_ablation": {
      "logical_requests": 78,
      "completed_requests": 78,
      "failed_requests": 0,
      "physical_attempts": 78,
      "attempts_with_usage": 78,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 37713,
      "completion_tokens": 1258,
      "total_tokens": 38971
    },
    "mechanism-search": {
      "logical_requests": 181,
      "completed_requests": 181,
      "failed_requests": 0,
      "physical_attempts": 181,
      "attempts_with_usage": 181,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 408921,
      "completion_tokens": 25279,
      "total_tokens": 434200
    },
    "online": {
      "logical_requests": 84,
      "completed_requests": 84,
      "failed_requests": 0,
      "physical_attempts": 84,
      "attempts_with_usage": 84,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 73624,
      "completion_tokens": 3851,
      "total_tokens": 77475
    },
    "policy-meta-probe": {
      "logical_requests": 368,
      "completed_requests": 368,
      "failed_requests": 0,
      "physical_attempts": 368,
      "attempts_with_usage": 368,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 793704,
      "completion_tokens": 50084,
      "total_tokens": 843788
    },
    "independent_policy_audit": {
      "logical_requests": 205,
      "completed_requests": 205,
      "failed_requests": 0,
      "physical_attempts": 206,
      "attempts_with_usage": 206,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 1,
      "prompt_tokens": 526529,
      "completion_tokens": 28474,
      "total_tokens": 555003
    },
    "independent_policy_audit_observations": {
      "logical_requests": 6,
      "completed_requests": 6,
      "failed_requests": 0,
      "physical_attempts": 6,
      "attempts_with_usage": 6,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 5062,
      "completion_tokens": 279,
      "total_tokens": 5341
    },
    "policy-proposal": {
      "logical_requests": 8,
      "completed_requests": 8,
      "failed_requests": 0,
      "physical_attempts": 8,
      "attempts_with_usage": 8,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 8754,
      "completion_tokens": 4294,
      "total_tokens": 13048
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
