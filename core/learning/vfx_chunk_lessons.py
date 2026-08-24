"""Adopt the VFX chunk rules into recall — as a PROJECTION, not a migration.

THE PREMISE, checked before it was built on (tests/test_domain_aware_recall.py asserts it): all 31
chunks in design/vfx-chunks/*.glsl already carry a `note` that is lesson-shaped -- a rule WITH its
reason -- plus a `from` field that is provenance. This knowledge was never missing. It was
unreachable: asking recall the channel-rotate rule in its own words returned 707 rows, none of them
channel-rotate.

WHY PROJECTION AND NOT A COPY. The .glsl header stays the single source of truth. A chunk's note is
edited by whoever edits the chunk, in the file they already have open; if adoption forked a second
editable copy into the lesson store, the two would drift and nobody would know which was right --
which is the precise failure this codebase names elsewhere as a name that lies. So adoption is
re-runnable, keyed by the chunk name, and refreshes when the note changes. The lesson record points
back at the file.

WHAT BECOMES AN ANTI-PATTERN. Four of the notes are warning-shaped ("WARNING…", "must not…",
"NEVER…") -- channel-rotate destroying a state-bearing hue, hash31 being unfit for anything that
must not band, and so on. Those adopt with the anti_pattern field set, which is what recall's
dissent-finder reads. That flag has existed on the write door for months with zero uses; per this
project's own finding, a field nothing fills stays empty until something depends on it.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from core.paths import repo_root
from typing import Any, Dict, List, Optional

# A note that tells you what NOT to do is a disconfirmer, and recall treats those differently from
# advice. Detected from the author's own emphasis rather than from a model's opinion of the text.
_WARNING_MARKS = ("WARNING", "NEVER", "must not", "never touch", "not good enough")


def _chunk_headers(chunk_dir: str) -> List[Dict[str, Any]]:
    out = []
    for fname in sorted(os.listdir(chunk_dir)):
        if not fname.endswith(".glsl"):
            continue
        path = os.path.join(chunk_dir, fname)
        try:
            with io.open(path, "r", encoding="utf-8") as fh:
                head = fh.readline().strip()
            if not head.startswith("//!"):
                continue
            meta = json.loads(head[3:])
        except (OSError, ValueError):
            continue                      # a malformed chunk must not stop the other thirty
        if meta.get("name") and meta.get("note"):
            meta["_file"] = "design/vfx-chunks/" + fname
            out.append(meta)
    return out


def _is_warning(note: str) -> bool:
    low = note.lower()
    return any(m.lower() in low for m in _WARNING_MARKS)


def _signal_for(meta: Dict[str, Any]) -> Dict[str, Any]:
    name = str(meta["name"])
    note = str(meta["note"])
    kind = str(meta.get("kind") or "")
    cat = str(meta.get("cat") or "")
    origin = str(meta.get("from") or "")

    # what_tried carries the SHAPE (where this piece can go, where it came from) and the
    # recommendation carries the RULE, so the two halves land in the fields recall already ranks.
    tried = "the %s chunk (%s%s)" % (name, kind, (", " + cat) if cat else "")
    if origin:
        tried += ", from " + origin

    # SYNTHESISE THE TRIGGER CLAUSE, and this was found live rather than reasoned: adoption made
    # these lessons retrievable by keyword search and they STILL never surfaced at a gesture,
    # because recall-at ranks by the corpus convention "Use when <symptom>, before <action>:
    # <advice>" and a chunk note has no such clause. Every adopted lesson scored ~0.17 against a
    # 0.20 floor with trigger=''. The note was authored for a human reading a palette; the ranker
    # assumes a different authoring surface, and a projection has to bridge that rather than copy
    # text across. The clause is derived from the chunk's own declared metadata, so it states a
    # fact the header already carries -- it is a rendering, not an invention.
    trigger = ("Use when adding or ordering the %s chunk (%s%s) in a composition, "
               "before compiling: " % (name, kind, (", " + cat) if cat else ""))
    return {
        "experiment_name": "vfx_chunk_" + name,
        "what_tried": tried,
        "expected_outcome": "",
        "actual_outcome": "",
        "recommendation": trigger + note,
        "category": "vfx-chunk",
        "domain": "vfx",
        "success": "yes",
        "confidence": "high",             # these are settled rules, not experiments in flight
        "anti_pattern": ("vfx:" + name) if _is_warning(note) else "",
        # The pointer is the point: the projection says where its truth lives.
        "source": meta.get("_file", ""),
        "agent_id": "vfx-chunks",
    }


def _fingerprint(sig: Dict[str, Any]) -> str:
    return hashlib.sha1(
        (sig["recommendation"] + "|" + sig["what_tried"] + "|" + sig["anti_pattern"])
        .encode("utf-8")).hexdigest()[:12]


def adopt_chunk_lessons(learning_store, chunk_dir: str,
                        force: bool = False) -> int:
    """Mint/refresh one lesson per chunk note. Returns how many chunks were adopted.

    Re-runnable by construction: a chunk whose note has not changed is skipped, so this can be
    wired to a hook or run by hand without forking duplicates or churning timestamps.
    """
    metas = _chunk_headers(chunk_dir)
    for meta in metas:
        sig = _signal_for(meta)
        fp = _fingerprint(sig)
        key = "learn:experiment:" + sig["experiment_name"]
        if not force:
            try:
                existing = learning_store.store.hgetall(key) or {}
            except Exception:
                existing = {}
            if existing.get("chunk_fingerprint") == fp:
                continue                  # note unchanged: nothing to say
        sig["metrics"] = {"chunk_fingerprint": fp}
        learning_store.persist_learning_derived_from_experiment(sig)
        # Stored flat as well as in metrics so the skip-check above is one cheap hgetall.
        try:
            learning_store.store.hset(key, mapping={"chunk_fingerprint": fp})
            if sig["anti_pattern"]:
                learning_store.store.sadd("learn:anti_patterns", sig["anti_pattern"])
        except Exception:
            pass
    return len(metas)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    from core.learning.learning_store import get_learning_store_instance

    repo = str(repo_root())
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chunks", default=os.path.join(repo, "design", "vfx-chunks"))
    ap.add_argument("--force", action="store_true", help="re-adopt even if the note is unchanged")
    ns = ap.parse_args(argv)

    ls = get_learning_store_instance()
    n = adopt_chunk_lessons(ls, ns.chunks, force=ns.force)
    warned = sum(1 for m in _chunk_headers(ns.chunks) if _is_warning(str(m.get("note") or "")))
    print("adopted %d chunk rule(s) into recall (domain=vfx), %d as anti-patterns" % (n, warned))
    # WARM THE CACHE, or this verb appears to do nothing. recall-at reads a prebuilt cache file, so
    # freshly adopted lessons stayed invisible at the surface that matters while every test passed --
    # cost a live debugging pass to notice. A write door that leaves a stale read path is only half
    # a door.
    try:
        from core.recall.at_action import warm_cache
        print("recall cache rebuilt: %d item(s)" % warm_cache(learning_store=ls))
    except Exception as exc:
        print("WARNING: adopted, but the recall cache did not rebuild (%s). "
              "Run: py -c \"from core.recall.at_action import warm_cache; warm_cache()\"" % exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
