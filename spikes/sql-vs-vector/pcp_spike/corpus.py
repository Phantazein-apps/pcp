"""Corpus generator: renders PCP memory pages from the persona entity tables.

Every page is produced from `Fact` records, so gold answers are exact by
construction. Everything is seeded; two runs with the same seed produce
byte-identical output.

Noise deliberately included (brief §Build 1):
  * near-duplicate pages
  * supersession pairs -- modelled ONLY as a `supersedes` relation, both
    pages left `active` so the §5.2 default filter does not resolve them
    (NOTES.md §2.1)
  * facts with validity windows, including overlapping ones
  * contradictions resolvable only via validity / lifecycle / relations
  * pages whose wording shares no vocabulary with the questions targeting
    them (asserted at build time)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from .model import Fact, Page, SEED, TODAY, content_tokens
from . import persona as P

PEOPLE_BY_ID = {p[0]: p for p in P.PEOPLE}


def _slug(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    return "-".join(x for x in "".join(out).split("-") if x)


class Builder:
    def __init__(self, seed: int = SEED):
        self.rng = random.Random(seed)
        self.pages: list[Page] = []
        self.facts: list[Fact] = []

    # ------------------------------------------------------------ helpers --
    def add(self, page: Page) -> Page:
        self.pages.append(page)
        return page

    def fact(self, **kw) -> Fact:
        f = Fact(**kw)
        self.facts.append(f)
        return f

    def _date(self, lo: str = "2024-01-01", hi: str = TODAY) -> str:
        import datetime as dt
        a = dt.date.fromisoformat(lo).toordinal()
        b = dt.date.fromisoformat(hi).toordinal()
        return dt.date.fromordinal(self.rng.randint(a, b)).isoformat()

    # -------------------------------------------------------------- people --
    def build_people(self) -> None:
        for pid, name, rel, org, city, role in P.PEOPLE:
            path = f"people/{_slug(name)}"
            first = name.split()[0]
            body = (
                f"{name} — {rel}. {role.capitalize()} at {org}, based in {city}.\n\n"
                f"Mara sees {first} mostly through {'work' if rel in ('colleague','manager','client') else rel} contexts. "
                f"{'Reachable on the internal directory.' if org == 'Nordvik Analytics' else 'Contact details are in the address book.'}"
            )
            self.add(Page(
                path=path, title=name, updated=self._date(), type="semantic",
                domain="people", body=body, tags=["people", rel, _slug(org)],
                lifecycle=self.rng.choice(["active", "active", "validated"]),
                confidence=round(self.rng.uniform(0.75, 0.99), 2),
                source={"origin": "chat", "client": "claude-desktop"},
                facts=[],
            ))
            self.fact(id=f"person.{pid}.role", domain="people", subject=name,
                      predicate="role", obj=role, page=path)
            self.fact(id=f"person.{pid}.city", domain="people", subject=name,
                      predicate="city", obj=city, page=path)
            self.fact(id=f"person.{pid}.org", domain="people", subject=name,
                      predicate="organisation", obj=org, page=path)
            self.fact(id=f"person.{pid}.rel", domain="people", subject=name,
                      predicate="relationship to Mara", obj=rel, page=path)

            # an episodic note per person
            ep = f"people/notes/{_slug(name)}-{self._date()}"
            self.add(Page(
                path=ep, title=f"Note — {name}", updated=self._date(),
                type="episodic", domain="people",
                body=self.rng.choice([
                    f"Caught up with {first} briefly. Nothing outstanding.",
                    f"{first} mentioned they are travelling later in the month.",
                    f"Owe {first} a reply about the thing from last week.",
                    f"{first} asked after the children. Sent photos.",
                ]),
                tags=["people", "note"],
                lifecycle=self.rng.choice(["active", "active", "stale"]),
                source={"origin": "chat"},
            ))

    # ------------------------------------------------------------ projects --
    def build_projects(self) -> None:
        for (pid, name, client, lead, dlead, status, vf, vu, budget, repo, stack) in P.PROJECTS:
            path = f"projects/{_slug(name)}"
            lead_name = PEOPLE_BY_ID[lead][1]
            dlead_name = PEOPLE_BY_ID[dlead][1]
            lifecycle = {"active": "active", "paused": "active",
                         "completed": "archived", "cancelled": "archived"}[status]
            body = (
                f"# {name}\n\n"
                f"Client: {client}. Engineering lead: {lead_name}. Design lead: {dlead_name}.\n"
                f"Budget {budget} kSEK. Repository `{repo}`. Built on {stack}.\n\n"
                f"Status: {status}. Started {vf}." + (f" Ended {vu}." if vu else "")
            )
            self.add(Page(
                path=path, title=f"Project {name}", updated=self._date(),
                type="semantic", domain="projects", body=body,
                tags=["projects", _slug(client), status, _slug(stack)],
                lifecycle=lifecycle, valid_from=vf, valid_until=vu,
                confidence=0.95, source={"origin": "connector", "client": "notion"},
            ))
            for pred, val in [("client", client), ("engineering lead", lead_name),
                              ("design lead", dlead_name), ("budget", f"{budget} kSEK"),
                              ("repository", repo), ("stack", stack), ("status", status)]:
                self.fact(id=f"project.{pid}.{_slug(pred)}", domain="projects",
                          subject=name, predicate=pred, obj=val, page=path,
                          lifecycle=lifecycle, valid_from=vf, valid_until=vu)

            for i in range(3):
                self.add(Page(
                    path=f"projects/{_slug(name)}/standup-{i}-{self._date()}",
                    title=f"{name} standup note {i+1}", updated=self._date(),
                    type="episodic", domain="projects",
                    body=self.rng.choice([
                        f"{name}: backlog groomed, two tickets carried over. {lead_name} to unblock the ingest path.",
                        f"{name}: {dlead_name} shared revised wireframes. Feedback by Friday.",
                        f"{name}: staging deploy green. Waiting on {client} for test data.",
                        f"{name}: scope conversation deferred to the next steering call.",
                    ]),
                    tags=["projects", "standup", _slug(name)],
                    lifecycle=self.rng.choice(["active", "active", "stale"]),
                    source={"origin": "chat"},
                ))

    # ------------------------------------------------------------ vehicles --
    def build_vehicles(self) -> None:
        for (vid, make, model, year, colour, plate, status, vf, vu, note) in P.VEHICLES:
            path = f"vehicles/{_slug(make + '-' + model)}"
            lifecycle = "active" if status == "current" else "archived"
            body = (
                f"{year} {make} {model}, {colour}. Registration {plate}.\n\n"
                f"{note.capitalize()}. Serviced by Peder Norrback at Norrback Bil in Molndal."
            )
            self.add(Page(
                path=path, title=f"{make} {model}", updated=self._date(),
                type="semantic", domain="vehicles", body=body,
                tags=["vehicles", _slug(make), status],
                lifecycle=lifecycle, valid_from=vf, valid_until=vu, confidence=0.97,
                source={"origin": "user"},
            ))
            for pred, val in [("colour", colour), ("registration", plate),
                              ("year", str(year)), ("make", make), ("model", model),
                              ("status", status)]:
                self.fact(id=f"vehicle.{vid}.{pred}", domain="vehicles",
                          subject=f"{make} {model}", predicate=pred, obj=val,
                          page=path, lifecycle=lifecycle, valid_from=vf, valid_until=vu)

    # ------------------------------------------------------------ finances --
    def build_finances(self) -> None:
        for (aid, inst, kind, ref, detail, sens) in P.ACCOUNTS:
            path = f"finances/{_slug(inst + '-' + kind)}"
            ns = "pcp.finance" if sens == "sensitive" else None
            body = f"{kind.capitalize()} with {inst}. Reference {ref}.\n\n{detail.capitalize()}."
            self.add(Page(
                path=path, title=f"{inst} — {kind}", updated=self._date(),
                type="semantic", domain="finances", body=body,
                tags=["finances", _slug(inst), _slug(kind)],
                sensitivity=sens, namespace=ns, lifecycle="active", confidence=0.93,
                source={"origin": "user"},
            ))
            for pred, val in [("institution", inst), ("reference", ref), ("kind", kind)]:
                self.fact(id=f"account.{aid}.{pred}", domain="finances",
                          subject=f"{inst} {kind}", predicate=pred, obj=val,
                          page=path, sensitivity=sens, namespace=ns)

    # -------------------------------------------------------------- health --
    def build_health(self) -> None:
        for (hid, label, detail, clin, since, until, sens) in P.HEALTH:
            path = f"health/{_slug(label)}"
            clin_name = PEOPLE_BY_ID[clin][1]
            lifecycle = "archived" if until else "active"
            body = f"{label.capitalize()}. {detail.capitalize()}.\n\nUnder {clin_name}."
            self.add(Page(
                path=path, title=label.capitalize(), updated=self._date(),
                type="semantic", domain="health", body=body,
                tags=["health", _slug(label)], sensitivity="sensitive",
                namespace="pcp.health", lifecycle=lifecycle,
                valid_from=since, valid_until=until, confidence=0.96,
                source={"origin": "user"},
            ))
            self.fact(id=f"health.{hid}.detail", domain="health", subject=label,
                      predicate="detail", obj=detail, page=path,
                      sensitivity="sensitive", namespace="pcp.health",
                      lifecycle=lifecycle, valid_from=since, valid_until=until)
            self.fact(id=f"health.{hid}.clinician", domain="health", subject=label,
                      predicate="clinician", obj=clin_name, page=path,
                      sensitivity="sensitive", namespace="pcp.health",
                      lifecycle=lifecycle)

    # -------------------------------------------------------------- travel --
    def build_travel(self) -> None:
        for (tid, dest, country, purpose, start, end, withs, note) in P.TRIPS:
            path = f"travel/{start[:7]}-{_slug(dest)}"
            names = ", ".join(PEOPLE_BY_ID[w][1] for w in withs)
            lifecycle = "archived" if end < TODAY else "active"
            body = (
                f"{purpose.capitalize()} in {dest}, {country}. {start} to {end}.\n\n"
                f"Travelling with {names}. {note.capitalize()}."
            )
            self.add(Page(
                path=path, title=f"{dest} — {purpose}", updated=self._date(),
                type="episodic", domain="travel", body=body,
                tags=["travel", _slug(dest), _slug(purpose)],
                lifecycle=lifecycle, valid_from=start, valid_until=end, confidence=0.9,
                source={"origin": "connector", "client": "calendar"},
            ))
            for pred, val in [("destination", dest), ("country", country),
                              ("purpose", purpose), ("start", start), ("end", end),
                              ("companions", names)]:
                self.fact(id=f"trip.{tid}.{pred}", domain="travel",
                          subject=f"{dest} trip", predicate=pred, obj=val, page=path,
                          lifecycle=lifecycle, valid_from=start, valid_until=end)

    # --------------------------------------------------------- preferences --
    def build_preferences(self) -> None:
        for (pid, area, stmt, strength) in P.PREFERENCES:
            path = f"preferences/{pid}"
            body = f"{stmt.capitalize()}.\n\nHeld {strength}ly; applies across contexts."
            self.add(Page(
                path=path, title=f"Preference — {area}", updated=self._date(),
                type="procedural" if area in ("ai", "work") else "semantic",
                domain="preferences", body=body, tags=["preferences", area],
                lifecycle="validated" if strength == "strong" else "active",
                confidence=0.98 if strength == "strong" else 0.8,
                source={"origin": "chat"},
            ))
            self.fact(id=f"pref.{pid}", domain="preferences", subject=area,
                      predicate="preference", obj=stmt, page=path)

    # ---------------------------------------------------------------- home --
    def build_home(self) -> None:
        for (hid, label, detail, sens, ns) in P.HOME:
            path = f"home/{_slug(label)}"
            body = f"{label.capitalize()}: {detail}."
            self.add(Page(
                path=path, title=label.capitalize(), updated=self._date(),
                type="semantic", domain="home", body=body,
                tags=["home", _slug(label)], sensitivity=sens, namespace=ns,
                lifecycle="active", confidence=0.94, source={"origin": "user"},
            ))
            self.fact(id=f"home.{hid}", domain="home", subject=label,
                      predicate="detail", obj=detail, page=path,
                      sensitivity=sens, namespace=ns)

    # =====================================================================
    # Designed cases. These carry the gold answers for the harder strata.
    # =====================================================================

    # -- T-a: supersession pairs -----------------------------------------
    # BOTH pages stay `active` with open validity, so the SPEC.md §5.2
    # default filter shows both and does NOT resolve the conflict. The only
    # discriminator is the `supersedes` edge on the newer page (NOTES.md §2.1).
    SUPERSESSION = [
        dict(key="role", domain="work", tags=["work", "role"],
             old_path="work/role-senior-data-engineer",
             old_title="Role at Nordvik Analytics",
             old_body="Mara's title at Nordvik Analytics is Senior Data Engineer. "
                      "She sits in the Data Platform group.",
             new_path="work/role-principal-data-engineer",
             new_title="Role at Nordvik Analytics",
             new_body="Mara's title at Nordvik Analytics is Principal Data Engineer. "
                      "She sits in the Data Platform group.",
             subject="Mara", predicate="job title", gold="Principal Data Engineer",
             stale_gold="Senior Data Engineer"),
        dict(key="reporting", domain="work", tags=["work", "reporting-line"],
             old_path="work/reporting-line-adeyemi",
             old_title="Reporting line",
             old_body="Mara reports to Olu Adeyemi, engineering manager, "
                      "with a fortnightly one-to-one.",
             new_path="work/reporting-line-hallgren",
             new_title="Reporting line",
             new_body="Mara reports to Petra Hallgren, VP Engineering, "
                      "with a fortnightly one-to-one.",
             subject="Mara", predicate="manager", gold="Petra Hallgren",
             stale_gold="Olu Adeyemi"),
        dict(key="steering", domain="projects", tags=["projects", "tidewater", "governance"],
             old_path="projects/tidewater/steering-chair-tuominen",
             old_title="Tidewater steering group chair",
             old_body="The Tidewater steering group is chaired by Mira Tuominen. "
                      "It meets on the first Tuesday of the month.",
             new_path="projects/tidewater/steering-chair-nordgren",
             new_title="Tidewater steering group chair",
             new_body="The Tidewater steering group is chaired by Elin Nordgren. "
                      "It meets on the first Tuesday of the month.",
             subject="Tidewater steering group", predicate="chair", gold="Elin Nordgren",
             stale_gold="Mira Tuominen"),
        dict(key="laptop", domain="work", tags=["work", "equipment"],
             old_path="work/laptop-macbook-pro",
             old_title="Work laptop",
             old_body="Mara's work laptop is a MacBook Pro 14, issued by Nordvik IT. "
                      "Asset tag NV-2291.",
             new_path="work/laptop-framework-16",
             new_title="Work laptop",
             new_body="Mara's work laptop is a Framework 16, issued by Nordvik IT. "
                      "Asset tag NV-4417.",
             subject="Mara", predicate="work laptop", gold="Framework 16",
             stale_gold="MacBook Pro 14"),
    ]

    # -- T-b: overlapping validity windows --------------------------------
    # Both pages are `active` AND current, so both survive the default
    # filter. Correctness depends on interval containment, nothing else.
    WINDOWS = [
        dict(key="parking", domain="home", tags=["home", "parking"],
             subject="parking space", predicate="entitlement",
             ask_date="2026-01-15", gold="courtyard space 14",
             options=[
                 dict(path="home/parking-courtyard", title="Parking — courtyard",
                      body="Parking permit for courtyard space 14, Kommendorsgatan. "
                           "Billed quarterly by the housing association.",
                      valid_from="2025-09-01", valid_until="2026-12-31",
                      answer="courtyard space 14"),
                 dict(path="home/parking-garage", title="Parking — garage",
                      body="Parking permit for garage bay G7 under the block. "
                           "Billed quarterly by the housing association.",
                      valid_from="2026-06-01", valid_until="2027-05-31",
                      answer="garage bay G7"),
             ]),
        dict(key="mobile", domain="work", tags=["work", "mobile"],
             subject="mobile number", predicate="operator",
             ask_date="2026-03-20", gold="Telia",
             options=[
                 dict(path="work/mobile-telia", title="Mobile plan — Telia",
                      body="Mara's mobile number runs on Telia, business tariff, "
                           "billed to Nordvik Analytics.",
                      valid_from="2024-03-01", valid_until="2026-10-31",
                      answer="Telia"),
                 dict(path="work/mobile-tre", title="Mobile plan — Tre",
                      body="Mara's mobile number runs on Tre, business tariff, "
                           "billed to Nordvik Analytics.",
                      valid_from="2026-09-01", valid_until="2028-08-31",
                      answer="Tre"),
             ]),
        dict(key="pool", domain="preferences", tags=["preferences", "exercise"],
             subject="pool membership", predicate="venue",
             ask_date="2026-02-10", gold="Valhallabadet",
             options=[
                 dict(path="preferences/pool-valhallabadet", title="Pool membership — Valhallabadet",
                      body="Swimming membership at Valhallabadet. Mornings, twice a week.",
                      valid_from="2025-01-01", valid_until="2026-12-31",
                      answer="Valhallabadet"),
                 dict(path="preferences/pool-frolundabadet", title="Pool membership — Frolundabadet",
                      body="Swimming membership at Frolundabadet, taken out for the "
                           "children's lessons. Weekends.",
                      valid_from="2026-05-01", valid_until="2027-04-30",
                      answer="Frolundabadet"),
             ]),
    ]

    # -- T-c: historical facts, reachable only via the opt-in override -----
    HISTORICAL = [
        dict(key="mortgage_rate", domain="finances", tags=["finances", "mortgage"],
             old=dict(path="finances/mortgage-rate-2023", title="Majorna mortgage rate",
                      body="The Majorna mortgage is fixed at 1.94 per cent. "
                           "Renegotiation due at the end of the term.",
                      lifecycle="stale", valid_from="2023-12-01", valid_until="2025-11-30"),
             new=dict(path="finances/mortgage-rate-2025", title="Majorna mortgage rate",
                      body="The Majorna mortgage is fixed at 3.42 per cent. "
                           "Renegotiation due at the end of the term.",
                      lifecycle="active", valid_from="2025-12-01", valid_until=None),
             sensitivity="sensitive", namespace="pcp.finance",
             subject="Majorna mortgage", predicate="previous interest rate",
             gold="1.94 per cent", change_date="2025-12-01"),
        dict(key="bank", domain="finances", tags=["finances", "banking"],
             old=dict(path="finances/bank-swedbank", title="Everyday bank",
                      body="Everyday banking is with Swedbank. Salary and household "
                           "payments both run through it.",
                      lifecycle="archived", valid_from="2012-08-01", valid_until="2021-03-31"),
             new=dict(path="finances/bank-handelsbanken", title="Everyday bank",
                      body="Everyday banking is with Handelsbanken. Salary and household "
                           "payments both run through it.",
                      lifecycle="active", valid_from="2021-04-01", valid_until=None),
             sensitivity="normal", namespace=None,
             subject="everyday banking", predicate="previous bank",
             gold="Swedbank", change_date="2021-04-01"),
    ]

    def build_designed(self) -> None:
        # --- T-a supersession pairs
        for spec in self.SUPERSESSION:
            self.add(Page(
                path=spec["old_path"], title=spec["old_title"], updated="2025-06-14",
                type="semantic", domain=spec["domain"], body=spec["old_body"],
                tags=spec["tags"], lifecycle="active", confidence=0.9,
                source={"origin": "chat"},
            ))
            self.add(Page(
                path=spec["new_path"], title=spec["new_title"], updated="2026-08-02",
                type="semantic", domain=spec["domain"], body=spec["new_body"],
                tags=spec["tags"], lifecycle="active", confidence=0.95,
                source={"origin": "chat"},
                derived_from=[spec["old_path"]],
                relations=[{"rel": "supersedes", "target": spec["old_path"], "confidence": 0.95}],
            ))
            self.fact(id=f"sup.{spec['key']}.current", domain=spec["domain"],
                      subject=spec["subject"], predicate=spec["predicate"],
                      obj=spec["gold"], page=spec["new_path"],
                      supersedes=spec["old_path"])
            self.fact(id=f"sup.{spec['key']}.former", domain=spec["domain"],
                      subject=spec["subject"], predicate="former " + spec["predicate"],
                      obj=spec["stale_gold"], page=spec["old_path"])

        # --- T-b overlapping windows
        for spec in self.WINDOWS:
            for opt in spec["options"]:
                self.add(Page(
                    path=opt["path"], title=opt["title"], updated="2026-06-20",
                    type="semantic", domain=spec["domain"], body=opt["body"],
                    tags=spec["tags"], lifecycle="active", confidence=0.93,
                    valid_from=opt["valid_from"], valid_until=opt["valid_until"],
                    source={"origin": "user"},
                ))
                self.fact(id=f"win.{spec['key']}.{_slug(opt['answer'])}", domain=spec["domain"],
                          subject=spec["subject"], predicate=spec["predicate"],
                          obj=opt["answer"], page=opt["path"],
                          valid_from=opt["valid_from"], valid_until=opt["valid_until"])

        # --- T-c historical
        for spec in self.HISTORICAL:
            o, n = spec["old"], spec["new"]
            self.add(Page(
                path=o["path"], title=o["title"], updated="2025-01-20",
                type="semantic", domain=spec["domain"], body=o["body"],
                tags=spec["tags"], lifecycle=o["lifecycle"],
                valid_from=o["valid_from"], valid_until=o["valid_until"],
                sensitivity=spec["sensitivity"], namespace=spec["namespace"],
                confidence=0.92, source={"origin": "user"},
            ))
            self.add(Page(
                path=n["path"], title=n["title"], updated="2026-01-08",
                type="semantic", domain=spec["domain"], body=n["body"],
                tags=spec["tags"], lifecycle=n["lifecycle"],
                valid_from=n["valid_from"], valid_until=n["valid_until"],
                sensitivity=spec["sensitivity"], namespace=spec["namespace"],
                confidence=0.95, source={"origin": "user"},
                derived_from=[o["path"]],
                relations=[{"rel": "supersedes", "target": o["path"], "confidence": 0.97}],
            ))
            self.fact(id=f"hist.{spec['key']}", domain=spec["domain"],
                      subject=spec["subject"], predicate=spec["predicate"],
                      obj=spec["gold"], page=o["path"], lifecycle=o["lifecycle"],
                      valid_from=o["valid_from"], valid_until=o["valid_until"],
                      sensitivity=spec["sensitivity"], namespace=spec["namespace"])

    # -- Paraphrase targets ----------------------------------------------
    # The page body and the question that targets it share ZERO content
    # tokens (asserted in validate()). The gold answer may appear in the
    # body -- it is the QUESTION that must not overlap.
    PARAPHRASE = [
        dict(key="dinghy", path="home/boathouse", title="At the boathouse",
             domain="home", tags=["home", "cabin"],
             body="A small wooden rowing craft sits under tarpaulin beside the "
                  "boathouse. Its name, painted across the transom, is Vitsippa.",
             question="What is Mara's dinghy called?",
             gold="Vitsippa", aliases=["the Vitsippa"]),
        dict(key="recycling", path="home/courtyard-collections", title="Courtyard collections",
             domain="home", tags=["home", "building"],
             body="Refuse and sorted material leave the courtyard early each "
                  "Wednesday; the caretaker moves the containers the evening prior.",
             question="What day is rubbish collected at the flat?",
             gold="Wednesday", aliases=["Wednesdays"]),
        dict(key="seat", path="travel/aloft", title="Aloft",
             domain="travel", tags=["travel"],
             body="On any flight she asks for a place beside the gangway, never "
                  "against the porthole — easier to rise and stretch stiff wrists.",
             question="Which seat does Mara book on planes?",
             gold="an aisle seat", aliases=["aisle", "by the gangway", "gangway"]),
        dict(key="kora", path="preferences/instrument", title="Practice",
             domain="preferences", tags=["leisure"],
             body="Twice a month she lifts the kora down from its case and works "
                  "through pieces Kwame taught her.",
             question="Which musical instrument does Mara play?",
             gold="the kora", aliases=["kora"]),
        dict(key="assembly", path="home/evacuation", title="If the building empties",
             domain="home", tags=["home", "safety"],
             body="Should the block be evacuated, the household gathers by the "
                  "chestnut tree at the far end of the courtyard.",
             question="Where does Mara's family regroup during a fire?",
             gold="by the chestnut tree at the end of the courtyard",
             aliases=["the chestnut tree"]),
        dict(key="tallyho", path="work/internal-utility", title="Side responsibility",
             domain="work", tags=["work", "tooling"],
             body="She looks after a small internal utility that reconciles "
                  "warehouse counts overnight; colleagues refer to it as Tallyho.",
             question="What is the in-house program Mara maintains called?",
             gold="Tallyho", aliases=[]),
        dict(key="bakery", path="preferences/loaves", title="Loaves",
             domain="preferences", tags=["food"],
             body="Loaves come from the bakery on Karl Johansgatan, the one with "
                  "the blue awning, every second morning.",
             question="Which shop does Mara get her bread from?",
             gold="the bakery on Karl Johansgatan",
             aliases=["Karl Johansgatan bakery"]),
        dict(key="cloud", path="work/platform-footprint", title="Platform footprint",
             domain="work", tags=["work", "infrastructure"],
             body="Everything at Nordvik runs on Amazon's platform; the migration "
                  "off the old racks finished two winters ago.",
             question="Which cloud vendor does Mara's employer use?",
             gold="AWS", aliases=["Amazon", "Amazon Web Services", "Amazon's platform"]),
        dict(key="climbing", path="people/notes/elder-child-saturdays", title="Saturdays",
             domain="people", tags=["family"],
             body="The elder child spends Saturday mornings at the climbing hall "
                  "in Gamlestaden and has done since she was seven.",
             question="What activity does Nell do at weekends?",
             gold="climbing", aliases=["bouldering", "climbing hall"]),
        dict(key="tyres", path="vehicles/seasonal-rubber", title="Seasonal rubber",
             domain="vehicles", tags=["vehicles", "maintenance"],
             body="Winter rubber goes onto the estate in the opening week of "
                  "November and comes off around Easter.",
             question="When does Mara swap her car tyres?",
             gold="the first week of November", aliases=["November", "early November"]),
    ]

    # -- Oblique traces ---------------------------------------------------
    # Default-visible pages that HINT at a restricted fact without stating
    # it. They make the scope_restricted stratum a real test: the topic is
    # visibly present, the answer is not. Naming the withheld fact is a leak.
    TRACES = [
        ("calendar/2026-09-appointment", "Afternoon blocked", "work",
         "Appointment at the Sahlberg Clinic, 14:00, with Dr. Selma Ferreira. "
         "Blocked the rest of the afternoon; back online by 16:30."),
        ("home/thursday-reminder", "Thursday reminder", "home",
         "Recurring Thursday evening reminder: take the weekly tablet, then the "
         "follow-up one on Friday morning."),
        ("family/school-forms", "School forms", "people",
         "Consent form for the school trip returned. Allergy box completed as usual, "
         "same as last year."),
        ("finances/standing-orders", "Standing orders", "finances",
         "Standing orders leave on the 25th each month: household, the savings pot, "
         "and the children's transfers."),
        ("home/cabin-paperwork", "Cabin paperwork", "home",
         "Cabin paperwork lives in the green folder in the hall cupboard, with the "
         "survey and the loan documents."),
        ("home/flat-notes", "About the flat", "home",
         "Fourth floor, no lift. The stairs are the workout. South-facing balcony."),
        ("home/away-cover", "Cover when away", "home",
         "Stig looks in when we are away — plants, post, and Bruno. Arranged each time "
         "by text."),
        ("home/morning-routine", "Mornings", "home",
         "Morning tablet before breakfast, then filter coffee, then the school run."),
        ("finances/payday", "Payday", "finances",
         "Payday is the 25th. The monthly investment transfer goes out automatically "
         "the same evening."),
        ("legal/appointment-note", "Meeting in town", "work",
         "Meeting in town on the 12th about the paperwork. An hour should be enough; "
         "bring the folder."),
    ]

    LEGAL = [
        ("legal/solicitor", "Solicitor of record", "pcp.legal",
         "Cecilia Bratt of Bratt & Soner acts for Mara on property matters. "
         "Instructed since 2019."),
        ("legal/cabin-title", "Cabin title", "pcp.legal",
         "Title to the Smogen cabin is held jointly with Sofie Lindqvist. "
         "Deed lodged with Bratt & Soner."),
        ("legal/will", "Will", "pcp.legal",
         "Mirror wills executed with Idris in 2022. Cecilia Bratt holds the originals."),
        ("legal/boundary", "Boundary matter", "pcp.legal",
         "Boundary question with the neighbouring plot at Smogen, opened 2026-02. "
         "Cecilia Bratt is corresponding with the other side's solicitor."),
    ]

    def build_paraphrase(self) -> None:
        for spec in self.PARAPHRASE:
            self.add(Page(
                path=spec["path"], title=spec["title"], updated="2026-05-11",
                type="semantic", domain=spec["domain"], body=spec["body"],
                tags=spec["tags"], lifecycle="active", confidence=0.9,
                source={"origin": "chat"},
            ))
            self.fact(id=f"para.{spec['key']}", domain=spec["domain"],
                      subject=spec["title"], predicate="detail", obj=spec["gold"],
                      page=spec["path"], aliases=list(spec["aliases"]))

    def build_traces(self) -> None:
        for path, title, domain, body in self.TRACES:
            self.add(Page(
                path=path, title=title, updated=self._date(), type="episodic",
                domain=domain, body=body, tags=["note"], lifecycle="active",
                confidence=0.85, source={"origin": "chat"},
            ))

    def build_legal(self) -> None:
        for path, title, ns, body in self.LEGAL:
            self.add(Page(
                path=path, title=title, updated=self._date(), type="semantic",
                domain="home", body=body, tags=["legal"], sensitivity="sensitive",
                namespace=ns, lifecycle="active", confidence=0.95,
                source={"origin": "user"},
            ))
        self.fact(id="legal.solicitor", domain="home", subject="legal matters",
                  predicate="solicitor", obj="Cecilia Bratt", page="legal/solicitor",
                  sensitivity="sensitive", namespace="pcp.legal",
                  aliases=["Cecilia Bratt of Bratt & Soner", "Bratt & Soner"])

    # -- Noise -------------------------------------------------------------
    DESIGNED_PREFIXES = ("work/role-", "work/reporting-", "work/laptop-", "work/mobile-",
                         "projects/tidewater/steering-", "home/parking-",
                         "preferences/pool-", "finances/mortgage-rate-",
                         "finances/bank-", "legal/")

    def build_near_duplicates(self, n: int = 45) -> None:
        """Near-duplicate pages: same fact, reworded, lower confidence."""
        pool = [p for p in self.pages
                if p.type == "semantic"
                and not p.path.startswith(self.DESIGNED_PREFIXES)
                and p.path not in {s["path"] for s in self.PARAPHRASE}]
        for src in self.rng.sample(pool, min(n, len(pool))):
            lead = self.rng.choice([
                "Noted again, from a later conversation:",
                "Repeated in passing:",
                "Restated during a clear-out of old notes:",
                "Same detail, recorded separately:",
            ])
            self.add(Page(
                path=f"{src.path}-dup", title=f"{src.title} (duplicate note)",
                updated=self._date(), type=src.type, domain=src.domain,
                body=f"{lead}\n\n{src.body}", tags=list(src.tags) + ["duplicate"],
                sensitivity=src.sensitivity, namespace=src.namespace,
                lifecycle=self.rng.choice(["active", "stale"]),
                confidence=round(self.rng.uniform(0.55, 0.8), 2),
                source={"origin": "chat"},
                derived_from=[src.path],
                relations=[{"rel": "refines", "target": src.path}],
            ))

    def build_work_misc(self) -> None:
        items = [
            ("work/standup-time", "Standup is at 09:45 CET, fifteen minutes, camera optional."),
            ("work/oncall", "On-call rotation is one week in six, shared with the platform group."),
            ("work/expenses", "Expenses go through Nordvik's portal within thirty days."),
            ("work/holiday-allowance", "Thirty days of annual leave plus the Swedish public holidays."),
            ("work/review-cycle", "Performance reviews run in March and September."),
            ("work/office", "Nordvik's Gothenburg office is at Lindholmspiren, third floor."),
            ("work/remote", "Two office days a week, usually Tuesday and Thursday."),
            ("work/parking-work", "No parking at Lindholmspiren; the tram from Stigbergstorget takes eleven minutes."),
            ("work/security-training", "Annual security training due each November."),
            ("work/vpn", "VPN is required for anything touching client data."),
            ("work/conference-budget", "Twenty thousand SEK a year for conferences and books."),
            ("work/mentoring", "Mara mentors two junior engineers, rotating each half year."),
            ("work/hiring", "Sits on the hiring loop for data engineering roles."),
            ("work/incident-process", "Incidents are declared in #inc, severity set by the on-call."),
            ("work/data-retention", "Client data is retained for the contract term plus ninety days."),
        ]
        for path, body in items:
            self.add(Page(
                path=path, title=path.split("/")[-1].replace("-", " ").capitalize(),
                updated=self._date(), type="procedural", domain="work", body=body,
                tags=["work"], lifecycle=self.rng.choice(["active", "validated"]),
                confidence=0.9, source={"origin": "chat"},
            ))
            self.fact(id=f"work.{_slug(path)}", domain="work", subject=path.split("/")[-1],
                      predicate="detail", obj=body, page=path)

    def build_procedural(self) -> None:
        items = [
            ("procedures/school-run", "School run: leave at 08:05, tram 3 to Kvarnberget, back by 08:50."),
            ("procedures/cabin-opening", "Opening the cabin: water on at the stopcock, check the flue, air it for a day."),
            ("procedures/cabin-closing", "Closing the cabin: drain the pipes, shutters down, key back to the hook."),
            ("procedures/backup", "Laptop backs up to the NAS nightly; the NAS mirrors weekly to an offsite disk."),
            ("procedures/tax-return", "Tax return filed in April; Yusuf Halim reviews before submission."),
            ("procedures/bruno-meds", "Bruno's renal food twice daily; repeat order from Palm Veterinar every six weeks."),
            ("procedures/bike-service", "Cargo bikes serviced each March before the season."),
            ("procedures/passport", "Passports checked every January for expiry inside six months."),
            ("procedures/grocery", "Grocery order placed Thursday, delivered Friday between 17:00 and 19:00."),
            ("procedures/winter-prep", "Winter prep: tyres, screenwash, and the cabin shutters, all in one weekend."),
            ("procedures/handover", "Project handover: runbook, on-call contacts, and a recorded walkthrough."),
            ("procedures/onboarding", "New engineers get a buddy, a starter ticket, and access on day one."),
            ("procedures/pr-review", "Pull requests: one approval for internal, two for anything client-facing."),
            ("procedures/incident-writeup", "Incident write-up within five working days, blameless format."),
            ("procedures/holiday-booking", "Holiday booked in the portal, then added to the team calendar."),
            ("procedures/expense-claim", "Photograph the receipt, upload same day, categorise later."),
            ("procedures/birthday", "Birthdays: a book, wrapped, plus something small the children choose."),
            ("procedures/hosting", "Hosting: vegetarian main, always, so nobody has to ask."),
        ]
        for path, body in items:
            self.add(Page(
                path=path, title=path.split("/")[-1].replace("-", " ").capitalize(),
                updated=self._date(), type="procedural", domain="preferences",
                body=body, tags=["procedure"], lifecycle="validated", confidence=0.92,
                source={"origin": "chat"},
            ))
            self.fact(id=f"proc.{_slug(path)}", domain="preferences",
                      subject=path.split("/")[-1], predicate="procedure", obj=body, page=path)

    FILLER_TEMPLATES = [
        "Quiet day. {a} and {b} came up in conversation; nothing to action.",
        "Rescheduled the call with {a}. New slot next week.",
        "Read a long piece about {topic}. Worth revisiting.",
        "{a} sent over notes from the session. Skimmed, will read properly later.",
        "Errand day: post office, then the hardware shop for {thing}.",
        "Slow morning. Coffee, then two hours on {topic} without interruption.",
        "Short call with {a} about scheduling. Nothing decided.",
        "Tidied the notes directory. Merged a few near-identical entries.",
        "{a} recommended a book on {topic}. Added to the list.",
        "Weather turned. Cancelled the ride, worked from the kitchen table instead.",
        "Picked up {thing} on the way home. Cheaper than expected.",
        "Long thread with {a} and {b}; resolved without a meeting.",
    ]
    FILLER_TOPICS = ["stream processing", "Nordic archives", "urban cycling", "bread making",
                     "kora tuning", "tidal modelling", "column stores", "Swedish grammar",
                     "cold-water swimming", "typography", "orchard grafting", "seabird counts",
                     "energy tariffs", "wooden boats", "risk models", "school reform"]
    FILLER_THINGS = ["a new kettle", "hinges", "seed trays", "a bicycle light", "picture hooks",
                     "sandpaper", "a torch", "cable ties", "a doormat", "gaffer tape"]

    def build_filler(self, n: int = 220) -> None:
        names = [p[1] for p in P.PEOPLE]
        for i in range(n):
            a, b = self.rng.sample(names, 2)
            body = self.rng.choice(self.FILLER_TEMPLATES).format(
                a=a, b=b, topic=self.rng.choice(self.FILLER_TOPICS),
                thing=self.rng.choice(self.FILLER_THINGS))
            d = self._date("2024-06-01", TODAY)
            self.add(Page(
                path=f"journal/{d}-{i:03d}", title=f"Journal — {d}", updated=d,
                type="episodic", domain="preferences", body=body, tags=["journal"],
                lifecycle=self.rng.choices(["active", "stale", "archived"], [6, 3, 1])[0],
                confidence=round(self.rng.uniform(0.4, 0.75), 2),
                source={"origin": "chat"},
            ))

    # ------------------------------------------------------------ profile --
    def build_profile(self) -> dict[str, dict]:
        """SPEC.md §4: core profile + four extension namespaces."""
        core = {
            "name": P.PERSONA["name"],
            "preferred_name": P.PERSONA["preferred_name"],
            "pronouns": P.PERSONA["pronouns"],
            "languages": [
                {"code": "sv", "level": "native", "rule": "at home with the children"},
                {"code": "en", "level": "native", "rule": "at work, and for AI output"},
                {"code": "tw", "level": "conversational", "rule": "with Kwame on calls"},
            ],
            "locale": P.PERSONA["locale"],
            "timezone": P.PERSONA["timezone"],
            "location": {"city": P.PERSONA["city"], "country": P.PERSONA["country"]},
            "communication": {
                "tone": "direct, unhurried",
                "verbosity": "prose over bullet lists for anything long-form",
                "formatting": "metric units, ISO-8601 dates, no emoji",
            },
            "work": {
                "employer": P.PERSONA["employer"],
                "role": P.PERSONA["role"],
                "group": "Data Platform",
            },
            "ai_instructions": (
                "Answer in British English. Do not schedule anything before 09:30. "
                "Never send notifications between 21:00 and 07:00."
            ),
        }
        health = {
            "conditions": [
                {"label": h[1], "since": h[4], "clinician": PEOPLE_BY_ID[h[3]][1]}
                for h in P.HEALTH if h[5] is None and "allerg" not in h[1] and "intoler" not in h[1]
            ],
            "allergies": [
                {"substance": "penicillin", "reaction": "rash", "documented": "1994-06-01"},
                {"substance": "shellfish", "reaction": "intolerance, not anaphylactic"},
            ],
            "providers": [
                {"name": "Dr. Selma Ferreira", "speciality": "rheumatology", "clinic": "Sahlberg Clinic"},
                {"name": "Dr. Anders Lindholm", "speciality": "general practice", "clinic": "Vastkust Vardcentral"},
                {"name": "Dr. Ada Okonkwo", "speciality": "endocrinology", "clinic": "Sahlberg Clinic"},
            ],
        }
        finance = {
            "accounts": [
                {"institution": a[1], "kind": a[2], "reference": a[3]}
                for a in P.ACCOUNTS
            ],
            "advisors": [{"name": "Yusuf Halim", "role": "accountant", "firm": "Halim Revision"}],
            "obligations": [
                {"kind": "mortgage", "property": "flat in Majorna", "rate": "3.42 per cent", "since": "2025-12-01"},
                {"kind": "mortgage", "property": "cabin at Smogen", "lender": "Lansforsakringar"},
            ],
        }
        home = {
            "addresses": [
                {"label": "flat", "city": "Gothenburg", "district": "Majorna",
                 "size_sqm": 78, "floor": 4, "lift": False},
                {"label": "cabin", "city": "Smogen", "heating": "wood"},
            ],
            "household": [PEOPLE_BY_ID[x][1] for x in ("idris", "nell", "theo")],
            "vehicles": [{"make": v[1], "model": v[2], "year": v[3], "colour": v[4],
                          "registration": v[5], "status": v[6]} for v in P.VEHICLES],
            "spare_keys": "one set with Stig Ohman, one at the cabin",
        }
        legal = {
            "solicitor": {"name": "Cecilia Bratt", "firm": "Bratt & Soner", "since": "2019"},
            "matters": [
                {"label": "cabin title", "status": "held jointly with Sofie Lindqvist"},
                {"label": "boundary question at Smogen", "opened": "2026-02", "status": "open"},
            ],
            "instruments": [{"kind": "mirror wills", "executed": "2022", "held_by": "Bratt & Soner"}],
        }
        return {"profile.core": core, "pcp.health": health, "pcp.finance": finance,
                "pcp.home": home, "pcp.legal": legal}

    # ----------------------------------------------------------- assemble --
    def build_index(self) -> None:
        by_domain: dict[str, int] = {}
        for p in self.pages:
            by_domain[p.domain] = by_domain.get(p.domain, 0) + 1
        lines = ["# Memory index", "",
                 f"{len(self.pages)} pages across {len(by_domain)} domains.", ""]
        for d in sorted(by_domain):
            lines.append(f"- `{d}/` — {by_domain[d]} pages")
        self.pages.insert(0, Page(
            path="_index", title="Memory index", updated=TODAY, type="semantic",
            domain="preferences", body="\n".join(lines), tags=["index"],
            lifecycle="validated", confidence=1.0, source={"origin": "user"},
        ))

    def build_all(self) -> None:
        for m in ("build_people", "build_projects", "build_vehicles", "build_finances",
                  "build_health", "build_travel", "build_preferences", "build_home",
                  "build_designed", "build_paraphrase", "build_traces", "build_legal",
                  "build_work_misc", "build_procedural", "build_near_duplicates",
                  "build_filler"):
            getattr(self, m)()
        self.build_index()

    # ----------------------------------------------------------- validate --
    def validate(self) -> list[str]:
        """Build-time assertions. Any failure aborts the build."""
        errs: list[str] = []
        paths = [p.path for p in self.pages]
        dupes = {p for p in paths if paths.count(p) > 1}
        if dupes:
            errs.append(f"duplicate page paths: {sorted(dupes)[:5]}")
        if not (500 <= len(self.pages) <= 800):
            errs.append(f"page count {len(self.pages)} outside the required 500-800")

        by_path = {p.path: p for p in self.pages}

        # relations must point at pages that exist
        for p in self.pages:
            for r in p.relations:
                if r["target"] not in by_path:
                    errs.append(f"{p.path}: relation target {r['target']} missing")
            for d in p.derived_from:
                if d not in by_path:
                    errs.append(f"{p.path}: derived_from {d} missing")

        # lifecycle must stay inside the SPEC.md §5.1 enum (NOTES.md §2.1)
        from .model import LIFECYCLES
        for p in self.pages:
            if p.lifecycle not in LIFECYCLES:
                errs.append(f"{p.path}: lifecycle {p.lifecycle!r} is not in SPEC.md §5.1")

        # T-a pairs: BOTH pages must survive the default filter, otherwise the
        # storage filter -- not the supersedes edge -- is doing the work.
        for spec in self.SUPERSESSION:
            for k in ("old_path", "new_path"):
                pg = by_path[spec[k]]
                if not pg.default_visible():
                    errs.append(f"T-a {spec['key']}: {pg.path} is hidden by the default "
                                f"filter; the edge would not be the discriminator")

        # T-b windows: every option must survive the default filter too.
        for spec in self.WINDOWS:
            for opt in spec["options"]:
                pg = by_path[opt["path"]]
                if not pg.default_visible():
                    errs.append(f"T-b {spec['key']}: {opt['path']} hidden by default filter")
            hit = [o for o in spec["options"]
                   if o["valid_from"] <= spec["ask_date"] <= (o["valid_until"] or "9999")]
            if len(hit) != 1:
                errs.append(f"T-b {spec['key']}: ask_date {spec['ask_date']} matches "
                            f"{len(hit)} windows, need exactly 1")
            elif hit[0]["answer"] != spec["gold"]:
                errs.append(f"T-b {spec['key']}: window answer {hit[0]['answer']!r} "
                            f"!= gold {spec['gold']!r}")

        # T-c historical: the answer page MUST be hidden by the default filter,
        # otherwise no opt-in is required.
        for spec in self.HISTORICAL:
            pg = by_path[spec["old"]["path"]]
            if pg.default_visible():
                errs.append(f"T-c {spec['key']}: {pg.path} is visible by default; "
                            f"no override needed, so it is not a temporal question")

        # Paraphrase: zero content-token overlap between question and page body.
        for spec in self.PARAPHRASE:
            pg = by_path[spec["path"]]
            q = content_tokens(spec["question"])
            b = content_tokens(pg.body) | content_tokens(pg.title)
            overlap = q & b
            if overlap:
                errs.append(f"paraphrase {spec['key']}: question shares "
                            f"{sorted(overlap)} with the target page")
        return errs

    # -------------------------------------------------------------- write --
    def write(self, root: Path) -> dict:
        from .model import SCOPE_BUNDLES, BUNDLE_NAMESPACES
        corpus_dir = root / "pages"
        if corpus_dir.exists():
            import shutil
            shutil.rmtree(corpus_dir)
        for p in self.pages:
            fp = corpus_dir / (p.path + ".md")
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(p.render(), encoding="utf-8")

        profile = self.build_profile()
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

        manifest = {
            "seed": SEED,
            "today": TODAY,
            "persona": P.PERSONA,
            "counts": {
                "pages": len(self.pages),
                "facts": len(self.facts),
                "by_domain": {d: sum(1 for p in self.pages if p.domain == d)
                              for d in sorted({p.domain for p in self.pages})},
                "by_lifecycle": {l: sum(1 for p in self.pages if p.lifecycle == l)
                                 for l in sorted({p.lifecycle for p in self.pages})},
                "default_visible": sum(1 for p in self.pages if p.default_visible()),
                "sensitive": sum(1 for p in self.pages if p.sensitivity == "sensitive"),
            },
            "pages": [
                {
                    "path": p.path, "title": p.title, "domain": p.domain,
                    "type": p.type, "lifecycle": p.lifecycle,
                    "sensitivity": p.sensitivity, "namespace": p.namespace,
                    "valid_from": p.valid_from, "valid_until": p.valid_until,
                    "confidence": p.confidence, "tags": p.tags,
                    "relations": p.relations, "derived_from": p.derived_from,
                    "updated": p.updated,
                    "default_visible": p.default_visible(),
                    "visible_in": [b for b in SCOPE_BUNDLES if visible_in(p, b)],
                    "body": p.body,
                }
                for p in self.pages
            ],
            "facts": [f.to_json() for f in self.facts],
            "profile_namespaces": list(profile),
            "designed": {
                "supersession": self.SUPERSESSION,
                "windows": self.WINDOWS,
                "historical": self.HISTORICAL,
                "paraphrase": self.PARAPHRASE,
                "traces": [t[0] for t in self.TRACES],
            },
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest


def main(root: str = "corpus", seed: int = SEED) -> dict:
    b = Builder(seed)
    b.build_all()
    errs = b.validate()
    if errs:
        raise SystemExit("corpus validation failed:\n  " + "\n  ".join(errs))
    m = b.write(Path(root))
    print(f"corpus: {m['counts']['pages']} pages, {m['counts']['facts']} facts, "
          f"{m['counts']['default_visible']} default-visible, "
          f"{m['counts']['sensitive']} sensitive")
    print("  by lifecycle:", m["counts"]["by_lifecycle"])
    return m


if __name__ == "__main__":
    main()
