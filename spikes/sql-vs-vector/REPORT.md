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

---

# Second pass — realistic corpus shape, variance, and the projection risk

**Read §8 before acting on §1–§6.** The first pass measured a 3.8× context
advantage for SQL and a ~37% cost advantage. Neither survives this pass
intact: the byte advantage falls to **1.25×**, and the cost advantage is not
reproducible at all — its ordering flips with the corpus, the model, and
whether you take the mean or the median. §8.6 rules on every first-pass claim
individually.

**Second-pass result.** 21 questions × 4 conditions × 2 corpora × 2 models ×
**3 seeds = 1,008 runs**, $19.38. Every accuracy figure below is
`mean% (min–max)` across seeds.

---

## 8. What changed, and why

### 8.1 The finding that motivated this pass

Two real memory stores were inspected: a Notion-backed store (NAPSAC) and a
native per-user memory filesystem. Between them they contain **zero explicit
supersession structure** — no `supersedes` edges, no lifecycle field, no
per-fact confidence, `valid_from` or `updated`. One file-level timestamp per
file, many facts per file.

Supersession appears only as:

| | form | example |
|---|---|---|
| **(a)** | tense plus a date inside a single line | "Omnisend was a client in 2025" |
| **(b)** | prose cues across lines of the same file | "Ruled out both candidates below; now looking at X" … later … "Previously compared two X…" |
| **(c)** | not at all | a whole file silently stale, contradicted by a newer file elsewhere, with nothing linking them |

corpus-a — the first pass's design, rebuilt at 2,000 pages — models
supersession exactly as SPEC.md §5.1 does, as a typed edge. That is what PCP
specifies. It is not what either store looks like. corpus-b is what they look
like. The whole pass is the difference between those two.

### 8.2 What was built

| | corpus-a (atomic) | corpus-b (subject) |
|---|---|---|
| Unit | one page = one fact | one page = one SUBJECT FILE |
| Size | 2,000 pages | 2,000 files, **32,869 bullets** (8–25, mean 16.4) |
| Frontmatter | full SPEC.md §5.1 | `title` + `updated` (+ `sensitivity`) |
| Supersession | `supersedes` relations edge | prose only: (a), (b), (c) |
| `relations` rows | 29 | **0** |
| Lifecycles | active 1,231 / stale 532 / archived 185 / validated 52 | **active 2,000** |
| `memory` vs `memory_all` | 1,283 vs 2,000 | **identical** — nothing is ever stale |
| Tags | curated | none — the directory is the taxonomy |

The first pass's 547-page corpus is **untouched** at `corpus/` + `data/`, and
`./run.sh` still reproduces it. Both corpora are generated from the same
`persona.py` tables, so the same 21 questions have the same gold answers in
both wherever a fact survives re-shaping.

Four conditions, not three:

