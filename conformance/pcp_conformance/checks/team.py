"""Team features: partitions, review, delegation (SPEC §5.3, §5.4, §7.3, §7.4).

Partition checks need a second principal (--second-token, or --second-login
on a server that signs in automatically in test mode) and the name of a
partition the first principal can write and the second cannot read
(--private-partition).
"""
import json

from ..registry import Skip, check


def _blob(r):
    return json.dumps(r.message) if r.message else ""


def _second(t, scopes):
    if t.opts.second_token:
        return {"access_token": t.opts.second_token, "scope": " ".join(scopes)}
    if t.opts.second_login:
        try:
            return t.oauth.get_token(scopes, extra={"login_hint": t.opts.second_login})
        except Exception as e:
            raise Skip(f"no token for the second principal: {e}")
    raise Skip("needs a second principal: pass --second-token or --second-login")


def _owner(t):
    return t.mcp(t.token(["memory:read", "memory:write", "memory:review", "audit:read"]))


@check("MEM-12", "MEM-13", "SCOPE-04", "AUD-06", tools=("partition_list", "memory_write", "audit_list"), writes=True)
def partitions(t, rec):
    if "partitions" not in t.features():
        for rid in ("MEM-12", "MEM-13", "SCOPE-04", "AUD-06"):
            rec.skip(rid, "the context does not use partitions")
        return
    private = t.opts.private_partition
    if not private:
        raise Skip("pass --private-partition: one the first principal can write and the second cannot read")
    t.need_writes()
    a = _owner(t)
    b_tok = _second(t, ["memory:read", "memory:write", "audit:read"])
    b = t.mcp(b_tok)
    canary = t.canary("part")
    path = t.test_path("private-" + canary[-6:])
    w = a.call("memory_write", {"path": path, "body": f"Private {canary}",
                                "frontmatter": {"title": "private", "partition": private}})
    if w.is_tool_error():
        raise Skip(f"the first principal cannot write to {private}: {w.tool_text()[:100]}")
    seen = []
    pl = b.call("partition_list", {})
    if private in _blob(pl):
        seen.append("partition_list")
    for name, args in (("memory_search", {"query": canary}), ("memory_list", {"prefix": t.test_path("")}),
                       ("context_brief", {})):
        if canary in _blob(b.call(name, args)) or path in _blob(b.call(name, args)):
            seen.append(name)
    rd = b.call("memory_read", {"path": path})
    if rd.error_code() != "not_found":
        seen.append(f"memory_read gave {rd.error_code()!r}")
    rec.expect("MEM-13", not seen, f"the private partition showed through {seen}")
    bw = b.call("memory_write", {"path": t.test_path("b-into-private"), "body": "x",
                                 "frontmatter": {"title": "x", "partition": private}})
    rec.expect("SCOPE-04", bw.is_tool_error(), "the second principal wrote into a partition it has no right on")
    mine = t.test_path("b-move-" + canary[-6:])
    b.call("memory_write", {"path": mine, "body": "move me", "frontmatter": {"title": "move"}})
    mv = b.call("memory_write", {"path": mine, "body": "move me", "frontmatter": {"title": "move", "partition": private}})
    rec.expect("MEM-12", mv.is_tool_error(), "a page moved into a partition the writer has no write right on")
    al = b.call("audit_list", {"since": t.started, "limit": 100})
    if al.is_tool_error():
        rec.skip("AUD-06", "the second principal cannot call audit_list")
    else:
        rec.expect("AUD-06", private not in _blob(al) and canary not in _blob(al),
                   "audit_list shows another principal's private partition")


@check("MEM-14", "MEM-15", "SEC-11", tools=("memory_propose", "review_list", "review_resolve", "memory_read"), writes=True)
def review(t, rec):
    if "review" not in t.features():
        for rid in ("MEM-14", "MEM-15", "SEC-11"):
            rec.skip(rid, "the context does not use review")
        return
    t.need_writes()
    a = _owner(t)
    canary = t.canary("rev")
    path = t.test_path("proposal-" + canary[-6:])
    p = a.call("memory_propose", {"path": path, "body": f"Proposed {canary}", "frontmatter": {"title": "proposal"}})
    sc = p.structured() or {}
    if p.is_tool_error():
        raise Skip(f"memory_propose failed: {p.tool_text()[:100]}")
    default = a.call("memory_search", {"query": canary})
    asked = a.call("memory_search", {"query": canary, "include_review": True})
    rec.expect("MEM-15", canary not in _blob(default) and canary in _blob(asked),
               "a proposal appeared in default retrieval, or not even when asked for")
    rd = a.call("memory_read", {"path": path, "revision": sc.get("revision")} if sc.get("revision") else {"path": path})
    rec.expect("SEC-11", 'review="proposed"' in rd.tool_text(), "a proposal is not marked review=\"proposed\" in the text block")
    lst = a.call("review_list", {})
    listed = path in _blob(lst)
    tools = {x["name"] for x in (a.list_tools()[1] or [])}
    if "review_resolve" in tools and listed:
        a.call("review_resolve", {"path": path, "revision": sc.get("revision", ""), "verb": "approve"})
    try:
        b = t.mcp(_second(t, ["memory:read", "memory:propose", "memory:write"]))
    except Skip as e:
        rec.skip("MEM-14", str(e))
        return
    target = t.test_path("needs-review-" + canary[-6:])
    w = b.call("memory_write", {"path": target, "body": f"Write needing review {canary}", "frontmatter": {"title": "x"}})
    ws = w.structured() or {}
    if w.is_tool_error():
        rec.expect("MEM-14", w.error_code() == "forbidden", f"an unapplied write failed with {w.error_code()!r}")
        return
    if ws.get("applied") is True:
        live = a.call("memory_search", {"query": canary})
        rec.expect("MEM-14", target in _blob(live), "a write reported as applied is not live")
    else:
        rec.expect("MEM-14", ws.get("review_state") == "proposed" and ws.get("revision"),
                   "an unapplied write does not say it became a proposal")


@check("SCOPE-06", "SCOPE-07", writes=True)
def delegation(t, rec):
    if "delegation" not in t.features() or not t.opts.delegated_token:
        for rid in ("SCOPE-06", "SCOPE-07"):
            rec.skip(rid, "needs the delegation feature and --delegated-token (an agent token acting for a human)")
        return
    t.need_writes()
    d = t.mcp(t.opts.delegated_token)
    canary = t.canary("del")
    path = t.test_path("delegated-" + canary[-6:])
    d.call("memory_write", {"path": path, "body": f"Delegated {canary}", "frontmatter": {"title": "d",
                            "source": {"on_behalf_of": "human:forged"}}})
    fm = (_owner(t).call("memory_read", {"path": path}).structured() or {}).get("frontmatter", {})
    src = fm.get("source") or {}
    rec.expect("SCOPE-07", src.get("principal", "").startswith("agent:") and src.get("on_behalf_of", "").startswith("human:")
               and src.get("on_behalf_of") != "human:forged", f"source is {src}")
    if t.opts.private_partition:
        r = d.call("memory_search", {"query": "pcp"})
        rec.expect("SCOPE-06", t.opts.private_partition not in _blob(r),
                   "a delegated read reached a partition the human cannot read")
    else:
        rec.skip("SCOPE-06", "pass --private-partition (one the human cannot read)")
