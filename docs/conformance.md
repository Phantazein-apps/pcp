# PCP v0.3 conformance requirements

Status: normative for the requirements it restates; it adds none. Where this
file and [`SPEC.md`](../SPEC.md) disagree, `SPEC.md` wins. SPEC §10 says how
a server claims conformance.

Every MUST and SHOULD of SPEC v0.3 that a server can be held to is listed
once, with a stable id. The [conformance suite](../conformance/) cites these
ids in its results, and its coverage check fails if an id marked for the
suite has no test.

## How to read the tables

**Level.** `MUST` (also REQUIRED, MUST NOT) or `SHOULD` (also RECOMMENDED,
SHOULD NOT). A server that misses a SHOULD still conforms; the suite reports
it as a warning.

**Profile.** Which conformance profile (SPEC §10) the requirement belongs to:

- `all`: Personal and Team.
- `P`: Personal only. `T`: Team only.
- A feature name (`partitions`, `review`, `delegation`), an optional tool
  (`export_create`, `erase_request`, `review_resolve`), `extensions`,
  `connections`, `user`, `device` (the custody declared), `org` (contexts
  an organization controls), `multi` (multi-context hosts), `local`
  (servers on the person's own machine), `routes` (contexts with
  `alternate_endpoints`): the requirement applies when the server uses it.

**Check.** How it is verified:

- `S`: the suite checks it black-box with one token or none.
- `S+`: the suite checks it but needs more than one token, a second context,
  or permission to write test data (`--allow-writes`).
- `A`: the archive checker checks it on an export archive
  (`python3 -m conformance archive <file>`, or `scripts/validate_schemas.py`
  for the examples).
- `M`: a person checks it on the management surface or the consent screen,
  following the note.
- `R`: review evidence: documentation, code review or an operator's
  statement, as SPEC §9.1 describes.

## DISC: Discovery (SPEC §2)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| DISC-01 | MUST | The context document is served at `<context-base>/.well-known/pcp.json` (or `/.well-known/pcp.json` for a single-context server) | 2.1, 2.2 | all | S |
| DISC-02 | MUST | The context document validates against `discovery.schema.json` | 2.3 | all | S |
| DISC-03 | MUST | `pcp_version` is `"0.3"` | 2.3 | all | S |
| DISC-04 | MUST | `controller_type` is present for `work` and is `human` for `personal` | 2.3 | all | S |
| DISC-05 | MUST | `export` is `true` only when the four commitments of §8.1 hold | 2.3, 8.1 | all | A |
| DISC-06 | MUST | Discovery documents contain no content and no personal data beyond the context URL | 2.3 | all | M |
| DISC-07 | MUST | A multi-context host serves a root document with `multi_context: true` and `context_url_template`, and without context fields | 2.2 | multi | S |
| DISC-08 | MUST | An unknown context's discovery URL gets HTTP 404 with a JSON body, never HTML or a redirect | 2.2 | multi | S |
| DISC-09 | MUST | `mcp_endpoint` equals the protected resource metadata's `resource` | 2.5 | all | S |
| DISC-10 | MUST | `resource_metadata` is the URL of that metadata | 2.5 | all | S |
| DISC-11 | MUST | `authorization_server`, if present, equals the metadata's one authorization server | 2.3, 2.5 | all | S |
| DISC-12 | SHOULD | `sse_endpoint` is not emitted | 2.3 | all | S |
| DISC-13 | MUST | Each alternate endpoint has its own context document and metadata, whose `resource` is that endpoint | 2.5, 9.8 | routes | S |

