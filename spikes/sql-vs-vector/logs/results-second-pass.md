<!-- generated from logs/raw/judged-a-haiku.jsonl logs/raw/judged-a-sonnet.jsonl logs/raw/judged-b-haiku.jsonl logs/raw/judged-b-sonnet.jsonl -->

### Headline, all models pooled

| corpus | condition | runs | seeds | accuracy | result bytes/run | tool calls | input tok/run | cache-creation tok/run | mean cost/run | median cost/run | latency s | leaks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| corpus-a | `sql_narrow` | 126 | 3 | 88% (86-90) | 3,719 | 2.8 | 12,591 | 2,092 | $0.0157 | $0.0132 | 8.1 | 0 |
| corpus-a | `sql_document` | 126 | 3 | 83% (81-83) | 2,751 | 2.6 | 12,941 | 1,711 | $0.0138 | $0.0108 | 8.3 | 0 |
| corpus-a | `vector_only` | 126 | 3 | 87% (86-88) | 5,841 | 2.0 | 8,477 | 2,136 | $0.0130 | $0.0080 | 6.5 | 0 |
| corpus-a | `both` | 126 | 3 | 87% (86-88) | 4,576 | 2.3 | 14,247 | 2,203 | $0.0148 | $0.0107 | 6.9 | 0 |
| corpus-b | `sql_narrow` | 126 | 3 | 92% (90-93) | 15,147 | 2.9 | 21,994 | 5,851 | $0.0256 | $0.0210 | 7.6 | 0 |
| corpus-b | `sql_document` | 126 | 3 | 91% (90-93) | 14,091 | 2.9 | 24,151 | 4,976 | $0.0238 | $0.0171 | 6.7 | 0 |
| corpus-b | `vector_only` | 126 | 3 | 87% (86-88) | 18,937 | 2.0 | 12,871 | 4,830 | $0.0228 | $0.0185 | 6.6 | 0 |
| corpus-b | `both` | 126 | 3 | 89% (88-90) | 14,746 | 2.8 | 19,088 | 5,018 | $0.0220 | $0.0185 | 7.4 | 0 |

### Headline -- haiku

| corpus | condition | runs | seeds | accuracy | result bytes/run | tool calls | input tok/run | cache-creation tok/run | mean cost/run | median cost/run | latency s | leaks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| corpus-a | `sql_narrow` | 63 | 3 | 90% (86-95) | 4,405 | 2.8 | 13,666 | 2,159 | $0.0164 | $0.0142 | 8.9 | 0 |
| corpus-a | `sql_document` | 63 | 3 | 84% (81-86) | 2,924 | 2.7 | 13,666 | 1,975 | $0.0154 | $0.0122 | 7.1 | 0 |
| corpus-a | `vector_only` | 63 | 3 | 86% | 5,612 | 2.5 | 9,054 | 1,247 | $0.0102 | $0.0065 | 6.6 | 0 |
| corpus-a | `both` | 63 | 3 | 87% (86-90) | 4,708 | 2.7 | 17,280 | 2,273 | $0.0157 | $0.0085 | 7.0 | 0 |
| corpus-b | `sql_narrow` | 63 | 3 | 95% | 18,580 | 3.0 | 26,056 | 7,088 | $0.0246 | $0.0211 | 8.5 | 0 |
| corpus-b | `sql_document` | 63 | 3 | 89% (86-95) | 16,913 | 3.1 | 27,448 | 6,470 | $0.0245 | $0.0229 | 7.7 | 0 |
| corpus-b | `vector_only` | 63 | 3 | 84% (81-86) | 17,694 | 2.4 | 11,481 | 3,129 | $0.0143 | $0.0071 | 7.1 | 0 |
| corpus-b | `both` | 63 | 3 | 86% (81-90) | 16,303 | 3.0 | 20,371 | 5,989 | $0.0199 | $0.0138 | 7.2 | 0 |

### Headline -- sonnet

