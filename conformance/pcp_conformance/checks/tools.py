"""MCP transport and tool surface (SPEC §3.1, §6). One token."""
import re

from ..mcp import LEGACY, MODERN, McpClient
from ..net import is_loopback
from ..registry import Skip, check

NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
RESERVED = {"profile", "memory", "context", "review", "partition", "audit", "export", "erase", "doc", "handoff"}
STANDARD = {"profile_get", "profile_update", "memory_search", "memory_read", "memory_list", "memory_write",
            "memory_propose", "review_list", "review_resolve", "partition_list", "context_brief", "audit_list",
            "export_create", "erase_request"}


def tools_of(t):
    if "tools" not in t._cache:
        tok = t.any_token()
        r, tools = t.mcp(tok).list_tools()
        t._cache["tools"] = (r, tools or [])
    return t._cache["tools"]


@check("AUTH-01", "AUTH-02", "AUTH-03", "AUTH-04", "AUTH-06")
def transport(t, rec):
    tok = t.any_token()["access_token"]
    legacy = McpClient(t.http, t.endpoint, tok, LEGACY)
    init = legacy.initialize()
    lr, ltools = legacy.list_tools()
    rec.expect("AUTH-01", init.result is not None and ltools is not None,
               f"2025-11-25 initialize/tools/list failed: {init.error or init.rpc_error or lr.error or lr.rpc_error}")
    modern = McpClient(t.http, t.endpoint, tok, MODERN)
    mr, mtools = modern.list_tools()
    rec.expect("AUTH-02", mtools is not None,
               f"2026-07-28 tools/list failed: {mr.error or mr.rpc_error}")
    same = None
    if ltools is not None:
        nosession = McpClient(t.http, t.endpoint, tok, LEGACY)
        nosession.initialized = True
        nr, ntools = nosession.list_tools()
        if ntools is not None:
            same = sorted(x["name"] for x in ntools) == sorted(x["name"] for x in ltools)
    if same is None:
        rec.skip("AUTH-03", "could not compare answers with and without a session")
    else:
        rec.expect("AUTH-03", same, "tools/list differs with and without an MCP session")
    working = lr if ltools is not None else mr
    ctype = working.response.content_type
    doc = t.context_doc or {}
    rec.expect("AUTH-04", ctype in ("application/json", "text/event-stream") and "sse_endpoint" not in doc,
               f"POST answered with {ctype!r}" if ctype not in ("application/json", "text/event-stream") else "sse_endpoint is listed")
    client = t.mcp(tok)
    h = client.headers("tools/list")
    h["Origin"] = "https://pcp-conformance.invalid"
    import json as _json
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    if client.revision == MODERN:
        body["params"] = {"_meta": client.meta()}
    resp = t.http.post(t.endpoint, body=_json.dumps(body).encode(), headers=h)
    rec.expect("AUTH-06", resp.status == 403, f"a foreign Origin got HTTP {resp.status}, expected 403")


@check("TOOL-01", "TOOL-02", "TOOL-03", "TOOL-04", "TOOL-05", "TOOL-14", "TOOL-15",
       tools=("profile_get", "profile_update", "memory_search", "memory_read", "memory_list", "memory_write",
              "context_brief", "audit_list", "memory_propose", "review_list", "partition_list"))
