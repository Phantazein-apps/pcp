"""OAuth client side: registration, authorization with PKCE, tokens.

Authorization is automatic when the server redirects straight back (the
reference server does in test mode), and interactive otherwise: the suite
prints the authorization URL, the person approves in a browser, and a
loopback listener catches the redirect.
"""
import base64
import hashlib
import http.server
import secrets
import threading
import urllib.parse
import webbrowser

from .net import origin_of, well_known_suffixed


def pkce_pair():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class AuthError(Exception):
    pass


class _Catcher(http.server.BaseHTTPRequestHandler):
    result = None

    def do_GET(self):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        type(self).result = q
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"PCP conformance: authorization received. You can close this tab.")

    def log_message(self, *a):
        pass


class OAuthClient:
    def __init__(self, http, resource, prm, as_meta, interactive=False, client_id=None, out=print):
        self.http, self.resource, self.prm, self.as_meta = http, resource, prm, as_meta
        self.interactive, self.client_id, self.out = interactive, client_id, out
        self.redirect_uri = None
        self.registration = None
        self._port = None

    # ------------------------------------------------------------ registration
    def register(self, redirect_uri=None, **extra):
        endpoint = self.as_meta.get("registration_endpoint")
        if not endpoint:
            raise AuthError("no registration_endpoint; pass --client-id for a pre-registered or CIMD client")
        body = {
            "client_name": "PCP conformance suite",
            "redirect_uris": [redirect_uri or self.loopback_redirect()],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        body.update(extra)
        return self.http.post(endpoint, json_body=body)

    def ensure_client(self):
        if self.client_id:
            if not self.redirect_uri:
                self.redirect_uri = self.loopback_redirect()
            return self.client_id
        r = self.register()
        if r.status not in (200, 201) or not r.is_json():
            raise AuthError(f"client registration failed: HTTP {r.status} {r.text[:200]}")
        self.registration = r.json()
        self.client_id = self.registration["client_id"]
        self.redirect_uri = self.registration.get("redirect_uris", [self.loopback_redirect()])[0]
        return self.client_id

    def loopback_redirect(self):
        if self._port is None:
            import socket
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            self._port = s.getsockname()[1]
            s.close()
        return f"http://127.0.0.1:{self._port}/callback"

    # ----------------------------------------------------------- authorization
    def authorize_url(self, scopes, challenge, state, resource=None, extra=None):
        q = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if resource is not False:
            q["resource"] = resource or self.resource
        q.update(extra or {})
        q = {k: v for k, v in q.items() if v is not None}
        return self.as_meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(q)

    def authorize(self, scopes, resource=None, extra=None):
        """Returns (callback params, verifier). Raises AuthError when it cannot."""
        self.ensure_client()
        verifier, challenge = pkce_pair()
        state = secrets.token_urlsafe(12)
        url = self.authorize_url(scopes, challenge, state, resource, extra)
        r = self.http.get(url)
        loc = r.header("location") or ""
        if r.status in (301, 302, 303, 307) and loc.startswith(self.redirect_uri.split("?")[0]):
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(loc).query))
        elif self.interactive:
            params = self._interactive(url)
        else:
            raise AuthError("authorization needs a person (run with --interactive), "
                            f"server answered HTTP {r.status}")
        if params.get("state") != state:
            raise AuthError("state mismatch in authorization response")
        return params, verifier

    def _interactive(self, url):
        port = urllib.parse.urlsplit(self.redirect_uri).port
        _Catcher.result = None
        srv = http.server.HTTPServer(("127.0.0.1", port), _Catcher)
        t = threading.Thread(target=srv.handle_request, daemon=True)
        t.start()
        self.out(f"\nApprove the PCP conformance suite in your browser:\n  {url}\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        t.join(timeout=600)
        srv.server_close()
        if not _Catcher.result:
            raise AuthError("no authorization response within 10 minutes")
        return _Catcher.result

    # ------------------------------------------------------------------ tokens
    def token_request(self, form):
        return self.http.post(self.as_meta["token_endpoint"], form=form,
                              headers={"Accept": "application/json"})

    def exchange(self, code, verifier, resource=None, extra=None):
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        if resource is not False:
            form["resource"] = resource or self.resource
        form.update(extra or {})
        return self.token_request(form)

    def refresh(self, refresh_token, scope=None, resource=None):
        form = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": self.client_id,
                "resource": resource or self.resource}
        if scope:
            form["scope"] = scope
        return self.token_request(form)

    def revoke(self, token, hint=None):
        endpoint = self.as_meta.get("revocation_endpoint")
        if not endpoint:
            return None
        form = {"token": token, "client_id": self.client_id}
        if hint:
            form["token_type_hint"] = hint
        return self.http.post(endpoint, form=form)

    def get_token(self, scopes, resource=None, extra=None):
        params, verifier = self.authorize(scopes, resource, extra)
        if "code" not in params:
            raise AuthError(f"authorization refused: {params.get('error')} {params.get('error_description', '')}")
        r = self.exchange(params["code"], verifier, resource)
        if r.status != 200 or not r.is_json():
            raise AuthError(f"token exchange failed: HTTP {r.status} {r.text[:200]}")
        tok = r.json()
        tok["_iss"] = params.get("iss")
        return tok


def discover_as(http, issuer):
    """RFC 8414 then OIDC discovery, in MCP's probe order."""
    p = urllib.parse.urlsplit(issuer)
    if p.path and p.path != "/":
        candidates = [well_known_suffixed(issuer, "oauth-authorization-server"),
                      well_known_suffixed(issuer, "openid-configuration"),
                      issuer.rstrip("/") + "/.well-known/openid-configuration"]
    else:
        o = origin_of(issuer)
        candidates = [o + "/.well-known/oauth-authorization-server", o + "/.well-known/openid-configuration"]
    for url in candidates:
        r = http.get(url, headers={"Accept": "application/json"})
        if r.status == 200 and r.is_json():
            return url, r
    return None, None
