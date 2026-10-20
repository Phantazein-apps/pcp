"""AUTH checks that run the OAuth flow (SPEC §3.3, §3.4)."""
import secrets
import time
import urllib.parse

from ..mcp import McpClient
from ..net import parse_www_authenticate
from ..oauth import AuthError, pkce_pair
from ..registry import Skip, check


def _authorize_raw(t, scopes, extra=None, resource=None, challenge=True):
    """GET the authorization endpoint; returns (response, callback params or None, verifier)."""
    t.need_register()
    o = t.oauth
    o.ensure_client()
    verifier, ch = pkce_pair()
    state = secrets.token_urlsafe(8)
    url = o.authorize_url(scopes, ch if challenge else None, state, resource, extra)
    if not challenge:
        url = url.replace("&code_challenge_method=S256", "")
    r = t.http.get(url)
    loc = r.header("location") or ""
    params = None
    if r.status in (302, 303, 307) and loc.startswith(o.redirect_uri.split("?")[0]):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(loc).query))
    return r, params, verifier


def _auto(t):
    """Raw authorization tests need a server that redirects back without a person."""
    r, params, _ = _authorize_raw(t, t.default_scopes())
    if params is None:
        raise Skip("the authorization endpoint needs a person; these checks run against servers that approve automatically in test mode")


@check("AUTH-20")
def dcr_rules(t, rec):
    _, _, meta = t.as_meta
    if not meta or not meta.get("registration_endpoint"):
        rec.skip("AUTH-20", "no registration_endpoint (DCR not offered)")
        return
    t.need_register()
    good = t.oauth.register()
    bad = t.oauth.register(redirect_uri="http://pcp-conformance.invalid/callback")
    problems = []
    if good.status not in (200, 201):
        problems.append(f"a loopback redirect URI was refused (HTTP {good.status})")
    elif good.is_json() and good.json().get("client_secret") and good.json().get("token_endpoint_auth_method", "none") == "none":
        problems.append("a public client was given a client_secret")
    if bad.status in (200, 201):
        problems.append("a plain-HTTP non-loopback redirect URI was accepted")
    rec.expect("AUTH-20", not problems, "; ".join(problems))


@check("AUTH-19")
def cimd_hardening(t, rec):
    _, _, meta = t.as_meta
    if not meta or not meta.get("client_id_metadata_document_supported"):
        rec.skip("AUTH-19", "CIMD not advertised")
        return
    t.need_register()
    problems = []
    for cid in ("http://pcp-conformance.example/client.json", "https://127.0.0.1/client.json",
                "https://10.0.0.1/client.json", "https://[::1]/client.json"):
        _, ch = pkce_pair()
        q = {"response_type": "code", "client_id": cid, "redirect_uri": "http://127.0.0.1:9/callback",
             "code_challenge": ch, "code_challenge_method": "S256", "state": "x", "resource": t.endpoint}
        r = t.http.get(meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(q))
        loc = r.header("location") or ""
        if r.status == 200 and "html" in r.content_type and "error" not in r.text.lower()[:2000]:
            problems.append(f"{cid} was accepted")
        if loc.startswith("http://127.0.0.1:9/callback") and "code=" in loc:
            problems.append(f"{cid} produced a code")
    rec.expect("AUTH-19", not problems, "; ".join(problems))


@check("AUTH-21", "AUTH-22", "AUTH-34")
def authorization_rules(t, rec):
    try:
        _auto(t)
    except Skip as e:
        for rid in ("AUTH-21", "AUTH-22"):
            rec.skip(rid, str(e))
        rec.skip("AUTH-34", str(e))
        return
    o = t.oauth
    r, params, _ = _authorize_raw(t, t.default_scopes(), challenge=False)
    refused = params is None or "code" not in params
    rec.expect("AUTH-21", refused, "authorization without code_challenge returned a code")
    problems = []
    # Unregistered redirect URI: never redirected to.
    saved = o.redirect_uri
    o.redirect_uri = "https://pcp-conformance.invalid/callback"
    r2, p2, _ = _authorize_raw(t, t.default_scopes())
    o.redirect_uri = saved
    if (r2.header("location") or "").startswith("https://pcp-conformance.invalid"):
        problems.append("redirected to an unregistered redirect URI")
    # Loopback port may differ (RFC 8252 §7.3).
    port_changed = saved.replace(f":{urllib.parse.urlsplit(saved).port}/", ":9/")
    o.redirect_uri = port_changed
    r3, p3, _ = _authorize_raw(t, t.default_scopes())
    o.redirect_uri = saved
    if not (r3.header("location") or "").startswith("http://127.0.0.1:9/"):
        problems.append("a loopback redirect URI with another port was refused")
    # Codes are single use.
    _, p4, v4 = _authorize_raw(t, t.default_scopes())
    if p4 and "code" in p4:
        first = o.exchange(p4["code"], v4)
        second = o.exchange(p4["code"], v4)
        if first.status != 200:
            problems.append(f"code exchange failed: HTTP {first.status}")
        if second.status == 200:
            problems.append("an authorization code was accepted twice")
        rec.expect("AUTH-34", bool(p4.get("iss")), "no iss in the authorization response")
    rec.expect("AUTH-22", not problems, "; ".join(problems))


