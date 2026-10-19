# PCP Specification: v0.3-draft

**Portable Context Protocol: format and server behavior**

Status: DRAFT, in progress · License: Apache 2.0 · Last updated: 2026-10-19

> **v0.3 is in progress.** This document is being rewritten in five phases
> ([`docs/v0.3-plan.md`](docs/v0.3-plan.md)), and each phase merges here.
> Sections marked *(v0.3)* are updated. Sections marked *(pending, v0.2 text)*
> have not been rewritten yet; where they disagree with an updated section,
> the updated section wins. If you need a stable text, pin the git tag
> [`v0.2-draft`](https://github.com/pcp-protocol/pcp/tree/v0.2-draft).
> A server implementing this draft emits `"pcp_version": "0.3"`.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be
interpreted as in RFC 2119 and RFC 8174 when they appear in capitals.

**Versioning.** A server emits the `pcp_version` it implements. Schemas are
versioned by path: every schema for this version has the `$id`
`https://pcp-protocol.github.io/pcp/schemas/0.3/<file>` and lives in
[`schemas/0.3/`](schemas/0.3/). Examples that validate against them are in
[`examples/0.3/`](examples/0.3/); run `python3 scripts/validate_schemas.py`
to check both. The MCP extension id of PCP is `io.github.pcp-protocol/pcp`.

### Changes from v0.2 (so far)

- A context has a **kind** (`personal`, `work`, `team`), one **controller**,
  and typed **principals** (§1). A personal context is a team of one and
  needs none of the team features.
- Discovery has a JSON Schema, a root document for multi-context hosts with
  a context URL template, `kind`, a conformance claim, and an `encryption`
  vocabulary built on key custody. `sse_endpoint` is gone (§2).
- Team contexts MAY have a team profile. `profile_update` is an RFC 7396
  merge patch. Empty profiles and reserved namespaces are defined (§4).
- Memory pages have a path grammar, a frontmatter JSON Schema, RFC 3339 UTC
  timestamps, transaction time, retention, partitions, review state and
  server-stamped provenance. Retrieval is implementation-defined with
  required behaviors (§5).
- Tools are renamed to `<part>_<verb>` and gain titles, annotations, output
  schemas and `isError` failures. New: `memory_propose`, `review_list`,
  `review_resolve`, `partition_list`, `audit_list`. Slots are reserved for
  documents and handoffs extensions (§6).
- New scopes `memory:propose`, `memory:review`, `memory.sensitive:write`,
  `profile.team:*` and `audit:read`, a written-out hierarchy, the partition
  ACL rule, delegated reads, and an audit entry schema without content (§7).
- Export, import and erasure are specified (§8): an archive layout with a
  checkable manifest (SHA-256 for every file, counts, declared omissions),
  a context descriptor with principals, partitions and access lists,
  archive-level and file-level encryption declarations, restore and import
  modes with conflict, idempotency and mapping rules, a round-trip
  guarantee, erasure with a receipt, and retention of expired pages. New
  optional tools `export_create` and `erase_request`, and the scope
  `erase:write`.
- Appendix A maps a team memory server (Agent Brain) onto PCP.

---

## 1. Overview *(v0.3)*

A **PCP context** is a bounded body of AI context with one controller. It has
up to three parts:

| Part | What it holds | Section |
|---|---|---|
| **Profile** | Structured facts about the person (core profile) or the team (team profile), plus consent-gated extension namespaces (health, legal, and so on) | §4 |
| **Memory** | Long-term memory as Markdown pages with YAML frontmatter: lifecycle, validity, provenance, and for teams partitions and review state | §5 |
| **Connections** | Live bridges to external sources (Notion, email, tasks) exposed as namespaced MCP tools | §6.4 |

A **PCP server** is any server that stores one or more contexts and serves
each over MCP per §3. It MAY be self-hosted (localhost, home server), run by
a hosting provider, or run as managed SaaS. The wire behavior is identical.

### 1.1 Design principles

1. **The controller owns the context.** Export (§8) is mandatory. A server
   that cannot fully export a context is non-conforming.
2. **Consent is per category, not all or nothing.** Sensitive data lives in
   extension namespaces and sensitive pages with their own OAuth scopes
   (§4.5, §7).
3. **One endpoint.** A client configures exactly one URL and one OAuth flow
   per context; everything else is negotiated.
4. **MCP-native.** PCP adds no new transport. Anything that speaks MCP can
   consume a PCP context.
5. **Host-agnostic.** No feature may depend on a specific cloud vendor. The
   reference deployment target is one Linux box.
6. **Honest claims.** Every claim a server makes about itself (encryption,
   export, conformance) is defined by this specification and checkable.
   A server MUST NOT describe a property with a term this specification
   defines differently.

### 1.2 Contexts, kinds and controllers

Every context has a **kind**:

| Kind | What it is | Typical controller |
|---|---|---|
| `personal` | One person's own context | That person |
| `work` | One person's context for their working life, kept apart from their personal context | The person, or their organization (defined in §3 and §9, v0.3 Phase 4) |
| `team` | A context shared by a group of people and agents | The organization or person who administers it |

Work and personal context are **separate contexts**, each with its own kind,
controller, grants and keys. A server MUST NOT mix them inside one context.
A host MAY serve many contexts (§2.2); a client is bound to one context per
grant.

Every context has exactly one **controller**: the principal (§1.3) that
decides who may access the context and that may export it and erase it. The
host that runs the server is not the controller unless it is the same party.

### 1.3 Principals

A **principal** is an identity that acts inside a context: someone or
something whose reads and writes the context can attribute. Every OAuth token
a PCP server accepts is issued to a client acting as exactly one principal
(the token's subject).

Principals are named with a typed id, following the actor syntax of the Open
Knowledge Format (OKF):

```
principal = type ":" local-id
type      = "human" / "agent" / "org" / "service"
local-id  = 1*128( ALPHA / DIGIT / "." / "_" / "@" / "+" / "/" / "-" )
```

| Type | Meaning |
|---|---|
| `human` | A person with an account in the context |
| `agent` | A non-human actor with its own identity in the context, such as a named team agent |
| `org` | An organization; appears as a controller, never as the author of a write |
| `service` | A process the server runs inside the context, such as consolidation or retention, so its writes stay attributable |

Rules:

1. A local id MUST be stable for the life of the context and unique within
   its type. It SHOULD be an opaque id or a handle, not an email address.
2. The server derives the acting principal from the token. A server MUST NOT
   accept a principal named in tool input as the author of a write.
3. An OKF agent actor of the form `<agent>/<version>` maps to
   `agent:<agent>/<version>`.
4. Roles (who may review, administer or grant access) are server-defined.
   PCP sees their effect only through scopes and the access list (§7.3).

### 1.4 Optional features and the team of one

A context MAY use three optional features, declared in discovery `features`
(§2.3):

| Feature | What it adds | Section |
|---|---|---|
| `partitions` | More than one partition, with a per-principal access list | §5.3, §7.3 |
| `review` | Writes that become proposals until a reviewer approves them | §5.4 |
| `delegation` | Agents that act for a human, reading with the intersection of both | §7.4 |

**A personal context is a team of one.** It has one human principal, who is
the controller; one partition, `default`; and no review queue. Every rule in
this specification has a defined meaning for that case: absent `partition`
means `default`, absent `review` means approved, and every principal has
`read`, `propose` and `write` on `default` within its token's scopes (§7.3). A server that serves only
personal contexts implements none of the optional features and is still
conforming.

## 2. Discovery *(v0.3: fields; authorization in Phase 4)*

### 2.1 Single-context servers

A server that hosts one context MUST serve a **context document** at:

```
GET /.well-known/pcp.json
```

```json
{
  "pcp_version": "0.3",
  "kind": "personal",
  "mcp_endpoint": "https://ctx.example.com/mcp",
  "authorization_server": "https://ctx.example.com",
  "profile_extensions": ["pcp.health"],
  "connections": ["notion"],
  "conformance": ["personal"],
  "export": true,
  "encryption": {
    "key_custody": "user",
    "readable_by": ["principals", "host_in_request"]
  }
}
```

### 2.2 Multi-context hosts

A host MAY serve many contexts under distinct base URLs, for example
`https://host.example/pcp/<context>`. Such a host:

1. MUST serve a context document for each context at
   `<context-base>/.well-known/pcp.json`, whose `mcp_endpoint` is that
   context's endpoint.
2. MUST serve a **root document** at the origin's `/.well-known/pcp.json`
   with `"multi_context": true` and a `context_url_template`: an RFC 6570
   level 1 URI Template with the single variable `{context}`, which expands to
   a context's base URL. The root document describes the host, not a context:
   it MUST NOT carry `mcp_endpoint` or `kind`.
3. MUST answer an unknown context's discovery URL with HTTP 404 and a JSON
   body, never with an HTML page or a redirect.

```json
{
  "pcp_version": "0.3",
  "multi_context": true,
  "context_url_template": "https://host.example/pcp/{context}",
  "authorization_server": "https://host.example"
}
```

Everything else in this specification applies per context, not per origin.

### 2.3 Fields

Schema: [`schemas/0.3/discovery.schema.json`](schemas/0.3/discovery.schema.json).
Clients MUST ignore fields they do not understand.

| Field | Context doc | Root doc | Meaning |
|---|---|---|---|
| `pcp_version` | REQUIRED | REQUIRED | The PCP version the server implements: `"0.3"` |
| `kind` | REQUIRED | absent | `personal`, `work` or `team` (§1.2) |
| `mcp_endpoint` | REQUIRED | absent | The context's MCP Streamable HTTP endpoint |
| `encryption` | REQUIRED | absent | Key custody and who can read plaintext (§2.4) |
| `multi_context` | absent | REQUIRED, `true` | Marks a root document |
| `context_url_template` | absent | REQUIRED | URI Template for context base URLs (§2.2) |
| `authorization_server` | OPTIONAL | OPTIONAL | Kept from v0.2. §3 (Phase 4) defines discovery through protected resource metadata |
| `server_card` | OPTIONAL | OPTIONAL | URL of the MCP server card for the endpoint |
| `profile` | OPTIONAL | absent | `core`, `team` or `none` (§4). Default: `core` for personal and work, `team` for team |
| `profile_extensions` | OPTIONAL | absent | Extension namespaces present (§4.5), so clients can request the right scopes |
| `connections` | OPTIONAL | absent | Connection ids present (§6.4) |
| `extensions` | OPTIONAL | absent | Tool extensions implemented, by reverse-DNS id (§6.5) |
| `features` | OPTIONAL | absent | Optional features in use: `partitions`, `review`, `delegation` (§1.4) |
| `conformance` | OPTIONAL | absent | Conformance profiles claimed: `personal`, `team` (§10) |
| `export` | OPTIONAL | absent | `true` claims the four commitments of §8.1: full export, a checkable archive, restore and import of the server's own archives, and no host-held archive keys. A server MUST NOT emit `true` otherwise |

`sse_endpoint` is removed: the HTTP+SSE transport is deprecated in MCP.
Servers SHOULD NOT emit it, and clients MUST ignore it.

### 2.4 Encryption vocabulary

`encryption` states who holds the keys and who can read plaintext. The
vocabulary is fixed here so that a claim means the same thing on every
server; §9.1 (Phase 4) adds the custody rules a claim commits the server to.

| Field | Values | Meaning |
|---|---|---|
| `key_custody` | `host` | The host holds keys that decrypt the context without any principal taking part. This includes storage that is encrypted on disk with host-held keys. |
| | `user` | The keys are wrapped by secrets only the context's principals hold. The host can decrypt only while serving a request that a principal authorized, and keeps neither keys nor plaintext afterwards. |
| | `device` | Plaintext and keys exist only on principals' devices. The host stores and serves ciphertext. |
| `readable_by` | array of `principals`, `host_in_request`, `host`, `escrow` | Every party that can obtain plaintext. `principals` (authorized principals through their clients) is always listed. `host_in_request`: the host, only while serving an authorized request. `host`: the host at any time. `escrow`: a third party holding a recovery share. |
| `e2e` | boolean, default `false` | End-to-end encrypted. MAY be `true` only when `key_custody` is `device`. |

Consistency rules, enforced by the schema: `host` custody lists `host` in
`readable_by`; `user` custody lists `host_in_request` and not `host`;
`device` custody lists neither. Indexes, embeddings, caches and any other
data derived from content **are content**: the declaration covers them, and
a server whose derived data a wider set of parties can read MUST declare that
wider set.

## 3. Transport and authorization *(pending, v0.2 text; rewritten in Phase 4)*

- Transport: **MCP Streamable HTTP** (REQUIRED).
- Authorization: **OAuth 2.1 with PKCE** (REQUIRED), per the MCP authorization specification.
- **Dynamic Client Registration** (RFC 7591) is REQUIRED, so any new chatbot can onboard without manual client setup. *(Phase 4 changes this to CIMD SHOULD, DCR MAY.)*
- Tokens are issued per client grant and MUST be individually revocable (§7.5).
- Servers MUST reject any non-TLS connection except on localhost.

### 3.1 The consent screen

During authorization the server MUST present a human-readable consent screen
listing each requested scope (§7.1) in plain language, for example: *"Claude
on Dana's iPhone requests: read your core profile, search your memory, read
your Notion. It is NOT requesting: health, legal, family data."* Scopes not
granted MUST NOT be silently added to future token refreshes. In a context
with partitions, the consent screen SHOULD also name the partitions the
signing-in principal can access.

## 4. Profile *(v0.3)*

A context has at most one profile document: the **core profile** (personal
and work contexts) or the **team profile** (team contexts). Discovery
`profile` says which (§2.3). Extension namespaces (§4.5) sit next to it.

### 4.1 Core profile (`profile.core`)

The core profile is a single JSON document conforming to
[`schemas/0.3/profile.core.schema.json`](schemas/0.3/profile.core.schema.json).
It is intentionally small and contains only low-sensitivity, high-utility
fields:

- `name`, `preferred_name`, `pronouns`
- `languages` (ordered by preference, with per-context rules, for example
  "German with family, English at work")
- `locale`, `timezone`, `location.city` (coarse; no street address in core)
- `communication`: tone, verbosity, formatting preferences for AI output
- `work`: role, organization, professional context (optional)
- `ai_instructions`: free-text standing instructions to any assistant

Every server MUST support `profile.core` for personal and work contexts.
The schema's `pcp_version` accepts every version a v0.3 server accepts
(`0.1`, `0.2`, `0.3`).

### 4.2 Team profile (`profile.team`)

A team context MAY have a team profile conforming to
[`schemas/0.3/profile.team.schema.json`](schemas/0.3/profile.team.schema.json):
the team's `name`, `purpose`, `controller`, `members` (principals with an
optional display name and server-defined role), working `languages`,
`timezone` and `ai_instructions`. A team context MAY instead have no profile
(`"profile": "none"`); everything else in this specification works without
one.

A team profile describes the team. Facts about individual members belong in
their own personal or work contexts, not here. A server MAY list only the
members the caller is allowed to see.

### 4.3 Updating a profile

`profile_update` (§6.2) applies an **RFC 7396 JSON Merge Patch** to one
document (`core`, `team` or an extension namespace):

1. Members in the patch replace members in the document; `null` deletes a
   member; arrays are replaced whole.
2. The result MUST validate against the document's schema. If it does not,
   the server MUST NOT change the document and MUST return an `isError`
   result with code `invalid_input` and the list of violations (§6.3).
3. The server sets `updated` and appends a change-log entry naming the
   changed members (as JSON Pointers), the principal, the client and the
   time. The change log MAY hold previous values only under the same
   protection (encryption, access) as the document itself.

### 4.4 Empty profile

A context MAY exist before its profile does. `profile_get` then returns
`"profile": null` with the context's `profile_type`. A server MUST NOT
return a placeholder document that fails the profile schema. `context_brief`
returns its other parts as usual.

### 4.5 Extension namespaces

Sensitive and specialized data lives in **extension namespaces**, each with
its own JSON Schema, its own OAuth scope pair (`profile.<ns>:read` and
`profile.<ns>:write`) and its own storage partition:

| Namespace | Contents (summary) | Sensitivity | Schema |
|---|---|---|---|
| `pcp.health` | Conditions, medications, allergies, providers, insurance | Special category | [Draft](schemas/0.3/pcp.health.schema.json) |
| `pcp.legal` | Legal matters, contracts of record, attorney contacts | High | Reserved |
| `pcp.family` | Family structure, dependents, important dates, emergency contacts | High | Reserved |
| `pcp.residency` | Citizenship(s), visas, residency status, tax residency | Special category | Reserved |
| `pcp.finance` | Accounts (references, not credentials), obligations, advisors | High | Reserved |
| `pcp.home` | Address(es), household, vehicles | Medium | Reserved |

Extension schemas are versioned independently and registered in
[`extensions/`](extensions/). Third parties MAY define extensions under their
own reverse-DNS prefix (`org.example.pets`); the `pcp.*` prefix is reserved
for this registry.

### 4.6 Rules for extensions

1. A server MUST NOT return extension data under a `profile.core` or
   `profile.team` scope.
2. A server MUST support enabling and disabling each extension independently.
3. Clients MUST NOT request extension scopes they do not need (enforced by
   the consent screen, not technically).
4. Special-category extensions (`health`, `residency`) SHOULD be stored
   encrypted with a separate key from the rest of the context.
5. **Reserved namespaces stay empty until their schema is published.** A
   server MUST NOT store, accept or return data in a `pcp.*` namespace whose
   schema is not published in this repository. In v0.3 only `pcp.health` has
   one; the others get schemas in v0.4.

## 5. Memory *(v0.3)*

Memory is long-term recall as **Markdown pages** with YAML frontmatter, one
topic per page. The body is plain Markdown. The frontmatter carries
lifecycle, validity, provenance and, for teams, partition and review state,
so a page can age, expire and cite its origin without leaving plain text, and
so memory from other tools imports cleanly ([`docs/interop.md`](docs/interop.md)).

### 5.1 Pages and paths

Every page has a **path**, unique in its context:

```
path    = segment *( "/" segment )            ; 255 characters at most
segment = first *63( ALPHA / DIGIT / "." / "_" / "-" )
first   = ALPHA / DIGIT / "_"
```

1. Paths are case-sensitive, but a context MUST NOT hold two paths that
   differ only in case, so an export unpacks on case-insensitive file
   systems. Clients SHOULD use lowercase.
2. No leading or trailing `/`, no empty segment, and no segment that starts
   with `.` (so never `.` or `..`).
3. A path is not a file name. Exports add `.md` (§8).
4. A server MUST reject an invalid path with `invalid_input` and MUST NOT
   rewrite it (no lowercasing, no replacing `.`). Dots are significant:
   `style/email-external.pt` is a valid path.
5. Segments that start with `_` are reserved for names defined by this
   specification or a convention it links (for example `style/_guide`).

**`_index`.** v0.2 described an `_index` page without saying who maintains it.
v0.3 drops it as a server duty: `memory_list` returns the listing. The path
`_index` stays reserved. If it exists it is an ordinary page holding an
overview written by a principal, and importers map a PACK `index.md` to it.
A server MUST NOT require or generate it.

### 5.2 Frontmatter

Schema: [`schemas/0.3/memory.page.schema.json`](schemas/0.3/memory.page.schema.json).
Frontmatter is validated as the JSON data model of YAML 1.2's core schema:
timestamps are strings, never native date types.

#### 5.2.1 Keys

REQUIRED: `title`, `updated`.

| Key | Values | Meaning |
|---|---|---|
| `title` | string | Short human-readable title. |
| `updated` | RFC 3339 UTC date-time (`Z`) | When the page last changed. Server-stamped. |
| `id` | opaque string | Optional server-assigned id, unique in the context and stable when the page moves. |
| `type` | `episodic` \| `semantic` \| `procedural` | Something that happened / a durable fact or preference / how something is done. |
| `tags` | array of strings | Free labels. Fine-grained categories from other tools go here. |
| `sensitivity` | `normal` \| `sensitive` (default `normal`) | `sensitive` pages are returned only under `memory.sensitive:read` (§7). Authoritative: see §5.2.2. |
| `lifecycle` | `active` \| `validated` \| `stale` \| `archived` (default `active`) | Ageing. Retrieval down-ranks `stale` and excludes `archived` by default; both remain exportable. |
| `confidence` | number 0 to 1 | How sure the context is that the content is true. |
| `importance` | number 0 to 1 | Salience for retrieval and retention. Not confidence. |
| `valid_from` / `valid_until` | RFC 3339 date or date-time | Valid time: when the fact is or was true. |
| `recorded_at` | RFC 3339 UTC date-time | Transaction time: when the context first recorded the page. Server-stamped on creation, never changed afterwards. |
| `expires` | RFC 3339 UTC date-time | Retention: after this instant the page MUST NOT be returned and SHOULD be deleted. Distinct from `valid_until`, which keeps the page as history. |
| `partition` | partition name (default `default`) | Which partition holds the page (§5.3). |
| `source` | object | Where the page came from: `origin`, `basis`, `principal`, `on_behalf_of`, `client`, `session`, `at` (below). |
| `derived_from` | array of paths | Pages this one was distilled from or supersedes. |
| `relations` | `[{ rel, target, confidence? }]` | Typed edges. `rel` is `supersedes`, `contradicts`, `refines` or `about`, or a namespaced relation `<prefix>:<name>` (for example `x-bm:pairs_with`) kept so imports stay lossless. Clients resolve conflicts with them; the server needs no graph engine. |
| `review` | object | Review state: `state`, `generated`, `verified`, `rejected` (§5.4). Absent means approved. |
| `x_import` | object | Set by import mode (§8.7.3): the source format, context, id, file hash and every source value without a PCP key. |
| `x_*`, `x-*` | any | Implementation or import keys. Preserved on round trip, never interpreted by other servers. |

`source` members:

| Member | Values | Meaning |
|---|---|---|
| `origin` | `chat` \| `agent` \| `connector` \| `import` \| `user` \| `consolidation` | `chat`: a client writing for a human during a conversation. `agent`: an agent principal writing under its own identity. `connector`: a connection. `import`: §8. `user`: a principal through the server's own interface. `consolidation`: a server process (§5.6). |
| `basis` | `provided` \| `observed` \| `inferred` | Whether the content was stated by a principal, recorded from activity, or derived by a model or rule. Lets a host tell which portability duties apply (for example GDPR Art 20). |
| `principal` | principal id | Server-stamped. The principal whose token created the page. |
| `on_behalf_of` | principal id | Server-stamped. The human an agent acted for (§7.4). |
| `client` | string | Server-stamped. The client that created the page (OAuth `client_id` or client name). |
| `session` | string | Client-supplied conversation or run id. |
| `at` | RFC 3339 date or date-time | When the source event happened. |

#### 5.2.2 Writing frontmatter

`memory_write` and `memory_propose` take the frontmatter as a JSON object
(`frontmatter`) next to the Markdown `body`. If `frontmatter` is absent and
the body begins with a YAML frontmatter block, the server MUST parse that
block as the frontmatter. If both are present and the body also begins with a
frontmatter block, the server MUST reject the write with `invalid_input`. A
server MUST NOT silently ignore frontmatter it was given.

**Sensitivity comes from the frontmatter.** There is no separate sensitivity
parameter. Updating an existing page without `sensitivity` or `partition`
keeps the stored value: an update never downgrades or moves a page by
omission. Modifying an existing `sensitive` page, and changing `sensitivity`
in either direction, requires `memory.sensitive:write` (§7.1). Creating a new
`sensitive` page needs only `memory:write` (or `memory:propose`): the client
hands data over and gains no access to it.

A write to a path that already holds a page the caller cannot read (a
sensitive page without `memory.sensitive:read`, or a page in a partition it
cannot read) MUST fail with `conflict` and the message that the path is
taken, and MUST NOT reveal anything else about that page. That a path is
taken is the only thing a write can learn.

#### 5.2.3 Server-stamped keys

The server sets `updated`, `recorded_at` (on creation), `id`,
`source.principal`, `source.on_behalf_of`, `source.client` and all of
`review`. Values a client supplies for these keys MUST be ignored: a client
makes a proposal with `memory_propose`, never by writing `review.state`, so a
server without the `review` feature never holds a proposed page. Restore
(§8.7.2) is the exception: archive values are kept as they are. Import
(§8.7.3) sets these keys as it describes. Both are recorded in the audit
log.

#### 5.2.4 Time

All server-stamped instants are RFC 3339 date-times in UTC with a `Z`
offset. Importers convert legacy `YYYY-MM-DD HH:MM:SS` values by assuming
UTC. Staleness from `valid_until` is computed at query time: a page whose
`valid_until` has passed is treated as `stale` by retrieval, and MUST NOT be
presented as current without its dates, but the server MUST NOT rewrite its
`lifecycle` for that reason.

### 5.3 Partitions

A **partition** is a named subset of a context's pages with its own access
list. Every page is in exactly one partition. Names match
`[a-z0-9][a-z0-9_-]{0,63}`. Every context has the partition `default`.

1. Access to a partition is decided by the server's per-principal access
   list, within the upper bound of the token's scopes (§7.3). Rights are
   `read`, `propose`, `write` and `review`.
2. A partition readable by one principal only is how a team keeps an agent's
   private working memory. PCP needs no separate flag for it.
3. Partitions and sensitivity are independent; both gates apply.
4. Moving a page to another partition (changing `partition`) requires
   `write` on both partitions.
5. A principal MUST NOT learn the names or contents of partitions it cannot
   read, including through counts, errors or search ranking.
6. `partition_list` (§6.2) returns the partitions the caller can access and
   its effective rights in each.

### 5.4 Review state

In a context with the `review` feature, some writes become **proposals**
that take effect only when a principal with the `review` right approves them.
Which partitions and principals need review is server policy.

**States.** `review.state` is `proposed`, `approved` or `rejected`. Absent
`review` means approved. Review provenance follows OKF:

- `generated: {by, at}`: who produced the content under review, and when.
- `verified: [{by, at}]`: each approval, appended.
- `rejected: {by, at}`: the rejection, when the state is `rejected`.

**The propose path.**

1. `memory_propose` always creates a proposal. For a path that does not
   exist, the proposal is a page at that path with state `proposed`. For an
   existing approved page, the proposal is a pending **revision** of it: the
   approved version stays what retrieval returns until the revision is
   approved, which then replaces it and sets `updated`.
2. `memory_write` to a partition where the caller holds `propose` but not
   `write`, or where the caller's writes need review, MUST either store the
   write as a proposal and say so (`applied: false`, `review_state:
   "proposed"`, a `revision` id), or fail with `forbidden`. It MUST NOT
   report a write as applied when it was not.
3. `review_list` returns pending proposals the caller may resolve or wrote.
   `review_resolve` applies a verb: `approve` or `reject`, or a namespaced
   verb the server documents (for example `x-ab:edit`). Each resolution
   writes an audit entry (§7.5).
4. Proposed and rejected pages and revisions MUST NOT be returned by default
   retrieval. They are returned only when the caller asks
   (`include_review`) and may see them: their author, or principals with
   `review` on the partition.
5. A server MAY resolve reviews only on its own management surface and not
   offer `review_resolve`. It MUST still keep the review fields.

Imports into a context with the `review` feature land as `proposed`
(§8.7.3 item 2).

### 5.5 Retrieval requirements

How a server retrieves memory is implementation-defined: keyword search,
SQL over views, vectors, or an in-memory search over pages decrypted for one
request. Whatever the method, `memory_search`, `memory_list` and
`context_brief` MUST:

1. **Filter before ranking.** Apply the partition access list, sensitivity
   and review visibility before ranking, counting or building snippets, so
   nothing the caller cannot read influences what it sees.
2. **Honor lifecycle and validity.** `memory_search` and `context_brief`
   return `active` and `validated` pages and current or undated pages first,
   and return `stale` or expired-validity pages only when asked
   (`include_stale`) or when nothing else matches, and then with their dates.
   `memory_list` lists stale pages with their `lifecycle` unless
   `include_stale` is `false`. All three exclude `archived` pages unless asked
   (`include_archived`), and never return pages past `expires`.
3. **Honor review.** As §5.4 item 4.
4. **Support `as_of`.** `memory_search` accepts `as_of`, an instant, and then
   answers as the context stood at that instant: only pages with
   `recorded_at` at or before it, judged valid by `valid_from` and
   `valid_until` at that instant. A server that keeps no page history
   evaluates `as_of` against current versions and reports
   `as_of_exact: false`.
5. **Treat indexes as content.** Indexes, embeddings, caches, snippets and
   summaries derived from pages are content: the same partition, sensitivity
   and encryption rules apply to them as to the pages (§2.4). A server MUST
   NOT keep a persistent derived structure that a party outside
   `readable_by` can read. Indexes are rebuildable and are not part of
   export.

Returned memory is data, not instructions. §9 (Phase 4) adds the framing
rule for returned content.

### 5.6 Consolidation (informative)

A server MAY run an extraction or consolidation pass that distills raw
memory into durable pages. Such pages carry `source.origin: consolidation`,
`source.principal: service:<name>` and `derived_from`. In a context with the
`review` feature they SHOULD enter as proposals. PCP only requires that
whatever pages exist conform to §5.2. *The trace is disposable; the page is
the artifact.*

### 5.7 The `style/` namespace

Pages under `style/` hold writing-style profiles
([`docs/style-profiles.md`](docs/style-profiles.md), informative). When a
page is created under `style/` without `sensitivity`, the server MUST store it
as `sensitive` and write `sensitivity: sensitive` into the stored
frontmatter, so the default travels with the page (§8.2 item 2). A write
that sets `sensitivity: normal` explicitly is honored.

## 6. Tool surface *(v0.3: names and team tools; MCP mechanics in Phase 4)*

### 6.1 Naming

Tool names are `<part>_<verb>`: lowercase, matching `^[a-z][a-z0-9_]{0,39}$`.
This is the only form that every MCP client and model API passes through
unchanged.

1. The parts `profile`, `memory`, `context`, `review`, `partition`, `audit`,
   `export` and `erase` are reserved for this specification. `doc` and
   `handoff` are reserved for the extension slots in §6.5.
2. A connection's tools are `<connection-id>_<verb>`. Connection ids match
   `[a-z][a-z0-9]{0,15}` (no underscore, so the name splits cleanly) and MUST
   NOT equal a reserved part.
3. In v0.3 a server MAY accept the v0.2 dotted names (`memory.search`) in
   `tools/call`, but MUST NOT list them in `tools/list`. This allowance ends
   in v0.4.

### 6.2 Standard tools

Input and output schemas: [`schemas/0.3/tools.schema.json`](schemas/0.3/tools.schema.json).
A server uses `$defs/<tool>_input` as a tool's `inputSchema` and
`$defs/<tool>_output` as its `outputSchema`.

The schemas in that file reference sibling schemas by relative URL. A
server MUST serve self-contained copies, with every `$ref` resolved, and the
top level of each `inputSchema` MUST be a plain object schema without
`oneOf`, `anyOf` or `allOf`, because model APIs reject top-level combinators.
Constraints that schemas then cannot express (for example "exactly one of
`path` or `id`") are enforced by the server and reported as `invalid_input`.

Every tool a PCP server lists, standard or not, MUST have a `title`, the
annotations below, and an `outputSchema`. A successful result MUST carry
`structuredContent` that validates against the output schema, and SHOULD
repeat it as JSON in a text content block for clients that ignore structured
content. Results with `isError: true` are not validated against the output
schema. `openWorldHint` is `false` for every standard tool.

| Tool | Title | Scope (upper bound, §7) | Read only | Destructive | Idempotent | Required when |
|---|---|---|---|---|---|---|
| `profile_get` | Get profile | `profile.core:read` or `profile.team:read`, plus `profile.<ns>:read` per extension | yes | no | yes | The context has a profile |
| `profile_update` | Update profile | `profile.core:write`, `profile.team:write` or `profile.<ns>:write` | no | yes (`null` deletes) | yes | The context has a profile |
| `memory_search` | Search memory | `memory:read` | yes | no | yes | Always |
| `memory_read` | Read memory page | `memory:read` | yes | no | yes | Always |
| `memory_list` | List memory pages | `memory:read` | yes | no | yes | Always |
| `memory_write` | Write memory page | `memory:write` (or `memory:propose`, §5.4) | no | yes (overwrites) | no (may create a revision per call) | Always |
| `memory_propose` | Propose memory change | `memory:propose` | no | no | no | The `review` feature is used |
| `review_list` | List pending reviews | `memory:read` | yes | no | yes | The `review` feature is used |
| `review_resolve` | Resolve a review | `memory:review` | no | no | yes | Optional (§5.4 item 5) |
| `partition_list` | List partitions | `memory:read` | yes | no | yes | The `partitions` feature is used |
| `context_brief` | Get context brief | Any of `profile.*:read`, `memory:read` | yes | no | yes | Always |
| `audit_list` | List access log | `audit:read` | yes | no | yes | Always |
| `export_create` | Export context | `export:read` | yes | no | no | Optional (§8.1 item 2) |
| `erase_request` | Erase memory | `erase:write` | no | yes | yes | Optional (§8.9.4) |

Behavior beyond the schemas:

- **`profile_get`** returns the context's profile document or `null` (§4.4)
  and the extension documents the token covers.
- **`profile_update`** applies a merge patch (§4.3).
- **`memory_read`** accepts exactly one of `path` or `id`, and optionally a
  `revision` so a reviewer can read a proposal. It returns the frontmatter
  and the body separately, and the number of pending revisions the caller
  may see.
- **`memory_list`** lists page summaries, filtered by path prefix,
  partition, `type`, lifecycle and review state. It replaces "read `_index`".
- **`memory_write`** creates or replaces a page (§5.2.2, §5.4). With
  `expected_updated` it fails with `conflict` unless the stored `updated`
  matches.
- **`context_brief`** is the first call of a conversation: the profile and
  the most relevant memory the token can read, within a token budget. It
  MUST NOT fail because the token lacks one of the scopes; it returns the
  parts the token covers and names the rest in `omitted`. In a team context
  it MAY include the caller's partitions.
- **`audit_list`** returns audit entries (§7.5) the caller may see: by
  default the controller sees all entries and other principals see their
  own.

- **`export_create`** bundles what the token can read into an archive
  (§8.1 item 2) and returns its status and, when ready, a short-lived
  download URL, also as a `resource_link` content block.
- **`erase_request`** erases by subject or by page (§8.9.4). It defaults
  to a dry run.

### 6.3 Errors

A tool that fails returns a result with `isError: true`, never a JSON-RPC
error. JSON-RPC errors are for protocol failures only: an unknown tool, or
arguments that are not an object.

1. The first text content block MUST start with the error code followed by
   `: `, for example `not_found: no page at that path`. This keeps the code
   visible on servers whose framework passes only a message through.
2. The result SHOULD also carry `structuredContent` of the form
   `{"error": {"code", "message", "required_scopes"?, "violations"?}}`
   (`$defs/error`).

| Code | When |
|---|---|
| `invalid_input` | Input fails the schema, a path is invalid, or a profile patch would produce an invalid document (with `violations`) |
| `not_found` | The object does not exist, **or the caller may not know it exists** |
| `forbidden` | The caller may see the object but lacks the right (with `required_scopes` when a scope is missing) |
| `conflict` | `expected_updated` does not match, a case-only path collision (§5.1), or the path is taken by a page the caller cannot read (§5.2.2) |
| `too_large` | Input or result exceeds a server limit |
| `rate_limited` | Too many calls |
| `locked` | The context's keys are not available for this request (§2.4) |
| `unsupported` | An optional feature or verb the server does not implement |
| `internal` | Anything else |

Reads of pages in partitions the caller cannot read, and of sensitive pages
without `memory.sensitive:read`, MUST produce `not_found`, never `forbidden`
(writes: §5.2.2). The
HTTP-level step-up for a missing scope (403 `insufficient_scope`) is defined
in §3 (Phase 4).

### 6.4 Connection tools

Connection tools are namespaced by connection id (`notion_search`,
`email_search_threads`, `tasks_create`) and gated by `conn.<id>:read` and
`conn.<id>:write`. Their annotations set `openWorldHint: true`. Connection
tool schemas are out of scope for v0.3 (each connector documents its own),
but the naming and scope-gating rules are normative.

### 6.5 Extension tools and reserved slots

An extension adds tools that do not change what memory means. Each extension
has a reverse-DNS id, listed in discovery `extensions`, and a tool part.
Extension tools follow §6.1 to §6.3 and are gated by `ext.<part>:read` and
`ext.<part>:write`.

PCP reserves two slots, for designs owned by the implementers who need them:

| Slot | Tool part | Scope | Covers |
|---|---|---|---|
| Shared documents | `doc` | `ext.doc:read`, `ext.doc:write` | Documents written by several principals: outlines, sections, leases, versions, stages, section review |
| Handoffs | `handoff` | `ext.handoff:read`, `ext.handoff:write` | Structured requests from one principal to another, with linked memory and a resolution |

A slot is filled by registering an extension in [`extensions/`](extensions/)
with its id, its tools and schemas, and how its data appears in an export
(§8.5). Until a slot is filled, a server MAY expose `doc_*` or `handoff_*`
tools only if it lists its extension id in discovery. Data in an extension
MUST still respect partitions, sensitivity and the audit rules.

## 7. Scopes, consent and audit *(v0.3: scopes, partitions, audit fields; step-up in Phase 4)*

### 7.1 Scope grammar and hierarchy

```
profile.core:read      | profile.core:write
profile.team:read      | profile.team:write
profile.<ns>:read      | profile.<ns>:write          e.g. profile.health:read
memory:read            | memory:propose | memory:write | memory:review
memory.sensitive:read  | memory.sensitive:write
conn.<id>:read         | conn.<id>:write             e.g. conn.notion:read
ext.<part>:read        | ext.<part>:write            e.g. ext.doc:write
audit:read
export:read
erase:write
```

For a namespace `pcp.health` the scope uses its last label: `profile.health`.
Third-party namespaces use the full name: `profile.org.example.pets:read`.

The only implications are these:

| Scope | Implies |
|---|---|
| `memory:write` | `memory:propose` |
| `memory.sensitive:read` | Nothing on its own. Together with `memory:read` it extends reads to sensitive pages. |
| `memory.sensitive:write` | Nothing on its own. Together with `memory:write` (or `memory:propose`) it extends writes to sensitive pages, including changing `sensitivity`. |
| `memory:review` | Nothing on its own. Together with `memory:read` it allows resolving proposals the caller can read. |

No `:write` scope implies the matching `:read`, so write-only clients (for
example an ingestion connector) are possible. No scope implies `audit:read`,
`export:read`, `erase:write`, `conn.*`, `ext.*` or extension namespaces. A server SHOULD NOT
grant a qualifier scope (`memory.sensitive:*`, `memory:review`) without its
base scope.

Tokens carry PCP scope strings. A server whose clients cannot request
granular scopes MAY grant a fixed set, but MUST state that set in the token's
`scope` and on the consent screen.

### 7.2 Defaults

The RECOMMENDED default grant for a new chat client:

- Personal and work contexts: `profile.core:read`, `memory:read`,
  `memory:write`.
- Team contexts: `profile.team:read`, `memory:read`, `memory:propose`.

Sensitive scopes, `memory:review`, `audit:read`, `export:read` and
`erase:write` are opt-in per client.

### 7.3 Partition access

**OAuth scopes are the upper bound; the server's access list decides.** For
every operation the effective right of a principal on a partition is the
intersection of the token's scopes and the access list entry for that
principal and partition.

- In a context without the `partitions` feature (every personal context, and
  any work or team context that uses only `default`), every principal of the
  context has `read`, `propose` and `write` on `default`; `review` is server
  policy.
- In a context with the `partitions` feature, the access list defaults to
  deny: a principal has no right on a partition until it is granted.

- The access list is server state, administered by the controller or the
  roles it appoints. It is not expressed in OAuth scopes in v0.3.
- The server MUST enforce it in the data query itself (§5.5 item 1).
- Changes to the access list are audited (`categories: ["partition"]`).

### 7.4 Delegated access

When an agent principal acts for a human (the `delegation` feature), the
agent reads with the **intersection** of its own access and the human's:
the token's scopes, the agent's access list and the human's access list. An
agent MUST NOT read anything the human it acts for could not read, nor
anything the agent itself could not.

The server decides from the token whether a call is delegated, never from
tool input. Delegated writes are stamped with `source.principal` (the agent)
and `source.on_behalf_of` (the human), and audit entries carry both.

An agent acting under its own identity, with no human, uses its own access
list.

### 7.5 Grants and audit

- The server MUST provide a way (UI or API) to list active grants (client,
  principal, scopes, last used, and a stable grant id that survives token
  refresh) and to revoke each individually. A RECOMMENDED shape is drafted in
  [`docs/management-api.md`](docs/management-api.md) (informative).
- The server MUST keep an **access log** per context and expose it through
  `audit_list` under `audit:read`, and to the controller on the management
  surface.

Each audit entry conforms to
[`schemas/0.3/audit.entry.schema.json`](schemas/0.3/audit.entry.schema.json):
`id`, `at`, `principal`, `on_behalf_of`, `client`, `grant`, `channel`
(`mcp`, `management`, `import`, `export`, `system`), `action` (the tool name
or a management action), `categories`, `partitions`, `outcome`, `counts`,
`object_ids`, `review_verb` and `duration_ms`.

**Categories, never content.** An entry records which categories an action
touched: `profile.core`, `profile.team`, `profile.<ns>` (named like its scope,
so `profile.health` for `pcp.health`), `memory`,
`memory.sensitive`, `review`, `partition`, `audit`, `export`, `erasure`, `grant`,
`conn.<id>` and `ext.<part>`. An entry MUST NOT contain page bodies, titles,
paths, search queries, profile values, or unkeyed hashes of any of them.
`object_ids` holds opaque ids, never paths. Partition names are recorded;
controllers SHOULD NOT put sensitive words in partition names.

The server MUST write an entry for every tool call (including failed
calls; `outcome` is `ok` or the §6.3 error code), every management action,
every review resolution, and every access-list change.

`audit_list` MUST NOT become a side channel. When it returns an entry to a
principal other than the controller, it MUST remove the categories,
partitions and object ids that principal cannot currently read, so an entry
for a `not_found` read does not reveal that the target was sensitive or where
it lives.

## 8. Portability: export, import and erasure *(v0.3)*

The controller can take a whole context elsewhere (**export**), bring it
into another server (**restore** or **import**), and remove data from it and
from every copy the server controls (**erasure**). All three are core.

### 8.1 Export

1. **Full export.** A server MUST let the controller produce a full export
   of the context at any time on its management surface, without the host's
   approval and without contacting the host's staff. It MAY let roles the
   controller appoints do the same. A full export has `coverage: "full"`.
2. **Over MCP.** `export_create` (§6.2) is OPTIONAL and needs `export:read`.
   `export:read` is the right to bundle, not to read: the archive holds what
   the token could read with its other scopes, within the principal's access
   list (§7.3), and, with `audit:read`, the entries `audit_list` would return
   to it. It is `full` only when that is the whole context; otherwise it is
   `partial`.
3. **Partial exports.** A partial archive lists what it leaves out in
   `omitted` with reason `not_authorized`, by category only. It MUST NOT
   reveal names, counts or anything else about partitions or pages the
   requester cannot read (§5.3 item 5). A partial archive can be imported
   but not restored (§8.7).
4. **Archives a server keeps** for download are content: the context's
   encryption declaration covers them, they expire after a documented
   period (RECOMMENDED at most 7 days), and erasure deletes them (§8.9.2).
5. Every export writes an audit entry (`channel: "export"`, the categories
   exported, counts).

**What `export: true` commits a server to.** Discovery `export` (§2.3) is a
claim with four parts:

1. The controller can make a full export at any time (item 1), and its
   manifest validates and checks (§8.3).
2. A full archive holds everything the context holds, except what §8.2
   item 8 excludes by rule. Anything else left out is declared in
   `omitted`, and a server whose full exports routinely omit data with
   reason `unsupported`, `size_limit` or `error` MUST NOT claim `export:
   true`.
3. The server can restore its own full archives into an empty context and
   import its own archives into an existing one (§8.7).
4. A full archive is readable without the exporting host: plaintext, or
   encrypted to keys the controller holds (§8.4).

Export is mandatory (§1.1), so a conforming server emits `export: true`. A
server that emits `false` or omits the field says honestly that it is not
yet conforming.

### 8.2 Archive layout

An archive is a **zip** file or a **POSIX tar** file (ustar or pax),
optionally gzip-compressed. Importers MUST accept zip, tar and tar.gz.
Entries are regular files and directories only: no links, devices or
duplicate names. `manifest.json` is at the root, with no wrapper directory.
File names follow the manifest's `file_path` grammar. Names like
`<handle>-<date>.pcp.zip` are RECOMMENDED.

```
manifest.json                 the manifest (§8.3)
context.json                  kind, controller, principals, partitions, access lists
profile/core.json             or profile/team.json; absent when empty (§4.4) or none
profile/changes.jsonl         the profile change log (§4.3), if the server keeps one
profile/<namespace>.json      one per extension namespace with data, e.g. profile/pcp.health.json
memory/<path>.md              one file per page, including proposed and rejected pages
revisions/<path>/<n>.md       pending and rejected revisions of existing pages
history/<path>/<n>.md         earlier versions of pages, if the server keeps them
audit/log.jsonl               the access log
erasures/receipts.jsonl       erasure receipts
extensions/<id>/...           extension data (§8.5)
connections/<id>.json         connection configuration (§8.5)
```

1. **Pages.** One file per page at `memory/<path>.md`, with the path of
   §5.1. The file is the stored page: UTF-8 without a byte order mark, a
   YAML frontmatter block between two `---` lines, then the body. The
   frontmatter validates against the memory page schema (§5.2). A server
   that stores fields rather than documents MUST serialize them
   deterministically, so the same page always gives the same bytes (§8.8).
2. **Defaults that change access are explicit.** A page the server stored
   as `sensitive` by default (§5.7) says `sensitivity: sensitive` in its
   file. An absent `partition` means `default`, an absent `review` means
   approved.
3. **Review.** Proposed and rejected pages are exported with their
   `review` object. Pending and rejected revisions of an existing page
   (§5.4) are complete page files under `revisions/<path>/`, numbered from 1
   in the order they were proposed, and listed in `memory.revisions` with
   the page path, the server's revision id and `base_updated`, the
   `updated` of the version the revision was proposed against.
4. **History.** A server that keeps earlier versions of pages (for example
   to answer `as_of` exactly, §5.5 item 4) MUST export them under
   `history/<path>/`, numbered from 1 for the oldest, and list them in
   `memory.history`.
5. **Context descriptor.** `context.json` conforms to
   [`schemas/0.3/export.context.schema.json`](schemas/0.3/export.context.schema.json).
   It lists every principal, including removed principals that any file in
   the archive names, and every partition with its access list (§7.3). In a
   context without the `partitions` feature it lists `default` with an empty
   access list. Roles are informative.
6. **Audit.** `audit/log.jsonl` holds one audit entry (§7.5) per line. A
   full export includes every entry the server retains. A partial export
   includes the entries `audit_list` would return to the requester, or none
   without `audit:read`. If retention or limits cut the log,
   `audit.truncated` is `true`.
7. **Erasure receipts.** `erasures/receipts.jsonl` holds every receipt the
   context has (§8.9.3), one per line.
8. **Never in an archive**, and never listed in `omitted`:
   - credentials and grants: OAuth access and refresh tokens, authorization
     codes, application passwords, client secrets, connection tokens and API
     keys (`credentials_included` is fixed to `false`);
   - key material of the context, and the keys of the digests in §8.9;
   - indexes, embeddings, caches, snippets and summaries derived from pages
     (`index_included` is fixed to `false`; they are rebuilt on import);
   - pages past `expires`, deleted pages and erased data (§8.9, §8.10);
   - server configuration that is not context data, such as rate limits or
     worker settings.

   Grants are re-established after a move: export, restore, re-grant.

### 8.3 Manifest

Schema: [`schemas/0.3/export.manifest.schema.json`](schemas/0.3/export.manifest.schema.json).
The manifest is the one file the archive does not list; it is the root of
the checks. An exporter MUST produce, and an importer MUST verify before
writing anything, all of the following:

1. **Schema.** The manifest validates against the schema.
2. **Files, both directions.** Every file in the archive except
   `manifest.json` is listed in `files` with the SHA-256 of its bytes as
   they are in the archive and its size in bytes. Every listed file is
   present with that hash and size. No path is listed twice.
3. **Counts.** `memory.page_count` is the number of files under `memory/`
   (an encrypted page file counts). `memory.sensitive_page_count` is the
   number of those with `sensitivity: sensitive`. `memory.review_counts`
   and `memory.partition_counts`, when present, match the pages.
   `audit.entries` and `erasures.receipts` are the number of lines in their
   files. Every file named in `memory.revisions` and `memory.history`
   exists.
4. **Paths.** Every path matches the `file_path` grammar: relative, no
   segment starting with a dot (so never `..`), no backslash. Every page
   path under `memory/`, `revisions/` and `history/` is a valid §5.1 path.
   No two paths in the archive differ only in case.
5. **Documents.** Every page, revision and history file validates against
   the memory page schema, every audit line against the audit entry
   schema, every receipt against the receipt schema, `context.json`
   against its schema, and each profile document against the schema its
   manifest entry names.
6. **References.** Every partition a page names is in `context.json`.
   Every principal named in a page's `source` or `review`, in an audit
   entry or in a receipt is listed in `context.json`.
7. **Omissions.** `omitted` lists data that exists in the context and is
   not in the archive, by category (never by content), with a reason and,
   when the requester may know it, a count. It never lists data that does
   not exist. A server MUST NOT drop data silently: an archive that leaves
   something out without saying so is indistinguishable from a complete
   one.
8. **Constants.** `credentials_included` and `memory.index_included` are
   `false`.

[`scripts/validate_schemas.py`](scripts/validate_schemas.py) runs checks 1
to 6 on the example archives in [`examples/0.3/export/`](examples/0.3/export/).
Signed manifests are deferred to v0.4.

### 8.4 Encryption

Archives use the §2.4 vocabulary in two declarations.

1. **What the data was promised.** `context.encryption` in the manifest is
   the context's discovery `encryption` at export time. An importer SHOULD
   show it to the controller, and MUST warn before importing into a context
   whose `readable_by` includes a party the source's did not (for example
   from `user` custody into `host` custody).
2. **Archive level.** The whole archive is encrypted as one envelope, for
   example `<name>.pcp.zip.age`. This hides paths and the manifest. The
   envelope MUST use a self-describing format (age, OpenPGP or JWE, for
   example), so its holder can open it without the exporting host, and the
   manifest inside repeats the declaration as `archive_encryption`.
3. **File level.** Single files inside a plaintext archive are ciphertext.
   Such a file keeps its plaintext name plus the scheme's suffix
   (`profile/pcp.health.json.jwe`, `memory/notes/visa.md.age`), its `files`
   entry carries `encryption`, and its `sha256` is that of the ciphertext.
   File-level encryption leaves paths and the manifest readable; use
   archive-level encryption when paths themselves are sensitive.
4. **Keys.** A declaration names the scheme, the `key_source`, an optional
   `key_id` and `recipients`, the `key_custody` (`user` or `device`) and
   `readable_by` (`principals`, and `escrow` when a third party holds a
   recovery share). It never contains a key. `host` custody is not allowed:
   an archive only the exporting host can decrypt is a backup, not an
   export.
5. **Defaults.** When the context's custody is `user` or `device`, the
   exporter SHOULD encrypt the archive to a key the controller holds unless
   the controller asks for plaintext. Under `device` custody the host holds
   only ciphertext, so it exports page files with file-level declarations
   (`key_source: "device_key"`) for the controller's devices to decrypt.
   Ciphertext that the controller cannot decrypt with keys it holds is not
   an export: it goes in `omitted` with reason `encrypted_key_unavailable`.
   An exporter SHOULD offer file-level encryption for special-category
   namespaces (§4.6 rule 4) in an otherwise plaintext archive.
6. **Importers** verify hashes before decrypting. A file that fails to
   decrypt fails the archive in restore mode and is `invalid` in import
   mode.

### 8.5 Extension data and connections

1. Each tool extension (§6.5) that holds data in the context exports it
   under `extensions/<id>/`, where `<id>` is its reverse-DNS id, and lists
   it in the manifest's `extensions` with the number of records and, for
   the reserved slots, `slot: "doc"` or `slot: "handoff"`. Its files are in
   `files` like any other.
2. The layout under `extensions/<id>/` is the extension's, and its
   registration in [`extensions/`](extensions/) MUST describe it: the files
   and their schemas, how records reference pages (by path or `id`, both of
   which restore keeps), and how each record carries its partition and
   provenance. RECOMMENDED: one file per record; Markdown with frontmatter
   for prose (document sections, handoff bodies), using the §5.2 keys
   `partition`, `source`, `review`, `updated` and `recorded_at` with their
   §5.2 meanings; JSON otherwise.
3. Extension data follows the same exclusions (§8.2 item 8) and coverage
   (§8.1) as pages: a partial export includes only records the requester
   may read.
4. An importer that implements the extension imports its data under the
   same restore and import rules. One that does not MUST NOT drop it
   silently. In restore mode it SHOULD keep the files verbatim and include
   them unchanged in its own later exports; otherwise it reports them as
   `extensions_not_imported` and the controller decides. Kept but unserved
   extension data is still content: the encryption declaration covers it
   and erasure reaches it.
5. **Connections.** Only configuration travels: `connections/<id>.json`
   holds the connection's type, label, enabled state and settings without
   secrets, and its manifest entry says `credentials_included: false`.
   After a restore the controller authorizes each connection again on the
   new server.

### 8.6 Versioning

1. `pcp_version` in the manifest is the PCP version whose rules the
   content follows. An exporter writes the version it implements and does
   not write older formats.
2. `manifest_version` versions the archive layout: `"2"` for v0.3. Any
   change to the layout or the manifest increments it.
3. An importer MUST check both before writing anything, and MUST reject an
   archive whose versions it does not support with a report that names
   them. It SHOULD accept archives of the previous PCP version, converting
   them as that version's migration notes say (Appendix B, Phase 5). v0.2
   defined no archive, so a v0.3 importer has none to convert; v0.2 page
   frontmatter found in other tools' folders is handled by §8.7.3 item 8.
4. Schemas are versioned by path (`schemas/0.3/`), so an archive validates
   against the schemas of its own `pcp_version`.

### 8.7 Import

An importer reads an archive in one of two modes:

| Mode | Target | Requested by | Result |
|---|---|---|---|
| **restore** | An empty context | Its controller | The context as it was: paths, page bytes, server-stamped keys, principals, partitions, access lists, review state, audit log, receipts |
| **import** | Any context | A principal with `propose` or `write` on the target partitions | The pages, marked as imported, and in a context with the `review` feature, as proposals |

Restore is how a context moves between hosts (export, restore, re-grant).
Import is how memory from another context or another tool joins an
existing one.

#### 8.7.1 Checks before writing

1. **Unpack safely.** Reject the archive if an entry is absolute, has an
   empty or `..` segment, a NUL byte or a backslash, is a link or a device,
   repeats a name, or would land outside the target directory. Check sizes
   against limits before unpacking.
2. **Verify** every §8.3 check and the versions (§8.6). If any fails,
   write nothing and return a report with `status: "rejected"`.
3. **Check rights** on every target partition (§8.7.3 item 7) before
   writing.
4. A server SHOULD support `dry_run`: the report without any write.

#### 8.7.2 Restore

1. The target context MUST be empty: no pages, no profile document and no
   extension data. The requester MUST be its controller, and the archive
   MUST have `coverage: "full"`. The target takes the archive's `kind`.
2. **Everything is kept as it is.** Page, revision and history files are
   stored so that the server's own export of them meets §8.8: the same
   bytes on the same implementation, the same data and body bytes on
   another. Server-stamped keys keep their archive values (§5.2.3), and no
   `x_import` is added.
3. **Principals and partitions** are created from `context.json` with the
   same ids, partitions and access lists. Each principal is **unbound**
   until the controller binds it to an account or a credential on the new
   server, and an unbound principal cannot authenticate. The archive's
   controller becomes the target's controller, bound to the requester's
   account.
4. **Audit and receipts.** The audit entries and erasure receipts are
   imported with their ids and times, and the server appends an entry for
   the restore (`channel: "import"`, `action: "import.restore"`).
5. **Grants and connections** are not restored. Clients are granted again
   and connections authorized again.
6. **All or nothing.** A restore that fails part way MUST leave the target
   empty.

#### 8.7.3 Import

For each page in the archive, an importer in import mode:

1. **Marks the page as imported.** It sets `source.origin: import`;
   `source.principal` to the mapped author (item 7) or else the importing
   principal; `source.client` to the importing client; keeps
   `source.basis` and `source.session`; and sets `source.at` to the source's
   `source.at`, or else its `recorded_at`. It sets `recorded_at` to the
   import instant, so `as_of` stays true for this context. It keeps
   `updated` (converted per item 8). It adds `x_import` (§5.2.1): `format:
   "pcp"`, `at`, `exporter`, the source `context`, the source `id`, the
   file's `sha256`, the source `recorded_at`, `source`, and `review` and
   `partition` when it changed them.
2. **Applies review.** In a context with the `review` feature every
   imported page is a proposal: `review: {state: proposed, generated: {by,
   at}}`, with `by` the stamped `source.principal` and `at` the import
   instant; the source's review object moves to `x_import.review`. The
   target's own reviewers approve it (§5.4). A server MAY let its
   controller approve a whole import at once; the audit entry records it
   and each page gets `verified` by the controller. In a context without
   `review`, imported pages are approved, and source pages that are
   proposed or rejected are skipped (`skipped_review_state`) unless the
   requester asks for them as approved pages.
3. **Imports pages only.** Revisions and history belong to the source's
   review and versioning; they are reported, not imported. The source's
   audit log and receipts describe another context and are not imported.
   Profile documents are imported only on request, as an RFC 7396 merge
   patch onto the target's document (§4.3), with the scopes `profile_update`
   would need.
4. **Keeps sensitivity.** A `sensitive` page stays
   sensitive. Creating it needs `memory:write` or `memory:propose`;
   replacing an existing sensitive page also needs `memory.sensitive:write`
   (§5.2.2).
5. **Resolves path conflicts.** When the path is free the page is created.
   When it is taken:
   - by a page with the same idempotency key (item 6): `skipped_duplicate`;
   - by a page the importer cannot read: `skipped_conflict`, or `renamed`
     under `on_conflict: rename`, revealing nothing else (§5.2.2);
   - otherwise as the request's `on_conflict` says. `revise` (the default
     with `review`) makes the incoming page a pending revision of the
     existing one. `skip` (the default without `review`) reports
     `skipped_conflict`. `rename` stores it at `<path>-imported-<n>`, with
     the smallest free `n` and the last segment shortened to fit 64
     characters, and records the source path in `x_import.path`.
     `replace` overwrites the page; it needs `write` on the partition, and
     `memory.sensitive:write` if either page is sensitive.

   **Case collisions.** A path that differs only in case from an existing
   page, or from an earlier page of the same import, counts as taken. An
   archive with a case-only collision fails §8.3 check 4. For foreign
   folders from case-sensitive file systems, the later of two such paths is
   renamed.