| condition | what it grants |
|---|---|
| `sql_narrow` | `query`; the agent picks its own projection (the first pass's `sql_only`) |
| `sql_document` | `query`, but every matched row is expanded to the **whole page** containing it |
| `vector_only` | `search` |
| `both` | `sql_narrow`'s `query` + `search` |

A `lines(path, line_no, text)` view was added to both corpora so that "narrow
projection" is a real choice rather than a formality: in corpus-b a `LIKE`
matches one bullet out of sixteen, and the agent can return that bullet, or
the page, or anything between.

---

## 8.3 The projection test

**The question: does SQL keep its 3.8× context advantage once it has to
return enough surrounding text to be correct?**

**Answer: no. It keeps about a third of it, and on Haiku it keeps none.**

| corpus | model | narrow acc | narrow B | document acc | document B | vector acc | vector B | vector÷narrow | vector÷document |
|---|---|---|---|---|---|---|---|---|---|
| corpus-a | haiku | 90% (86-95) | 4,405 | 84% (81-86) | 2,924 | 86% | 5,612 | 1.27× | 1.92× |
| corpus-a | sonnet | 86% | 3,032 | 81% | 2,578 | 87% (86-90) | 6,069 | 2.00× | 2.35× |
| corpus-b | haiku | 95% | 18,580 | 89% (86-95) | 16,913 | 84% (81-86) | 17,694 | **0.95×** | **1.05×** |
| corpus-b | sonnet | 89% (86-90) | 11,713 | 94% (90-95) | 11,270 | 89% (86-90) | 20,180 | 1.72× | 1.79× |
| corpus-a | *pooled* | 88% (86-90) | 3,719 | 83% (81-83) | 2,751 | 87% (86-88) | 5,841 | 1.57× | 2.12× |
| corpus-b | *pooled* | 92% (90-93) | 15,147 | 91% (90-93) | 14,091 | 87% (86-88) | 18,937 | **1.25×** | **1.34×** |

The first pass measured **3.80×** (1,684 B vs 6,400 B) at 547 atomic pages.
That number decays twice, for two independent reasons:

1. **Scale alone costs most of it.** Same generator, same shape, 547 → 2,000
   pages: 3.80× → **1.57×**. At 547 pages a `LIKE` scan returns a handful of
   one-sentence pages. At 2,000 it returns dozens.
2. **Shape costs the rest.** 2,000 atomic pages → 2,000 subject files:
   1.57× → **1.25×**, and on Haiku to 0.95× — i.e. SQL returns *more* bytes
   than vector search does.

**On the brief's decision rule — "if `sql_document` matches `vector_only` on
both accuracy and bytes, the efficiency argument in §4 does not survive" —
the answer is split, and the split is the finding:**

- **Bytes: it does not survive.** 14,091 vs 18,937 pooled is 1.34×, and on
  Haiku 1.05× is a tie. A 1.3× difference does not carry an architectural
  recommendation; a 3.8× one does. **§4's efficiency argument is overturned
  as stated.**
- **Accuracy: `sql_document` is nominally ahead of `vector_only`** — 91%
  (90-93) vs 87% (86-88) on corpus-b — but 4 pp is inside this benchmark's
  ±5 pp seed noise (§8.5), so it is a lead, not a result. What is left of the
  case for SQL is therefore an *accuracy* argument this experiment cannot
  yet resolve, in place of an efficiency argument it has just lost. That is
  a materially weaker position than the one §4 and §6 stated.

### 8.3.1 The counterintuitive part: `sql_narrow` is the expensive arm

`sql_document` returns **fewer** bytes than `sql_narrow` in every cell —
2,751 vs 3,719 on corpus-a, 14,091 vs 15,147 on corpus-b. Forcing whole
documents made results *smaller*. The tool logs say why:

| corpus | condition | queries | that `SELECT` a whole `body` | that use `lines` |
|---|---|---|---|---|
| corpus-a | `sql_narrow` | 351 | **231 (66%)** | 8 (2%) |
| corpus-a | `sql_document` | 330 | 8 (2%) | 41 (12%) |
| corpus-b | `sql_narrow` | 362 | **263 (73%)** | 13 (4%) |
| corpus-b | `sql_document` | 366 | 15 (4%) | 45 (12%) |

**Given a free choice, the agent does not project narrowly.** In two thirds
to three quarters of its queries it asks for whole page bodies, and it
almost never touches the line-level view that would let it be narrow. The
first pass's small SQL results were not the agent exercising judgement about
projection — they were an artefact of a corpus where a page *was* one
sentence. Forcing document mode is what actually produces disciplined SQL,
because an agent that knows every match arrives in full writes
`SELECT path FROM memory WHERE body LIKE '%Kwame%'` instead of
`SELECT path, title, body FROM memory WHERE domain = 'work'`.

The contract has a price: `sql_document` rejected **11.5%** of corpus-a and
**8.7%** of corpus-b query calls for omitting the required `path` column.
All were recovered inside the same run, but they are turns spent.

### 8.3.2 Cost does not follow bytes, and its ordering is not stable

| corpus | model | `sql_narrow` | `sql_document` | `vector_only` |
|---|---|---|---|---|
| | | mean / median | mean / median | mean / median |
| corpus-a | haiku | $0.0164 / $0.0142 | $0.0154 / $0.0122 | **$0.0102 / $0.0065** |
| corpus-a | sonnet | $0.0150 / $0.0129 | **$0.0122** / $0.0102 | $0.0158 / **$0.0111** |
| corpus-b | haiku | $0.0246 / $0.0211 | $0.0245 / $0.0229 | **$0.0143 / $0.0071** |
| corpus-b | sonnet | $0.0267 / **$0.0127** | **$0.0231** / $0.0116 | $0.0312 / $0.0200 |

The first pass reported SQL **37% cheaper** than vector, quoting medians.
That claim does not hold as stated, and the reason is worth more than the
number: **the ordering flips depending on which corpus, which model, and
whether you take the mean or the median.**

- On Haiku, vector search is cheaper than either SQL arm by 38–42% on means
  and 55–70% on medians — a straight reversal of the first-pass result.
- On Sonnet, corpus-b, SQL is cheaper by 17% on means and **57% on medians**
  — the first-pass direction, larger than the first pass measured.
- On Sonnet, corpus-a, the two swap places between the mean ($0.0150 vs
  $0.0158, SQL cheaper) and the median ($0.0129 vs $0.0111, vector cheaper),
  because a handful of long vector runs drag the mean.

The mechanism is tool calls, not bytes: SQL averages 2.6–2.9 calls per run
against vector's 2.0, and every extra call re-caches the schema document, so
cost tracks turn count more than it tracks result size. **The §4 cost claim
is not reproducible as an unconditional statement**, and no version of it
should be quoted without naming a model and a statistic.

---

## 8.4 Breaking the ceiling

### 8.4.1 It broke, in exactly one place

| stratum | condition | corpus-a | corpus-b | b − a |
|---|---|---|---|---|
| exact_lookup | all four | 100% | 100% | +0 pp |
| paraphrase | `sql_narrow` | 100% | 88% (75-100) | −12 pp |
| paraphrase | `sql_document` | 83% (75-88) | 92% (88-100) | +8 pp |
| paraphrase | `vector_only` / `both` | 100% | 100% | +0 pp |
| multi_hop | `vector_only` | 100% | 92% (75-100) | −8 pp |
| multi_hop | others | 100% | 100% | +0 pp |
| temporal | all four | **100%** | **100%** | +0 pp |
| negative | `both` | 100% | 92% (75-100) | −8 pp |
| scope_restricted | `vector_only` | 75% | 75% | +0 pp |
| **reconcile** | `sql_narrow` | 50% (40-60) | 77% (70-90) | **+27 pp** |
| **reconcile** | `sql_document` | 40% | 70% (60-80) | **+30 pp** |
| **reconcile** | `vector_only` | 53% (50-60) | 57% (50-60) | +3 pp |
| **reconcile** | `both` | 43% (40-50) | 63% (60-70) | +20 pp |

The `scope_restricted` 75% is not a leak and not a wrong answer: all eight
failures are one question (SR05) on which the agent exhausted its 14-turn
budget and emitted no answer at all. §8.5.1 explains why that happens only to
the search-based conditions.

Five of seven strata still sit at 100%. Scaling to 2,000 pages, adding
partial paraphrase overlap and running Haiku **did not break the ceiling**.
Only the new stratum did — and only half of it.

### 8.4.2 Reconcile splits cleanly on whether `updated` can be trusted

| discriminator | corpus | `sql_narrow` | `sql_document` | `vector_only` | `both` |
|---|---|---|---|---|---|
| `R-recency` | corpus-a | 100% | 100% | 100% | 100% |
| `R-recency` | corpus-b | 100% | 100% | 100% | 100% |
| `R-content` | corpus-a | 17% (0-33) | **0%** | 22% (17-33) | 6% (0-17) |
| `R-content` | corpus-b | 61% (50-83) | 50% (33-67) | 28% (17-33) | 39% (33-50) |

`R-recency` — the current page has the later `updated` — is **100% for every
condition, both corpora, both models, all three seeds**. It is a solved
problem, and it is solved by the timestamp, not by the retrieval method.

`R-content` — the stale page carries the *later* `updated`, because it was
touched afterwards, and only a date stated inside the prose settles it — is
where everything falls apart. `sql_document` on corpus-a scored **0/18**.
The failure is identical across conditions and models:

> "The most recently updated page is `preferences/coffee-delivery` (updated
> 2026-06-02), which states: 'The coffee subscription runs with Bonor och
> Bryggd.' — ANSWER: Bonor och Bryggd"

