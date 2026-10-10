"""Human review queue: the final check-off on any harness change (meta-harness task 06).

Automatic graders filter; a person decides. Some qualities only a person judges well -- taste,
risk, fit with where the project is going -- and person labels are also the ground truth that
keeps the model judges honest (task 05's calibration reads them).

AN ITEM is a candidate that passed the automatic gate. It carries the verdict object, the two or
three scenarios where old and new differ most, the candidate's config diff against the live
harness, and the proposer's predicted effect. Items expire after 7 days, as Forge proposals do:
a stale queue is a queue nobody reads.

DECIDING: accept, reject, or "needs more runs", with one better / same / worse call per
criterion and a free-text reason. Every per-criterion call is stored beside the grader's call
for the same criterion; for the model-graded ones (quality, process) it also goes into the
judge-calibration file.

SIGN-OFF POLICY (the task's open question): one reviewer, except when the change touches a
high-risk surface -- hooks, guards, policy, settings -- which needs two distinct reviewers.

NO HARNESS CHANGE REACHES THE LIVE CONFIG WITHOUT A RECORDED ACCEPT: `apply` refuses otherwise.
Apply first backs up every file the overlay touches (recording which did not exist), so
`rollback` restores the previous config byte for byte.

PROVISIONAL WATCH (Forge F4 uses 14 days): apply snapshots the live outcome signals -- fails,
flips, repeats, session churn -- over the window before; `watch` compares the window after and
rolls back on its own if the live numbers got worse. A rejected item is written back to the
candidate folder with its reason, where the proposer (task 07) reads it.
"""

from __future__ import annotations

import difflib
import hashlib
import html
import json
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.metaharness import home

ROOT = Path(__file__).resolve().parents[2]
TTL_DAYS = 7
WATCH_DAYS = 14
HIGH_RISK = (
    ".claude/settings",
    ".codex/",
    ".cursor/hooks",
    "agent/harness/hooks/",
    "agent/harness/guards.py",
    "agent/policy/",
    "scripts/hooks/",
)
CALLS = ("better", "same", "worse")
DECISIONS = ("accept", "reject", "more_runs")
#: Watch: the after-window rate may exceed the before-window rate by this factor before it
#: counts as worse, and needs at least this many events to count at all.
WORSE_FACTOR = 1.25
MIN_EVENTS = 5