6. **Is idempotent.** The idempotency key is the source path
   (`x_import.path`, or else the page's path) together with the SHA-256 of
   the file as received (`x_import.sha256`). A page whose key matches is
   skipped as a duplicate, so running an import twice changes nothing,
   while an edited source page (a new hash) is imported again under
   `on_conflict`.
7. **Maps principals and partitions.** Principal ids are local to a
   context (§1.3): `human:dana` in the source is not `human:dana` in the
   target. The request MAY carry a `principal_map` from source ids to target
   ids, set by the target's controller; mapped ids are written into
   `source.principal`, `source.on_behalf_of` and `review.generated.by`, and
   unmapped authors become the importing principal. `x_import.source`
   always keeps the source ids. The request carries a target `partition`
   for unmapped source partitions (default `default`) and MAY carry a
   `partition_map`. Import never creates partitions or changes access
   lists, and the importer needs `propose` or `write` on every target
   partition; if it lacks one, the import is rejected before anything is
   written.
8. **Converts timestamps.** Server-stamped instants (`updated`,
   `recorded_at`, `expires`, review `at`) become RFC 3339 UTC: values like
   `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS` without an offset are
   taken as UTC; values with an offset are converted; a date-only `updated`
   becomes midnight UTC; Unix seconds or milliseconds are converted.
   `valid_from` and `valid_until` keep their offsets. An unparseable value
   makes the page `invalid`. A missing `updated` takes the best source time
   the mapping names, or else the import instant; an importer never invents
   an earlier time than the source states. A converted value is not stored
   a second time in `x_import`.
9. **Skips** pages whose `expires` has passed (`skipped_expired`) and pages
   that match an erasure tombstone (`skipped_erased`, §8.9.5).
10. **Keeps unknown keys one way (settles S19).** A PCP archive has no
    unknown keys: every key is a §5.2 key or an `x_*` or `x-*` key, kept as
    it is. For other formats, values that have a PCP key are mapped and
    not repeated; values without one go once into `x_import.fields` under
    their source names; derived values (hashes, scores, embeddings) are
    dropped. The raw source frontmatter is not kept: it would restate
    mapped values, and the two copies drift apart as soon as the page is
    edited. An implementation that needs its own keys for its own round
    trip keeps them under its own `x_<name>` key (for example
    `x_agent_brain`).
11. **Writes an audit entry** (`channel: "import"`, `action:
    "import.merge"`, categories, counts; never paths).

Extension data follows §8.5 item 4 in both modes.

#### 8.7.4 Import report

An import returns a report conforming to `$defs/import_report` in the
manifest schema: mode, status (`complete`, `partial` or `rejected`), the
archive's exporter, `exported_at` and manifest hash, counts per outcome,
and per item outcomes with paths. The report goes only to the requester;
the audit entry carries the counts.

#### 8.7.5 Other formats

Importers for other tools' exports use import mode with
`x_import.format` naming the tool. The mappings for Agent Brain, Basic
Memory, Mem0, supermemory, OMP, Remnic and DTI conversations are in
[`docs/interop.md`](docs/interop.md) (informative). When a source has no
hashes, the importer computes `x_import.sha256` over the record as received
(for JSON records, over its RFC 8785 canonical form). An export produced by
a model summarizing memory is lossy by design; an importer SHOULD use the
source's lossless listing instead when one exists.

### 8.8 Round trip

The **body** of a page is the bytes after the line that closes its
frontmatter block. The guarantee:

1. **Same implementation.** Export a context (A), restore it into an empty
   context on the same implementation, and export again (B). Every file
   under `memory/`, `revisions/`, `history/`, `profile/` and `extensions/`,
   and `context.json`, is byte-identical in A and B. B's audit log is A's
   followed by the entries for the restore and the export.
2. **Across implementations.** Export from X, restore on Y, export from Y.
   For every page, revision and history file the body is byte-identical and
   the frontmatter is equal as data (the same keys and values after a YAML
   1.2 core-schema parse), including `updated`, `recorded_at`, `id`,
   `source`, `review`, `relations` and every `x_*` key; key order and
   quoting may differ. `context.json`, profile documents, audit entries and
   receipts are equal as JSON.
3. **Import is lossless but not a round trip.** It records the import
   (`source.origin`, `recorded_at`, `review`, `x_import`), so the frontmatter
   changes, but every source value is in the imported page or in its
   `x_import`, and the body is byte-identical.

So a server that stores fields rather than documents MUST keep, for every
restored or imported page, each frontmatter key it has no column for and
the body bytes as received.

### 8.9 Erasure

Erasure removes data from the context, from what was derived from it, and
from every copy the server controls, and leaves a **receipt** that proves it
ran without saying what was erased. Every conforming server MUST support it
on its management surface.

#### 8.9.1 Requests

1. The controller requests erasure, or a role the controller appoints.
   Kinds:
   - `subject`: everything whose content matches a subject string, in every
     partition;
   - `pages`: pages named by path or `id`;
   - `context`: the whole context, which also revokes every grant and ends
     the context.
2. `include_derived` (default `true`) extends the targets to pages whose
   `derived_from` names a target, transitively, and to consolidation output
   built from them.
3. The server documents its matching for `subject`. It SHOULD match the
   phrase case-insensitively in titles, bodies, tags and `x_*` values, and
   MUST NOT widen a multi-word subject to its single words.
4. A server SHOULD offer a dry run that returns counts per store and
   deletes nothing.

#### 8.9.2 Order of operations

1. **Collect** every target: pages, their revisions and history, derived
   pages, extension records, and their index, embedding and cache entries.
   Also collect the stores the server does not delete from directly:
   backups, replicas, workers and queues.
2. **Audit first.** Write the audit entry for the request synchronously
   (`action: "erase.request"`, `categories` including `erasure`, the
   receipt id in `object_ids`). If it cannot be written, abort and delete
   nothing.
3. **Delete** the targets and their derived entries, and every archive the
   server holds that was made before the erasure (§8.1 item 4), since any of
   them may contain the targets. Then ask the other stores to delete, and
   collect their results.
4. **Check for residue.** Run the same matching again over the context and
   the remaining archives, and record what it finds per store.
5. **Write the receipt** and a completion audit entry (`action:
   "erase.complete"`).
6. Archives already downloaded are out of the server's reach. The
   management surface SHOULD tell the controller that archives made before
   the erasure still contain the erased data.

#### 8.9.3 Receipt

Schema: [`schemas/0.3/erasure.receipt.schema.json`](schemas/0.3/erasure.receipt.schema.json).
A receipt holds the kind, the requester, the request and completion
times, counts per store, residue per store, the propagation result per
store and a status:

- `complete`: no residue and every store confirmed;
- `pending_propagation`: no residue, but a store will delete later, with
  `due_by` (for example a backup that ages out at the end of its retention);
- `residue_found`: residue remains, or a store failed.

A receipt MUST NOT contain the subject, matched paths, titles or content,
nor an unkeyed hash of any of them: a plain SHA-256 of a short name is
reversed by guessing. For `subject` erasures it carries `subject_digest`, an
HMAC-SHA-256 of the normalized subject under a per-context key the server
keeps and never exports, so the management surface MAY confirm whether a
given subject was erased. Receipts are kept for the life of the context,
are readable by the controller, and travel in exports (§8.2 item 7).

#### 8.9.4 The `erase_request` tool

`erase_request` (§6.2) is OPTIONAL. It needs `erase:write`, and the
principal MUST be the controller or hold a role the controller appointed
for erasure: the scope is the upper bound, the server decides (§7.3). It
offers kinds `subject` and `pages` only; whole-context erasure stays on the
management surface. `dry_run` defaults to `true`, so a first call never
deletes, and the tool is annotated destructive. A real run returns the
receipt.

#### 8.9.5 Tombstones

An archive made before an erasure still holds the erased data. To keep an
import from bringing it back, a server SHOULD keep, with each receipt, keyed
digests (under the same key) of each erased page's file and of its path and
body. When it does, import mode MUST skip pages that match
(`skipped_erased`). Tombstones are keyed digests, not content, and are not
exported, because their key is not.

### 8.10 Retention and deleted pages

1. After a page's `expires` (§5.2.1) it MUST NOT be returned (§5.5) or
   exported, and SHOULD be deleted, with its revisions, history and derived
   entries, within the server's documented retention interval
   (RECOMMENDED 24 hours).
2. Retention is not erasure. It removes the expired page, not pages
   derived from it (they carry their own `expires`), and leaves no receipt.
   It runs as a server principal (`service:retention`) and writes one audit
   entry per run (`channel: "system"`, `action: "retention.sweep"`,
   `counts.deleted`).
3. A page a principal deleted is no longer part of the context. It MUST
   NOT be returned or exported. A server that keeps deleted pages for undo
   SHOULD purge them within a documented interval, and erasure reaches them.
4. Archives a server keeps for download expire as §8.1 item 4 says.

## 9. Security baseline *(pending, v0.2 text; rewritten in Phase 4; see SECURITY.md)*

- TLS everywhere (except localhost). At-rest encryption REQUIRED for
  extension namespaces marked special-category; RECOMMENDED for the whole
  context.
- Per-context isolation REQUIRED in multi-context deployments (separate
  process or container, or provably equivalent storage isolation).
- Source credentials stored encrypted, never logged, never exported.
- Rate limiting on the OAuth endpoints; tokens SHOULD be short-lived with
  refresh.

## 10. Conformance *(pending; profiles and suite in Phase 5)*

v0.3 defines two claimable profiles, written out in Phase 5:

- **Personal**: discovery (§2), transport and OAuth (§3), `profile.core`
  (§4.1, §4.3, §4.4), memory and the tools marked "Always" or "The context
  has a profile" (§5, §6), scopes and audit (§7), export, import and
  erasure (§8). None of the optional features in §1.4 is required.
- **Team**: the same without `profile.core`, plus whichever of `partitions`,
  `review` and `delegation` the context declares, each with its tools and
  rules.

Extensions and connections are optional; if present they MUST follow §4.5,
§4.6, §6 and §8.5.

A v0.2 checklist from the export branch is in
[`docs/conformance.md`](docs/conformance.md); Phase 5 rewrites it for v0.3.

## 11. Open questions *(pending; replaced by the v0.4 list in Phase 5)*

- Push vs pull ingestion contract for connections.
- Federation: can two PCP contexts share scoped context (family plans)?
- Standardizing the management surface; see the informative draft in
  [`docs/management-api.md`](docs/management-api.md).
- Memory conflict policy: is client-side resolution via `relations` (§5.2)
  enough, or does a server need a normative merge and supersession rule?
- Per-partition grants carried in OAuth (RFC 9396 rich authorization
  requests).
- Alignment target: if an MCP memory or profile extension or a live-serving
  portability standard is ratified, map PCP's memory and export onto it
  rather than maintain a parallel shape.

---

## Appendix A. Mapping a team memory server onto PCP (informative)

This appendix maps Agent Brain, an open-source WordPress plugin that gives a
team's agents shared, partitioned, reviewed memory, onto PCP v0.3. It is
built from the plugin source (commit `4f24875`, plugin 1.0.0 with
`wordpress/mcp-adapter` 0.6.1) on 2026-10-19. It is a guide for that
project's maintainers and for any similar server, not a requirement.

### A.1 Concepts

| Agent Brain | PCP v0.3 home | Status |
|---|---|---|
| One site (one brain) | A context of kind `team` (§1.2); controller `org:<site>` or the administering human | Core |
| `ab_agent` users | Principals `agent:<user_login>` (§1.3) | Core |
| `ab_curator`, administrator | Principals `human:<user_login>` with the `review` right and the `memory:review` scope | Core |
| Application passwords, OAuth tokens (`mcp` scope) | Grants (§7.5). Tokens carry PCP scope strings; a fixed set stated on the consent screen is allowed (§7.1) | Core; scope strings need a change |
| MCP `clientInfo.name` per session | `source.client` (§5.2.1) | Core |
| `ab_scope` terms, `ab_read_scopes` / `ab_write_scopes` user meta | Partitions (§5.3) named by term slug; the user meta is the access list (§7.3); default deny matches | Core |
| A scope only one agent can read | A partition with an access list of one (§5.3 item 2) | Core |
| Numeric ids instead of paths | Rows: path `memory/<type>/<id>` (`memory/episode/9131`), `id` `ab-memory-<id>`. Knowledge: `knowledge/<post_name>`; procedures: `procedures/<post_name>`; `id` `ab-knowledge-<post id>` or `ab-procedure-<post id>`. `memory_read` by `id` keeps numeric lookups working | Core |
| Raw memory row (`working`, `episode`) | Page with `type: episodic`, `partition`, `importance` (÷100), `source.origin: agent`, `source.principal` | Core |
| Raw memory row (`fact`) | Page with `type: semantic`, `source.origin: consolidation`, `source.basis: inferred` | Core |
| No title on rows | `title`: derived from the first line of content | Core; derive on read and export |
| `created` (`Y-m-d H:i:s` UTC), no `updated` | `recorded_at` and `updated` (RFC 3339 UTC); rows are immutable, so `updated` = `created` | Core; format conversion |
| Working-memory `expires` (48 h) | `expires` (§5.2.1), not `valid_until` | Core |
| Status `rolled_up` | `lifecycle: archived` plus `derived_from` on the roll-up | Core |
| Status `deleted` | Not part of the context: not returned, not exported (§8.10 item 3); erasure reaches it | Core; the exporter must filter it |
| `importance` 0 to 100 | `importance` 0 to 1 | Core |
| `agent_id`, `agent_written` | `source.principal`, `source.origin` | Core |
| `client` column | `source.client` | Core |
| `source_ids`, `wp_ab_memory_links` | `derived_from` (paths) | Core |
| `search_keys` | `tags`, or `x_agent_brain.search_keys` to keep them apart | Core |
| `ab_knowledge` (approved, WP status `private`) | Page, `type: semantic`, `lifecycle: validated`, `review.state: approved` | Core |
| `ab_procedure` | Page, `type: procedural` | Core |
| `ab_proposed`, `ab_rejected` post statuses | `review.state: proposed`, `rejected` (§5.4) | Core |
| `ab_proposing_agent` | `review.generated.by` | Core |
| `ab_reviewed_by`, `ab_reviewed_at`, `ab_review_outcome` | `review.verified[]` (approved), `review.rejected` (rejected); outcome `edited` maps to approve plus a namespaced verb such as `x-ab:edit` | Core |
| Review in wp-admin only | Allowed: `review_resolve` is optional (§5.4 item 5) | Core |
| Compression creating proposals | Consolidation (§5.6) by `service:compression` | Core |
| `context-briefing` | `context_brief` with `profile_type: team` or `none` | Core |
| `memory-search` | `memory_search`, filtered by partition before ranking (already done in SQL) | Core |
| `knowledge-read` | `memory_search` or `memory_list`, with `type` | Core |
| `memory-get` (numeric id) | `memory_read` by `id` | Core |
| `memory-write` | `memory_write` into a partition with `write` | Core |
| `<memory_data>` wrapper with provenance attributes | Untrusted-content framing, §9 (Phase 4) | Phase 4 |
| `wp_ab_audit` | Audit entries (§7.5). Add `client`, `grant`, `categories`; `args_hash` must be keyed or left out of `audit_list` | Core; fields to add |
| Forget with audit-first abort and receipt | Erasure with receipt (§8.9). The receipt's `subject_hash` must become a keyed `subject_digest` | Core; digest to change |
| Markdown export (`Modules/Forget/Exporter.php`) | §8 archive and manifest; every exporter field is mapped in [`docs/interop.md`](docs/interop.md) §2 | Core; exporter to extend |
| Backups (encrypted with a site key) | Not an export: host custody (§8.4 item 4). Erasure propagates to them (§8.9.2) | Out of scope |
| Handoffs (`ab_handoff`, `handoff-read`, `handoff-request-review`) | Handoffs extension slot (§6.5) | Extension |
| Artifacts, sections, leases, versions, stages, section review | Shared documents extension slot (§6.5) | Extension |
| Publish gate (`public-grant`), `publish_blocked` | Out of scope: publishing outside the context | Out of scope |
| Cloud worker, backups, ops jobs | Out of scope: host operations; their access to content is covered by `encryption.readable_by` (§2.4) | Out of scope |
| No team profile | `profile.team` (optional) from the site name, a purpose setting and the users holding `ab_agent` or `ab_curator`; or `profile: none` | Optional |

### A.2 Tools

| Agent Brain ability | PCP tool |
|---|---|
| `agent-brain/context-briefing` | `context_brief` |
| `agent-brain/memory-search` | `memory_search` |
| `agent-brain/memory-get` | `memory_read` (by `id`) |
| `agent-brain/knowledge-read` | `memory_search` (with a query; `q` becomes `query`) or `memory_list` (without), each with `type` |
| `agent-brain/memory-write` | `memory_write` |
| (none; proposals come from compression) | `memory_propose`: new, required with `review` |
| (none; wp-admin review queue) | `review_list` (new, required with `review`), `review_resolve` (optional) |
| (none) | `partition_list`, `audit_list`: new |
| `handoff-read`, `handoff-request-review` | `handoff_*` (extension) |
| `artifact-*`, `section-*` | `doc_*` (extension) |
| Forget (wp-admin) | Erasure on the management surface (§8.9); `erase_request` optional |
| Export (wp-admin download) | Full export on the management surface (§8.1); `export_create` optional |

### A.3 Implementing on WordPress

Checked against `wordpress/mcp-adapter` 0.6.1:

- **Names.** Abilities must be named `namespace/name`, which the adapter
  turns into `namespace-name`. The `mcp_adapter_tool_name` filter can return
  any name matching `^[a-zA-Z0-9_.-]+$` up to 128 characters, so a server can
  emit `memory_search` from an ability such as `pcp/memory-search`.
- **Titles and annotations.** The ability `label` becomes the tool `title`.
  `meta.annotations` (`readonly`, `destructive`, `idempotent`,
  `openWorldHint`) map to the MCP hints; the abilities need to declare them.
- **Output schemas.** `output_schema` becomes `outputSchema`, and array
  results are returned as `structuredContent` plus a JSON text block, which
  is what §6.2 asks for.
- **Errors.** A `WP_Error` becomes an `isError` result, but the adapter
  passes only its message, so the message must start with the PCP code
  (`not_found: ...`) to meet §6.3 item 1. The Abilities API's own
  input-validation and `permission_callback` failures produce messages
  without that prefix, and a permission failure cannot become `not_found`.
  So keep `input_schema` permissive, let `permission_callback` accept any
  authenticated principal, and do validation and access checks inside
  `execute_callback`; or rewrite results in the `mcp_adapter_tool_call_result`
  filter. Structured error content needs that filter or an adapter change.
- **Schema features.** The WordPress REST validator ignores `$ref`, `allOf`
  and `if`, so register dereferenced schemas (§6.2) and validate frontmatter
  in `execute_callback` against the full memory page schema.
- **Sessions.** The adapter's sessions are fine for v0.3: no PCP semantics
  depend on a session.
