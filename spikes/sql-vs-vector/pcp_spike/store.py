"""Storage: (a) a WordPress-shaped schema, (b) curated views over it.

Layer (a) mirrors what the WordPress deployment plan would produce: memory
pages as a custom post type, frontmatter as postmeta EAV, tags and domains
as terms. Nothing here is clever -- it is deliberately the awkward shape the
real deployment has, so the view layer has something real to flatten.

Layer (b) is one curated, flattened view set per scope bundle, exposing only
the rows and columns that scope permits (SPEC.md §4.3, §7.1).

Scope enforcement is structural. Each bundle's views are materialised into
their own SQLite file; the harness opens exactly one of those, read-only. A
scope-restricted leak therefore cannot be a query bug -- only the model
asserting something it was never shown.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .model import SCOPE_BUNDLES, BUNDLE_NAMESPACES, LIFECYCLE_DEFAULT_VISIBLE, TODAY

WP_SCHEMA = """
PRAGMA journal_mode = MEMORY;

CREATE TABLE wp_posts (
    ID            INTEGER PRIMARY KEY,
    post_author   INTEGER NOT NULL DEFAULT 1,
    post_date     TEXT    NOT NULL,
    post_modified TEXT    NOT NULL,
    post_title    TEXT    NOT NULL,
    post_name     TEXT    NOT NULL,          -- the PCP page path
    post_content  TEXT    NOT NULL,          -- markdown body
    post_status   TEXT    NOT NULL DEFAULT 'publish',
    post_type     TEXT    NOT NULL           -- pcp_memory | pcp_profile
);
CREATE INDEX idx_posts_name ON wp_posts(post_name);
CREATE INDEX idx_posts_type ON wp_posts(post_type);

CREATE TABLE wp_postmeta (
    meta_id    INTEGER PRIMARY KEY,
    post_id    INTEGER NOT NULL REFERENCES wp_posts(ID),
    meta_key   TEXT    NOT NULL,
    meta_value TEXT
);
CREATE INDEX idx_meta_post ON wp_postmeta(post_id);
CREATE INDEX idx_meta_key  ON wp_postmeta(meta_key);

