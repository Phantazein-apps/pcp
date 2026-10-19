# PCP interop: importer mappings, projections and a JSON-LD context

*Informative. How memory from other tools enters a PCP context, and how a PCP
context can be shown to tools that speak other formats. Updated 2026-10-19
for v0.3 (SPEC §8).*

## 1. Position and rules shared by every mapping

PCP does not try to replace other memory formats. Its own layer is discovery,
profile, per-category consent, team access and a checkable export, served
over MCP. Memory pages are plain Markdown with YAML frontmatter (SPEC §5) so
that memory from other tools imports with little loss, and so that a PCP
context can be read without PCP software.

Every importer below runs in **import mode** (SPEC §8.7.3). In short:

- `source.origin: import`; `source.principal` is the mapped author or the
  importing principal; `source.at` is the source's creation time.
- `recorded_at` is the import instant; `updated` keeps the source's last
  change, converted to RFC 3339 UTC (§8.7.3 item 8).
- In a context with the `review` feature every imported page is a proposal.
- `x_import` records `format`, `at`, the source `id`, the `sha256` of the
  record as received (the idempotency key with the source path), and in
  `fields` every source value with no PCP key, once, under its source name.
  The raw source frontmatter is not kept (S19).
- Derived values (hashes, embeddings, relevance scores) are dropped; they
  are rebuilt from content (§5.5 item 5).
- Items the source marks deleted, forgotten or expired are not imported
  (`skipped_erased`, `skipped_expired`).
- When a source has no stable path, the importer builds one from a fixed
  prefix and the source id (`mem0/<id>`), never from a title alone, so a
  re-import finds the same page.
- **Titles.** When a source has no title, the importer derives one from the
  first line of content: Markdown markup stripped, cut at a word boundary to
  at most 80 characters. The body stays as it was.

In the tables, "fields" means `x_import.fields`, and "map" means the
`principal_map` or `partition_map` of the import request (§8.7.3 item 7).

## 2. Agent Brain

Agent Brain is a WordPress plugin that gives a team's agents shared,
partitioned and reviewed memory. SPEC Appendix A maps its concepts. This
section maps every field of its export, and the data its export does not
yet carry, onto a PCP archive, checked against portakey `4f24875`
(`Modules/Forget/Exporter.php`, `Forgetter.php`, `Matcher.php`,
`ReceiptRepository.php`, `Backup/Restore.php`, `TarReader.php`, and the
memory and audit tables).

### 2.1 Today's export, field by field

`Exporter::exportMarkdown()` writes one file per memory row
(`memory-<id>.md`), knowledge post (`knowledge-<ID>.md`) and procedure post
(`procedure-<ID>.md`), each with eight frontmatter keys, zipped without a
manifest.

**Memory rows** (`wp_ab_memory`):

| Exporter key | Source | PCP archive |
|---|---|---|
| (file name) `memory-<id>.md` | row id | `memory/memory/<type>/<id>.md`, page path `memory/<type>/<id>` (Appendix A) |
| `id` | `id` | `id: ab-memory-<id>` |
| `type` | `working`, `episode`, `fact` | `type: episodic` (working, episode) or `semantic` (fact); the original in `x_agent_brain.type` |
| `scope` | `scope_id`, an `ab_scope` term id | `partition`: the term's slug (must match `[a-z0-9][a-z0-9_-]{0,63}`) |
| `agent` | `agent_id`, a user id | `source.principal`: `agent:<user_login>` for `ab_agent` users, else `human:<user_login>`; listed in `context.json` |
| `created` | `created`, `Y-m-d H:i:s` UTC | `recorded_at`, `updated` (rows are immutable) and `source.at`, as `YYYY-MM-DDTHH:MM:SSZ` |
| `importance` | 0 to 100 | `importance` divided by 100 |
| `status` | `active` | no `lifecycle` key (active) |
| | `rolled_up` | `lifecycle: archived`; the roll-up names the row in `derived_from` |
| | `proposed` | `review: {state: proposed, generated: {by: <agent>, at: <created>}}` |
| | `deleted` | **not exported** (SPEC §8.10 item 3). Today's exporter selects every row, including deleted ones |
| `source_ids` | JSON list of row ids | `derived_from`: `memory/<type>/<id>` for each |
| (body) | `content` | body, the stored text as is (not the escaped `<memory_data>` framing that recall returns) |

**Knowledge and procedure posts** (`ab_knowledge`, `ab_procedure`):