| corpus | condition | runs | seeds | accuracy | result bytes/run | tool calls | input tok/run | cache-creation tok/run | mean cost/run | median cost/run | latency s | leaks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| corpus-a | `sql_narrow` | 63 | 3 | 86% | 3,032 | 2.8 | 11,516 | 2,025 | $0.0150 | $0.0129 | 7.5 | 0 |
| corpus-a | `sql_document` | 63 | 3 | 81% | 2,578 | 2.5 | 12,215 | 1,447 | $0.0122 | $0.0102 | 8.5 | 0 |
| corpus-a | `vector_only` | 63 | 3 | 87% (86-90) | 6,069 | 1.5 | 7,899 | 3,025 | $0.0158 | $0.0111 | 5.8 | 0 |
| corpus-a | `both` | 63 | 3 | 86% | 4,443 | 2.0 | 11,214 | 2,132 | $0.0139 | $0.0119 | 6.4 | 0 |
| corpus-b | `sql_narrow` | 63 | 3 | 89% (86-90) | 11,713 | 2.7 | 17,933 | 4,615 | $0.0267 | $0.0127 | 7.5 | 0 |
| corpus-b | `sql_document` | 63 | 3 | 94% (90-95) | 11,270 | 2.7 | 20,855 | 3,482 | $0.0231 | $0.0116 | 6.4 | 0 |
| corpus-b | `vector_only` | 63 | 3 | 89% (86-90) | 20,180 | 1.7 | 14,262 | 6,531 | $0.0312 | $0.0200 | 6.3 | 0 |
| corpus-b | `both` | 63 | 3 | 92% (90-95) | 13,189 | 2.7 | 17,805 | 4,047 | $0.0241 | $0.0209 | 7.4 | 0 |

### The projection test

| corpus | model | narrow acc | narrow bytes | document acc | document bytes | vector acc | vector bytes | vector/narrow | vector/document |
|---|---|---|---|---|---|---|---|---|---|
| corpus-a | haiku | 90% (86-95) | 4,405 | 84% (81-86) | 2,924 | 86% | 5,612 | 1.3x | 1.9x |
| corpus-a | sonnet | 86% | 3,032 | 81% | 2,578 | 87% (86-90) | 6,069 | 2.0x | 2.4x |
| corpus-b | haiku | 95% | 18,580 | 89% (86-95) | 16,913 | 84% (81-86) | 17,694 | 1.0x | 1.0x |
| corpus-b | sonnet | 89% (86-90) | 11,713 | 94% (90-95) | 11,270 | 89% (86-90) | 20,180 | 1.7x | 1.8x |

### corpus-a vs corpus-b, per stratum, per condition (pooled)

| stratum | condition | corpus-a | corpus-b | b - a |
|---|---|---|---|---|
| exact_lookup | `sql_narrow` | 100% | 100% | +0 pp |
| exact_lookup | `sql_document` | 100% | 100% | +0 pp |
| exact_lookup | `vector_only` | 100% | 100% | +0 pp |
| exact_lookup | `both` | 100% | 100% | +0 pp |
| paraphrase | `sql_narrow` | 100% | 88% (75-100) | -12 pp |
| paraphrase | `sql_document` | 83% (75-88) | 92% (88-100) | +8 pp |
| paraphrase | `vector_only` | 100% | 100% | +0 pp |
| paraphrase | `both` | 100% | 100% | +0 pp |
| multi_hop | `sql_narrow` | 100% | 100% | +0 pp |
| multi_hop | `sql_document` | 100% | 100% | +0 pp |
| multi_hop | `vector_only` | 100% | 92% (75-100) | -8 pp |
| multi_hop | `both` | 100% | 100% | +0 pp |
| temporal | `sql_narrow` | 100% | 100% | +0 pp |
| temporal | `sql_document` | 100% | 100% | +0 pp |
| temporal | `vector_only` | 100% | 100% | +0 pp |
| temporal | `both` | 100% | 100% | +0 pp |
| negative | `sql_narrow` | 100% | 100% | +0 pp |
| negative | `sql_document` | 100% | 100% | +0 pp |
| negative | `vector_only` | 100% | 100% | +0 pp |
| negative | `both` | 100% | 92% (75-100) | -8 pp |
| scope_restricted | `sql_narrow` | 100% | 100% | +0 pp |
| scope_restricted | `sql_document` | 100% | 100% | +0 pp |
| scope_restricted | `vector_only` | 75% | 75% | +0 pp |
| scope_restricted | `both` | 100% | 83% (75-100) | -17 pp |
| reconcile | `sql_narrow` | 50% (40-60) | 77% (70-90) | +27 pp |
| reconcile | `sql_document` | 40% | 70% (60-80) | +30 pp |
| reconcile | `vector_only` | 53% (50-60) | 57% (50-60) | +3 pp |
| reconcile | `both` | 43% (40-50) | 63% (60-70) | +20 pp |

### corpus-a vs corpus-b, per stratum -- haiku

