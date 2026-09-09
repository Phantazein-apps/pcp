# Spike: SQL-over-views vs. embedding retrieval

Does an agent given a scoped, read-only **SQL tool over curated views**
retrieve personal memory as well as, or better than, one given a
**vector-search tool**? And does giving it *both* make it worse, as claimed
in "Giving AI agents a SQL tool is unreasonably effective"?

Retrieval only. No WordPress, no MCP adapter, no OAuth.

- **Findings and recommendation:** [`REPORT.md`](REPORT.md)
- **Environment probes and design decisions:** [`NOTES.md`](NOTES.md)

## Run it

```bash
./run.sh                      # first pass: 60 questions x 3 conditions x sonnet
./run.sh --full               # adds haiku and a second seed
./run.sh --embeddings none    # BM25 only, for environments without HF egress
```

`run.sh` creates the venv, builds the corpus, storage and embeddings, runs
the sweep, judges the answers and writes the tables. Everything is seeded;
the corpus is byte-identical between runs.

## Layout

| Path | What it is |
|---|---|
| `pcp_spike/persona.py` | The synthetic persona's entity tables |
| `pcp_spike/corpus.py`  | Renders 547 memory pages from typed `Fact` records |
| `pcp_spike/store.py`   | WP-shaped schema + curated per-scope views |
| `pcp_spike/retrieval.py` | Cosine over local embeddings; BM25 |
| `pcp_spike/tool.py`    | The harness CLI -- the agent's only data access |
| `pcp_spike/qset.py`    | The 60 questions and their validators |
| `pcp_spike/runner.py`  | Drives the conditions via `claude-agent-sdk` |
| `pcp_spike/judge.py`   | Grades answers: correct / partial / wrong / leak |
| `pcp_spike/report.py`  | Aggregates judged runs into tables |
| `corpus/`              | Generated pages + `manifest.json` (ground truth) |
| `data/`                | SQLite: master + one file per scope; embeddings |
| `logs/raw/`            | Every run and every verdict, JSONL |

## The tool the agent sees

```bash
python tool.py query  --scope default "SELECT path, body FROM memory WHERE domain='vehicles'"
python tool.py search --scope default -k 5 "what car does she drive"
python tool.py schema                      # the view documentation
```

`query` is read-only (single SELECT, 2 s timeout, 200 rows, 20 KB, CSV).
`search` is brute-force cosine over local embeddings, scope-filtered.
Both default to the pages currently in force and share one opt-in
(`memory_all` / `--include-stale`) for historical material.

## Conditions

| Condition | Tools granted | System prompt |
|---|---|---|
| `sql_only` | `query` | carries the view schema and column semantics |
| `vector_only` | `search` | describes search and the include-stale opt-in |
| `both` | `query` + `search` | carries both |
