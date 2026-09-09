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

### 3.4 Two ablations: isolating the join

Two follow-up sweeps (30 runs each, temporal stratum only) test whether the
`supersedes` join carries any weight of its own.

| mechanism | condition | baseline | − `relations` | − `relations`, − recency |
|---|---|---|---|---|
| **T-a** chase the edge | `sql_only` | 4/4 | 4/4 | **4/4** |
| | `vector_only` | 4/4 | 4/4 | **1/4** |
| | `both` | 4/4 | 4/4 | **4/4** |
| T-b windows *(control)* | all three | 3/3 | 3/3 | 3/3 |
| T-c override *(control)* | all three | 3/3 | 3/3 | 3/3 |

**Ablation 1 — withhold the edge from search output** (`--hide-relations`).
No effect: `vector_only` still scored 4/4. The transcripts say why:

> "Two conflicting active entries exist, but the more recently updated one
> (2026-08-02, higher confidence 0.95) supersedes the older one
> (2025-06-14, confidence 0.9)."

Supersession was encoded **three times over** — as the edge, as a later
`updated`, and as a higher `confidence`. The latter two are co-located
scalars sitting in frontmatter that any retrieval path returns. The join was
never necessary, so the baseline T-a column never measured a join. That is a
defect in my corpus, not a property of the retrieval methods.

**Ablation 2 — also remove the recency signal** (`--flat-supersession`:
both pages get identical `updated` and `confidence`). Now the edge is the
only discriminator, and the *superseded* page ranks higher by cosine
(0.6773 vs 0.6412), so taking the top hit is actively wrong.

`vector_only` collapses to **1/4**. It fails honestly rather than
confabulating — "NOT FOUND (conflicting records: both appear as current with
identical metadata)" — which is the right behaviour given what it can see,
but it is still a miss. `sql_only` holds at 4/4 by doing the anti-join.
`both` also holds at 4/4, and the logs show it reaching for `query` in
**all four** runs after search returned an ambiguous pair.

Two caveats on this table. The one T-a question `vector_only` still passed
(TP02) it passed for the wrong reason: the corpus separately tags Petra
Hallgren as "manager" and Olu Adeyemi as "colleague" on their people pages,
so a corroborating signal survived the ablation. And n = 4 per cell; the
direction is unambiguous, the magnitude is not.

**So the join asymmetry is real and large — but only visible once
supersession stops being redundantly encoded.** Whether real exported memory
is redundant in that way is the single most important thing a follow-up must
establish (§5).

---

## 4. Cost and data volume

This is where the conditions actually differ, and it is consistent across
all 60 questions rather than resting on a handful.

| | `sql_only` | `vector_only` | ratio |
|---|---|---|---|
| Result bytes returned per run | 1,684 | 6,400 | **3.8×** |
| Result bytes per tool call | 665 | 3,692 | **5.5×** |
| Cache-creation tokens per run | 1,842 | 4,805 | 2.6× |
| Median cost per run | $0.0113 | $0.0178 | **1.6×** |
| Median latency | 5.1 s | 6.1 s | 1.2× |
| Mean tool calls | 2.5 | 1.7 | 0.7× |

SQL makes *more* calls but each returns far less: it asks for the columns it
wants, while search returns whole page bodies for every hit. In a personal
memory server where the retrieval result is prepended to every conversation
turn, a 3.8× difference in context consumed is the dominant operational
number — larger than any accuracy difference this spike could detect.

---

## 5. Where the synthetic corpus could bias the result

Named honestly, worst first.

1. **The benchmark ceilings out.** Five of six strata are at 100% for all
   three conditions. Nothing about accuracy can be concluded. A useful
   version needs harder questions, a larger corpus, or a weaker model.
2. **Supersession was redundantly encoded** (§3.4). This *inflated*
   `vector_only`'s baseline temporal score to a perfect 4/4 that collapsed
   to 1/4 once the redundancy was removed. Any generator that stamps newer
   facts with newer timestamps will hide the join requirement.
3. **The corpus is internally consistent in ways real memory is not.**
   Because pages are rendered from shared entity tables, a fact often
   appears with corroborating detail elsewhere (TP02). Real memory
   contradicts itself and leaves facts unsupported.
4. **Paraphrase disjointness is total, not partial.** Real questions overlap
   their target pages *somewhat*. Engineering zero overlap makes the
   paraphrase stratum maximally favourable to embeddings; partial overlap
   would let SQL `LIKE` and BM25 recover more than measured here.
5. **Pages are short and structurally uniform** — one to three
   template-generated sentences. Long, heterogeneous pages change both
   methods: vector needs chunking, `LIKE` gets noisier.
6. **The taxonomy is unrealistically clean.** Every page has exactly one
   domain from a nine-value enum and tidy tags. `sql_only`'s exploration
   strategy leaned on `WHERE domain = ...`; real memory may have no reliable
   categorisation to filter on.
7. **The SQL condition's system prompt is hand-written.** A worse schema
   document would lower `sql_only` and the spike cannot separate "SQL is
   good" from "this schema doc is good".
8. **Scope enforcement is structural**, so zero leaks tests only the model's
   restraint, not the storage layer. A deployment that filters at query time
   has a failure mode this design cannot exhibit.
