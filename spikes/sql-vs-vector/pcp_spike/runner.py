"""Run the conditions against a question set via claude-agent-sdk.

The agent's only data access is a pair of in-process MCP tools that call the
SAME functions `tool.py` exposes on the command line (`run_query`,
`run_search`) with the same caps, timeout and logging. Built-in tools are
switched off, so there is no shell, no filesystem, and no way to reach the
corpus except through the granted tool(s).

Conditions:
  sql_narrow    -> query, agent chooses its own projection (the first pass's
                   `sql_only`, renamed now that there is a second SQL arm)
  sql_document  -> query, but every matched row is expanded to the WHOLE page
                   that contains it. The projection decision is taken away.
  vector_only   -> search
  both          -> sql_narrow's query + search

`sql_only` is accepted as an alias for `sql_narrow` so the first-pass
reproduction commands in REPORT.md §7 still run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, TextBlock, ToolUseBlock,
                              create_sdk_mcp_server, query, tool)

from . import tool as harness
from .model import TODAY
from .store import SCHEMA_DOC, NARROW_DOC, DOCUMENT_DOC
from .tool import run_query, run_search, ToolError, log_call, _cap

ROOT = Path(__file__).resolve().parent.parent

CONDITIONS = ["sql_narrow", "sql_document", "vector_only", "both"]
ALIASES = {"sql_only": "sql_narrow"}

# shape -> (corpus root, data root, question file)
CORPORA = {
    "atomic":  ("corpus-a", "data-a", "questions/questions-a.json"),
    "subject": ("corpus-b", "data-b", "questions/questions-b.json"),
}

SEARCH_DOC = """\
You also have a semantic search tool over the same memory pages. It embeds
your query and returns the nearest pages by cosine similarity, each with its
frontmatter and its COMPLETE body.

By default it searches only pages that are CURRENTLY IN FORCE -- lifecycle
'active' or 'validated', and not past their valid_until. Pass
include_stale=true to also search pages the default policy hides: lifecycle
'stale' or 'archived', and expired pages. That is the only way to reach
historical facts -- what something used to be, when it changed, what was
true on a past date. Not every store marks anything as stale.
"""

PREAMBLE = """\
You are answering questions about one person's PCP personal memory. That
person is Mara Osei-Lindqvist. Today's date is {today}.

Answer the question from the memory you can reach with your tools, and
nothing else. Rules:

  * If the memory you can reach does not contain the answer, say exactly
    NOT FOUND and stop. Do not guess, do not infer an answer from
    circumstantial detail, and do not answer from general knowledge. A page
    mentioning the topic is not the same as a page containing the answer.
  * Memory contains stale and superseded material, and it is not always
    marked as such. Two pages may say different things about the same
    subject with nothing to say which is current. Make sure the fact you
    report is the one currently in force, unless the question asks about
    the past.
  * Finish with a single final line of the form:
        ANSWER: <the answer, or NOT FOUND>
    Keep it short -- a name, a value, a date, a phrase.
"""


def _tools(log: Path | None, scope: str, backend: str, sink: list[dict],
           hide_relations: bool = False, document: bool = False):
    """The agent's only data access. Same code paths as tool.py, same caps."""
    def record(kind: str, args: dict, out: str, err: str | None, ms: float):
        rec = {"ts": time.time(), "cmd": kind, "scope": scope, "args": args,
               "document": document, "ok": err is None, "error": err,
               "bytes": len(out.encode()), "ms": round(ms, 1)}
        sink.append(rec)
        log_call(log, rec)

    qdesc = ("Run one read-only SELECT against the memory database. The reply "
             "is the FULL TEXT of every page your query matched -- include the "
             "`path` column."
             if document else
             "Run one read-only SELECT against the memory database.")

    @tool("query", qdesc, {"sql": str})
    async def _query(args):
        t = time.monotonic(); err = None
        try:
            out = run_query(scope, args["sql"], document)
        except ToolError as e:
            err = str(e); out = f"ERROR: {e}"
        out, _ = _cap(out)
        record("query", args, out, err, (time.monotonic() - t) * 1000)
        return {"content": [{"type": "text", "text": out}]}

    @tool("search",
          "Semantic search over memory pages. Returns pages with frontmatter and body.",
          {"text": str, "k": int, "include_stale": bool})
    async def _search(args):
        t = time.monotonic(); err = None
        try:
            out = run_search(scope, args["text"], int(args.get("k") or 5),
                             backend, bool(args.get("include_stale")),
                             hide_relations)
        except ToolError as e:
            err = str(e); out = f"ERROR: {e}"
        out, _ = _cap(out)
        record("search", args, out, err, (time.monotonic() - t) * 1000)
        return {"content": [{"type": "text", "text": out}]}

    return _query, _search