## AUTH: Transport and authorization (SPEC §3)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| AUTH-01 | MUST | Interoperates with MCP 2025-11-25 clients (`initialize` negotiation) | 3.1 | all | S |
| AUTH-02 | MUST | Interoperates with MCP 2026-07-28 clients (per-request `_meta`, `MCP-Protocol-Version`) | 3.1 | all | S |
| AUTH-03 | MUST | The same request gets the same answer with or without an MCP session | 3.1 | all | S |
| AUTH-04 | MUST | Streamable HTTP: POST answered with `application/json` or `text/event-stream`; the HTTP+SSE transport is not required or listed | 3.1 | all | S |
| AUTH-05 | MUST | Every non-loopback endpoint uses HTTPS | 3.1, 9.3 | all | S |
| AUTH-06 | MUST | A request whose `Origin` is not allowed gets 403; a request without `Origin` is allowed | 3.1, 9.3 | all | S |
| AUTH-07 | MUST | Protected resource metadata per context with `resource` = `mcp_endpoint`, exactly one `authorization_servers` entry, `scopes_supported` = the default grant without `offline_access`, `bearer_methods_supported: ["header"]` | 3.2 | all | S |
| AUTH-08 | MUST | The metadata is served at the path-suffixed well-known URL | 3.2 | all | S |
| AUTH-09 | MUST | On a multi-context host, an origin-root metadata document does not name a context, and origin-audience tokens are not accepted by contexts | 3.2 | multi | S |
| AUTH-10 | MUST | An unauthenticated MCP request gets 401 with `WWW-Authenticate: Bearer resource_metadata="..."`; never a redirect, login page, 200 or JSON-RPC error | 3.2 | all | S |
| AUTH-11 | SHOULD | The 401 challenge carries `scope` with the default grant | 3.2 | all | S |
| AUTH-12 | MUST | An invalid, expired, revoked or wrong-audience token gets 401 with `error="invalid_token"` | 3.2, 3.4 | all | S |
| AUTH-13 | MUST | Authorization server metadata (RFC 8414 or OIDC) at the probed location, `issuer` identical to the metadata's entry, `code_challenge_methods_supported` includes `S256`, auth methods and registration mechanisms advertised | 3.2 | all | S |
| AUTH-14 | MUST | Discovery and metadata documents: HTTP 200, `application/json`, no authentication, no redirects | 3.2 | all | S |
| AUTH-15 | SHOULD | Metadata allows cross-origin reads | 3.2 | all | S |
| AUTH-16 | MUST | Unknown paths under `/.well-known/` and `<context-base>/.well-known/` get HTTP 404 with a JSON body | 3.2 | all | S |
| AUTH-17 | MUST | At least one registration mechanism (CIMD, DCR or pre-registration) | 3.3 | all | S |
| AUTH-18 | SHOULD | CIMD supported and advertised (`client_id_metadata_document_supported`) | 3.3 | all | S |
| AUTH-19 | MUST | CIMD fetch hardening: https only, public addresses only, no redirects, size cap, `client_id` equals the URL, redirect URIs matched, fails closed | 3.3 | all | S+ |
| AUTH-20 | MUST | DCR, if offered: public clients, redirect URIs limited to https, loopback (any port) and optional private-use schemes | 3.3 | all | S |
| AUTH-21 | MUST | PKCE `S256` required for every client; authorization without a code challenge is refused | 3.4 | all | S |
| AUTH-22 | MUST | Exact redirect URI matching, except loopback ports; single-use authorization codes | 3.4 | all | S |
| AUTH-23 | MUST | Tokens only in the `Authorization` header, never accepted from the URL | 3.4 | all | S |
| AUTH-24 | MUST | The `resource` parameter is accepted and each token is bound to exactly one context; unknown or multiple resources get `invalid_target` | 3.4 | all | S |
| AUTH-25 | MUST | A token for another context is rejected with 401 `invalid_token` | 3.4 | all | S+ |
| AUTH-26 | MUST | No token passthrough: tokens for other resources are never accepted or forwarded | 3.4 | all | R |
| AUTH-27 | MUST | Every grant has a stable grant id that survives refresh | 3.4 | all | M |
| AUTH-28 | MUST | Revoking a grant invalidates its access and refresh tokens at the MCP endpoint within 5 minutes | 3.4 | all | S+ |
| AUTH-29 | SHOULD | An RFC 7009 revocation endpoint is offered | 3.4 | all | S |
| AUTH-30 | MUST | Refresh tokens of public clients rotate on every use | 3.4 | all | S |
| AUTH-31 | SHOULD | Reusing a rotated refresh token revokes the grant | 3.4 | all | S |
| AUTH-32 | MUST | Refresh never widens a grant; a `scope` parameter can only narrow | 3.4 | all | S+ |
| AUTH-33 | SHOULD | Access tokens live at most one hour | 3.4 | all | S |
| AUTH-34 | SHOULD | `iss` in authorization responses, advertised with `authorization_response_iss_parameter_supported` | 3.4 | all | S |
| AUTH-35 | MUST | Tokens, codes and secrets stored only as hashes, never logged or exported | 3.4 | all | R |
| AUTH-36 | SHOULD | A call the token can never make gets 403 `insufficient_scope` naming every needed scope (or a `forbidden` result with `required_scopes`) | 3.5 | all | S+ |
| AUTH-37 | MUST | A missing right that depends on the object is never a 403 challenge | 3.5 | all | S+ |
| AUTH-38 | MUST | A tool left out of `tools/list` still gets the step-up answer when called, never "unknown tool" | 3.5 | all | S+ |
| AUTH-39 | MUST | The consent screen shows the client and the source of its name, the context with its kind and controller, the account, each scope in plain language and individually declinable, and what sensitive categories are not requested | 3.6 | all | M |
| AUTH-40 | MUST | No new grant without explicit approval, except organization policy for org-controlled contexts | 3.6, 3.7 | all | M |
| AUTH-41 | MUST | The consent page cannot be framed and is protected against CSRF | 3.6 | all | S |
| AUTH-42 | MUST | Organization policy never replaces consent for a personal context or a person-controlled work context | 3.7 | org | M |
| AUTH-43 | MUST | Over stdio, a runtime grants a configured scope set, records it as a grant and audits every call | 3.1 | local | M |