CREATE TABLE wp_terms (
    term_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    slug    TEXT NOT NULL
);
CREATE TABLE wp_term_taxonomy (
    term_taxonomy_id INTEGER PRIMARY KEY,
    term_id          INTEGER NOT NULL REFERENCES wp_terms(term_id),
    taxonomy         TEXT    NOT NULL       -- pcp_tag | pcp_domain
);
CREATE TABLE wp_term_relationships (
    object_id        INTEGER NOT NULL REFERENCES wp_posts(ID),
    term_taxonomy_id INTEGER NOT NULL REFERENCES wp_term_taxonomy(term_taxonomy_id),
    PRIMARY KEY (object_id, term_taxonomy_id)
);
"""

# Meta keys carrying SPEC.md §5.1 frontmatter.
META_SCALAR = ["type", "lifecycle", "sensitivity", "confidence",
               "valid_from", "valid_until", "namespace", "source_origin",
               "source_client"]


def _pivot(alias: str = "p") -> str:
    """SQL that pivots the postmeta EAV back into named columns."""
    cols = []
    for k in META_SCALAR:
        cols.append(
            f"(SELECT meta_value FROM wp_postmeta m WHERE m.post_id = {alias}.ID "
            f"AND m.meta_key = 'pcp_{k}') AS {k}"
        )
    return ",\n           ".join(cols)


def build_master(manifest: dict, db_path: Path) -> None:
    """Populate layer (a) and define layer (b) over it."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(WP_SCHEMA)

    term_ids: dict[tuple[str, str], int] = {}

    def term(tax: str, name: str) -> int:
        key = (tax, name)
        if key not in term_ids:
            tid = len(term_ids) + 1
            con.execute("INSERT INTO wp_terms(term_id,name,slug) VALUES (?,?,?)",
                        (tid, name, name.lower().replace(" ", "-")))
            con.execute("INSERT INTO wp_term_taxonomy(term_taxonomy_id,term_id,taxonomy) "
                        "VALUES (?,?,?)", (tid, tid, tax))
            term_ids[key] = tid
        return term_ids[key]

    for i, pg in enumerate(manifest["pages"], start=1):
        con.execute(
            "INSERT INTO wp_posts(ID,post_date,post_modified,post_title,post_name,"
            "post_content,post_status,post_type) VALUES (?,?,?,?,?,?,?,?)",
            (i, pg["updated"], pg["updated"], pg["title"], pg["path"],
             pg["body"], "publish", "pcp_memory"))
        meta = {
            "pcp_type": pg["type"],
            "pcp_lifecycle": pg["lifecycle"],
            "pcp_sensitivity": pg["sensitivity"],
            "pcp_confidence": pg["confidence"],
            "pcp_valid_from": pg["valid_from"],
            "pcp_valid_until": pg["valid_until"],
            "pcp_namespace": pg["namespace"],
        }
        for k, v in meta.items():
            if v is not None:
                con.execute("INSERT INTO wp_postmeta(post_id,meta_key,meta_value) "
                            "VALUES (?,?,?)", (i, k, str(v)))
        for rel in pg["relations"]:
            con.execute("INSERT INTO wp_postmeta(post_id,meta_key,meta_value) "
                        "VALUES (?,?,?)", (i, "pcp_relation", json.dumps(rel)))
        for d in pg["derived_from"]:
            con.execute("INSERT INTO wp_postmeta(post_id,meta_key,meta_value) "
                        "VALUES (?,?,?)", (i, "pcp_derived_from", d))
        con.execute("INSERT OR IGNORE INTO wp_term_relationships VALUES (?,?)",
                    (i, term("pcp_domain", pg["domain"])))
        for t in pg["tags"]:
            con.execute("INSERT OR IGNORE INTO wp_term_relationships VALUES (?,?)",
                        (i, term("pcp_tag", t)))

    # Profile documents live as their own post type, body = JSON (SPEC.md §4).
    prof_root = db_path.parent.parent / "corpus" / "profile"
    for j, ns in enumerate(manifest["profile_namespaces"], start=1):
        doc = json.loads((prof_root / f"{ns}.json").read_text(encoding="utf-8"))
        pid = 100000 + j
        con.execute(
            "INSERT INTO wp_posts(ID,post_date,post_modified,post_title,post_name,"
            "post_content,post_status,post_type) VALUES (?,?,?,?,?,?,?,?)",
            (pid, TODAY, TODAY, ns, f"profile/{ns}", json.dumps(doc, ensure_ascii=False),
             "publish", "pcp_profile"))
        con.execute("INSERT INTO wp_postmeta(post_id,meta_key,meta_value) VALUES (?,?,?)",
                    (pid, "pcp_namespace", ns))

    con.commit()
    _define_views(con)
    con.commit()
    con.close()


