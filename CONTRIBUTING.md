# Contributing to PCP

PCP is an open specification, and anyone can help shape it. While PCP is pre-1.0, the process is deliberately lightweight:

- **Discussion** → GitHub Issues. One topic per issue. Design questions welcome — see SPEC §11 for the open list.
- **Changes** → PRs against `SPEC.md` / schemas. Normative changes must state: what breaks, who's affected, migration path.
- **New extension namespaces** → see [`extensions/README.md`](extensions/README.md).
- **Security best practices** → PRs to `SECURITY.md` are the most community-owned part of this repo; field reports from self-hosters are explicitly wanted.

## Versioning

- The spec uses semver on the document: v0.x drafts may break compatibility; from v1.0, breaking changes require a major version and a migration note.
- Schemas carry their version in `$id`.

## Ground rules

- Implementation-neutral: nothing in the spec may require a specific cloud, database, or vendor.
- Privacy first: any proposal that weakens consent granularity, export rights, or the audit log needs extraordinary justification.
- Rough consensus, running code: proposals accompanied by a working implementation (in any codebase) carry more weight.
- Vendor-neutral: no company, product or implementation gets special standing. Product names stay out of normative text; informative mappings to open implementations are welcome.

## Openness

- The specification, schemas and examples are Apache 2.0 and free to implement for any purpose, with no fees and no permission needed.
- Decisions are made in public, on issues and pull requests, on technical merit.
- Anyone who implements the spec may say so. Conformance claims are checked against the spec and its test suite, not granted by any organization.
