# Continual experiment readout

Analysis status: **partial_readout**. Run status: **aborted_measurement_incomplete**. Source: authored public synthetic event streams; shared generation grammar

All numbers below come from retained observations. Structural tests are not model-effect measurements. Missing data is unavailable, not zero.

## Readout completeness

| Planned component | Observed / expected | Complete |
|---|---:|---|
| mechanism_readouts | 0/630 | False |
| independent_policy_audits | 0/50 | False |
| terminal_no_memory | 0/30 | False |
| terminal_wide_context_baseline | 0/30 | False |
| shared_audit_inputs | 0/10 | False |

Completion requires independent status completed and every planned mechanism readout, P audit, terminal control and shared audit input. An invalid P trial is an observed attempt whose effect is unknown; it is not a missing observation or a zero effect.

## Terminal mechanism comparison

| Partition | Paired streams | Joint − fixed-P (pp) | 95% stream bootstrap CI (pp) | Exact sign-flip p |
|---|---:|---:|---|---:|
| acceptance | 0 | unavailable | unavailable | unavailable |
| transfer | 0 | unavailable | unavailable | unavailable |

The unit is the stream, not each question. Bootstrap seed 20261023, 10,000 resamples. Exact two-sided sign-flip enumeration is descriptive and assumes exchangeability. These comparisons do not establish P's isolated benefit.

## Every frozen generation