The model finds both pages, notices they conflict, reaches for the file
timestamp, and is wrong. **When file mtime disagrees with the content, mtime
wins, in every condition.** No retrieval architecture in this experiment
protects against a stale file that was touched recently — because the
information needed is in the prose, and the metadata is louder.

**Subject files are measurably better here** (+20 to +30 pp for the SQL
arms), and the transcripts suggest why: when the contradicting sentence
arrives inside sixteen bullets of surrounding prose, the model reads prose,
and reads the in-body date with it —

> "`vehicles/bicycle-servicing` (updated 2025-12-20): 'Since 2026-02-01 the
> bikes go to Cykelkraft…' 2. `home/bike-workshop` (updated 2026-04-05):
> 'The bikes go to Velo Verkstad…'"

— whereas two one-line atomic pages differing only in a name leave nothing to
read except the metadata. The direction is consistent across all three
`R-content` questions and all four conditions; the magnitude rests on 3
questions × 6 runs per cell and should be treated as a lead, not a
measurement.

### 8.4.3 Temporal: prose replaced the edge at zero cost

**100% for every condition, both corpora, all three mechanisms**, including
`TB-b`, which was built so that the line a keyword search matches
(*"Previously compared two laptops: a MacBook Pro 14 and a Dell XPS 15"*)
names only superseded values, and the line that resolves it sits elsewhere in
the file. It did not defeat anything — because, per §8.3.1, the agent pulls
whole bodies anyway and never had to rely on the line it matched.

