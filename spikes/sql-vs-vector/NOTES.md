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
