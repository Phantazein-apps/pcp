"""Retrieval backends: brute-force cosine over embeddings, and BM25.

Both backends apply the SAME scope filter and the SAME SPEC.md §5.2 default
lifecycle/validity policy as the SQL views, with the same `include_stale`
opt-in. Neither condition is given a filtering power the other lacks.

No ANN index -- exact cosine over a dense matrix is both faster and
unambiguous at this corpus size.

**Chunking.** corpus-a's pages are one fact each and fit inside the model's
256-token window, so one vector per page is the whole page. corpus-b's
subject files are 8-25 bullets and DO overflow that window, so embedding them
whole would silently truncate most of every file and hand the vector
condition a rigged loss. corpus-b is therefore embedded one vector PER LINE
and scored max-over-lines, which is the standard mitigation and the fair
comparison: it means the vector condition matches at line granularity and
returns at page granularity -- exactly what `sql_document` is forced to do.
The shape is read from the manifest, so no condition has to ask for it.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(page: dict) -> str:
    """What gets embedded for an atomic page: the whole thing."""
    return f"{page['title']}\n{page['body']}"


def chunks_for(page: dict) -> list[str]:
    """What gets embedded for a subject file: one vector per bullet.

    The title is prefixed to every chunk so a line like "Sold in 2023." is
    still attached to the subject it belongs to.
    """
    out = []
    for raw in page["body"].splitlines():
        txt = raw.strip().lstrip("-").strip()
        if txt:
            out.append(f"{page['title']}: {txt}")
    return out or [embed_text(page)]


def build_embeddings(manifest: dict, master: Path) -> int:
    """Populate the embeddings table. Returns the number of VECTORS built."""
    model = _load_model()
    pages = manifest["pages"]
    chunked = manifest.get("shape") == "subject"

    texts: list[str] = []
    owners: list[str] = []          # one page path per vector
    for p in pages:
        for t in (chunks_for(p) if chunked else [embed_text(p)]):
            texts.append(t)
            owners.append(p["path"])

    vecs = model.encode(texts, normalize_embeddings=True, batch_size=128,
                        show_progress_bar=False).astype(np.float32)

    con = sqlite3.connect(master)
    con.execute("DROP TABLE IF EXISTS pcp_embeddings")
    con.execute("CREATE TABLE pcp_embeddings "
                "(vec_id INTEGER PRIMARY KEY, path TEXT, dim INTEGER, vector BLOB)")
    con.executemany(
        "INSERT INTO pcp_embeddings VALUES (?,?,?,?)",
        [(i, owners[i - 1], int(vecs.shape[1]), vecs[i - 1].tobytes())
         for i in range(1, len(owners) + 1)])
    con.commit()
    con.close()

    np.save(master.parent / "embeddings.npy", vecs)
    (master.parent / "embedding_paths.json").write_text(
        json.dumps({"chunked": chunked, "owners": owners}), encoding="utf-8")
    return len(owners)


class Index:
    """Scope-aware retrieval over one corpus."""

    def __init__(self, data_root: Path, corpus_root: Path, backend: str = "vector"):
        self.data_root = Path(data_root)
        self.backend = backend
        self.manifest = json.loads(
            (Path(corpus_root) / "manifest.json").read_text(encoding="utf-8"))
        self.shape = self.manifest.get("shape", "atomic")
        self.pages = {p["path"]: p for p in self.manifest["pages"]}
        self.order = [p["path"] for p in self.manifest["pages"]]
        self._vecs = None
        self._owners = None
        self._bm25 = None
        self._bm25_owners = None

    # -------------------------------------------------------------- data --
    def vectors(self) -> np.ndarray:
        if self._vecs is None:
            f = self.data_root / "embeddings.npy"
            if not f.exists():
                raise SystemExit(
                    "embeddings.npy missing -- run `python -m pcp_spike.build --embeddings local`")
            self._vecs = np.load(f)
        return self._vecs

    def owners(self) -> list[str]:
        """The page path each vector belongs to."""
        if self._owners is None:
            meta = json.loads(
                (self.data_root / "embedding_paths.json").read_text(encoding="utf-8"))
            self._owners = meta["owners"] if isinstance(meta, dict) else list(meta)
        return self._owners

    def bm25(self):
        if self._bm25 is None:
            from rank_bm25 import BM25Okapi
            texts, owners = [], []
            for path in self.order:
                p = self.pages[path]
                for t in (chunks_for(p) if self.shape == "subject" else [embed_text(p)]):
                    texts.append(t)
                    owners.append(path)
            self._bm25 = BM25Okapi([self._tok(t) for t in texts])
            self._bm25_owners = owners
        return self._bm25

    @staticmethod
    def _tok(s: str) -> list[str]:
        import re
        return re.findall(r"[a-z0-9]+", s.lower())

    # ------------------------------------------------------------- scope --
    def scope_paths(self, scope: str, include_stale: bool) -> set[str]:
        """Exactly the pages the SQL views would expose for this scope."""
        db = self.data_root / f"scope_{scope}.sqlite"
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        table = "memory_all" if include_stale else "memory"
        paths = {r[0] for r in con.execute(f"SELECT path FROM {table}")}
        con.close()
        return paths

    # ------------------------------------------------------------ search --
    def _frontmatter(self, p: dict, hide_relations: bool) -> dict:
        # corpus-b pages carry a file-level `updated` and nothing else, so
        # search must not invent structure the store does not have.
        if self.shape == "subject":
            fm = {"title": p["title"], "updated": p["updated"]}
            if p.get("sensitivity") not in (None, "normal"):
                fm["sensitivity"] = p["sensitivity"]
            return fm
        return {
            "title": p["title"], "updated": p["updated"], "type": p["type"],
            "domain": p["domain"], "lifecycle": p["lifecycle"],
            "sensitivity": p["sensitivity"], "confidence": p["confidence"],
            "valid_from": p["valid_from"], "valid_until": p["valid_until"],
            "tags": p["tags"],
            **({} if hide_relations else {"relations": p["relations"]}),
        }

    def search(self, scope: str, query: str, k: int = 5,
               include_stale: bool = False,
               hide_relations: bool = False) -> list[dict]:
        allowed = self.scope_paths(scope, include_stale)
        if not allowed:
            return []

        if self.backend == "vector":
            owners = self.owners()
            qv = _load_model().encode([query], normalize_embeddings=True).astype(np.float32)[0]
            scores = self.vectors() @ qv
        elif self.backend == "lexical":
            bm = self.bm25()
            owners = self._bm25_owners
            scores = np.asarray(bm.get_scores(self._tok(query)), dtype=np.float32)
        else:
            raise ValueError(f"unknown backend {self.backend!r}")

        # max-over-chunks, then top-k PAGES (a page is the retrieval unit in
        # both shapes; chunking only changes what is matched, not what is
        # returned).
        best: dict[str, float] = {}
        for owner, sc in zip(owners, scores):
            if owner in allowed and (owner not in best or sc > best[owner]):
                best[owner] = float(sc)
        top = sorted(best.items(), key=lambda kv: -kv[1])[:k]

        out = []
        for path, sc in top:
            p = self.pages[path]
            out.append({
                "path": path,
                "score": round(sc, 4),
                "frontmatter": self._frontmatter(p, hide_relations),
                "body": p["body"],
            })
        return out