def tool_list(t, rec):
    r, tools = tools_of(t)
    if not tools:
        raise Skip(f"tools/list failed: {r.error or r.rpc_error}")
    names = [x["name"] for x in tools]
    bad = [n for n in names if not NAME.match(n)]
    rec.expect("TOOL-01", not bad, f"names that break the rule: {bad}")
    doc = t.context_doc or {}
    required = {"memory_search", "memory_read", "memory_list", "memory_write", "context_brief", "audit_list"}
    if doc.get("profile", "core" if doc.get("kind") != "team" else "team") != "none":
        required |= {"profile_get", "profile_update"}
    feats = set(doc.get("features", []))
    if "review" in feats:
        required |= {"memory_propose", "review_list"}
    if "partitions" in feats:
        required.add("partition_list")
    granted = t.granted(t.any_token())
    missing = sorted(required - set(names))
    note = "" if not missing else f" (the token holds {sorted(granted)}; a server may hide tools a token cannot call)"
    rec.expect("TOOL-03", not missing, f"missing tools: {missing}{note}")
    problems, schema_problems = [], []
    for tool in tools:
        n = tool["name"]
        ann = tool.get("annotations") or {}
        if not tool.get("title") and not ann.get("title"):
            problems.append(f"{n}: no title")
        if not ann or not any(k in ann for k in ("readOnlyHint", "destructiveHint", "idempotentHint")):
            problems.append(f"{n}: no annotations")
        if "outputSchema" not in tool:
            problems.append(f"{n}: no outputSchema")
        if n in STANDARD and ann.get("openWorldHint") is not False:
            problems.append(f"{n}: openWorldHint is not false")
        ins = tool.get("inputSchema") or {}
        if n in STANDARD and (set(ins) & {"oneOf", "anyOf", "allOf"} or ins.get("type") != "object" or "$ref" in str(ins)):
            schema_problems.append(n)
    rec.expect("TOOL-04", not problems, "; ".join(problems[:8]))
    rec.expect("TOOL-05", not schema_problems, f"inputSchema not a self-contained plain object: {schema_problems}")
    conns = doc.get("connections") or []
    if conns:
        cbad = [c for c in conns if not re.match(r"^[a-z][a-z0-9]{0,15}$", c) or c in RESERVED]
        ctools = [x for x in tools if x["name"].split("_")[0] in conns]
        open_world = [x["name"] for x in ctools if (x.get("annotations") or {}).get("openWorldHint") is not True]
        rec.expect("TOOL-02", not cbad, f"bad connection ids: {cbad}")
        rec.expect("TOOL-14", not open_world, f"connection tools without openWorldHint: true: {open_world}")
    else:
        rec.skip("TOOL-02", "no connections")
        rec.skip("TOOL-14", "no connections")
    exts = doc.get("extensions") or []
    ext_tools = [x["name"] for x in tools if x["name"] not in STANDARD and x["name"].split("_")[0] not in conns]
    if ext_tools:
        rec.expect("TOOL-15", bool(exts), f"extension tools {ext_tools} but no extensions in discovery")
    else:
        rec.skip("TOOL-15", "no extension tools")


@check("TOOL-06", "TOOL-07", "TOOL-08", "TOOL-09", "TOOL-10", "TOOL-12", "MEM-19", "PROF-01", "PROF-02", "PROF-05",
       "PROF-08", tools=("memory_read", "memory_search", "memory_list", "profile_get", "context_brief"))
def tool_results(t, rec):
    tok = t.any_token()
    c = t.mcp(tok)
    granted = t.granted(tok)
    problems, texts = [], []
    calls = [("memory_list", {"limit": 5}), ("memory_search", {"query": "pcp conformance", "limit": 3}),
             ("context_brief", {})]
    kind = t.kind()
    if kind != "team":
        calls.append(("profile_get", {}))
    results = {}
    for name, args in calls:
        r = c.call(name, args)
        results[name] = r
        if r.result is None:
            problems.append(f"{name}: {r.error or r.rpc_error}")
            continue
        if r.is_tool_error():
            continue
        sc = r.structured()
        if sc is None:
            problems.append(f"{name}: no structuredContent")
        else:
            errs = t.tool_schema_errors(name, "output", sc)
            if errs:
                problems.append(f"{name}: {errs[0]}")
        texts.append(bool(r.tool_text()))
    rec.expect("TOOL-06", not problems, "; ".join(problems[:6]))
    rec.expect("TOOL-07", all(texts) if texts else False, "a successful result has no text block")
    nf = c.call("memory_read", {"path": t.test_path("does-not-exist")})
    code = nf.error_code()
    first = nf.tool_text()
    rec.expect("TOOL-08", nf.is_tool_error() and nf.rpc_error is None and first.startswith(f"{code}: "),
               f"a missing page gave {nf.rpc_error or first[:80]!r}")
    sc = nf.structured() or {}
    rec.expect("TOOL-09", isinstance(sc, dict) and isinstance(sc.get("error"), dict) and "code" in sc["error"],
               "the error result has no structuredContent.error")
    rec.expect("TOOL-10", code == "not_found", f"a missing page gave {code!r}, expected not_found")
    both = c.call("memory_read", {"path": t.test_path("x"), "id": "x"})
    neither = c.call("memory_read", {})
    rec.expect("TOOL-12", both.error_code() == "invalid_input" and neither.error_code() == "invalid_input",
               f"path and id together gave {both.error_code()!r}, neither gave {neither.error_code()!r}")
    if "memory:read" in granted:
        r = c.call("memory_search", {"query": "pcp conformance", "as_of": "2026-01-01T00:00:00Z"})
        ok = r.result is not None and not r.is_tool_error()
        rec.expect("MEM-19", ok, f"as_of was refused: {r.tool_text()[:80] or r.error}")
    else:
        rec.skip("MEM-19", "the token lacks memory:read")
    pg = results.get("profile_get")
    if pg is not None and pg.result and not pg.is_tool_error():
        sc = pg.structured() or {}
        prof = sc.get("profile")
        if kind in ("personal", "work"):
            rec.expect("PROF-01", sc.get("profile_type") == "core" and (prof is None or not t.schema_errors("profile.core.schema.json", prof)),
                       f"profile_type {sc.get('profile_type')!r}, or the profile fails profile.core")
            rec.skip("PROF-02", "not a team context")
        rec.expect("PROF-05", "profile" in sc, "profile_get output has no profile member")
        bad = c.call("profile_get", {"namespaces": ["pcp.legal"]})
        leaked = ((bad.structured() or {}).get("extensions") or {}).get("pcp.legal")
        rec.expect("PROF-08", not leaked, "pcp.legal returned data, but it has no published schema")
    elif kind == "team":
        tg = c.call("profile_get", {})
        sc = tg.structured() or {}
        prof = sc.get("profile")
        rec.skip("PROF-01", "team context")
        rec.expect("PROF-02", prof is None or not t.schema_errors("profile.team.schema.json", prof),
                   "the team profile fails profile.team")
        rec.expect("PROF-05", tg.is_tool_error() or "profile" in sc, "profile_get output has no profile member")
        rec.skip("PROF-08", "team context")
    else:
        for rid in ("PROF-01", "PROF-02", "PROF-05", "PROF-08"):
            rec.skip(rid, "profile_get not callable with this token")


