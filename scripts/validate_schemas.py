#!/usr/bin/env python3
"""Validate PCP schemas and examples.

Checks that every schema under schemas/<version>/ is valid JSON Schema
Draft 2020-12, then validates every example under examples/<version>/:

  discovery/*.json      against discovery.schema.json
  profile/core*.json    against profile.core.schema.json
  profile/team*.json    against profile.team.schema.json
  memory/*.md           frontmatter against memory.page.schema.json
  audit/*.jsonl         each line against audit.entry.schema.json
  tools/<tool>_<input|output>*.json  against tools.schema.json#/$defs/<tool>_<input|output>
  export/<archive>/     every check of SPEC §8.3 (see check_archive below)

Files under an invalid/ subdirectory must FAIL validation; an archive under
export/invalid/ must fail at least one archive check.

Archive files encrypted at file level (JWE, alg dir, enc A256GCM) are
decrypted with the public test key in export/example-keys.json when the
cryptography package is installed, and checked like plaintext files;
without it they are only hashed and counted.

Frontmatter is parsed with YAML 1.2 core-schema semantics for timestamps
(they stay strings), as SPEC §5.2 requires.

Usage: python3 scripts/validate_schemas.py [version]   (default 0.3)
Requires: pip install jsonschema pyyaml   (optional: cryptography)
"""
import base64
import hashlib
import json
import pathlib
import re
import sys

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = sys.argv[1] if __name__ == "__main__" and len(sys.argv) > 1 else "0.3"
SCHEMAS = ROOT / "schemas" / VERSION
EXAMPLES = ROOT / "examples" / VERSION


class CoreLoader(yaml.SafeLoader):
    """SafeLoader without the YAML 1.1 timestamp resolver."""


CoreLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def load_schemas():
    schemas, registry = {}, Registry()
    for path in sorted(SCHEMAS.glob("*.json")):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def validator(schemas, registry, name, pointer=None):
    schema = schemas[name]
    if pointer:
        schema = {"$ref": f"{schema['$id']}#{pointer}"}
    return Draft202012Validator(schema, registry=registry)


def instances(path):
    if path.suffix == ".md":
        match = FRONTMATTER.match(path.read_text())
        if not match:
            raise ValueError("no frontmatter block")
        yield "frontmatter", yaml.load(match.group(1), Loader=CoreLoader)
    elif path.suffix == ".jsonl":
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if line.strip():
                yield f"line {n}", json.loads(line)
    else:
        yield "document", json.loads(path.read_text())


def target(path):
    kind = path.relative_to(EXAMPLES).parts[0]
    stem = path.stem
    if kind == "discovery":
        return "discovery.schema.json", None
    if kind == "profile":
        return ("profile.team.schema.json" if stem.startswith("team") else "profile.core.schema.json"), None
    if kind == "memory":
        return "memory.page.schema.json", None
    if kind == "audit":
        return "audit.entry.schema.json", None
    if kind == "tools":
        m = re.match(r"([a-z_]+?_(?:input|output))", stem)
        return "tools.schema.json", f"/$defs/{m.group(1)}"
    raise ValueError(f"no schema for {kind}")


# --------------------------------------------------------------- archives
# SPEC §8.3. Independent of the exporter: everything is recomputed from the
# files on disk and compared with what the manifest claims.

