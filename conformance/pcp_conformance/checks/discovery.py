"""DISC and metadata checks (SPEC §2, §3.2). No token needed."""
import json
import urllib.parse

from ..net import is_loopback, origin_of, parse_www_authenticate, well_known_suffixed
from ..registry import Skip, check


@check("DISC-01", "DISC-02", "DISC-03", "DISC-04", "DISC-12")
def context_document(t, rec):
    doc = t.context_doc
    if not rec.expect("DISC-01", doc is not None,
                      "no context document whose mcp_endpoint is the endpoint under test was found at "
                      "<context-base>/.well-known/pcp.json", f"found at {t.context_doc_url}"):
        raise Skip("no context document")
    errors = t.schema_errors("discovery.schema.json", doc)
    rec.expect("DISC-02", not errors, "; ".join(errors[:5]))
    rec.expect("DISC-03", doc.get("pcp_version") == "0.3", f"pcp_version is {doc.get('pcp_version')!r}")
    kind, ct = doc.get("kind"), doc.get("controller_type")
    ok = (kind != "work" or ct in ("human", "org")) and (kind != "personal" or ct in (None, "human"))
    rec.expect("DISC-04", ok, f"kind {kind!r} with controller_type {ct!r}")
    rec.expect("DISC-12", "sse_endpoint" not in doc, "sse_endpoint is emitted")


@check("DISC-07", "DISC-08")
def root_document(t, rec):
    r, doc = t.root_doc
    if not (doc and doc.get("multi_context")):
        rec.skip("DISC-07", "not a multi-context host (no root document with multi_context: true)")
        rec.skip("DISC-08", "not a multi-context host")
        return
    errors = t.schema_errors("discovery.schema.json", doc)
    bad = [k for k in ("mcp_endpoint", "resource_metadata", "kind", "controller_type", "alternate_endpoints") if k in doc]
    rec.expect("DISC-07", not errors and not bad and "{context}" in doc.get("context_url_template", ""),
               f"root document problems: {errors[:3]} context fields {bad}")
    template = doc.get("context_url_template", "")
    unknown = template.replace("{context}", "pcp-conformance-no-such-context-" + t.run_id) + "/.well-known/pcp.json"
    r2 = t.http.get(unknown, headers={"Accept": "application/json"})
    rec.expect("DISC-08", r2.status == 404 and r2.is_json(),
               f"unknown context discovery URL gave HTTP {r2.status} {r2.content_type}")


@check("DISC-09", "DISC-10", "DISC-11", "AUTH-07", "AUTH-08", "AUTH-14", "AUTH-15")
def protected_resource_metadata(t, rec):
    doc = t.context_doc or {}
    r, prm = t.prm
    rec.expect("AUTH-14", r.status == 200 and r.is_json() and r.header("location") is None,
               f"metadata at {t.prm_url} gave HTTP {r.status} {r.content_type}")
    if prm is None:
        for rid in ("DISC-09", "DISC-10", "DISC-11", "AUTH-07", "AUTH-08"):
            rec.fail(rid, "no protected resource metadata")
        return
    rec.expect("DISC-09", prm.get("resource") == t.endpoint,
               f"resource {prm.get('resource')!r} is not the MCP endpoint {t.endpoint!r}")
    rec.expect("DISC-10", doc.get("resource_metadata") == t.prm_url,
               f"context document resource_metadata {doc.get('resource_metadata')!r} is not {t.prm_url!r}")
    servers = prm.get("authorization_servers") or []
    aserv = doc.get("authorization_server")
    rec.expect("DISC-11", aserv is None or servers == [aserv],
               f"authorization_server {aserv!r} does not match {servers}")
    problems = []
    if prm.get("resource") != t.endpoint:
        problems.append("resource is not the MCP endpoint")
    if len(servers) != 1:
        problems.append(f"{len(servers)} authorization servers, expected exactly one")
    scopes = prm.get("scopes_supported")
    if not isinstance(scopes, list) or not scopes:
        problems.append("no scopes_supported")
    elif "offline_access" in scopes:
        problems.append("scopes_supported includes offline_access")
    if prm.get("bearer_methods_supported") != ["header"]:
        problems.append(f"bearer_methods_supported is {prm.get('bearer_methods_supported')!r}")
    rec.expect("AUTH-07", not problems, "; ".join(problems))
    expected = well_known_suffixed(t.endpoint, "oauth-protected-resource")
    r2 = t.http.get(expected, headers={"Accept": "application/json"})
    rec.expect("AUTH-08", r2.status == 200 and r2.is_json() and r2.json().get("resource") == t.endpoint,
               f"{expected} gave HTTP {r2.status}")
    rec.expect("AUTH-15", (r.header("access-control-allow-origin") or "") in ("*",),
               "metadata has no Access-Control-Allow-Origin: *")


@check("AUTH-09")
def origin_root_metadata(t, rec):
    if not t.multi_context:
        rec.skip("AUTH-09", "not a multi-context host")
        return
    r = t.http.get(origin_of(t.endpoint) + "/.well-known/oauth-protected-resource", headers={"Accept": "application/json"})
    if r.status != 200 or not r.is_json():
        rec.ok("AUTH-09", "no origin-root metadata document")
        return
    res = r.json().get("resource")
    rec.expect("AUTH-09", res != t.endpoint and "/" not in urllib.parse.urlsplit(res or "").path.strip("/"),
               f"origin-root metadata names resource {res!r}")


