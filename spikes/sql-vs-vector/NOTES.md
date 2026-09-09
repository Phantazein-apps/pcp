# Spike notes — SQL-over-views vs. embedding retrieval

Working notes for `spikes/sql-vs-vector/`. Findings and the recommendation
live in [`REPORT.md`](REPORT.md); this file records environment probes and
the design decisions taken before building.

## 1. Environment probes (run 2026-09-09)

Probed in the order the brief specifies.

### 1.1 Model access — `claude-agent-sdk` (PROBE 1: **PASS**)

| Check | Result |
|---|---|
| `ANTHROPIC_API_KEY` in env | **absent** |
| `curl https://api.anthropic.com/v1/models` | `401` (confirms no usable key) |
| `pip install claude-agent-sdk` into a venv | OK — `0.2.152` |
| One-line `query(...)` with `model="sonnet"` | **OK — returned `PONG`** |

The SDK spawns the local `claude` CLI (`/opt/node22/bin/claude`, v2.1.266),
which carries this session's own authentication. **No API key is required.**
Probe 1 passes, so the harness is built on `claude-agent-sdk` and the
Claude Code subagent fallback (option 2 in the brief) is *not* used.

Consequence for the brief's "capture tokens and latency if the mechanism
exposes them, otherwise say so": the SDK's `ResultMessage` exposes
`usage` (input/output/cache-read/cache-creation tokens), `total_cost_usd`,
`duration_ms` and `num_turns`. **Tokens, cost and latency are all captured
as measured values — nothing in the report is estimated.**

Note: a trivial prompt still bills ~22.8k cache-creation tokens because the
CLI injects its default system prompt and tool definitions. The runner
suppresses that with `setting_sources=[]`, an explicit `system_prompt`, and
in-process SDK tools instead of the built-in tool surface, so per-run token
counts reflect the experiment rather than the harness.

### 1.2 Egress to huggingface.co (**REACHABLE**)

| Check | Result |
|---|---|
| `https://huggingface.co/api/models/...` | `200` |
| `pip install torch` (CPU index) | OK — `2.14.0+cpu` (`download.pytorch.org` reachable) |
| `pip install sentence-transformers` | OK — `6.0.1` |
| Download + encode with `all-MiniLM-L6-v2` | OK — 384-dim vectors, ~8 s cold |

**The true vector condition runs.** The brief's BM25 contingency is not
needed as a stand-in. BM25 (`rank_bm25`) is still built and wired as a
*third, additional* backend (`lexical`), because it is nearly free and it
separates "embeddings helped" from "any non-SQL search helped" — but the
headline `vector_only` condition uses real dense embeddings, and nothing in
the report is renamed `lexical_only`.

The `--embeddings local` switch is wired and is the default. `--embeddings
none` forces the BM25 path for environments where egress is blocked.

### 1.3 Other

- Python 3.11.15; 4 cores; 15 GB RAM; ~30 GB free disk (venv is ~1.6 GB).
- No provider other than Anthropic is used. The embedding model is
  downloaded from HuggingFace and runs locally on CPU — no account, no key.

## 2. Spec reconciliation (§4 / §5)

The brief and `SPEC.md` v0.2-draft disagree in one place. Both points were
put to the requester before building; the decisions taken are recorded here.

### 2.1 Supersession — spec followed exactly (decision **reverted**)

`SPEC.md` §5.1 defines `lifecycle` as
`active | validated | stale | archived`. There is **no `superseded`
value**; the spec expresses supersession through a typed edge,
`relations: [{rel: supersedes, target: <page path>}]`.

The brief asks for "superseded facts (`lifecycle=superseded` with a newer
page)". This was initially resolved in favour of the brief — add the enum
value — and then **reverted by the requester**. Final decision:

> **The spike does not modify the spec.** `lifecycle` keeps exactly the four
> spec values. Supersession is modelled *only* as a `supersedes` relation on
> the newer page.

**Rationale, and why it is load-bearing for this experiment.** A scalar
`lifecycle: superseded` is a single self-announcing token sitting in the
same flat row as the fact. Both conditions could exploit it: SQL as
`WHERE lifecycle <> 'superseded'`, and vector search as a frontmatter field
returned inline with every hit, trivially filtered after retrieval. That
would have handed the vector condition a filterable attribute and **erased
the asymmetry actually under test**.

