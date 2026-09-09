"""Case (c) supersession: two pages that contradict, with NO marker.

The second-pass survey of two real memory stores (REPORT.md §8.1) found that
the commonest form of supersession is not an edge and not a lifecycle flag --
it is a whole page that has silently gone stale, contradicted by a newer page
somewhere else, with *nothing at all* linking the two.

These specs model exactly that, and are shared by BOTH corpora so the
`reconcile` stratum is the same question asked of two different shapes:

  * both pages are `active` with open validity -- the SPEC.md §5.2 default
    filter shows both
  * there is no `supersedes` edge, no `derived_from`, no `contradicts`
  * confidence is identical (corpus-a) or absent entirely (corpus-b)
  * the pages live in different directories and share no path prefix

That leaves at most two signals, and the specs deliberately split on which:

  `recency`  -- the current page has the later file-level `updated`. A reader
                who trusts mtime gets it right.
  `content`  -- `updated` is actively MISLEADING: the stale page was touched
                later (a reformat, a re-import) and carries the newer
                timestamp. The only thing that resolves it is a date stated
                inside the prose of the current page.

The `content` cases are the ones that matter. The first-pass follow-up
question was "do `updated` timestamps track currency, or does bulk import
stamp everything with the import date?" -- these are the corpus's answer to
"what if they don't".

Subjects are chosen to appear nowhere else in the persona tables, so a
`reconcile` question cannot be resolved by a corroborating page elsewhere.
"""
from __future__ import annotations