def _flatten(doc, prefix="") -> list[tuple[str, str]]:
    """Flatten a profile JSON document into (key_path, value) rows."""
    out: list[tuple[str, str]] = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            out += _flatten(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out += _flatten(v, f"{prefix}[{i}]")
    else:
        out.append((prefix, "" if doc is None else str(doc)))
    return out


def _scope_predicate(bundle: str) -> str:
    """Row-level filter: which pages this scope bundle may see at all."""
    allowed_ns = BUNDLE_NAMESPACES[bundle]
    ns_list = ", ".join(f"'{n}'" for n in allowed_ns)
    parts = [f"(v.namespace IS NULL OR v.namespace IN ({ns_list}))"]
    if "memory.sensitive:read" not in SCOPE_BUNDLES[bundle]:
        parts.append("(v.sensitivity IS NULL OR v.sensitivity = 'normal')")
    return " AND ".join(parts)


def _default_predicate() -> str:
    """SPEC.md §5.2 default retrieval policy."""
    lc = ", ".join(f"'{l}'" for l in sorted(LIFECYCLE_DEFAULT_VISIBLE))
    return (f"v.lifecycle IN ({lc}) "
            f"AND (v.valid_until IS NULL OR v.valid_until >= '{TODAY}')")


def _define_views(con: sqlite3.Connection) -> None:
    base = f"""
CREATE VIEW v_base AS
SELECT p.ID           AS id,
       p.post_name    AS path,
       p.post_title   AS title,
       p.post_modified AS updated,
       p.post_content AS body,
       (SELECT t.name FROM wp_term_relationships tr
          JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
          JOIN wp_terms t ON t.term_id = tt.term_id
         WHERE tr.object_id = p.ID AND tt.taxonomy = 'pcp_domain' LIMIT 1) AS domain,
       {_pivot('p')}
  FROM wp_posts p
 WHERE p.post_type = 'pcp_memory';

CREATE VIEW v_base_tags AS
SELECT p.post_name AS path, t.name AS tag
  FROM wp_posts p
  JOIN wp_term_relationships tr ON tr.object_id = p.ID
  JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
  JOIN wp_terms t ON t.term_id = tt.term_id
 WHERE tt.taxonomy = 'pcp_tag' AND p.post_type = 'pcp_memory';

CREATE VIEW v_base_relations AS
SELECT p.post_name AS source_page,
       json_extract(m.meta_value, '$.rel')        AS rel,
       json_extract(m.meta_value, '$.target')     AS target_page,
       json_extract(m.meta_value, '$.confidence') AS confidence
  FROM wp_posts p
  JOIN wp_postmeta m ON m.post_id = p.ID AND m.meta_key = 'pcp_relation'
 WHERE p.post_type = 'pcp_memory';
"""
    con.executescript(base)

    cols = ("v.path, v.title, v.domain, v.type, v.lifecycle, v.sensitivity, "
            "v.valid_from, v.valid_until, v.confidence, v.updated, v.body")
    for bundle in SCOPE_BUNDLES:
        scope = _scope_predicate(bundle)
        con.executescript(f"""
CREATE VIEW v_{bundle}_memory_all AS
SELECT {cols} FROM v_base v WHERE {scope};

CREATE VIEW v_{bundle}_memory AS
SELECT {cols} FROM v_base v WHERE {scope} AND {_default_predicate()};

CREATE VIEW v_{bundle}_tags AS
SELECT t.path, t.tag FROM v_base_tags t
 WHERE t.path IN (SELECT v.path FROM v_base v WHERE {scope});

CREATE VIEW v_{bundle}_relations_all AS
SELECT r.source_page, r.rel, r.target_page, r.confidence FROM v_base_relations r
 WHERE r.source_page IN (SELECT v.path FROM v_base v WHERE {scope});

CREATE VIEW v_{bundle}_relations AS
SELECT r.source_page, r.rel, r.target_page, r.confidence FROM v_base_relations r
 WHERE r.source_page IN (SELECT v.path FROM v_base v
                          WHERE {scope} AND {_default_predicate()});
""")


def build_profile_tables(con: sqlite3.Connection, manifest: dict, corpus_root: Path) -> None:
    """Flatten profile JSON into a queryable (namespace, key, value) table."""
    con.execute("CREATE TABLE IF NOT EXISTS pcp_profile_flat "
                "(namespace TEXT, key TEXT, value TEXT)")
    for ns in manifest["profile_namespaces"]:
        doc = json.loads((corpus_root / "profile" / f"{ns}.json").read_text(encoding="utf-8"))
        for k, v in _flatten(doc):
            con.execute("INSERT INTO pcp_profile_flat VALUES (?,?,?)", (ns, k, v))
    con.commit()


def materialise_scope(master: Path, out: Path, bundle: str,
                      manifest: dict, corpus_root: Path) -> dict:
    """Materialise one bundle's curated views into its own SQLite file.

    The result contains ONLY what that scope may see, so the harness can
    open it read-only and no cross-scope row is reachable even in principle.
    """
    if out.exists():
        out.unlink()
    con = sqlite3.connect(out)
    con.execute("ATTACH DATABASE ? AS src", (str(master),))
    con.execute("CREATE TABLE IF NOT EXISTS _profile_src (namespace TEXT, key TEXT, value TEXT)")

    made: dict[str, int] = {}
    for name, view in [
        ("memory",         f"v_{bundle}_memory"),
        ("memory_all",     f"v_{bundle}_memory_all"),
        ("tags",           f"v_{bundle}_tags"),
        ("relations",      f"v_{bundle}_relations"),
        ("relations_all",  f"v_{bundle}_relations_all"),
    ]:
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM src.{view}")
        made[name] = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]

    # profile: only namespaces this bundle may read (SPEC.md §4.3 rule 1)
    con.execute("CREATE TABLE profile (namespace TEXT, key TEXT, value TEXT)")
    for ns in BUNDLE_NAMESPACES[bundle]:
        if ns not in manifest["profile_namespaces"]:
            continue
        doc = json.loads((corpus_root / "profile" / f"{ns}.json").read_text(encoding="utf-8"))
        for k, v in _flatten(doc):
            con.execute("INSERT INTO profile VALUES (?,?,?)", (ns, k, v))
    made["profile"] = con.execute("SELECT count(*) FROM profile").fetchone()[0]

    con.execute("DROP TABLE _profile_src")
    con.executescript("""
CREATE INDEX idx_mem_path   ON memory(path);
CREATE INDEX idx_mem_domain ON memory(domain);
CREATE INDEX idx_mema_path  ON memory_all(path);
CREATE INDEX idx_rel_src    ON relations(source_page);
CREATE INDEX idx_rel_tgt    ON relations(target_page);
CREATE INDEX idx_rela_tgt   ON relations_all(target_page);
CREATE INDEX idx_tag_path   ON tags(path);
CREATE INDEX idx_prof_key   ON profile(key);
""")
    con.commit()
    con.execute("DETACH DATABASE src")
    con.close()
    return made