9. **One persona, one seed, one model (Sonnet), no repeats.** There is no
   variance estimate. The 57/58/58 split is one draw.

### What a follow-up on real exported memory should check

- **Is supersession redundantly encoded?** Do `updated` timestamps track
  currency, or does bulk import stamp everything with the import date? If
  timestamps are unreliable, the `supersedes` edge — and the join — becomes
  load-bearing, and §3.4's decisive column is the one that matters.
- **What is the real lexical gap** between how a person asks and how their
  memory was written? Measure token overlap on actual query/page pairs
  rather than assuming either extreme.
- **Page length and structure distribution**, which decides whether vector
  retrieval needs chunking at all.
- **Does a usable taxonomy exist**, or must domains and tags be inferred
  before any SQL view can be curated?
- **Scale.** 547 pages is small enough that a full `LIKE` scan is free. At
  10k+ pages both the SQL plan and vector recall change.
- **Leak behaviour under query-time filtering**, not structural isolation.

---

## 6. Recommendation

**SQL-over-views becomes the primary retrieval path for MultiPass.
Embeddings stay, as an explicitly secondary fallback. Do not expose the two
as peer tools.**

Not softened, and stated against the evidence:

- **Accuracy does not decide this.** 57 / 58 / 58 with three discordant
  pairs is a tie. Anyone claiming SQL "wins" or "loses" on these numbers is
  reading noise. `vector_only` is nominally one question ahead.
- **SQL wins the operational argument outright**: 3.8× less context per run
  and ~37% lower cost, sustained across all 60 questions. For a server whose
  retrieval output is injected into every turn, that is the number that
  compounds.
- **SQL wins the one capability difference that is real.** Once supersession
  stops being redundantly encoded, `sql_only` scores 4/4 and `vector_only`
  1/4. Personal memory is exactly the domain where facts get replaced —
  jobs, addresses, medications, phone numbers — so this is not an exotic
  case.
- **Embeddings earn their keep on paraphrase**, and only there. They reached
  *the kora* and *the chestnut tree*, which SQL missed; SQL reached
  *Tallyho*, which they missed. The union is 9/10 against 7/10 and 8/10
  alone. Dropping embeddings entirely would cost real recall when a person
  asks about their memory in words that do not appear in it.
- **The talk's prescription — remove the vector tool — is not supported
  here.** `both` matched `vector_only` overall (58/60) and matched
  `sql_only` on the decisive join ablation (4/4), because it fell back to
  `query` in all four runs once search returned an ambiguous pair. Removing
  the vector tool would have cost paraphrase recall and bought nothing.
- **But the talk's *observation* reproduces exactly, and it constrains the
  design.** Given both tools as peers the agent opened with `search` in 92%
  of runs, and on the temporal stratum used `query` in only 2 of 10. Left to
  choose freely it will not reach for SQL. So: make `memory.query` the
  documented primary, and expose semantic search as a narrower, named
  fallback ("use when a keyword and domain search has returned nothing"),
  rather than as an equal sibling.

The honest summary is that this spike **did not find the accuracy difference
it went looking for**, found a clear efficiency difference, and found one
real capability difference that only became visible after an ablation
exposed a flaw in the corpus.

---

## 7. Reproduction and logs

```bash
cd spikes/sql-vs-vector
./run.sh                    # first pass: 60 x 3 x sonnet x 1 seed = 180 runs
./run.sh --full             # adds haiku and a second seed
./run.sh --embeddings none  # BM25 only, for environments without HF egress
```

Ablations:

```bash
python -m pcp_spike.runner --strata temporal --hide-relations --tag ablation-norel
python -m pcp_spike.build  --flat-supersession        # rebuild without the recency signal
python -m pcp_spike.runner --strata temporal --hide-relations --tag ablation-join
python -m pcp_spike.build                             # restore the canonical corpus
```

Everything is seeded; the corpus is byte-identical between runs.

| Artefact | Path |
|---|---|
| First-pass runs (180) | `logs/raw/runs-first-pass.jsonl` |
| First-pass verdicts | `logs/raw/judged-first-pass.jsonl` |
| Ablation 1 (− relations) | `logs/raw/runs-ablation-norel.jsonl`, `judged-ablation-norel.jsonl` |
| Ablation 2 (− relations, − recency) | `logs/raw/runs-ablation-join.jsonl`, `judged-ablation-join.jsonl` |
| Generated tables | `logs/results-first-pass.md` |
| Corpus + ground truth | `corpus/pages/`, `corpus/manifest.json` |
| Questions | `questions/questions.json` |

Each run record carries the full transcript, every tool call with its result
byte count and any error, and measured `input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`,
`total_cost_usd` and `duration_ms`.

**Totals:** 240 agent runs (180 first pass + 30 + 30 ablation), 501 tool
calls, **$4.82** in model spend ($4.16 agents + $0.65 judge).

Four tool errors in 501 calls (0.8%), none of them a harness fault: two were
the guard refusing a multi-statement query, and two were the agent writing
SQL against a column that does not exist (`path` on the profile table,
a mistyped `tags_check`). All four were recovered from in the same run. The
model never hit the statement timeout or the row/byte caps.

Environment probes and the spec-reconciliation decisions are in
[`NOTES.md`](NOTES.md).