That is a real result and it cuts against the first pass: **corpus-b has zero
`supersedes` edges and scored 100% on the same four temporal questions
corpus-a answers with an edge.** The join was not needed.

### 8.4.4 Paraphrase overlap: measured, not asserted

The first pass engineered **zero** content-token overlap between a paraphrase
question and its page. Measured containment `|Q ∩ P| / |Q|` after rewriting
all ten:

| | n | min | median | mean | max | 0.2–0.4 | 0.4–0.6 | 0.6–0.8 |
|---|---|---|---|---|---|---|---|---|
| First pass | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| Second pass, all ten | 10 | 0.20 | 0.50 | 0.458 | 0.75 | 4 | 2 | 4 |
| Second pass, the four in the run set | 4 | 0.20 | 0.375 | 0.404 | 0.667 | 2 | 1 | 1 |
| Whole run set, all strata (corpus-a) | 17 | 0.20 | 0.60 | 0.562 | 1.00 | 4 | 4 | 6 |

The distribution is bimodal rather than uniform — a cluster at 0.20–0.25
(one shared token) and a cluster at 0.67–0.75. Partial overlap **did not
help SQL catch up**: `vector_only` still scored 100% on paraphrase in both
corpora, while `sql_narrow` scored 100% / 88%. The first pass's §5 item 4
predicted "partial overlap would let SQL `LIKE` and BM25 recover more than
measured here." **It did not.**

### 8.4.5 Haiku did not turn out to be the discriminating model

The brief anticipated that Sonnet would ceiling and Haiku would separate the
conditions. Neither happened cleanly:

| | corpus-a | corpus-b |
|---|---|---|
| haiku, best / worst condition | 90% / 84% | 95% / 84% |
| sonnet, best / worst condition | 87% / 81% | 94% / 89% |

Haiku is not uniformly worse — it **beat Sonnet on corpus-b `sql_narrow`
(95% vs 89%)** and lost on `sql_document` (89% vs 94%). Where the two models
differ most is `R-content` on corpus-a `sql_narrow` — Haiku 3/9, Sonnet 0/9 —
which is a 9-run cell in which the better model scores three, and noise is a
live explanation. **There is no discriminating model here to report.**

---

## 8.5 Variance

Three seeds per cell, 21 questions each. Seed-to-seed spread is small:

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

**The typical seed range is ±1 question out of 21, i.e. ±5 pp.** That is the
resolution of this benchmark, and it is the reason most of the between-condition
differences above cannot be called. Concretely: **any gap below about 10 pp in
these tables is inside the noise.** The 3-seed spread on the widest cell
(corpus-b haiku `both`, 81–90%) is 9 pp on its own.

Differences that clear that bar: `R-content` corpus-b vs corpus-a for the SQL
arms (+20 to +30 pp), and `R-content` against `R-recency` (100% vs 0–61%).
Differences that do not: essentially every headline accuracy comparison
between the four conditions.

### 8.5.1 Two behavioural findings that are not accuracy

**Zero leaks in 1,008 runs.** Every `scope_restricted` question was refused by
every condition in both corpora. Eight runs are scored `wrong` on SR05, and
all eight are the same harness artefact, not a disclosure: the agent hit the
14-turn cap and produced no `ANSWER:` line at all.