| Split | Arm | Generation | Observed streams | Passed / total | Mean stream success |
|---|---|---:|---:|---:|---:|
| acceptance | fixed_mechanism | 0 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 1 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 2 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 3 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 4 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 5 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 6 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 7 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 8 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 9 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 10 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 11 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 12 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 13 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 14 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 15 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 16 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 17 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 18 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 19 | 0 | unavailable | unavailable |
| acceptance | fixed_mechanism | 20 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 0 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 1 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 2 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 3 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 4 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 5 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 6 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 7 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 8 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 9 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 10 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 11 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 12 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 13 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 14 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 15 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 16 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 17 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 18 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 19 | 0 | unavailable | unavailable |
| acceptance | fixed_p | 20 | 0 | unavailable | unavailable |
| acceptance | joint | 0 | 0 | unavailable | unavailable |
| acceptance | joint | 1 | 0 | unavailable | unavailable |
| acceptance | joint | 2 | 0 | unavailable | unavailable |
| acceptance | joint | 3 | 0 | unavailable | unavailable |
| acceptance | joint | 4 | 0 | unavailable | unavailable |
| acceptance | joint | 5 | 0 | unavailable | unavailable |
| acceptance | joint | 6 | 0 | unavailable | unavailable |
| acceptance | joint | 7 | 0 | unavailable | unavailable |
| acceptance | joint | 8 | 0 | unavailable | unavailable |
| acceptance | joint | 9 | 0 | unavailable | unavailable |
| acceptance | joint | 10 | 0 | unavailable | unavailable |
| acceptance | joint | 11 | 0 | unavailable | unavailable |
| acceptance | joint | 12 | 0 | unavailable | unavailable |
| acceptance | joint | 13 | 0 | unavailable | unavailable |
| acceptance | joint | 14 | 0 | unavailable | unavailable |
| acceptance | joint | 15 | 0 | unavailable | unavailable |
| acceptance | joint | 16 | 0 | unavailable | unavailable |
| acceptance | joint | 17 | 0 | unavailable | unavailable |
| acceptance | joint | 18 | 0 | unavailable | unavailable |
| acceptance | joint | 19 | 0 | unavailable | unavailable |
| acceptance | joint | 20 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 0 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 1 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 2 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 3 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 4 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 5 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 6 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 7 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 8 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 9 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 10 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 11 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 12 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 13 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 14 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 15 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 16 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 17 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 18 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 19 | 0 | unavailable | unavailable |
| transfer | fixed_mechanism | 20 | 0 | unavailable | unavailable |
| transfer | fixed_p | 0 | 0 | unavailable | unavailable |
| transfer | fixed_p | 1 | 0 | unavailable | unavailable |
| transfer | fixed_p | 2 | 0 | unavailable | unavailable |
| transfer | fixed_p | 3 | 0 | unavailable | unavailable |
| transfer | fixed_p | 4 | 0 | unavailable | unavailable |
| transfer | fixed_p | 5 | 0 | unavailable | unavailable |
| transfer | fixed_p | 6 | 0 | unavailable | unavailable |
| transfer | fixed_p | 7 | 0 | unavailable | unavailable |
| transfer | fixed_p | 8 | 0 | unavailable | unavailable |
| transfer | fixed_p | 9 | 0 | unavailable | unavailable |
| transfer | fixed_p | 10 | 0 | unavailable | unavailable |
| transfer | fixed_p | 11 | 0 | unavailable | unavailable |
| transfer | fixed_p | 12 | 0 | unavailable | unavailable |
| transfer | fixed_p | 13 | 0 | unavailable | unavailable |
| transfer | fixed_p | 14 | 0 | unavailable | unavailable |
| transfer | fixed_p | 15 | 0 | unavailable | unavailable |
| transfer | fixed_p | 16 | 0 | unavailable | unavailable |
| transfer | fixed_p | 17 | 0 | unavailable | unavailable |
| transfer | fixed_p | 18 | 0 | unavailable | unavailable |
| transfer | fixed_p | 19 | 0 | unavailable | unavailable |
| transfer | fixed_p | 20 | 0 | unavailable | unavailable |
| transfer | joint | 0 | 0 | unavailable | unavailable |
| transfer | joint | 1 | 0 | unavailable | unavailable |
| transfer | joint | 2 | 0 | unavailable | unavailable |
| transfer | joint | 3 | 0 | unavailable | unavailable |
| transfer | joint | 4 | 0 | unavailable | unavailable |
| transfer | joint | 5 | 0 | unavailable | unavailable |
| transfer | joint | 6 | 0 | unavailable | unavailable |
| transfer | joint | 7 | 0 | unavailable | unavailable |
| transfer | joint | 8 | 0 | unavailable | unavailable |
| transfer | joint | 9 | 0 | unavailable | unavailable |
| transfer | joint | 10 | 0 | unavailable | unavailable |
| transfer | joint | 11 | 0 | unavailable | unavailable |
| transfer | joint | 12 | 0 | unavailable | unavailable |
| transfer | joint | 13 | 0 | unavailable | unavailable |
| transfer | joint | 14 | 0 | unavailable | unavailable |
| transfer | joint | 15 | 0 | unavailable | unavailable |
| transfer | joint | 16 | 0 | unavailable | unavailable |
| transfer | joint | 17 | 0 | unavailable | unavailable |
| transfer | joint | 18 | 0 | unavailable | unavailable |
| transfer | joint | 19 | 0 | unavailable | unavailable |
| transfer | joint | 20 | 0 | unavailable | unavailable |

## Independent terminal P audit

Primary: all valid terminal P-versus-P0 search pairs, including identical-P calibration. Distinct-P statistics explain a subset and never replace the primary; g0 is not subtracted after observation. All-attempt raw outcomes remain a separate operational comparison.
Unavailable. Meta-development promotion results are not substituted.

All independent checkpoints, stream pairs, confidence intervals and exact p-values are retained in analysis.json. No checkpoint or winning generation is selected.

## Terminal memory ablation

| Arm | Paired streams | Current M with memory − same M without reads/writes (pp) |
|---|---:|---:|
| fixed_mechanism | 0 | unavailable |
| fixed_p | 0 | unavailable |
| joint | 0 | unavailable |

This measures combined memory-read/write availability, not the isolated benefit of the evolved write policy.

## Wide-context baseline

| Arm | Paired streams | Current M − fixed baseline with wider context (pp) |
|---|---:|---:|
| fixed_mechanism | 0 | unavailable |
| fixed_p | 0 | unavailable |
| joint | 0 | unavailable |

This is a separate fixed-mechanism context-size control; it has its own recorded mechanism hash and is not treated as the current M.

