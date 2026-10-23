# Continual experiment readout

Analysis status: **partial_readout**. Run status: **aborted_measurement_incomplete**. Source: authored public synthetic event streams; shared generation grammar

All numbers below come from retained observations. Structural tests are not model-effect measurements. Missing data is unavailable, not zero.

## Terminal mechanism comparison

| Partition | Paired streams | Joint − fixed-P (pp) | 95% stream bootstrap CI (pp) | Exact sign-flip p |
|---|---:|---:|---|---:|
| acceptance | 0 | unavailable | unavailable | unavailable |
| transfer | 0 | unavailable | unavailable | unavailable |

The unit is the stream, not each question. Bootstrap seed 20261023, 10,000 resamples. Exact two-sided sign-flip enumeration is descriptive and assumes exchangeability. These comparisons do not establish P's isolated benefit.

## Every frozen generation

| Split | Arm | Generation | Observed streams | Passed / total | Mean stream success |
|---|---|---:|---:|---:|---:|
| acceptance | fixed_mechanism | 0 | 0 | 0/0 | unavailable% |
| acceptance | fixed_mechanism | 1 | 0 | 0/0 | unavailable% |
| acceptance | fixed_mechanism | 2 | 0 | 0/0 | unavailable% |
| acceptance | fixed_p | 0 | 0 | 0/0 | unavailable% |
| acceptance | fixed_p | 1 | 0 | 0/0 | unavailable% |
| acceptance | fixed_p | 2 | 0 | 0/0 | unavailable% |
| acceptance | joint | 0 | 0 | 0/0 | unavailable% |
| acceptance | joint | 1 | 0 | 0/0 | unavailable% |
| acceptance | joint | 2 | 0 | 0/0 | unavailable% |
| transfer | fixed_mechanism | 0 | 0 | 0/0 | unavailable% |
| transfer | fixed_mechanism | 1 | 0 | 0/0 | unavailable% |
| transfer | fixed_mechanism | 2 | 0 | 0/0 | unavailable% |
| transfer | fixed_p | 0 | 0 | 0/0 | unavailable% |
| transfer | fixed_p | 1 | 0 | 0/0 | unavailable% |
| transfer | fixed_p | 2 | 0 | 0/0 | unavailable% |
| transfer | joint | 0 | 0 | 0/0 | unavailable% |
| transfer | joint | 1 | 0 | 0/0 | unavailable% |
| transfer | joint | 2 | 0 | 0/0 | unavailable% |

## Independent terminal P audit

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

## Actual adoption and memory chains

| Lane | Observed rounds | M changes | P changes |
|---|---:|---:|---:|
| 931/fixed_mechanism | 2 | 0 | 0 |
| 931/fixed_p | 2 | 0 | 0 |
| 931/joint | 1 | 0 | 0 |

| Arm | Episodes | Structural chains | All four tasks passed | Effective closed loops |
|---|---:|---:|---:|---:|
| fixed_mechanism | 2 | 2 | 2 | 2 |
| fixed_p | 2 | 2 | 1 | 1 |
| joint | 2 | 2 | 2 | 2 |

Diagnostic statuses (main search and meta forks, scopes retained separately in JSON): {'executed': 12, 'invalid_diagnosis': 1, 'no_action': 1, 'invalid_candidate': 1}.
Observed adjacent-version regressions: 0; every regression is retained in analysis.json.

## Physical requests and costs

