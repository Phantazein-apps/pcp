"""Aggregate judged runs into the tables that go into REPORT.md."""
from __future__ import annotations

import argparse
import json
import statistics as stat
from collections import defaultdict
from pathlib import Path

from .model import STRATA

CONDITION_ORDER = ["sql_only", "vector_only", "both"]


def load(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {}
    v = [r["verdict"] for r in rows]
    tok_in = [r.get("input_tokens", 0) + r.get("cache_read_input_tokens", 0)
              + r.get("cache_creation_input_tokens", 0) for r in rows]
    return {
        "n": n,
        "correct": v.count("correct"),
        "partial": v.count("partial"),
        "wrong": v.count("wrong"),
        "leak": v.count("leak"),
        "acc": v.count("correct") / n,
        "calls": stat.mean(r["n_tool_calls"] for r in rows),
        "tok_in": stat.mean(tok_in),
        "tok_out": stat.mean(r.get("output_tokens", 0) for r in rows),
        "bytes": stat.mean(r.get("result_bytes", 0) for r in rows),
        "ms": stat.median([r.get("duration_ms") or r.get("wall_ms", 0) for r in rows]),
        "cost": sum(r.get("cost_usd") or 0 for r in rows),
        "errors": sum(r.get("tool_errors", 0) for r in rows),
    }


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def by_condition(recs: list[dict], model: str | None = None) -> str:
    rows = []
    for c in CONDITION_ORDER:
        sel = [r for r in recs if r["condition"] == c and (model is None or r["model"] == model)]
        if not sel:
            continue
        a = _agg(sel)
        rows.append([c, a["n"], f"{a['acc']*100:.0f}%", a["correct"], a["partial"],
                     a["wrong"], a["leak"], f"{a['calls']:.1f}",
                     f"{a['tok_in']:,.0f}", f"{a['tok_out']:,.0f}",
                     f"{a['ms']/1000:.1f}", f"${a['cost']:.2f}"])
    return md_table(["condition", "n", "accuracy", "correct", "partial", "wrong",
                     "leak", "mean tool calls", "mean input tok", "mean output tok",
                     "median latency s", "cost"], rows)


def by_stratum(recs: list[dict], model: str | None = None) -> str:
    rows = []
    for s in STRATA:
        row = [s]
        for c in CONDITION_ORDER:
            sel = [r for r in recs if r["condition"] == c and r["stratum"] == s
                   and (model is None or r["model"] == model)]
            if not sel:
                row.append("-")
                continue
            a = _agg(sel)
            cell = f"{a['acc']*100:.0f}% ({a['correct']}/{a['n']})"
            if a["leak"]:
                cell += f" **{a['leak']} leak**"
            row.append(cell)
        rows.append(row)
    return md_table(["stratum"] + CONDITION_ORDER, rows)


def temporal_by_mechanism(recs: list[dict], model: str | None = None) -> str:
    labels = {"T-a": "T-a  chase a supersedes edge",
              "T-b": "T-b  overlapping validity windows",
              "T-c": "T-c  opt-in override (historical)"}
    rows = []
    for m in ["T-a", "T-b", "T-c"]:
        row = [labels[m]]
        for c in CONDITION_ORDER:
            sel = [r for r in recs if r["condition"] == c and r.get("mechanism") == m
                   and (model is None or r["model"] == model)]
            a = _agg(sel)
            row.append(f"{a['acc']*100:.0f}% ({a['correct']}/{a['n']})" if a else "-")
        rows.append(row)
    return md_table(["temporal mechanism"] + CONDITION_ORDER, rows)


def tool_preference(recs: list[dict]) -> str:
    """The claim under test: with both tools, which does the agent reach for?"""
    sel = [r for r in recs if r["condition"] == "both"]
    first, used_q, used_s, used_both, none = defaultdict(int), 0, 0, 0, 0
    for r in sel:
        names = [c["name"].rsplit("__", 1)[-1] for c in r["tool_calls"]]
        if not names:
            none += 1
            continue
        first[names[0]] += 1
        q, s = "query" in names, "search" in names
        used_q += q and not s
        used_s += s and not q
        used_both += q and s
    n = len(sel)
    rows = [
        ["first call was `search`", first.get("search", 0), f"{first.get('search',0)/n*100:.0f}%"],
        ["first call was `query`", first.get("query", 0), f"{first.get('query',0)/n*100:.0f}%"],
        ["used only `search`", used_s, f"{used_s/n*100:.0f}%"],
        ["used only `query`", used_q, f"{used_q/n*100:.0f}%"],
        ["used both", used_both, f"{used_both/n*100:.0f}%"],
        ["made no tool call", none, f"{none/n*100:.0f}%"],
    ]
    return md_table(["behaviour in the `both` condition", "runs", "share"], rows)


def override_usage(recs: list[dict]) -> str:
    """Did the agent take the opt-in that T-c questions require?"""
    rows = []
    for c in CONDITION_ORDER:
        for m, label in [("T-c", "T-c questions"), (None, "all questions")]:
            sel = [r for r in recs if r["condition"] == c
                   and (m is None or r.get("mechanism") == m)]
            if not sel:
                continue
            took = 0
            for r in sel:
                used = False
                for tc in r["tool_calls"]:
                    inp = tc.get("input", {})
                    if inp.get("include_stale"):
                        used = True
                    sql = str(inp.get("sql", "")).lower()
                    if "memory_all" in sql or "relations_all" in sql:
                        used = True
                took += used
            rows.append([c, label, f"{took}/{len(sel)}", f"{took/len(sel)*100:.0f}%"])
    return md_table(["condition", "subset", "runs that used the override", "share"], rows)


def seed_variance(recs: list[dict]) -> str:
    """Run-to-run variance. Nothing in the sampling is seeded, so the two
    `seed` labels are independent repeats of the same 60 questions."""
    seeds = sorted({r.get("seed", 1) for r in recs})
    if len(seeds) < 2:
        return "_Only one repeat in this sweep; no variance estimate._"
    rows = []
    for m in sorted({r["model"] for r in recs}):
        for c in CONDITION_ORDER:
            per = {}
            for sd in seeds:
                sel = [r for r in recs if r["condition"] == c and r["model"] == m
                       and r.get("seed", 1) == sd]
                per[sd] = {r["qid"]: r["verdict"] == "correct" for r in sel}
            if not all(per.values()):
                continue
            counts = [sum(v.values()) for v in per.values()]
            qids = set(per[seeds[0]]) & set(per[seeds[1]])
            flips = sum(1 for q in qids if per[seeds[0]][q] != per[seeds[1]][q])
            rows.append([m, c, " / ".join(str(x) for x in counts),
                         f"{max(counts)-min(counts)}", f"{flips}/{len(qids)}"])
    return md_table(["model", "condition", "correct per repeat", "spread",
                     "questions that flipped"], rows)


def failures(recs: list[dict], limit: int = 12) -> str:
    bad = [r for r in recs if r["verdict"] in ("wrong", "leak")]
    bad.sort(key=lambda r: (r["verdict"] != "leak", r["stratum"], r["qid"]))
    rows = []
    for r in bad[:limit]:
        rows.append([r["qid"], r["stratum"], r["condition"], r["verdict"],
                     (r["gold"] or "")[:34], (r["answer"] or "")[:44].replace("|", "/")])
    return md_table(["qid", "stratum", "condition", "verdict", "gold", "answer given"], rows)


def totals(recs: list[dict]) -> dict:
    return {
        "runs": len(recs),
        "cost_usd": sum(r.get("cost_usd") or 0 for r in recs),
        "judge_cost_usd": sum(r.get("judge_cost_usd") or 0 for r in recs),
        "tool_calls": sum(r["n_tool_calls"] for r in recs),
        "tool_errors": sum(r.get("tool_errors", 0) for r in recs),
        "models": sorted({r["model"] for r in recs}),
        "conditions": sorted({r["condition"] for r in recs}),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.report")
    ap.add_argument("--judged", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = load(a.judged)
    models = sorted({r["model"] for r in recs})

    parts = [f"<!-- generated from {a.judged} -->", ""]
    parts += ["### Overall, by condition", "", by_condition(recs), ""]
    parts += ["### Accuracy by stratum", "", by_stratum(recs), ""]
    parts += ["### Temporal, by mechanism", "", temporal_by_mechanism(recs), ""]
    parts += ["### Tool preference", "", tool_preference(recs), ""]
    parts += ["### Opt-in override usage", "", override_usage(recs), ""]
    parts += ["### Run-to-run variance", "", seed_variance(recs), ""]
    if len(models) > 1:
        for m in models:
            parts += [f"### By condition — {m}", "", by_condition(recs, m), ""]
            parts += [f"### By stratum — {m}", "", by_stratum(recs, m), ""]
            parts += [f"### Temporal by mechanism — {m}", "",
                      temporal_by_mechanism(recs, m), ""]
    parts += ["### Failures", "", failures(recs, 20), ""]
    parts += ["### Totals", "", "```json",
              json.dumps(totals(recs), indent=2), "```", ""]
    text = "\n".join(parts)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
