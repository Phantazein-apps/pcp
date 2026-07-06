# HCS Specification — v0.1-draft

**Hosted Context Server protocol — format & server behavior**

Status: DRAFT · License: Apache 2.0 · Last updated: 2026-07-05

The key words MUST, SHOULD, MAY are to be interpreted as in RFC 2119.

---

## 1. Overview

An **HCS context** is one person's portable AI context. It has three parts:

| Part | What it holds | Section |
|---|---|---|
| **Profile** | Structured facts about the person: identity, preferences, plus consent-gated sensitive categories (health, legal, family, residency, …) | §4 |
| **Memory** | Long-term unstructured memory: markdown pages + a semantic index (PACK-compatible) | §5 |
| **Connections** | Live bridges to external sources (Notion, email, messaging, tasks) exposed as namespaced MCP tools | §6 |

A **Hosted Context Server (HCS)** is any server that stores an HCS context and serves it over MCP per §3. An HCS MAY be self-hosted (localhost, home server), run by a hosting provider, or run as managed SaaS — the wire behavior is identical.

### 1.1 Design principles

1. **The user owns the context.** Export (§8) is mandatory. A conforming server that cannot fully export a context is non-conforming.
2. **Consent is per-category, not all-or-nothing.** Sensitive data lives in extension namespaces with independent OAuth scopes (§4.3, §7).
3. **One endpoint.** A client configures exactly one URL and one OAuth flow; everything else is negotiated.
4. **MCP-native.** HCS adds no new transport. Anything that speaks MCP can consume an HCS context.
5. **Host-agnostic.** No feature may depend on a specific cloud vendor. The reference deployment target is one Linux box.

## 2. Discovery

A server MUST serve a discovery document at:

```
GET /.well-known/hcs.json
```

```json
{
  "hcs_version": "0.1",
  "mcp_endpoint": "https://ctx.example.com/mcp",
  "sse_endpoint": "https://ctx.example.com/sse",
  "authorization_server": "https://ctx.example.com",
  "profile_extensions": ["hcs.health", "hcs.legal", "hcs.family", "hcs.residency"],
  "connections": ["notion", "email", "tasks"],
  "export": true,
  "encryption": { "at_rest": true, "e2e": false }
}
```

- `mcp_endpoint` (Streamable HTTP) is REQUIRED; `sse_endpoint` is OPTIONAL (legacy clients).
- `profile_extensions` and `connections` advertise what this context contains, so clients can request the right scopes up front.

### 2.1 Multi-context hosts

A single origin MAY host many contexts under distinct base paths
(`https://host.example/<handle>`). Such a host MUST serve a per-context
discovery document at `<context-base>/.well-known/hcs.json`
(e.g. `https://host.example/dk/.well-known/hcs.json`) whose `mcp_endpoint`
points at that context's endpoint. The origin-root `/.well-known/hcs.json`
then describes the host itself — same fields, no tenant specifics — and
SHOULD include `"multi_context": true`. Everything else in this spec applies
per context, not per origin.

## 3. Transport & authorization

- Transport: **MCP Streamable HTTP** (REQUIRED), SSE (OPTIONAL).
- Authorization: **OAuth 2.1 with PKCE** (REQUIRED), per the MCP authorization specification.
- **Dynamic Client Registration** (RFC 7591) is REQUIRED, so any new chatbot can onboard without manual client setup.
- Tokens are issued **per client-device pair** and MUST be individually revocable (§7.3).
- Servers MUST reject any non-TLS connection except on localhost.

### 3.1 The consent screen

During authorization the server MUST present a human-readable consent screen listing each requested scope (§7.1) in plain language, e.g. *"Claude on Dennis's iPhone requests: read your core profile, search your memory, read your Notion. It is NOT requesting: health, legal, family data."* Scopes not granted MUST NOT be silently dropped into future token refreshes.

## 4. Profile

### 4.1 Core profile (`profile.core`)

The core profile is a single JSON document conforming to [`schemas/profile.core.schema.json`](schemas/profile.core.schema.json). It is intentionally small and contains only low-sensitivity, high-utility fields:

- `name`, `preferred_name`, `pronouns`
- `languages` (ordered by preference, with per-context rules, e.g. "German with family, English at work")
- `locale`, `timezone`, `location.city` (coarse — no street address in core)
- `communication` — tone, verbosity, formatting preferences for AI output
- `work` — role, employer, professional context (optional)
- `ai_instructions` — free-text standing instructions to any assistant

Every conforming server MUST support `profile.core`. Everything else is an extension.

### 4.2 Extension namespaces

Sensitive and specialized data lives in **extension namespaces**, each with its own JSON Schema, its own OAuth scope, and its own storage partition:

| Namespace | Contents (summary) | Sensitivity |
|---|---|---|
| `hcs.health` | Conditions, medications, allergies, providers, insurance | Special category |
| `hcs.legal` | Legal matters, contracts of record, attorney contacts | High |
| `hcs.family` | Family structure, dependents, important dates, emergency contacts | High |
| `hcs.residency` | Citizenship(s), visas, residency status, tax residency | Special category |
| `hcs.finance` | Accounts (references, not credentials), obligations, advisors | High |
| `hcs.home` | Address(es), household, vehicles | Medium |