| Exporter key | Source | PCP archive |
|---|---|---|
| (file name) | `ID` | `memory/knowledge/<post_name>.md` or `memory/procedures/<post_name>.md`. `post_name` can hold percent-encoded characters for non-ASCII titles, which the path grammar forbids: then use `knowledge/<ID>` |
| `id` | `ID` | `id: ab-knowledge-<ID>` or `ab-procedure-<ID>` |
| `type` | post type | `type: semantic` (knowledge) or `procedural` |
| `scope` | `ab_scope` term ids (a list) | `partition`: the term's slug. A page has one partition (SPEC §5.3); a post in several terms goes in the first by term id, with the others in `x_agent_brain.also_in`. That narrows access, which fails closed; Agent Brain restores all terms from the key |
| `agent` | `ab_proposing_agent` | `review.generated.by` and `source.principal` |
| `created` | `post_date_gmt` | `recorded_at` |
| `importance` | `ab_importance` | `importance` divided by 100 |
| `status` | `private` (approved) | `lifecycle: validated` for knowledge; `review.state: approved` with `verified` (below) |
| | `ab_proposed` | `review.state: proposed` |
| | `ab_rejected` | `review.state: rejected`, `rejected: {by, at}` from the review meta |
| | `trash`, `draft`, `auto-draft` | not exported |
| `source_ids` | `ab_source_memory_ids` | `derived_from`: `memory/<type>/<id>` |
| (body) | `post_content` | body, as stored |

### 2.2 Data the export does not carry yet

| Agent Brain data | PCP archive |
|---|---|
| `post_title` | `title` (REQUIRED). Rows have no title: derive one (§1) |
| `post_modified_gmt` | `updated` for posts |
| Row `search_keys`, post `ab_search_keys` | `tags`, or `x_agent_brain.search_keys` to keep them apart from labels |
| Row `client` | `source.client` |
| Row `agent_written` | `source.origin: agent` when 1; when 0, `consolidation` with `source.principal: service:compression` for compression output, else `user` |
| Row `expires` | `expires`. Rows past it are not exported (§8.10) |
| `wp_ab_memory_links` (`derived_kind`, `derived_id`, `source_id`) | `derived_from` on the derived row or post |
| `ab_reviewed_by`, `ab_reviewed_at` | `review.verified: [{by, at}]` or `review.rejected` |
| `ab_review_outcome` `edited` | approved, plus `x_agent_brain.review_outcome: edited` |
| `ab_source_artifact`, `ab_compiled_from` | `relations` with `x-ab:compiled_from` targets, or `x_agent_brain` |
| WordPress post revisions | `history/<path>/<n>.md`, if exported (SPEC §8.2 item 4) |
| `ab_scope` terms | `context.json` partitions (`name`: slug, `description`: term name) |
| `ab_read_scopes`, `ab_write_scopes` user meta | `context.json` access: read gives `read`; write gives `propose` and `write`; curators get `review` |
| Users with `ab_agent`, `ab_curator`, administrator | `context.json` principals with `roles`; deleted users that rows still name as `status: removed` |
| Site | `controller`: `org:<site host>` or the administering human |
| `wp_ab_audit` (`id`, `ts`, `actor_id`, `event`, `status`, `object_type`, `object_id`, `args_hash`, `meta`, `duration_ms`) | `audit/log.jsonl`: `id: ab-audit-<id>`, `at` from `ts`, `principal` from `actor_id`, `action` (PCP tool name for ability events), `channel` (`mcp` or `management`), `categories`, `outcome` from `status`, `object_ids: ab-<kind>-<id>`, counts from `meta`, `duration_ms`. Drop `args_hash`: it is an unkeyed hash of input (SPEC §7.5) |
| `ab_forget_receipts` (`id`, `subject_hash`, `created`, `curator_id`, `counts`, `residue`, `status`) | `erasures/receipts.jsonl`: `id`, `kind: subject`, `requested_by`, `requested_at` and `completed_at` from `created`, `counts`, `residue`, `status` (`complete` or `residue_found`). `subject_hash` is an unkeyed SHA-256, so it is **not** exported; new receipts carry a keyed `subject_digest` (SPEC §8.9.3) |
| Handoffs (`ab_handoff`: title, content, `ab_handoff_to`, `ab_handoff_status`, `ab_handoff_action`, `ab_handoff_section`, `ab_source_memory_ids`) | `extensions/<handoff extension id>/`, slot `handoff` (SPEC §8.5); linked rows by page path |
| Artifacts, sections, leases, versions, stages | `extensions/<doc extension id>/`, slot `doc` |
| Application passwords, OAuth tokens and clients | Never exported (SPEC §8.2 item 8) |
| Encrypted backups (`ab_backup_key`, a site key) | Not an export: host custody (SPEC §8.4 item 4). Erasure propagates to them |
| Settings (`ab_proposal_threshold`, `ab_export_keep` and the like) | Not exported (server configuration) |

