# PCP management API: draft for v0.3 (informative)

Status: DRAFT. Informative: a host that offers the same functions through a
UI only, or through a differently shaped API, still conforms. Updated
2026-10-19 for SPEC v0.3 §7.5 and §8.

## Why this document exists

SPEC requires a management surface for the controller of a context: list
and revoke grants (§7.5), read the access log (§7.5), export (§8.1), restore
and import (§8.7), and erase (§8.9). It leaves the shape to the host. This
draft sketches a RECOMMENDED shape so hosts converge and tools (CLIs,
migration helpers, the conformance suite) can work against more than one.

## Principles

1. **Management is not context serving.** The MCP surface (SPEC §6) is for
   clients acting under scoped grants. The management surface is for the
   controller and the roles it appoints, signed in with the host's own login
   (magic link, passkey or SSO, as the host chooses). The two MUST NOT share
   tokens.
2. **Same objects, same schemas.** A profile written here is the same
   document MCP serves, validated against the same schema; an export made
   here is the same archive (SPEC §8.2).
3. **Every action is audited** in the context's access log with
   `channel: "management"` (or `export`, `import`), never with content.
4. **Errors** use the SPEC §6.3 codes: a JSON body
   `{"error": {"code", "message", "violations"?}}` with HTTP 400
   (`invalid_input`), 403 (`forbidden`), 404 (`not_found`), 409
   (`conflict`), 413 (`too_large`), 429 (`rate_limited`), 423 (`locked`) or
   501 (`unsupported`).

## Recommended HTTP surface

All paths are relative to the context's management base, for example
`https://host.example/api/` for a single-context server or
`https://host.example/api/contexts/<context>/` on a multi-context host.
JSON in and out unless noted. Lists take `limit` and `cursor` and return
`next_cursor`.

### Context, profile and connections

| Method and path | Behavior |
|---|---|
| `GET /me` | The signed-in principal, the context's kind and controller, the profile document, connections and summary counts. SHOULD include `profile_gaps` and `profile_provenance` ([profile-bootstrap.md](profile-bootstrap.md)). |
| `PATCH /profile` | RFC 7396 merge patch, exactly like `profile_update` (SPEC §4.3): validated against the schema, 400 with `violations` otherwise, and a change-log entry. |
| `GET /profile/changes` | The profile change log, newest first. |
| `GET /extensions`, `PATCH /extensions/{namespace}` | Extension namespaces and `{ "enabled": boolean }` (SPEC §4.6 rule 2). |
| `GET /connections`, `POST /connections`, `PATCH /connections/{id}`, `DELETE /connections/{id}` | Connection configuration. A disabled connection exposes no tools. Deleting also revokes the third-party credentials the host holds for it. |

### Principals and partitions

| Method and path | Behavior |
|---|---|
| `GET /principals` | Principals as in `context.json` (SPEC §8.2 item 5), with `bound: boolean` after a restore (SPEC §8.7.2 item 3). |
| `POST /principals/{id}/bind` | Bind an unbound principal to an account or credential on this host. |
| `GET /partitions` | Partitions and their access lists. |
| `PUT /partitions/{name}/access` | Replace one partition's access list. Audited with `categories: ["partition"]`. |

### Grants

A **grant** is one client's authorization in a context: the family of
access and refresh tokens that one consent produced. Its `id` is stable
across refreshes, and the same id appears as `grant` in audit entries, so
the controller can see what a grant did and revoke it.

| Method and path | Behavior |
|---|---|
| `GET /grants` | Active grants: `{ id, client: { id, name, uri? }, principal, device?, scopes, created, last_used, expires? }`. `device` is a label the controller or the client gave, for recognizing the grant; it has no protocol meaning. |
| `PATCH /grants/{id}` | Rename the `device` label. |
| `DELETE /grants/{id}` | Revoke the grant: every access and refresh token of the family stops working at once, and no refresh can produce a new one. |
| `GET /audit` | The access log (SPEC §7.5), newest first, filterable by `category`, `principal`, `grant`, `since`, `until`. |

### Export

| Method and path | Behavior |
|---|---|
| `POST /exports` | Start a full export (SPEC §8.1 item 1). Body: `{ "encrypt_to"?: [recipient], "passphrase"?: boolean, "plaintext"?: boolean }` for archive-level encryption (SPEC §8.4). Returns 202 with `{ id, status: "pending" }`, or 201 when ready at once. |
| `GET /exports` | Archives the host holds, with `expires_at`. |
| `GET /exports/{id}` | `{ id, status: "pending" \| "ready" \| "failed", created, expires_at, sha256, bytes, coverage, page_count, omitted }`. `omitted` repeats the manifest's, so the controller sees gaps before downloading. |
| `GET /exports/{id}/archive` | The archive: `application/zip` or `application/x-tar` (with `Content-Encoding: gzip` when compressed), `Content-Disposition: attachment`, and `Digest` or `Repr-Digest` with its SHA-256. Never a public URL: only the signed-in controller, or a short-lived signed link it requested. |
| `DELETE /exports/{id}` | Delete a held archive before it expires. |

### Restore and import

| Method and path | Behavior |
|---|---|
| `POST /imports` | Upload an archive (`multipart/form-data`: `archive` and `options`). Options: `mode` (`restore` or `import`), `dry_run`, `format` (`pcp` or a foreign format, docs/interop.md), `on_conflict` (`revise`, `skip`, `rename`, `replace`), `partition`, `partition_map`, `principal_map`, `include_profile`, `approve_all` (controller only, SPEC §8.7.3 item 2). Returns the import report (`export.manifest.schema.json#/$defs/import_report`), or 202 and an id for long imports. `restore` into a context that is not empty fails with 409 `conflict`. |
| `GET /imports/{id}` | The report. |

### Erasure

| Method and path | Behavior |
|---|---|
| `POST /erasures` | Body: `{ "kind": "subject" \| "pages" \| "context", "subject"?, "paths"?, "ids"?, "include_derived"?: true, "dry_run"?: false }`. A dry run returns `{ "dry_run": true, "would_erase": { store: count } }`. A real run follows SPEC §8.9.2 and returns the receipt (`erasure.receipt.schema.json`), or 202 and an id while stores propagate. If the audit entry cannot be written first, 500 `internal` and nothing is deleted. `kind: "context"` also revokes every grant and ends the context; the host SHOULD require the controller to confirm by re-authenticating. |
| `GET /erasures`, `GET /erasures/{id}` | Receipts, newest first. A pending receipt updates as stores report. |
| `POST /erasures/{id}/verify` | Body `{ "subject" }`. Answers `{ "match": boolean }` by computing the keyed digest (SPEC §8.9.3). Rate limited, and audited without the subject. |

## Relationship to scopes

Management endpoints are not gated by OAuth scopes: the controller sees
everything in the context, including extension namespaces and sensitive
pages. Roles the controller appoints see what the host's role model allows,
and the host enforces it. Reads of special-category namespaces SHOULD still
be audited individually, like MCP access.

## Open questions

- Pagination and rate-limit headers.
- Whether to standardize this surface in v0.4 (SPEC §11), and whether the
  conformance suite (Phase 5) should exercise it or only the archive.
- A signed manifest or a detached signature for held archives (SPEC §8.3,
  deferred to v0.4).
