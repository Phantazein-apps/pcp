"""Synthetic persona: entity tables the corpus is generated from.

One persona, fully synthetic. Every value here is invented; no real person,
company, address, account or medical record is represented.
"""
from __future__ import annotations

PERSONA = {
    "name": "Mara Osei-Lindqvist",
    "preferred_name": "Mara",
    "pronouns": "she/her",
    "city": "Gothenburg",
    "country": "SE",
    "timezone": "Europe/Stockholm",
    "locale": "en-GB",
    "employer": "Nordvik Analytics",
    "role": "Principal Data Engineer",
}

# id, name, relation, org, city, role
PEOPLE = [
    ("idris",     "Idris Bello",          "partner",    "Kvarnberget Skola", "Gothenburg", "music teacher"),
    ("nell",      "Nell Osei-Lindqvist",  "child",      "Kvarnberget Skola", "Gothenburg", "pupil"),
    ("theo",      "Theo Osei-Lindqvist",  "child",      "Kvarnberget Skola", "Gothenburg", "pupil"),
    ("astrid",    "Astrid Lindqvist",     "mother",     "retired",           "Uppsala",    "retired archivist"),
    ("kwame",     "Kwame Osei",           "father",     "retired",           "Kumasi",     "retired surveyor"),
    ("sofie",     "Sofie Lindqvist",      "sister",     "Renhold AB",        "Malmo",      "logistics manager"),
    ("yaw",       "Yaw Osei",             "brother",    "Brightwater Ltd",   "London",     "civil engineer"),
    ("petra",     "Petra Hallgren",       "manager",    "Nordvik Analytics", "Gothenburg", "VP Engineering"),
    ("tomas",     "Tomas Ek",             "colleague",  "Nordvik Analytics", "Gothenburg", "staff engineer"),
    ("ingrid",    "Ingrid Saarinen",      "colleague",  "Nordvik Analytics", "Helsinki",   "data scientist"),
    ("rafael",    "Rafael Duarte",        "colleague",  "Nordvik Analytics", "Lisbon",     "platform engineer"),
    ("hanna",     "Hanna Brozek",         "colleague",  "Nordvik Analytics", "Krakow",     "design lead"),
    ("olu",       "Olu Adeyemi",          "colleague",  "Nordvik Analytics", "Gothenburg", "engineering manager"),
    ("mira",      "Mira Tuominen",        "colleague",  "Nordvik Analytics", "Helsinki",   "product manager"),
    ("bengt",     "Bengt Ahlgren",        "colleague",  "Nordvik Analytics", "Gothenburg", "SRE"),
    ("lucia",     "Lucia Ferrante",       "colleague",  "Nordvik Analytics", "Milan",      "analytics engineer"),
    ("dmitri",    "Dmitri Sokolov",       "colleague",  "Nordvik Analytics", "Tallinn",    "QA lead"),
    ("aisha",     "Aisha Rahman",         "colleague",  "Nordvik Analytics", "Gothenburg", "security engineer"),
    ("johan",     "Johan Wikstrom",       "client",     "Halvorsen Marine",  "Bergen",     "CTO"),
    ("elin",      "Elin Nordgren",        "client",     "Halvorsen Marine",  "Bergen",     "data lead"),
    ("markus",    "Markus Reinholt",      "client",     "Stellarcrest Bank", "Stockholm",  "head of risk"),
    ("priya",     "Priya Venkatesan",     "client",     "Stellarcrest Bank", "Stockholm",  "programme manager"),
    ("nils",      "Nils Bergqvist",       "client",     "Tallhojd Energi",   "Vasteras",   "operations director"),
    ("carmen",    "Carmen Ibarra",        "client",     "Tallhojd Energi",   "Vasteras",   "systems architect"),
    ("ferreira",  "Dr. Selma Ferreira",   "clinician",  "Sahlberg Clinic",   "Gothenburg", "rheumatologist"),
    ("lindholm",  "Dr. Anders Lindholm",  "clinician",  "Vastkust Vardcentral", "Gothenburg", "GP"),
    ("okonkwo",   "Dr. Ada Okonkwo",      "clinician",  "Sahlberg Clinic",   "Gothenburg", "endocrinologist"),
    ("bratt",     "Cecilia Bratt",        "professional", "Bratt & Soner",   "Gothenburg", "solicitor"),
    ("halim",     "Yusuf Halim",          "professional", "Halim Revision",  "Gothenburg", "accountant"),
    ("norrback",  "Peder Norrback",       "professional", "Norrback Bil",    "Molndal",    "mechanic"),
    ("vidal",     "Rosa Vidal",           "professional", "Vidal Fastighet", "Gothenburg", "letting agent"),
    ("stig",      "Stig Ohman",           "neighbour",  "-",                 "Gothenburg", "retired teacher"),
    ("bea",       "Beatrice Holm",        "friend",     "Gothenburg Univ.",  "Gothenburg", "lecturer"),
    ("noor",      "Noor Haddad",          "friend",     "Klarvatten AB",     "Gothenburg", "hydrologist"),
    ("frida",     "Frida Lund",           "friend",     "freelance",         "Oslo",       "illustrator"),
    ("emeka",     "Emeka Nwosu",          "friend",     "Brightwater Ltd",   "London",     "product designer"),
    ("lars",      "Lars Sundqvist",       "friend",     "Sundqvist Snickeri","Boras",      "carpenter"),
    ("greta",     "Greta Palm",           "friend",     "Palm Veterinar",    "Gothenburg", "veterinarian"),
    ("hugo",      "Hugo Ranta",           "colleague",  "Nordvik Analytics", "Helsinki",   "data engineer"),
    ("saskia",    "Saskia Vermeer",       "colleague",  "Nordvik Analytics", "Utrecht",    "ML engineer"),
]

