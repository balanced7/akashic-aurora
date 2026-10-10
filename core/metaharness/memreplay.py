"""Replay the memory system itself, before and after a lesson changes (meta-harness task 08).

Recall-level replay (Forge F0, pack_replay) checks only whether a lesson WOULD SURFACE. This
closes the loop: does memory change outcomes? The same corpus and runner run the same scenarios
with different memory states, and the graders compare the arms.

SNAPSHOT: `capture` freezes the memory planes -- lessons and their indexes (learn:*), notes and
agent memory (mem:*), recall usefulness counters (recall:use:*) -- into one JSON file. `load`
writes a snapshot into a run's PRIVATE file store (the runner points Redis at a closed port
for any card that carries a snapshot), so every arm sees exactly one memory state.

ARMS, on the same scenarios, harness, model and trials:

    none     no memory at all
    before   memory as of before the change
    after    memory as of now
    ablate   after, with the one lesson removed

MEASURES: pass rate and the other grades (task 05); whether the lesson SURFACED in the run (its
source pointer appears in the trace, as recall-at prints it); repeats of the lesson's mistake
recorded inside the run's private store.

PROVEN EFFECT: after minus ablate, paired by scenario, with a cluster-bootstrap interval. It is
stamped on the lesson (`proven_effect`, visible in `recall --full`), and the recall ranker reads
it as a stronger signal than flip credit: a lesson whose interval is above zero is boosted, one
whose interval is below zero is damped.

TRIGGERS: a lesson that changes a lot -- new, edited, about to be benched, graduated or
compiled -- is queued (`enqueue`); `drain` replays the queue on the scenarios most related to
each lesson (files, domain, trigger words), within a daily budget.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.metaharness import home

PREFIXES = ("learn:", "mem:", "recall:use:")
ARMS = ("none", "before", "after", "ablate")
#: Ranker factors for a proven effect: interval above zero / below zero.
BOOST, DAMP = 1.5, 0.5


def snap_dir() -> Path:
    p = home() / "memsnap"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- snapshots
def _dump_key(store: Any, k: str) -> tuple[str, Any] | None:
    """(type, value) for one key, probing types the Store protocol cannot name directly."""
    probes = (
        ("hash", lambda: store.hgetall(k)),
        ("zset", lambda: store.zrange(k, 0, -1, withscores=True)),
        ("list", lambda: store.lrange(k, 0, -1)),
        ("set", lambda: sorted(store.smembers(k))),
        ("string", lambda: store.get(k)),
    )
    for kind, fn in probes:
        try:
            v = fn()
        except Exception:  # noqa: BLE001  # WRONGTYPE on Redis: try the next shape
            continue
        if v:
            return kind, ([list(x) for x in v] if kind == "zset" else v)
    return None


def capture(
    *,
    store: Any = None,
    exclude: tuple[str, ...] = (),
    before: str = "",
    label: str = "",
    replace: dict[str, dict[str, str]] | None = None,
) -> Path:
    """Freeze the memory planes into a snapshot file and return its path.

    `exclude` drops lessons by name (and their index memberships). `replace` puts back a
    lesson's PREVIOUS record (what `enqueue` saved at the moment it changed) -- the exact
    "before". `before` (ISO time) is the fallback when no previous record was kept: it drops
    lessons stamped at or after that time, an approximation, since a lesson EDITED since keeps
    its new text."""
    if store is None:
        from core.foundation.store import create_store

        store = create_store()
    data: dict[str, Any] = {}
    for prefix in PREFIXES:
        for k in sorted(store.keys(prefix + "*")):
            got = _dump_key(store, k)
            if got:
                data[k] = {"type": got[0], "value": got[1]}
    drop = set(exclude)
    if before:
        for k, v in list(data.items()):
            if (
                k.startswith("learn:experiment:")
                and v["type"] == "hash"
                and str(v["value"].get("timestamp") or "") >= before[:26]
            ):
                drop.add(k[len("learn:experiment:") :])
    for name in drop:
        data.pop(f"learn:experiment:{name}", None)
        data.pop(f"recall:use:learn:experiment:{name}", None)
        for v in data.values():
            if v["type"] in ("list", "set"):
                v["value"] = [x for x in v["value"] if x != name]
            elif v["type"] == "zset":
                v["value"] = [x for x in v["value"] if x[0] != name]
    for name, prev in (replace or {}).items():
        data[f"learn:experiment:{name}"] = {"type": "hash", "value": dict(prev)}
    body = json.dumps(data, sort_keys=True)
    digest = hashlib.sha256(body.encode()).hexdigest()[:12]
    lessons = sum(1 for k in data if k.startswith("learn:experiment:"))
    meta = {
        "at": _now(),
        "label": label,
        "excluded": sorted(drop),
        "before": before,
        "digest": digest,
        "lessons": lessons,
    }
    path = snap_dir() / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{label or 'snap'}-{digest}.json"
    path.write_text(json.dumps({"meta": meta, "data": data}), encoding="utf-8")
    return path


def empty_snapshot() -> Path:
    path = snap_dir() / "empty.json"
    if not path.exists():
        path.write_text(
            json.dumps({"meta": {"label": "none", "lessons": 0, "at": _now()}, "data": {}}), encoding="utf-8"
        )
    return path


def load(snapshot: Path, state_root: Path) -> int:
    """Write a snapshot into a FileStore under `state_root` (the run's AI_SETUP). Returns keys."""
    from core.foundation.store import FileStore

    snap = json.loads(Path(snapshot).read_text(encoding="utf-8"))
    (state_root / "session_logs").mkdir(parents=True, exist_ok=True)
    fs = FileStore(str(state_root / "session_logs" / "store_state.json"))
    for k, v in snap["data"].items():
        t, val = v["type"], v["value"]
        if t == "hash":
            fs.hset(k, mapping={str(f): str(x) for f, x in val.items()})
        elif t == "zset":
            fs.zadd(k, {str(m): float(sc) for m, sc in val})
        elif t == "list":
            fs.rpush(k, *[str(x) for x in val])
        elif t == "set":
            fs.sadd(k, *[str(x) for x in val])
        else:
            fs.set(k, str(val))
    return len(snap["data"])


# --------------------------------------------------------------------------- arms
def arm_candidates(
    base: str,
    lesson: str,
    *,
    before: str = "",
    previous: dict[str, str] | None = None,
    known_previous: bool = False,
    tag: str = "",
    store: Any = None,
) -> dict[str, str]:
    """Create the four arm candidates: the base candidate's overlay and card, each with its own
    memory snapshot. With `known_previous`, the before arm is now-with-the-previous-record
    (or without the lesson, when `previous` is None: it was new). Returns arm -> name."""
    from core.metaharness import replay

    card = replay.candidate(base)
    tag = tag or re.sub(r"[^A-Za-z0-9_-]", "_", lesson)[:40]
    if known_previous:
        before_snap = capture(
            store=store,
            exclude=() if previous else (lesson,),
            replace={lesson: previous} if previous else None,
            label=f"{tag}-before",
        )
    else:
        before_snap = capture(store=store, before=before, label=f"{tag}-before")
    snaps = {
        "none": empty_snapshot(),
        "before": before_snap,
        "after": capture(store=store, label=f"{tag}-after"),
        "ablate": capture(store=store, exclude=(lesson,), label=f"{tag}-ablate"),
    }
    names = {}
    for arm, snap in snaps.items():
        name = f"mem-{tag}-{arm}"
        replay.create_candidate(
            name,
            overlay_from=card["overlay"],
            harness=card["harness"],
            model=card.get("model") or "",
            effort=card.get("effort") or "",
            command=card.get("command") or [],
            env=card.get("env") or {},
            memory=str(snap),
            parent=base,
            hypothesis=f"memory arm '{arm}' for lesson {lesson}",
            budget_usd=card.get("budget_usd"),
            timeout_s=card.get("timeout_s"),
        )
        names[arm] = name
    return names


def related_scenarios(lesson: dict[str, Any], *, n: int = 10) -> list[str]:
    """Accepted scenarios most related to a lesson: shared files, then shared trigger words."""
    from core.metaharness import corpus

    try:
        files = set(json.loads(lesson.get("files_affected") or "[]"))
    except (TypeError, ValueError):
        files = set()
    text = " ".join(
        str(lesson.get(f) or "") for f in ("recommendation", "what_tried", "experiment_name", "anti_pattern")
    ).lower()
    words = set(re.findall(r"[a-z_][a-z0-9_]{3,}", text))
    scored = []
    for s in corpus.all_ids():
        lab = corpus.labels(s)
        if lab.get("status") != "accepted":
            continue
        prompt = (corpus.scenario_dir(s) / "prompt.md").read_text(encoding="utf-8").lower()
        f = len(files & set(lab.get("files") or []))
        w = len(words & set(re.findall(r"[a-z_][a-z0-9_]{3,}", prompt)))
        if f or w:
            scored.append((3 * f + w, s))
    return [s for _, s in sorted(scored, key=lambda x: (-x[0], x[1]))[:n]]


def surfaced(run_dir: Path, lesson: str) -> bool:
    """Did the lesson reach the agent in this run? recall-at prints each lesson's source."""
    t = run_dir / "transcript.jsonl"
    return t.exists() and f"learn:experiment:{lesson}" in t.read_text(encoding="utf-8", errors="replace")


def repeats_in_run(run_dir: Path, lesson: str) -> int:
    """Repeats of the lesson's mistake recorded inside the run's private store."""
    p = run_dir / "state" / "session_logs" / "store_state.json"
    if not p.exists():
        return 0
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return 0
    return sum(1 for v in (doc.get("hash") or {}).values() if isinstance(v, dict) and v.get("of") == lesson)


# --------------------------------------------------------------------------- the experiment
def experiment(
    lesson: str,
    base: str,
    *,
    scenarios: list[str] | None = None,
    before: str = "",
    previous: dict[str, str] | None = None,
    known_previous: bool = False,
    trials: int = 3,
    repo: Path | None = None,
    runner: list[str] | None = None,
    judge=None,
    store: Any = None,
    daily_usd: float | None = None,
) -> dict[str, Any]:
    """Run the four arms for one lesson and report its proven effect."""
    from core.learning.learning_store import get_learning_store_instance
    from core.metaharness import graders, replay, stats

    ls = get_learning_store_instance() if store is None else None
    st = store if store is not None else ls.store if ls else None
    rec = (st.hgetall(f"learn:experiment:{lesson}") if st is not None else {}) or {}
    scen = scenarios or related_scenarios(rec)
    if not scen:
        return {"lesson": lesson, "error": "no related accepted scenarios"}
    names = arm_candidates(
        base,
        lesson,
        before=before or str(rec.get("timestamp") or ""),
        previous=previous,
        known_previous=known_previous,
        store=st,
    )
    spent = 0.0
    for cand in names.values():
        for s in scen:
            if daily_usd is not None and spent >= daily_usd:
                break
            for r in replay.run(cand, s, trials=trials, repo=repo or replay.ROOT):
                spent += float(r.get("cost_usd") or 0.0)
                if r.get("run_dir"):
                    graders.grade_run(Path(r["run_dir"]), s, repo=repo or replay.ROOT, runner=runner, judge=judge)
    comps = {
        "after_vs_before": graders.compare(names["before"], names["after"], scen),
        "after_vs_none": graders.compare(names["none"], names["after"], scen),
        "after_vs_ablate": graders.compare(names["ablate"], names["after"], scen),
    }
    sur = {
        arm: sum(surfaced(rd, lesson) for s in scen for rd in replay.runs_for(cand, s)) for arm, cand in names.items()
    }
    reps = {
        arm: sum(repeats_in_run(rd, lesson) for s in scen for rd in replay.runs_for(cand, s))
        for arm, cand in names.items()
    }
    fn = (
        comps["after_vs_ablate"]["criteria"].get("functional")
        or comps["after_vs_ablate"]["criteria"].get("correctness")
        or {}
    )
    effect = {
        "effect": fn.get("effect"),
        "ci": fn.get("ci"),
        "n_scenarios": fn.get("n_scenarios"),
        "verdict": fn.get("verdict"),
        "surfaced": sur,
        "repeats": reps,
        "scenarios": scen,
        "at": _now(),
        "spent_usd": round(spent, 4),
    }
    if st is not None and fn:
        st.hset(f"learn:experiment:{lesson}", mapping={"proven_effect": json.dumps(effect)})
    out = {
        "lesson": lesson,
        "arms": names,
        "comparisons": {k: {c: r["verdict"] for c, r in v["criteria"].items()} for k, v in comps.items()},
        "proven_effect": effect,
    }
    (snap_dir() / f"effect-{re.sub(r'[^A-Za-z0-9_-]', '_', lesson)[:60]}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8"
    )
    _ = stats  # the verdicts above carry the statistics
    return out


def ranker_factor(proven_effect: Any) -> float:
    """1.0 unless a proven effect's interval clears zero: BOOST above, DAMP below."""
    try:
        pe = json.loads(proven_effect) if isinstance(proven_effect, str) else (proven_effect or {})
        lo, hi = (pe.get("ci") or [None, None])[:2]
    except (TypeError, ValueError, AttributeError):
        return 1.0
    if lo is not None and float(lo) > 0:
        return BOOST
    if hi is not None and float(hi) < 0:
        return DAMP
    return 1.0


# --------------------------------------------------------------------------- triggers
def _queue_path() -> Path:
    return snap_dir() / "queue.jsonl"


def enqueue(lesson: str, why: str, previous: dict[str, str] | None) -> None:
    """Queue a lesson that is ABOUT to change, with its record as it stands (None if new). Call
    it before the write. Cheap -- one small append, no snapshot -- and fail-soft: it runs on
    the learn / bench / graduate paths and must never break them. Off with
    AKASHIC_MEMREPLAY_TRIGGERS=0."""
    import os

    if os.getenv("AKASHIC_MEMREPLAY_TRIGGERS", "1") == "0":
        return
    try:
        with _queue_path().open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"lesson": lesson, "why": why, "at": _now(), "previous": dict(previous) if previous else None}
                )
                + "\n"
            )
    except Exception:  # noqa: BLE001  # a trigger is a bonus; the lesson write is what matters
        pass


def queued() -> list[dict[str, Any]]:
    p = _queue_path()
    if not p.exists():
        return []
    rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        latest.setdefault(r["lesson"], r)  # the FIRST queued record is the true "before"
    return list(latest.values())


def drain(
    base: str, *, daily_usd: float, trials: int = 3, repo: Path | None = None, runner: list[str] | None = None
) -> list[dict[str, Any]]:
    """Replay every queued lesson (within the budget), then clear the queue entries it ran."""
    done, out = set(), []
    budget = daily_usd
    for q in queued():
        if budget <= 0:
            break
        res = experiment(
            q["lesson"],
            base,
            previous=q.get("previous"),
            known_previous=True,
            trials=trials,
            repo=repo,
            runner=runner,
            daily_usd=budget,
        )
        budget -= float((res.get("proven_effect") or {}).get("spent_usd") or 0.0)
        out.append(res)
        done.add(q["lesson"])
    rest = (
        [json.loads(ln) for ln in _queue_path().read_text(encoding="utf-8").splitlines() if ln.strip()]
        if _queue_path().exists()
        else []
    )
    _queue_path().write_text("".join(json.dumps(r) + "\n" for r in rest if r["lesson"] not in done), encoding="utf-8")
    return out