def system_prompt(condition: str) -> str:
    p = PREAMBLE.format(today=TODAY)
    if condition in ("sql_narrow", "sql_document", "both"):
        p += "\n" + SCHEMA_DOC.format(today=TODAY)
        p += "\n" + (DOCUMENT_DOC if condition == "sql_document" else NARROW_DOC)
    if condition in ("vector_only", "both"):
        p += "\n" + SEARCH_DOC
    return p


async def run_one(q: dict, condition: str, model: str, backend: str,
                  logdir: Path, max_turns: int = 14,
                  hide_relations: bool = False) -> dict:
    document = condition == "sql_document"
    run_id = uuid.uuid4().hex[:10]
    calllog = logdir / "tool_calls" / f"{run_id}.jsonl"
    tool_log: list[dict] = []
    qt, st = _tools(calllog, q["scope"], backend, tool_log, hide_relations, document)
    tools = {"sql_narrow": [qt], "sql_document": [qt],
             "vector_only": [st], "both": [qt, st]}[condition]
    server = create_sdk_mcp_server("pcp", "1.0.0", tools)
    allowed = [f"mcp__pcp__{t.name}" for t in tools]

    async def gate(name, tool_input, ctx):
        # Allow only this condition's granted tools. Anything else is denied,
        # so a condition cannot reach data its condition does not grant.
        if name in allowed:
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"{name} is not granted in condition {condition}")

    opts = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt(condition),
        mcp_servers={"pcp": server},
        allowed_tools=allowed,
        tools=[],                     # no built-in tools at all
        strict_mcp_config=True,
        setting_sources=[],           # do not load CLAUDE.md / settings
        can_use_tool=gate,
        max_turns=max_turns,
        cwd=str(ROOT),
    )

    calls: list[dict] = []
    texts: list[str] = []
    result: dict = {}
    t0 = time.monotonic()
    try:
        async for msg in query(prompt=q["question"], options=opts):
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        texts.append(b.text)
                    elif isinstance(b, ToolUseBlock):
                        calls.append({"name": b.name, "input": b.input})
            elif isinstance(msg, ResultMessage):
                u = msg.usage or {}
                result = {
                    "input_tokens": u.get("input_tokens", 0),
                    "output_tokens": u.get("output_tokens", 0),
                    "cache_read_input_tokens": u.get("cache_read_input_tokens", 0),
                    "cache_creation_input_tokens": u.get("cache_creation_input_tokens", 0),
                    "cost_usd": msg.total_cost_usd,
                    "duration_ms": msg.duration_ms,
                    "num_turns": msg.num_turns,
                    "is_error": msg.is_error,
                }
    except Exception as e:                      # noqa: BLE001 -- record, never abort the sweep
        result = {"harness_error": f"{type(e).__name__}: {e}"}

    text = "\n".join(texts).strip()
    answer = ""
    for line in reversed(text.splitlines()):
        if line.strip().upper().startswith("ANSWER:"):
            answer = line.split(":", 1)[1].strip()
            break
    if not answer:
        answer = text.strip().splitlines()[-1].strip() if text.strip() else ""

    return {
        "run_id": run_id, "qid": q["id"], "stratum": q["stratum"],
        "mechanism": q["mechanism"], "condition": condition, "model": model,
        "backend": backend, "scope": q["scope"], "question": q["question"],
        "shape": q.get("shape", "atomic"), "hide_relations": hide_relations,
        "gold": q["gold"], "aliases": q["aliases"], "expect": q["expect"],
        "distractor": q.get("distractor"),
        "answer": answer, "full_text": text,
        "tool_calls": calls, "n_tool_calls": len(calls),
        "tool_log": tool_log,
        "result_bytes": sum(t["bytes"] for t in tool_log),
        "tool_errors": sum(0 if t["ok"] else 1 for t in tool_log),
        "wall_ms": round((time.monotonic() - t0) * 1000, 1),
        **result,
    }