## PROF: Profile (SPEC §4)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| PROF-01 | MUST | `profile.core` supported for personal and work contexts and valid against its schema | 4.1 | P | S |
| PROF-02 | MUST | `profile.team`, if present, valid against its schema | 4.2 | T | S |
| PROF-03 | MUST | `profile_update` is an RFC 7396 merge patch; an invalid result changes nothing and returns `invalid_input` with violations | 4.3 | all | S+ |
| PROF-04 | MUST | Updates set `updated` and append a change-log entry (members, principal, client, time) | 4.3 | all | M |
| PROF-05 | MUST | An empty profile is returned as `"profile": null`, never a placeholder that fails the schema | 4.4 | all | S |
| PROF-06 | MUST | No extension data under `profile.core` or `profile.team` scopes | 4.6 | extensions | S+ |
| PROF-07 | MUST | Each extension can be enabled and disabled independently | 4.6 | extensions | M |
| PROF-08 | MUST | No data in a `pcp.*` namespace without a published schema | 4.6 | all | S |
| PROF-09 | MUST | Special-category namespaces encrypted at rest | 9.1.1 | extensions | R |
| PROF-10 | SHOULD | Special-category namespaces under a separate key | 4.6, 9.1.1 | extensions | R |

## MEM: Memory (SPEC §5)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| MEM-01 | MUST | Invalid paths rejected with `invalid_input`, never rewritten | 5.1 | all | S+ |
| MEM-02 | MUST | No two paths differing only in case | 5.1 | all | S+ |
| MEM-03 | MUST | `_index` is never required or generated | 5.1 | all | R |
| MEM-04 | MUST | Stored frontmatter validates against `memory.page.schema.json` (`title`, `updated` required) | 5.2 | all | S |
| MEM-05 | MUST | A frontmatter block at the start of `body` is parsed when `frontmatter` is absent; both together are rejected; frontmatter is never ignored | 5.2.2 | all | S+ |
| MEM-06 | MUST | An update without `sensitivity` or `partition` keeps the stored values | 5.2.2 | all | S+ |
| MEM-07 | MUST | Modifying a sensitive page or changing `sensitivity` needs `memory.sensitive:write` | 5.2.2 | all | S+ |
| MEM-08 | MUST | A write to a path holding a page the caller cannot read fails with `conflict` and reveals nothing else | 5.2.2 | all | S+ |
| MEM-09 | MUST | Server-stamped keys (`updated`, `recorded_at`, `id`, `source.principal`, `source.on_behalf_of`, `source.client`, `review`) ignore client values | 5.2.3 | all | S+ |
| MEM-10 | MUST | Server-stamped instants are RFC 3339 UTC with `Z` | 5.2.4 | all | S |
| MEM-11 | MUST | A page past `valid_until` is not presented as current without its dates, and its `lifecycle` is not rewritten | 5.2.4 | all | S+ |
| MEM-12 | MUST | Moving a page between partitions needs `write` on both | 5.3 | partitions | S+ |
| MEM-13 | MUST | A principal learns nothing about partitions it cannot read: names, contents, counts, errors, ranking | 5.3 | partitions | S+ |
| MEM-14 | MUST | `memory_write` that needs review stores a proposal and says so (`applied: false`), or fails with `forbidden`; never reports an unapplied write as applied | 5.4 | review | S+ |
| MEM-15 | MUST | Proposed and rejected pages are excluded from default retrieval and returned only to their author or reviewers who ask | 5.4 | review | S+ |
| MEM-16 | MUST | Review fields are kept even when review is resolved only on the management surface | 5.4 | review | A |
| MEM-17 | MUST | Retrieval filters partitions, sensitivity and review before ranking, counting or snippets | 5.5 | all | S+ |
| MEM-18 | MUST | Retrieval honors lifecycle and validity; `archived` excluded by default; pages past `expires` never returned | 5.5 | all | S+ |
| MEM-19 | MUST | `memory_search` accepts `as_of`, and reports `as_of_exact: false` when it cannot answer exactly | 5.5 | all | S |
| MEM-20 | MUST | No persistent derived structure readable outside `readable_by` | 5.5, 9.1 | all | R |

