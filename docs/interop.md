# PCP interop: OMP & Remnic

*Informative. How a PCP server maps to and from the two closest open memory
projects. Last updated 2026-07-07.*

## Position

PCP is not a competing **memory-object** standard. Its distinct layer is
**discovery + profile + per-category consent + connections**, served over MCP
(§2–§4, §6–§7). The raw memory layer (§5) is deliberately plain markdown so it
interoperates with, rather than replaces, the memory formats other tools already
use. A PCP server SHOULD be able to import memory produced by:

- **[Open Memory Protocol (OMP)](https://github.com/SMJAI/open-memory-protocol)** — a memory-object spec: JSON memories typed `episodic`/`semantic`/`procedural`, with `source`, `tags`, `expires_at`, exported via `GET /v1/export`.
- **[Remnic](https://github.com/joshuaswarren/remnic)** (formerly Engram) — markdown + YAML frontmatter memories with rich categories, `lifecycle_state`, `confidence`, `derived_from`, `validAt`/`invalidAt`, and typed graph edges. Filesystem-native.

Both are markdown/JSON-native, so import is near-lossless. Neither defines
discovery, OAuth-scoped consent, a profile schema, or connections — the parts
PCP adds on top.

## Field mapping → PCP page frontmatter (§5.1)

| PCP frontmatter | OMP memory object | Remnic frontmatter |
|---|---|---|
| body (markdown) | `content` | page body |
| `type` (`episodic`/`semantic`/`procedural`) | `type` (same values) | `category` → map (see below) |
| `tags` | `tags` | `tags` |
| `updated` | `updated_at` | `updated` |
| `valid_from` / `valid_until` | — / `expires_at` | `validAt` / `invalidAt` |
| `lifecycle` | — (default `active`) | `lifecycle_state` (`active`/`validated`/`stale`/`archived`) 1:1 |
| `confidence` | — | `confidence` |
| `source` | `source.{tool,session_id,timestamp}` → `{origin:"import", client, session, at}` | `source_corroboration` / inline `[Source: …]` → `source` |
| `derived_from` | — | `derived_from` |
| `relations` | — | typed graph edges → `relations` (`supersedes`/`contradicts`/`refines`/`about`) |

### Remnic category → PCP `type`

Remnic's fine-grained categories collapse onto PCP's three-way `type`, preserving
the original in `tags`:

- `fact`, `preference`, `principle`, `rule`, `relationship`, `skill` → `semantic`
- `decision`, `correction`, `commitment`, `moment` → `episodic`
- `procedure` → `procedural`

## Transport

All three ride **MCP**. OMP exposes `omp_remember`/`omp_recall`/…; Remnic exposes
`remnic.recall`/`remnic.memory_store`/…; PCP exposes `memory.search`/`memory.read`/
`memory.write` (§6). A PCP server bridging another tool's memory MAY expose the
foreign tools directly *or* re-index the imported pages under the PCP surface.

## Import contract

- `import` (§8) SHOULD accept an OMP `/v1/export` JSON array and a Remnic memory
  folder, mapping fields per the table above. Unmapped source fields SHOULD be
  preserved under a `x_import` frontmatter key rather than dropped.
- Third-party credentials are never imported (§8).

## Non-goals & the alignment trigger

PCP will not re-standardize the memory object, and will not fork OMP or Remnic.
Where a **governed** standard emerges at PCP's own altitude — an MCP memory/profile
**extension**, or a live-serving portability standard such as the Data Transfer
Initiative's AI-conversation schema — PCP's memory (§5) and export (§8) SHOULD be
mapped onto it, and this document extended, rather than maintaining a parallel
shape (§11).
