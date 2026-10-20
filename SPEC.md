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
| `export` | OPTIONAL | absent | `true` claims that §8 export and import work for this context. A server MUST NOT emit `true` otherwise |

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
server without the `review` feature never holds a proposed page. Import (§8) is the exception: imported values are kept
as they are, and the importer is recorded in the audit log.

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

Imports into a team context land as `proposed` (§8, Phase 3).

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
as `sensitive`. A write that sets `sensitivity: normal` explicitly is
honored.

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

Erasure (`erase_*`) and export tools are specified in §8 (Phase 3).

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
(§8). Until a slot is filled, a server MAY expose `doc_*` or `handoff_*`
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
`export:read`, `conn.*`, `ext.*` or extension namespaces. A server SHOULD NOT
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

Sensitive scopes, `memory:review`, `audit:read` and `export:read` are opt-in
per client.

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
`memory.sensitive`, `review`, `partition`, `audit`, `export`, `grant`,
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

## 8. Portability: export and import *(pending, v0.2 text; rewritten in Phase 3)*

- `export:read` scope grants a full export: a tar or zip of all Markdown
  memory pages, the profile and extension JSON documents, connection
  *configuration* (never third-party credentials or tokens), and the audit
  log. Format: the export manifest schema is not yet published; it is drafted
  for v0.3 (see [`docs/v0.3-plan.md`](docs/v0.3-plan.md), Phase 3). Phase 3
  also carries partitions, principals and review state, and adds erasure.
- A conforming server MUST be able to **import** its own export format.
  Migrating hosts means export, import, then re-grant connections.
- Third-party credentials (Gmail OAuth tokens and so on) MUST NOT be included
  in exports.

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
  has a profile" (§5, §6), scopes and audit (§7), export (§8). None of the
  optional features in §1.4 is required.
- **Team**: the same without `profile.core`, plus whichever of `partitions`,
  `review` and `delegation` the context declares, each with its tools and
  rules.

Extensions and connections are optional; if present they MUST follow §4.5,
§4.6 and §6.

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
| Status `deleted` | Not exported; erasure in §8 (Phase 3) | Phase 3 |
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
| Forget with audit-first abort and receipt | Erasure with receipt (§8, Phase 3, D11) | Phase 3 |
| Markdown export | §8 manifest and layout | Phase 3 |
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
