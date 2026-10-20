"""Optional tools and endpoint hardening (SPEC §8.1, §8.9.4, §3.6, §9.3)."""
import json
import time

from ..net import origin_of
from ..registry import Skip, check


def _listed(t, tok):
    _, tools = t.mcp(tok).list_tools()
    return {x["name"]: x for x in tools or []}


@check("TOOL-18", "ERA-02", tools=("erase_request",), writes=True)
def erase_request(t, rec):
    tok = t.token(["memory:read", "memory:write", "erase:write"])
    tools = _listed(t, tok)
    if "erase_request" not in tools:
        rec.skip("TOOL-18", "erase_request is not offered")
        rec.skip("ERA-02", "erase_request is not offered (check subject matching on the management surface)")
        return
    t.need_writes()
    c = t.mcp(tok)
    ann = tools["erase_request"].get("annotations") or {}
    props = (tools["erase_request"].get("inputSchema") or {}).get("properties", {})
    canary = t.canary("era")
    dry = c.call("erase_request", {"subject": canary})
    sc = dry.structured() or {}
    rec.expect("TOOL-18", ann.get("destructiveHint") is True and sc.get("dry_run") is True and "context" not in json.dumps(props),
               f"destructiveHint {ann.get('destructiveHint')!r}, default dry_run {sc.get('dry_run')!r}")
    one, two = canary + "a", canary + "b"
    c.call("memory_write", {"path": t.test_path("era-1"), "body": f"{one} only", "frontmatter": {"title": "e1"}})
    c.call("memory_write", {"path": t.test_path("era-2"), "body": f"{one} {two}", "frontmatter": {"title": "e2"}})
    r = c.call("erase_request", {"subject": f"{one} {two}", "dry_run": True})
    pages = ((r.structured() or {}).get("would_erase") or {}).get("pages")
    rec.expect("ERA-02", pages in (1, None) and not r.is_tool_error(),
               f"a two-word subject would erase {pages} pages; only one contains the phrase")


@check("TOOL-19", "EXP-04", tools=("export_create",), writes=True)
def export_create(t, rec):
    tok = t.token(["memory:read", "export:read", "audit:read"])
    if "export_create" not in _listed(t, tok):
        rec.skip("TOOL-19", "export_create is not offered")
        rec.skip("EXP-04", "export_create is not offered (check the export audit entry on the management surface)")
        return
    t.need_writes()
    c = t.mcp(tok)
    r = c.call("export_create", {})
    sc = r.structured() or {}
    rec.expect("TOOL-19", not r.is_tool_error() and sc.get("status") and sc.get("coverage") in ("full", "partial"),
               f"export_create gave {r.tool_text()[:100]!r}")
    log = c.call("audit_list", {"limit": 20})
    rec.expect("EXP-04", '"export"' in json.dumps(log.structured() or {}), "no audit entry with channel export")


@check("AUTH-41", "SEC-03")
def consent_page(t, rec):
    _, _, meta = t.as_meta
    if not meta:
        raise Skip("no authorization server metadata")
    t.need_register()
    try:
        o = t.oauth
        o.ensure_client()
    except Exception as e:
        raise Skip(f"no client: {e}")
    from ..oauth import pkce_pair
    _, ch = pkce_pair()
    url = o.authorize_url(t.default_scopes(), ch, "consent-check", extra={"prompt": "consent"})
    r = t.http.get(url)
    hops = 0
    while r.status in (301, 302, 303, 307) and hops < 3:
        loc = r.header("location") or ""
        if loc.startswith(o.redirect_uri.split("?")[0]):
            raise Skip("the server approved without showing a page (test mode); check the consent page by hand")
        if loc.startswith("/"):
            loc = origin_of(url) + loc
        r = t.http.get(loc)
        hops += 1
    if "html" not in r.content_type:
        raise Skip(f"no HTML page to check (HTTP {r.status} {r.content_type})")
    csp = (r.header("content-security-policy") or "").lower()
    xfo = (r.header("x-frame-options") or "").lower()
    unframable = "frame-ancestors 'none'" in csp or xfo == "deny"
    rec.expect("AUTH-41", unframable, "the consent or sign-in page can be framed (CSRF is checked by review)")
    cache = (r.header("cache-control") or "").lower()
    rec.expect("SEC-03", "frame-ancestors 'none'" in csp and "no-store" in cache and len(csp) > len("frame-ancestors 'none'"),
               f"CSP {csp!r}, Cache-Control {cache!r}")


@check("SEC-01")
def rate_limits(t, rec):
    if not t.opts.allow_load:
        rec.skip("SEC-01", "sends a burst of requests; run with --allow-load against a test deployment")
        return
    _, _, meta = t.as_meta
    if not meta:
        raise Skip("no authorization server metadata")
    endpoint = meta["token_endpoint"]
    limited = None
    for i in range(300):
        r = t.http.post(endpoint, form={"grant_type": "authorization_code", "code": f"bogus-{i}",
                                        "code_verifier": "x" * 43, "client_id": "pcp-conformance"})
        if r.status == 429:
            limited = r
            break
    rec.expect("SEC-01", limited is not None and limited.header("retry-after") is not None,
               "300 bad token requests in a row were never limited with 429 and Retry-After")