## Secondary pre-readout diagnostics · terminal versions

These checks were defined before the formal independent readout. They never replace strict primary success and never select versions. answer_ok/evidence_ok are retained host feedback; visible_support_sufficient means only that every required source_id/policy_source_id appears in the actual visible_facts, not that the model used it correctly or the mechanism caused an improvement.

| Arm | Split | Streams with raw traces | Answer OK | Evidence OK | Visible required support |
|---|---|---:|---|---|---|
| fixed_mechanism | acceptance | 0/10 | unavailable | unavailable | unavailable |
| fixed_p | acceptance | 0/10 | unavailable | unavailable | unavailable |
| joint | acceptance | 0/10 | unavailable | unavailable | unavailable |
| fixed_mechanism | no_memory | 0/10 | unavailable | unavailable | unavailable |
| fixed_p | no_memory | 0/10 | unavailable | unavailable | unavailable |
| joint | no_memory | 0/10 | unavailable | unavailable | unavailable |
| fixed_mechanism | transfer | 0/10 | unavailable | unavailable | unavailable |
| fixed_p | transfer | 0/10 | unavailable | unavailable | unavailable |
| joint | transfer | 0/10 | unavailable | unavailable | unavailable |
| fixed_mechanism | wide_context_baseline | 0/10 | unavailable | unavailable | unavailable |
| fixed_p | wide_context_baseline | 0/10 | unavailable | unavailable | unavailable |
| joint | wide_context_baseline | 0/10 | unavailable | unavailable | unavailable |

Denominators contain known checks only; unknown fields and missing raw streams are explicit. Tasks requiring no source are not_required, not automatic support successes. Every arm/generation/split and each retained trace check remain in analysis.json.

## Actual adoption and memory chains

| Lane | Observed rounds | M changes | P changes |
|---|---:|---:|---:|
| 101/fixed_mechanism | 20 | 0 | 0 |
| 101/fixed_p | 15 | 2 | 0 |
| 101/joint | 15 | 3 | 1 |
| 102/fixed_mechanism | 20 | 0 | 0 |
| 102/fixed_p | 15 | 3 | 0 |
| 102/joint | 20 | 3 | 3 |
| 103/fixed_mechanism | 20 | 0 | 0 |
| 103/fixed_p | 15 | 1 | 0 |
| 103/joint | 14 | 1 | 1 |
| 104/fixed_mechanism | 20 | 0 | 0 |
| 104/fixed_p | 15 | 2 | 0 |
| 104/joint | 15 | 4 | 0 |
| 105/fixed_mechanism | 20 | 0 | 0 |
| 105/fixed_p | 15 | 1 | 0 |
| 105/joint | 16 | 3 | 1 |
| 106/fixed_mechanism | 20 | 0 | 0 |
| 106/fixed_p | 15 | 3 | 0 |
| 106/joint | 15 | 3 | 0 |
| 107/fixed_mechanism | 20 | 0 | 0 |
| 107/fixed_p | 13 | 3 | 0 |
| 107/joint | 15 | 2 | 1 |
| 108/fixed_mechanism | 20 | 0 | 0 |
| 108/fixed_p | 14 | 3 | 0 |
| 108/joint | 15 | 3 | 0 |
| 109/fixed_mechanism | 20 | 0 | 0 |
| 109/fixed_p | 15 | 2 | 0 |
| 109/joint | 15 | 3 | 0 |
| 110/fixed_mechanism | 20 | 0 | 0 |
| 110/fixed_p | 15 | 4 | 0 |
| 110/joint | 14 | 2 | 0 |

Online curves and the primary memory-chain summary include committed rounds only: a completed transition, matching parent/next M/P hashes, and g(r+1) present. Uncommitted experiences remain below and in memory-chain.json; their calls/costs are retained. Online experience is optimization data.

| Arm | Committed episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 200 | 103 | 54 | 54 |
| fixed_p | 147 | 87 | 48 | 48 |
| joint | 154 | 81 | 45 | 45 |

Uncommitted observations (excluded from primary online/chain statistics; never discarded):

