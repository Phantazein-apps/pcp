"""Shared types and constants for the spike.

Every page in the corpus is rendered from `Fact` records, so the gold answer
for a question is exact by construction rather than annotated afterwards.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Any

SEED = 20260909

# ---------------------------------------------------------------- scopes ----
# Scope bundles, expressed in the SPEC.md §7.1 grammar. A bundle is what the
# harness CLI's --scope names; it expands to the set of atomic scopes granted.
SCOPE_BUNDLES: dict[str, list[str]] = {
    # §7.2 RECOMMENDED default grant for a new chat client.
    "default": ["profile.core:read", "memory:read"],
    "health": ["profile.core:read", "memory:read", "profile.health:read", "memory.sensitive:read"],
    "finance": ["profile.core:read", "memory:read", "profile.finance:read", "memory.sensitive:read"],
    "home": ["profile.core:read", "memory:read", "profile.home:read", "memory.sensitive:read"],
    "full": [
        "profile.core:read", "memory:read", "memory.sensitive:read",
        "profile.health:read", "profile.finance:read", "profile.home:read",
        "profile.legal:read",
    ],
}

# Which profile extension namespace each scope bundle may read (§4.2/§4.3).
BUNDLE_NAMESPACES: dict[str, list[str]] = {
    "default": ["profile.core"],
    "health": ["profile.core", "pcp.health"],
    "finance": ["profile.core", "pcp.finance"],
    "home": ["profile.core", "pcp.home"],
    "full": ["profile.core", "pcp.health", "pcp.finance", "pcp.home", "pcp.legal"],
}

DOMAINS = [
    "people", "work", "projects", "finances", "health",
    "vehicles", "travel", "preferences", "home",
]

# SPEC.md §5.1 lifecycle enum, verbatim. The spike does NOT extend it.
# Supersession is modelled ONLY as the spec models it: a typed relations
# edge, `{rel: "supersedes", target: <page path>}`, on the NEWER page.
# Following that edge is a join -- see NOTES.md §2.1 for why that matters.
LIFECYCLES = ["active", "validated", "stale", "archived"]
LIFECYCLE_DEFAULT_VISIBLE = {"active", "validated"}

TYPES = ["episodic", "semantic", "procedural"]
STRATA = [
    "exact_lookup", "paraphrase", "multi_hop",
    "temporal", "negative", "scope_restricted",
]

TODAY = "2026-09-09"


@dataclass
class Fact:
    """One atomic, checkable assertion. The unit of ground truth."""
    id: str
    domain: str
    subject: str
    predicate: str
    obj: str                      # the gold answer string
    page: str                     # path of the page that carries it
    lifecycle: str = "active"
    sensitivity: str = "normal"   # normal | sensitive
    valid_from: str | None = None
    valid_until: str | None = None
    confidence: float | None = None
    namespace: str | None = None  # profile extension gating this fact, if any
    supersedes: str | None = None  # page path this fact's page supersedes
    aliases: list[str] = field(default_factory=list)  # other acceptable answers

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Page:
    """A PCP memory page: SPEC.md §5.1 frontmatter + a markdown body."""
    path: str
    title: str
    updated: str
    type: str
    domain: str
    body: str
    tags: list[str] = field(default_factory=list)
    sensitivity: str = "normal"
    lifecycle: str = "active"
    confidence: float | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    source: dict[str, str] | None = None
    derived_from: list[str] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    namespace: str | None = None   # extension namespace gating this page
    facts: list[str] = field(default_factory=list)  # Fact ids carried here

    # ---- derived -----------------------------------------------------
    def default_visible(self) -> bool:
        """Visible under SPEC.md §5.2 default retrieval policy."""
        if self.lifecycle not in LIFECYCLE_DEFAULT_VISIBLE:
            return False
        if self.valid_until and self.valid_until < TODAY:
            return False
        return True

    def frontmatter(self) -> dict[str, Any]:
        fm: dict[str, Any] = {"title": self.title, "updated": self.updated}
        fm["type"] = self.type
        if self.tags:
            fm["tags"] = list(self.tags)
        if self.sensitivity != "normal":
            fm["sensitivity"] = self.sensitivity
        fm["lifecycle"] = self.lifecycle
        if self.confidence is not None:
            fm["confidence"] = self.confidence
        if self.valid_from:
            fm["valid_from"] = self.valid_from
        if self.valid_until:
            fm["valid_until"] = self.valid_until
        if self.source:
            fm["source"] = dict(self.source)
        if self.derived_from:
            fm["derived_from"] = list(self.derived_from)
        if self.relations:
            fm["relations"] = [dict(r) for r in self.relations]
        return fm

    def render(self) -> str:
        import yaml
        fm = yaml.safe_dump(self.frontmatter(), sort_keys=False, allow_unicode=True).rstrip()
        return f"---\n{fm}\n---\n\n{self.body.strip()}\n"


# ------------------------------------------------------- token utilities ----
_STOP = {
    "a", "an", "the", "of", "to", "in", "on", "at", "for", "with", "and", "or",
    "is", "are", "was", "were", "be", "been", "am", "do", "does", "did", "has",
    "have", "had", "what", "which", "who", "whom", "whose", "when", "where",
    "why", "how", "that", "this", "these", "those", "it", "its", "as", "by",
    "from", "up", "out", "if", "then", "than", "so", "there", "their", "they",
    "s", "t", "my", "me", "i", "you", "your", "he", "she", "him", "her", "his",
    "hers", "we", "us", "our", "not", "no", "any", "all", "some", "more",
    "most", "other", "into", "over", "under", "about", "after", "before",
    "does", "doing", "done", "can", "could", "should", "would", "will",
    "currently", "current", "now", "today", "please", "tell", "list", "give",
}


def stem(tok: str) -> str:
    """Very light suffix stripping -- enough to catch plural/tense overlap."""
    for suf in ("ing", "ies", "ied", "es", "ed", "s"):
        if len(tok) > 4 and tok.endswith(suf):
            base = tok[: -len(suf)]
            if suf == "ies":
                base += "y"
            return base
    return tok


def content_tokens(text: str) -> set[str]:
    """Lowercased, stopworded, lightly stemmed content tokens."""
    raw = re.findall(r"[a-z0-9]+", text.lower())
    return {stem(t) for t in raw if t not in _STOP and len(t) > 1}


def stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]