Following a `supersedes` relation is a **join**: the discriminating
information is not in the fact's own row, it is in an edge that points *at*
that row from elsewhere. That is precisely the operation a SQL tool does
natively and a similarity search cannot do at all — a vector index over page
text has no way to rank the surviving page above the one it replaced,
because both pages are about the same topic and read almost identically.
This is the single largest structural difference between the two retrieval
paths, so the corpus is designed to preserve it rather than flatten it.

Concretely, the SQL condition can express the discriminator as an anti-join:

```sql
SELECT m.* FROM v_memory_default m
LEFT JOIN v_relations_default r
       ON r.target_page = m.path AND r.rel = 'supersedes'
WHERE  r.target_page IS NULL          -- nothing supersedes this page
  AND  m.domain = 'work';
```

The vector condition has no equivalent move.

**Implementation.** For a supersession pair, *both* pages are left
`lifecycle: active` with open (or current) validity, so the §5.2 default
filter shows both and does **not** resolve the conflict. Only the edge does.
This is also the realistic shape: a memory system that has recorded a new
fact has not necessarily gone back to re-flag the old page.

### 2.2 Retrieval policy — conformant default, symmetric opt-in

`SPEC.md` §5.2 requires retrieval to honour lifecycle and validity by
default. Applying that filter inside the storage layer would let the server
do the temporal reasoning for both conditions, and the temporal stratum
would stop measuring the agent.

**Decision (requester): conformant default + opt-in override, applied
symmetrically to both backends.**

- Default: both `query` and `search` see only `active` / `validated` pages
  that are current or undated. `archived`, `stale`, `superseded` and
  expired pages are excluded.
- Opt-in: `query` gains an `_all` view per scope; `search` gains
  `--include-stale`. Both surface the full set with lifecycle and validity
  as columns/frontmatter.
- The opt-in is advertised identically in both system prompts, so neither
  condition is told more than the other.

### 2.3 Temporal stratum — designed against the default filter

The §2.2 default filter already hides `stale`, `archived` and expired pages.
That filter is doing real work, and a question it answers on its own is not
a temporal question — it is an exact lookup wearing a date. "What is Mara's
job title?" resolves because the old title page is `stale` and never
reaches the agent; **that question lives in `exact_lookup`, not here.**

Every question in the `temporal` stratum must therefore require at least one
of three mechanisms that the default filter cannot supply:

| # | Mechanism | Shape in the corpus | Why the filter can't do it |
|---|---|---|---|
| **T-a** | **Chase a `supersedes` relation** | Two pages, *both* `active`, both current or undated, near-identical in topic. The newer carries `relations: [{rel: supersedes, target: <old>}]`. | Both pages pass the default filter. The only discriminator is an edge pointing at the old page from the new one — a join (§2.1). |
| **T-b** | **Choose between overlapping validity windows** | Two or more `active` pages whose `valid_from`/`valid_until` windows overlap; the question pins a specific date. | Both windows are current, so both survive the filter. Correctness depends on interval containment, not on lifecycle. |
| **T-c** | **Use the opt-in override** | The answer is a *historical* fact on a `stale`/`archived`/expired page — "what did I drive before the estate", "when did the rate change". | The default filter's whole job is to hide these. The agent must notice the question is historical and opt in (`v_*_all` / `--include-stale`). |

The stratum is built as 4 × T-a, 3 × T-b, 3 × T-c. Each question records
which mechanism it exercises in the manifest, so the report can break
temporal accuracy down by mechanism rather than reporting one blended
number — T-a is where the SQL/vector asymmetry should show up most sharply,
and T-c is where both conditions can succeed if the agent reads its tool
documentation.

A question whose gold answer is reachable from the default view alone is
rejected at build time: the generator asserts, for every temporal question,
that the answer is **not** derivable from the default-visible page set by a
single lookup.

## 3. Other design decisions

- **Scope enforcement is structural, not filtered at query time.** Each
  scope gets its own SQLite file, built by materialising that scope's
  curated views. `tool.py --scope S` opens only that file, read-only. A
  scope-restricted leak therefore cannot come from a query bug — it can
  only come from the model asserting something it was never shown.
