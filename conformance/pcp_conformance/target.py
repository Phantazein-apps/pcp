"""The server under test: discovery, metadata, schemas, tokens and clients."""
import importlib.util
import secrets
import urllib.parse

from .mcp import McpClient, MODERN
from .net import Http, origin_of, parse_www_authenticate, well_known_suffixed
from .oauth import AuthError, OAuthClient, discover_as
from .registry import ROOT, Skip


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_schemas", ROOT / "scripts" / "validate_schemas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Options:
    def __init__(self, **kw):
        self.endpoint = kw.get("endpoint")
        self.discovery = kw.get("discovery")
        self.other_endpoint = kw.get("other_endpoint")
        self.token = kw.get("token")
        self.token_scopes = kw.get("token_scopes")
        self.client_id = kw.get("client_id")
        self.interactive = kw.get("interactive", False)
        self.allow_writes = kw.get("allow_writes", False)
        self.allow_load = kw.get("allow_load", False)
        self.allow_register = kw.get("allow_register", False)
        self.revocation_wait = kw.get("revocation_wait", 300)
        self.scan_path = kw.get("scan_path")
        self.second_token = kw.get("second_token")
        self.second_login = kw.get("second_login")
        self.private_partition = kw.get("private_partition")
        self.delegated_token = kw.get("delegated_token")
        self.insecure = kw.get("insecure", False)
        self.timeout = kw.get("timeout", 15)


