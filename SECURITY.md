# PCP Security Model & Self-Hosting Best Practices

This document is non-normative except where it restates SPEC §9. It is the living home for community best practices on securing a context server. PRs welcome: this is exactly the document the community should own.

## Threat model

A PCP context is among the most sensitive datasets a person has: health, legal, citizenship, family, plus live access to email and messages. Assume:

| Threat | Primary mitigations |
|---|---|
| Server compromise (multi-tenant host) | Per-context isolation (SPEC §9.5); per-context keys; special-category data on separate keys |
| Stolen/leaked OAuth token | Short-lived tokens bound to one context, grants revocable one by one, refresh rotation, audit log (SPEC §3.4) |
| Malicious/over-curious MCP client | Scope minimization by default (§7.2); consent screen lists what is NOT granted; per-category scopes |
| Prompt-injection exfiltration via a connected LLM | Scope-gate everything; `memory.sensitive` and special-category extensions off by default; returned content framed as data (SPEC §9.6); audit log makes reads visible |
| Rogue host operator | User-held keys or device custody (SPEC §9.1) limit what a host can read; otherwise choose your host like you choose an email provider, or self-host |
| Data loss | Export is a user right (§8); encourage scheduled automated exports to user-controlled storage |

## Baseline (restating SPEC §3 and §9, REQUIRED for conformance)

- TLS for all non-loopback traffic, overlay networks included
- OAuth 2.1 with PKCE; tokens bound to one context; grants revocable one by one
- `Origin` validated on the MCP route; rate limits on the OAuth endpoints
- An `encryption` declaration that matches what the server does (SPEC §9.1)
- At-rest encryption for special-category extensions
- Per-context isolation in multi-context deployments
- Source credentials encrypted, never logged, never exported
- Returned content framed as data, never as instructions
- A localhost server bound to loopback, checking `Host` and `Origin`
- A user-visible audit log of category-level access, without content

The conformance suite ([`conformance/`](conformance/)) checks most of this from outside.

## Self-hoster checklist

- [ ] Server reachable only via TLS (Caddy/Traefik auto-TLS); SSH key-only, no password auth
- [ ] Runtime in a container/systemd unit with resource limits, non-root
- [ ] Disk encryption on (LUKS) or per-tenant application-level encryption verified
- [ ] Automated encrypted offsite backups (restic/borg) + one tested restore
- [ ] Unattended security updates enabled
- [ ] OAuth rate limiting / fail2ban on auth endpoints
- [ ] Review the audit log monthly; revoke stale grants
- [ ] Scheduled export to a second location you control

## Host operator (multi-tenant) additions

- [ ] One container per context, or documented equivalent isolation (SPEC §9.5)
- [ ] Context keys in a KMS or sealed store, not in app config (or held by users: SPEC §9.1.3)
- [ ] Data-retention policy: suspended tenants retained encrypted ≤ 30 days, then destroyed
- [ ] Incident-response contact published; disclose breaches to tenants without delay
- [ ] GDPR/equivalent: you are a processor of special-category data; publish a DPA template for customers and document data residency

## Reporting

Report vulnerabilities in the spec or schemas privately through GitHub's [private vulnerability reporting](../../security/advisories/new). Please do not open public issues for exploitable findings.

Vulnerabilities in a specific implementation belong with that implementation's maintainers.
