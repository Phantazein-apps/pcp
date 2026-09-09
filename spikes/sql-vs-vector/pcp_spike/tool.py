"""Harness CLI -- the ONLY data access the agent gets.

    python tool.py query  --scope S "SELECT ..."
    python tool.py search --scope S -k 5 "free text"

Guarantees (brief §Build 4):
  * read-only: the scope database is opened `mode=ro` with `query_only`, and
    only a single SELECT/WITH statement is accepted
  * 2 s statement timeout, enforced by a progress handler
  * 200-row cap, 20 KB result cap
  * CSV output for `query`
  * every call, its result size, and any error are logged as JSONL
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROW_CAP = 200
BYTE_CAP = 20 * 1024
TIMEOUT_S = 2.0

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORPUS = ROOT / "corpus"

_FORBIDDEN = re.compile(
    r"\b(attach|detach|pragma|insert|update|delete|drop|create|alter|replace|"
    r"vacuum|reindex|begin|commit|rollback|load_extension)\b", re.I)


class ToolError(Exception):
    pass


# ------------------------------------------------------------------ logging --
def log_call(logfile: Path | None, record: dict) -> None:
    if not logfile:
        return
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _cap(text: str) -> tuple[str, bool]:
    raw = text.encode("utf-8")
    if len(raw) <= BYTE_CAP:
        return text, False
    return raw[:BYTE_CAP].decode("utf-8", "ignore") + "\n-- [truncated at 20 KB] --", True


# -------------------------------------------------------------------- query --
def run_query(scope: str, sql: str) -> str:
    db = DATA / f"scope_{scope}.sqlite"
    if not db.exists():
        raise ToolError(f"unknown scope {scope!r}")

    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ToolError("only one statement per call")
    if not re.match(r"^\s*(select|with)\b", stripped, re.I):
        raise ToolError("only SELECT (or WITH ... SELECT) statements are permitted")
    if _FORBIDDEN.search(stripped):
        raise ToolError("statement contains a forbidden keyword; this tool is read-only")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    deadline = time.monotonic() + TIMEOUT_S
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 2000)
    try:
        cur = con.execute(stripped)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(ROW_CAP + 1)
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "interrupted" in msg.lower():
            raise ToolError(f"query exceeded the {TIMEOUT_S:g} s statement timeout") from None
        raise ToolError(f"SQL error: {msg}") from None
    except sqlite3.Error as e:
        raise ToolError(f"SQL error: {e}") from None
    finally:
        con.close()

    truncated_rows = len(rows) > ROW_CAP
    rows = rows[:ROW_CAP]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if cols:
        w.writerow(cols)
    for r in rows:
        w.writerow(["" if v is None else str(v) for v in r])
    out = buf.getvalue()
    if truncated_rows:
        out += f"-- [row cap: only the first {ROW_CAP} rows are shown] --\n"
    if not rows:
        out += "-- [0 rows] --\n"
    return out


# ------------------------------------------------------------------- search --
def run_search(scope: str, text: str, k: int, backend: str,
               include_stale: bool, hide_relations: bool = False) -> str:
    from .retrieval import Index
    idx = Index(DATA, CORPUS, backend=backend)
    hits = idx.search(scope, text, k=k, include_stale=include_stale,
                      hide_relations=hide_relations)
    if not hits:
        return "-- [no matches] --\n"
    parts = []
    for i, h in enumerate(hits, 1):
        fm = h["frontmatter"]
        fm_lines = [f"  {kk}: {vv}" for kk, vv in fm.items()
                    if vv not in (None, [], "")]
        parts.append(
            f"### {i}. {h['path']}  (score {h['score']})\n"
            + "\n".join(fm_lines)
            + f"\n\n{h['body']}\n"
        )
    return "\n".join(parts)


# --------------------------------------------------------------------- main --
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="tool.py", description="PCP retrieval harness")
    ap.add_argument("--log", default=os.environ.get("PCP_TOOL_LOG"),
                    help="append a JSONL record per call to this file")
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="read-only SQL over the scope's curated views")
    q.add_argument("--scope", required=True)
    q.add_argument("sql")

    s = sub.add_parser("search", help="semantic (or lexical) search over the scope's pages")
    s.add_argument("--scope", required=True)
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--backend", choices=["vector", "lexical"], default="vector")
    s.add_argument("--hide-relations", action="store_true",
                   help="omit the `relations` edges from returned frontmatter "
                        "(ablation: forces supersession to be resolved by join)")
    s.add_argument("--include-stale", action="store_true",
                   help="also search pages the default policy hides "
                        "(stale, archived, expired)")
    s.add_argument("text")

    sub.add_parser("schema", help="print the schema documentation").add_argument(
        "--scope", default="default")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    logfile = Path(a.log) if a.log else None
    t0 = time.monotonic()
    rec: dict = {"ts": time.time(), "cmd": a.cmd, "scope": getattr(a, "scope", None)}
    try:
        if a.cmd == "query":
            rec["sql"] = a.sql
            out = run_query(a.scope, a.sql)
        elif a.cmd == "search":
            rec.update(text=a.text, k=a.k, backend=a.backend,
                       include_stale=a.include_stale)
            out = run_search(a.scope, a.text, a.k, a.backend, a.include_stale,
                             getattr(a, 'hide_relations', False))
        else:
            from .store import SCHEMA_DOC
            from .model import TODAY
            out = SCHEMA_DOC.format(today=TODAY)
        out, capped = _cap(out)
        rec.update(ok=True, bytes=len(out.encode()), truncated=capped,
                   ms=round((time.monotonic() - t0) * 1000, 1))
        log_call(logfile, rec)
        sys.stdout.write(out)
        return 0
    except ToolError as e:
        rec.update(ok=False, error=str(e), bytes=0,
                   ms=round((time.monotonic() - t0) * 1000, 1))
        log_call(logfile, rec)
        sys.stderr.write(f"ERROR: {e}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
