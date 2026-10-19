# PCP Security Model & Self-Hosting Best Practices

This document is non-normative except where it restates SPEC §9. It is the living home for community best practices on securing a context server. PRs welcome — this is exactly the document the community should own.

## Threat model

A PCP context is among the most sensitive datasets a person has: health, legal, citizenship, family, plus live access to email and messages. Assume:

| Threat | Primary mitigations |
|---|---|
| Server compromise (multi-tenant host) | Per-tenant container/process isolation; per-tenant encryption keys; special-category data on separate keys |
| Stolen/leaked OAuth token | Short-lived tokens, per-device grants, one-click revocation, audit log |
| Malicious/over-curious MCP client | Scope minimization by default (§7.2); consent screen lists what is NOT granted; per-category scopes |
| Prompt-injection exfiltration via a connected LLM | Scope-gate everything; `memory.sensitive` and special-category extensions off by default; audit log makes reads visible |
| Rogue host operator | E2E tier (roadmap v0.2); until then: choose your host like you choose an email provider — or self-host |
| Data loss | Export is a user right (§8); encourage scheduled automated exports to user-controlled storage |

## Baseline (restating SPEC §9 — REQUIRED for conformance)

- TLS for all non-localhost traffic
- OAuth 2.1 + PKCE, per-device revocable tokens
- At-rest encryption for special-category extensions, separate key from tenant data
- Per-tenant isolation in multi-tenant deployments
- Source credentials encrypted, never logged, never exported
- User-visible audit log of category-level access

## Self-hoster checklist

- [ ] Server reachable only via TLS (Caddy/Traefik auto-TLS); SSH key-only, no password auth
- [ ] Runtime in a container/systemd unit with resource limits, non-root
- [ ] Disk encryption on (LUKS) or per-tenant application-level encryption verified
- [ ] Automated encrypted offsite backups (restic/borg) + one tested restore
- [ ] Unattended security updates enabled
- [ ] OAuth rate limiting / fail2ban on auth endpoints
- [ ] Review the audit log monthly; revoke stale device grants
- [ ] Scheduled export to a second location you control

## Host operator (multi-tenant) additions

- [ ] One container per tenant (or documented equivalent isolation)
- [ ] Tenant keys in a KMS or sealed store, not in app config
- [ ] Data-retention policy: suspended tenants retained encrypted ≤ 30 days, then destroyed
- [ ] Incident-response contact published; disclose breaches to tenants without delay
- [ ] GDPR/equivalent: you are a processor of special-category data — DPA template for customers, data residency documented

## Reporting

Report vulnerabilities in the spec or schemas privately through GitHub's [private vulnerability reporting](../../security/advisories/new). Please do not open public issues for exploitable findings.

Vulnerabilities in a specific implementation belong with that implementation's maintainers.
