"""corpus-b: memory shaped the way real memory stores are actually shaped.

corpus-a treats a FACT as the unit of storage: one page, one assertion, full
SPEC.md §5.1 frontmatter, supersession as a typed `supersedes` edge. That is
what PCP §5 specifies. It is not what either of the two real stores surveyed
for the second pass looks like (REPORT.md §8.1).

Both of those stores are SUBJECT-shaped, and neither carries any explicit
supersession structure at all:

  * the unit is a subject file with 8-25 bullet facts in it
  * there is ONE file-level `updated` and nothing else -- no per-fact
    lifecycle, confidence, valid_from, valid_until, or relations
  * supersession appears only as prose, in three forms:
      (a) tense plus a date inside a single line
          "Omnisend was a client in 2025"
      (b) prose cues spread across lines of the same file
          "Ruled out both candidates below" ... "Previously compared two X"
      (c) not at all -- a whole file silently stale, contradicted by a newer
          file somewhere else, with nothing linking them

corpus-b reproduces exactly that. Same persona, same gold answers, different
shape. What changes is not the truth, only how it is written down -- which is
the point: it isolates the effect of storage shape on retrieval.

Consequences that are deliberate, not oversights:

  * `memory` and `memory_all` are IDENTICAL, because nothing is ever marked
    stale. The §5.2 default filter has nothing to filter.
  * `relations` is empty. There is no join to do.
  * `tags` is empty. The directory a file sits in is the only taxonomy, which
    is what the surveyed stores have.
  * SENSITIVITY IS FILE-LEVEL. A subject file containing one sensitive fact
    is sensitive in its entirety, so scope filtering is coarser here than in
    corpus-a. That is not a bug in the generator -- it is the direct
    consequence of subject-sized pages, and it is the sharpest input to the
    unit-of-storage question in REPORT.md §8.6.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from . import persona as P
from .model import Fact, Page, SEED, TODAY
from .reconcile import RECONCILE

PEOPLE_BY_ID = {p[0]: p for p in P.PEOPLE}
PROJ_BY_ID = {p[0]: p for p in P.PROJECTS}
VEH_BY_ID = {v[0]: v for v in P.VEHICLES}


def _slug(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    s = "".join(out)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


class SubjectBuilder:
    """Builds corpus-b. Every page is a subject file of bullet facts."""

    MIN_BULLETS = 8
    MAX_BULLETS = 25

    def __init__(self, seed: int = SEED, target_pages: int = 2000):
        self.rng = random.Random(seed + 7)
        self.target_pages = target_pages
        self.pages: list[Page] = []
        self.facts: list[Fact] = []
        self.gold_lines: dict[str, list[str]] = {}   # page path -> gold bullets

    # ------------------------------------------------------------ helpers --
    def _date(self, lo: str = "2024-01-01", hi: str = TODAY) -> str:
        import datetime as dt
        a = dt.date.fromisoformat(lo).toordinal()
        b = dt.date.fromisoformat(hi).toordinal()
        return dt.date.fromordinal(self.rng.randint(a, b)).isoformat()

    def file(self, path: str, title: str, domain: str, bullets: list[str], *,
             updated: str | None = None, sensitivity: str = "normal",
             namespace: str | None = None, pad: bool = True,
             ptype: str = "semantic") -> Page:
        """Add one subject file. Gold bullets first, filler shuffled in after.

        Padding puts the gold bullet somewhere in the middle of the file
        rather than at the top, so a retrieval method that returns only the
        first line of a page gets nothing.
        """
        body_lines = list(bullets)
        if pad:
            n = self.rng.randint(self.MIN_BULLETS, self.MAX_BULLETS)
            extra = max(0, n - len(body_lines))
            filler, seen = [], set()
            for _ in range(extra * 4):
                if len(filler) >= extra:
                    break
                b = self._filler_bullet(domain)
                if b not in seen:
                    seen.add(b)
                    filler.append(b)
            # interleave: keep gold bullets in original order, but pushed
            # down into the file
            head = filler[: len(filler) // 2]
            tail = filler[len(filler) // 2:]
            body_lines = head + body_lines + tail
        pg = Page(
            path=path, title=title, updated=updated or self._date(),
            type=ptype, domain=domain,
            body="\n".join(f"- {b}" for b in body_lines),
            tags=[],                     # no curated taxonomy in corpus-b
            sensitivity=sensitivity, namespace=namespace,
            lifecycle="active",          # every file; carries zero information
            confidence=None, valid_from=None, valid_until=None,
            source=None, derived_from=[], relations=[],
            minimal=True,
        )
        self.pages.append(pg)
        self.gold_lines[path] = list(bullets)
        return pg

    def fact(self, **kw) -> Fact:
        f = Fact(**kw)
        self.facts.append(f)
        return f

    # ------------------------------------------------------------- filler --
    FILLER = [
        "Thread picked up again after the {season} break; nothing outstanding.",
        "Checked in on this during the {month} review, no change since.",
        "{who} mentioned this in passing; noted for completeness.",
        "Reminder set for {month} to look at this again.",
        "Left as it stands for now -- revisit if the situation shifts.",
        "Filed the paperwork for this in the hall cupboard folder.",
        "Took about {n} minutes to sort out in the end.",
        "Worth remembering that this changed once already, back in {year}.",
        "No action needed; recorded so it is not asked again.",
        "{who} has the details if they are ever needed.",
        "Discussed over coffee on a {day}, nothing formal decided.",
        "This sits alongside the {topic} arrangements.",
        "Rough note, not verified: {topic} may need looking at in {month}.",
        "Copied across from an older note during the {month} tidy-up.",
        "Cross-check with the {topic} file if anything looks off.",
        "Small enough that it never made it onto a list before now.",
        "{who} asked about this once; the answer has not changed.",
        "Kept here rather than in {topic} because it comes up more often.",
        "The {season} arrangement is the same as last year's.",
    ]
    TOPICS = ["household", "travel", "school", "cabin", "billing", "cycling",
              "reading", "swimming", "gardening", "correspondence", "storage",
              "insurance", "commuting", "cooking", "music practice"]
    MONTHS = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]
    SEASONS = ["summer", "winter", "autumn", "spring"]

    def _filler_bullet(self, domain: str) -> str:
        return self.rng.choice(self.FILLER).format(
            who=self.rng.choice([p[1] for p in P.PEOPLE]),
            month=self.rng.choice(self.MONTHS),
            day=self.rng.choice(self.DAYS),
            season=self.rng.choice(self.SEASONS),
            topic=self.rng.choice(self.TOPICS),
            year=self.rng.choice(["2021", "2022", "2023", "2024", "2025"]),
            n=self.rng.choice(["ten", "twenty", "forty", "ninety"]),
        )

    # ======================================================== core subjects --
    def build_people(self) -> None:
        for (pid, name, rel, org, city, role) in P.PEOPLE:
            path = f"people/{_slug(name)}"
            bullets = [
                f"{name} -- {rel}.",
                f"Works at {org} as {role}.",
                f"Based in {city}.",
            ]
            self.file(path, name, "people", bullets)
            for pred, obj in (("relation", rel), ("organisation", org),
                              ("city", city), ("role", role)):
                self.fact(id=f"person.{pid}.{pred}", domain="people", subject=name,
                          predicate=pred, obj=obj, page=path)

    def build_projects(self) -> None:
        for (pjid, name, client, lead, dlead, status, vf, vu, budget, repo,
             stack) in P.PROJECTS:
            path = f"projects/{_slug(name)}"
            bullets = [
                f"{name} is funded by {client}.",
                f"Engineering lead is {PEOPLE_BY_ID[lead][1]}.",
                f"Design lead is {PEOPLE_BY_ID[dlead][1]}.",
                f"Built on {stack}; repository is {repo}.",
                f"Budget {budget} kSEK. Status: {status}, from {vf}"
                + (f" to {vu}." if vu else "."),
            ]
            self.file(path, name, "projects", bullets)
            for pred, obj in (("client", client), ("stack", stack),
                              ("repository", repo), ("budget", f"{budget} kSEK"),
                              ("lead", PEOPLE_BY_ID[lead][1]),
                              ("design lead", PEOPLE_BY_ID[dlead][1]),
                              ("status", status)):
                self.fact(id=f"proj.{pjid}.{_slug(pred)}", domain="projects",
                          subject=name, predicate=pred, obj=obj, page=path)

    def build_vehicles(self) -> None:
        for (vid, make, model, year, colour, plate, status, vf, vu,
             note) in P.VEHICLES:
            path = f"vehicles/{_slug(make + ' ' + model)}"
            # (a) tense + date in the line: a sold car says so IN the prose.
            if status == "sold":
                bullets = [
                    f"{make} {model} ({year}, {colour}), registration {plate}.",
                    f"Was the car from {vf} until {vu}; {note}.",
                    f"Sold in {vu[:4]}. No longer owned.",
                ]
            else:
                bullets = [
                    f"{make} {model} ({year}, {colour}), registration {plate}.",
                    f"In use since {vf}; {note}.",
                ]
            self.file(path, f"{make} {model}", "vehicles", bullets)
            for pred, obj in (("registration", plate), ("colour", colour),
                              ("year", str(year)), ("status", status)):
                self.fact(id=f"veh.{vid}.{pred}", domain="vehicles",
                          subject=f"{make} {model}", predicate=pred, obj=obj,
                          page=path)

    def build_finances(self) -> None:
        for (aid, inst, kind, ref, detail, sens) in P.ACCOUNTS:
            path = f"finances/{_slug(inst + ' ' + kind)}"
            bullets = [
                f"{kind.capitalize()} with {inst}, reference {ref}.",
                f"{detail.capitalize()}.",
            ]
            # A file with one sensitive fact is sensitive in its ENTIRETY.
            self.file(path, f"{inst} {kind}", "finances", bullets,
                      sensitivity=sens,
                      namespace="pcp.finance" if sens == "sensitive" else None)
            self.fact(id=f"acct.{aid}", domain="finances", subject=kind,
                      predicate="institution", obj=inst, page=path,
                      sensitivity=sens,
                      namespace="pcp.finance" if sens == "sensitive" else None)

    def build_health(self) -> None:
        for (hid, label, detail, clin, since, until, sens) in P.HEALTH:
            path = f"health/{_slug(label)}"
            bullets = [f"{label.capitalize()}: {detail}."]
            if until:
                bullets.append(f"Ran from {since} until {until}; stopped since.")
            else:
                bullets.append(f"Ongoing since {since}.")
            bullets.append(f"Under {PEOPLE_BY_ID[clin][1]}.")
            self.file(path, label.capitalize(), "health", bullets,
                      sensitivity=sens, namespace="pcp.health")
            self.fact(id=f"health.{hid}", domain="health", subject=label,
                      predicate="detail", obj=detail, page=path,
                      sensitivity=sens, namespace="pcp.health")

    def build_travel(self) -> None:
        for (tid, dest, country, purpose, start, end, with_ids, note) in P.TRIPS:
            path = f"travel/{start[:7]}-{_slug(dest)}"
            companions = ", ".join(PEOPLE_BY_ID[w][1] for w in with_ids)
            past = end < TODAY
            bullets = [
                f"{dest}, {country} -- {purpose}. {start} to {end}.",
                (f"Went with {companions}." if past else f"Going with {companions}."),
                f"{note.capitalize()}.",
            ]
            self.file(path, f"{dest} {start[:7]}", "travel", bullets,
                      ptype="episodic")
            self.fact(id=f"trip.{tid}", domain="travel", subject=dest,
                      predicate="purpose", obj=purpose, page=path)

    def build_preferences(self) -> None:
        by_area: dict[str, list[tuple]] = {}
        for (pfid, area, statement, strength) in P.PREFERENCES:
            by_area.setdefault(area, []).append((pfid, statement, strength))
        for area, items in by_area.items():
            path = f"preferences/{_slug(area)}"
            bullets = [f"{s.capitalize()}. ({st})" for _, s, st in items]
            self.file(path, f"Preferences -- {area}", "preferences", bullets)
            for pfid, s, _ in items:
                self.fact(id=f"pref.{pfid}", domain="preferences", subject=area,
                          predicate="preference", obj=s, page=path)

    def build_home(self) -> None:
        for (hid, label, detail, sens, ns) in P.HOME:
            path = f"home/{_slug(label)}"
            bullets = [f"{label.capitalize()}: {detail}."]
            self.file(path, label.capitalize(), "home", bullets,
                      sensitivity=sens, namespace=ns)
            self.fact(id=f"home.{hid}", domain="home", subject=label,
                      predicate="detail", obj=detail, page=path,
                      sensitivity=sens, namespace=ns)

    def build_legal(self) -> None:
        self.file("legal/property-matters", "Property matters", "home", [
            "Cecilia Bratt of Bratt & Soner acts on property matters; "
            "instructed since 2019.",
            "Title to the Smogen cabin is held jointly with Sofie Lindqvist; "
            "deed lodged with Bratt & Soner.",
            "Mirror wills executed with Idris in 2022; Cecilia Bratt holds the "
            "originals.",
            "Boundary question with the neighbouring plot at Smogen, opened "
            "2026-02. Cecilia Bratt is corresponding with the other side.",
        ], sensitivity="sensitive", namespace="pcp.legal")
        self.fact(id="legal.solicitor", domain="home", subject="legal matters",
                  predicate="solicitor", obj="Cecilia Bratt",
                  page="legal/property-matters", sensitivity="sensitive",
                  namespace="pcp.legal",
                  aliases=["Cecilia Bratt of Bratt & Soner", "Bratt & Soner"])

    # ==================================== supersession, encoded ONLY as prose --

    # (a) tense plus a date inside a SINGLE line. Both the current and the
    #     former value sit in the same file, on adjacent-ish lines; the tense
    #     and the date are the only things that separate them.
    PROSE_A = [
        dict(key="role", path="work/role-at-nordvik", title="Role at Nordvik Analytics",
             domain="work", subject="Mara", predicate="job title",
             gold="Principal Data Engineer", stale_gold="Senior Data Engineer",
             bullets=[
                 "Title is Principal Data Engineer, since the August 2026 "
                 "reorganisation.",
                 "Sits in the Data Platform group.",
                 "Was Senior Data Engineer from 2023 until August 2026.",
             ]),
        dict(key="reporting", path="work/reporting-line", title="Reporting line",
             domain="work", subject="Mara", predicate="manager",
             gold="Petra Hallgren", stale_gold="Olu Adeyemi",
             bullets=[
                 "Reports to Petra Hallgren, VP Engineering, since August 2026.",
                 "Fortnightly one-to-one, Wednesday afternoons.",
                 "Reported to Olu Adeyemi, engineering manager, up to July 2026.",
             ]),
    ]

    # (b) prose cues spread ACROSS LINES of the same file. No line is
    #     self-sufficient: the line carrying the answer does not say it is
    #     current, and the line that says which is current does not carry the
    #     answer. This is the case narrow projection cannot survive.
    PROSE_B = [
        dict(key="laptop", path="work/equipment", title="Work equipment",
             domain="work", subject="Mara", predicate="work laptop",
             gold="Framework 16", stale_gold="MacBook Pro 14",
             bullets=[
                 "Ruled out both of the candidates below; now on a Framework "
                 "16, issued by IT in May.",
                 "Docking station at the desk, two 27-inch monitors.",
                 "Previously compared two laptops for the refresh: a MacBook "
                 "Pro 14 and a Dell XPS 15.",
             ]),
        dict(key="steering", path="projects/tidewater-governance",
             title="Tidewater governance", domain="projects",
             subject="Tidewater steering group", predicate="chair",
             gold="Elin Nordgren", stale_gold="Mira Tuominen",
             bullets=[
                 "Chair rotated at the March meeting; Elin Nordgren has "
                 "chaired it since then.",
                 "Meets monthly, first Tuesday, forty minutes.",
                 "Mira Tuominen set up the Tidewater steering group and ran "
                 "it from the kickoff.",
             ]),
    ]

    def build_prose_supersession(self) -> None:
        for spec in self.PROSE_A + self.PROSE_B:
            self.file(spec["path"], spec["title"], spec["domain"],
                      spec["bullets"], updated="2026-08-21")
            self.fact(id=f"prose.{spec['key']}.current", domain=spec["domain"],
                      subject=spec["subject"], predicate=spec["predicate"],
                      obj=spec["gold"], page=spec["path"])
            self.fact(id=f"prose.{spec['key']}.former", domain=spec["domain"],
                      subject=spec["subject"],
                      predicate="former " + spec["predicate"],
                      obj=spec["stale_gold"], page=spec["path"])

    # (c) whole files silently stale, contradicted by a newer file elsewhere.
    def build_reconcile(self) -> None:
        for spec in RECONCILE:
            for side in ("current", "stale"):
                d = spec[side]
                sentences = [t.strip() + "." for t in d["body"].split(". ")
                             if t.strip()]
                sentences[-1] = sentences[-1].rstrip(".") + "."
                self.file(d["path"], d["title"], spec["domain"], sentences,
                          updated=d["updated"])
            self.fact(id=f"rec.{spec['key']}.current", domain=spec["domain"],
                      subject=spec["subject"], predicate=spec["predicate"],
                      obj=spec["gold"], page=spec["current"]["path"],
                      aliases=list(spec["aliases"]))
            self.fact(id=f"rec.{spec['key']}.stale", domain=spec["domain"],
                      subject=spec["subject"],
                      predicate="superseded " + spec["predicate"],
                      obj=spec["stale_gold"], page=spec["stale"]["path"])

    # ---------------------------------------------------------- paraphrase --
    # The same ten bodies as corpus-a, but each is now ONE BULLET inside a
    # larger subject file, so the retrieval unit is much bigger than the fact.
    def build_paraphrase(self) -> None:
        from .corpus import Builder
        for spec in Builder.PARAPHRASE:
            path = f"{spec['domain']}/subject-{spec['key']}"
            self.file(path, spec["title"], spec["domain"], [spec["body"]])
            self.fact(id=f"para.{spec['key']}", domain=spec["domain"],
                      subject=spec["title"], predicate="detail",
                      obj=spec["gold"], page=path, aliases=list(spec["aliases"]))

    # -------------------------------------------------------------- traces --
    def build_traces(self) -> None:
        from .corpus import Builder
        for path, title, domain, body in Builder.TRACES:
            self.file(path, title, domain, [body], ptype="episodic")

    # -------------------------------------------------------------- filler --
    FILLER_SUBJECTS = [
        "kitchen", "laundry", "recycling", "post", "keys", "lighting",
        "windows", "flooring", "shelving", "curtains", "radiators", "hallway",
        "balcony", "cellar", "loft", "porch", "gate", "fence", "path", "shed",
        "bookshelf", "records", "photographs", "letters", "receipts", "manuals",
        "warranties", "subscriptions", "deliveries", "appointments",
        "reminders", "lists", "recipes", "menus", "shopping", "budgeting",
        "timetables", "routes", "tickets", "maps",
    ]
    FILLER_QUALIFIERS = ["at the flat", "at the cabin", "in the basement",
                         "for the children", "for work", "for the summer",
                         "for the winter", "on Saturdays", "in town",
                         "for visitors"]

    def build_filler(self, n: int) -> None:
        """Subject files with nothing gold in them, to reach corpus scale."""
        made = 0
        i = 0
        while made < n:
            i += 1
            subj = self.rng.choice(self.FILLER_SUBJECTS)
            qual = self.rng.choice(self.FILLER_QUALIFIERS)
            path = f"notes/{_slug(subj)}-{_slug(qual)}-{i:04d}"
            title = f"{subj.capitalize()} {qual}"
            self.file(path, title, self.rng.choice(
                ["home", "preferences", "people", "work", "travel"]),
                [f"{title} -- running notes."], ptype="episodic")
            made += 1

    # ------------------------------------------------------------ assemble --
    def build_all(self) -> None:
        for m in ("build_people", "build_projects", "build_vehicles",
                  "build_finances", "build_health", "build_travel",
                  "build_preferences", "build_home", "build_legal",
                  "build_prose_supersession", "build_reconcile",
                  "build_paraphrase", "build_traces"):
            getattr(self, m)()
        self.build_filler(max(0, self.target_pages - len(self.pages)))

    # ------------------------------------------------------------ validate --
    def validate(self) -> list[str]:
        errs: list[str] = []
        paths = [p.path for p in self.pages]
        dupes = {p for p in paths if paths.count(p) > 1}
        if dupes:
            errs.append(f"duplicate page paths: {sorted(dupes)[:5]}")

        lo, hi = int(self.target_pages * 0.95), int(self.target_pages * 1.05)
        if not (lo <= len(self.pages) <= hi):
            errs.append(f"page count {len(self.pages)} outside {lo}-{hi}")

        # The defining property of corpus-b: NO per-fact structure anywhere.
        for p in self.pages:
            if p.relations or p.derived_from:
                errs.append(f"{p.path}: corpus-b must carry no relations")
            if p.confidence is not None:
                errs.append(f"{p.path}: corpus-b must carry no confidence")
            if p.valid_from or p.valid_until:
                errs.append(f"{p.path}: corpus-b must carry no validity window")
            if p.lifecycle != "active":
                errs.append(f"{p.path}: corpus-b lifecycle must be uniformly active")
            if p.tags:
                errs.append(f"{p.path}: corpus-b must carry no tags")
            if not p.minimal:
                errs.append(f"{p.path}: corpus-b pages must render minimal frontmatter")

        # Bullet counts must sit in the surveyed 8-25 band.
        bad = [p.path for p in self.pages
               if not (self.MIN_BULLETS <= len(p.body.splitlines()) <= self.MAX_BULLETS)]
        if bad:
            errs.append(f"{len(bad)} files outside the {self.MIN_BULLETS}-"
                        f"{self.MAX_BULLETS} bullet band, e.g. {bad[:3]}")

        # Case (c): both sides of every reconcile pair must be present, both
        # visible, and neither marked in any way.
        by_path = {p.path: p for p in self.pages}
        for spec in RECONCILE:
            for side in ("current", "stale"):
                if spec[side]["path"] not in by_path:
                    errs.append(f"reconcile {spec['key']}: {side} page missing")
            cur, stale = by_path.get(spec["current"]["path"]), by_path.get(spec["stale"]["path"])
            if cur and stale:
                if spec["discriminator"] == "recency" and not (cur.updated > stale.updated):
                    errs.append(f"reconcile {spec['key']}: declared recency-resolved "
                                f"but the current page is not the newer one")
                if spec["discriminator"] == "content" and cur.updated > stale.updated:
                    errs.append(f"reconcile {spec['key']}: declared content-resolved "
                                f"but recency already gives the right answer")

        # Prose supersession: both values must live in the SAME file, so the
        # discriminator can only be the surrounding prose.
        for spec in self.PROSE_A + self.PROSE_B:
            pg = by_path.get(spec["path"])
            if pg is None:
                errs.append(f"prose {spec['key']}: page missing")
                continue
            for val in (spec["gold"], spec["stale_gold"]):
                if val.lower() not in pg.body.lower():
                    errs.append(f"prose {spec['key']}: {val!r} not in {pg.path}")
        # (b) specifically: the cue line and the answer line must be different
        # lines, otherwise narrow projection would be enough.
        for spec in self.PROSE_B:
            pg = by_path[spec["path"]]
            lines = pg.body.splitlines()
            gold_l = [i for i, l in enumerate(lines) if spec["gold"].lower() in l.lower()]
            stale_l = [i for i, l in enumerate(lines) if spec["stale_gold"].lower() in l.lower()]
            if not gold_l or not stale_l or set(gold_l) & set(stale_l):
                errs.append(f"prose-b {spec['key']}: gold and stale must be on "
                            f"separate lines of the same file")
        return errs

    # --------------------------------------------------------------- write --
    def write(self, root: Path) -> dict:
        from .model import SCOPE_BUNDLES, BUNDLE_NAMESPACES
        from .corpus import Builder

        pages_dir = root / "pages"
        if pages_dir.exists():
            import shutil
            shutil.rmtree(pages_dir)
        for p in self.pages:
            fp = pages_dir / (p.path + ".md")
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(p.render(), encoding="utf-8")

        # The profile documents are shape-independent -- same persona, same
        # SPEC.md §4 documents, so corpus-a and corpus-b share them exactly.
        profile = Builder(SEED).build_profile()
        (root / "profile").mkdir(parents=True, exist_ok=True)
        for ns, doc in profile.items():
            (root / "profile" / f"{ns}.json").write_text(
                json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

        def visible_in(p: Page, bundle: str) -> bool:
            if p.namespace and p.namespace not in BUNDLE_NAMESPACES[bundle]:
                return False
            if p.sensitivity == "sensitive" and "memory.sensitive:read" not in SCOPE_BUNDLES[bundle]:
                return False
            return True

        nb = [len(p.body.splitlines()) for p in self.pages]
        manifest = {
            "seed": SEED,
            "shape": "subject",
            "today": TODAY,
            "persona": P.PERSONA,
            "counts": {
                "pages": len(self.pages),
                "facts": len(self.facts),
                "bullets": sum(nb),
                "bullets_per_file": {
                    "min": min(nb), "max": max(nb),
                    "mean": round(sum(nb) / len(nb), 1),
                },
                "by_domain": {d: sum(1 for p in self.pages if p.domain == d)
                              for d in sorted({p.domain for p in self.pages})},
                "by_lifecycle": {"active": len(self.pages)},
                "default_visible": sum(1 for p in self.pages if p.default_visible()),
                "sensitive": sum(1 for p in self.pages if p.sensitivity == "sensitive"),
            },
            "pages": [
                {
                    "path": p.path, "title": p.title, "domain": p.domain,
                    "type": p.type, "lifecycle": p.lifecycle,
                    "sensitivity": p.sensitivity, "namespace": p.namespace,
                    "valid_from": None, "valid_until": None,
                    "confidence": None, "tags": [],
                    "relations": [], "derived_from": [],
                    "updated": p.updated,
                    "default_visible": True,
                    "visible_in": [b for b in SCOPE_BUNDLES if visible_in(p, b)],
                    "body": p.body,
                }
                for p in self.pages
            ],
            "facts": [f.to_json() for f in self.facts],
            "profile_namespaces": list(profile),
            "designed": {
                "prose_a": self.PROSE_A,
                "prose_b": self.PROSE_B,
                "reconcile": RECONCILE,
                "paraphrase": Builder.PARAPHRASE,
                "traces": [t[0] for t in Builder.TRACES],
                # corpus-b has no edge-, window- or lifecycle-encoded
                # supersession at all. Recorded as empty on purpose so the
                # report can say so from the manifest rather than from prose.
                "supersession": [],
                "windows": [],
                "historical": [],
            },
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest


def main(root: str = "corpus-b", seed: int = SEED, target_pages: int = 2000) -> dict:
    b = SubjectBuilder(seed, target_pages)
    b.build_all()
    errs = b.validate()
    if errs:
        raise SystemExit("corpus-b validation failed:\n  " + "\n  ".join(errs))
    m = b.write(Path(root))
    c = m["counts"]
    print(f"corpus-b: {c['pages']} subject files, {c['bullets']} bullets "
          f"({c['bullets_per_file']['min']}-{c['bullets_per_file']['max']}, "
          f"mean {c['bullets_per_file']['mean']}), {c['facts']} gold facts, "
          f"{c['sensitive']} sensitive files")
    return m


if __name__ == "__main__":
    raise SystemExit(main() and 0)
