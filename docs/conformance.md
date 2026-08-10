# PCP conformance checklist — v0.2-draft

**Status: normative for the MUSTs it restates, informative in how it groups them.**
This document adds no requirements. It turns every MUST in [`SPEC.md`](../SPEC.md)
into something a person or a test suite can check, and says how to check it.

A server may claim **"PCP v0.1 conformant"** when every box in
[§A](#a-required)–[§E](#e-export) passes. Extensions (§F) and connections (§G)
are optional; if present, their boxes apply too.

Why this exists: §10 defines conformance by pointing at six sections, and those
sections contain 40-odd separate obligations. "We implement §7" is not a claim
anyone can verify — and portability only means something if two independent
implementations can be held to the same list.

---

## A. Discovery — §2

- [ ] **A1** `GET /.well-known/pcp.json` returns 200 with `Content-Type: application/json`.
- [ ] **A2** The document contains `pcp_version`, `mcp_endpoint`, `authorization_server`.
- [ ] **A3** `mcp_endpoint` is an absolute `https:` URL (or `http://localhost…`, see B4) and accepts MCP Streamable HTTP.
- [ ] **A4** `profile_extensions` lists exactly the namespaces this context can serve — no more. *Advertising an extension you cannot serve makes a client request a scope that will never return data, and the failure surfaces as an empty profile rather than an error.*
- [ ] **A5** `connections` lists exactly the connection ids whose tools are exposed.
- [ ] **A6** `export` is `true`. *A server may only advertise `false` if it is knowingly non-conforming — §1.1.1.*
- [ ] **A7** **Multi-context hosts only.** Each context serves its own `<base>/.well-known/pcp.json` whose `mcp_endpoint` points at that context. The origin root serves a host-level document with `"multi_context": true` and no tenant specifics.
  - *Check the negative:* the origin-root document must not leak a handle, a count of tenants, or any per-user field.

## B. Transport & authorization — §3

- [ ] **B1** MCP Streamable HTTP is served at `mcp_endpoint`.
- [ ] **B2** OAuth 2.1 with PKCE. An authorization attempt without a code challenge is rejected.
- [ ] **B3** **Dynamic Client Registration (RFC 7591) is implemented.** *This is the one that decides whether portability is real. A server requiring manual client setup works with the clients its operator has heard of and no others — which is the lock-in PCP exists to remove, relocated one layer down.*
- [ ] **B4** Non-TLS connections are refused, except on localhost.
- [ ] **B5** Tokens are issued per client-device pair.
- [ ] **B6** Any single token can be revoked without affecting the others (test: two clients, revoke one, the other still works).
- [ ] **B7** The consent screen names each requested scope in plain language, and names what is **not** being requested (§3.1).
- [ ] **B8** A refresh never widens scope. Test: grant `profile.core:read`, refresh, assert the new token still cannot read `memory`. *This is the quiet one — scope creep on refresh is invisible to the user, who consented once and is never asked again.*

## C. Profile — §4

- [ ] **C1** `profile.core` is served and validates against [`profile.core.schema.json`](../schemas/profile.core.schema.json).
- [ ] **C2** A token holding only `profile.core:read` receives **no** extension data. Test with a context that has `pcp.health` populated; assert the response contains none of it. *(§4.3.1)*
- [ ] **C3** Each extension can be enabled and disabled independently *(§4.3.2)*.
- [ ] **C4** Special-category namespaces (`pcp.health`, `pcp.residency`) are stored under a key separate from the rest of the tenant *(§4.3.4)*.

## D. Memory — §5, §6

- [ ] **D1** Every stored page has `title` and `updated` in frontmatter.
- [ ] **D2** Pages marked `sensitivity: sensitive` are returned **only** under `memory.sensitive:read`. Test with a plain `memory:read` token and assert absence — including absence from search results and from `context.brief`.
- [ ] **D3** `memory.search` returns `active`/`validated` and current-or-undated pages ahead of others.
- [ ] **D4** A page whose `valid_until` has passed is not presented as current without its dates *(§5.1)*.
- [ ] **D5** `archived` pages are excluded from default retrieval but still appear in an export.
- [ ] **D6** The tool surface exists and is scope-gated: `profile.get`, `profile.update`, `memory.search`, `memory.read`, `memory.write`, `memory.list`, `context.brief`.
- [ ] **D7** `context.brief` returns core profile **plus** top-relevance memory in one call, and requires both `profile.core:read` and `memory:read`.
- [ ] **D8** `profile.update` uses patch semantics and records a change-log entry.

## E. Export — §8

The section that carries the product. Every box here is checkable with a single
archive and a JSON Schema validator.

- [ ] **E1** `export:read` produces a tar or zip archive.
- [ ] **E2** The archive root contains `manifest.json`, validating against [`export.manifest.schema.json`](../schemas/export.manifest.schema.json). A worked example — health data encrypted under a user passphrase, 128 pages, one namespace the server could not produce and therefore declared — is in [`export.manifest.example.json`](../schemas/export.manifest.example.json). It validates as-is; the schema sets `additionalProperties: false`, so it carries no explanatory keys you would have to strip before copying it.
- [ ] **E3** Every file listed in `files[]` exists at the stated path with the stated `sha256` and `bytes`.
- [ ] **E4** Every file in the archive except `manifest.json` appears in `files[]`. *Both directions — an unlisted file is as much a defect as a missing one, because it means the manifest is not a description of the archive.*
- [ ] **E5** `memory.page_count` equals the number of pages actually present.
- [ ] **E6** No path in `files[]` is absolute or contains `..`.
- [ ] **E7** **No third-party credentials anywhere in the archive.** Grep the unpacked tree for the access-token shapes of every connector you support. `credentials_included` is fixed to `false` by the schema; E7 is the check that the assertion is true.
- [ ] **E8** Memory pages travel byte-identical to storage — frontmatter included, unknown keys preserved. *An exporter that normalises frontmatter is lossy in exactly the fields §5.1 added: lifecycle, provenance, relations.*
- [ ] **E9** Anything not exported is declared in `omitted[]` with a reason.
- [ ] **E10** **Round trip.** Import the archive into a *fresh* context on the same implementation, export again, and diff. Profile documents, page contents and page count must match. The semantic index is excluded — it is derived (§5.2).
- [ ] **E11** **Cross-implementation round trip.** Import an archive produced by a *different* PCP server. This is the only box that tests the actual promise; the rest test that one implementation is self-consistent.

## F. Extensions — §4.2–4.3 (if present)

- [ ] **F1** Each namespace has a published JSON Schema and its own `profile.<ns>:read` / `:write` scope pair.
- [ ] **F2** Third-party namespaces use their own prefix. `pcp.*` is reserved for the registry.
- [ ] **F3** Each namespace has its own storage partition.

## G. Connections — §6, §7 (if present)

- [ ] **G1** Tools are namespaced `<connection_id>.<verb>`.
- [ ] **G2** Each is gated by `conn.<id>:read` / `conn.<id>:write`.
- [ ] **G3** Source credentials are stored encrypted, never logged, never exported.

## H. Audit — §7.3

- [ ] **H1** Active grants can be listed: client, device, scopes, last used.
- [ ] **H2** Each grant can be revoked individually.
- [ ] **H3** An access log exists per tenant, is visible to the user, and records which client read which category, when.
- [ ] **H4** The log is included in exports (see E) and marked `truncated` if retention cut it.

---

## Known gaps in v0.2-draft

Stated here so an implementer meets them as decisions rather than as surprises.

| Gap | Effect on conformance |
|---|---|
| `pcp.residency`, `pcp.legal`, `pcp.family`, `pcp.finance`, `pcp.home` are **Reserved** with no schema | F1 cannot be checked for them. Two servers will invent incompatible shapes for the same namespace, and E11 will fail on precisely the sensitive categories the consent model exists to protect. **Highest-value thing to close.** |
| No conformance **test suite**, only this list | Every box is a manual check. §11 tracks the suite. |
| Connection tool schemas are per-connector (§6) | G1/G2 check namespacing and gating only. Two servers may both be conformant and expose incompatible `notion.search` signatures — so a client written against one may not work against the other even when both pass. |
| E2E encryption tier undefined (§11) | `encryption.key_source: client_key` is expressible in the manifest but nothing specifies how search works over it. |

## Claiming conformance

State the version and the date, and publish which optional sections you
implement:

> *Implements PCP v0.1 (conformance checklist v0.2-draft, checked 2026-08-10).
> Extensions: `pcp.health`. Connections: `notion`, `email`. E11 verified
> against \<other implementation\>.*

A claim that does not name what it was tested against is a claim about one
implementation's opinion of itself. **E11 is the only box that tests
portability**; everything else tests self-consistency, and a server can pass
all of them while remaining an island.
