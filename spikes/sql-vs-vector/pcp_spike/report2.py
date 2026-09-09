"""Aggregate the second-pass sweeps into the tables that go into REPORT.md §8.

Every accuracy figure here is reported as `mean% (min-max)` across seeds.
Nothing is a single draw, because the brief for this pass says no headline
number goes out without a range attached, and the first pass's 57/58/58 was
exactly the kind of number that needed one.
"""
from __future__ import annotations

import argparse
import json
import statistics as stat
from collections import defaultdict
from pathlib import Path

from .model import STRATA

CONDITIONS = ["sql_narrow", "sql_document", "vector_only", "both"]
SHAPES = [("atomic", "corpus-a"), ("subject", "corpus-b")]
SHAPE_LABEL = dict(SHAPES)


def load(*paths: str) -> list[dict]:
    out = []
    for p in paths:
        f = Path(p)
        if not f.exists():
            continue
        out += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    return out


def sel(recs, **kw) -> list[dict]:
    def ok(r):
        for k, v in kw.items():
            if v is None:
                continue
            if r.get(k) != v:
                return False
        return True
    return [r for r in recs if ok(r)]


# ------------------------------------------------------------------ stats --
def acc_by_seed(rows: list[dict]) -> list[float]:
    by: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by[r.get("seed", 1)].append(r)
    return [sum(1 for x in v if x["verdict"] == "correct") / len(v)
            for v in by.values() if v]


def cell(rows: list[dict]) -> dict:
    """One cell of a table: accuracy with a range, plus the cost side."""
    if not rows:
        return {}
    per_seed = acc_by_seed(rows)
    n_correct = sum(1 for r in rows if r["verdict"] == "correct")
    return {
        "n": len(rows),
        "seeds": len(per_seed),
        "acc": n_correct / len(rows),
        "acc_mean": stat.mean(per_seed),
        "acc_min": min(per_seed),
        "acc_max": max(per_seed),
        "correct": n_correct,
        "partial": sum(1 for r in rows if r["verdict"] == "partial"),
        "wrong": sum(1 for r in rows if r["verdict"] == "wrong"),
        "leak": sum(1 for r in rows if r["verdict"] == "leak"),
        "bytes": stat.mean(r.get("result_bytes", 0) for r in rows),
        "calls": stat.mean(r["n_tool_calls"] for r in rows),
        "tok_in": stat.mean(r.get("input_tokens", 0) + r.get("cache_read_input_tokens", 0)
                            + r.get("cache_creation_input_tokens", 0) for r in rows),
        "cache_creation": stat.mean(r.get("cache_creation_input_tokens", 0) for r in rows),
        "cost": stat.mean(r.get("cost_usd") or 0 for r in rows),
        # The first pass quoted MEDIAN cost/run, so both are carried here:
        # the two disagree enough on these sweeps to change the ordering.
        "cost_med": stat.median([r.get("cost_usd") or 0 for r in rows]),
        "cost_total": sum(r.get("cost_usd") or 0 for r in rows),
        "ms": stat.median([r.get("duration_ms") or r.get("wall_ms", 0) for r in rows]),
        "errors": sum(r.get("tool_errors", 0) for r in rows),
    }


def pct(c: dict) -> str:
    """`mean% (min-max)` -- the only accuracy format used in this report."""
    if not c:
        return "-"
    if c["acc_min"] == c["acc_max"]:
        return f"{c['acc_mean']*100:.0f}%"
    return f"{c['acc_mean']*100:.0f}% ({c['acc_min']*100:.0f}-{c['acc_max']*100:.0f})"