```json
{
  "totals": {
    "logical_requests": 328,
    "completed_requests": 327,
    "failed_requests": 1,
    "physical_attempts": 331,
    "attempts_with_usage": 331,
    "attempts_without_usage": 0,
    "failed_physical_attempts": 4,
    "prompt_tokens": 751943,
    "completion_tokens": 46912,
    "total_tokens": 798855
  },
  "by_arm_and_purpose": {
    "fixed_mechanism": {
      "continual_task": {
        "logical_requests": 9,
        "completed_requests": 9,
        "failed_requests": 0,
        "physical_attempts": 9,
        "attempts_with_usage": 9,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 8853,
        "completion_tokens": 294,
        "total_tokens": 9147
      },
      "continual_memory_extraction": {
        "logical_requests": 4,
        "completed_requests": 4,
        "failed_requests": 0,
        "physical_attempts": 4,
        "attempts_with_usage": 4,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 2164,
        "completion_tokens": 391,
        "total_tokens": 2555
      }
    },
    "fixed_p": {
      "continual_task": {
        "logical_requests": 105,
        "completed_requests": 105,
        "failed_requests": 0,
        "physical_attempts": 105,
        "attempts_with_usage": 105,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 78281,
        "completion_tokens": 2838,
        "total_tokens": 81119
      },
      "continual_mechanism_proposal": {
        "logical_requests": 8,
        "completed_requests": 8,
        "failed_requests": 0,
        "physical_attempts": 9,
        "attempts_with_usage": 9,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 1,
        "prompt_tokens": 143786,
        "completion_tokens": 5915,
        "total_tokens": 149701
      },
      "continual_memory_extraction": {
        "logical_requests": 52,
        "completed_requests": 52,
        "failed_requests": 0,
        "physical_attempts": 52,
        "attempts_with_usage": 52,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 27092,
        "completion_tokens": 4525,
        "total_tokens": 31617
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 3,
        "completed_requests": 3,
        "failed_requests": 0,
        "physical_attempts": 3,
        "attempts_with_usage": 3,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 59044,
        "completion_tokens": 2474,
        "total_tokens": 61518
      },
      "continual_diagnosis": {
        "logical_requests": 6,
        "completed_requests": 6,
        "failed_requests": 0,
        "physical_attempts": 6,
        "attempts_with_usage": 6,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 73384,
        "completion_tokens": 5908,
        "total_tokens": 79292
      },
      "continual_policy_proposal": {
        "logical_requests": 2,
        "completed_requests": 2,
        "failed_requests": 0,
        "physical_attempts": 2,
        "attempts_with_usage": 2,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1896,
        "completion_tokens": 1181,
        "total_tokens": 3077
      }
    },
    "joint": {
      "continual_task": {
        "logical_requests": 81,
        "completed_requests": 81,
        "failed_requests": 0,
        "physical_attempts": 81,
        "attempts_with_usage": 81,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 57978,
        "completion_tokens": 2291,
        "total_tokens": 60269
      },
      "continual_memory_extraction": {
        "logical_requests": 40,
        "completed_requests": 40,
        "failed_requests": 0,
        "physical_attempts": 40,
        "attempts_with_usage": 40,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 21222,
        "completion_tokens": 3614,
        "total_tokens": 24836
      },
      "continual_mechanism_syntax_repair": {
        "logical_requests": 3,
        "completed_requests": 3,
        "failed_requests": 0,
        "physical_attempts": 3,
        "attempts_with_usage": 3,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 55532,
        "completion_tokens": 2760,
        "total_tokens": 58292
      },
      "continual_mechanism_proposal": {
        "logical_requests": 7,
        "completed_requests": 6,
        "failed_requests": 1,
        "physical_attempts": 9,
        "attempts_with_usage": 9,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 3,
        "prompt_tokens": 147562,
        "completion_tokens": 7287,
        "total_tokens": 154849
      },
      "continual_diagnosis": {
        "logical_requests": 6,
        "completed_requests": 6,
        "failed_requests": 0,
        "physical_attempts": 6,
        "attempts_with_usage": 6,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 73295,
        "completion_tokens": 6306,
        "total_tokens": 79601
      },
      "continual_policy_proposal": {
        "logical_requests": 2,
        "completed_requests": 2,
        "failed_requests": 0,
        "physical_attempts": 2,
        "attempts_with_usage": 2,
        "attempts_without_usage": 0,
        "failed_physical_attempts": 0,
        "prompt_tokens": 1854,
        "completion_tokens": 1128,
        "total_tokens": 2982
      }
    }
  },
  "by_phase": {
    "online": {
      "logical_requests": 39,
      "completed_requests": 39,
      "failed_requests": 0,
      "physical_attempts": 39,
      "attempts_with_usage": 39,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 33051,
      "completion_tokens": 2055,
      "total_tokens": 35106
    },
    "policy-meta-probe": {
      "logical_requests": 171,
      "completed_requests": 170,
      "failed_requests": 1,
      "physical_attempts": 173,
      "attempts_with_usage": 173,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 3,
      "prompt_tokens": 405246,
      "completion_tokens": 25779,
      "total_tokens": 431025
    },
    "mechanism-search": {
      "logical_requests": 114,
      "completed_requests": 114,
      "failed_requests": 0,
      "physical_attempts": 115,
      "attempts_with_usage": 115,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 1,
      "prompt_tokens": 309896,
      "completion_tokens": 16769,
      "total_tokens": 326665
    },
    "policy-proposal": {
      "logical_requests": 4,
      "completed_requests": 4,
      "failed_requests": 0,
      "physical_attempts": 4,
      "attempts_with_usage": 4,
      "attempts_without_usage": 0,
      "failed_physical_attempts": 0,
      "prompt_tokens": 3750,
      "completion_tokens": 2309,
      "total_tokens": 6059
    }
  },
  "usage_note": "Provider-reported usage summed once per physical attempt; missing usage is unknown, not free. Shared independent P-audit costs are not assigned to the joint arm."
}
```

## Limits and missing evidence

- Shared authored synthetic generation grammar, not independent real-business validation
- One model sample per retained execution; temperature zero does not remove sampling variation
- Stream-paired descriptive confidence intervals and p-values do not establish causal superiority
- Meta-development policy promotions are optimization observations, never independent P evidence
- Terminal memory ablation changes reads and writes together; it does not isolate the write-policy contribution
- Missing version: 931/joint/g2
- Independent readout incomplete or unavailable; missing observations are not zero outcomes

[Interactive offline evidence](index.html) · [Full analysis](analysis.json) · [Memory chains](memory-chain.json) · [Independent inputs](independent.json)
