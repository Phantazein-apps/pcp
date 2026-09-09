<!-- generated from logs/raw/judged-first-pass.jsonl -->

### Overall, by condition

| condition | n | accuracy | correct | partial | wrong | leak | mean tool calls | mean input tok | mean output tok | median latency s | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sql_only | 60 | 95% | 57 | 0 | 3 | 0 | 2.5 | 9,129 | 339 | 5.1 | $0.79 |
| vector_only | 60 | 97% | 58 | 0 | 2 | 0 | 1.7 | 8,261 | 256 | 6.1 | $1.41 |
| both | 60 | 97% | 58 | 0 | 2 | 0 | 2.3 | 11,357 | 327 | 6.1 | $1.18 |

### Accuracy by stratum

| stratum | sql_only | vector_only | both |
|---|---|---|---|
| exact_lookup | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| paraphrase | 70% (7/10) | 80% (8/10) | 80% (8/10) |
| multi_hop | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| temporal | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| negative | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| scope_restricted | 100% (10/10) | 100% (10/10) | 100% (10/10) |

### Temporal, by mechanism

| temporal mechanism | sql_only | vector_only | both |
|---|---|---|---|
| T-a  chase a supersedes edge | 100% (4/4) | 100% (4/4) | 100% (4/4) |
| T-b  overlapping validity windows | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| T-c  opt-in override (historical) | 100% (3/3) | 100% (3/3) | 100% (3/3) |

### Tool preference

| behaviour in the `both` condition | runs | share |
|---|---|---|
| first call was `search` | 55 | 92% |
| first call was `query` | 5 | 8% |
| used only `search` | 30 | 50% |
| used only `query` | 3 | 5% |
| used both | 27 | 45% |
| made no tool call | 0 | 0% |

### Opt-in override usage

| condition | subset | runs that used the override | share |
|---|---|---|---|
| sql_only | T-c questions | 3/3 | 100% |
| sql_only | all questions | 30/60 | 50% |
| vector_only | T-c questions | 3/3 | 100% |
| vector_only | all questions | 27/60 | 45% |
| both | T-c questions | 3/3 | 100% |
| both | all questions | 25/60 | 42% |

### Failures

| qid | stratum | condition | verdict | gold | answer given |
|---|---|---|---|---|---|
| PA04 | paraphrase | sql_only | wrong | the kora | NOT FOUND |
| PA05 | paraphrase | sql_only | wrong | by the chestnut tree at the end of | NOT FOUND |
| PA06 | paraphrase | vector_only | wrong | Tallyho | NOT FOUND |
| PA06 | paraphrase | both | wrong | Tallyho | NOT FOUND |
| PA09 | paraphrase | sql_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | vector_only | wrong | climbing | NOT FOUND |
| PA09 | paraphrase | both | wrong | climbing | NOT FOUND |

### Totals

```json
{
  "runs": 180,
  "cost_usd": 3.383699800000001,
  "judge_cost_usd": 0.4406850000000001,
  "tool_calls": 395,
  "tool_errors": 2,
  "models": [
    "sonnet"
  ],
  "conditions": [
    "both",
    "sql_only",
    "vector_only"
  ]
}
```