# id, name, client_org, lead_id, design_lead_id, status, valid_from, valid_until, budget_ksek, repo, stack
PROJECTS = [
    ("tidewater",  "Tidewater",      "Halvorsen Marine",  "tomas",   "hanna",   "active",    "2025-11-03", None,         4200, "nordvik/tidewater",  "Flink"),
    ("bluefin",    "Bluefin",        "Halvorsen Marine",  "rafael",  "frida",   "active",    "2026-02-16", None,         2750, "nordvik/bluefin",    "dbt"),
    ("ledgerline", "Ledgerline",     "Stellarcrest Bank", "ingrid",  "hanna",   "active",    "2026-01-12", None,         6100, "nordvik/ledgerline", "Spark"),
    ("sentinel",   "Sentinel",       "Stellarcrest Bank", "aisha",   "hanna",   "active",    "2026-04-06", None,         3300, "nordvik/sentinel",   "Rust"),
    ("windrow",    "Windrow",        "Tallhojd Energi",   "lucia",   "frida",   "active",    "2026-03-02", None,         1900, "nordvik/windrow",    "DuckDB"),
    ("kilnstone",  "Kilnstone",      "Tallhojd Energi",   "hugo",    "hanna",   "completed", "2025-01-13", "2025-10-31", 2400, "nordvik/kilnstone",  "Airflow"),
    ("halyard",    "Halyard",        "Halvorsen Marine",  "saskia",  "frida",   "completed", "2024-09-02", "2025-06-30", 1500, "nordvik/halyard",    "Kafka"),
    ("moraine",    "Moraine",        "Nordvik Analytics", "bengt",   "hanna",   "active",    "2026-05-18", None,          900, "nordvik/moraine",    "Terraform"),
    ("passerine",  "Passerine",      "Nordvik Analytics", "dmitri",  "frida",   "paused",    "2026-02-02", None,          650, "nordvik/passerine",  "Playwright"),
    ("oxbow",      "Oxbow",          "Stellarcrest Bank", "olu",     "hanna",   "active",    "2026-06-15", None,         5200, "nordvik/oxbow",      "Iceberg"),
    ("greenfell",  "Greenfell",      "Tallhojd Energi",   "mira",    "frida",   "cancelled", "2025-08-04", "2026-01-09", 1100, "nordvik/greenfell",  "Superset"),
    ("thornwood",  "Thornwood",      "Halvorsen Marine",  "ingrid",  "hanna",   "active",    "2026-07-20", None,         2100, "nordvik/thornwood",  "Polars"),
]

# id, make, model, year, colour, plate, status, valid_from, valid_until, note
VEHICLES = [
    ("volvo_v60",  "Volvo",  "V60",       2019, "graphite grey", "MLK 471", "current", "2023-04-11", None,         "family estate, main car"),
    ("kia_soul",   "Kia",    "Soul EV",   2022, "pearl white",   "RTB 908", "current", "2024-08-19", None,         "second car, Idris commutes in it"),
    ("saab_95",    "Saab",   "9-5",       2008, "midnight blue", "BJH 226", "sold",    "2016-05-02", "2023-04-02", "sold when the V60 arrived"),
    ("vespa",      "Piaggio","Vespa GTS", 2021, "sage green",    "CFN 145", "current", "2021-06-30", None,         "summer runabout, kept at Smogen"),
    ("trailer",    "Brenderup","1205S",   2017, "galvanised",    "XPD 033", "current", "2019-03-15", None,         "small trailer, garage"),
    ("ford_focus", "Ford",   "Focus",     2012, "silver",        "ZWQ 610", "sold",    "2014-01-20", "2016-04-28", "first car after moving to Gothenburg"),
]