- **Oblique traces.** Because enforcement is airtight, the
  `scope_restricted` stratum would be trivial if the restricted topic were
  invisible. Non-sensitive pages therefore carry *traces* of sensitive
  facts (an appointment with a named specialist, a recurring payment to a
  clinic) without the fact itself. "Not found" is correct; naming the
  withheld fact is a leak.
- **Corpus is generated from facts, not scraped from prose.** Every page is
  rendered from typed `Fact` records, so gold answers are exact by
  construction rather than annotated after the fact.
- **Paraphrase disjointness is asserted, not assumed.** For the paraphrase
  stratum the build fails if a question shares any content token (after
  lowercasing, stopword removal and light stemming) with its target page.

---

# Second pass — corpus shape, variance, and the projection risk

Design record for the second pass. Findings are in [`REPORT.md`](REPORT.md)
§8; this section records what was built, what was decided, and what it cost.

## 4. What the second pass changes

### 4.1 Two corpora, side by side

| | corpus-a | corpus-b |
|---|---|---|
| Root | `corpus-a/`, `data-a/` | `corpus-b/`, `data-b/` |
| Generator | `pcp_spike/corpus.py` | `pcp_spike/corpus_b.py` |
| Unit | one page = one fact | one page = one SUBJECT FILE |
| Size | 2,000 pages | 2,000 files, 32,869 bullets (8–25, mean 16.4) |
| Frontmatter | full SPEC.md §5.1 | `title` + `updated` (+ `sensitivity`) |
| Supersession | `supersedes` relations edge | prose only — cases (a), (b), (c) |
| Lifecycle | active/validated/stale/archived | uniformly `active` |
| Confidence, validity | per page | absent |
| Tags | curated | absent — the directory is the taxonomy |
| `relations` rows | 29 | **0** |
| `memory` vs `memory_all` | 1,283 vs 2,000 | identical (nothing is ever stale) |

The **first pass's 547-page corpus is untouched** at `corpus/` + `data/`, and
`./run.sh` still reproduces it. corpus-a is a rebuild of the same generator at
2,000 pages, not a replacement of the control.

Both corpora are generated from the same `persona.py` entity tables, so gold
answers are identical by construction wherever a fact survives the re-shaping.
Where it does not — T-b validity windows and T-c the opt-in override both
require per-fact metadata corpus-b does not have — the question is dropped
from the second-pass set rather than quietly reweighted. §8.5 rules on what
that costs.

### 4.2 Measured per-run cost, and the budget guard

The first pass cost $4.82 for 240 runs. Extrapolating that to a 2-corpus,
4-condition, 2-model, 3-seed design put the second pass far over the $25 cap,
so per-run cost was **measured in three pilots before the budget was
committed** rather than assumed:

| corpus | model | condition | $/run | result bytes/run |
|---|---|---|---|---|
| corpus-a | haiku | `sql_narrow` | 0.0156 | 3,887 |
| corpus-a | haiku | `sql_document` | 0.0117 | 3,258 |
| corpus-a | haiku | `vector_only` | 0.0063 | 1,993 |
| corpus-a | haiku | `both` | 0.0083 | 2,035 |
| corpus-b | haiku | `sql_narrow` | 0.0235 | 20,754 |
| corpus-b | haiku | `sql_document` | 0.0202 | 11,364 |
| corpus-b | sonnet | (all four) | 0.0204–0.0245 | 6,264–10,628 |

Two things fell out of the pilots that changed the design:

1. **Sonnet is barely more expensive than Haiku per run here** (~$0.023 vs
   ~$0.022 on corpus-b), because Sonnet emits a third of the output tokens.
   That made a full two-model factorial affordable, where a 3× assumption
   would have forced Sonnet down to a token subset.
2. **`sql_narrow` on corpus-b returns MORE bytes than `sql_document`** —
   20.8 KB against 11.4 KB. Free projection over subject files does not
   produce narrow results; it produces `SELECT body` and 20 KB-capped `LIKE`
   scans. This is the second pass's central finding and it showed up in the
   pilot, before a single scored run.

The question set was then sized to the measured cost: **21 questions**, with
the allocation weighted away from the four strata that ceilinged in the first
pass and towards the three that can separate anything (§4.3).

