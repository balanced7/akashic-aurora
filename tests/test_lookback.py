"""
P7 / T027 -- lookback: one question over the rationale corpus. THE pillar's closing pin.

Bar: the DUAL PRE-REGISTERED battery (tests/data/lookback_battery_*.md, committed at
b49fb47 + 0d42832 BEFORE implementation existed -- the F0 fence) passes: every probe's
expected artifact appears in the returned hits (per_layer=3 == top-3 by construction).
Unit pins cover the three root-caused mechanisms: morphology-tolerant relevance (the
Ranker's designed relevance_fn seam), reference-class doc exclusion, and fail-soft layers.

Run: py -m pytest tests/test_lookback.py -q   (integration probes need the real repo corpus)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.lookback import REFERENCE_DOCS, _stem_relevance, lookback

BATTERY = [
    ("C1", "why is the bifrost bus ephemeral instead of durable",
     ["comms-pillar-synthesis", "coordination-plan-synthesis"]),
    ("C2", "why is there no permanent per-agent file ownership",
     ["AGENTS.md", "master-directive-list"]),
    ("C3", "why are project notes write-once and corrected by superseding instead of editing",
     ["d6153c2", "memory.md", "notes supersession"]),
    ("C4", "why does the lesson forge gate edits behind a replay audit",
     ["lesson-forge-design", "forge-f0-audit"]),
    ("C5", "what happened to the GPT experiment-pivot analysis from early july",
     ["experiment-pivot-gpt-analysis", "SAVE THIS", "1783256159"]),
    ("C6", "why does the wake listener detect messages without consuming them",
     ["p0-wake-detect-design", "deepseek-p0-design-review", "d925d6b"]),
    ("D1", "why is the bus ephemeral and not a durable message queue",
     ["claude-comms-pillar-fenced", "comms-pillar-synthesis"]),
    ("D2", "why were CRDTs and consensus rejected for agent coordination",
     ["claude-comms-pillar-fenced", "coordination-plan-synthesis"]),
    ("D3", "why is the task ledger the coordination substrate instead of the message stream",
     ["coordination-plan-synthesis"]),
    ("D4", "what governs which bus messages survive a restart and why those kinds",
     ["comms-pillar-synthesis", "bifrost:"]),
    ("D5", "where did the forge blind the optimizer to its own contexts rule come from",
     ["74d6e0d", "5562014"]),
    ("D6", "why is the where-we-are note write-once superseded by re-noting the same title",
     ["comms-pillar-status", "where-we-are", "mem:decision"]),
]


def test_the_preregistered_battery_passes():
    """Runs against the CANONICAL corpus via subprocess (read-only; counters killed): the
    battery probes real history by design, which the suite's sandbox deliberately empties
    (same hermeticity lesson as the P2 cold-start drill, inverted)."""
    import json
    import subprocess
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ, "AI_SETUP": repo, "REDIS_DB": "0",
           "AKASHIC_LOOKBACK_NO_COUNT": "1"}
    failures = []
    for tag, q, expects in BATTERY:
        p = subprocess.run([sys.executable, "agent_cli.py", "lookback", *q.split(), "--json"],
                           cwd=repo, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120, env=env)
        try:
            hits = json.loads(p.stdout or "[]")
        except ValueError:
            hits = []
        blob = " | ".join(f"{h['layer']}:{h['source']}:{h['excerpt']}" for h in hits).lower()
        if not any(exp.lower() in blob for exp in expects):
            failures.append(f"{tag}: {q[:60]} -> expected one of {expects}")
    assert not failures, "battery probes failed:\n" + "\n".join(failures)


def test_stem_relevance_tolerates_morphology():
    assert _stem_relevance("notes supersession wired", "why superseding notes") > 0
    assert _stem_relevance("completely unrelated text", "why superseding notes") == 0.0
    assert _stem_relevance("anything", "a an of") == 0.0, "no meaningful terms -> 0"


def test_stem_relevance_about_beats_mentions():
    """S5 pin (battery sec. 3b): a LONG doc that mentions each query term once (a
    vocabulary catalog) must score BELOW a long doc that discusses them repeatedly.
    Coverage alone tied them; concentration separates about-X from mentions-X."""
    q = "why is the bifrost bus ephemeral"
    filler = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod " * 60
    catalog = f"bifrost ephemeral {filler}"                       # one mention each, ~4.3KB
    discussion = ("the bifrost bus stays ephemeral because durable state belongs to the "
                  "ledger; bifrost transports, the store remembers. ephemeral streams trim; "
                  "the bus is a doorbell. bifrost ephemeral bus, not a database. ") * 12 + filler
    assert _stem_relevance(discussion, q) > _stem_relevance(catalog, q), \
        "repeated on-topic use must outrank one-mention cataloging in long texts"


def test_stem_relevance_short_text_single_mention_keeps_full_weight():
    """S5 must NOT tax short corpora (commits, notes, promoted excerpts): under one
    TF_LEN_UNIT a single mention is a full-weight match -- pre-S5 behavior exactly."""
    assert _stem_relevance("notes supersession wired", "why superseding notes") == \
        _stem_relevance("notes supersession wired supersession supersession",
                        "why superseding notes"), \
        "short texts: concentration is saturated at one occurrence"


def test_reference_docs_never_appear():
    hits = lookback("what does the bus transport layer terminology mean")
    sources = {h["source"] for h in hits}
    for ref in REFERENCE_DOCS:
        assert not any(ref in s for s in sources), f"{ref} is reference, not rationale"


def test_empty_question_and_layer_narrowing():
    assert lookback("") == []
    only_git = lookback("wake listener detect consume", layers=["git"])
    assert only_git and all(h["layer"] == "git" for h in only_git)


def test_hits_carry_drill_pointers_and_status():
    hits = lookback("why does the lesson forge gate edits behind a replay audit")
    assert hits
    for h in hits:
        assert h["drill"], "every hit must be drillable"
        assert h["status"], "every hit carries its currency/kind label"
