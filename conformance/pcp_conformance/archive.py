"""Archive checks (SPEC §8.2, §8.3, §8.8) on archive files.

`check` unpacks safely and runs the same checks as scripts/validate_schemas.py.
`roundtrip` compares an archive with the archive exported after restoring it.
"""
import json
import pathlib
import tarfile
import tempfile
import zipfile

from .target import _load_validator


class UnsafeArchive(Exception):
    pass


def _safe_name(name):
    if name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    parts = name.rstrip("/").split("/")
    return all(p not in ("", ".", "..") for p in parts)


def unpack(path, dest):
    """Unpacks zip, tar or tar.gz, refusing anything SPEC §8.7.1 item 1 refuses."""
    path = pathlib.Path(path)
    seen = set()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                name = info.filename
                if not _safe_name(name) or name in seen:
                    raise UnsafeArchive(f"unsafe or repeated entry {name!r}")
                seen.add(name)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise UnsafeArchive(f"link entry {name!r}")
                if not name.endswith("/"):
                    out = dest / name
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(info))
        return
    with tarfile.open(path) as tar:
        for m in tar.getmembers():
            if m.name in (".", "./"):
                continue
            if m.name.startswith("./"):
                m.name = m.name[2:]
            if not _safe_name(m.name) or m.name in seen:
                raise UnsafeArchive(f"unsafe or repeated entry {m.name!r}")
            seen.add(m.name)
            if not (m.isfile() or m.isdir()):
                raise UnsafeArchive(f"entry {m.name!r} is not a regular file or directory")
            if m.isfile():
                out = dest / m.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(tar.extractfile(m).read())


def check(path, keys=None):
    """Returns (problems, manifest)."""
    v = _load_validator()
    schemas, registry = v.load_schemas()
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        p = pathlib.Path(path)
        if p.is_dir():
            root = p
        else:
            try:
                unpack(p, root)
            except UnsafeArchive as e:
                return [str(e)], None
        if not (root / "manifest.json").exists():
            return ["no manifest.json at the root"], None
        problems = v.check_archive(root, schemas, registry, keys or {})
        manifest = json.loads((root / "manifest.json").read_text())
        ctx = json.loads((root / "context.json").read_text()) if (root / "context.json").exists() else {}
        if ctx.get("kind") == "personal":
            orgs = [p["id"] for p in ctx.get("principals", []) if p.get("id", "").startswith("org:")]
            if orgs or not str(ctx.get("controller", "")).startswith("human:"):
                problems.append(f"personal context with organization principals or controller: {orgs or ctx.get('controller')}")
        return problems, manifest


ROUNDTRIP_DIRS = ("memory/", "revisions/", "history/", "profile/", "extensions/")


def _files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def roundtrip(a_path, b_path, same_implementation=True):
    """SPEC §8.8: compare archive A with archive B exported after restoring A."""
    v = _load_validator()
    problems = []
    with tempfile.TemporaryDirectory() as da, tempfile.TemporaryDirectory() as db:
        ra, rb = pathlib.Path(da), pathlib.Path(db)
        for src, dst in ((a_path, ra), (b_path, rb)):
            p = pathlib.Path(src)
            if p.is_dir():
                dst = p
            else:
                unpack(p, dst)
        ra = pathlib.Path(a_path) if pathlib.Path(a_path).is_dir() else ra
        rb = pathlib.Path(b_path) if pathlib.Path(b_path).is_dir() else rb
        fa, fb = _files(ra), _files(rb)
        keys = [k for k in fa if k.startswith(ROUNDTRIP_DIRS) or k == "context.json"]
        for k in keys:
            if k not in fb:
                problems.append(f"{k}: missing after the round trip")
                continue
            if same_implementation:
                if fa[k] != fb[k]:
                    problems.append(f"{k}: bytes differ")
            elif k.endswith(".md"):
                ta, tb = fa[k].decode(), fb[k].decode()
                ma, mb = v.FRONTMATTER.match(ta), v.FRONTMATTER.match(tb)
                if not (ma and mb):
                    problems.append(f"{k}: no frontmatter")
                    continue
                if ta[ma.end():] != tb[mb.end():]:
                    problems.append(f"{k}: body bytes differ")
                if v.frontmatter_of(ta) != v.frontmatter_of(tb):
                    problems.append(f"{k}: frontmatter differs as data")
            elif k.endswith(".json"):
                if json.loads(fa[k]) != json.loads(fb[k]):
                    problems.append(f"{k}: differs as JSON")
        extra = [k for k in fb if (k.startswith(ROUNDTRIP_DIRS) or k == "context.json") and k not in fa]
        problems += [f"{k}: new after the round trip" for k in extra]
        if (ra / "audit/log.jsonl").exists() and (rb / "audit/log.jsonl").exists():
            la = (ra / "audit/log.jsonl").read_text().splitlines()
            lb = (rb / "audit/log.jsonl").read_text().splitlines()
            if same_implementation and lb[: len(la)] != la:
                problems.append("audit/log.jsonl: B does not start with A's entries")
    return problems
