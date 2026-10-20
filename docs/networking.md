# Reaching a context: overlay networks and blocked routes (informative)

Status: informative, written 2026-10-20 for SPEC v0.3. The normative rules
are in SPEC §3.1 item 5, §3.4 item 2, §9.4 and §9.8; this page explains how
to meet them and why they exist.

A PCP context is useful only when the clients that need it can reach it.
Two situations make that harder than it looks:

- **Blocked routes.** Some networks block whole IP addresses, not
  hostnames. Since 2025, Spanish internet providers have been ordered to
  block the shared addresses of large CDNs during football broadcasts, and
  hundreds of thousands of unrelated sites behind those addresses become
  unreachable from Spain for hours. A context behind such an address
  disappears for people on those networks.
- **Private runtimes.** A context whose keys live on a person's device
  (`device` custody, SPEC §9.1.4) is served by a runtime on that device,
  which should not be exposed to the whole internet.

## 1. Who is affected by a blocked route

What matters is where each request comes from:

| Request | Comes from | Affected by a block on the person's network? |
|---|---|---|
| A cloud AI client calling the MCP endpoint (a chat assistant on the web) | The AI provider's servers | No, unless the provider's own network is affected |
| A local client calling the MCP endpoint (a desktop app, an IDE agent, a local model) | The person's device | Yes |
| Sign-in and consent for a new client | The person's browser | Yes, so new connections fail even for cloud clients |
| Token refresh by a cloud client | The provider's servers | No |
| Token refresh by a local client | The person's device | Yes |
| The management surface (export, erasure, grants) | The person's browser | Yes |

So during a block, existing cloud connections usually keep working, while
everything the person does from their own devices fails, including the
things that give them control.

## 2. Alternate routes (SPEC §9.8)

A host can serve the same context at a second URL that does not share the
blocked addresses:

- a dedicated IP address not shared with other customers (blocks target
  shared addresses);
- a second hostname on another provider with its own address, for example
  `https://ctx-alt.example/...`, kept as a fallback;
- an overlay network address for the person's own devices (section 3).

Each route is its own OAuth resource with its own protected resource
metadata, because MCP clients compare the metadata's `resource` with the
URL they were given (SPEC §3.2). The context document of each route lists
the others in `alternate_endpoints`, and a token issued for any route of a
context is accepted at all of them (SPEC §9.8 item 2), so a person who
switches a client to the fallback URL does not need a new grant, as long as
the client lets them change the URL.

The authorization server needs a route too. Its issuer identifier must
match exactly (RFC 8414), so a second hostname is a second issuer. A host
that wants sign-in and refresh to survive a block either puts its
authorization server on an address that is not blocked, or offers a
separate issuer on the fallback route and accepts that grants made there
are separate grants.

Operational practice that helps:

- Monitor whether the host's addresses appear on public block trackers, and
  publish a status note when they do.
- Say plainly what is happening and why. Never blame the person's setup.
- Keep the management surface (export above all) reachable on the fallback
  route, so a person can always leave (SPEC §1.1 principle 1).

## 3. Overlay networks

An overlay (mesh VPN) connects a person's devices, and optionally a host,
into a private network that works across the internet: each device gets a
private address, and traffic between devices is encrypted and, where
possible, direct. Uses for PCP:

1. **Local clients reach a hosted context during a block**, through an
   overlay node on the host side that is not behind the blocked addresses.
2. **A device runtime is reachable from the person's other devices**
   (phone, laptop, desktop) without a public address: the Private case.
3. **A home server** serves a context to the person's devices only.

What an overlay cannot do: carry cloud AI clients' traffic. Those clients
run on the provider's servers, which cannot join the person's network. A
context that only listens on an overlay is invisible to them. For cloud
clients a public route is still needed: a public endpoint, or a relay that
forwards to the device runtime without reading the traffic (SPEC §9.1.4
V2, section 4 below).

### Options

Checked on 2026-10-20 against each project's repository:

| Project | License | Coordination server you can run yourself | Notes |
|---|---|---|---|
| Nebula | MIT | Yes: certificate authority and lighthouses, no central service | Certificate-based identity. Simple to self-host completely |
| NetBird | Client: BSD-3-Clause. Management, signal and relay servers: AGPL-3.0 | Yes | WireGuard underneath; SSO integration for identity |
| Headscale (with Tailscale clients) | Headscale: BSD-3-Clause. Tailscale client: BSD-3-Clause | Yes (Headscale) | An open implementation of the Tailscale control server |
| ZeroTier | Core: MPL-2.0. Network controller: ZeroTier Source-Available License, which limits commercial use | Yes, within that license | Check the controller license before a host runs it for customers |

A host that offers an overlay to its customers should prefer projects whose
coordination server it can run under an open license, so the route does not
depend on a third party's service (SPEC §1.1 principle 5).

### Rules that still apply on an overlay (SPEC §9.8)

- **TLS.** An overlay encrypts traffic between nodes, but anyone else on
  the same overlay network can still reach the endpoint, browsers treat
  plain HTTP as insecure, and OAuth needs HTTPS outside loopback. Serve
  HTTPS with a certificate for a real hostname that resolves to the overlay
  address (an ACME DNS challenge works without a public address), or with a
  private certificate authority the person's devices trust.
- **Authentication.** Being on the network is not authentication. Every
  request still carries a token for one context (SPEC §3.4), and the
  server never treats a source address as a principal.
- **Binding.** A desktop runtime listens on loopback by default (SPEC §9.4);
  listening on the overlay interface is an explicit choice, after which the
  network-facing rules of SPEC §9.3 apply to it.
- **Discovery.** The overlay route has its own context document and
  protected resource metadata, and appears in `alternate_endpoints` of the
  other routes.

## 4. Relays to a device runtime

For cloud clients to reach a context whose keys live on a device, a host can
run a public relay that forwards each connection to the device runtime over
an outbound tunnel the device opened. To keep `device` custody (SPEC §9.1.4
V2) the relay must not terminate TLS: it routes by the TLS server name and
passes the encrypted bytes through, and the device runtime holds the
certificate's private key. The certificate is issued for the relay
hostname, and the device obtains and renews it itself (an ACME DNS
challenge through an API the host offers works). A relay that terminates
TLS, even to inspect only headers, can read every request, and the context
must then declare `user` custody at best.

The device must be online for the context to answer. When it is not, the
relay answers with a `locked` tool result (SPEC §9.1.5), or with HTTP 503
when it cannot speak MCP, and never with cached content.

## 5. Checklist for a host

- Can a person on a blocked network still export their context?
- Does each route serve its own protected resource metadata with the right
  `resource`, and does each context document list the others?
- Are tokens for one route accepted at the others, and never across
  contexts?
- Does every overlay or private route use TLS and require a token?
- Does a relay for device custody pass TLS through untouched?