### 2.3 What the exporter needs to change

1. Write the §8.2 layout and a `manifest.json` with every file's SHA-256
   and size, counts, `omitted` and `credentials_included: false`.
2. Emit partition slugs, principal ids from `user_login`, RFC 3339 UTC
   times, `title` and `updated`.
3. Filter `deleted` rows, rows past `expires`, and trashed posts.
4. Emit frontmatter with a real YAML serializer. Today's `yamlScalar()`
   quotes strings but escapes only `"`, and writes lists as `[a, b]`
   unquoted, so a value with a comma, a backslash or a newline breaks. JSON
   strings are valid YAML, so `wp_json_encode()` per value is enough.
5. Add the data in §2.2, `context.json`, the audit log and the receipts.
6. Keep the export-artifact handling as it is: protected directory, no
   public URL, retention, and deletion of every artifact on forget all match
   SPEC §8.1 item 4 and §8.9.2.
7. Forget: key the subject digest (for example
   `hash_hmac('sha256', $subject, <site secret>)`), and keep `Matcher`'s
   phrase rule, which already meets SPEC §8.9.1 item 3.

### 2.4 Importing into Agent Brain

| PCP page | Agent Brain |
|---|---|
| `type: semantic` or `procedural`, approved | `ab_knowledge` or `ab_procedure`, status `private`; review meta from `review.verified` |
| Proposed (always, in import mode) | `ab_proposed`, reviewed in wp-admin |
| Rejected (restore only) | `ab_rejected` |
| `type: episodic`, `x_agent_brain.type` `working`, `episode` or `fact` | an `ab_memory` row of that type; without the key, `episode` |
| `partition` | the mapped `ab_scope` term |
| `importance` | ×100, rounded |
| `expires` | row `expires` |
| `title`, `valid_*`, `relations`, `tags`, `x_*`, `x_import` and every key without a column | kept as a whole, so the next export gives them back (SPEC §8.8): post meta for posts, and a new column for rows, which have no meta table |

`Backup/Restore.php` only unpacks a backup for inspection, and
`TarReader` already rejects absolute paths, `..`, NUL bytes, links and
devices, which is most of SPEC §8.7.1 item 1. A PCP importer can reuse it.

### 2.5 A round trip through the hosted demo brain

The demo holds a real team brain (scope "MultiPass + Agent Brain (Dennis &
Roger)": 11 memories, 3 procedures and 6 proposed decisions, as of
2026-10-19). Reasoned through without copying its content:

