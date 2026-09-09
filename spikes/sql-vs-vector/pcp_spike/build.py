"""One-command build: corpus -> WP schema + curated views -> embeddings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import corpus, store
from .model import SEED

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.build")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--flat-supersession", action="store_true",
                    help="ABLATION: give both pages of a supersession pair the same "
                         "`updated` and `confidence`, so only the edge discriminates")
    ap.add_argument("--embeddings", choices=["local", "none"], default="local",
                    help="'local' uses sentence-transformers on CPU; 'none' skips "
                         "the embeddings table and leaves only the BM25 backend")
    a = ap.parse_args(argv)

    print("[1/3] corpus")
    corpus.main(str(ROOT / "corpus"), a.seed, a.flat_supersession)

    print("[2/3] storage")
    store.main(str(ROOT / "corpus"), str(ROOT / "data"))

    print("[3/3] embeddings")
    if a.embeddings == "local":
        from . import retrieval
        manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text(encoding="utf-8"))
        n = retrieval.build_embeddings(manifest, ROOT / "data" / "pcp.sqlite")
        print(f"  embedded {n} pages with {retrieval.MODEL_NAME}")
    else:
        print("  skipped (--embeddings none); the vector condition cannot run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
