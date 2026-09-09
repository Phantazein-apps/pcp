"""One-command build: corpus -> WP schema + curated views -> embeddings.

Two corpora, same persona, same gold answers, different storage shape:

    python -m pcp_spike.build --shape atomic   --target-pages 2000
    python -m pcp_spike.build --shape subject  --target-pages 2000

Each writes to its own corpus/ and data/ root, so both exist side by side and
a sweep only has to be pointed at one of them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import store
from .model import SEED

ROOT = Path(__file__).resolve().parent.parent

# shape -> (corpus root, data root)
# The first pass's corpus lives on untouched at corpus/ + data/ (547 atomic
# pages); it is the control and `run.sh` still reproduces it. The second pass
# builds its own pair of 2,000-unit corpora alongside it.
ROOTS = {
    "atomic":  ("corpus-a", "data-a"),
    "subject": ("corpus-b", "data-b"),
}


def _gold_paths(manifest: dict) -> set[str]:
    keep = {f["page"] for f in manifest["facts"]}
    d = manifest["designed"]
    for spec in d.get("reconcile", []):
        keep |= {spec["current"]["path"], spec["stale"]["path"]}
    for spec in d.get("supersession", []):
        keep |= {spec["old_path"], spec["new_path"]}
    for spec in d.get("prose_a", []) + d.get("prose_b", []):
        keep.add(spec["path"])
    for spec in d.get("windows", []):
        keep |= {o["path"] for o in spec["options"]}
    for spec in d.get("historical", []):
        keep |= {spec["old"]["path"], spec["new"]["path"]}
    keep |= set(d.get("traces", []))
    return keep


def build_one(shape: str, seed: int, target_pages: int | None,
              embeddings: str, flat_supersession: bool = False,
              corpus_root: str | None = None,
              data_root: str | None = None,
              with_reconcile: bool = False) -> dict:
    cdir, ddir = ROOTS[shape]
    corpus = ROOT / (corpus_root or cdir)
    data = ROOT / (data_root or ddir)

    print(f"[1/3] corpus ({shape}) -> {corpus.name}")
    if shape == "atomic":
        from . import corpus as corpus_a
        manifest = corpus_a.main(str(corpus), seed, flat_supersession, target_pages,
                                 with_reconcile)
    else:
        from . import corpus_b
        manifest = corpus_b.main(str(corpus), seed, target_pages or 2000)

    print(f"[2/3] storage -> {data.name}")
    store.main(str(corpus), str(data))

    # A compact, committable extract: everything the report is checked
    # against, without the ~8 MB of page bodies that regenerate from the seed.
    gt = {
        "shape": manifest["shape"], "seed": manifest["seed"],
        "today": manifest["today"], "counts": manifest["counts"],
        "designed": manifest["designed"], "facts": manifest["facts"],
        "profile_namespaces": manifest["profile_namespaces"],
        # Only the pages a claim in REPORT.md rests on: every page carrying a
        # gold fact, plus every designed case. The ~1,800 filler pages are
        # noise by construction and regenerate from the seed.
        "pages": [{k: v for k, v in p.items() if k != "body"}
                  for p in manifest["pages"] if p["path"] in _gold_paths(manifest)],
    }
    (corpus / "ground-truth.json").write_text(
        json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[3/3] embeddings")
    if embeddings == "local":
        from . import retrieval
        manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
        n = retrieval.build_embeddings(manifest, data / "pcp.sqlite")
        unit = "chunks" if manifest.get("shape") == "subject" else "pages"
        print(f"  embedded {n} {unit} with {retrieval.MODEL_NAME}")
    else:
        print("  skipped (--embeddings none); the vector condition cannot run")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pcp_spike.build")
    ap.add_argument("--shape", choices=["atomic", "subject", "both"], default="atomic")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--target-pages", type=int, default=None,
                    help="grow the corpus to roughly this many pages/files "
                         "(the second pass runs both shapes at 2000)")
    ap.add_argument("--flat-supersession", action="store_true",
                    help="ABLATION (atomic only): give both pages of a supersession "
                         "pair the same `updated` and `confidence`, so only the edge "
                         "discriminates")
    ap.add_argument("--embeddings", choices=["local", "none"], default="local",
                    help="'local' uses sentence-transformers on CPU; 'none' skips "
                         "the embeddings table and leaves only the BM25 backend")
    ap.add_argument("--with-reconcile", action="store_true",
                    help="include the second pass's `reconcile` stratum -- eight "
                         "contradicting page pairs with no marker. Off by default "
                         "so `run.sh` still rebuilds the first-pass corpus exactly.")
    ap.add_argument("--corpus-root", default=None)
    ap.add_argument("--data-root", default=None)
    a = ap.parse_args(argv)

    shapes = ["atomic", "subject"] if a.shape == "both" else [a.shape]
    for sh in shapes:
        # corpus-b is defined with the reconcile pairs in it; for the atomic
        # generator they are opt-in.
        build_one(sh, a.seed, a.target_pages, a.embeddings,
                  a.flat_supersession, a.corpus_root, a.data_root,
                  a.with_reconcile or sh == "subject")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
