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

Files under an invalid/ subdirectory must FAIL validation.

Frontmatter is parsed with YAML 1.2 core-schema semantics for timestamps
(they stay strings), as SPEC §5.2 requires.

Usage: python3 scripts/validate_schemas.py [version]   (default 0.3)
Requires: pip install jsonschema pyyaml
"""
import json
import pathlib
import re
import sys

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = sys.argv[1] if len(sys.argv) > 1 else "0.3"
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


def main():
    schemas, registry = load_schemas()
    print(f"{len(schemas)} schemas valid (Draft 2020-12): {', '.join(schemas)}")
    failures, checked = 0, 0
    # SPEC §6.2: model APIs reject top-level combinators in an inputSchema.
    for name, sub in schemas.get("tools.schema.json", {}).get("$defs", {}).items():
        if name.endswith("_input") and name != "frontmatter_input" and (set(sub) & {"oneOf", "anyOf", "allOf"} or sub.get("type") != "object"):
            failures += 1
            print(f"FAIL tools.schema.json#/$defs/{name}: inputSchema top level must be a plain object schema")
    for path in sorted(EXAMPLES.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
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
    print(f"{checked} instances checked, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
