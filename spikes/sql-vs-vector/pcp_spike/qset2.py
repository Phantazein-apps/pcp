"""The second-pass question set: 30 questions across SEVEN strata.

Built once per corpus shape. Gold answers come from `persona.py` in both
cases, so corpus-a and corpus-b are asked THE SAME questions with THE SAME
expected answers wherever the fact survives the re-shaping -- which is what
makes the side-by-side in REPORT.md §8.2 a comparison rather than two
unrelated benchmarks.

What changes between shapes:

  * `targets`   -- the page paths differ, because corpus-b groups facts into
                   subject files.
  * `mechanism` -- corpus-a resolves supersession with a `supersedes` edge
                   (T-a); corpus-b has no edges, so the same four questions
                   are resolved by prose: tense-plus-date inside one line
                   (TB-a) or a cue on a different line of the same file
                   (TB-b).

Three first-pass mechanisms have NO corpus-b counterpart and are therefore
out of the second-pass run set entirely, not silently reweighted:
T-b (overlapping validity windows) and T-c (the opt-in override) both need
per-fact validity and lifecycle, and corpus-b has neither. The first-pass
result for them stands on its own; §8.5 rules on it.

The paraphrase stratum is the other deliberate change. In the first pass the
question shared ZERO content tokens with its target page, which is the
maximally embedding-friendly extreme. Here the overlap is PARTIAL and the
distribution actually generated is measured and reported (§8.4), not asserted.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics as stat
from pathlib import Path

from . import persona as P
from .model import STRATA, content_tokens
from .qset import Q
from .reconcile import RECONCILE, QUESTIONED, QUESTIONS as RQ

PEOPLE = {p[0]: p for p in P.PEOPLE}
PROJ = {p[0]: p for p in P.PROJECTS}
VEH = {v[0]: v for v in P.VEHICLES}

# Target counts per stratum. 21 questions x 4 conditions x 2 corpora x
# 2 models x 3 seeds = 1,008 runs, which is what the $25 budget buys at the
# per-run cost measured in the pilots (NOTES.md §4.2).
#
# The allocation is deliberately uneven. exact_lookup, multi_hop, negative and
# scope_restricted all ceilinged at 100% in the first pass, so they get the
# minimum needed to show whether the ceiling survives corpus-b -- two each.
# The budget goes to the three strata that can actually separate anything:
# paraphrase (the only first-pass stratum that did), temporal (re-encoded from
# an edge to prose), and reconcile (new, and the hardest).
PLAN = {
    "exact_lookup": 2, "paraphrase": 4, "multi_hop": 2, "temporal": 4,
    "negative": 2, "scope_restricted": 2, "reconcile": 5,
}

# ---------------------------------------------------------------- targets --
# path of the page carrying each answer, per shape
TARGETS = {
    "atomic": {
        "role":      ["work/role-principal-data-engineer", "work/role-senior-data-engineer"],
        "reporting": ["work/reporting-line-hallgren", "work/reporting-line-adeyemi"],
        "steering":  ["projects/tidewater/steering-chair-nordgren",
                      "projects/tidewater/steering-chair-tuominen"],
        "laptop":    ["work/laptop-framework-16", "work/laptop-macbook-pro"],
    },
    "subject": {
        "role":      ["work/role-at-nordvik"],
        "reporting": ["work/reporting-line"],
        "steering":  ["projects/tidewater-governance"],
        "laptop":    ["work/equipment"],
    },
}

# corpus-a resolves all four with an edge; corpus-b with prose, of two kinds.
MECHANISM = {
    "atomic":  {"role": "T-a", "reporting": "T-a", "steering": "T-a", "laptop": "T-a"},
    "subject": {"role": "TB-a", "reporting": "TB-a",
                "steering": "TB-b", "laptop": "TB-b"},
}

TEMPORAL_GOLD = {
    "role":      ("What is Mara's job title at Nordvik Analytics?", "Principal Data Engineer", []),
    "reporting": ("Who does Mara report to at work?", "Petra Hallgren", []),
    "steering":  ("Who chairs the Tidewater steering group?", "Elin Nordgren", []),
    "laptop":    ("What laptop does Mara use for work?", "Framework 16", ["Framework"]),
}


def _para_path(shape: str, spec: dict) -> str:
    return spec["path"] if shape == "atomic" else f"{spec['domain']}/subject-{spec['key']}"


# ------------------------------------------------------- paraphrase, partial --
# One rewritten question per first-pass paraphrase target. The first pass
# engineered ZERO content-token overlap; these are written to overlap
# PARTIALLY, across a spread of bands. The measured containment is computed
# from the built corpus in `overlap_report()` -- these are the inputs to that
# measurement, not a claim about it.
PARTIAL = {
    "kora":      "Which instrument did Kwame teach Mara to play?",
    "recycling": "Which day is the rubbish taken from the courtyard?",
    "cloud":     "Which cloud provider does Nordvik use?",
    "climbing":  "What does Nell do on Saturday mornings?",
    "tallyho":   "What do colleagues call the internal utility Mara looks after?",
    "dinghy":    "What is the wooden boat by the boathouse called?",
    "seat":      "Which side of the plane does Mara ask for a place on?",
    "assembly":  "Where does the household meet if the building is evacuated?",
    "bakery":    "Which bakery does Mara get her loaves from?",
    "tyres":     "When does Mara put the winter rubber on the estate?",
}
# The four that go into the run set, chosen to SPAN the measured containment
# band rather than cluster at one end: ~0.20, ~0.25, ~0.50, ~0.67.
PARA_RUN = ["kora", "cloud", "bakery", "tallyho"]


def build(shape: str, corpus_root: Path) -> list[dict]:
    manifest = json.loads((corpus_root / "manifest.json").read_text(encoding="utf-8"))
    para = {s["key"]: s for s in manifest["designed"]["paraphrase"]}
    rec = {s["key"]: s for s in RECONCILE}
    tgt, mech = TARGETS[shape], MECHANISM[shape]

    qs: list[dict] = []

    # -- exact lookup: one hop, the answer is written on one page ----------
    v = VEH["volvo_v60"]
    qs += [
        Q("EX01", "exact_lookup", "What is the registration number of Mara's Volvo V60?",
          v[5], targets=["vehicles/volvo-v60"]),
        Q("EX02", "exact_lookup", "Which client funds the Ledgerline project?",
          PROJ["ledgerline"][2], targets=["projects/ledgerline"]),
    ]

    # -- paraphrase: partial lexical overlap with the target page ----------
    for i, key in enumerate(PARA_RUN, start=1):
        sp = para[key]
        qs.append(Q(f"PA{i:02d}", "paraphrase", PARTIAL[key], sp["gold"],
                    aliases=sp["aliases"], targets=[_para_path(shape, sp)],
                    note=f"paraphrase target {key}"))

    # -- multi-hop: two or more joins ------------------------------------
    qs += [
        Q("MH01", "multi_hop",
          "Which city is the design lead of the Bluefin project based in?",
          PEOPLE[PROJ["bluefin"][4]][4],
          targets=["projects/bluefin", "people/frida-lund"]),
        Q("MH05", "multi_hop",
          "Who is the design lead on the most expensive project that is currently active?",
          PEOPLE[PROJ["oxbow"][4]][1], targets=["projects/oxbow"]),
    ]

    # -- temporal: the SAME four questions of both shapes ------------------
    for i, key in enumerate(["role", "reporting", "steering", "laptop"], start=1):
        question, gold, aliases = TEMPORAL_GOLD[key]
        qs.append(Q(f"TP{i:02d}", "temporal", question, gold, aliases=aliases,
                    mechanism=mech[key], targets=tgt[key],
                    note=f"supersession case {key}"))

    # -- negative: no answer exists anywhere -------------------------------
    for qid, q, toks in [
        ("NG01", "What is the name of Mara's dog?", ["dog"]),
        ("NG05", "What model of espresso machine does Mara own?", ["espresso machine"]),
    ]:
        qs.append(Q(qid, "negative", q, "not found", expect="not_found", leak_tokens=toks))

    # -- scope-restricted: asked under a scope that must not see the answer -
    for qid, q, gold, target, toks in [
        ("SR01", "What condition is Mara being treated for by Dr Selma Ferreira?",
         "psoriatic arthritis", "health/psoriatic-arthritis", ["psoriatic"]),
        ("SR05", "Which institution holds Mara's emergency savings buffer?",
         "Lansforsakringar", "finances/lansforsakringar-savings", ["Lansforsakringar"]),
    ]:
        qs.append(Q(qid, "scope_restricted", q, "not found", expect="not_found",
                    scope="default", targets=[target], leak_tokens=toks, withheld=gold))

    # -- reconcile: two pages contradict, nothing says which is current ----
    for i, key in enumerate(QUESTIONED, start=1):
        sp = rec[key]
        qs.append(Q(f"RC{i:02d}", "reconcile", RQ[key], sp["gold"],
                    aliases=sp["aliases"],
                    mechanism=f"R-{sp['discriminator']}",
                    targets=[sp["current"]["path"], sp["stale"]["path"]],
                    note=f"stale twin: {sp['stale_gold']}",
                    # the answer a reader gets by trusting the wrong page
                    withheld=None))
        qs[-1]["distractor"] = sp["stale_gold"]

    for q in qs:
        q.setdefault("distractor", None)
        q["shape"] = shape
    return qs


# ------------------------------------------------------------- validation --
def _paths(data_root: Path, scope: str, table: str) -> set[str]:
    con = sqlite3.connect(f"file:{data_root / f'scope_{scope}.sqlite'}?mode=ro", uri=True)
    out = {r[0] for r in con.execute(f"SELECT path FROM {table}")}
    con.close()
    return out


def _scope_text(data_root: Path, scope: str) -> tuple[str, str]:
    con = sqlite3.connect(f"file:{data_root / f'scope_{scope}.sqlite'}?mode=ro", uri=True)
    dflt = " \n".join(f"{t} {b}" for t, b in con.execute("SELECT title, body FROM memory"))
    allt = " \n".join(f"{t} {b}" for t, b in con.execute("SELECT title, body FROM memory_all"))
    prof = " \n".join(f"{k} {v}" for k, v in con.execute("SELECT key, value FROM profile"))
    con.close()
    return dflt + " " + prof, allt + " " + prof


def validate(qs: list[dict], manifest: dict, data_root: Path) -> list[str]:
    errs: list[str] = []
    shape = manifest.get("shape", "atomic")
    for s, want in PLAN.items():
        got = sum(1 for q in qs if q["stratum"] == s)
        if got != want:
            errs.append(f"stratum {s}: {got} questions, planned {want}")
    if len({q["id"] for q in qs}) != len(qs):
        errs.append("duplicate question ids")

    cache: dict[str, tuple[str, str]] = {}

    def text(scope):
        if scope not in cache:
            cache[scope] = _scope_text(data_root, scope)
        return cache[scope]

    def hit(hay: str, q: dict) -> bool:
        return any(c and c.lower() in hay.lower() for c in [q["gold"]] + q["aliases"])

    for q in qs:
        dflt, allt = text(q["scope"])
        st = q["stratum"]

        if st in ("exact_lookup", "paraphrase", "multi_hop", "temporal", "reconcile"):
            if not hit(dflt, q):
                errs.append(f"{q['id']}: gold {q['gold']!r} is not reachable from the "
                            f"default view of scope {q['scope']}")
            for t in q["targets"]:
                if t not in _paths(data_root, q["scope"], "memory"):
                    errs.append(f"{q['id']}: target {t} is not in the default view")

        if st == "temporal":
            # Both readings must survive the default filter, in BOTH shapes.
            # Otherwise the storage filter, not the encoding under test, is
            # doing the discriminating.
            if shape == "atomic":
                sdb = data_root / f"scope_{q['scope']}.sqlite"
                con = sqlite3.connect(f"file:{sdb}?mode=ro", uri=True)
                n = con.execute("SELECT count(*) FROM relations WHERE rel='supersedes' "
                                "AND target_page=?", (q["targets"][1],)).fetchone()[0]
                con.close()
                if n == 0:
                    errs.append(f"{q['id']} (T-a): no supersedes edge targets "
                                f"{q['targets'][1]}")
            else:
                if len(q["targets"]) != 1:
                    errs.append(f"{q['id']} ({q['mechanism']}): corpus-b must carry both "
                                f"readings in ONE file")

        elif st == "reconcile":
            # Neither page may be marked in any way, in either shape.
            sdb = data_root / f"scope_{q['scope']}.sqlite"
            con = sqlite3.connect(f"file:{sdb}?mode=ro", uri=True)
            for t in q["targets"]:
                n = con.execute("SELECT count(*) FROM relations_all WHERE "
                                "source_page=? OR target_page=?", (t, t)).fetchone()[0]
                if n:
                    errs.append(f"{q['id']}: {t} carries a relations edge -- the "
                                f"reconcile stratum must have no marker")
            rows = list(con.execute(
                "SELECT path, lifecycle, confidence FROM memory_all WHERE path IN (?,?)",
                tuple(q["targets"])))
            con.close()
            if len(rows) != 2:
                errs.append(f"{q['id']}: expected both pages visible, saw {len(rows)}")
            elif len({r[1] for r in rows}) != 1 or len({r[2] for r in rows}) != 1:
                errs.append(f"{q['id']}: the two pages differ in lifecycle or "
                            f"confidence -- that is a marker")
            if q["distractor"] and q["distractor"].lower() not in dflt.lower():
                errs.append(f"{q['id']}: the stale twin's answer {q['distractor']!r} is "
                            f"not reachable, so nothing has to be reconciled")

        elif st == "negative":
            _, full_all = text("full")
            for tok in q["leak_tokens"]:
                if tok.lower() in full_all.lower():
                    errs.append(f"{q['id']} (negative): {tok!r} DOES appear in the corpus")

        elif st == "scope_restricted":
            seen_all = _paths(data_root, q["scope"], "memory_all")
            for t in q["targets"]:
                if t in seen_all:
                    errs.append(f"{q['id']}: target {t} IS visible under scope "
                                f"{q['scope']} -- not actually restricted")
            for tok in q["leak_tokens"]:
                if tok.lower() in allt.lower():
                    errs.append(f"{q['id']}: leak token {tok!r} is reachable under "
                                f"scope {q['scope']}")
    return errs


# ---------------------------------------------------- overlap measurement --
def overlap_report(shape: str, corpus_root: Path) -> dict:
    """Measured question/page token overlap -- the thing §5 item 4 asked for.

    Two numbers per question, both over lowercased, stopworded, lightly
    stemmed content tokens:
      containment  |Q & P| / |Q|   -- how much of the question is IN the page
      jaccard      |Q & P| / |Q | P|
    `containment` is the one that matters for retrieval: it is the share of
    the question's content words a `LIKE` or a BM25 hit could match on.
    """
    manifest = json.loads((corpus_root / "manifest.json").read_text(encoding="utf-8"))
    pages = {p["path"]: p for p in manifest["pages"]}
    para = {s["key"]: s for s in manifest["designed"]["paraphrase"]}

    def measure(question: str, path: str) -> dict:
        pg = pages[path]
        qt = content_tokens(question)
        pt = content_tokens(pg["body"]) | content_tokens(pg["title"])
        inter = qt & pt
        return {"containment": round(len(inter) / max(1, len(qt)), 3),
                "jaccard": round(len(inter) / max(1, len(qt | pt)), 3),
                "q_tokens": len(qt), "shared": sorted(inter)}

    rows = []
    for key, question in PARTIAL.items():
        sp = para[key]
        path = _para_path(shape, sp)
        first = {"key": key, "in_run_set": key in PARA_RUN,
                 "question": question, "path": path,
                 "first_pass_question": sp["question"]}
        first.update(measure(question, path))
        first["first_pass_containment"] = measure(sp["question"], path)["containment"]
        rows.append(first)

    # And the whole run set, so the paraphrase band can be read against the
    # rest of the benchmark rather than in isolation.
    qs = build(shape, corpus_root)
    allrows = []
    for q in qs:
        if not q["targets"] or q["expect"] != "answer":
            continue
        t = q["targets"][0]
        if t not in pages:
            continue
        m = measure(q["question"], t)
        allrows.append({"id": q["id"], "stratum": q["stratum"], **m})

    def dist(vals):
        vals = sorted(vals)
        if not vals:
            return {}
        return {"n": len(vals), "min": vals[0], "max": vals[-1],
                "mean": round(stat.mean(vals), 3),
                "median": round(stat.median(vals), 3),
                "bands": {b: sum(1 for v in vals if lo <= v < hi)
                          for b, (lo, hi) in [("0.0-0.2", (0.0, 0.2)),
                                              ("0.2-0.4", (0.2, 0.4)),
                                              ("0.4-0.6", (0.4, 0.6)),
                                              ("0.6-0.8", (0.6, 0.8)),
                                              ("0.8-1.0", (0.8, 1.01))]}}

    return {
        "shape": shape,
        "paraphrase": rows,
        "paraphrase_distribution": dist([r["containment"] for r in rows]),
        "paraphrase_run_set_distribution": dist(
            [r["containment"] for r in rows if r["in_run_set"]]),
        "first_pass_paraphrase_distribution": dist(
            [r["first_pass_containment"] for r in rows]),
        "run_set": allrows,
        "run_set_distribution": dist([r["containment"] for r in allrows]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.qset2")
    ap.add_argument("--shape", choices=["atomic", "subject"], required=True)
    ap.add_argument("--corpus-root", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--overlap-out", default=None)
    a = ap.parse_args(argv)

    corpus_root, data_root = Path(a.corpus_root), Path(a.data_root)
    manifest = json.loads((corpus_root / "manifest.json").read_text(encoding="utf-8"))
    qs = build(a.shape, corpus_root)
    errs = validate(qs, manifest, data_root)
    if errs:
        raise SystemExit("question-set validation failed:\n  " + "\n  ".join(errs))

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(qs, indent=2, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(q["stratum"] for q in qs)
    print(f"questions ({a.shape}): {len(qs)} -> {a.out}")
    for s in STRATA:
        extra = ""
        if s in ("temporal", "reconcile"):
            m = Counter(q["mechanism"] for q in qs if q["stratum"] == s)
            extra = "  (" + ", ".join(f"{k}:{v}" for k, v in sorted(m.items())) + ")"
        print(f"  {s:18s} {c[s]}{extra}")

    if a.overlap_out:
        rep = overlap_report(a.shape, corpus_root)
        Path(a.overlap_out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        d = rep["paraphrase_distribution"]
        f = rep["first_pass_paraphrase_distribution"]
        print(f"  paraphrase containment: mean {d['mean']} "
              f"(range {d['min']}-{d['max']}); first pass was mean {f['mean']}")
        print(f"  -> {a.overlap_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
