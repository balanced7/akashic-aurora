"""Recall domains — the boundary line, and why it is not a tag.

Daniil, 2026-08-02: "divide the boundary lines so we can get the same help for aurora for these
kinds of help as we would when working on the system itself" and then, decisively, "ideally I
wouldn't want to build another system, I would want recall to be domain aware and enable cross
domain learning eventually."

A DOMAIN IS A TRIPLE, NOT A LABEL: (what TRIGGERS retrieval, what it is KEYED by, what EVIDENCE
settles a lesson). That distinction is the whole design. A flat `domain` string on each record
would fix only the KEY and leave the other two wrong -- recall-at would still fire only on file
paths and shell commands (system-shaped triggers, so a shader gesture has no trigger surface at
all), and a shader claim would still be "settled" by whatever settles a code claim. The atom shape
stays identical across domains, which is what keeps this ONE system rather than two.

THE DECISION RULE, and it is decidable at write time: A LESSON BELONGS TO THE DOMAIN WHOSE EVIDENCE
SETTLES IT. "Static assets must send no-store" was LEARNED during vfx work, but a test settles it,
so it is system. "Snapshots must composite on the console ground, because claude judges them
against the background they live on" is settled by looking at a render, so it is vfx.

CROSS-DOMAIN LEARNING (the "eventually") needs no new machinery: domains partition RANKING, not the
corpus. In-domain first; when in-domain retrieval is thin, other-domain hits are admitted LABELLED
so they read as analogy rather than instruction; and a lesson credited useful in >=2 domains is
promoted to domain-general. That is the existing funnel measured across a boundary.
"""
from __future__ import annotations

import re
from typing import Any, Dict

DEFAULT_DOMAIN = "system"

DOMAINS: Dict[str, Dict[str, Any]] = {
    "system": {
        "triggers": ["file path", "shell command", "tool call"],
        "keys": ["text over code and tooling vocabulary"],
        "evidence": "a test or a pin settles it",
        # Markers are for BACKFILL INFERENCE only -- ~840 existing lessons carry no domain and are
        # never going to be hand-labelled. They are not the definition of the domain; the evidence
        # rule above is.
        "markers": [
            "bifrost", "lane", "redis", "pytest", "hook", "commit", "git", "ledger", "store",
            "handoff", "runner", "seat", "mailbox", "daemon", "cursor", "acl", "registry",
            "powershell", "subprocess", "endpoint", "schema", "migration", "pin", "regression",
        ],
    },
    "vfx": {
        "triggers": ["composition gesture (add chunk, set param, pick palette, compose)",
                     "the bench's current subject"],
        "keys": ["effect", "parameter range", "subject kind"],
        "evidence": "a render you looked at settles it",
        "markers": [
            "shader", "glsl", "frag", "chunk", "vfx", "render", "palette", "hue", "chroma",
            "luminance", "vignette", "tonemap", "tone", "dither", "glow", "bloom", "tile",
            "gap", "wireframe", "geodesic", "avatar", "sprite", "canvas", "webgl", "raymarch",
            "shadertoy", "swirl", "kaleido", "blend", "mask", "uv", "pixel", "colour", "color",
        ],
    },
}

# Paths are the strongest signal available and they beat vocabulary, because a lesson ABOUT the vfx
# bench often uses system words (endpoint, commit, test) while sitting squarely in the vfx domain.
_PATH_HINTS = (
    ("vfx", re.compile(r"(design/vfx|vfx-chunks|vfx-sketches|vfx_render|vfx_ingest|vfx\.html|"
                       r"agent-avatar|\.glsl|\.frag)", re.I)),
)

_WORD = re.compile(r"[a-z0-9_]+")


def _text_of(record: Dict[str, Any]) -> str:
    if not isinstance(record, dict):
        return str(record or "")
    parts = [str(record.get(k) or "") for k in
             ("experiment_name", "what_tried", "expected_outcome", "actual_outcome",
              "recommendation", "root_cause", "category", "anti_pattern")]
    return " ".join(parts).lower()


def infer_domain(record: Dict[str, Any]) -> str:
    """Best-effort domain for a lesson that did not declare one.

    Deliberately biased toward DEFAULT_DOMAIN. The backfill runs over ~840 existing lessons that
    were all written before domains existed, and every one of them currently MEANS "system" by
    construction. A confident guess that relabels eight hundred of them into a domain nobody
    checked would be worse than the flat corpus we are fixing -- so an unknowable record stays
    system, and only a clear signal moves it.
    """
    text = _text_of(record)
    if not text.strip():
        return DEFAULT_DOMAIN
    for name, pat in _PATH_HINTS:
        if pat.search(text):
            return name
    tokens = set(_WORD.findall(text))
    scores = {name: sum(1 for m in spec["markers"] if m in tokens)
              for name, spec in DOMAINS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return DEFAULT_DOMAIN
    # A tie, or a bare one-word brush with a non-default domain, is not evidence. Require the
    # winner to actually beat the default rather than merely draw with it.
    if best != DEFAULT_DOMAIN and scores[best] <= scores.get(DEFAULT_DOMAIN, 0):
        return DEFAULT_DOMAIN
    return best


def valid_domain(name: str) -> bool:
    return str(name or "") in DOMAINS
