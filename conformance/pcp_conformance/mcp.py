"""MCP over Streamable HTTP, in both supported revisions.

Revision 2026-07-28 carries the protocol version in each request's _meta
and in headers; 2025-11-25 negotiates it once through initialize. PCP
requires both (SPEC §3.1), so the suite speaks both.
"""
import itertools
import json

MODERN = "2026-07-28"
LEGACY = "2025-11-25"

_ids = itertools.count(1)


class RpcResult:
    def __init__(self, response, message=None, error=None):
        self.response = response
        self.message = message or {}
        self.error = error

    @property
    def http_status(self):
        return self.response.status

    @property
    def result(self):
        return self.message.get("result")

    @property
    def rpc_error(self):
        return self.message.get("error")

    def tool_text(self):
        res = self.result or {}
        return "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")

    def is_tool_error(self):
        return bool((self.result or {}).get("isError"))

    def structured(self):
        return (self.result or {}).get("structuredContent")

    def error_code(self):
        """The §6.3 code of an isError result: from structuredContent, else the text prefix."""
        sc = self.structured() or {}
        code = (sc.get("error") or {}).get("code") if isinstance(sc, dict) else None
        if code:
            return code
        if not self.is_tool_error():
            return None
        text = self.tool_text()
        head = text.split(":", 1)[0].strip() if ":" in text else ""
        return head if head.isidentifier() and len(head) <= 32 else None


def parse_body(resp):
    """Returns the JSON-RPC message from a JSON body or the last data event of an SSE body."""
    ctype = resp.content_type
    if ctype == "application/json":
        try:
            return resp.json(), None
        except ValueError as e:
            return None, f"invalid JSON: {e}"
    if ctype == "text/event-stream":
        last = None
        for block in resp.text.split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
            if data:
                try:
                    msg = json.loads(data)
                except ValueError:
                    continue
                if "result" in msg or "error" in msg:
                    last = msg
        return last, None if last else "no response in event stream"
    return None, f"unexpected Content-Type {ctype!r}"


class McpClient:
    def __init__(self, http, endpoint, token=None, revision=MODERN, session=None):
        self.http, self.endpoint, self.token = http, endpoint, token
        self.revision, self.session = revision, session
        self.initialized = None

    def headers(self, method, name=None, extra=None):
        h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
             "MCP-Protocol-Version": self.revision}
        if self.revision == MODERN:
            h["Mcp-Method"] = method
            if name is not None:
                h["Mcp-Name"] = name
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.session:
            h["Mcp-Session-Id"] = self.session
        h.update(extra or {})
        return {k: v for k, v in h.items() if v is not None}

    def meta(self):
        return {"io.modelcontextprotocol/protocolVersion": self.revision,
                "io.modelcontextprotocol/clientInfo": {"name": "pcp-conformance", "version": "0.3"},
                "io.modelcontextprotocol/clientCapabilities": {}}

    def request(self, method, params=None, name=None, headers=None, raw_body=None):
        params = dict(params or {})
        if self.revision == MODERN:
            params["_meta"] = {**self.meta(), **params.get("_meta", {})}
        msg = {"jsonrpc": "2.0", "id": next(_ids), "method": method}
        if params:
            msg["params"] = params
        body = raw_body if raw_body is not None else json.dumps(msg).encode()
        resp = self.http.post(self.endpoint, body=body, headers=self.headers(method, name, headers))
        if resp.status != 200:
            return RpcResult(resp, error=f"HTTP {resp.status}")
        message, err = parse_body(resp)
        return RpcResult(resp, message, err)

    def initialize(self):
        """2025-11-25 handshake. Keeps a session id if the server sets one."""
        r = self.request("initialize", {"protocolVersion": self.revision, "capabilities": {},
                                        "clientInfo": {"name": "pcp-conformance", "version": "0.3"}})
        sid = r.response.header("mcp-session-id")
        if sid:
            self.session = sid
        if r.result is not None:
            self.http.post(self.endpoint, body=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
                           headers=self.headers("notifications/initialized"))
        self.initialized = r
        return r

    def discover(self):
        """server/discover in 2026-07-28; initialize before that."""
        if self.revision == MODERN:
            return self.request("server/discover")
        return self.initialize()

    def ensure_ready(self):
        if self.revision != MODERN and self.initialized is None:
            self.initialize()

    def list_tools(self):
        self.ensure_ready()
        tools, cursor = [], None
        for _ in range(20):
            r = self.request("tools/list", {"cursor": cursor} if cursor else {})
            if r.result is None:
                return r, None
            tools += r.result.get("tools", [])
            cursor = r.result.get("nextCursor")
            if not cursor:
                break
        return r, tools

    def call(self, name, arguments=None, headers=None):
        self.ensure_ready()
        return self.request("tools/call", {"name": name, "arguments": arguments or {}}, name=name, headers=headers)