`runner.py --budget N` is a hard guard: the sweep stops paying for runs once
measured spend passes N. Guards are per sweep and sum to $21.50.

### 4.3 The seventh stratum, and why the allocation is uneven

`reconcile` is new: two pages that contradict each other with **no marker of
any kind** — no `supersedes` edge, no lifecycle difference, no confidence gap,
no shared path prefix. This is case (c) of the supersession survey, and it is
the commonest form in the two real stores examined. Eight pairs exist in both
corpora; five carry questions. Build-time assertions enforce the absence of a
marker, so the stratum cannot silently degrade into an exact lookup.

The pairs split on what is left to resolve them:

- **`R-recency` (2 questioned)** — the current page has the later `updated`.
  Trusting mtime works.
- **`R-content` (3 questioned)** — `updated` is *backwards*: the stale page
  was touched later, so recency actively misleads, and only a date stated
  inside the prose settles it. This is the corpus's answer to the first
  pass's open question "do `updated` timestamps track currency, or does bulk
  import stamp everything with the import date?"

Question counts per stratum are 2 / 4 / 2 / 4 / 2 / 2 / 5. The four strata at
100% for every condition in the first pass get two questions each — enough to
show whether the ceiling survives corpus-b, not enough to spend budget on.

### 4.4 Chunking, and why the vector condition gets it on corpus-b

corpus-a pages are one fact each and fit inside `all-MiniLM-L6-v2`'s 256-token
window. corpus-b subject files do not: at a mean of 16.4 bullets, embedding
them whole would silently truncate most of every file and hand `vector_only` a
rigged loss on corpus-b that had nothing to do with retrieval method.

corpus-b is therefore embedded **one vector per bullet** (32,869 vectors) and
scored max-over-bullets, returning whole pages. That is the standard
mitigation, and it is also the fair comparison: it makes the vector condition
match at line granularity and return at page granularity — precisely what
`sql_document` is forced to do. The shape is read from the manifest, so no
condition has to ask for it.

### 4.5 Paraphrase overlap is now measured, not asserted

The first pass asserted **zero** content-token overlap between a paraphrase
question and its target page, which is the maximally embedding-friendly
extreme and was named as a bias in §5 item 4. The second pass rewrites all ten
paraphrase questions for partial overlap and **measures what it actually
generated** (`logs/overlap-{a,b}.json`), reporting containment `|Q ∩ P| / |Q|`
per question rather than claiming a target band was hit.

### 4.6 The judge got a deterministic stage, and a distractor guard

Grading an answer `correct` without a model call now happens when the gold
string or an alias appears in a short answer **and** the question's
`distractor` — the value a reader gets by trusting the stale page of a
supersession or reconcile pair — does *not*. That last clause is what makes
the shortcut safe on exactly the two strata where it would otherwise be
dangerous. Anything hedging between the two readings still goes to the model.
The model judge is also now told the superseded value explicitly and told to
grade it `wrong`.

### 4.7 What did NOT change

The scope model, the structural scope enforcement, the read-only guards
(single SELECT, 2 s timeout, 200 rows, 20 KB), the tool-call logging, the
`claude-agent-sdk` runner, and the cost accounting are all first-pass code,
unmodified. `sql_only` is still accepted as an alias for `sql_narrow` so the
§7 reproduction commands run.

### 4.8 Spend, including what was thrown away

Honest accounting: the second pass spent money before the scored sweeps
started, and one partial sweep was discarded.

| | runs | $ |
|---|---|---|
| Pilot: corpus-b, haiku, SQL conditions | 18 | 0.39 |
| Pilot: corpus-b, sonnet, all conditions | 16 | 0.37 |
| Pilot: corpus-a, haiku, all conditions | 36 | 0.38 |
| Discarded partial `a-haiku` (budget guard set too tight; restarted) | 44 | 0.68 |
| **Sunk before the scored sweeps** | **114** | **1.82** |

The pilot logs were not retained — only the per-condition cost table in §4.2
that was derived from them. The discarded `a-haiku` partial was thrown away
because its budget guard would have truncated seed 3 wholesale, leaving two
seeds in a design that requires three; restarting was cheaper than patching
the gap. Scored-sweep spend is in REPORT.md §8.9.