@check("AUTH-10", "AUTH-11", "SEC-08")
def unauthenticated_challenge(t, rec):
    r = t.challenge
    params = parse_www_authenticate(r.header("www-authenticate"))
    ok = r.status == 401 and params and params.get("_scheme") == "bearer" and params.get("resource_metadata")
    rec.expect("AUTH-10", bool(ok), f"unauthenticated tools/list gave HTTP {r.status} "
               f"with WWW-Authenticate {r.header('www-authenticate')!r}")
    rec.expect("AUTH-11", bool(params and params.get("scope")), "the challenge has no scope parameter")
    if is_loopback(t.endpoint):
        rec.expect("SEC-08", r.status == 401, f"loopback server answered an unauthenticated request with {r.status}")
    else:
        rec.skip("SEC-08", "not a loopback server")


@check("AUTH-12", "AUTH-23")
def invalid_tokens(t, rec):
    from ..mcp import McpClient
    r = McpClient(t.http, t.endpoint, "pcp-conformance-invalid-token").request("tools/list")
    params = parse_www_authenticate(r.response.header("www-authenticate")) or {}
    rec.expect("AUTH-12", r.http_status == 401 and params.get("error") == "invalid_token",
               f"an invalid token gave HTTP {r.http_status}, error={params.get('error')!r}")
    try:
        tok = t.any_token()["access_token"]
    except Skip as e:
        rec.skip("AUTH-23", str(e))
        return
    sep = "&" if "?" in t.endpoint else "?"
    c = McpClient(t.http, t.endpoint + sep + "access_token=" + urllib.parse.quote(tok), None, t.revision(tok))
    r2 = c.request("tools/list")
    rec.expect("AUTH-23", r2.http_status == 401, f"a token in the query string was accepted (HTTP {r2.http_status})")


@check("AUTH-13", "AUTH-17", "AUTH-18", "AUTH-29", "AUTH-34")
def authorization_server_metadata(t, rec):
    _, prm = t.prm
    url, r, meta = t.as_meta
    if not meta:
        for rid in ("AUTH-13", "AUTH-17"):
            rec.fail(rid, "no authorization server metadata found at the RFC 8414 or OIDC locations")
        for rid in ("AUTH-18", "AUTH-29", "AUTH-34"):
            rec.skip(rid, "no authorization server metadata")
        return
    issuer = (prm.get("authorization_servers") or [None])[0]
    problems = []
    if meta.get("issuer") != issuer:
        problems.append(f"issuer {meta.get('issuer')!r} is not {issuer!r}")
    if "S256" not in (meta.get("code_challenge_methods_supported") or []):
        problems.append("code_challenge_methods_supported lacks S256")
    if not meta.get("token_endpoint_auth_methods_supported"):
        problems.append("no token_endpoint_auth_methods_supported")
    if r.header("location") or r.status != 200:
        problems.append(f"metadata answered HTTP {r.status}")
    rec.expect("AUTH-13", not problems, "; ".join(problems))
    mechanisms = bool(meta.get("registration_endpoint")) or bool(meta.get("client_id_metadata_document_supported")) or bool(t.opts.client_id)
    rec.expect("AUTH-17", mechanisms, "neither registration_endpoint nor client_id_metadata_document_supported, and no --client-id")
    rec.expect("AUTH-18", meta.get("client_id_metadata_document_supported") is True, "CIMD not advertised")
    rec.expect("AUTH-29", bool(meta.get("revocation_endpoint")), "no revocation_endpoint")
    rec.expect("AUTH-34", meta.get("authorization_response_iss_parameter_supported") is True,
               "authorization_response_iss_parameter_supported is not true")


@check("AUTH-16")
def unknown_well_known(t, rec):
    probes = [origin_of(t.endpoint) + "/.well-known/pcp-conformance-" + t.run_id]
    if t.context_base:
        probes.append(t.context_base + "/.well-known/pcp-conformance-" + t.run_id)
    bad = []
    for url in probes:
        r = t.http.get(url, headers={"Accept": "application/json"})
        if not (r.status == 404 and r.is_json()):
            bad.append(f"{url}: HTTP {r.status} {r.content_type}")
    rec.expect("AUTH-16", not bad, "; ".join(bad))


@check("AUTH-05")
def tls(t, rec):
    urls = [t.endpoint, t.prm_url]
    _, _, meta = t.as_meta
    for k in ("authorization_endpoint", "token_endpoint", "registration_endpoint", "revocation_endpoint"):
        if meta and meta.get(k):
            urls.append(meta[k])
    plain = [u for u in urls if u.startswith("http://") and not is_loopback(u)]
    rec.expect("AUTH-05", not plain, f"plain HTTP endpoints: {plain}")


@check("DISC-13")
def alternate_endpoints(t, rec):
    alts = (t.context_doc or {}).get("alternate_endpoints") or []
    if not alts:
        rec.skip("DISC-13", "no alternate_endpoints")
        return
    bad = []
    for alt in alts:
        prm_url = well_known_suffixed(alt, "oauth-protected-resource")
        r = t.http.get(prm_url, headers={"Accept": "application/json"})
        if not (r.status == 200 and r.is_json() and r.json().get("resource") == alt):
            bad.append(f"{alt}: metadata at {prm_url} gave HTTP {r.status}")
    rec.expect("DISC-13", not bad, "; ".join(bad))
