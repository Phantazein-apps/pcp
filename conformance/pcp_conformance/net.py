"""A small HTTP client: no redirects followed, every response returned."""
import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request


class Response:
    def __init__(self, status, headers, body, url):
        self.status = status
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.body = body
        self.url = url

    def header(self, name, default=None):
        return self.headers.get(name.lower(), default)

    @property
    def content_type(self):
        return (self.header("content-type") or "").split(";")[0].strip().lower()

    @property
    def text(self):
        return self.body.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.body)

    def is_json(self):
        if self.content_type != "application/json":
            return False
        try:
            self.json()
            return True
        except ValueError:
            return False

    def __repr__(self):
        return f"<{self.status} {self.content_type} {self.url}>"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Http:
    def __init__(self, timeout=15, insecure=False):
        self.timeout = timeout
        handlers = [_NoRedirect()]
        if insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        self.opener = urllib.request.build_opener(*handlers)
        self.log = []

    def request(self, method, url, body=None, headers=None, form=None, json_body=None):
        headers = dict(headers or {})
        data = body
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers.setdefault("Content-Type", "application/json")
        elif form is not None:
            data = urllib.parse.urlencode(form, doseq=True).encode()
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        headers.setdefault("User-Agent", "pcp-conformance/0.3")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                resp = Response(r.status, dict(r.headers), r.read(), url)
        except urllib.error.HTTPError as e:
            resp = Response(e.code, dict(e.headers or {}), e.read() if e.fp else b"", url)
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            resp = Response(0, {}, str(getattr(e, "reason", e)).encode(), url)
        self.log.append((method, url, resp.status))
        return resp

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)


def is_loopback(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1") or host.startswith("127.")


def parse_www_authenticate(value):
    """Parses a Bearer challenge into a dict of its parameters."""
    if not value:
        return None
    scheme, _, rest = value.strip().partition(" ")
    params = {"_scheme": scheme.lower()}
    i, n = 0, len(rest)
    while i < n:
        while i < n and rest[i] in " ,":
            i += 1
        start = i
        while i < n and rest[i] not in "=":
            i += 1
        key = rest[start:i].strip().lower()
        i += 1
        if i < n and rest[i] == '"':
            i += 1
            val = []
            while i < n and rest[i] != '"':
                if rest[i] == "\\" and i + 1 < n:
                    i += 1
                val.append(rest[i])
                i += 1
            i += 1
            params[key] = "".join(val)
        else:
            start = i
            while i < n and rest[i] != ",":
                i += 1
            params[key] = rest[start:i].strip()
        if not key:
            break
    return params


def well_known_suffixed(url, name):
    """RFC 9728 / 8414 path insertion: https://h/p -> https://h/.well-known/<name>/p."""
    p = urllib.parse.urlsplit(url)
    path = p.path.rstrip("/")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, f"/.well-known/{name}{path}", "", ""))


def origin_of(url):
    p = urllib.parse.urlsplit(url)
    return f"{p.scheme}://{p.netloc}"
