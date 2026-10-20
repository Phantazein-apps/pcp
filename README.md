<div align="center">

<img src="assets/banner.svg" alt="PCP — Portable Context Protocol: portable AI context behind one URL you control" width="100%">

<p>
  <img src="https://img.shields.io/badge/spec-v0.3--draft%20(in%20progress)-ff0018?style=flat-square&labelColor=000000" alt="Spec v0.3-draft, in progress">
  <img src="https://img.shields.io/badge/status-request%20for%20comments-f4f2ee?style=flat-square&labelColor=000000" alt="Request for comments">
  <img src="https://img.shields.io/badge/built%20on-MCP%20·%20OAuth%202.1%20·%20Markdown-ff0018?style=flat-square&labelColor=000000" alt="MCP · OAuth 2.1 · Markdown">
  <img src="https://img.shields.io/badge/license-Apache%202.0-a8a5a0?style=flat-square&labelColor=000000" alt="Apache 2.0">
</p>

# Portable Context Protocol

**An open protocol for AI context you own.**

Your profile, your memory, your connections — behind one URL you control,<br>usable by any AI assistant, on any device, from any vendor.

</div>

---

## The problem

Every AI assistant is building a memory of you. Each one keeps it in its own silo. What Claude knows about you, ChatGPT doesn't. What your coding agent learned last week, your phone's assistant has never seen. And when you leave a provider, your context stays behind.

Email solved this decades ago: open protocols meant you could pick any client and any server, and move between them. **PCP does the same for AI context.**

## What PCP is

PCP is a small, open specification built entirely on standards you already use — [MCP](https://modelcontextprotocol.io), OAuth 2.1 and plain Markdown. It defines two things:

1. **A format** for a context: a structured **profile**, long-term **memory** as Markdown pages with YAML frontmatter, and **connections** to live sources like email, notes and tasks.
2. **A server behavior**: a single MCP endpoint that serves that context with per-category consent, a user-visible audit log, and full export.

A context can belong to one person (`personal`), to one person's working life (`work`), or to a team of people and agents (`team`).

## How it works

> Open any MCP-enabled assistant. Paste your context URL. Choose what to share on one consent screen. The assistant now knows your preferences and history — and you can revoke it, audit it, or take it elsewhere at any time.

A PCP server announces itself at a well-known URL:

```http
GET /.well-known/pcp.json
```

```json
{
  "pcp_version": "0.3",
  "kind": "personal",
  "mcp_endpoint": "https://ctx.example.com/mcp",
  "profile_extensions": ["pcp.health"],
  "connections": ["notion"],
  "export": true,
  "encryption": { "key_custody": "user", "readable_by": ["principals", "host_in_request"] }
}
```

Any MCP client can then use the standard tools — `context_brief`, `profile_get`, `memory_search`, `memory_write` and more — limited to the scopes you granted. A coding assistant gets `memory:read`; it never sees `profile.health` unless you say so.

## Principles

- **You own your context.** Full export and import are required for conformance. A server that can't hand your data back isn't a PCP server.
- **Consent by category, not all-or-nothing.** Health, legal, family and financial data live in separate namespaces with their own OAuth scopes.
- **One URL, any client.** If it speaks MCP, it can use your context. No SDK, no new transport.
- **Run it anywhere.** Your laptop, a Raspberry Pi next to a local LLM, a home server, a hosting provider. The wire format is identical, so switching hosts is export + import.
- **Honest claims.** Terms like "encrypted" and "exportable" are defined by the spec and checkable — not marketing.
- **Vendor-neutral by design.** Nothing in the spec may require a specific cloud, database, model provider or company. No implementation is privileged.

## Status

**v0.3-draft, in progress — request for comments.** Nothing is stable yet. v0.3 is being written in phases ([`docs/v0.3-plan.md`](docs/v0.3-plan.md)); the team context model has landed; export, authorization and conformance are next. For a frozen text, pin the [`v0.2-draft`](../../tree/v0.2-draft) tag.

This is the right time to shape the protocol. Early feedback changes the spec; later feedback changes v2.

## Get involved

- **Read the spec** — [`SPEC.md`](SPEC.md). Section 11 lists open questions.
- **Open an issue** — design questions, gaps, things that don't fit your use case.
- **Build an implementation** — a server, a client, an importer, a conformance test. Running code carries the most weight. Open an issue so we can test interop together.
- **Host it** — if you run a hosting platform, PCP is designed to be offered alongside email, storage and websites: one context per customer, standard export, no lock-in. We want to hear what you need from the spec.
- **Write an extension** — new profile namespaces and connections: see [`extensions/`](extensions/).
- **Harden it** — [`SECURITY.md`](SECURITY.md) is meant to be community-owned. Field reports from self-hosters are especially welcome.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how changes are made.

## Implementations

No implementation claims v0.3 conformance yet; the conformance suite arrives in the final v0.3 phase. Listing is open to every implementation — open source or commercial, self-hosted or hosted — and is never an endorsement. Building one? Open a PR to add it.

| Project | Role | License | Status |
|---|---|---|---|
| [Refugio](https://github.com/Phantazein-apps/refugio) | Local LLM; connects to any PCP context as an MCP client, and can host one on `localhost` | Open source, free | PCP client; local server planned |

### Fully local: PCP + Refugio

PCP is the *context* refuge; [Refugio](https://github.com/Phantazein-apps/refugio) is the *compute* refuge — a local LLM that never sends data to the cloud. Together they make a fully sovereign setup:

- Refugio connects to your PCP endpoint as a standard MCP client, so your local model gets the same memory and profile as Claude on your phone.
- A PCP server can run on the same machine (`localhost` deployment profile), so nothing leaves your device.
- Refugio's memory backends (MemPalace, PACK) use the format PCP standardizes, so a Refugio install can become a full PCP context without migrating data.

## Repository layout

| Path | Contents |
|---|---|
| [`SPEC.md`](SPEC.md) | The protocol specification |
| [`schemas/0.3/`](schemas/0.3/) | JSON Schemas: discovery, profiles, memory page frontmatter, tools, audit entries |
| [`examples/0.3/`](examples/0.3/) | Examples that validate against the schemas (`invalid/` ones must fail) |
| [`scripts/validate_schemas.py`](scripts/validate_schemas.py) | Checks every schema and example (`pip install jsonschema pyyaml`) |
| [`extensions/`](extensions/) | Extension namespace registry and authoring guide |
| [`docs/`](docs/) | Informative guides: interop with other memory formats, management API, profile bootstrap, style profiles |
| [`SECURITY.md`](SECURITY.md) | Threat model and best practices for self-hosters and hosts |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to propose changes |

## License

Specification text, schemas and examples are licensed under [Apache 2.0](LICENSE). Anyone may implement PCP, free of charge, for any purpose. Any implementation that passes the conformance requirements may say it implements PCP; no one may imply the project endorses their product.

## Governance

PCP is developed in the open by its contributors, in the [`pcp-protocol`](https://github.com/pcp-protocol) organization. Decisions are made in public issues and pull requests, on technical merit. No company or implementation has special standing, and none is the "official" one.