## TOOL: Tool surface and MCP mechanics (SPEC §6)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| TOOL-01 | MUST | Tool names match `^[a-z][a-z0-9_]{0,39}$`; dotted v0.2 names are never listed | 6.1 | all | S |
| TOOL-02 | MUST | Connection ids match `[a-z][a-z0-9]{0,15}` and are not reserved parts | 6.1 | connections | S |
| TOOL-03 | MUST | The tools required for the profile and features are listed: `memory_search`, `memory_read`, `memory_list`, `memory_write`, `context_brief`, `audit_list`; `profile_get` and `profile_update` with a profile; `memory_propose` and `review_list` with `review`; `partition_list` with `partitions` | 6.2 | all | S |
| TOOL-04 | MUST | Every listed tool has a `title`, annotations and an `outputSchema`; `openWorldHint` is false for standard tools | 6.2 | all | S |
| TOOL-05 | MUST | Standard tools' `inputSchema` is self-contained and has no top-level `oneOf`, `anyOf` or `allOf` | 6.2 | all | S |
| TOOL-06 | MUST | Successful results carry `structuredContent` that validates against the output schema | 6.2 | all | S |
| TOOL-07 | SHOULD | Results repeat structured content in a text block | 6.2 | all | S |
| TOOL-08 | MUST | Tool failures are `isError` results, not JSON-RPC errors; the first text block starts with `<code>: ` | 6.3 | all | S |
| TOOL-09 | SHOULD | Failures carry `structuredContent.error` with `code` and `message` | 6.3 | all | S |
| TOOL-10 | MUST | Reads of objects the caller cannot see produce `not_found`, never `forbidden` | 6.3 | all | S+ |
| TOOL-11 | MUST | `context_brief` never fails for a missing scope; it names what it left out | 6.2 | all | S+ |
| TOOL-12 | MUST | `memory_read` accepts exactly one of `path` or `id` | 6.2 | all | S |
| TOOL-13 | MUST | `memory_write` with a stale `expected_updated` fails with `conflict` | 6.2 | all | S+ |
| TOOL-14 | MUST | Connection tools are gated by `conn.<id>:*` and annotated `openWorldHint: true` | 6.4 | connections | S |
| TOOL-15 | MUST | Extension tools follow §6.1 to §6.3, are gated by `ext.<part>:*`, and their extension id is in discovery | 6.5 | extensions | S |
| TOOL-16 | SHOULD | PCP is declared as the MCP extension `io.github.pcp-protocol/pcp` with `pcp_version` and `discovery` | 6.6 | all | S |
| TOOL-17 | SHOULD | Server instructions name the context's kind (and controller for work and team) and never contain stored content | 6.6, 9.2.3 | all | S |
| TOOL-18 | MUST | `erase_request` defaults to a dry run, is annotated destructive, and offers only `subject` and `pages` | 8.9.4 | erase_request | S |
| TOOL-19 | MUST | `export_create` bundles only what the token can read and returns a status and download link | 8.1 | export_create | S+ |

