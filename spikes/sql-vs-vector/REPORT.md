# SQL-over-views vs. embedding retrieval for PCP personal memory

**Spike result, first pass.** 60 questions × 3 conditions × Sonnet × 1 seed
= 180 runs, plus a 30-run ablation. Corpus: 547 synthetic PCP memory pages.

---

## 1. The short answer

**On accuracy, this experiment cannot tell the three conditions apart.**
95% / 97% / 97% is 57, 58 and 58 correct out of 60. Paired per-question
comparison of `sql_only` against `vector_only` yields **three discordant
pairs** (SQL alone right on 1, vector alone right on 2); exact two-sided
McNemar p = 1.0. Five of the six strata sit at 100% for every condition.
The benchmark ceilings out, and no accuracy claim in either direction is
supportable from it.

**The talk's first claim reproduces cleanly; its second does not.** Given
both tools, the agent opened with `search` in **92%** of runs, and on the
temporal stratum — the one built around a join — it used `search` 10/10 and
`query` only 2/10. It does reach for vector search. But it did not thereby
do worse: `both` tied `vector_only` and edged `sql_only`. **Removing the
vector tool did not improve results here.**

**What does separate the conditions is cost and data volume.** At
indistinguishable accuracy, SQL returned **1,684 bytes per run against
vector's 6,400** (665 vs 3,692 bytes per tool call) and cost **$0.0113 per
run against $0.0178** (median). That is a ~3.8× difference in context
consumed and a ~37% difference in price, sustained across the whole set.

**Recommendation: SQL-over-views becomes the primary retrieval path for
MultiPass; keep embeddings as a secondary, explicitly-subordinate fallback.
Do not expose the two as peer tools.** Reasoning in §6.

---

## 2. What was tested

| | |
|---|---|
| Corpus | 547 pages generated from typed `Fact` records, one synthetic persona, 9 domains. Deliberate noise: 45 near-duplicates, supersession pairs, validity windows, contradictions, and 10 pages whose wording shares **zero** content tokens with the questions targeting them. |
| Profile | `profile.core` + four extension namespaces (`pcp.health`, `pcp.finance`, `pcp.home`, `pcp.legal`), per SPEC.md §4. |
| Storage | WordPress-shaped schema (`wp_posts` / `wp_postmeta` EAV / term tables), with curated flattened views over it, one view set per scope bundle. |
| Scope enforcement | **Structural.** Each bundle's views are materialised into their own SQLite file; the harness opens exactly one, read-only. A scope leak cannot be a query bug — only the model asserting something it was never shown. |
| Retrieval | Brute-force cosine over a local `all-MiniLM-L6-v2` embeddings table (no ANN). BM25 built as an extra backend. |
| Conditions | `sql_only` (query, schema in the system prompt), `vector_only` (search), `both`. |
| Model | Sonnet. Judge: Haiku, with a deterministic pre-stage for refusals. |

Both backends apply the same scope filter, the same SPEC.md §5.2 default
policy (only `active`/`validated`, current-or-undated pages), and the same
opt-in override (`memory_all` / `include_stale`). Neither condition has a
filtering power the other lacks.

### The three temporal mechanisms

The §5.2 default filter already hides stale and expired pages, so a question
that filter answers on its own is an exact lookup wearing a date. Every
temporal question therefore requires one of:

| | Mechanism | Why the default filter cannot do it |
|---|---|---|
| **T-a** (4 q) | Chase a `supersedes` relation | Both pages are `active` and current, so both survive the filter. Only the edge discriminates. |
| **T-b** (3 q) | Choose between overlapping validity windows | Both windows are current; correctness is interval containment. |
| **T-c** (3 q) | Use the opt-in override | The answer is a historical fact on a hidden page. |

Supersession is modelled exactly as SPEC.md §5.1 specifies — a `supersedes`
relations edge, **not** an extended `lifecycle` enum. Rationale in
[`NOTES.md`](NOTES.md) §2.1.

---

## 3. Results

### 3.1 Overall

| condition | n | accuracy | correct | partial | wrong | leak | mean tool calls | mean result bytes | median latency | median cost/run |
|---|---|---|---|---|---|---|---|---|---|---|
| `sql_only` | 60 | 95% | 57 | 0 | 3 | **0** | 2.5 | 1,684 | 5.1 s | $0.0113 |
| `vector_only` | 60 | 97% | 58 | 0 | 2 | **0** | 1.7 | 6,400 | 6.1 s | $0.0178 |
| `both` | 60 | 97% | 58 | 0 | 2 | **0** | 2.3 | 5,256 | 6.1 s | $0.0151 |

Token counts, cost and latency are **measured**, not estimated — the
`claude-agent-sdk` `ResultMessage` exposes `usage`, `total_cost_usd` and
`duration_ms`. Mean input tokens (all classes summed): 9,129 / 8,261 /
11,357. Cost is driven by cache-creation tokens, where vector's bulky
results land: 1,842 / 4,805 / 3,471.

### 3.2 By stratum

| stratum | `sql_only` | `vector_only` | `both` |
|---|---|---|---|
| exact_lookup | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| paraphrase | 70% (7/10) | 80% (8/10) | 80% (8/10) |
| multi_hop | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| temporal | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| negative | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| scope_restricted | 100% (10/10) | 100% (10/10) | 100% (10/10) |

**Zero leaks in 180 runs.** Every scope-restricted question was correctly
refused by every condition, despite each having an oblique trace in scope —
a named clinician with no condition, a "weekly tablet" reminder with no
drug, a neighbour who holds keys with no statement that he holds them. The
model did not infer across the gap. Given structural enforcement this tests
the model's restraint, not the storage layer, and the model was restrained.

**Paraphrase is the only stratum that separates anything**, and the split is
more interesting than the totals:

| | PA01 | PA02 | PA03 | PA04 | PA05 | PA06 | PA07 | PA08 | PA09 | PA10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `sql_only` | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ |
| `vector_only` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ |
| `both` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ |

They fail on **different questions**. SQL missed *the kora* and *the
chestnut tree* — cases where guessing the right `LIKE` term is the whole
problem. Vector missed *Tallyho*, which SQL found. The union of what either
reaches is **9/10**; `both` scored 8/10, because having reached for search
and got a plausible-looking result set, it did not fall back to SQL. The
complementarity is real and the agent does not exploit it.

### 3.3 Temporal, by mechanism

| mechanism | `sql_only` | `vector_only` | `both` |
|---|---|---|---|
| T-a chase a `supersedes` edge | 100% (4/4) | 100% (4/4) | 100% (4/4) |
| T-b overlapping validity windows | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| T-c opt-in override | 100% (3/3) | 100% (3/3) | 100% (3/3) |

All three conditions took the opt-in override on 3/3 T-c questions.

**T-a did not test what it was built to test, and the fault is in my tool
design.** `search` returns each hit's frontmatter, and frontmatter includes
`relations`. When both pages of a supersession pair land in one result set —
which they do, being near-identical in topic — the vector condition is
**handed the edge inline** and never performs a join:

```
### 2. work/role-principal-data-engineer  (score 0.6412)
  ...
  relations: [{'rel': 'supersedes', 'target': 'work/role-senior-data-engineer', ...}]
```

`sql_only` genuinely did the join (`SELECT * FROM relations WHERE
target_page IN (...)`). `vector_only` read the answer off the page. That is
a fair reflection of what a spec-conformant `memory.search` would return —
§5.1 makes `relations` frontmatter — but it means **the join asymmetry only
exists when the edge is not co-located with the retrieved rows.**