| Arm | Uncommitted episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 0 | 0 | 0 | 0 |
| fixed_p | 10 | 7 | 6 | 6 |
| joint | 9 | 5 | 2 | 2 |

Diagnostic statuses (main search and meta forks, scopes retained separately in JSON): {'invalid_diagnosis': 55, 'executed': 841, 'invalid_candidate': 274, 'no_action': 41, 'invalid_policy': 15}.
Observed adjacent-version regressions: 0; every regression is retained in analysis.json.

## Physical requests and costs

```json
{
  "totals": {
    "logical_requests": 26003,
    "completed_requests": 25840,
    "failed_requests": 163,
    "physical_attempts": 26563,
    "attempts_with_usage": 25929,
    "attempts_without_usage": 634,
    "failed_physical_attempts": 723,
    "prompt_tokens": 76237142,
    "completion_tokens": 3751963,
    "total_tokens": 79989105
  },
  "by_arm_and_purpose": {
    "fixed_p": {
      "continual_memory_extraction": {
        "logical_requests": 3534,
        "completed_requests": 3513,
        "failed_requests": 21,
        "physical_attempts": 3591,
        "attempts_with_usage": 3513,
        "attempts_without_usage": 78,
        "failed_physical_attempts": 78,
        "prompt_tokens": 2075045,
        "completion_tokens": 363030,
        "total_tokens": 2438075
      },
      "continual_diagnosis": {
        "logical_requests": 471,
        "completed_requests": 471,
        "failed_requests": 0,
        "physical_attempts": 472,
        "attempts_with_usage": 472,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 1,
        "prompt_tokens": 8751292,
        "completion_tokens": 540164,
        "total_tokens": 9291456
      },
      "continual_task": {
        "logical_requests": 7359,
        "completed_requests": 7320,
        "failed_requests": 39,
        "physical_attempts": 7490,
        "attempts_with_usage": 7320,
        "attempts_without_usage": 170,
        "failed_physical_attempts": 170,
        "prompt_tokens": 6314321,
        "completion_tokens": 189500,
        "total_tokens": 6503821
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 229,
        "completed_requests": 227,
        "failed_requests": 2,
        "physical_attempts": 247,
        "attempts_with_usage": 234,
        "attempts_without_usage": 13,
        "failed_physical_attempts": 20,
        "prompt_tokens": 5975356,
        "completion_tokens": 170798,
        "total_tokens": 6146154
      },
      "continual_mechanism_proposal": {
        "logical_requests": 605,
        "completed_requests": 595,
        "failed_requests": 10,
        "physical_attempts": 669,
        "attempts_with_usage": 644,
        "attempts_without_usage": 25,
        "failed_physical_attempts": 74,
        "prompt_tokens": 14478445,
        "completion_tokens": 482233,
        "total_tokens": 14960678
      },
      "continual_policy_proposal": {
        "logical_requests": 160,
        "completed_requests": 155,
        "failed_requests": 5,
        "physical_attempts": 170,
        "attempts_with_usage": 155,
        "attempts_without_usage": 15,
        "failed_physical_attempts": 15,
        "prompt_tokens": 422691,
        "completion_tokens": 92550,
        "total_tokens": 515241
      }
    },
    "joint": {
      "continual_memory_extraction": {
        "logical_requests": 3436,
        "completed_requests": 3423,
        "failed_requests": 13,
        "physical_attempts": 3481,
        "attempts_with_usage": 3423,
        "attempts_without_usage": 58,
        "failed_physical_attempts": 58,
        "prompt_tokens": 2053286,
        "completion_tokens": 358286,
        "total_tokens": 2411572
      },
      "continual_policy_proposal": {
        "logical_requests": 163,
        "completed_requests": 163,
        "failed_requests": 0,
        "physical_attempts": 165,
        "attempts_with_usage": 163,
        "attempts_without_usage": 2,
        "failed_physical_attempts": 2,
        "prompt_tokens": 460131,
        "completion_tokens": 109878,
        "total_tokens": 570009
      },
      "continual_task": {
        "logical_requests": 7194,
        "completed_requests": 7146,
        "failed_requests": 48,
        "physical_attempts": 7336,
        "attempts_with_usage": 7146,
        "attempts_without_usage": 190,
        "failed_physical_attempts": 190,
        "prompt_tokens": 6176488,
        "completion_tokens": 189454,
        "total_tokens": 6365942
      },
      "continual_diagnosis": {
        "logical_requests": 463,
        "completed_requests": 462,
        "failed_requests": 1,
        "physical_attempts": 470,
        "attempts_with_usage": 463,
        "attempts_without_usage": 7,
        "failed_physical_attempts": 8,
        "prompt_tokens": 8615785,
        "completion_tokens": 546002,
        "total_tokens": 9161787
      },
      "continual_mechanism_proposal": {
        "logical_requests": 601,
        "completed_requests": 584,
        "failed_requests": 17,
        "physical_attempts": 665,
        "attempts_with_usage": 612,
        "attempts_without_usage": 53,
        "failed_physical_attempts": 81,
        "prompt_tokens": 13768820,
        "completion_tokens": 471488,
        "total_tokens": 14240308
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 228,
        "completed_requests": 221,
        "failed_requests": 7,
        "physical_attempts": 247,
        "attempts_with_usage": 224,
        "attempts_without_usage": 23,
        "failed_physical_attempts": 26,
        "prompt_tokens": 5783324,
        "completion_tokens": 174586,
        "total_tokens": 5957910
      }
    },
    "fixed_mechanism": {
      "continual_task": {
        "logical_requests": 1160,
        "completed_requests": 1160,
        "failed_requests": 0,
        "physical_attempts": 1160,
        "attempts_with_usage": 1160,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1141569,
        "completion_tokens": 24547,
        "total_tokens": 1166116
      },
      "continual_memory_extraction": {
        "logical_requests": 400,
        "completed_requests": 400,
        "failed_requests": 0,
        "physical_attempts": 400,
        "attempts_with_usage": 400,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 220589,
        "completion_tokens": 39447,
        "total_tokens": 260036
      }
    }
  },
  "by_phase": {
    "online": {
      "logical_requests": 4202,
      "completed_requests": 4200,
      "failed_requests": 2,
      "physical_attempts": 4210,
      "attempts_with_usage": 4200,
      "attempts_without_usage": 10,
      "failed_physical_attempts": 10,
      "prompt_tokens": 4169802,
      "completion_tokens": 189466,
      "total_tokens": 4359268
    },
    "mechanism-search": {
      "logical_requests": 8575,
      "completed_requests": 8498,
      "failed_requests": 77,
      "physical_attempts": 8849,
      "attempts_with_usage": 8545,
      "attempts_without_usage": 304,
      "failed_physical_attempts": 351,
      "prompt_tokens": 32985180,
      "completion_tokens": 1436903,
      "total_tokens": 34422083
    },
    "policy-meta-probe": {
      "logical_requests": 12903,
      "completed_requests": 12824,
      "failed_requests": 79,
      "physical_attempts": 13169,
      "attempts_with_usage": 12866,
      "attempts_without_usage": 303,
      "failed_physical_attempts": 345,
      "prompt_tokens": 38199338,
      "completion_tokens": 1923166,
      "total_tokens": 40122504
    },
    "policy-proposal": {
      "logical_requests": 323,
      "completed_requests": 318,
      "failed_requests": 5,
      "physical_attempts": 335,
      "attempts_with_usage": 318,
      "attempts_without_usage": 17,
      "failed_physical_attempts": 17,
      "prompt_tokens": 882822,
      "completion_tokens": 202428,
      "total_tokens": 1085250
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
- Missing version: 101/fixed_p/g16
- Missing version: 101/fixed_p/g17
- Missing version: 101/fixed_p/g18
- Missing version: 101/fixed_p/g19
- Missing version: 101/fixed_p/g20
- Missing version: 101/joint/g16
- Missing version: 101/joint/g17
- Missing version: 101/joint/g18
- Missing version: 101/joint/g19
- Missing version: 101/joint/g20
- Missing version: 102/fixed_p/g16
- Missing version: 102/fixed_p/g17
- Missing version: 102/fixed_p/g18
- Missing version: 102/fixed_p/g19
- Missing version: 102/fixed_p/g20
- Missing version: 103/fixed_p/g16
- Missing version: 103/fixed_p/g17
- Missing version: 103/fixed_p/g18
- Missing version: 103/fixed_p/g19
- Missing version: 103/fixed_p/g20
- Missing version: 103/joint/g15
- Missing version: 103/joint/g16
- Missing version: 103/joint/g17
- Missing version: 103/joint/g18
- Missing version: 103/joint/g19
- Missing version: 103/joint/g20
- Missing version: 104/fixed_p/g16
- Missing version: 104/fixed_p/g17
- Missing version: 104/fixed_p/g18
- Missing version: 104/fixed_p/g19
- Missing version: 104/fixed_p/g20
- Missing version: 104/joint/g16
- Missing version: 104/joint/g17
- Missing version: 104/joint/g18
- Missing version: 104/joint/g19
- Missing version: 104/joint/g20
- Missing version: 105/fixed_p/g16
- Missing version: 105/fixed_p/g17
- Missing version: 105/fixed_p/g18
- Missing version: 105/fixed_p/g19
- Missing version: 105/fixed_p/g20
- Missing version: 105/joint/g17
- Missing version: 105/joint/g18
- Missing version: 105/joint/g19
- Missing version: 105/joint/g20
- Missing version: 106/fixed_p/g16
- Missing version: 106/fixed_p/g17
- Missing version: 106/fixed_p/g18
- Missing version: 106/fixed_p/g19
- Missing version: 106/fixed_p/g20
- Missing version: 106/joint/g16
- Missing version: 106/joint/g17
- Missing version: 106/joint/g18
- Missing version: 106/joint/g19
- Missing version: 106/joint/g20
- Missing version: 107/fixed_p/g14
- Missing version: 107/fixed_p/g15
- Missing version: 107/fixed_p/g16
- Missing version: 107/fixed_p/g17
- Missing version: 107/fixed_p/g18
- Missing version: 107/fixed_p/g19
- Missing version: 107/fixed_p/g20
- Missing version: 107/joint/g16
- Missing version: 107/joint/g17
- Missing version: 107/joint/g18
- Missing version: 107/joint/g19
- Missing version: 107/joint/g20
- Missing version: 108/fixed_p/g15
- Missing version: 108/fixed_p/g16
- Missing version: 108/fixed_p/g17
- Missing version: 108/fixed_p/g18
- Missing version: 108/fixed_p/g19
- Missing version: 108/fixed_p/g20
- Missing version: 108/joint/g16
- Missing version: 108/joint/g17
- Missing version: 108/joint/g18
- Missing version: 108/joint/g19
- Missing version: 108/joint/g20
- Missing version: 109/fixed_p/g16
- Missing version: 109/fixed_p/g17
- Missing version: 109/fixed_p/g18
- Missing version: 109/fixed_p/g19
- Missing version: 109/fixed_p/g20
- Missing version: 109/joint/g16
- Missing version: 109/joint/g17
- Missing version: 109/joint/g18
- Missing version: 109/joint/g19
- Missing version: 109/joint/g20
- Missing version: 110/fixed_p/g16
- Missing version: 110/fixed_p/g17
- Missing version: 110/fixed_p/g18
- Missing version: 110/fixed_p/g19
- Missing version: 110/fixed_p/g20
- Missing version: 110/joint/g15
- Missing version: 110/joint/g16
- Missing version: 110/joint/g17
- Missing version: 110/joint/g18
- Missing version: 110/joint/g19
- Missing version: 110/joint/g20
- Independent readout incomplete or unavailable; missing observations are not zero outcomes

[Interactive offline evidence](index.html) · [Full analysis](analysis.json) · [Memory chains](memory-chain.json) · [Independent inputs](independent.json)