## SCOPE: Scopes, partitions and delegation (SPEC §7.1 to §7.4)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| SCOPE-01 | MUST | Only the implications of §7.1 hold: no `:write` implies `:read`; qualifiers need their base scope | 7.1 | all | S+ |
| SCOPE-02 | MUST | Sensitive pages are returned only with `memory.sensitive:read`, including in search, lists and `context_brief` | 5.2.1, 7.1 | all | S+ |
| SCOPE-03 | MUST | A fixed scope set, where used, is stated in the token's `scope` and on the consent screen | 7.1 | all | S |
| SCOPE-04 | MUST | Effective rights are the intersection of token scopes and the access list; access lists default to deny with `partitions` | 7.3 | partitions | S+ |
| SCOPE-05 | MUST | The access list is enforced in the data query itself | 7.3 | partitions | R |
| SCOPE-06 | MUST | Delegated reads use the intersection of the agent's and the human's access; delegation is decided from the token | 7.4 | delegation | S+ |
| SCOPE-07 | MUST | Delegated writes are stamped with `source.principal` and `source.on_behalf_of` | 7.4 | delegation | S+ |

## AUD: Grants and audit (SPEC §7.5)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| AUD-01 | MUST | Active grants can be listed (client, principal, scopes, created, last used, grant id) and revoked one by one | 7.5 | all | M |
| AUD-02 | MUST | An access log per context, exposed by `audit_list` under `audit:read` and to the controller | 7.5 | all | S |
| AUD-03 | MUST | Audit entries validate against `audit.entry.schema.json` | 7.5 | all | S |
| AUD-04 | MUST | Entries never contain page bodies, titles, paths, queries, profile values or unkeyed hashes of them | 7.5 | all | S+ |
| AUD-05 | MUST | An entry for every tool call (failed ones too), management action, review resolution, access-list change, grant change, principal change and key change | 7.5 | all | S+ |
| AUD-06 | MUST | `audit_list` to a non-controller removes categories, partitions and object ids the caller cannot read | 7.5 | all | S+ |

## EXP: Export (SPEC §8.1 to §8.6)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| EXP-01 | MUST | The controller can make a full export at any time without the host's approval | 8.1 | all | M |
| EXP-02 | MUST | A partial archive declares omissions by category only and reveals nothing about unreadable data | 8.1 | all | A |
| EXP-03 | MUST | Kept archives are covered by the encryption declaration, expire, and are deleted by erasure | 8.1 | all | R |
| EXP-04 | MUST | Every export writes an audit entry | 8.1 | all | S+ |
| EXP-05 | MUST | Archive layout: zip or tar, root `manifest.json`, regular files only, paths per the grammar | 8.2 | all | A |
| EXP-06 | MUST | Pages are stored files (frontmatter valid, deterministic serialization) | 8.2 | all | A |
| EXP-07 | MUST | Defaults that change access are explicit in page files | 8.2 | all | A |
| EXP-08 | MUST | `context.json` validates and lists every principal and partition referenced | 8.2, 8.3 | all | A |
| EXP-09 | MUST | Never in an archive: credentials, keys, indexes, expired, deleted or erased data | 8.2 | all | A |
| EXP-10 | MUST | Manifest checks 1 to 8: schema, files both directions with SHA-256 and size, counts, paths, documents, references, omissions, constants | 8.3 | all | A |
| EXP-11 | MUST | Archive and file encryption declarations use `user` or `device` custody, never `host`, and never contain a key | 8.4 | all | A |
| EXP-12 | SHOULD | Under `user` or `device` custody the archive is encrypted to a controller key unless plaintext is requested | 8.4 | user, device | A |
| EXP-13 | MUST | Extension data under `extensions/<id>/`, listed in the manifest; connections carry configuration only | 8.5 | extensions, connections | A |
| EXP-14 | MUST | An exporter writes the version it implements; an importer checks both versions before writing | 8.6 | all | A |