| stratum | condition | corpus-a | corpus-b | b - a |
|---|---|---|---|---|
| exact_lookup | `sql_narrow` | 100% | 100% | +0 pp |
| exact_lookup | `sql_document` | 100% | 100% | +0 pp |
| exact_lookup | `vector_only` | 100% | 100% | +0 pp |
| exact_lookup | `both` | 100% | 100% | +0 pp |
| paraphrase | `sql_narrow` | 100% | 92% (75-100) | -8 pp |
| paraphrase | `sql_document` | 92% (75-100) | 100% | +8 pp |
| paraphrase | `vector_only` | 100% | 100% | +0 pp |
| paraphrase | `both` | 100% | 100% | +0 pp |
| multi_hop | `sql_narrow` | 100% | 100% | +0 pp |
| multi_hop | `sql_document` | 100% | 100% | +0 pp |
| multi_hop | `vector_only` | 100% | 83% (50-100) | -17 pp |
| multi_hop | `both` | 100% | 100% | +0 pp |
| temporal | `sql_narrow` | 100% | 100% | +0 pp |
| temporal | `sql_document` | 100% | 100% | +0 pp |
| temporal | `vector_only` | 100% | 100% | +0 pp |
| temporal | `both` | 100% | 100% | +0 pp |
| negative | `sql_narrow` | 100% | 100% | +0 pp |
| negative | `sql_document` | 100% | 100% | +0 pp |
| negative | `vector_only` | 100% | 100% | +0 pp |
| negative | `both` | 100% | 83% (50-100) | -17 pp |
| scope_restricted | `sql_narrow` | 100% | 100% | +0 pp |
| scope_restricted | `sql_document` | 100% | 100% | +0 pp |
| scope_restricted | `vector_only` | 50% | 50% | +0 pp |
| scope_restricted | `both` | 100% | 67% (50-100) | -33 pp |
| reconcile | `sql_narrow` | 60% (40-80) | 87% (80-100) | +27 pp |
| reconcile | `sql_document` | 40% | 53% (40-80) | +13 pp |
| reconcile | `vector_only` | 60% | 60% | +0 pp |
| reconcile | `both` | 47% (40-60) | 60% | +13 pp |

### corpus-a vs corpus-b, per stratum -- sonnet

| stratum | condition | corpus-a | corpus-b | b - a |
|---|---|---|---|---|
| exact_lookup | `sql_narrow` | 100% | 100% | +0 pp |
| exact_lookup | `sql_document` | 100% | 100% | +0 pp |
| exact_lookup | `vector_only` | 100% | 100% | +0 pp |
| exact_lookup | `both` | 100% | 100% | +0 pp |
| paraphrase | `sql_narrow` | 100% | 83% (75-100) | -17 pp |
| paraphrase | `sql_document` | 75% | 83% (75-100) | +8 pp |
| paraphrase | `vector_only` | 100% | 100% | +0 pp |
| paraphrase | `both` | 100% | 100% | +0 pp |
| multi_hop | `sql_narrow` | 100% | 100% | +0 pp |
| multi_hop | `sql_document` | 100% | 100% | +0 pp |
| multi_hop | `vector_only` | 100% | 100% | +0 pp |
| multi_hop | `both` | 100% | 100% | +0 pp |
| temporal | `sql_narrow` | 100% | 100% | +0 pp |
| temporal | `sql_document` | 100% | 100% | +0 pp |
| temporal | `vector_only` | 100% | 100% | +0 pp |
| temporal | `both` | 100% | 100% | +0 pp |
| negative | `sql_narrow` | 100% | 100% | +0 pp |
| negative | `sql_document` | 100% | 100% | +0 pp |
| negative | `vector_only` | 100% | 100% | +0 pp |
| negative | `both` | 100% | 100% | +0 pp |
| scope_restricted | `sql_narrow` | 100% | 100% | +0 pp |
| scope_restricted | `sql_document` | 100% | 100% | +0 pp |
| scope_restricted | `vector_only` | 100% | 100% | +0 pp |
| scope_restricted | `both` | 100% | 100% | +0 pp |
| reconcile | `sql_narrow` | 40% | 67% (60-80) | +27 pp |
| reconcile | `sql_document` | 40% | 87% (80-100) | +47 pp |
| reconcile | `vector_only` | 47% (40-60) | 53% (40-60) | +7 pp |
| reconcile | `both` | 40% | 67% (60-80) | +27 pp |

### Temporal, by supersession mechanism

| mechanism | corpus | `sql_narrow` | `sql_document` | `vector_only` | `both` |
|---|---|---|---|---|---|
| `T-a` | corpus-a | 100% | 100% | 100% | 100% |
| `TB-a` | corpus-b | 100% | 100% | 100% | 100% |
| `TB-b` | corpus-b | 100% | 100% | 100% | 100% |