# The schema blurb handed to the agent in the sql_only and both conditions.
SCHEMA_DOC = """\
You are querying a read-only SQLite database of one person's PCP personal
memory. Only the tables below exist; there are no others.

  memory(path, title, domain, type, lifecycle, sensitivity,
         valid_from, valid_until, confidence, updated, body)
      One row per memory page that is CURRENTLY IN FORCE. This view already
      applies the PCP default retrieval policy: it contains only pages whose
      lifecycle is 'active' or 'validated' AND whose valid_until is either
      NULL or not yet passed. Start here.
        path        stable page identifier, e.g. 'projects/tidewater'
        domain      one of: people, work, projects, finances, health,
                    vehicles, travel, preferences, home
        type        episodic (something that happened) | semantic (a durable
                    fact or preference) | procedural (how the person does a thing)
        lifecycle   active | validated   (in this view only)
        valid_from  / valid_until  ISO-8601 dates bounding when the fact
                    is/was true. NULL valid_until means open-ended.
        confidence  0.0-1.0, how sure the context is of this page
        body        the page's markdown text

  memory_all(...same columns...)
      EVERY page, including ones the default policy hides: lifecycle 'stale'
      or 'archived', and pages whose valid_until has passed. Use this when
      the question is about the PAST -- what something used to be, when it
      changed, what was true on a given date. It is the only place historical
      facts are visible.

  relations(source_page, rel, target_page, confidence)
      Typed edges between pages. rel is one of:
        supersedes  source_page REPLACES target_page. The newer page is the
                    source. Both pages can be active at once, so this edge is
                    often the ONLY way to tell which of two similar pages is
                    current: a page that appears as a target_page of a
                    'supersedes' edge has been replaced.
        contradicts, refines, about
      relations_all(...) is the same over memory_all.

  tags(path, tag)
      Free labels per page.

  profile(namespace, key, value)
      The structured profile, flattened. key is a dotted path into the JSON,
      e.g. 'work.role', 'communication.tone', 'languages[0].code'.

Notes:
  - Today's date is {today}.
  - Only SELECT statements are permitted. One statement per call.
  - Results are capped at 200 rows and 20 KB and returned as CSV.
  - Page bodies are prose; use LIKE '%...%' on body, or filter by domain/tag
    first and read the bodies of what comes back.
"""


def main(corpus_root: str = "corpus", data_root: str = "data") -> None:
    corpus = Path(corpus_root)
    data = Path(data_root)
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    master = data / "pcp.sqlite"
    build_master(manifest, master)
    con = sqlite3.connect(master)
    build_profile_tables(con, manifest, corpus)
    con.close()
    print(f"master: {master}")
    for bundle in SCOPE_BUNDLES:
        made = materialise_scope(master, data / f"scope_{bundle}.sqlite",
                                 bundle, manifest, corpus)
        print(f"  scope {bundle:8s} memory={made['memory']:4d} "
              f"memory_all={made['memory_all']:4d} relations={made['relations']:3d} "
              f"profile={made['profile']:3d}")


if __name__ == "__main__":
    main()