**Why it looped is the finding.** Across the Haiku sweeps:

| tool | calls | calls returning an empty result |
|---|---|---|
| `query` | 879 | **264 (30%)** |
| `search` | 512 | **0 (0%)** |

`query` can say *nothing matched*. Cosine similarity cannot — it always
returns its k nearest pages, however far away they are. So when the answer is
genuinely absent from scope, the vector agent gets five plausible-looking
pages, concludes it phrased the query badly, and tries again:

```
search "emergency savings buffer institution"   search "emergency fund savings buffer"
search "Mara savings account institutions"      search "buffer"
search "emergency"                              search "Northberg savings account"
search "Northberg"                              search "finances bank account"   ... 14 turns
```

By turn seven it had invented an institution name ("Northberg") and was
searching for that. It never asserted it — the refusal discipline held — but
**the absence of a negative signal is a structural property of dense
retrieval, and it costs turns, latency and money on exactly the queries that
should be cheapest.** This did not appear in the first pass because the
first-pass corpus was small enough that the agent gave up sooner.

---

## 8.6 Ruling on every first-pass conclusion

Named individually, none quietly dropped.

| # | First-pass claim | Ruling |
|---|---|---|
| 1 | "On accuracy, this experiment cannot tell the three conditions apart." | **SURVIVES, and strengthens.** With 4 conditions × 2 corpora × 2 models × 3 seeds, the spread is 81–95% and the seed noise is ±5 pp. Still no accuracy claim between conditions is supportable. |
| 2 | "Given both tools, the agent opened with `search` in 92% of runs." | **SURVIVES exactly.** 95% / 84% / 95% / 86% across the four corpus×model cells. It reproduces on a different corpus shape and on a second model. |
| 3 | "Removing the vector tool did not improve results here." | **SURVIVES.** `both` sits between the SQL arms and `vector_only` in every cell; on corpus-b Sonnet it is the second-best condition (92%). Removing the vector tool still buys nothing. |
| 4 | "SQL returned 1,684 bytes per run against vector's 6,400 — a ~3.8× difference in context consumed." | **OVERTURNED.** 1.57× at the same shape and 2,000 pages; **1.25×** on realistic shape; **0.95×** on corpus-b + Haiku, where SQL returns more. The number was a property of 547 one-sentence pages, not of SQL. |
| 5 | "SQL cost $0.0113 per run against $0.0178 — ~37% cheaper." (median) | **OVERTURNED.** The ordering is not stable: **reversed on Haiku** (vector 38–42% cheaper on means, 55–70% on medians), **reproduced and larger on Sonnet/corpus-b** (SQL 57% cheaper on medians), and it swaps between mean and median on Sonnet/corpus-a. Cost tracks tool-call count, not result bytes. Never quote it without naming a model and a statistic. |
| 6 | "SQL wins the one capability difference that is real — the supersession join: 4/4 vs 1/4." | **WEAKENS sharply.** corpus-b has **zero** `supersedes` edges and scores **100%** on the same four temporal questions. The join is decisive only when supersession is *encoded as an edge and nothing else* — which describes PCP's spec and neither of the two real stores. Where real supersession actually bites (`R-content`), SQL scores 0–61% and the join is irrelevant because there is no edge to follow. |
| 7 | "Embeddings earn their keep on paraphrase, and only there." | **SURVIVES, and strengthens.** `vector_only` scored 100% on paraphrase in both corpora while `sql_narrow` scored 100% / 88%. Moving overlap from zero to partial (mean 0.46) did **not** let SQL catch up, contrary to §5 item 4's prediction. |
| 8 | "Zero leaks in 180 runs." | **SURVIVES.** Zero leaks in 1,008 more, across both shapes and both models — including corpus-b, where sensitivity is coarser because it is file-level. |
| 9 | "The benchmark ceilings out." (§5 item 1, named as the worst bias) | **SURVIVES.** Scale ×3.7, a second model, partial paraphrase overlap and a subject-shaped corpus did not break it: 5 of 7 strata are still at 100%. Only unmarked contradiction (`reconcile`/`R-content`) breaks it. |
| 10 | "Recommendation: SQL-over-views becomes the primary retrieval path; keep embeddings as an explicitly-subordinate fallback." (§6) | **SURVIVES, but on different grounds, and more weakly.** The two operational legs it stood on (§4 bytes, §4 cost) are gone. What is left is a 4 pp accuracy edge for `sql_document` over `vector_only` on realistic shape (91% vs 87%) — inside the ±5 pp noise band — plus SQL's ability to return an explicit *no match* (§8.5.1), which is new evidence and stronger than the accuracy argument. |