### Reconcile, by discriminator

| mechanism | corpus | `sql_narrow` | `sql_document` | `vector_only` | `both` |
|---|---|---|---|---|---|
| `R-content` | corpus-a | 17% (0-33) | 0% | 22% (17-33) | 6% (0-17) |
| `R-recency` | corpus-a | 100% | 100% | 100% | 100% |
| `R-content` | corpus-b | 61% (50-83) | 50% (33-67) | 28% (17-33) | 39% (33-50) |
| `R-recency` | corpus-b | 100% | 100% | 100% | 100% |

### Reconcile, by discriminator -- haiku

| mechanism | corpus | `sql_narrow` | `sql_document` | `vector_only` | `both` |
|---|---|---|---|---|---|
| `R-content` | corpus-a | 33% (0-67) | 0% | 33% | 11% (0-33) |
| `R-recency` | corpus-a | 100% | 100% | 100% | 100% |
| `R-content` | corpus-b | 78% (67-100) | 22% (0-67) | 33% | 33% |
| `R-recency` | corpus-b | 100% | 100% | 100% | 100% |

### Reconcile, by discriminator -- sonnet

| mechanism | corpus | `sql_narrow` | `sql_document` | `vector_only` | `both` |
|---|---|---|---|---|---|
| `R-content` | corpus-a | 0% | 0% | 11% (0-33) | 0% |
| `R-recency` | corpus-a | 100% | 100% | 100% | 100% |
| `R-content` | corpus-b | 44% (33-67) | 78% (67-100) | 22% (0-33) | 44% (33-67) |
| `R-recency` | corpus-b | 100% | 100% | 100% | 100% |

### Variance: every cell, every seed

| corpus | model | condition | seed 1 | seed 2 | seed 3 | mean (range) |
|---|---|---|---|---|---|---|
| corpus-a | haiku | `sql_narrow` | 19/21 | 20/21 | 18/21 | 90% (86-95) |
| corpus-a | haiku | `sql_document` | 17/21 | 18/21 | 18/21 | 84% (81-86) |
| corpus-a | haiku | `vector_only` | 18/21 | 18/21 | 18/21 | 86% |
| corpus-a | haiku | `both` | 18/21 | 19/21 | 18/21 | 87% (86-90) |
| corpus-a | sonnet | `sql_narrow` | 18/21 | 18/21 | 18/21 | 86% |
| corpus-a | sonnet | `sql_document` | 17/21 | 17/21 | 17/21 | 81% |
| corpus-a | sonnet | `vector_only` | 19/21 | 18/21 | 18/21 | 87% (86-90) |
| corpus-a | sonnet | `both` | 18/21 | 18/21 | 18/21 | 86% |
| corpus-b | haiku | `sql_narrow` | 20/21 | 20/21 | 20/21 | 95% |
| corpus-b | haiku | `sql_document` | 20/21 | 18/21 | 18/21 | 89% (86-95) |
| corpus-b | haiku | `vector_only` | 18/21 | 17/21 | 18/21 | 84% (81-86) |
| corpus-b | haiku | `both` | 17/21 | 18/21 | 19/21 | 86% (81-90) |
| corpus-b | sonnet | `sql_narrow` | 19/21 | 19/21 | 18/21 | 89% (86-90) |
| corpus-b | sonnet | `sql_document` | 19/21 | 20/21 | 20/21 | 94% (90-95) |
| corpus-b | sonnet | `vector_only` | 18/21 | 19/21 | 19/21 | 89% (86-90) |
| corpus-b | sonnet | `both` | 20/21 | 19/21 | 19/21 | 92% (90-95) |

### Tool preference in `both`

| corpus | model | runs | opened with `search` | opened with `query` | used both |
|---|---|---|---|---|---|
| corpus-a | haiku | 63 | 95% | 5% | 30% |
| corpus-a | sonnet | 63 | 84% | 16% | 48% |
| corpus-b | haiku | 63 | 95% | 5% | 32% |
| corpus-b | sonnet | 63 | 86% | 14% | 59% |

### Tool-call errors