## IMP: Restore, import and round trip (SPEC §8.7, §8.8)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| IMP-01 | MUST | Unsafe archives (absolute or `..` paths, links, devices, duplicates) are rejected before writing | 8.7.1 | all | M |
| IMP-02 | MUST | Any failed manifest check rejects the archive with nothing written | 8.7.1 | all | M |
| IMP-03 | MUST | Restore only into an empty context, by its controller, from a full archive; all or nothing | 8.7.2 | all | M |
| IMP-04 | MUST | Restore keeps everything; principals stay unbound until bound; grants and connections are not restored | 8.7.2 | all | M |
| IMP-05 | MUST | Import marks pages (`source.origin: import`, `recorded_at`, `x_import`), applies review, keeps sensitivity, resolves conflicts, is idempotent, maps principals and partitions, converts timestamps, skips expired and erased pages | 8.7.3 | all | M |
| IMP-06 | MUST | Importers warn before importing into a context with a wider `readable_by` or another controller | 8.4, 9.2.3 | all | M |
| IMP-07 | MUST | Same-implementation round trip: files byte-identical after export, restore, export | 8.8 | all | A |
| IMP-08 | MUST | Cross-implementation round trip: bodies byte-identical, frontmatter equal as data | 8.8 | all | A |

## ERA: Erasure and retention (SPEC §8.9, §8.10)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| ERA-01 | MUST | Erasure (`subject`, `pages`, `principal`, `context`) is available on the management surface | 8.9 | all | M |
| ERA-02 | MUST | Subject matching never widens a multi-word subject to single words | 8.9.1 | all | S+ |
| ERA-03 | MUST | The audit entry is written first; if it cannot be, nothing is deleted | 8.9.2 | all | R |
| ERA-04 | MUST | Receipts validate against `erasure.receipt.schema.json` and contain no subject, paths, titles, content or unkeyed hashes | 8.9.3 | all | A |
| ERA-05 | MUST | Receipts are kept for the life of the context and travel in exports | 8.9.3 | all | A |
| ERA-06 | MUST | With tombstones, import skips matching pages | 8.9.5 | all | M |
| ERA-07 | MUST | Pages past `expires`, and deleted pages, are never returned or exported | 8.10 | all | S+ |
| ERA-08 | SHOULD | Expired pages are deleted within the documented interval (RECOMMENDED 24 hours), audited as `retention.sweep` | 8.10 | all | R |

## KEY: Key custody (SPEC §9.1)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| KEY-01 | MUST | The declared custody matches behavior; the server documents which metadata it keeps readable | 9.1, 9.1.1 | all | R |
| KEY-02 | MUST | `host` custody lists `host` and never claims user-held keys, end-to-end encryption or unreadability | 9.1.2 | all | R |
| KEY-03 | MUST | U1: only wrapped context keys are stored, each opened by a principal's or grant's secret | 9.1.3 | user | R |
| KEY-04 | MUST | U2: decryption only during an authorized request; nothing kept afterwards, including key material at the token endpoint | 9.1.3 | user | R |
| KEY-05 | MUST | U3: no plaintext content at rest, in backups, replicas, queues, caches or archives | 9.1.3 | user | S+ |
| KEY-06 | MUST | U4: derived data encrypted, or blind-indexed under a key derived from the context key, and what blind indexes reveal is documented | 9.1.3 | user | R |
| KEY-07 | MUST | U5: every decrypting request is audited | 9.1.3 | user | S+ |
| KEY-08 | MUST | U6: revoking a grant deletes its wrapped key; removing a principal deletes theirs | 9.1.3 | user | M |
| KEY-09 | MUST | V1 to V4: keys and plaintext only on devices; relays pass TLS through with CAA-restricted certificates; host-side writers cannot read back; every path holds | 9.1.4 | device | R |
| KEY-10 | MUST | A token that can never unlock gets 401 `invalid_token`; a temporarily unavailable key gives `locked` without content | 9.1.5 | user, device | M |
| KEY-11 | MUST | Any recovery arrangement in which the host takes part is declared `host`; others are declared `escrow`, opt-in, shown with their holders, and can be ended | 9.1.6 | all | R |
| KEY-12 | MUST | Wrapping-key changes delete old wrapped copies; context-key rotation after removal (MUST for `device`, SHOULD for `user`) | 9.1.7 | user, device | R |
| KEY-13 | MUST | Under `user` and `device` custody the host cannot recover lost keys, and says so at setup | 9.1.7 | user, device | M |
| KEY-14 | MUST | Archives kept under `user` custody are encrypted to a controller key; the erasure digest key is content key material | 9.1.8 | user | R |