def md(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


# ----------------------------------------------------------------- tables --
def headline(recs: list[dict], model: str | None = None) -> str:
    rows = []
    for shape, label in SHAPES:
        for c in CONDITIONS:
            k = cell(sel(recs, shape=shape, condition=c, model=model))
            if not k:
                continue
            rows.append([label, f"`{c}`", k["n"], k["seeds"], pct(k),
                         f"{k['bytes']:,.0f}", f"{k['calls']:.1f}",
                         f"{k['tok_in']:,.0f}", f"{k['cache_creation']:,.0f}",
                         f"${k['cost']:.4f}", f"${k['cost_med']:.4f}",
                         f"{k['ms']/1000:.1f}", k["leak"]])
    return md(["corpus", "condition", "runs", "seeds", "accuracy",
               "result bytes/run", "tool calls", "input tok/run",
               "cache-creation tok/run", "mean cost/run", "median cost/run",
               "latency s", "leaks"], rows)


def side_by_side(recs: list[dict], model: str | None = None) -> str:
    """corpus-a against corpus-b, per condition, per stratum."""
    rows = []
    for s in STRATA:
        for c in CONDITIONS:
            a = cell(sel(recs, shape="atomic", condition=c, stratum=s, model=model))
            b = cell(sel(recs, shape="subject", condition=c, stratum=s, model=model))
            if not a and not b:
                continue
            delta = ("-" if not (a and b)
                     else f"{(b['acc_mean']-a['acc_mean'])*100:+.0f} pp")
            rows.append([s, f"`{c}`", pct(a), pct(b), delta])
    return md(["stratum", "condition", "corpus-a", "corpus-b", "b - a"], rows)


def projection(recs: list[dict]) -> str:
    """The projection test: does SQL keep its context advantage?"""
    rows = []
    for shape, label in SHAPES:
        for m in sorted({r["model"] for r in recs}):
            base = cell(sel(recs, shape=shape, condition="sql_narrow", model=m))
            doc = cell(sel(recs, shape=shape, condition="sql_document", model=m))
            vec = cell(sel(recs, shape=shape, condition="vector_only", model=m))
            if not (base and doc and vec):
                continue
            rows.append([
                label, m,
                pct(base), f"{base['bytes']:,.0f}",
                pct(doc), f"{doc['bytes']:,.0f}",
                pct(vec), f"{vec['bytes']:,.0f}",
                f"{vec['bytes']/max(1,base['bytes']):.1f}x",
                f"{vec['bytes']/max(1,doc['bytes']):.1f}x",
            ])
    return md(["corpus", "model",
               "narrow acc", "narrow bytes",
               "document acc", "document bytes",
               "vector acc", "vector bytes",
               "vector/narrow", "vector/document"], rows)


def by_mechanism(recs: list[dict], stratum: str, model: str | None = None) -> str:
    """Mechanism x condition, split by corpus.

    A mechanism name is NOT unique to a corpus -- `R-recency` and `R-content`
    exist in both -- so the shape has to be part of the key, not looked up
    from the first matching record.
    """
    rows = []
    for shape, label in SHAPES:
        mechs = sorted({r.get("mechanism") for r in recs
                        if r["stratum"] == stratum and r["shape"] == shape
                        and r.get("mechanism")})
        for mech in mechs:
            row = [f"`{mech}`", label]
            for c in CONDITIONS:
                row.append(pct(cell(sel(recs, shape=shape, condition=c,
                                        mechanism=mech, model=model))))
            rows.append(row)
    return md(["mechanism", "corpus"] + [f"`{c}`" for c in CONDITIONS], rows)


def variance(recs: list[dict]) -> str:
    """Every headline cell's per-seed accuracy, laid out rather than averaged."""
    rows = []
    seeds = sorted({r.get("seed", 1) for r in recs})
    for shape, label in SHAPES:
        for m in sorted({r["model"] for r in recs}):
            for c in CONDITIONS:
                rs = sel(recs, shape=shape, condition=c, model=m)
                if not rs:
                    continue
                per = []
                for sd in seeds:
                    ss = [r for r in rs if r.get("seed", 1) == sd]
                    per.append(f"{sum(1 for r in ss if r['verdict']=='correct')}/{len(ss)}"
                               if ss else "-")
                k = cell(rs)
                rows.append([label, m, f"`{c}`"] + per + [pct(k)])
    return md(["corpus", "model", "condition"] + [f"seed {s}" for s in seeds]
              + ["mean (range)"], rows)


def tool_preference(recs: list[dict]) -> str:
    rows = []
    for shape, label in SHAPES:
        for m in sorted({r["model"] for r in recs}):
            s = sel(recs, shape=shape, condition="both", model=m)
            if not s:
                continue
            first = defaultdict(int)
            both_used = 0
            for r in s:
                names = [c["name"].rsplit("__", 1)[-1] for c in r["tool_calls"]]
                if names:
                    first[names[0]] += 1
                if "query" in names and "search" in names:
                    both_used += 1
            n = len(s)
            rows.append([label, m, n,
                         f"{first['search']/n*100:.0f}%",
                         f"{first['query']/n*100:.0f}%",
                         f"{both_used/n*100:.0f}%"])
    return md(["corpus", "model", "runs", "opened with `search`",
               "opened with `query`", "used both"], rows)


def failures(recs: list[dict], limit: int = 30) -> str:
    bad = [r for r in recs if r["verdict"] in ("wrong", "leak", "partial")]
    bad.sort(key=lambda r: (r["verdict"] != "leak", r["shape"], r["stratum"], r["qid"]))
    counts = defaultdict(int)
    for r in bad:
        counts[(r["shape"], r["stratum"], r["qid"], r["condition"], r["model"],
                r["verdict"])] += 1
    rows = []
    for (shape, st, qid, c, m, v), n in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]:
        ex = next(r for r in bad if r["qid"] == qid and r["condition"] == c
                  and r["model"] == m and r["shape"] == shape and r["verdict"] == v)
        rows.append([SHAPE_LABEL[shape], qid, st, f"`{c}`", m, v, f"{n}/3",
                     (ex["gold"] or "")[:24],
                     (ex["answer"] or "")[:40].replace("|", "/")])
    return md(["corpus", "qid", "stratum", "condition", "model", "verdict",
               "seeds", "gold", "example answer"], rows)


