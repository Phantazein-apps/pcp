# Example archives (SPEC §8)

Real, small PCP archives, unpacked. Every hash and count in their manifests
is computed from the files next to them, and `scripts/validate_schemas.py`
recomputes all of it (SPEC §8.3 checks 1 to 6).

| Archive | What it shows |
|---|---|
| [`team/`](team/) | A team context with the `partitions` and `review` features: three partitions and their access lists, an approved procedure derived from an archived episode, a proposed and a rejected page, a pending revision of an approved page, a sensitive page, a page by a removed agent, working memory with `expires`, an erasure receipt still waiting on backups, a truncated audit log, and one handoff under a tool extension. Paths and ids follow the Agent Brain mapping in SPEC Appendix A. |
| [`personal/`](personal/) | A personal context (a team of one): core profile with its change log, a `pcp.health` document and a sensitive page encrypted at file level, a `style/` page with the sensitive default written out, a stale page with validity dates, one earlier version of a page under `history/`, and a connection's configuration without credentials. |
| [`invalid/`](invalid/) | Archives that must fail: a file the manifest does not list; a wrong page count and a tampered file; a page whose author and partition `context.json` does not know. |

The file-level encrypted files are compact JWE (`alg: dir`, `enc: A256GCM`).
[`example-keys.json`](example-keys.json) holds the **public test key**, so
the validator can decrypt and check them when the `cryptography` package is
installed. Never use it for real data.

The content is invented. Edit a file and the validator prints the hash and
size the manifest should list.