## CTX: Work, personal and organization control (SPEC §9.2)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| CTX-01 | MUST | A personal context has no `org` principal, and no organization holds a role, key, escrow share, or export or erasure right | 9.2.1 | P | A |
| CTX-02 | MUST | Under `user` custody, a person in an org-controlled context is told the organization can read it | 9.2.1 | org | M |
| CTX-03 | MUST | A context's kind never changes once it holds data; controller transfers need both sides and are audited | 9.2.1 | all | M |
| CTX-04 | MUST | A personal context's controller can always add a sign-in not delegated to an external identity provider | 9.2.2 | P | M |
| CTX-05 | MUST | Contexts of one person share no keys, grants, logs or partitions; derived wrapping keys use distinct inputs | 9.2.3 | all | R |
| CTX-06 | MUST | No context reveals another of the same person through tools, management views, audit entries, exports or errors | 9.2.3 | all | S+ |
| CTX-07 | MUST | Offboarding removes the principal at once: grants revoked, key copies deleted, delegation ended, status `removed`, id never reused | 9.2.4 | org | M |

## SEC: Security baseline (SPEC §9.3 to §9.8)

| Id | Level | Requirement | § | Profile | Check |
|---|---|---|---|---|---|
| SEC-01 | MUST | OAuth endpoints and CIMD fetches are rate-limited; over the limit, 429 with `Retry-After` | 9.3 | all | S+ |
| SEC-02 | SHOULD | Limits keyed by client id or account, not IP alone; MCP limited per grant | 9.3 | all | R |
| SEC-03 | MUST | HTML surfaces send `frame-ancestors 'none'`, a restrictive CSP and `no-store` | 9.3 | all | S |
| SEC-04 | MUST | Data, keys and archives are never served from a web directory without an access check | 9.3, 9.4 | all | R |
| SEC-05 | MUST | Localhost: binds to loopback by default | 9.4 | local | S |
| SEC-06 | MUST | Localhost: `Host` other than `localhost`, `127.0.0.1` or `[::1]` is rejected | 9.4 | local | S |
| SEC-07 | MUST | Localhost: `Origin` checked against an allow list; POST needs `Content-Type: application/json` | 9.4 | local | S |
| SEC-08 | MUST | Localhost: every request is authenticated | 9.4 | local | S |
| SEC-09 | MUST | Every query, cache key, index and job carries the context id | 9.5 | multi | R |
| SEC-10 | MUST | Text blocks that carry content frame it with the preamble and escaped `<memory_data>` elements | 9.6 | all | S+ |
| SEC-11 | MUST | Proposals returned to reviewers carry `review="proposed"` or `"rejected"` | 9.6 | review | S+ |
| SEC-12 | MUST | Stored content never appears in instructions, tool descriptions or error messages | 9.6 | all | S+ |
| SEC-13 | MUST | Connection credentials stored encrypted, never logged, returned or exported | 9.7 | connections | R |
| SEC-14 | MUST | Overlay and private routes apply TLS and authorization; a network address never identifies a principal | 9.8 | routes | R |