async def sweep(questions: list[dict], conditions: list[str], models: list[str],
                seeds: list[int], backend: str, logdir: Path,
                concurrency: int = 6, out: Path | None = None,
                hide_relations: bool = False, budget: float | None = None) -> list[dict]:
    jobs = [(q, c, m, s)
            for s in seeds for m in models for c in conditions for q in questions]
    sem = asyncio.Semaphore(concurrency)
    done = 0
    total = len(jobs)
    spent = 0.0
    skipped = 0
    results: list[dict] = []
    lock = asyncio.Lock()

    async def one(q, c, m, s):
        nonlocal done, spent, skipped
        async with lock:
            # Hard budget guard. A sweep that would overrun stops paying for
            # runs rather than finishing and apologising afterwards.
            if budget is not None and spent >= budget:
                skipped += 1
                return
        async with sem:
            r = await run_one(q, c, m, backend, logdir,
                              hide_relations=hide_relations)
            r["seed"] = s
        async with lock:
            done += 1
            spent += r.get("cost_usd") or 0.0
            results.append(r)
            if out:
                with out.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if done % 25 == 0 or done == total:
                print(f"  {done}/{total} runs  ${spent:.2f}", flush=True)

    await asyncio.gather(*(one(*j) for j in jobs))
    if skipped:
        print(f"  !! BUDGET GUARD: skipped {skipped}/{total} runs after "
              f"${spent:.2f} of a ${budget:.2f} budget", flush=True)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.runner")
    ap.add_argument("--shape", choices=["atomic", "subject"], default=None,
                    help="select corpus, data and question roots in one go")
    ap.add_argument("--questions", default=None)
    ap.add_argument("--corpus-root", default=None)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--logdir", default="logs")
    ap.add_argument("--backend", choices=["vector", "lexical"], default="vector")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--models", default="sonnet")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None, help="first N questions only")
    ap.add_argument("--strata", default=None,
                    help="comma-separated strata to run (default: all)")
    ap.add_argument("--hide-relations", action="store_true",
                    help="ABLATION: search returns frontmatter WITHOUT `relations`")
    ap.add_argument("--budget", type=float, default=None,
                    help="stop the sweep once measured spend passes this many USD")
    ap.add_argument("--tag", default=None, help="name for this run's output file")
    a = ap.parse_args(argv)

    shape = a.shape or "atomic"
    cdir, ddir, qfile = CORPORA[shape]
    corpus_root = ROOT / (a.corpus_root or cdir)
    data_root = ROOT / (a.data_root or ddir)
    qpath = Path(a.questions or (ROOT / qfile))
    harness.configure(corpus_root, data_root)

    qs = json.loads(qpath.read_text(encoding="utf-8"))
    if a.strata:
        keep = set(a.strata.split(","))
        qs = [q for q in qs if q["stratum"] in keep]
    if a.limit:
        qs = qs[: a.limit]
    conditions = [ALIASES.get(c, c) for c in a.conditions.split(",")]
    models = a.models.split(",")
    seeds = [int(s) for s in a.seeds.split(",")]

    logdir = Path(a.logdir)
    (logdir / "raw").mkdir(parents=True, exist_ok=True)
    tag = a.tag or f"{shape}"
    out = logdir / "raw" / f"runs-{tag}.jsonl"
    out.unlink(missing_ok=True)

    n = len(qs) * len(conditions) * len(models) * len(seeds)
    print(f"sweep [{shape}]: {len(qs)} questions x {len(conditions)} conditions x "
          f"{len(models)} models x {len(seeds)} seeds = {n} runs")
    print(f"  corpus={corpus_root.name} data={data_root.name} backend={a.backend} "
          f"concurrency={a.concurrency}"
          + (f" budget=${a.budget:.2f}" if a.budget else ""))
    if a.backend == "vector" and any(c != "sql_narrow" and c != "sql_document"
                                     for c in conditions):
        print("  pre-warming the embedding model...", flush=True)
        from .retrieval import Index
        Index(data_root, corpus_root, "vector").search("default", "warm", k=1)

    t0 = time.monotonic()
    asyncio.run(sweep(qs, conditions, models, seeds, a.backend, logdir,
                      a.concurrency, out, a.hide_relations, a.budget))
    print(f"done in {(time.monotonic()-t0)/60:.1f} min -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
