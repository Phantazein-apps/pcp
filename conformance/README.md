# PCP v0.3 conformance suite

Black-box checks of a PCP server against
[`docs/conformance.md`](../docs/conformance.md), which lists every
requirement of SPEC v0.3 with a stable id. Each result names the id it
checks, so a report reads as "AUTH-25 pass, SEC-10 fail" against the
document.

The suite checks what can be checked from outside: discovery, OAuth,
the MCP transport, the tool surface, scopes and leak tests with canary
strings, framing, audit entries, and export archives. Requirements that
need the management surface (`M`) or review evidence (`R`) are listed in
the report as manual; a conformance claim covers them by a person's check.

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r conformance/requirements.txt
```

Python 3.10 or later. The suite uses the standard library for HTTP and
`jsonschema` and `pyyaml` for the schemas in [`schemas/0.3/`](../schemas/0.3/).

## Run it

From the `conformance/` directory:

```bash
python3 -m pcp_conformance run --endpoint https://ctx.example.com/mcp
```

By default the suite is **read-only**: it fetches discovery and metadata,
sends unauthenticated and invalid requests, and registers nothing. Checks
that need more say so and are skipped. Widen it with:

| Option | What it allows |
|---|---|
| `--interactive` | Run OAuth in your browser: the suite prints an authorization URL and catches the redirect on a loopback port. Each scope set the checks need is one approval. |
| `--token T [--token-scopes "a b"]` | Use an access token you already have, instead of OAuth. Checks that need other scopes are skipped. |
| `--allow-register` | Register OAuth clients (DCR) and probe the CIMD fetcher with addresses it must refuse. |
| `--allow-writes` | Write test pages. Every page lives under `pcp-conformance/<run id>/` and carries a unique canary string. **Use a throwaway context**: PCP has no tool to delete pages, so remove them with erasure afterwards. |
| `--allow-load` | Send a burst of bad token requests to check rate limiting (SEC-01). Only against a test deployment. |
| `--other-endpoint URL` | A second context of the same person, for audience binding (AUTH-25) and separation (CTX-06). |
| `--second-token T` or `--second-login NAME`, `--private-partition P` | A second principal and a partition it cannot read, for the team checks. |
| `--delegated-token T` | An agent token acting for a human, for the delegation checks. |
| `--scan-path DIR` | The server's data directory. Under `user` custody the suite writes a canary and searches every file for it (KEY-05). |
| `--revocation-wait S` | How long to wait for a revoked grant to stop working (default 300, the SPEC's bound). |
| `--only IDS` | Run only the checks that cite these ids. |
| `--json`, `--report FILE` | A JSON report. |

The exit status is 1 if any MUST failed. A failed SHOULD is a warning.

### Archives

```bash
python3 -m pcp_conformance archive context.pcp.zip            # SPEC §8.3 checks
python3 -m pcp_conformance roundtrip a.pcp.zip b.pcp.zip       # SPEC §8.8, same implementation
python3 -m pcp_conformance roundtrip a.pcp.zip b.pcp.zip --cross   # across implementations
```

`archive` unpacks safely (it refuses absolute paths, `..`, links and
repeated names, as an importer must) and runs the same checks as
[`scripts/validate_schemas.py`](../scripts/validate_schemas.py). Pass
`--keys` with a JSON key file to check file-level JWE content.

## The reference server

[`reference/server.py`](reference/server.py) is a small PCP server, in memory
and in one file, that exists so the suite can run in CI. It is not for real
data. It serves three contexts on `127.0.0.1`: a personal one, a work one
controlled by an organization, and a team one with partitions and review.
In `--test-mode` it approves authorizations at once for the user named by
`login_hint`.

```bash
conformance/run-reference.sh .venv/bin/python
```

runs the self-check, the suite against all three contexts, and then the
suite against four deliberately broken builds of the server
(`--break sensitive-leak`, `audience`, `origin`, `framing`), each of which
must make the suite fail. CI runs the same script.

## Coverage rules

```bash
python3 -m pcp_conformance self-check
```

fails when a requirement marked `S` or `S+` in `docs/conformance.md` has no
check, when a check cites an id the document does not have, or when a
standard tool (SPEC §6.2) has no check that calls it. Add a requirement to
the document and the self-check tells you to write its check.

## Claiming conformance

SPEC §10 says what a claim states. In short: the profile, the suite version
and date, the report, and how the manual and review items were checked.