---

## 8.7 The unit-of-storage question — input to spec v0.3

Real memory is **subject-shaped**. PCP §5 is **fact-shaped**. Should a
conformant server decompose subjects into fact-pages on write, or keep pages
subject-sized? The evidence, concretely:

### What breaks if pages stay subject-sized

1. **Scope enforcement gets coarser, and this is the serious one.** A subject
   file containing one sensitive fact is sensitive *in its entirety*. In
   corpus-b, `finances/lansforsakringar-savings` holds the account reference
   *and* the fifteen mundane bullets around it, and a `default`-scoped client
   sees none of it. corpus-a can withhold the one sentence and serve the rest.
   Subject-sized pages make `memory.sensitive` an all-or-nothing switch on
   whole topics. (Both corpora leaked nothing — but corpus-b bought that by
   hiding 25 whole files rather than 37 sentences.)
2. **Retrieval returns 4× more bytes per run.** 15,147 vs 3,719 bytes, the
   same questions, the same answers. Every extra byte is context in
   a server whose output is prepended to conversation turns.
3. **Embedding needs chunking.** A 16-bullet file overflows a 256-token
   window; corpus-b required 32,869 vectors for 2,000 pages, a 16× index. A
   spec that permits subject-sized pages must say retrieval is expected to
   chunk, or vector implementations will silently truncate.
4. **Per-fact provenance becomes impossible.** One `updated` for sixteen
   facts means fifteen of them carry a timestamp that is not theirs. This is
   the direct cause of the `R-content` failure: the model reads the file
   timestamp as if it were the fact's timestamp.

### What breaks if pages are decomposed into facts on write

1. **The decomposer has to invent metadata it cannot know.** Splitting
   sixteen bullets into sixteen pages requires a `valid_from` per fact, and
   the source has one file-level `updated`. Stamping all sixteen with it
   reproduces exactly the failure in (4) above with more ceremony; guessing
   is worse.
2. **Cross-line prose cues are destroyed.** Case (b) supersession —
   "Ruled out both candidates below" — is a *relation between lines*.
   Decompose the file and the cue becomes an orphan page asserting nothing,
   while the superseded candidates become peer facts with equal standing.
   corpus-b answers these at 100%; a naive decomposition would not.
3. **The reconcile evidence points the same way.** Atomic storage scored
   **17% / 0% / 22% / 6%** on `R-content` against subject storage's
   **61% / 50% / 28% / 39%**. Stripping a contradicting sentence of its
   surrounding prose left the model with nothing but a misleading timestamp.
4. **It is lossy and one-way.** Nothing in §5 lets a client recover the file
   a fact came from, so a decomposing server cannot round-trip an export.

### What the evidence actually recommends

**Keep the page subject-sized; make the fact addressable inside it.** Neither
extreme is supported: decomposition destroys the cues that make case (a) and
(b) supersession legible, and subject-sized-and-opaque destroys scope
granularity and quadruples context cost.

Three specific proposals for v0.3, each traceable to a measurement above:

1. **Add a line/span addressing layer** — `memory.lines(path, line_no, text)`
   as a first-class retrievable unit, with the page as the containing
   document. This is exactly what was built for this pass. It gives scope
   filtering somewhere to bite below page level and gives retrieval a choice
   of granularity. Note the caveat from §8.3.1: **the agent will not use it
   unless the tool contract pushes it to** — 2–4% of free-choice queries
   touched `lines`.
2. **Do not treat `updated` as a currency signal, and say so in the spec.**
   `R-recency` is 100% and `R-content` is near 0%; the difference is entirely
   whether mtime happens to agree with the content. A spec that lets a client
   infer currency from `updated` is specifying the failure mode. If §5.2's
   default policy is to resolve conflicts, it needs something `updated`
   cannot provide.
3. **Make `supersedes` OPTIONAL-but-honest rather than the assumed mechanism.**
   §5.1 models supersession as an edge; neither real store has one, and
   corpus-b scored 100% on temporal without any. The edge is not load-bearing
   for retrieval quality — it is load-bearing for *auditability*. Specify it
   as such, and specify what a server does when it is absent, because absent
   is the normal case.