@check("AUTH-24", "AUTH-25", "AUTH-33", "SCOPE-03")
def resource_binding(t, rec):
    tok = t.any_token()
    rec.expect("SCOPE-03", bool(tok.get("scope")), "the token response has no scope")
    if "expires_in" in tok:
        rec.expect("AUTH-33", int(tok["expires_in"]) <= 3600, f"access tokens live {tok['expires_in']} s")
    else:
        rec.skip("AUTH-33", "no expires_in in the token response")
    other = t.opts.other_endpoint
    if other:
        r = McpClient(t.http, other, tok["access_token"], t.revision(tok["access_token"])).request("tools/list")
        params = parse_www_authenticate(r.response.header("www-authenticate")) or {}
        rec.expect("AUTH-25", r.http_status == 401 and params.get("error") == "invalid_token",
                   f"a token for {t.endpoint} at {other} gave HTTP {r.http_status} error={params.get('error')!r}")
    else:
        rec.skip("AUTH-25", "needs a second context: pass --other-endpoint")
    try:
        _auto(t)
    except Skip as e:
        rec.skip("AUTH-24", str(e))
        return
    problems = []
    unknown = t.endpoint.rstrip("/") + "-pcp-conformance-unknown"
    r, params, verifier = _authorize_raw(t, t.default_scopes(), resource=unknown)
    if params and "code" in params:
        ex = t.oauth.exchange(params["code"], verifier, resource=unknown)
        if ex.status == 200:
            problems.append("a token was issued for an unknown resource")
        elif ex.is_json() and ex.json().get("error") != "invalid_target":
            problems.append(f"unknown resource refused with {ex.json().get('error')!r}, not invalid_target")
    elif params and params.get("error") not in ("invalid_target", None):
        problems.append(f"unknown resource refused with {params.get('error')!r}, not invalid_target")
    if other:
        r, params, verifier = _authorize_raw(t, t.default_scopes())
        if params and "code" in params:
            ex = t.oauth.exchange(params["code"], verifier, resource=False,
                                  extra={"resource": [t.endpoint, other]})
            if ex.status == 200:
                problems.append("a token was issued for two contexts at once")
    rec.expect("AUTH-24", not problems, "; ".join(problems))


@check("AUTH-30", "AUTH-31")
def refresh_rotation(t, rec):
    tok = t.token(fresh=True)
    rt = tok.get("refresh_token")
    if not rt:
        raise Skip("no refresh token issued")
    o = t.oauth
    r1 = o.refresh(rt)
    if r1.status != 200:
        rec.fail("AUTH-30", f"refresh failed: HTTP {r1.status} {r1.text[:120]}")
        rec.skip("AUTH-31", "refresh failed")
        return
    new = r1.json()
    rotated = new.get("refresh_token") and new["refresh_token"] != rt
    reuse = o.refresh(rt)
    rec.expect("AUTH-30", bool(rotated) and reuse.status != 200,
               "refresh token not rotated" if not rotated else "a rotated refresh token was accepted again")
    r = McpClient(t.http, t.endpoint, new["access_token"], t.revision(new["access_token"])).request("tools/list")
    rec.expect("AUTH-31", r.http_status == 401, "reusing a rotated refresh token did not revoke the grant")


@check("AUTH-32", needs=("a narrow token",))
def refresh_never_widens(t, rec):
    narrow = t.token(["profile.core:read"], fresh=True)
    rt = narrow.get("refresh_token")
    if not rt:
        raise Skip("no refresh token issued")
    r = t.oauth.refresh(rt, scope="profile.core:read memory:read memory:write")
    if r.status != 200:
        rec.ok("AUTH-32", f"a widening refresh was refused (HTTP {r.status})")
        return
    new = r.json()
    widened = {"memory:read", "memory:write"} & set((new.get("scope") or "").split())
    call = McpClient(t.http, t.endpoint, new["access_token"], t.revision(new["access_token"])).call(
        "memory_search", {"query": "pcp-conformance"})
    can_read = call.http_status == 200 and call.result is not None and not call.is_tool_error()
    rec.expect("AUTH-32", not widened and not can_read,
               f"refresh widened the grant to {sorted(widened)}" if widened else "the refreshed token can read memory")


@check("AUTH-28")
def revocation(t, rec):
    _, _, meta = t.as_meta
    if not meta or not meta.get("revocation_endpoint"):
        raise Skip("no RFC 7009 revocation endpoint; check revocation on the management surface by hand")
    tok = t.token(fresh=True)
    o = t.oauth
    o.revoke(tok.get("refresh_token") or tok["access_token"], "refresh_token" if tok.get("refresh_token") else None)
    deadline = time.time() + t.opts.revocation_wait
    status = None
    while time.time() < deadline:
        r = McpClient(t.http, t.endpoint, tok["access_token"], t.revision(tok["access_token"])).request("tools/list")
        status = r.http_status
        if status == 401:
            break
        time.sleep(min(10, max(1, t.opts.revocation_wait / 30)))
    rec.expect("AUTH-28", status == 401,
               f"the access token still works {t.opts.revocation_wait} s after its grant was revoked (HTTP {status})")