# id, institution, kind, ref, detail, sensitivity
ACCOUNTS = [
    ("sal_main",   "Handelsbanken",  "salary account",   "HB-4471",   "salary paid on the 25th",             "normal"),
    ("joint",      "Handelsbanken",  "joint account",    "HB-8802",   "household bills, shared with Idris",   "normal"),
    ("buffer",     "Lansforsakringar","savings",         "LF-2290",   "emergency buffer, 6 months outgoings", "sensitive"),
    ("isk",        "Avanza",         "investment (ISK)", "AV-7715",   "index funds, monthly transfer",        "sensitive"),
    ("pension_occ","Alecta",         "occupational pension","AL-3364", "via Nordvik Analytics",               "sensitive"),
    ("pension_pri","Avanza",         "private pension",  "AV-9021",   "topped up in December",                "sensitive"),
    ("mortgage",   "Handelsbanken",  "mortgage",         "HB-1153",   "flat in Majorna",                      "sensitive"),
    ("mortgage2",  "Lansforsakringar","mortgage",        "LF-6640",   "cabin at Smogen",                      "sensitive"),
    ("card_amex",  "Amex",           "credit card",      "AX-5528",   "travel and expenses",                  "sensitive"),
    ("kids_save",  "Handelsbanken",  "childrens savings","HB-7734",   "one per child, birthday transfers",    "sensitive"),
    ("company",    "Skatteverket",   "sole trader reg.", "SE-556914", "dormant consultancy registration",     "sensitive"),
    ("insurance",  "Trygg-Hansa",    "home insurance",   "TH-4102",   "flat and cabin on one policy",          "normal"),
]

# id, label, detail, clinician_id, since, until, sensitivity
HEALTH = [
    ("psoriatic",  "psoriatic arthritis", "diagnosed after eighteen months of joint pain", "ferreira", "2021-11-04", None, "sensitive"),
    ("methotrex",  "methotrexate",        "15 mg weekly, Thursday evenings",               "ferreira", "2022-01-10", None, "sensitive"),
    ("folate",     "folic acid",          "5 mg, day after methotrexate",                  "ferreira", "2022-01-10", None, "sensitive"),
    ("thyroid",    "hypothyroidism",      "levothyroxine 75 mcg each morning",             "okonkwo",  "2019-03-22", None, "sensitive"),
    ("penicillin", "penicillin allergy",  "rash, documented age nine",                     "lindholm", "1994-06-01", None, "sensitive"),
    ("shellfish",  "shellfish intolerance","not anaphylactic, avoids prawns",              "lindholm", "2018-02-14", None, "sensitive"),
    ("bp_watch",   "borderline blood pressure", "monitored, no medication",                "lindholm", "2025-05-09", None, "sensitive"),
    ("physio",     "physiotherapy",       "Tuesdays, hand and wrist programme",            "ferreira", "2024-09-03", None, "sensitive"),
    ("sulfasal",   "sulfasalazine",       "trialled, stopped for nausea",                  "ferreira", "2021-12-01", "2022-01-09", "sensitive"),
    ("vitd",       "vitamin D",           "2000 IU through the winter",                    "lindholm", "2023-10-01", None, "sensitive"),
    ("mri_knee",   "knee MRI",            "clear, no structural damage",                   "ferreira", "2025-02-11", None, "sensitive"),
    ("flu_jab",    "annual flu vaccination", "recommended on immunosuppressant",           "lindholm", "2022-10-05", None, "sensitive"),
]