class Target:
    def __init__(self, opts, out=print):
        self.opts, self.out = opts, out
        self.http = Http(timeout=opts.timeout, insecure=opts.insecure)
        self.run_id = secrets.token_hex(4)
        import datetime as _dt
        self.started = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._cache = {}
        self._tokens = {}
        self._oauth = None
        self.validator_mod = _load_validator()
        self.schemas, self.registry = self.validator_mod.load_schemas()

    # ----------------------------------------------------------- utilities
    def canary(self, label="c"):
        return f"pcpcanary{label}{secrets.token_hex(6)}"

    def test_path(self, name):
        return f"pcp-conformance/{self.run_id}/{name}"

    def schema_errors(self, name, instance, pointer=None):
        v = self.validator_mod.validator(self.schemas, self.registry, name, pointer)
        return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in v.iter_errors(instance)]

    def tool_schema_errors(self, tool, kind, instance):
        return self.schema_errors("tools.schema.json", instance, f"/$defs/{tool}_{kind}")

    def need_register(self, strict=False):
        """strict: only --allow-register (DCR rule checks and CIMD probes); otherwise any flag that implies a client."""
        o = self.opts
        if strict and not o.allow_register:
            raise Skip("registers clients and probes the CIMD fetcher; run with --allow-register")
        if not (o.allow_register or o.allow_writes or o.interactive or o.client_id):
            raise Skip("registers OAuth clients; run with --allow-register (or --interactive, --allow-writes)")

    def need_writes(self):
        if not self.opts.allow_writes:
            raise Skip("writes test data; run with --allow-writes against a throwaway context")

    # ----------------------------------------------------------- discovery
    @property
    def context_doc_url(self):
        if "doc_url" not in self._cache:
            self._find_context_doc()
        return self._cache["doc_url"]

    @property
    def context_doc(self):
        if "doc_url" not in self._cache:
            self._find_context_doc()
        return self._cache.get("doc")

    def _find_context_doc(self):
        candidates = []
        if self.opts.discovery:
            candidates.append(self.opts.discovery)
        if self.opts.endpoint:
            p = urllib.parse.urlsplit(self.opts.endpoint)
            parts = p.path.rstrip("/").split("/")
            for i in range(len(parts), 0, -1):
                base = "/".join(parts[:i])
                candidates.append(f"{p.scheme}://{p.netloc}{base}/.well-known/pcp.json")
        found_url, found = None, None
        for url in candidates:
            r = self.http.get(url, headers={"Accept": "application/json"})
            if r.status == 200 and r.is_json():
                doc = r.json()
                if doc.get("multi_context"):
                    continue
                if not self.opts.endpoint or doc.get("mcp_endpoint") == self.opts.endpoint or url == self.opts.discovery:
                    found_url, found = url, doc
                    break
        self._cache["doc_url"], self._cache["doc"] = found_url, found
        if found and not self.opts.endpoint:
            self.opts.endpoint = found.get("mcp_endpoint")

    @property
    def endpoint(self):
        if not self.opts.endpoint:
            self._find_context_doc()
        if not self.opts.endpoint:
            raise Skip("no MCP endpoint: pass --endpoint or --discovery")
        return self.opts.endpoint

    @property
    def context_base(self):
        url = self.context_doc_url
        return url[: -len("/.well-known/pcp.json")] if url else None

    @property
    def root_doc(self):
        if "root" not in self._cache:
            r = self.http.get(origin_of(self.endpoint) + "/.well-known/pcp.json", headers={"Accept": "application/json"})
            self._cache["root"] = (r, r.json() if r.status == 200 and r.is_json() else None)
        return self._cache["root"]

    @property
    def multi_context(self):
        r, doc = self.root_doc
        return bool(doc and doc.get("multi_context"))

    def kind(self):
        return (self.context_doc or {}).get("kind")

    def features(self):
        return set((self.context_doc or {}).get("features", []))

    def custody(self):
        return ((self.context_doc or {}).get("encryption") or {}).get("key_custody")

    # ------------------------------------------------------------ challenge
    @property
    def challenge(self):
        """The 401 an unauthenticated tools/list gets."""
        if "challenge" not in self._cache:
            c = McpClient(self.http, self.endpoint)
            r = c.request("tools/list")
            self._cache["challenge"] = r.response
        return self._cache["challenge"]

    @property
    def prm_url(self):
        params = parse_www_authenticate(self.challenge.header("www-authenticate"))
        if params and params.get("resource_metadata"):
            return params["resource_metadata"]
        if self.context_doc and self.context_doc.get("resource_metadata"):
            return self.context_doc["resource_metadata"]
        return well_known_suffixed(self.endpoint, "oauth-protected-resource")

    @property
    def prm(self):
        if "prm" not in self._cache:
            r = self.http.get(self.prm_url, headers={"Accept": "application/json"})
            self._cache["prm"] = (r, r.json() if r.status == 200 and r.is_json() else None)
        return self._cache["prm"]

    @property
    def as_meta(self):
        if "as" not in self._cache:
            _, prm = self.prm
            servers = (prm or {}).get("authorization_servers") or []
            if not servers:
                self._cache["as"] = (None, None, None)
            else:
                url, r = discover_as(self.http, servers[0])
                self._cache["as"] = (url, r, r.json() if r else None)
        return self._cache["as"]

    # --------------------------------------------------------------- tokens
    @property
    def oauth(self):
        if self._oauth is None:
            _, _, meta = self.as_meta
            if not meta:
                raise Skip("no authorization server metadata")
            self._oauth = OAuthClient(self.http, self.endpoint, self.prm[1], meta,
                                      interactive=self.opts.interactive, client_id=self.opts.client_id, out=self.out)
        return self._oauth

    def default_scopes(self):
        _, prm = self.prm
        return list((prm or {}).get("scopes_supported") or ["profile.core:read", "memory:read", "memory:write"])

    def token(self, scopes=None, fresh=False, resource=None):
        """A token dict for exactly these scopes. Raises Skip when none can be had."""
        scopes = sorted(set(scopes or self.default_scopes()))
        key = (tuple(scopes), resource)
        if not fresh and key in self._tokens:
            return self._tokens[key]
        if self.opts.token and not fresh and resource is None:
            given = set((self.opts.token_scopes or " ".join(self.default_scopes())).split())
            if set(scopes) == given:
                tok = {"access_token": self.opts.token, "scope": " ".join(sorted(given))}
                self._tokens[key] = tok
                return tok
        if not self.opts.client_id:
            self.need_register()
        try:
            tok = self.oauth.get_token(scopes, resource)
        except AuthError as e:
            raise Skip(f"no token for {' '.join(scopes)}: {e}")
        tok["_requested"] = scopes
        if not fresh:
            self._tokens[key] = tok
        return tok

    def any_token(self):
        """The default token, or the supplied one."""
        if self.opts.token:
            given = (self.opts.token_scopes or " ".join(self.default_scopes())).split()
            return self.token(given)
        return self.token()

    def mcp(self, token=None, revision=None):
        tok = token["access_token"] if isinstance(token, dict) else token
        return McpClient(self.http, self.endpoint, tok, revision or self.revision(tok))

    def revision(self, tok=None):
        """2026-07-28 if the server answers it, else 2025-11-25. AUTH-01 and AUTH-02 test both."""
        if "revision" not in self._cache:
            if tok is None:
                return MODERN
            from .mcp import LEGACY
            r = McpClient(self.http, self.endpoint, tok, MODERN).request("tools/list")
            self._cache["revision"] = MODERN if r.result is not None else LEGACY
        return self._cache["revision"]

    def granted(self, token):
        return set((token.get("scope") or "").split())
