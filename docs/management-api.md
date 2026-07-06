# HCS Management API — draft for v0.2 (informative)

Status: DRAFT · Informative, not normative for v0.1 conformance

## Why this document exists

SPEC.md §7.3 requires every conforming server to provide *"a way (UI or API)"*
for the tenant owner to list and revoke grants, and to see the audit log. §4
implies the owner can create and edit their profile; §6 implies connections
get configured somehow. v0.1 deliberately leaves the *shape* of that
management surface to the host.

This document sketches a RECOMMENDED shape so that hosts converge and
management tooling (CLIs, migration helpers) can interoperate. It is
informative: a host that ships only a UI, or a differently-shaped API, is
still conformant with v0.1.

## Principles

1. **Management ≠ context serving.** The MCP surface (§6) is for AI clients
   acting under scoped grants. The management surface is for the *owner*,
   authenticated by the host's own login (magic link, passkey, SSO — host's
   choice). The two MUST NOT share tokens.
2. **Same objects, same schemas.** A profile written through management is
   the same `profile.core` (+ extension) document served over MCP, validated
   against the same JSON Schemas.
3. **Every write is logged.** Management writes append to the same per-tenant
   audit log as MCP access (§7.3).

## Recommended HTTP surface

All endpoints are same-origin with the host's panel UI, under `/api/`,
authenticated by the host's owner session. JSON in, JSON out.

| Method & path | Behavior |
|---|---|
| `GET /api/me` | Owner identity + profile document + connections + summary counts. The panel's boot call. SHOULD include `profile_gaps` (recommended-but-empty fields) and `profile_provenance` (per-field: which actor last set it, when) per [profile-bootstrap.md](profile-bootstrap.md). |
| `PUT /api/profile` | Replace the `profile.core` document. Server MUST validate against `profile.core.schema.json` and reject non-conforming documents (400 with a list of violations). Server MUST append a change-log entry (§6 `profile.update` semantics). |
| `GET /api/profile/changes` | The profile change log, newest first. |
| `GET /api/connections` | List connection configs: `{ id, type, label, enabled, created }`. |
| `POST /api/connections` | Add a connection config `{ type, label? }`. Returns the created config. Linking/authorizing the third-party source is host-defined and MAY be a separate step. |
| `PATCH /api/connections/{id}` | Enable/disable: `{ enabled: boolean }`. Disabled connections MUST NOT expose their `conn.<id>.*` tools over MCP. |
| `DELETE /api/connections/{id}` | Remove the config. Host MUST also revoke any third-party credentials it holds for this connection. |
| `GET /api/grants` | Active client grants per §7.3: `{ id, client, device, scopes, last_used }`. |
| `DELETE /api/grants/{id}` | Revoke one grant (token family) individually. |
| `GET /api/audit` | The §7.3 access log, newest first, filterable by category. |

## Relationship to scopes

Management endpoints are not scope-gated (the owner sees everything they own,
including extension namespaces), but reads/writes of special-category
extensions SHOULD be individually audited like any MCP access.

## Open questions

- Standard error envelope, pagination, and rate-limit headers.
- Whether `PUT /api/profile` should accept patch semantics to mirror the MCP
  `profile.update` tool exactly.
- Management of extension namespaces (enable/disable per §4.3) — likely
  `PATCH /api/extensions/{ns}`.
