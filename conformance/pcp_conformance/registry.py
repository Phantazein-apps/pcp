"""Requirement ids, checks and results.

Requirements come from docs/conformance.md, so the suite and the document
cannot drift apart: a check that cites an unknown id, or an id marked for
the suite (S or S+) that no check cites, fails the self-check.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
REQUIREMENTS_DOC = ROOT / "docs" / "conformance.md"

ROW = re.compile(r"^\|\s*([A-Z]+-\d+)\s*\|\s*(MUST|SHOULD)\s*\|(.*?)\|\s*([\d., ]+)\s*\|\s*([^|]+?)\s*\|\s*([A-Z+]+)\s*\|\s*$")


class Requirement:
    def __init__(self, rid, level, text, section, profile, check):
        self.id, self.level, self.text = rid, level, text.strip()
        self.section, self.profile, self.check = section.strip(), profile, check

    @property
    def suite(self):
        return self.check in ("S", "S+")


def load_requirements(path=REQUIREMENTS_DOC):
    reqs = {}
    for line in path.read_text().splitlines():
        m = ROW.match(line)
        if m:
            r = Requirement(*m.groups())
            if r.id in reqs:
                raise ValueError(f"duplicate requirement id {r.id}")
            reqs[r.id] = r
    return reqs


CHECKS = []
STANDARD_TOOLS = (
    "profile_get", "profile_update", "memory_search", "memory_read", "memory_list",
    "memory_write", "memory_propose", "review_list", "review_resolve", "partition_list",
    "context_brief", "audit_list", "export_create", "erase_request",
)


def check(*ids, tools=(), writes=False, needs=()):
    """Registers a check function covering requirement ids.

    tools: standard tools the check exercises (for the tool coverage rule).
    writes: the check writes test data and runs only with --allow-writes.
    needs: other preconditions, reported when they are missing.
    """
    def deco(fn):
        fn.ids, fn.tools, fn.writes, fn.needs = ids, tools, writes, needs
        CHECKS.append(fn)
        return fn
    return deco


class Finding:
    def __init__(self, rid, status, message=""):
        self.id, self.status, self.message = rid, status, message

    def as_dict(self):
        return {"id": self.id, "status": self.status, "message": self.message}


class Skip(Exception):
    """Raised by a check whose preconditions are missing."""


class Recorder:
    """Collects findings for one check run."""

    STATUSES = ("pass", "fail", "warn", "skip", "manual")

    def __init__(self, reqs, check_name):
        self.reqs, self.check_name, self.findings = reqs, check_name, []

    def _add(self, rid, status, message):
        if rid not in self.reqs:
            raise KeyError(f"{self.check_name} cites unknown requirement {rid}")
        if status == "fail" and self.reqs[rid].level == "SHOULD":
            status = "warn"
        self.findings.append(Finding(rid, status, message))

    def ok(self, rid, message=""):
        self._add(rid, "pass", message)

    def fail(self, rid, message):
        self._add(rid, "fail", message)

    def expect(self, rid, cond, message_if_false, message_if_true=""):
        (self.ok if cond else self.fail)(rid, message_if_true if cond else message_if_false)
        return cond

    def skip(self, rid, message):
        self._add(rid, "skip", message)


def self_check(reqs):
    """Coverage rules. Returns a list of problems."""
    problems = []
    cited = set()
    tools = set()
    for fn in CHECKS:
        for rid in fn.ids:
            if rid not in reqs:
                problems.append(f"{fn.__name__} cites unknown requirement {rid}")
            cited.add(rid)
        tools.update(fn.tools)
    for rid, r in reqs.items():
        if r.suite and rid not in cited:
            problems.append(f"{rid} is marked {r.check} in docs/conformance.md but no check cites it")
    for t in STANDARD_TOOLS:
        if t not in tools:
            problems.append(f"standard tool {t} has no check")
    return problems