# id, destination, country, purpose, start, end, with_ids, note
TRIPS = [
    ("bergen26",   "Bergen",     "Norway",   "client workshop",  "2026-03-10", "2026-03-12", ["tomas"],           "Halvorsen Marine onsite"),
    ("stockholm26","Stockholm",  "Sweden",   "client review",    "2026-05-04", "2026-05-05", ["ingrid"],          "Stellarcrest quarterly"),
    ("lisbon26",   "Lisbon",     "Portugal", "team offsite",     "2026-06-01", "2026-06-05", ["rafael", "hanna"], "Nordvik engineering week"),
    ("kumasi25",   "Kumasi",     "Ghana",    "family",           "2025-12-18", "2026-01-06", ["idris", "nell", "theo"], "three weeks with Kwame"),
    ("smogen26",   "Smogen",     "Sweden",   "holiday",          "2026-07-04", "2026-08-02", ["idris", "nell", "theo"], "cabin, full month"),
    ("london25",   "London",     "UK",       "family",           "2025-10-24", "2025-10-27", ["nell"],            "half term with Yaw"),
    ("helsinki26", "Helsinki",   "Finland",  "client workshop",  "2026-02-18", "2026-02-19", ["mira"],            "Ledgerline kickoff"),
    ("uppsala26",  "Uppsala",    "Sweden",   "family",           "2026-04-11", "2026-04-13", ["theo"],            "Astrid's birthday"),
    ("milan25",    "Milan",      "Italy",    "conference",       "2025-09-15", "2025-09-18", ["lucia"],           "data engineering summit"),
    ("vasteras26", "Vasteras",   "Sweden",   "client review",    "2026-08-25", "2026-08-26", ["lucia"],           "Tallhojd Windrow demo"),
    ("krakow26",   "Krakow",     "Poland",   "team visit",       "2026-09-22", "2026-09-24", ["hanna"],           "design week, booked"),
    ("oslo25",     "Oslo",       "Norway",   "personal",         "2025-06-06", "2025-06-08", ["frida"],           "Frida's exhibition"),
    ("tallinn26",  "Tallinn",    "Estonia",  "client workshop",  "2026-10-14", "2026-10-16", ["dmitri"],          "QA handover, booked"),
    ("boras25",    "Boras",      "Sweden",   "personal",         "2025-11-08", "2025-11-09", ["lars"],            "collecting the workbench"),
    ("utrecht26",  "Utrecht",    "Netherlands","team visit",     "2026-11-03", "2026-11-05", ["saskia"],          "ML platform review, booked"),
    ("malmo26",    "Malmo",      "Sweden",   "family",           "2026-05-30", "2026-05-31", ["sofie"],           "Sofie's move"),
]

# id, area, statement, strength
PREFERENCES = [
    ("coffee",    "food",     "drinks filter coffee, black, never espresso after 14:00", "strong"),
    ("meeting",   "work",     "declines meetings before 09:30 to do the school run",     "strong"),
    ("writing",   "ai",       "wants prose, not bullet lists, in long-form answers",     "strong"),
    ("units",     "ai",       "metric units and ISO dates, always",                      "strong"),
    ("lang_home", "language", "Swedish at home with the children, English at work",      "strong"),
    ("lang_fam",  "language", "Twi with Kwame on calls",                                 "medium"),
    ("travel_pref","travel",  "trains over short-haul flights inside Scandinavia",       "strong"),
    ("food_diet", "food",     "vegetarian on weekdays, fish at weekends",                "medium"),
    ("notify",    "ai",       "no notifications between 21:00 and 07:00",                "strong"),
    ("music",     "leisure",  "listens to highlife and Nordic jazz while working",       "medium"),
    ("reading",   "leisure",  "reads translated fiction, one book a fortnight",          "medium"),
    ("exercise",  "health",   "swims Monday and Friday mornings at Valhallabadet",       "medium"),
    ("code_style","work",     "prefers explicit SQL over ORM abstractions",              "strong"),
    ("review",    "work",     "reviews pull requests first thing, before standup",       "medium"),
    ("gift",      "social",   "gives books as gifts, never gift cards",                  "medium"),
    ("phone",     "ai",       "prefers written summaries over voice notes",              "strong"),
    ("weekend",   "family",   "Saturdays are family time, no work calls",                "strong"),
    ("temp",      "home",     "keeps the flat at 19 degrees through winter",             "medium"),
    ("shopping",  "home",     "one big grocery order on Thursdays",                      "medium"),
    ("dentist",   "health",   "books dental checkups in January and July",               "medium"),
    ("news",      "leisure",  "reads the news once, in the evening, not through the day", "medium"),
    ("packing",   "travel",   "cabin bag only for anything under four nights",           "strong"),
]

# id, label, detail, sensitivity, namespace
HOME = [
    ("flat",     "flat in Majorna",   "three rooms, 78 square metres, fourth floor, no lift", "sensitive", "pcp.home"),
    ("cabin",    "cabin at Smogen",   "inherited from Astrid's side, wood heated",            "sensitive", "pcp.home"),
    ("boiler",   "boiler service",    "serviced each September by Vastkust VVS",              "normal",    None),
    ("wifi",     "home network",      "mesh, three nodes, guest network for visitors",        "normal",    None),
    ("bikes",    "bicycles",          "four, two cargo, stored in the basement cage",         "normal",    None),
    ("plants",   "balcony planting",  "tomatoes and herbs, watered by Stig when away",        "normal",    None),
    ("cat",      "cat, Bruno",        "tabby, eleven, on renal diet from Greta Palm",         "normal",    None),
    ("storage",  "basement storage",  "cage 4B, skis and camping gear",                       "normal",    None),
    ("keys",     "spare keys",        "one set with Stig, one at the cabin",                  "sensitive", "pcp.home"),
    ("renovation","kitchen renovation","planned for spring, quotes from Lars",                "normal",    None),
]