@check("TOOL-16", "TOOL-17")
def mcp_mechanics(t, rec):
    tok = t.any_token()
    c = t.mcp(tok)
    r = c.discover()
    res = r.result or {}
    caps = res.get("capabilities") or {}
    ext = (caps.get("extensions") or {}).get("io.github.pcp-protocol/pcp") or \
          (caps.get("experimental") or {}).get("io.github.pcp-protocol/pcp")
    rec.expect("TOOL-16", isinstance(ext, dict) and ext.get("pcp_version") == "0.3",
               "PCP is not declared as io.github.pcp-protocol/pcp with pcp_version 0.3")
    instructions = res.get("instructions") or ""
    kind = t.kind() or ""
    rec.expect("TOOL-17", bool(instructions) and kind in instructions.lower(),
               "no instructions, or they do not name the context's kind")
    t._cache["instructions"] = instructions


@check("SEC-05", "SEC-06", "SEC-07")
def localhost_profile(t, rec):
    if not is_loopback(t.endpoint):
        for rid in ("SEC-05", "SEC-06", "SEC-07"):
            rec.skip(rid, "not a loopback server")
        return
    import json as _json
    import socket
    import urllib.parse
    p = urllib.parse.urlsplit(t.endpoint)
    port = p.port or 80
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    if ip and not ip.startswith("127."):
        sock = socket.socket()
        sock.settimeout(2)
        reachable = sock.connect_ex((ip, port)) == 0
        sock.close()
        rec.expect("SEC-05", not reachable, f"the server also listens on {ip}:{port}")
    else:
        rec.skip("SEC-05", "no non-loopback address to probe")
    tok = t.any_token()["access_token"]
    c = t.mcp(tok)
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    if c.revision == MODERN:
        body["params"] = {"_meta": c.meta()}
    raw = _json.dumps(body).encode()
    h = c.headers("tools/list")
    h["Host"] = "pcp-conformance.invalid"
    r1 = t.http.post(t.endpoint, body=raw, headers=h)
    rec.expect("SEC-06", r1.status in (403, 421), f"a foreign Host got HTTP {r1.status}")
    h = c.headers("tools/list")
    h["Content-Type"] = "text/plain"
    r2 = t.http.post(t.endpoint, body=raw, headers=h)
    h = c.headers("tools/list")
    h["Origin"] = "http://pcp-conformance.invalid"
    r3 = t.http.post(t.endpoint, body=raw, headers=h)
    rec.expect("SEC-07", r2.status >= 400 and r3.status == 403,
               f"text/plain POST gave HTTP {r2.status}; a foreign Origin gave HTTP {r3.status}")
