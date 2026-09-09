<!-- generated from logs/raw/judged-full.jsonl -->

### Overall, by condition

| condition | n | accuracy | correct | partial | wrong | leak | truncated | mean tool calls | mean input tok | mean output tok | median latency s | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sql_only | 240 | 97% | 231 | 0 | 7 | 0 | 2 | 2.8 | 12,042 | 473 | 5.7 | $3.41 |
| vector_only | 240 | 97% | 228 | 1 | 6 | 0 | 5 | 2.8 | 13,643 | 492 | 6.7 | $4.50 |
| both | 240 | 98% | 229 | 0 | 5 | 0 | 6 | 3.0 | 14,874 | 494 | 6.7 | $4.19 |

### Accuracy by stratum

| stratum | sql_only | vector_only | both |
|---|---|---|---|
| exact_lookup | 100% (40/40) | 95% (38/40) | 100% (40/40) |
| paraphrase | 82% (33/40) | 88% (35/40) | 88% (35/40) |
| multi_hop | 100% (40/40) | 100% (40/40) | 100% (40/40) |
| temporal | 100% (40/40) | 100% (40/40) | 100% (40/40) |
| negative | 100% (39/39) _+1t_ | 100% (39/39) _+1t_ | 100% (37/37) _+3t_ |
| scope_restricted | 100% (39/39) _+1t_ | 100% (36/36) _+4t_ | 100% (37/37) _+3t_ |

### Temporal, by mechanism

| temporal mechanism | sql_only | vector_only | both |
|---|---|---|---|
| T-a  chase a supersedes edge | 100% (16/16) | 100% (16/16) | 100% (16/16) |
| T-b  overlapping validity windows | 100% (12/12) | 100% (12/12) | 100% (12/12) |
| T-c  opt-in override (historical) | 100% (12/12) | 100% (12/12) | 100% (12/12) |

### Tool preference

| behaviour in the `both` condition | runs | share |
|---|---|---|
| first call was `search` | 227 | 95% |
| first call was `query` | 13 | 5% |
| used only `search` | 129 | 54% |
| used only `query` | 7 | 3% |
| used both | 104 | 43% |
| made no tool call | 0 | 0% |

### Opt-in override usage

| condition | subset | runs that used the override | share |
|---|---|---|---|
| sql_only | T-c questions | 12/12 | 100% |
| sql_only | all questions | 87/240 | 36% |
| vector_only | T-c questions | 12/12 | 100% |
| vector_only | all questions | 93/240 | 39% |
| both | T-c questions | 12/12 | 100% |
| both | all questions | 88/240 | 37% |

### Run-to-run variance

| model | condition | correct per repeat | spread | questions that flipped |
|---|---|---|---|---|
| haiku | sql_only | 59 / 57 | 2 | 0/58 |
| haiku | vector_only | 55 / 58 | 3 | 2/56 |
| haiku | both | 57 / 56 | 1 | 1/55 |
| sonnet | sql_only | 58 / 57 | 1 | 1/60 |
| sonnet | vector_only | 58 / 57 | 1 | 1/60 |
| sonnet | both | 58 / 58 | 0 | 0/60 |

### By condition — haiku

| condition | n | accuracy | correct | partial | wrong | leak | truncated | mean tool calls | mean input tok | mean output tok | median latency s | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sql_only | 120 | 98% | 116 | 0 | 2 | 0 | 2 | 3.2 | 15,828 | 622 | 7.1 | $2.04 |
| vector_only | 120 | 98% | 113 | 1 | 1 | 0 | 5 | 3.8 | 18,723 | 713 | 8.0 | $2.13 |
| both | 120 | 99% | 113 | 0 | 1 | 0 | 6 | 3.8 | 18,443 | 671 | 7.8 | $2.14 |

### By stratum — haiku

| stratum | sql_only | vector_only | both |
|---|---|---|---|
| exact_lookup | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| paraphrase | 90% (18/20) | 90% (18/20) | 95% (19/20) |
| multi_hop | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| temporal | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| negative | 100% (19/19) _+1t_ | 100% (19/19) _+1t_ | 100% (17/17) _+3t_ |
| scope_restricted | 100% (19/19) _+1t_ | 100% (16/16) _+4t_ | 100% (17/17) _+3t_ |

### Temporal by mechanism — haiku

| temporal mechanism | sql_only | vector_only | both |
|---|---|---|---|
| T-a  chase a supersedes edge | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| T-b  overlapping validity windows | 100% (6/6) | 100% (6/6) | 100% (6/6) |
| T-c  opt-in override (historical) | 100% (6/6) | 100% (6/6) | 100% (6/6) |

### By condition — sonnet

| condition | n | accuracy | correct | partial | wrong | leak | truncated | mean tool calls | mean input tok | mean output tok | median latency s | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sql_only | 120 | 96% | 115 | 0 | 5 | 0 | 0 | 2.4 | 8,257 | 324 | 5.0 | $1.38 |
| vector_only | 120 | 96% | 115 | 0 | 5 | 0 | 0 | 1.8 | 8,564 | 271 | 6.0 | $2.37 |
| both | 120 | 97% | 116 | 0 | 4 | 0 | 0 | 2.2 | 11,305 | 317 | 5.8 | $2.05 |

### By stratum — sonnet

| stratum | sql_only | vector_only | both |
|---|---|---|---|
| exact_lookup | 100% (20/20) | 90% (18/20) | 100% (20/20) |
| paraphrase | 75% (15/20) | 85% (17/20) | 80% (16/20) |
| multi_hop | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| temporal | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| negative | 100% (20/20) | 100% (20/20) | 100% (20/20) |
| scope_restricted | 100% (20/20) | 100% (20/20) | 100% (20/20) |

### Temporal by mechanism — sonnet

| temporal mechanism | sql_only | vector_only | both |
|---|---|---|---|
| T-a  chase a supersedes edge | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| T-b  overlapping validity windows | 100% (6/6) | 100% (6/6) | 100% (6/6) |
| T-c  opt-in override (historical) | 100% (6/6) | 100% (6/6) | 100% (6/6) |

### Failures

_13 run(s) hit the 14-turn cap without emitting a final answer; those are counted as `truncated`, excluded from accuracy, and not listed below._

| qid | stratum | condition | verdict | gold | answer given |
|---|---|---|---|---|---|
| EX03 | exact_lookup | vector_only | wrong | Europe/Stockholm | NOT FOUND |
| EX03 | exact_lookup | vector_only | wrong | Europe/Stockholm | NOT FOUND |
| PA04 | paraphrase | sql_only | wrong | the kora | NOT FOUND |
| PA04 | paraphrase | sql_only | wrong | the kora | NOT FOUND |
| PA06 | paraphrase | both | wrong | Tallyho | NOT FOUND |
| PA06 | paraphrase | vector_only | wrong | Tallyho | NOT FOUND |
| PA06 | paraphrase | both | wrong | Tallyho | NOT FOUND |
| PA08 | paraphrase | sql_only | wrong | AWS | NOT FOUND |
| PA09 | paraphrase | sql_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | vector_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | both | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | sql_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | vector_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | both | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | sql_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | vector_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | both | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | sql_only | wrong | climbing | NOT FOUND |

### Totals

```json
{
  "runs": 720,
  "cost_usd": 12.1007054,
  "judge_cost_usd": 1.7029789999999998,
  "tool_calls": 2055,
  "tool_errors": 6,
  "models": [
    "haiku",
    "sonnet"
  ],
  "conditions": [
    "both",
    "sql_only",
    "vector_only"
  ]
}
```