| corpus | condition | errors | calls | rate | message |
|---|---|---|---|---|---|
| corpus-a | `sql_document` | 38 | 330 | 11.5% | this session returns whole pages, so your SELECT mus |
| corpus-b | `sql_document` | 32 | 366 | 8.7% | this session returns whole pages, so your SELECT mus |
| corpus-a | `sql_document` | 13 | 330 | 3.9% | SQL error: no such column: path |
| corpus-a | `sql_narrow` | 12 | 351 | 3.4% | only one statement per call |
| corpus-b | `sql_document` | 9 | 366 | 2.5% | SQL error: no such column: path |
| corpus-b | `sql_narrow` | 5 | 362 | 1.4% | only one statement per call |
| corpus-b | `both` | 4 | 357 | 1.1% | SQL error: no such column: path |
| corpus-a | `both` | 1 | 296 | 0.3% | SQL error: no such column: path |
| corpus-a | `sql_narrow` | 1 | 351 | 0.3% | SQL error: no such column: body |
| corpus-a | `both` | 1 | 296 | 0.3% | SQL error: no such column: updated |

### Failures

| corpus | qid | stratum | condition | model | verdict | seeds | gold | example answer |
|---|---|---|---|---|---|---|---|---|
| corpus-a | PA02 | paraphrase | `sql_document` | sonnet | wrong | 3/3 | AWS | NOT FOUND |
| corpus-a | RC03 | reconcile | `sql_narrow` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `both` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `vector_only` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `sql_document` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `sql_document` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `vector_only` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `sql_narrow` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC03 | reconcile | `both` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-a | RC04 | reconcile | `vector_only` | haiku | wrong | 3/3 | Hemfrid | Stadpartner Vast |
| corpus-a | RC04 | reconcile | `sql_document` | haiku | wrong | 3/3 | Hemfrid | Stadpartner Vast |
| corpus-a | RC04 | reconcile | `both` | haiku | wrong | 3/3 | Hemfrid | Stadpartner Vast |
| corpus-a | RC04 | reconcile | `vector_only` | sonnet | wrong | 3/3 | Hemfrid | Stadpartner Vast |
| corpus-a | RC04 | reconcile | `both` | sonnet | wrong | 3/3 | Hemfrid | NOT FOUND (conflicting active records: h |
| corpus-a | RC04 | reconcile | `sql_document` | sonnet | wrong | 3/3 | Hemfrid | Stadpartner Väst |
| corpus-a | RC04 | reconcile | `sql_narrow` | sonnet | wrong | 3/3 | Hemfrid | Stadpartner Väst |
| corpus-a | RC05 | reconcile | `sql_document` | haiku | wrong | 3/3 | Cykelkraft | Velo Verkstad in Olskroken |
| corpus-a | RC05 | reconcile | `sql_narrow` | sonnet | wrong | 3/3 | Cykelkraft | Velo Verkstad (in Olskroken) |
| corpus-a | RC05 | reconcile | `sql_document` | sonnet | wrong | 3/3 | Cykelkraft | Velo Verkstad (in Olskroken) |
| corpus-a | RC05 | reconcile | `both` | sonnet | wrong | 3/3 | Cykelkraft | Velo Verkstad (in Olskroken) |
| corpus-a | SR05 | scope_restricted | `vector_only` | haiku | wrong | 3/3 | not found |  |
| corpus-b | RC03 | reconcile | `both` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-b | RC03 | reconcile | `vector_only` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-b | RC03 | reconcile | `sql_document` | haiku | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-b | RC03 | reconcile | `both` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-b | RC03 | reconcile | `vector_only` | sonnet | wrong | 3/3 | Kafferosteriet Kaj | Bonor och Bryggd |
| corpus-b | SR05 | scope_restricted | `vector_only` | haiku | wrong | 3/3 | not found |  |
| corpus-a | RC05 | reconcile | `sql_narrow` | haiku | wrong | 2/3 | Cykelkraft | Velo Verkstad in Olskroken |
| corpus-a | RC05 | reconcile | `both` | haiku | wrong | 2/3 | Cykelkraft | Velo Verkstad in Olskroken |
| corpus-a | RC05 | reconcile | `vector_only` | sonnet | wrong | 2/3 | Cykelkraft | Velo Verkstad (in Olskroken) |

### Totals

```json
{
  "runs": 1008,
  "by_shape": {
    "corpus-a": 504,
    "corpus-b": 504
  },
  "by_model": {
    "haiku": 504,
    "sonnet": 504
  },
  "seeds": [
    1,
    2,
    3
  ],
  "tool_calls": 2569,
  "tool_errors": 116,
  "judged_by_rule": 903,
  "agent_cost_usd": 19.0847,
  "judge_cost_usd": 0.2911,
  "total_cost_usd": 19.3757
}
```
