"""world_seed -- authoritative state flows DOWN, and says what it refused to carry.

WHY THIS EXISTS. A twin with an empty brain cannot test anything realistic. Alpha booted
with 0 keys against prod's 19,850: every recall returns nothing, every boot renders empty,
and the behaviours most worth exercising are precisely the ones that need a populated
memory. So state must flow down -- prod -> beta -> alpha, never the reverse.

DIRECTION IS NOT NEGOTIABLE. Downward is a copy; upward is a claim. Seeding down is safe
because the higher tier is authoritative by definition. Promoting up is NOT the mirror
operation and must never be implemented by pointing this module the other way: a lesson
learned in alpha contains alpha's interpretation of alpha's mutant code, so it is not a
replayable input. The upward path is re-litigation (ground the claim against the higher
tier's OWN store, or file it as a provenance-tagged rumor), and it lives elsewhere.
That asymmetry is the whole design; a `--from alpha --to prod` would quietly destroy it,
so it is refused rather than documented against.

WHAT DOES NOT RIDE DOWN, and why -- measured against prod's live keyspace 2026-08-14:

    bifrost:*   7,740 keys   TRANSPORT AND IDENTITY. Stream cursors, seat presence,
                             runner locks, incarnation keys. An alpha that inherits prod's
                             cursors believes it has already consumed mail it never saw;
                             an alpha that inherits presence keys claims to be seats that
                             are not running in it. This is the single most dangerous class
                             and it is the largest one, which is why the default is a
                             KNOWLEDGE allowlist rather than a transport denylist -- a
                             denylist silently ships every new prefix nobody classified.

    recall:*      800 keys   DERIVED RANKING STATE. Rebuildable from learn:, and copying it
                             imports prod's tuning as though alpha had earned it. Opt-in.

    events:*    4,740 keys   THE DURABLE SALIENT PLANE. Genuinely knowledge, but its records
                             pair with bifrost stream ids, so seeding it without transport
                             yields records pointing at cursors that do not exist here.
                             Opt-in, and the flag says that out loud.

THE REPORTING CONTRACT (the Dawe Test, adopted 2026-08-13). A seed that reports only what it
copied is a RESPONSE. This one reports what it REFUSED to copy and why, because the excluded
classes are the ones that will surprise someone at 3am. "Copied 3,397 keys" is fluent and
tells you nothing about whether your twin will behave.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

#: Tier order. A world may only be seeded FROM a strictly higher tier.
TIERS = {"prod": 3, "beta": 2, "alpha": 1}

#: Knowledge classes, as an ALLOWLIST. A new prefix nobody classified stays home by
#: default -- the opposite choice ships unclassified state on every future slice.
KNOWLEDGE_PREFIXES = (
    "learn:",          # lessons -- the thing a twin most needs to behave like the house
    "mem:",            # decisions, notes, where-we-are
    "narr:",           # the narrative spine (Atlas/Track/Chapter/Beat)
    "artifact:",       # artifacts
    "knowledge_map:",
    "residents:",
    "lookback:",
)

#: Opt-in classes, each with the sentence a human needs before saying yes.
OPTIONAL_PREFIXES = {
    "events": ("events:", "the durable salient plane; its records reference bifrost stream "
                          "ids that will NOT exist in the target"),
    "recall": ("recall:", "derived ranking state; rebuildable from learn:, and importing it "
                          "gives the twin prod's tuning as though it had earned it"),
}

#: Never seeded, with the reason rendered in every report.
REFUSED_PREFIXES = {
    "bifrost:": "transport and identity -- cursors, presence, runner locks. An inherited "
                "cursor makes the twin believe it consumed mail it never saw.",
}


#: Where a seeded world records what it inherited. Deliberately under a prefix that is NOT in
#: KNOWLEDGE_PREFIXES, so a manifest never rides down into the next world and claim a lineage
#: that is not its own.
MANIFEST_KEY = "world:seed:manifest"


class SeedRefusal(RuntimeError):
    """A seed was refused. Always carries why, and what would be legal instead."""


@dataclass
class SeedPlan:
    source: str
    target: str
    include: List[str] = field(default_factory=list)
    prefixes: List[str] = field(default_factory=list)
    #: prefix -> reason, for everything deliberately left behind.
    excluded: Dict[str, str] = field(default_factory=dict)

    def render(self, counts: Optional[Dict[str, int]] = None, applied: bool = False) -> str:
        head = "SEEDED" if applied else "PLAN (dry run -- pass apply=True to write)"
        lines = [f"{head}: {self.source} -> {self.target}"]
        lines.append("  CARRIED:")
        for p in self.prefixes:
            n = f"{counts.get(p, 0):>7,} keys" if counts else "      ? keys"
            lines.append(f"    {n}  {p}*")
        lines.append("  REFUSED (this is the half that surprises people):")
        for p, why in sorted(self.excluded.items()):
            n = f"{counts.get(p, 0):>7,} keys" if counts and p in counts else "        "
            lines.append(f"    {n}  {p}* -- {why}")
        return "\n".join(lines)


def plan(source: str, target: str, include: Optional[List[str]] = None) -> SeedPlan:
    """Build and validate a seed plan. Raises SeedRefusal rather than guessing."""
    include = list(include or [])

    for name, role in ((source, "source"), (target, "target")):
        if name not in TIERS:
            raise SeedRefusal(
                f"{role} {name!r} is not a world (legal: {', '.join(TIERS)})")

    if target == "prod":
        raise SeedRefusal(
            "refusing to seed INTO prod. Downward is a copy; upward is a claim. A lesson "
            "learned in a twin contains that twin's interpretation of its own mutant code, "
            "so it is not a replayable input and must not arrive as bulk state.\n"
            "  The upward path is re-litigation: the higher tier grounds the claim against "
            "its OWN store, or files it as provenance-tagged and grounded:false -- a rumour, "
            "not a fact.")

    if source == target:
        raise SeedRefusal(f"source and target are both {source!r}; nothing to do")

    if TIERS[source] <= TIERS[target]:
        raise SeedRefusal(
            f"refusing to seed {source} -> {target}: a world may only be seeded from a "
            f"strictly HIGHER tier (prod > beta > alpha). {target} is not below {source}.")

    prefixes = list(KNOWLEDGE_PREFIXES)
    excluded = dict(REFUSED_PREFIXES)
    for key, (prefix, why) in OPTIONAL_PREFIXES.items():
        if key in include:
            prefixes.append(prefix)
        else:
            excluded[prefix] = f"{why} (opt in with include=['{key}'])"

    unknown = [k for k in include if k not in OPTIONAL_PREFIXES]
    if unknown:
        raise SeedRefusal(
            f"unknown include {unknown} (legal: {', '.join(OPTIONAL_PREFIXES)}). "
            f"Transport is never includable: {', '.join(REFUSED_PREFIXES)}")

    return SeedPlan(source=source, target=target, include=include,
                    prefixes=prefixes, excluded=excluded)


def write_manifest(dst, plan: SeedPlan, counts: Dict[str, int], when: str) -> dict:
    """Record in the TARGET what it inherited, from where, and when.

    THE HOLE THIS PARTIALLY FILLS, stated plainly because it is only partially filled.
    A seeded lesson is byte-identical to a native one: same schema, same id, same agent
    name. Nothing in the RECORD says which institution learned it, so the moment anyone
    copies a key by hand -- or runs the shipped scripts/ops/snapshot_knowledge.py, which
    does exactly that for the whole knowledge layer -- two institutions collapse into one
    indistinguishable mass.

    This makes the question answerable at CORPUS level: "was this world's memory inherited,
    from where, and when?" It does NOT make it answerable per key. The real fix is a
    provenance.world stamp folded in at the store's write door, the way bus.py already folds
    frm_incarnation at the transport door -- which is a change to the write path, and belongs
    at a gate rather than in the same night that discovered the need for it.

    Not stamping INSIDE the values on the way down is deliberate: the copy is DUMP/RESTORE
    precisely so it preserves types and TTLs exactly, and rewriting payloads in flight would
    trade that fidelity for a field that belongs at the write door anyway.
    """
    import json
    doc = {
        "seeded_at": when,
        "source_world": plan.source,
        "target_world": plan.target,
        "carried": {p: counts.get(p, 0) for p in plan.prefixes},
        "refused": {p: why for p, why in plan.excluded.items()},
        "total_carried": sum(counts.get(p, 0) for p in plan.prefixes),
        "caveat": ("corpus-level provenance only -- individual keys carry no world stamp, "
                   "so a key copied out of here by hand is indistinguishable from a native one"),
    }
    dst.set(MANIFEST_KEY, json.dumps(doc))
    return doc


def read_manifest(client) -> Optional[dict]:
    """What this world inherited, or None if its memory is all its own."""
    import json
    try:
        raw = client.get(MANIFEST_KEY)
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:
        return None


def copy_prefix(src, dst, prefix: str, apply: bool = False, batch: int = 500) -> int:
    """DUMP/RESTORE every key under `prefix`. Returns the count seen (or written).

    DUMP/RESTORE rather than type-by-type reads: it preserves the exact value
    representation and the TTL, and it cannot silently mangle a type this module does
    not know about -- which matters because the knowledge plane holds strings, hashes,
    streams and sorted sets, and a seed that quietly flattens one of them produces a
    twin that fails in a way nobody traces back to the seed.
    """
    seen = 0
    for key in src.scan_iter(match=f"{prefix}*", count=batch):
        seen += 1
        if not apply:
            continue
        payload = src.dump(key)
        if payload is None:                      # raced with an expiry; nothing to carry
            continue
        ttl = src.pttl(key)
        dst.restore(key, ttl if ttl and ttl > 0 else 0, payload, replace=True)
    return seen
