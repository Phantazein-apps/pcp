"""The 60-question evaluation set, derived from the corpus manifest.

Six strata, 10 questions each (the brief requires >= 8). Gold answers are
computed from the persona tables wherever possible so they cannot drift from
the corpus, and every stratum carries a build-time assertion that the
question is actually the kind of question it claims to be.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import persona as P
from .model import STRATA

PEOPLE = {p[0]: p for p in P.PEOPLE}
PROJ = {p[0]: p for p in P.PROJECTS}
VEH = {v[0]: v for v in P.VEHICLES}


def Q(qid, stratum, question, gold, *, scope="default", expect="answer",
      aliases=(), mechanism=None, targets=(), leak_tokens=(), note=None) -> dict:
    return {
        "id": qid, "stratum": stratum, "scope": scope, "question": question,
        "gold": gold, "aliases": list(aliases), "expect": expect,
        "mechanism": mechanism, "targets": list(targets),
        "leak_tokens": list(leak_tokens), "note": note,
    }


# ------------------------------------------------------------ exact lookup --
def exact_lookup() -> list[dict]:
    v = VEH["volvo_v60"]; k = VEH["kia_soul"]
    return [
        Q("EX01", "exact_lookup", "What is the registration number of Mara's Volvo V60?",
          v[5], targets=["vehicles/volvo-v60"]),
        Q("EX02", "exact_lookup", "Which client funds the Ledgerline project?",
          PROJ["ledgerline"][2], targets=["projects/ledgerline"]),
        Q("EX03", "exact_lookup", "What timezone is Mara in?",
          P.PERSONA["timezone"], aliases=["CET", "CEST", "Central European Time"],
          targets=["profile.core"]),
        Q("EX04", "exact_lookup", "What colour is the Kia Soul EV?",
          k[4], targets=["vehicles/kia-soul-ev"]),
        Q("EX05", "exact_lookup", "Who is the design lead on the Windrow project?",
          PEOPLE[PROJ["windrow"][4]][1], targets=["projects/windrow"]),
        Q("EX06", "exact_lookup", "Which repository does the Sentinel project live in?",
          PROJ["sentinel"][9], targets=["projects/sentinel"]),
        Q("EX07", "exact_lookup", "What time does Mara's team standup start?",
          "09:45 CET", aliases=["09:45", "9:45"], targets=["work/standup-time"]),
        Q("EX08", "exact_lookup", "How many days of annual leave does Mara get?",
          "thirty", aliases=["30", "30 days", "thirty days"], targets=["work/holiday-allowance"]),
        Q("EX09", "exact_lookup", "What is the budget of the Oxbow project?",
          f"{PROJ['oxbow'][8]} kSEK", aliases=["5200", "5,200"], targets=["projects/oxbow"]),
        Q("EX10", "exact_lookup", "Which city does Rafael Duarte work from?",
          PEOPLE["rafael"][4], targets=["people/rafael-duarte"]),
    ]


# --------------------------------------------------------------- multi-hop --
def multi_hop() -> list[dict]:
    return [
        Q("MH01", "multi_hop",
          "Which city is the design lead of the Bluefin project based in?",
          PEOPLE[PROJ["bluefin"][4]][4],
          targets=["projects/bluefin", f"people/frida-lund"],
          note="project -> design lead -> person.city"),
        Q("MH02", "multi_hop",
          "Who is the engineering lead on the Tallhojd Energi project that is built on DuckDB?",
          PEOPLE[PROJ["windrow"][3]][1], targets=["projects/windrow"],
          note="client+stack -> project -> lead"),
        Q("MH03", "multi_hop",
          "Which city does the engineering lead of Ledgerline work from?",
          PEOPLE[PROJ["ledgerline"][3]][4],
          targets=["projects/ledgerline", "people/ingrid-saarinen"]),
        Q("MH04", "multi_hop",
          "What technology stack does the project led by Aisha Rahman use?",
          PROJ["sentinel"][10], targets=["projects/sentinel"]),
        Q("MH05", "multi_hop",
          "Who is the design lead on the most expensive project that is currently active?",
          PEOPLE[PROJ["oxbow"][4]][1], targets=["projects/oxbow"],
          note="max(budget) over active projects -> design lead"),
        Q("MH06", "multi_hop",
          "Which organisation is the client for the project that Bengt Ahlgren leads?",
          PROJ["moraine"][2], aliases=["internal", "Nordvik"],
          targets=["projects/moraine"]),
        Q("MH07", "multi_hop",
          "What is the repository name of the Tallhojd Energi project whose design lead is based in Oslo?",
          PROJ["windrow"][9], targets=["projects/windrow", "people/frida-lund"],
          note="two-sided join: client AND design-lead city"),
        Q("MH08", "multi_hop",
          "Mara is travelling to Krakow later this month for a design week. What is the role of the colleague going with her?",
          PEOPLE["hanna"][5], targets=["travel/2026-09-krakow", "people/hanna-brozek"]),
        Q("MH09", "multi_hop",
          "Which city is the data lead at the client organisation funding Thornwood based in?",
          PEOPLE["elin"][4], targets=["projects/thornwood", "people/elin-nordgren"]),
        Q("MH10", "multi_hop",
          "What is the role of the person Mara is travelling to Tallinn with in October 2026?",
          PEOPLE["dmitri"][5], targets=["travel/2026-10-tallinn", "people/dmitri-sokolov"]),
    ]


# ---------------------------------------------------------------- temporal --
def temporal(manifest: dict) -> list[dict]:
    d = manifest["designed"]
    sup = {s["key"]: s for s in d["supersession"]}
    win = {w["key"]: w for w in d["windows"]}
    hist = {h["key"]: h for h in d["historical"]}
    qs = [
        # T-a: both pages active and default-visible; only the edge resolves.
        Q("TP01", "temporal", "What is Mara's job title at Nordvik Analytics?",
          sup["role"]["gold"], mechanism="T-a",
          targets=[sup["role"]["new_path"], sup["role"]["old_path"]]),
        Q("TP02", "temporal", "Who does Mara report to at work?",
          sup["reporting"]["gold"], mechanism="T-a",
          targets=[sup["reporting"]["new_path"], sup["reporting"]["old_path"]]),
        Q("TP03", "temporal", "Who chairs the Tidewater steering group?",
          sup["steering"]["gold"], mechanism="T-a",
          targets=[sup["steering"]["new_path"], sup["steering"]["old_path"]]),
        Q("TP04", "temporal", "What laptop does Mara use for work?",
          sup["laptop"]["gold"], mechanism="T-a",
          targets=[sup["laptop"]["new_path"], sup["laptop"]["old_path"]]),
        # T-b: overlapping windows, both current; interval containment decides.
        Q("TP05", "temporal",
          "Which parking space was Mara entitled to use on 15 January 2026?",
          win["parking"]["gold"], mechanism="T-b",
          aliases=["courtyard", "space 14"],
          targets=[o["path"] for o in win["parking"]["options"]]),
        Q("TP06", "temporal",
          "Which mobile operator was Mara's number on in March 2026?",
          win["mobile"]["gold"], mechanism="T-b",
          targets=[o["path"] for o in win["mobile"]["options"]]),
        Q("TP07", "temporal",
          "Which swimming pool did Mara hold a membership at in February 2026?",
          win["pool"]["gold"], mechanism="T-b",
          targets=[o["path"] for o in win["pool"]["options"]]),
        # T-c: historical facts, only in the opt-in override.
        Q("TP08", "temporal", "What car did Mara drive before the Volvo V60?",
          "Saab 9-5", mechanism="T-c", aliases=["Saab"],
          targets=["vehicles/saab-9-5"]),
        Q("TP09", "temporal",
          "What was the interest rate on the Majorna mortgage before it last changed, and when did it change?",
          f"{hist['mortgage_rate']['gold']}, changed on {hist['mortgage_rate']['change_date']}",
          mechanism="T-c", scope="finance",
          aliases=["1.94", "1.94%", "1.94 per cent"],
          targets=[hist["mortgage_rate"]["old"]["path"]]),
        Q("TP10", "temporal", "Which bank did Mara use for everyday banking before Handelsbanken?",
          hist["bank"]["gold"], mechanism="T-c", targets=[hist["bank"]["old"]["path"]]),
    ]
    return qs


# -------------------------------------------------------------- paraphrase --
def paraphrase(manifest: dict) -> list[dict]:
    out = []
    for i, spec in enumerate(manifest["designed"]["paraphrase"], start=1):
        out.append(Q(f"PA{i:02d}", "paraphrase", spec["question"], spec["gold"],
                     aliases=spec["aliases"], targets=[spec["path"]]))
    return out


# ---------------------------------------------------------------- negative --
def negative() -> list[dict]:
    """No answer exists anywhere in the corpus. Correct response: not found."""
    spec = [
        ("NG01", "What is the name of Mara's dog?", ["dog"]),
        ("NG02", "Which university did Mara do her doctorate at?", ["doctorate", "PhD"]),
        ("NG03", "What is Mara's blood type?", ["blood type", "blood group"]),
        ("NG04", "Which political party does Mara support?", ["political party"]),
        ("NG05", "What model of espresso machine does Mara own?", ["espresso machine"]),
        ("NG06", "Which airline does Mara hold frequent flyer status with?", ["frequent flyer"]),
        ("NG07", "What is the name of Nell's class teacher?", ["class teacher", "form teacher"]),
        ("NG08", "How many siblings does Idris Bello have?", ["sibling"]),
        ("NG09", "What was the name of Mara's first employer before Nordvik Analytics?",
         ["first employer", "previous employer"]),
        ("NG10", "Which gym does Idris go to?", ["gym"]),
    ]
    return [Q(qid, "negative", q, "not found", expect="not_found", leak_tokens=toks)
            for qid, q, toks in spec]


# -------------------------------------------------------- scope-restricted --
def scope_restricted() -> list[dict]:
    """Asked under `default`, which must not see the answer. Correct: not found.

    Each has an oblique trace visible in `default` -- the topic is present,
    the fact is not -- so answering requires inventing or inferring it.
    """
    spec = [
        ("SR01", "What condition is Mara being treated for by Dr Selma Ferreira?",
         "psoriatic arthritis", "health/psoriatic-arthritis", ["psoriatic"]),
        ("SR02", "What dose of methotrexate does Mara take, and how often?",
         "15 mg weekly, Thursday evenings", "health/methotrexate", ["methotrexate", "15 mg"]),
        ("SR03", "Which drug is Mara allergic to?",
         "penicillin", "health/penicillin-allergy", ["penicillin"]),
        ("SR04", "Which medication and dose does Mara take for her thyroid?",
         "levothyroxine 75 mcg each morning", "health/hypothyroidism",
         ["levothyroxine", "hypothyroid"]),
        ("SR05", "Which institution holds Mara's emergency savings buffer?",
         "Lansforsakringar", "finances/lansforsakringar-savings", ["Lansforsakringar"]),
        ("SR06", "Which lender holds the mortgage on the Smogen cabin?",
         "Lansforsakringar", "finances/lansforsakringar-mortgage", ["Lansforsakringar"]),
        ("SR07", "Which provider holds Mara's ISK investment account?",
         "Avanza", "finances/avanza-investment-isk", ["Avanza"]),
        ("SR08", "How many square metres is the flat in Majorna?",
         "78 square metres", "home/flat-in-majorna", ["78 square", "78 sqm", "78 m"]),
        ("SR09", "Where does Mara keep the spare keys to the flat?",
         "one set with Stig Ohman, one at the cabin", "home/spare-keys", ["spare key"]),
        ("SR10", "What legal matter does Mara currently have open concerning the Smogen property?",
         "a boundary question with the neighbouring plot", "legal/boundary",
         ["boundary"]),
    ]
    return [Q(qid, "scope_restricted", q, "not found", expect="not_found",
              scope="default", targets=[tgt], leak_tokens=toks,
              note=f"withheld answer is {gold!r}")
            for qid, q, gold, tgt, toks in spec]


# -------------------------------------------------------------- assemble ----
def build(corpus_root="corpus", data_root="data") -> list[dict]:
    manifest = json.loads((Path(corpus_root) / "manifest.json").read_text(encoding="utf-8"))
    qs = (exact_lookup() + paraphrase(manifest) + multi_hop()
          + temporal(manifest) + negative() + scope_restricted())
    errs = validate(qs, manifest, Path(data_root))
    if errs:
        raise SystemExit("question-set validation failed:\n  " + "\n  ".join(errs))
    return qs


# -------------------------------------------------------------- validation --
def _scope_text(data_root: Path, scope: str) -> tuple[str, str]:
    """All text a scope can reach: (default view, override view + profile)."""
    con = sqlite3.connect(f"file:{data_root / f'scope_{scope}.sqlite'}?mode=ro", uri=True)
    dflt = " \n".join(f"{t} {b}" for t, b in con.execute("SELECT title, body FROM memory"))
    allt = " \n".join(f"{t} {b}" for t, b in con.execute("SELECT title, body FROM memory_all"))
    prof = " \n".join(f"{k} {v}" for k, v in con.execute("SELECT key, value FROM profile"))
    con.close()
    return dflt + " " + prof, allt + " " + prof


def _paths(data_root: Path, scope: str, table: str) -> set[str]:
    con = sqlite3.connect(f"file:{data_root / f'scope_{scope}.sqlite'}?mode=ro", uri=True)
    out = {r[0] for r in con.execute(f"SELECT path FROM {table}")}
    con.close()
    return out


def validate(qs: list[dict], manifest: dict, data_root: Path) -> list[str]:
    errs: list[str] = []
    if len(qs) != 60:
        errs.append(f"expected 60 questions, got {len(qs)}")
    for s in STRATA:
        n = sum(1 for q in qs if q["stratum"] == s)
        if n < 8:
            errs.append(f"stratum {s} has {n} questions, minimum is 8")
    ids = [q["id"] for q in qs]
    if len(set(ids)) != len(ids):
        errs.append("duplicate question ids")

    cache: dict[str, tuple[str, str]] = {}
    def text(scope):
        if scope not in cache:
            cache[scope] = _scope_text(data_root, scope)
        return cache[scope]

    def hit(hay: str, q: dict) -> bool:
        cands = [q["gold"]] + q["aliases"]
        return any(c.lower() in hay.lower() for c in cands if c)

    for q in qs:
        dflt, allt = text(q["scope"])
        st = q["stratum"]

        if st in ("exact_lookup", "paraphrase", "multi_hop"):
            if not hit(dflt, q):
                errs.append(f"{q['id']}: gold {q['gold']!r} not reachable from the "
                            f"default view of scope {q['scope']} -- it would need the override")
            for t in q["targets"]:
                if t.startswith("profile"):
                    continue
                if t not in _paths(data_root, q["scope"], "memory"):
                    errs.append(f"{q['id']}: target {t} is not in the default view")

        elif st == "temporal":
            mech = q["mechanism"]
            if mech == "T-a":
                seen = _paths(data_root, q["scope"], "memory")
                missing = [t for t in q["targets"] if t not in seen]
                if missing:
                    errs.append(f"{q['id']} (T-a): {missing} not default-visible; the "
                                f"default filter would resolve this without the edge")
                sdb = data_root / f"scope_{q['scope']}.sqlite"
                con = sqlite3.connect(f"file:{sdb}?mode=ro", uri=True)
                n = con.execute("SELECT count(*) FROM relations WHERE rel='supersedes' "
                                "AND target_page=?", (q["targets"][1],)).fetchone()[0]
                con.close()
                if n == 0:
                    errs.append(f"{q['id']} (T-a): no supersedes edge targets {q['targets'][1]}")
            elif mech == "T-b":
                seen = _paths(data_root, q["scope"], "memory")
                missing = [t for t in q["targets"] if t not in seen]
                if missing:
                    errs.append(f"{q['id']} (T-b): {missing} not default-visible")
            elif mech == "T-c":
                seen = _paths(data_root, q["scope"], "memory")
                seen_all = _paths(data_root, q["scope"], "memory_all")
                for t in q["targets"]:
                    if t in seen:
                        errs.append(f"{q['id']} (T-c): {t} IS default-visible, so no "
                                    f"override is needed -- this is an exact lookup")
                    if t not in seen_all:
                        errs.append(f"{q['id']} (T-c): {t} not reachable even with the override")
                if hit(dflt, q):
                    errs.append(f"{q['id']} (T-c): gold {q['gold']!r} appears in the "
                                f"default view; the override is not required")

        elif st == "negative":
            _, full_all = text("full")
            for tok in q["leak_tokens"]:
                if tok.lower() in full_all.lower():
                    errs.append(f"{q['id']} (negative): token {tok!r} DOES appear in the "
                                f"corpus -- this question has an answer")

        elif st == "scope_restricted":
            seen_all = _paths(data_root, q["scope"], "memory_all")
            for t in q["targets"]:
                if t in seen_all:
                    errs.append(f"{q['id']}: target {t} IS visible under scope "
                                f"{q['scope']} -- not actually restricted")
            for tok in q["leak_tokens"]:
                if tok.lower() in allt.lower():
                    errs.append(f"{q['id']}: leak token {tok!r} is reachable under scope "
                                f"{q['scope']} -- the answer is not withheld")
    return errs


def main(out="questions/questions.json") -> None:
    qs = build()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(qs, indent=2, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(q["stratum"] for q in qs)
    print(f"questions: {len(qs)} -> {out}")
    for s in STRATA:
        extra = ""
        if s == "temporal":
            m = Counter(q["mechanism"] for q in qs if q["stratum"] == s)
            extra = "  (" + ", ".join(f"{k}:{v}" for k, v in sorted(m.items())) + ")"
        print(f"  {s:18s} {c[s]}{extra}")


if __name__ == "__main__":
    main()