def b64u_decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def decrypt_jwe(data, keys):
    """Compact JWE with alg dir and enc A256GCM. Returns None if it cannot."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    header_b64, _, iv, ct, tag = data.decode().split(".")
    header = json.loads(b64u_decode(header_b64))
    if header.get("alg") != "dir" or header.get("enc") != "A256GCM" or header.get("kid") not in keys:
        return None
    key = bytes.fromhex(keys[header["kid"]])
    return AESGCM(key).decrypt(b64u_decode(iv), b64u_decode(ct) + b64u_decode(tag), header_b64.encode())


def frontmatter_of(text):
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("no frontmatter block")
    return yaml.load(match.group(1), Loader=CoreLoader)


def principals_named(fm):
    src, rev = fm.get("source", {}), fm.get("review", {})
    names = [src.get("principal"), src.get("on_behalf_of")]
    names += [rev.get("generated", {}).get("by"), rev.get("rejected", {}).get("by")]
    names += [v.get("by") for v in rev.get("verified", [])]
    return {n for n in names if n}


def check_archive(root, schemas, registry, keys):
    """Returns a list of problems; empty means the archive checks."""
    problems = []

    def bad(msg):
        problems.append(msg)

    def validate(name, instance, label, pointer=None):
        for e in validator(schemas, registry, name, pointer).iter_errors(instance):
            bad(f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}")

    manifest = json.loads((root / "manifest.json").read_text())
    validate("export.manifest.schema.json", manifest, "manifest.json")

    # 2. Files, both directions.
    present = {p.relative_to(root).as_posix() for p in root.rglob("*")
               if p.is_file() and p.name != ".DS_Store"} - {"manifest.json"}
    listed = {}
    for entry in manifest.get("files", []):
        if entry["path"] in listed:
            bad(f"{entry['path']}: listed twice")
        listed[entry["path"]] = entry
    for path in sorted(present - set(listed)):
        bad(f"{path}: in the archive but not in files[]")
    for path in sorted(set(listed) - present):
        bad(f"{path}: in files[] but not in the archive")
    plain = {}
    for path in sorted(present & set(listed)):
        data = (root / path).read_bytes()
        entry = listed[path]
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"] or len(data) != entry["bytes"]:
            bad(f"{path}: sha256/bytes are {digest}/{len(data)}, manifest says {entry['sha256']}/{entry['bytes']}")
        if "encryption" in entry:
            if entry["encryption"].get("scheme") == "jwe":
                data = decrypt_jwe(data, keys)
            else:
                data = None
            if data is None:
                continue
            path = path.rsplit(".", 1)[0]  # the plaintext name
        plain[path] = data

    # 4. Paths: case-only collisions anywhere in the archive.
    seen = {}
    for path in sorted(present):
        other = seen.setdefault(path.lower(), path)
        if other != path:
            bad(f"{path}: differs only in case from {other}")

    def page_path(path, prefix):
        name = path[len(prefix):]
        if "encryption" in listed.get(path, {}):
            name = name.rsplit(".", 1)[0]
        if not name.endswith(".md"):
            bad(f"{path}: page files end in .md")
            return None
        name = name[:-3]
        if not re.fullmatch(schemas["memory.page.schema.json"]["$defs"]["path"]["pattern"], name) or len(name) > 255:
            bad(f"{path}: {name!r} is not a valid page path (SPEC §5.1)")
            return None
        return name

    # 5 and 3. Pages, counts and review files.
    ctx = json.loads(plain.get("context.json", b"{}") or b"{}")
    validate("export.context.schema.json", ctx, "context.json")
    known_partitions = {p["name"] for p in ctx.get("partitions", [])}
    known_principals = {p["id"] for p in ctx.get("principals", [])}
    mctx = manifest.get("context", {})
    if ctx.get("kind") != mctx.get("kind") or ctx.get("controller") != mctx.get("controller"):
        bad("context.json: kind or controller differs from the manifest")
    if ctx.get("controller") not in known_principals:
        bad("context.json: the controller is not listed in principals")
    named = set()

    def check_page(path, label):
        data = plain.get(path)
        if data is None:
            return None
        try:
            fm = frontmatter_of(data.decode())
        except ValueError as e:
            bad(f"{label}: {e}")
            return None
        validate("memory.page.schema.json", fm, label)
        if fm.get("partition", "default") not in known_partitions:
            bad(f"{label}: partition {fm.get('partition')!r} is not in context.json")
        named.update(principals_named(fm))
        return fm

    mem = manifest.get("memory", {})
    pages = [p for p in present if p.startswith("memory/")]
    sensitive, unread = 0, 0
    review_counts = {"approved": 0, "proposed": 0, "rejected": 0}
    partition_counts = {}
    for path in sorted(pages):
        if page_path(path, "memory/") is None:
            continue
        fm = check_page(path[:-4] if path.endswith(".jwe") else path, path)
        if fm is None:
            unread += 1
            continue
        sensitive += fm.get("sensitivity") == "sensitive"
        review_counts[fm.get("review", {}).get("state", "approved")] += 1
        part = fm.get("partition", "default")
        partition_counts[part] = partition_counts.get(part, 0) + 1
    if len(pages) != mem.get("page_count"):
        bad(f"memory.page_count is {mem.get('page_count')}, the archive has {len(pages)} page files")
    if unread:
        if not sensitive <= mem.get("sensitive_page_count", 0) <= sensitive + unread:
            bad(f"memory.sensitive_page_count {mem.get('sensitive_page_count')} is impossible ({sensitive} readable sensitive, {unread} unreadable)")
    else:
        if sensitive != mem.get("sensitive_page_count"):
            bad(f"memory.sensitive_page_count is {mem.get('sensitive_page_count')}, the pages say {sensitive}")
        if "review_counts" in mem and {k: mem["review_counts"].get(k, 0) for k in review_counts} != review_counts:
            bad(f"memory.review_counts is {mem['review_counts']}, the pages say {review_counts}")
        if "partition_counts" in mem and mem["partition_counts"] != partition_counts:
            bad(f"memory.partition_counts is {mem['partition_counts']}, the pages say {partition_counts}")
    for key, prefix in (("revisions", "revisions/"), ("history", "history/")):
        files = {e["file"]: e for e in mem.get(key, [])}
        for path in sorted(p for p in present if p.startswith(prefix)):
            if path not in files:
                bad(f"{path}: not listed in memory.{key}")
        for path, e in files.items():
            if path not in present:
                bad(f"memory.{key}: {path} is missing")
                continue
            if not path.startswith(f"{prefix}{e['page']}/"):
                bad(f"memory.{key}: {path} is not under {prefix}{e['page']}/")
            check_page(path, path)

    # Audit, receipts, profile.
    def lines(path):
        data = plain.get(path)
        return [json.loads(l) for l in data.decode().splitlines() if l.strip()] if data is not None else []

    audit = manifest.get("audit", {})
    entries = lines(audit.get("path", "audit/log.jsonl"))
    for n, entry in enumerate(entries, 1):
        validate("audit.entry.schema.json", entry, f"audit line {n}")
        named.update(entry.get(k) for k in ("principal", "on_behalf_of") if entry.get(k))
    if len(entries) != audit.get("entries"):
        bad(f"audit.entries is {audit.get('entries')}, the log has {len(entries)} lines")
    if "erasures" in manifest:
        receipts = lines(manifest["erasures"]["path"])
        for n, receipt in enumerate(receipts, 1):
            validate("erasure.receipt.schema.json", receipt, f"receipt line {n}")
            named.add(receipt.get("requested_by"))
        if len(receipts) != manifest["erasures"]["receipts"]:
            bad(f"erasures.receipts is {manifest['erasures']['receipts']}, the file has {len(receipts)} lines")
    elif any(p.startswith("erasures/") for p in present):
        bad("erasures/ is present but the manifest has no erasures member")
    prof = manifest.get("profile", {})
    if prof.get("path") in plain:
        validate("profile.team.schema.json" if prof["type"] == "team" else "profile.core.schema.json",
                 json.loads(plain[prof["path"]]), prof["path"])
    for n, change in enumerate(lines(prof["changes"]) if "changes" in prof else [], 1):
        validate("export.manifest.schema.json", change, f"profile change {n}", "/$defs/profile_change")
    by_id = {s["$id"]: name for name, s in schemas.items()}
    for ext in prof.get("extensions", []):
        doc = plain.get(ext["path"].rsplit(".", 1)[0] if "encryption" in listed.get(ext["path"], {}) else ext["path"])
        if ext["path"] not in present:
            bad(f"profile.extensions: {ext['path']} is missing")
        elif doc is not None and ext.get("schema") in by_id:
            validate(by_id[ext["schema"]], json.loads(doc), ext["path"])

    # 6. References.
    for principal in sorted(named - known_principals):
        bad(f"principal {principal} is named in the archive but not listed in context.json")

    # Extensions and connections.
    ext_dirs = [e["path"] for e in manifest.get("extensions", [])]
    for path in sorted(p for p in present if p.startswith("extensions/")):
        if not any(path.startswith(d) for d in ext_dirs):
            bad(f"{path}: under extensions/ but no manifest extension owns it")
    for d in ext_dirs:
        if not any(p.startswith(d) for p in present):
            bad(f"extensions: {d} holds no files")
    for conn in manifest.get("connections", []):
        if "path" in conn and conn["path"] not in present:
            bad(f"connections: {conn['path']} is missing")
    return problems


def main():
    schemas, registry = load_schemas()
    print(f"{len(schemas)} schemas valid (Draft 2020-12): {', '.join(schemas)}")
    failures, checked = 0, 0
    # SPEC §6.2: model APIs reject top-level combinators in an inputSchema.
    for name, sub in schemas.get("tools.schema.json", {}).get("$defs", {}).items():
        if name.endswith("_input") and name != "frontmatter_input" and (set(sub) & {"oneOf", "anyOf", "allOf"} or sub.get("type") != "object"):
            failures += 1
            print(f"FAIL tools.schema.json#/$defs/{name}: inputSchema top level must be a plain object schema")
    export = EXAMPLES / "export"
    for path in sorted(EXAMPLES.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or export in path.parents:
            continue
        expect_valid = "invalid" not in path.relative_to(EXAMPLES).parts
        name, pointer = target(path)
        v = validator(schemas, registry, name, pointer)
        for label, instance in instances(path):
            checked += 1
            errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
            rel = path.relative_to(ROOT)
            if expect_valid and errors:
                failures += 1
                print(f"FAIL {rel} ({label}):")
                for e in errors:
                    print(f"   {'/'.join(map(str, e.path)) or '<root>'}: {e.message}")
            elif not expect_valid and not errors:
                failures += 1
                print(f"FAIL {rel} ({label}): expected to be invalid, but it validates")
            else:
                print(f"ok   {rel} ({label}){'' if expect_valid else ' rejected as expected'}")
    keys_file = export / "example-keys.json"
    keys = json.loads(keys_file.read_text())["keys"] if keys_file.exists() else {}
    for manifest in sorted(export.rglob("manifest.json")):
        root = manifest.parent
        rel = root.relative_to(ROOT)
        expect_valid = "invalid" not in root.relative_to(export).parts
        problems = check_archive(root, schemas, registry, keys)
        checked += 1
        if expect_valid and problems:
            failures += 1
            print(f"FAIL archive {rel}:")
            for p in problems:
                print(f"   {p}")
        elif not expect_valid and not problems:
            failures += 1
            print(f"FAIL archive {rel}: expected to fail the SPEC §8.3 checks, but it passes")
        else:
            files = len(json.loads(manifest.read_text()).get("files", []))
            note = f"rejected as expected: {problems[0]}" if problems else f"{files} files, hashes and counts check"
            print(f"ok   archive {rel} ({note})")
    print(f"{checked} instances checked, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
