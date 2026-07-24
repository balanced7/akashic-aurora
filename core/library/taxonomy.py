"""Taxonomy constants + the birth-door classifier (A1, homes-and-order round).

Spec: docs/taxonomy-ergonomics-reconciliation-2026-07.md (ratified 2026-07-23; Daniel's
gate verbatim in research/briefs/taxonomy-ergonomics-think-pass-2026-07-23.md).

Bootstrap posture: the roster lives here as code-loaded data until A3, when it migrates
into a governed taxonomy atom (the reconciliation, section 7). Growing the roster goes
through the propose-category door + Daniel's gate -- never an inline edit here (T034
cap + deletion ritual; the audit library domain flags orphans and sprawl).
"""

from __future__ import annotations

import re

# --- The three planes (never blurred): TYPE = kind (LIBRARY.md canon) · ARC = campaign
# --- (ledger authority) · CATEGORY = aboutness (this roster). 1-3 per atom, PRIMARY first.

CATEGORY_ROSTER: tuple[str, ...] = (
    "substrate", "migration", "library", "recall", "memory", "bus",
    "coordination", "agent-lifecycle", "identity", "security", "method",
    "conducting", "governance", "audit", "testing", "tooling",
    "ergonomics", "ui", "wiki", "voice", "optics", "performance",
    "frontier", "narrative",
)

CATEGORY_CAP_PER_ATOM = 3

# Census/legacy terms resolve through these folds (reconciliation section 1) so the
# 184-file census and older headers classify without inventing roster entries.
CATEGORY_FOLDS: dict[str, str] = {
    "reasoning": "memory", "knowledge-stack": "memory", "resilience": "agent-lifecycle",
    "ops": "agent-lifecycle", "backup": "substrate", "secrets": "security",
    "mcp": "tooling", "search": "wiki", "fleet": "bus", "story": "narrative",
    "design-methodology": "method", "research": "frontier", "spend": "performance",
    "bench": "performance", "visualgen": "ui", "wishlist": "ergonomics",
    "onboarding": "ergonomics",
}

# --- Typed edges (T103 G4). Grows ONLY by the T034 ritual; supersession rides its own
# --- first-class fields (supersedes/superseded), never a rel entry.
REL_ROSTER: tuple[str, ...] = ("derives-from", "contradicts", "supports", "discusses", "cites")
REL_DEFAULT_BACKFILL = "discusses"  # weakest honest claim for migration-era backfill

# --- Conversation-atom provenance (kimi's authority law: authority derives from
# --- (type, origin, settled) -- never from prose confidence).
ORIGINS: tuple[str, ...] = ("authored", "conversation", "ruling", "migrated")
SETTLED_STATES: tuple[str, ...] = ("live", "settled", "ruled")

# --- The birth-door keyword classifier (deepseek spec, extended to cover the roster).
# --- Order matters only for tie-breaks; ALL matches return, confidence-ordered.
CATEGORY_KEYWORDS: dict[str, str] = {
    "substrate": r"substrate|atom|projection|jsonl|store\b|durab|snapshot|restore",
    "migration": r"migrat|sweep|census|enrich|backfill|strangler|p0|p3",
    "library": r"library|shelf|shelv|taxonom|filing|home\b|naming|canon|index",
    "recall": r"recall|retriev|funnel|knowledge.?map|curator|inject",
    "memory": r"memory|note[s]?\b|lesson|decision|reasoning|spine|chapter",
    "bus": r"\bbus\b|bifrost|packet|lane|routing|dedup|stream|handoff|wake",
    # 'ledger'/'conductor' pruned 2026-07-23: over-generic tokens (they name a TYPE and a
    # role) stamped the first-light dogfood falsely -- kimi gem, fence round 1.
    "coordination": r"coordinat|lock\b|barrier|control.?plane|negotiat",
    "agent-lifecycle": r"runner|daemon|seat|liveness|hook|crash|recover|reviv|watchdog",
    "identity": r"identity|roster|acl|grant|tenan|quarantine|persona",
    "security": r"security|secret|credential|trust|auth|admin|escalat",
    "method": r"method|baseline|fence|dual.?pass|kill.?drill|blind.?hal|reconcil|protocol",
    "conducting": r"conduct|directive|charter|brief|round\b|gate\b|delegat",
    "governance": r"governance|ruling|ratif|supersession.?law|verdict|approv",
    "audit": r"audit|drift|belief.?vs.?state|lint|photograph|observab",
    "testing": r"test|pin[s]?\b|probe|kata|verif|mojibake|regression",
    "tooling": r"tool|verb\b|mint|sugar|alias|kit\b|mcp|door[s]?\b",
    "ergonomics": r"ergonomic|friction|wishlist|boot|primer|onboard|dx\b",
    "ui": r"\bui\b|console|pane|card|render|theme|glass|viz|svg|diagram",
    "wiki": r"wiki|graph\b|backlink|hop\b|hierarch|bases|obsidian|constellation",
    "voice": r"voice|tone|goodhart|casino|keynote|restraint|typograph",
    "optics": r"optic|portfolio|public.?face|github.?face|readme|journey",
    "performance": r"perf|latenc|throughput|cold.?open|bench|spend|cost|budget|frugal",
    "frontier": r"frontier|prior.?art|sota|survey|outside|gemini|karpathy|scan",
    "narrative": r"narrative|chronicle|story|reflection|night.?plan|journal",
}


def classify(text: str, cap: int = CATEGORY_CAP_PER_ATOM) -> list[str]:
    """Suggest up to ``cap`` roster categories for a title/heading/snippet.

    Confidence order: whole-word match beats substring match, then earlier roster
    position tie-breaks (stable, deterministic -- the door shows every suggestion and
    the agent confirms; a wrong stamp is a post-hoc lint fix, never a write-time block).
    """
    if not text:
        return []
    hay = text.lower()
    scored: list[tuple[int, int, str]] = []
    for pos, cat in enumerate(CATEGORY_ROSTER):
        pattern = CATEGORY_KEYWORDS[cat]
        word_hit = re.search(r"(?:^|[^a-z0-9])(?:" + pattern + r")", hay)
        if word_hit:
            scored.append((0, pos, cat))
        elif re.search(pattern, hay):
            scored.append((1, pos, cat))
    scored.sort()
    if not scored:
        return []
    # kimi gem ruling (fence round 1): slot 1 as-is; slots 2..cap require a WORD match
    # (tier 0) -- a weak substring hit can never fill a trailing slot, killing
    # false-positive category padding without blunting genuinely multi-category atoms.
    picked = [scored[0][2]]
    picked += [cat for tier, _, cat in scored[1:] if tier == 0][: max(0, cap - 1)]
    return picked[:cap]


def resolve(term: str) -> str | None:
    """Resolve a candidate category term to a roster entry (folds honored), else None."""
    t = (term or "").strip().lower()
    if t in CATEGORY_ROSTER:
        return t
    return CATEGORY_FOLDS.get(t)
