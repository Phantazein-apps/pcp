# PCP Extension Registry

Two kinds of extension are registered here:

- **Profile namespaces** hold everything the core profile deliberately
  excludes. Each one is a JSON Schema, a scope pair (`profile.<ns>:read` and
  `:write`) and a storage partition (SPEC §4.5).
- **Tool extensions** add tools that do not change what memory means. Each
  one has a reverse-DNS id, a tool part and an `ext.<part>` scope pair
  (SPEC §6.5).

## Profile namespaces (v0.3)

| Namespace | Status | Schema | Sensitivity class |
|---|---|---|---|
| `pcp.health` | Draft (reference example) | [`../schemas/0.3/pcp.health.schema.json`](../schemas/0.3/pcp.health.schema.json) | **Special category**: SHOULD use a separate encryption key |
| `pcp.residency` | Reserved | none | **Special category**: citizenship(s), visas, residency and tax status |
| `pcp.legal` | Reserved | none | High: matters, contracts of record, attorney contacts |
| `pcp.family` | Reserved | none | High: family structure, dependents, key dates, emergency contacts |
| `pcp.finance` | Reserved | none | High: account references (never credentials), obligations, advisors |
| `pcp.home` | Reserved | none | Medium: addresses, household, vehicles |

"Reserved" means the namespace and its sensitivity class are fixed by this
registry, and **no server may store or return data in it until its schema is
published here** (SPEC §4.6 rule 5). Schemas for the reserved namespaces are
planned for v0.4.

## Tool extension slots (v0.3)

| Slot | Tool part | Status | Owner |
|---|---|---|---|
| Shared documents (outlines, sections, leases, versions, stages, section review) | `doc` | Reserved, unfilled | Proposed by the implementers who need it |
| Handoffs between principals | `handoff` | Reserved, unfilled | Proposed by the implementers who need it |

A slot is filled by a PR that adds the extension's id, its tools with input
and output schemas, its scopes, and how its data appears in an export
(SPEC §8.5): the files under `extensions/<id>/` and their schemas, how
records reference pages (by path or `id`), and how each record carries its
partition and provenance. The team example archive
([`examples/0.3/export/team/`](../examples/0.3/export/team/)) shows one
handoff record under a placeholder id.

## Authoring rules

1. **One concern per namespace.** If a field could plausibly belong to two
   namespaces, it belongs to the more sensitive one.
2. **References, not secrets.** Extensions store facts and references (a
   policy number *reference*, an account *alias*), never credentials, tokens,
   or full identifiers usable for fraud on their own.
3. **`additionalProperties: false`.** Profile namespaces are strict schemas;
   free text goes in designated `notes` fields, and unbounded narrative goes
   in memory, not the profile.
4. **Third-party namespaces and extensions** use reverse-DNS prefixes
   (`com.example.pets`). The `pcp.*` prefix is assigned only through this
   registry.
5. **Sensitivity class is normative.** Special-category namespaces inherit
   the encryption requirements of SPEC §4.6 and §9.

## Proposing an extension

Open a PR adding a row to this registry and a schema in `schemas/<version>/`,
with a short rationale: what user story requires an *assistant* to know
this, and why memory pages are not the right home for it.