1. **Export.** One partition (the scope's slug). Principals: the agent
   that wrote the episodes (`agent:<login>`), the two curators
   (`human:<login>`), and the site as controller. 11 pages under
   `memory/memory/episode/`, 3 under `procedures/`, 6 under `knowledge/`
   with `review.state: proposed` and `generated.by` the proposing agent.
   `review_counts` 14 approved, 6 proposed. Ids collide across tables (a
   memory row and a knowledge post can both be 15); the `ab-memory-` and
   `ab-knowledge-` prefixes and the separate path roots keep them apart.
2. **What recall shows is not what export writes.** Recall wraps content in
   `<memory_data>` with HTML entities (`&#039;`). The exporter writes the
   stored text, or the body would change on every round trip.
3. **Restore into a fresh Agent Brain.** Same paths, ids and review state;
   the 6 decisions are still in the review queue; principals are unbound
   until the curators sign in and agents get new application passwords.
   Re-export is byte-identical if the exporter serializes deterministically
   (SPEC §8.8 item 1).
4. **Import into a personal context** (for example one person's own
   context): import mode, so the 14 approved pages arrive approved with
   `source.origin: import`, and the 6 proposals are skipped
   (`skipped_review_state`) because a personal context has no review
   queue, unless the person asks for them.
5. **Import into another team** with review: all 20 arrive as proposals in
   the target partition the importer chose, authors mapped through
   `principal_map` or attributed to the importer.

## 3. Basic Memory

[Basic Memory](https://docs.basicmemory.com) keeps a directory of Markdown
files. Frontmatter has `title`, `type`, `permalink` and `tags`; the body has
observations (`- [category] text #tag (context)`) and relations
(`- relation_type [[Target]]`).

| Basic Memory | PCP |
|---|---|
| `permalink` | path (it is stable across renames). Without one, the file path without `.md` |
| `title` | `title` |
| `type` (free: note, person, project and so on) | `type: semantic` by default (`episodic` for dated journal notes, `procedural` for how-to notes, when the importer is told); the original in fields |
| `tags` | `tags` |
| Frontmatter dates, else the file's modification time | `updated`; creation time in `source.at` |
| Relation lines `- rel [[Target]]` | `relations: [{rel: "x-bm:<rel>", target: <target permalink>}]`; `rel` lowercased to `[a-z0-9_-]`. Targets that do not exist yet are kept (forward references) |
| Observation lines | stay in the body |
| Body | body, byte-identical; relation lines stay in it too |
| Workspace or project | `partition` via map |

## 4. Mem0

[Mem0](https://docs.mem0.ai) stores memory rows. Its `POST /v1/exports` is
shaped by a model and lossy by design, so an importer reads the memory
listing (`get_all` with pagination) and the history instead (SPEC §8.7.5).

| Mem0 | PCP |
|---|---|
| `id` | path `mem0/<id>`, fields `id` |
| `memory` | body; `title` derived (§1) |
| `user_id` | the subject. Into a personal context, the controller; into a team, `principal_map` |
| `agent_id` | `source.principal` via map (`agent:<agent_id>`) |
| `app_id` | fields |
| `run_id` | `source.session` |
| `categories` | `tags` |
| `metadata` | fields |
| `created_at`, `updated_at` | `source.at`, `updated` |
| `expiration_date` | `expires` (retention, not validity) |
| `replaced_by` | the replacing page gets `relations: [{rel: supersedes, target: mem0/<id>}]`; the replaced page `lifecycle: archived` |
| `synthesized` | `source.basis: inferred`; otherwise `provided` |
| `lifecycle_state` | `lifecycle` when the value is a PCP value, else fields |
| `hash`, scores, embeddings | dropped |
| History events | not imported (another context's audit trail) |

## 5. supermemory

[supermemory](https://supermemory.ai/docs) keeps versioned memory entries.
Field names below are as read in the Phase 1 audit (2026-10-18); check them
against the API version you import from.

| supermemory | PCP |
|---|---|
| `id` | path `supermemory/<rootMemoryId or id>`, fields `id` |
| `memory` (content) | body; `title` derived |
| Version chain (`version`, `parentMemoryId`, `rootMemoryId`, `isLatest`) | the latest version is the page. Earlier versions MAY be imported as `lifecycle: archived` pages at `<path>/v<version>` that the latest `supersedes`; by default they are skipped and reported |
| `isStatic` | `type: semantic`, `lifecycle: validated` |
| `isInference` | `source.basis: inferred` (and a proposal in a context with review) |
| `isForgotten` | not imported (`skipped_erased`) |
| `forgetAfter` | `expires`. (The Phase 1 audit suggested `valid_until`, before SPEC §5.2 separated retention from validity; forgetting is retention.) |
| `temporalContext` dates | `valid_from`, `valid_until`; anything else in fields |
| Relations `updates`, `extends`, `derives` | `supersedes`, `refines`, `derived_from` |
| Container tags (namespaces) | `partition` via map; also `tags` |
| `createdAt`, `updatedAt` | `source.at`, `updated` |
| `metadata` | fields |

## 6. Open Memory Protocol (OMP)

[OMP](https://github.com/SMJAI/open-memory-protocol) exports a JSON array
(`GET /v1/export`). No commits since 2026-07-02.

| OMP | PCP |
|---|---|
| `id` | path `omp/<id>`, fields `id` |
| `content` | body; `title` derived |
| `type` (`episodic`, `semantic`, `procedural`) | `type`, same values |
| `tags` | `tags` |
| `namespace` | `partition` via map |
| `created_at`, `updated_at` | `source.at`, `updated` |
| `expires_at` | `expires` |
| `source.tool`, `source.session_id`, `source.timestamp` | fields `tool`, `source.session`, `source.at` |

## 7. Remnic

[Remnic](https://github.com/joshuaswarren/remnic) keeps Markdown with YAML
frontmatter, and exports **capsules**: lossless, with a SHA-256 manifest and
optional AES-256-GCM. An importer verifies the capsule's own hashes first,
like SPEC §8.7.1 item 2, and decrypts with the key the person supplies.

| Remnic | PCP |
|---|---|
| File path | path, when it matches the grammar |
| `category` | `type`: `fact`, `preference`, `principle`, `rule`, `relationship`, `skill` to `semantic`; `decision`, `correction`, `commitment`, `moment` to `episodic`; `procedure` to `procedural`. The category also in `tags` |
| `tags` | `tags` |
| `updated` | `updated` |
| `lifecycle_state` | `lifecycle` (same four values) |
| `confidence` | `confidence` |
| `validAt`, `invalidAt` | `valid_from`, `valid_until` |
| `derived_from` | `derived_from` |
| Typed graph edges | `relations` (`supersedes`, `contradicts`, `refines`, `about`), others as `x-remnic:<type>` |
| `source_corroboration`, inline `[Source: ...]` | fields; body unchanged |
| `sharedBy` | `source.principal` via map |
| Namespaces (with read and write principals) | `partition` via map; their principal lists are not imported (access lists are the target's own) |
| Contradiction and suggestion queues | not imported (another context's review) |

## 8. DTI AI conversations

The Data Transfer Initiative's AI Conversation schema
([schemas.pub/24](https://schemas.pub/schemas/24)) carries conversations as
messages with an author, a time and content. There is no memory schema.
Field names here are generic; map them to the schema version you receive.

| Conversation | PCP |
|---|---|
| Conversation id | path `conversations/<id>`, `source.session` |
| Title, else the first user message | `title` |
| Messages | body: one block per message, `**<author role>** (<time>):` then the text. Attachments are referenced by name, not embedded |
| Start time | `source.at`, `valid_from` |
| Last message time | `updated` |
| | `type: episodic`, `source.basis: provided` |

Importers SHOULD NOT extract facts during import. A consolidation pass can
distill pages from the transcripts later (SPEC §5.6), and in a context with
review those pages are proposals.

## 9. Optional OKF projection

The [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(v0.2) is a directory of Markdown with YAML in which only `type` is
required, so PCP pages are already valid OKF documents. A server MAY offer
an **OKF projection**: a directory any OKF reader can load. It is a view for
sharing, one way and lossy, and never counts as an export.

1. Include approved pages only, and by default only `normal` pages in
   partitions the requester chose. Proposed, rejected, sensitive and
   expired pages are left out.
2. Same paths and bodies. Frontmatter:

| PCP | OKF |
|---|---|
| `type` | `type` (OKF `type` is free) |
| `title` | `title` |
| `review.generated`, else `{by: source.principal, at: recorded_at}` | `generated: {by, at}` |
| `review.verified` | `verified: [{by, at}]` |
| `lifecycle` | `status` |
| `valid_until` | `stale_after` |
| `derived_from` | `sources` (relative links) |
| `tags` | `tags` |
| Principals `human:<id>` | `human:<id>` |
| Principals `agent:<name>` or `agent:<name>/<version>` | `<name>` or `<name>/<version>` |

3. PCP-only keys (`partition`, `sensitivity`, `source`, `x_*`) are dropped.

## 10. JSON-LD context (draft)

[`schemas/0.3/pcp.context.jsonld`](../schemas/0.3/pcp.context.jsonld) maps
frontmatter keys to Dublin Core, PROV-O and schema.org terms, with PCP terms
under `https://phantazein-apps.github.io/pcp/ns#` where nothing fits, so a
page lifts to RDF (for example into a Solid pod) without PCP requiring RDF.
Page paths become `@id`s relative to the context's base URL. It is a draft:
the terms may change before v0.3 is released, and the `ns#` terms are not
yet documented at that URL.

```json
{ "@context": "https://phantazein-apps.github.io/pcp/schemas/0.3/pcp.context.jsonld",
  "@id": "knowledge/estimates-not-advice",
  "title": "The calculator shows estimates, never advice",
  "type": "semantic",
  "updated": "2026-09-20T11:00:00Z",
  "review": { "state": "approved", "verified": [{ "by": "human:lee", "at": "2026-09-20T11:00:00Z" }] } }
```

## 11. Alignment trigger

PCP will not standardize the memory object again, and will not fork any of
the projects above. If a governed standard emerges at PCP's own level (an
MCP memory or profile extension, or a live-serving portability standard),
PCP's memory (§5) and export (§8) should be mapped onto it and this document
extended, rather than a parallel shape kept (SPEC §11).