Extension schemas are versioned independently and registered in [`extensions/`](extensions/). Third parties MAY define extensions under their own prefix (`org.example.pets`); the `hcs.*` prefix is reserved for this registry.

### 4.3 Rules for extensions

1. A server MUST NOT return extension data under a `profile.core` scope.
2. A server MUST support enabling/disabling each extension independently.
3. Clients MUST NOT request extension scopes they do not need (enforced socially + by consent UI, not technically).
4. Special-category extensions (`health`, `residency`) SHOULD be stored encrypted with a separate key from the rest of the tenant data.

## 5. Memory

- Memory is a set of **markdown pages** with YAML frontmatter, PACK-compatible: an `_index` page, directory-like naming, one topic per page.
- The server maintains a **semantic index** (implementation-defined: sqlite-vec, LanceDB, HNSW, …) over pages; the index is derived data and is NOT part of export conformance (it can be rebuilt).
- Frontmatter REQUIRED keys: `title`, `updated`; RECOMMENDED: `tags`, `sensitivity` (`normal` | `sensitive`), `source`.
- Pages marked `sensitivity: sensitive` MUST only be returned under the `memory.sensitive:read` scope.

## 6. Standard tool surface

Tools are namespaced `<part>.<verb>`. A conforming server MUST expose (subject to granted scopes):

| Tool | Scope | Behavior |
|---|---|---|
| `profile.get` | `profile.core:read` (+ per-extension scopes) | Returns core profile; includes only extensions covered by the token's scopes |
| `profile.update` | `profile.core:write` etc. | Patch semantics; server keeps a change log |
| `memory.search` | `memory:read` | Semantic + keyword search over pages |
| `memory.read` | `memory:read` | Fetch a page by path |
| `memory.write` | `memory:write` | Create/update a page; server re-indexes |
| `memory.list` | `memory:read` | List pages / read `_index` |
| `context.brief` | `profile.core:read` + `memory:read` | One call returning a compact "who am I talking to" bundle: core profile + top-relevance memory. Intended as the first call a new session makes. |

Connection tools are namespaced by connection id: `notion.search`, `email.search_threads`, `tasks.create`, each gated by `conn.<id>:read` / `conn.<id>:write` scopes. Connection tool schemas are out of scope for v0.1 (each connector documents its own), but the **namespacing and scope-gating rules** are normative.

## 7. Scopes, consent, audit

### 7.1 Scope grammar

```
profile.core:read | profile.core:write
profile.<ext>:read | profile.<ext>:write     e.g. profile.health:read
memory:read | memory:write | memory.sensitive:read
conn.<id>:read | conn.<id>:write             e.g. conn.notion:read
export:read
```

### 7.2 Defaults

The RECOMMENDED default grant for a new chat client is: `profile.core:read`, `memory:read`, `memory:write` — nothing else. Sensitive extensions are opt-in per client.

### 7.3 Device management & audit

- The server MUST provide a way (UI or API) to list active grants (client, device, scopes, last used) and revoke each individually. A RECOMMENDED shape for this management surface is drafted in [`docs/management-api.md`](docs/management-api.md) (informative).
- The server MUST keep an **access log** per tenant: which client read which category, when. The log MUST be visible to the user and SHOULD be exposed as `audit.list` under a `profile.core:read` scope.

## 8. Portability: export & import

- `export:read` scope grants a full export: a tar/zip of all markdown memory pages, the profile core + extension JSON documents, connection *configuration* (never third-party credentials/tokens), and the audit log. Format: [`schemas/export.manifest.schema.json`] (v0.2).
- A conforming server MUST be able to **import** its own export format. Migrating hosts = export → import → re-grant connections.
- Third-party credentials (Gmail OAuth tokens, etc.) MUST NOT be included in exports.

## 9. Security baseline (normative summary — see SECURITY.md)

- TLS everywhere (except localhost). At-rest encryption REQUIRED for extension namespaces marked special-category; RECOMMENDED for the whole tenant.
- Per-tenant isolation REQUIRED in multi-tenant deployments (separate process/container or provably equivalent storage isolation).
- Source credentials stored encrypted, never logged, never exported.
- Rate limiting on the OAuth endpoints; tokens SHOULD be short-lived with refresh.

## 10. Conformance

A server may claim **"HCS v0.1 conformant"** if it implements: discovery (§2), transport + OAuth (§3), `profile.core` (§4.1), memory tools (§5, §6), scope enforcement (§7), and export (§8). Extensions and connections are optional; if present they MUST follow §4.2–4.3 and §6.

## 11. Open questions for v0.2

- E2E encryption tier (client-side keys; how does search work — searchable encryption vs client-side index?)
- Multi-profile (work persona vs personal persona) under one tenant
- Push vs pull ingestion contract for connections
- Formal export manifest schema + conformance test suite
- Federation: can two HCS instances share scoped context (family plans)?
- Standardizing the management surface — see the informative draft in [`docs/management-api.md`](docs/management-api.md)