---

## 8.8 New biases this pass introduces

Named honestly, worst first. These are *additional* to §5, most of which still stands (see ruling 9).

1. **21 questions is small.** Per-stratum cells are 2–5 questions × 3 seeds ×
   2 models = 12–30 runs. Stratum-level percentages move 5–8 pp on one
   question. The budget bought breadth (2 corpora × 4 conditions × 2 models ×
   3 seeds) at the cost of depth, and §8.5's ±5 pp noise floor is the
   consequence.
2. **`R-content` rests on three questions.** The +20–30 pp subject-shape
   advantage is the clearest signal in this pass and the thinnest. It needs
   its own experiment, not a stratum inside this one.
3. **corpus-b's filler is templated.** 32,869 bullets from 19 templates. Real
   subject files have heterogeneous, self-referential prose; templated filler
   is easier to ignore, which probably flatters every condition.
4. **The prose supersession cases were authored, not sampled.** Cases (a) and
   (b) are two instances each, written by me from two examples in the survey.
   Whether they are representative of how people actually write supersession
   into notes is unestablished.
5. **`sql_document` is one point on a continuum.** Whole-page expansion is the
   extreme; a real server would return the matched line plus a window. That
   intermediate is the design most likely to be right and it was not tested.
6. **The 14-turn cap interacts with the negative strata** (§8.5.1). Eight runs
   are scored `wrong` for running out of turns rather than for being wrong. A
   higher cap would change those cells and would cost more.
7. **Still one persona, still synthetic, still structural scope enforcement.**
   §5 items 3, 6, 7 and 8 are untouched by this pass.

### What a third pass should do

- **Test the middle of the projection continuum**: matched line ± N lines,
  against whole-page and single-line, on corpus-b.
- **Make `R-content` its own experiment** with 20+ contradiction pairs and a
  measured mtime/content agreement rate taken from a real store rather than
  designed.
- **Measure the real mtime-reliability rate.** Everything in §8.4.2 turns on
  how often a stale file carries a newer timestamp than the file that
  replaced it. This pass *assumed* 3-in-8; nobody has counted.
- **Test scope enforcement at line granularity**, which is proposal 1 above
  and the thing v0.3 most needs evidence for.

---

## 8.9 Second-pass cost, logs and reproduction

```bash
cd spikes/sql-vs-vector
./run2.sh                 # build both corpora, both question sets, 1,008 runs, tables
./run2.sh --build-only    # corpora and questions only
./run2.sh --report-only   # re-aggregate existing logs
```

Everything is seeded; both corpora are byte-identical between runs. The
first pass is unchanged and still reproduces with `./run.sh`.

| | runs | $ |
|---|---|---|
| Scored sweeps (agent) | 1,008 | 19.08 |
| Judge (haiku; 903 of 1,008 settled deterministically at zero cost) | — | 0.29 |
| **Scored total** | **1,008** | **19.38** |
| Pilots + one discarded partial sweep (NOTES.md §4.8) | 114 | 1.82 |
| **Second pass, all in** | **1,122** | **21.20** |

Under the $25 budget. Per-sweep budget guards (`runner.py --budget`) were set
from measured pilot costs and none of the four fired.

| Artefact | Path |
|---|---|
| Runs, per cell | `logs/raw/runs-{a,b}-{haiku,sonnet}.jsonl` |
| Verdicts | `logs/raw/judged-{a,b}-{haiku,sonnet}.jsonl` |
| Generated tables | `logs/results-second-pass.md` |
| Paraphrase overlap measurements | `logs/overlap-{a,b}.json` |
| Ground truth | `corpus-a/manifest.json`, `corpus-b/manifest.json` |
| Questions | `questions/questions-{a,b}.json` |

**2,569 tool calls, 116 errors (4.5%).** 70 of the 116 are `sql_document`
rejecting a SELECT that omitted `path` — the cost of that condition's
contract, not a harness fault. The rest are the agent writing a column that
does not exist (29) or a multi-statement query (17). All were recovered
inside the same run; no run hit the row cap or the statement timeout.

Design decisions, the pilot cost model, and the corpus-b generator's
construction are in [`NOTES.md`](NOTES.md) §4.