def queue_dir() -> Path:
    p = home() / "review"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def item(iid: str) -> dict[str, Any]:
    try:
        return json.loads((queue_dir() / iid / "item.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise KeyError(f"no review item {iid!r}") from e


def _save(it: dict[str, Any]) -> None:
    d = queue_dir() / it["id"]
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "item.json.tmp"
    tmp.write_text(json.dumps(it, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(d / "item.json")


def overlay_files(overlay: Path) -> list[str]:
    return sorted(str(p.relative_to(overlay)) for p in overlay.rglob("*") if p.is_file())


def config_diff(overlay: Path, live_root: Path) -> str:
    """Unified diff of every overlay file against the live harness file it would replace."""
    out: list[str] = []
    for rel in overlay_files(overlay):
        new = (overlay / rel).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        live = live_root / rel
        old = live.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if live.exists() else []
        out.extend(difflib.unified_diff(old, new, f"a/{rel}", f"b/{rel}"))
    return "".join(out)


def high_risk(files: list[str]) -> bool:
    return any(f.startswith(HIGH_RISK) or any(h in f for h in HIGH_RISK) for f in files)


def _most_different(verdict: dict[str, Any], n: int = 3) -> list[str]:
    """Scenarios where old and new differ most, by functional then correctness grades."""
    from core.metaharness import stats
    from core.metaharness.graders import _collect

    va, _ = _collect(verdict["a"], verdict["scenarios"])
    vb, _ = _collect(verdict["b"], verdict["scenarios"])
    score: dict[str, float] = {}
    for k in ("functional", "correctness"):
        for s, d in stats.paired_diffs(va[k], vb[k]).items():
            score[s] = score.get(s, 0.0) + abs(d)
    return sorted(verdict["scenarios"], key=lambda s: (-score.get(s, 0.0), s))[:n]


# --------------------------------------------------------------------------- queue
def enqueue(candidate: str, verdict: dict[str, Any], *, live_root: Path = ROOT, predicted: str = "") -> dict[str, Any]:
    """Queue a candidate that passed the automatic gate. `verdict` is graders.compare's object
    for this candidate (b) against the live harness candidate (a)."""
    from core.metaharness import replay

    card = replay.candidate(candidate)
    overlay = Path(card["overlay"])
    files = overlay_files(overlay)
    iid = f"{candidate}-{uuid.uuid4().hex[:6]}"
    now = _now()
    it = {
        "id": iid,
        "candidate": candidate,
        "against": verdict.get("a"),
        "status": "pending",
        "created": _iso(now),
        "expires": _iso(now + timedelta(days=TTL_DAYS)),
        "verdict": verdict,
        "show_scenarios": _most_different(verdict),
        "files": files,
        "high_risk": high_risk(files),
        "reviewers_needed": 2 if high_risk(files) else 1,
        "predicted": predicted or card.get("hypothesis") or "",
        "decisions": [],
    }
    d = queue_dir() / iid
    d.mkdir(parents=True)
    (d / "config.diff").write_text(config_diff(overlay, live_root), encoding="utf-8")
    _save(it)
    return it


def pending() -> list[dict[str, Any]]:
    """Live items, oldest first; expired ones are marked expired on the way past."""
    out = []
    for d in sorted(queue_dir().iterdir()):
        if not (d / "item.json").exists():
            continue
        it = item(d.name)
        if it["status"] == "pending" and datetime.fromisoformat(it["expires"]) < _now():
            it["status"] = "expired"
            _save(it)
        if it["status"] == "pending":
            out.append(it)
    return sorted(out, key=lambda x: x["created"])


# --------------------------------------------------------------------------- decide
def decide(iid: str, reviewer: str, decision: str, calls: dict[str, str], reason: str) -> dict[str, Any]:
    """Record one reviewer's decision. `calls` is criterion -> better/same/worse."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    bad = {k: v for k, v in calls.items() if v not in CALLS}
    if bad:
        raise ValueError(f"per-criterion calls must be {CALLS}: {bad}")
    if not reviewer or not reason.strip():
        raise ValueError("a decision needs a reviewer and a reason")
    it = item(iid)
    if it["status"] != "pending":
        raise ValueError(f"item {iid} is {it['status']}, not pending")
    it["decisions"].append(
        {"reviewer": reviewer, "decision": decision, "calls": calls, "reason": reason, "at": _iso(_now())}
    )
    _record_labels(it, calls, reviewer)
    accepts = {d["reviewer"] for d in it["decisions"] if d["decision"] == "accept"}
    if decision == "reject":
        it["status"] = "rejected"
        _write_back(it, reason)
    elif decision == "more_runs":
        it["status"] = "more_runs"
        _write_back(it, reason)
    elif len(accepts) >= it["reviewers_needed"]:
        it["status"] = "accepted"
    _save(it)
    return it


_TO_LABEL = {"better": "2", "worse": "1", "same": "tie"}


def _grader_call(it: dict[str, Any], criterion: str) -> str:
    v = ((it.get("verdict") or {}).get("criteria") or {}).get(criterion) or {}
    return {"better": "better", "worse": "worse"}.get(str(v.get("verdict")), "same")


def _record_labels(it: dict[str, Any], calls: dict[str, str], reviewer: str) -> None:
    """Person call next to grader call, per criterion. Model-graded criteria also feed the
    judge calibration (task 05) in the judge's own vocabulary."""
    from core.metaharness import graders

    with (queue_dir() / "labels.jsonl").open("a", encoding="utf-8") as f:
        for crit, person in calls.items():
            grader = _grader_call(it, crit)
            f.write(
                json.dumps(
                    {"item": it["id"], "criterion": crit, "person": person, "grader": grader, "reviewer": reviewer}
                )
                + "\n"
            )
            if crit in ("quality", "process"):
                graders.add_label(crit, _TO_LABEL[person], _TO_LABEL[grader], ref=it["id"])


def disagreements() -> list[dict[str, Any]]:
    """Every per-criterion call where the person and the grader disagree."""
    p = queue_dir() / "labels.jsonl"
    if not p.exists():
        return []
    rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["person"] != r["grader"]]


def _write_back(it: dict[str, Any], reason: str) -> None:
    """Return the outcome to the candidate's archive folder, where the proposer reads it."""
    from core.metaharness import replay

    d = replay.candidates_dir() / it["candidate"]
    if d.exists():
        rec = {"item": it["id"], "status": it["status"], "reason": reason, "at": _iso(_now())}
        with (d / "reviews.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")


# --------------------------------------------------------------------------- apply / rollback
def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def apply(iid: str, *, live_root: Path = ROOT, signals: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lay an ACCEPTED candidate's overlay over the live harness, backing everything up first."""
    from core.metaharness import replay

    it = item(iid)
    if it["status"] != "accepted":
        raise PermissionError(
            f"refused: item {iid} is {it['status']}; no harness change lands without a recorded accept"
        )
    overlay = Path(replay.candidate(it["candidate"])["overlay"])
    backup = queue_dir() / iid / "backup"
    if backup.exists():
        shutil.rmtree(backup)
    manifest = []
    for rel in overlay_files(overlay):
        live = live_root / rel
        existed = live.exists()
        if existed:
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, backup / rel)
        manifest.append({"path": rel, "existed": existed, "before": _digest(live)})
    for rel in overlay_files(overlay):
        (live_root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / rel, live_root / rel)
    try:  # task 09: a precompiled candidate records on each lesson where it now lives
        from core.metaharness.precompile import stamp_compiled

        it["compiled_lessons"] = stamp_compiled(overlay, it["candidate"])
    except Exception:  # noqa: BLE001  # the config change has landed; the stamp is bookkeeping
        it["compiled_lessons"] = 0
    now = _now()
    it.update(
        status="applied",
        applied_at=_iso(now),
        live_root=str(live_root),
        manifest=manifest,
        watch_until=_iso(now + timedelta(days=WATCH_DAYS)),
        signals_before=signals if signals is not None else live_signals(now - timedelta(days=WATCH_DAYS), now),
    )
    _save(it)
    return it


def rollback(iid: str, *, reason: str = "") -> dict[str, Any]:
    """Restore exactly the files apply() replaced, and remove the ones it created."""
    it = item(iid)
    if it["status"] not in ("applied", "kept"):
        raise ValueError(f"item {iid} is {it['status']}; only an applied item rolls back")
    live_root = Path(it["live_root"])
    backup = queue_dir() / iid / "backup"
    for m in it["manifest"]:
        live = live_root / m["path"]
        if m["existed"]:
            shutil.copy2(backup / m["path"], live)
        else:
            live.unlink(missing_ok=True)
    it.update(status="rolled_back", rolled_back_at=_iso(_now()), rollback_reason=reason)
    _save(it)
    _write_back(it, f"rolled back: {reason}")
    return it


# --------------------------------------------------------------------------- watch
def _store_repeats() -> list[dict[str, Any]]:
    """Recorded repeats (learn:repeats) -- they live in the store, not on the event firehose."""
    try:
        from core.learning.learning_store import get_learning_store_instance

        ls = get_learning_store_instance()
        return [ls.store.hgetall(f"learn:repeat:{rid}") for rid in ls.store.smembers(ls.REPEAT_INDEX)]
    except Exception:  # noqa: BLE001  # fail-soft: no store means no repeats seen
        return []


def live_signals(
    start: datetime,
    end: datetime,
    events: list[dict[str, Any]] | None = None,
    repeats: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Outcome signals in [start, end): fails, flips, repeats, session churn, sessions."""
    if repeats is None:
        repeats = _store_repeats() if events is None else []
    if events is None:
        try:
            from core.events.event_log import get_event_log

            events = get_event_log().scan(limit=50000)
        except Exception:  # noqa: BLE001  # fail-soft: no events means no evidence either way
            events = []
    s, e = _iso(start), _iso(end)
    out = {
        "fails": 0,
        "flips": 0,
        "repeats": 0,
        "churn": 0,
        "sessions": 0,
        "days": max(1e-9, (end - start).total_seconds() / 86400),
    }
    for ev in events:
        at = str(ev.get("at") or "")
        if not (s <= at < e):
            continue
        k = ev.get("kind")
        if k == "fail":
            out["fails"] += 1
        elif k == "flip":
            out["flips"] += 1
        elif k == "repeat":  # a repeat event, where a door emits one
            out["repeats"] += 1
        elif k == "session_signals":
            out["sessions"] += 1
            # churn = repeated calls on the same target (session_signals.repetition_count)
            out["churn"] += int(((ev.get("detail") or {}).get("repetition_count")) or 0)
    # Repeats are stamped naive UTC (learning_store); compare on the same footing.
    s_naive, e_naive = s[:19], e[:19]
    out["repeats"] += sum(1 for r in repeats if s_naive <= str(r.get("at") or "")[:19] < e_naive)
    return out


def _per_session(sig: dict[str, Any], key: str) -> float:
    return sig[key] / max(1, sig["sessions"]) if sig["sessions"] else sig[key] / sig["days"]


def got_worse(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Which signals rose past WORSE_FACTOR (per session, or per day without sessions)."""
    worse = []
    for k in ("fails", "repeats", "churn"):
        if after[k] < MIN_EVENTS:
            continue
        b, a = _per_session(before, k), _per_session(after, k)
        if a > max(b, 1e-9) * WORSE_FACTOR:
            worse.append(f"{k}: {b:.2f} -> {a:.2f} per {'session' if after['sessions'] else 'day'}")
    return worse


def watch(
    *,
    now: datetime | None = None,
    events: list[dict[str, Any]] | None = None,
    repeats: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Check every applied item. Roll back on worse live signals; keep it once the window ends."""
    now = now or _now()
    out = []
    for d in sorted(queue_dir().iterdir()):
        if not (d / "item.json").exists():
            continue
        it = item(d.name)
        if it["status"] != "applied":
            continue
        after = live_signals(datetime.fromisoformat(it["applied_at"]), now, events, repeats)
        worse = got_worse(it["signals_before"], after)
        if worse:
            it = rollback(it["id"], reason="provisional watch: " + "; ".join(worse))
        elif now >= datetime.fromisoformat(it["watch_until"]):
            it.update(status="kept", kept_at=_iso(now), signals_after=after)
            _save(it)
        out.append({"id": it["id"], "status": it["status"], "worse": worse, "after": after})
    return out


# --------------------------------------------------------------------------- the review page
def render(iid: str) -> Path:
    """A self-contained HTML page for one item: verdict table, config diff, and the old and new
    diffs side by side for the scenarios that differ most. Opens from disk; decide with the CLI."""
    it = item(iid)
    v = it["verdict"]
    d = queue_dir() / iid
    esc = html.escape
    rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{r['a']}</td><td>{r['b']}</td><td>{r['effect']:+.4f}</td>"
        f"<td>[{r['ci'][0]}, {r['ci'][1]}]</td><td class='{esc(str(r['verdict']).replace(' ', '-'))}'>{esc(str(r['verdict']))}</td></tr>"
        for k, r in (v.get("criteria") or {}).items()
    )
    sides = []
    for s in it["show_scenarios"]:
        cells = []
        for side in ("a", "b"):
            runs = (v.get("runs") or {}).get(side, {}).get(s) or []
            diff = Path(runs[0], "diff.patch").read_text(encoding="utf-8")[:20000] if runs else "(no run)"
            cells.append(f"<td><h4>{esc(v[side])}</h4><pre>{esc(diff)}</pre></td>")
        sides.append(f"<h3>{esc(s)}</h3><table class='side'><tr>{''.join(cells)}</tr></table>")
    crits = ", ".join(f"{k}=better|same|worse" for k in (v.get("criteria") or {}))
    lessons_html = _lessons_section(it["candidate"])
    page = f"""<!doctype html><meta charset="utf-8"><title>Review {esc(iid)}</title>
<style>body{{font:14px system-ui;margin:16px;max-width:1400px}}pre{{white-space:pre-wrap;font:12px ui-monospace;background:#f6f6f6;padding:8px}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px;vertical-align:top}}.side td{{width:50%}}
.better{{color:#0a0}}.worse{{color:#c00}}</style>
<h1>{esc(it["candidate"])} vs {esc(str(it["against"]))}</h1>
<p>Pareto: <b>{esc(str(v.get("pareto")))}</b>. Predicted effect: {esc(it["predicted"] or "(none stated)")}.
Reviewers needed: {it["reviewers_needed"]}{" (high-risk surface)" if it["high_risk"] else ""}. Expires {esc(it["expires"])}.</p>
<table><tr><th>criterion</th><th>old</th><th>new</th><th>effect</th><th>95% CI</th><th>grader call</th></tr>{rows}</table>
{lessons_html}
<h2>Config diff</h2><pre>{esc((d / "config.diff").read_text(encoding="utf-8"))}</pre>
<h2>Where they differ most</h2>{"".join(sides)}
<h2>Decide</h2><pre>uv run agent_cli.py review decide {esc(iid)} --reviewer YOU --decision accept|reject|more_runs \\
  --calls "{esc(crits)}" --reason "..."</pre>"""
    out = d / "review.html"
    out.write_text(page, encoding="utf-8")
    return out


def _lessons_section(candidate: str) -> str:
    """The proven effect (task 08) of every lesson the candidate's contract says it builds on."""
    from core.metaharness import archive

    names = [str(x) for x in (archive.contract(candidate).get("lessons") or [])]
    if not names:
        return ""
    try:
        from core.learning.learning_store import get_learning_store_instance

        store = get_learning_store_instance().store
    except Exception:  # noqa: BLE001  # the page still renders without the store
        return ""
    rows = []
    for n in names:
        pe = (store.hgetall(f"learn:experiment:{n}") or {}).get("proven_effect") or ""
        try:
            d = json.loads(pe) if pe else {}
        except ValueError:
            d = {}
        cell = f"{d.get('effect')} CI {d.get('ci')} ({d.get('verdict')})" if d else "not replayed yet"
        rows.append(f"<tr><td>{html.escape(n)}</td><td>{html.escape(cell)}</td></tr>")
    return (
        "<h2>Lessons it builds on: proven effect</h2><table><tr><th>lesson</th><th>effect on replay</th></tr>"
        + "".join(rows)
        + "</table>"
    )
