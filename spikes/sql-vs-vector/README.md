# Spike: SQL-over-views vs. embedding retrieval

Does an agent given a scoped, read-only **SQL tool over curated views**
retrieve personal memory as well as, or better than, one given a
**vector-search tool**? And does giving it *both* make it worse, as claimed
in "Giving AI agents a SQL tool is unreasonably effective"?

Retrieval only. No WordPress, no MCP adapter, no OAuth.

Two passes. The **first** compared three conditions over 547 atomic,
fact-per-page memory pages. The **second** rebuilt the benchmark against the
shape real memory stores actually have — subject files of 8-25 bullets, one
file-level timestamp, supersession only in prose — and re-ran every
first-pass conclusion against it. Several did not survive.

- **Findings and recommendation:** [`REPORT.md`](REPORT.md)
  — first pass §1-§7, **second pass §8** (read §8 before acting on §1-§6)
- **Environment probes and design decisions:** [`NOTES.md`](NOTES.md)
  — first pass §1-§3, second pass §4

## Run it

```bash
./run.sh                      # first pass: 60 questions x 3 conditions x sonnet
./run.sh --full               # adds haiku and a second seed
./run.sh --embeddings none    # BM25 only, for environments without HF egress

./run2.sh                     # second pass: 21 q x 4 conditions x 2 corpora
                              #              x 2 models x 3 seeds = 1,008 runs
./run2.sh --build-only        # both corpora and both question sets only
./run2.sh --report-only       # re-aggregate existing logs
```

Both scripts create the venv, build the corpora, storage and embeddings, run
the sweeps, judge the answers and write the tables. Everything is seeded;
every corpus is byte-identical between runs.

## Layout

| Path | What it is |
|---|---|
| `pcp_spike/persona.py` | The synthetic persona's entity tables -- shared by both corpora |
| `pcp_spike/corpus.py`  | **corpus-a**: renders atomic, one-fact-per-page memory |
| `pcp_spike/corpus_b.py`| **corpus-b**: renders subject files of 8-25 bullet facts |
| `pcp_spike/reconcile.py` | The eight unmarked contradiction pairs, shared by both |
| `pcp_spike/store.py`   | WP-shaped schema + curated per-scope views, incl. `lines` |
| `pcp_spike/retrieval.py` | Cosine over local embeddings (chunked for corpus-b); BM25 |
| `pcp_spike/tool.py`    | The harness CLI -- the agent's only data access |
| `pcp_spike/qset.py`    | First pass: the 60 questions and their validators |
| `pcp_spike/qset2.py`   | Second pass: 21 questions per shape, + overlap measurement |
| `pcp_spike/runner.py`  | Drives the conditions via `claude-agent-sdk` |
| `pcp_spike/judge.py`   | Grades answers: correct / partial / wrong / leak |
| `pcp_spike/report.py`  | First-pass tables |
| `pcp_spike/report2.py` | Second-pass tables, with per-seed ranges throughout |
| `corpus/`, `data/`     | First-pass control: 547 atomic pages, untouched |
| `corpus-a/`, `data-a/` | Second pass, atomic shape, 2,000 pages |
| `corpus-b/`, `data-b/` | Second pass, subject shape, 2,000 files / 32,869 bullets |
| `logs/raw/`            | Every run and every verdict, JSONL |

## The tool the agent sees

```bash
python tool.py query  --scope default "SELECT path, body FROM memory WHERE domain='vehicles'"
python tool.py query  --scope default --document "SELECT path FROM lines WHERE text LIKE '%kora%'"
python tool.py search --scope default -k 5 "what car does she drive"
python tool.py schema                      # the view documentation
```

`query` is read-only (single SELECT, 2 s timeout, 200 rows, 20 KB, CSV).
`--document` discards the projection and returns the whole containing file
for every matched row. `search` is brute-force cosine over local embeddings,
scope-filtered. Both default to the pages currently in force and share one
opt-in (`memory_all` / `--include-stale`) for historical material.

Point either at a corpus with `PCP_CORPUS` / `PCP_DATA`, e.g.
`PCP_CORPUS=corpus-b PCP_DATA=data-b python tool.py ...`.

## Conditions

| Condition | Tools granted | System prompt |
|---|---|---|
| `sql_narrow` | `query` | view schema; the agent picks its own projection |
| `sql_document` | `query` (document mode) | view schema; every match returns in full |
| `vector_only` | `search` | describes search and the include-stale opt-in |
| `both` | `query` + `search` | carries both |

`sql_only` is accepted as an alias for `sql_narrow`, so the first pass's
reproduction commands still run.
