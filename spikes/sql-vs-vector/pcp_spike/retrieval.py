"""Retrieval backends: brute-force cosine over embeddings, and BM25.

Both backends apply the SAME scope filter and the SAME SPEC.md §5.2 default
lifecycle/validity policy as the SQL views, with the same `include_stale`
opt-in. Neither condition is given a filtering power the other lacks.

No ANN index -- 547 pages is small enough that exact cosine over a dense
matrix is both faster and unambiguous.
"""
from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None
_bm25_cache: dict[str, object] = {}


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(page: dict) -> str:
    """What actually gets embedded for a page."""
    return f"{page['title']}\n{page['body']}"


def build_embeddings(manifest: dict, master: Path) -> int:
    """Populate the embeddings table: (page id, path, vector)."""
    model = _load_model()
    pages = manifest["pages"]
    texts = [embed_text(p) for p in pages]
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=64,
                        show_progress_bar=False).astype(np.float32)
    con = sqlite3.connect(master)
    con.execute("DROP TABLE IF EXISTS pcp_embeddings")
    con.execute("CREATE TABLE pcp_embeddings "
                "(page_id INTEGER PRIMARY KEY, path TEXT, dim INTEGER, vector BLOB)")
    for i, (p, v) in enumerate(zip(pages, vecs), start=1):
        con.execute("INSERT INTO pcp_embeddings VALUES (?,?,?,?)",
                    (i, p["path"], int(v.shape[0]), v.tobytes()))
    con.commit()
    con.close()
    np.save(master.parent / "embeddings.npy", vecs)
    (master.parent / "embedding_paths.json").write_text(
        json.dumps([p["path"] for p in pages]), encoding="utf-8")
    return len(pages)


class Index:
    """Scope-aware retrieval over the corpus."""

    def __init__(self, data_root: Path, corpus_root: Path, backend: str = "vector"):
        self.data_root = Path(data_root)
        self.backend = backend
        self.manifest = json.loads(
            (Path(corpus_root) / "manifest.json").read_text(encoding="utf-8"))
        self.pages = {p["path"]: p for p in self.manifest["pages"]}
        self.order = [p["path"] for p in self.manifest["pages"]]
        self._vecs = None
        self._bm25 = None

    # -------------------------------------------------------------- data --
    def vectors(self) -> np.ndarray:
        if self._vecs is None:
            f = self.data_root / "embeddings.npy"
            if not f.exists():
                raise SystemExit(
                    "embeddings.npy missing -- run `python -m pcp_spike.build --embeddings local`")
            self._vecs = np.load(f)
        return self._vecs

    def bm25(self):
        if self._bm25 is None:
            from rank_bm25 import BM25Okapi
            toks = [self._tok(embed_text(self.pages[p])) for p in self.order]
            self._bm25 = BM25Okapi(toks)
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
    def search(self, scope: str, query: str, k: int = 5,
               include_stale: bool = False) -> list[dict]:
        allowed = self.scope_paths(scope, include_stale)
        mask = np.array([p in allowed for p in self.order])
        if not mask.any():
            return []

        if self.backend == "vector":
            qv = _load_model().encode([query], normalize_embeddings=True).astype(np.float32)[0]
            scores = self.vectors() @ qv
        elif self.backend == "lexical":
            scores = np.asarray(self.bm25().get_scores(self._tok(query)), dtype=np.float32)
        else:
            raise ValueError(f"unknown backend {self.backend!r}")

        scores = np.where(mask, scores, -np.inf)
        idx = np.argsort(-scores)[:k]
        out = []
        for i in idx:
            if not np.isfinite(scores[i]):
                continue
            p = self.pages[self.order[i]]
            out.append({
                "path": p["path"],
                "score": round(float(scores[i]), 4),
                "frontmatter": {
                    "title": p["title"], "updated": p["updated"], "type": p["type"],
                    "domain": p["domain"], "lifecycle": p["lifecycle"],
                    "sensitivity": p["sensitivity"], "confidence": p["confidence"],
                    "valid_from": p["valid_from"], "valid_until": p["valid_until"],
                    "tags": p["tags"], "relations": p["relations"],
                },
                "body": p["body"],
            })
        return out