def tool_errors(recs: list[dict]) -> str:
    """What the failed tool calls actually were, by corpus and condition."""
    kinds: dict[tuple, int] = defaultdict(int)
    calls: dict[tuple, int] = defaultdict(int)
    for r in recs:
        for t in r.get("tool_log", []):
            calls[(r["shape"], r["condition"])] += 1
            if t.get("ok"):
                continue
            e = (t.get("error") or "")[:52]
            kinds[(r["shape"], r["condition"], e)] += 1
    rows = []
    for (shape, c, e), n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        rows.append([SHAPE_LABEL[shape], f"`{c}`", n, calls[(shape, c)],
                     f"{n/max(1,calls[(shape,c)])*100:.1f}%", e])
    return md(["corpus", "condition", "errors", "calls", "rate", "message"], rows)


def totals(recs: list[dict]) -> dict:
    agent = sum(r.get("cost_usd") or 0 for r in recs)
    judge = sum(r.get("judge_cost_usd") or 0 for r in recs)
    return {
        "runs": len(recs),
        "by_shape": {SHAPE_LABEL[s]: sum(1 for r in recs if r["shape"] == s)
                     for s in {r["shape"] for r in recs}},
        "by_model": {m: sum(1 for r in recs if r["model"] == m)
                     for m in sorted({r["model"] for r in recs})},
        "seeds": sorted({r.get("seed", 1) for r in recs}),
        "tool_calls": sum(r["n_tool_calls"] for r in recs),
        "tool_errors": sum(r.get("tool_errors", 0) for r in recs),
        "judged_by_rule": sum(1 for r in recs if r.get("judged_by") == "rule"),
        "agent_cost_usd": round(agent, 4),
        "judge_cost_usd": round(judge, 4),
        "total_cost_usd": round(agent + judge, 4),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.report2")
    ap.add_argument("--judged", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = load(*a.judged)
    models = sorted({r["model"] for r in recs})

    parts = [f"<!-- generated from {' '.join(a.judged)} -->", ""]
    parts += ["### Headline, all models pooled", "", headline(recs), ""]
    for m in models:
        parts += [f"### Headline -- {m}", "", headline(recs, m), ""]
    parts += ["### The projection test", "", projection(recs), ""]
    parts += ["### corpus-a vs corpus-b, per stratum, per condition (pooled)",
              "", side_by_side(recs), ""]
    for m in models:
        parts += [f"### corpus-a vs corpus-b, per stratum -- {m}", "",
                  side_by_side(recs, m), ""]
    parts += ["### Temporal, by supersession mechanism", "",
              by_mechanism(recs, "temporal"), ""]
    parts += ["### Reconcile, by discriminator", "",
              by_mechanism(recs, "reconcile"), ""]
    for m in models:
        parts += [f"### Reconcile, by discriminator -- {m}", "",
                  by_mechanism(recs, "reconcile", m), ""]
    parts += ["### Variance: every cell, every seed", "", variance(recs), ""]
    parts += ["### Tool preference in `both`", "", tool_preference(recs), ""]
    parts += ["### Tool-call errors", "", tool_errors(recs), ""]
    parts += ["### Failures", "", failures(recs), ""]
    parts += ["### Totals", "", "```json", json.dumps(totals(recs), indent=2),
              "```", ""]
    text = "\n".join(parts)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