# key, domain, tags, subject, predicate, discriminator,
# current{path,title,body,updated}, stale{path,title,body,updated}, gold, stale_gold
RECONCILE = [
    # ---------------------------------------------------- recency-resolved --
    dict(key="dentist", domain="health", tags=["health", "dental"],
         subject="dental practice", predicate="provider", discriminator="recency",
         current=dict(path="health/dental-care",
                      title="Dental care",
                      body="Dental check-ups are at Tandvard Majorna on Saggatan. "
                           "Six-monthly, booked in January and July.",
                      updated="2026-06-12"),
         stale=dict(path="health/dentist-appointments",
                    title="Dentist appointments",
                    body="Dental check-ups are at Kliniken Linne on Linnegatan. "
                         "Six-monthly, booked in January and July.",
                    updated="2025-02-08"),
         gold="Tandvard Majorna",
         aliases=["Tandvard Majorna on Saggatan", "Tandvård Majorna"],
         stale_gold="Kliniken Linne"),

    dict(key="broadband", domain="home", tags=["home", "network"],
         subject="home broadband", predicate="provider", discriminator="recency",
         current=dict(path="home/broadband",
                      title="Broadband",
                      body="Broadband at the flat is with Bahnhof, 1000/1000 fibre, "
                           "billed monthly.",
                      updated="2026-07-19"),
         stale=dict(path="home/internet-connection",
                    title="Internet connection",
                    body="Broadband at the flat is with Telenor, 250/100 fibre, "
                         "billed monthly.",
                    updated="2025-03-22"),
         gold="Bahnhof", aliases=[], stale_gold="Telenor"),

    dict(key="breakdown", domain="vehicles", tags=["vehicles", "cover"],
         subject="roadside assistance", predicate="provider", discriminator="recency",
         current=dict(path="vehicles/roadside-assistance",
                      title="Roadside assistance",
                      body="Breakdown cover for both cars is with Assistanskaren, "
                           "renewed on the policy anniversary.",
                      updated="2026-05-30"),
         stale=dict(path="vehicles/breakdown-cover",
                    title="Breakdown cover",
                    body="Breakdown cover for both cars is with Falck Vagassistans, "
                         "renewed on the policy anniversary.",
                    updated="2024-11-14"),
         gold="Assistanskaren", aliases=["Assistanskåren"],
         stale_gold="Falck Vagassistans"),

    dict(key="optician", domain="health", tags=["health", "eyes"],
         subject="optician", predicate="provider", discriminator="recency",
         current=dict(path="health/eye-tests",
                      title="Eye tests",
                      body="Eye tests are at Synoptik at Frolunda Torg, every two "
                           "years, reading glasses only.",
                      updated="2026-04-27"),
         stale=dict(path="health/optician",
                    title="Optician",
                    body="Eye tests are at Smarteyes on Avenyn, every two years, "
                         "reading glasses only.",
                    updated="2024-09-19"),
         gold="Synoptik", aliases=["Synoptik at Frolunda Torg"],
         stale_gold="Smarteyes"),

    dict(key="passwords", domain="preferences", tags=["tooling", "security"],
         subject="password manager", predicate="product", discriminator="recency",
         current=dict(path="preferences/password-manager",
                      title="Password manager",
                      body="The household uses 1Password on a family plan; "
                           "five members, shared vault for the flat and the cabin.",
                      updated="2026-08-14"),
         stale=dict(path="work/credentials-tooling",
                    title="Credentials tooling",
                    body="The household uses Bitwarden on a family plan; "
                         "five members, shared vault for the flat and the cabin.",
                    updated="2025-05-06"),
         gold="1Password", aliases=["1Password family plan"],
         stale_gold="Bitwarden"),

    # ---------------------------------------------------- content-resolved --
    # `updated` is BACKWARDS here: the stale page was touched later.
    dict(key="coffee_sub", domain="preferences", tags=["food", "subscription"],
         subject="coffee subscription", predicate="roaster", discriminator="content",
         current=dict(path="preferences/coffee-subscription",
                      title="Coffee subscription",
                      body="From 2026-05-01 the coffee subscription runs with "
                           "Kafferosteriet Kaj -- 500 g of filter roast every "
                           "fortnight, delivered on a Tuesday.",
                      updated="2026-02-14"),
         stale=dict(path="preferences/coffee-delivery",
                    title="Coffee delivery",
                    body="The coffee subscription runs with Bonor och Bryggd -- "
                         "500 g of filter roast every fortnight, delivered on a "
                         "Tuesday.",
                    updated="2026-06-02"),
         gold="Kafferosteriet Kaj", aliases=["Kafferosteriet"],
         stale_gold="Bonor och Bryggd"),

    dict(key="cleaning", domain="home", tags=["home", "household"],
         subject="cleaning service", predicate="provider", discriminator="content",
         current=dict(path="home/cleaning-service",
                      title="Cleaning service",
                      body="Hemfrid took over the fortnightly clean on 2026-06-15. "
                           "Alternate Fridays, key left with the porter.",
                      updated="2026-03-08"),
         stale=dict(path="home/household-help",
                    title="Household help",
                    body="Stadpartner Vast does the fortnightly clean. Alternate "
                         "Fridays, key left with the porter.",
                    updated="2026-07-11"),
         gold="Hemfrid", aliases=[], stale_gold="Stadpartner Vast"),

    dict(key="bike_service", domain="vehicles", tags=["bicycles", "maintenance"],
         subject="bicycle servicing", predicate="workshop", discriminator="content",
         current=dict(path="vehicles/bicycle-servicing",
                      title="Bicycle servicing",
                      body="Since 2026-02-01 the bikes go to Cykelkraft on Andra "
                           "Langgatan for their annual service, cargo bikes included.",
                      updated="2025-12-20"),
         stale=dict(path="home/bike-workshop",
                    title="Bike workshop",
                    body="The bikes go to Velo Verkstad in Olskroken for their "
                         "annual service, cargo bikes included.",
                    updated="2026-04-05"),
         gold="Cykelkraft", aliases=["Cykelkraft on Andra Langgatan"],
         stale_gold="Velo Verkstad"),
]

# The five that carry questions in the run set: two recency, three content.
# Weighted towards `content` on purpose -- `recency` is the easy half, and a
# stratum built to break a ceiling should not be half-easy.
QUESTIONED = ["dentist", "broadband", "coffee_sub", "cleaning", "bike_service"]

QUESTIONS = {
    "dentist":      "Which dental practice does Mara go to?",
    "broadband":    "Which company provides the broadband at the flat?",
    "coffee_sub":   "Which roaster supplies Mara's coffee subscription?",
    "cleaning":     "Which firm does the fortnightly clean at the flat?",
    "bike_service": "Which workshop services the family's bicycles?",
}


def by_key() -> dict[str, dict]:
    return {s["key"]: s for s in RECONCILE}
