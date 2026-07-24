"""
seed_narrative.py -- dogfood the spine: ingest real git history as Beats, then chronicle.

    py scripts/seed_narrative.py            # enrich canonical store + chronicle
    py scripts/seed_narrative.py --dry-run  # show what WOULD be added, change nothing

Why: the narrative spine should tell the TRUE story of this project's build-out, not a
hand-written summary that drifts. Every commit is already a salient event; this walks
`git log` oldest->newest and emits a `commit` Beat for any commit not already on the
timeline (idempotent -- safe to re-run). Pre-existing commit Beats that were stored
UNROUTED (track=None, from before Slice 2) are re-routed in place using the commit's
touched paths. Then it runs the Chronicler so `story` and `boot` reflect reality.

Snapshot first if you're nervous:  py scripts/ops/snapshot_knowledge.py snapshot
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.foundation.store import create_store
from core.narrative.beat_log import BeatLog, TIMELINE
from core.narrative.schema import Beat, beat_key, track_key, Track
from core.narrative.track_router import get_track_router, RouteHint


def _git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _commits():
    """Oldest-first list of (sha12, iso_date, subject, [files])."""
    # Use the FULL sha sliced to 12 -- this matches scripts/mirror.py's source format
    # (`git:<rev-parse HEAD[:12]>`) so re-seeding is idempotent against mirror's beats.
    raw = _git("log", "--reverse", "--pretty=format:%H%x01%cI%x01%s")
    out = []
    for line in raw.splitlines():
        parts = line.split("\x01")
        if len(parts) != 3:
            continue
        sha, iso, subject = parts
        files = [f for f in _git("show", "--name-only", "--pretty=format:", sha).splitlines() if f.strip()]
        out.append((sha[:12], iso, subject, files))
    return out


def _salient(subject, files):
    return subject.lower().startswith(("feat", "fix", "slice")) or any(f.startswith("core/") for f in files)


def _existing_sources(store):
    """Map source -> beat_id for every beat already on the timeline."""
    found = {}
    for bid in store.zrange(TIMELINE, 0, -1):
        raw = store.get(beat_key(bid))
        if not raw:
            continue
        try:
            b = Beat.from_dict(json.loads(raw))
            found[b.source] = b
        except (ValueError, TypeError):
            pass
    return found


def _repair_unrouted(store, router, dry):
    """Backfill Beats stuck at track None/unknown (logged before routing/themes were
    wired). Recovers the routing signal the SAME way emit would have: a learning beat's
    Track is inferred from its source learn:experiment hash `category`; themes come from
    the real ThemeAssigner. Nothing is hardcoded -- the production rules decide.
    git: beats are handled by the commit pass above and skipped here.
    """
    try:
        from core.narrative.theme_assigner import get_theme_assigner
        ta = get_theme_assigner()
    except Exception:
        ta = None

    fixed = 0
    for bid in store.zrange(TIMELINE, 0, -1):
        raw = store.get(beat_key(bid))
        if not raw:
            continue
        try:
            b = Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            continue
        if b.track not in (None, "", "unknown"):
            continue
        if b.source.startswith("git:"):
            continue

        hint = RouteHint()
        if b.source.startswith("learn:experiment:"):
            try:
                rec = store.hgetall(b.source)
                hint = RouteHint(category=str(rec.get("category", "")))
            except Exception:
                pass

        res = router.route_one(b, hint, store.get("narr:router:active"))
        old_track = b.track
        new_track = res.track
        new_themes = b.themes or (ta.assign(b, hint) if ta else [])
        if new_track == old_track and new_themes == b.themes:
            continue

        print(f"  repair   {bid}  track {old_track}->{new_track} (basis={res.basis})  "
              f"themes={new_themes}  {b.summary[:45]}")
        if not dry:
            b.track = new_track
            b.themes = new_themes
            store.set(beat_key(bid), json.dumps(b.to_dict()))
            if new_track and new_track != "unknown":
                store.set("narr:router:active", new_track)
                store.zadd(f"narr:track:{new_track}:beats", {bid: 0})
                if not store.get(track_key(new_track)):
                    store.set(track_key(new_track), json.dumps(
                        Track(id=new_track, title=new_track.replace("-", " ").title(),
                              created_at=b.at).to_dict()))
        fixed += 1
    return fixed


def main():
    dry = "--dry-run" in sys.argv
    store = create_store()
    bl = BeatLog(store)
    existing = _existing_sources(store)
    router = get_track_router()

    added = rerouted = skipped = 0
    for sha, iso, subject, files in _commits():
        source = f"git:{sha}"
        hint = RouteHint(paths=files)
        weight = 4 if _salient(subject, files) else 2

        prior = existing.get(source)
        if prior is not None:
            if prior.track is None:                 # legacy unrouted -> repair in place
                res = router.route_one(prior, hint, store.get("narr:router:active"))
                if not dry:
                    prior.track = res.track
                    store.set(beat_key(prior.id), json.dumps(prior.to_dict()))
                    store.set("narr:router:active", res.track)
                    store.zadd(f"narr:track:{res.track}:beats", {prior.id: 0})
                    if not store.get(track_key(res.track)):
                        store.set(track_key(res.track), json.dumps(
                            Track(id=res.track, title=res.track.replace("-", " ").title(),
                                  created_at=prior.at).to_dict()))
                rerouted += 1
                print(f"  reroute  {sha}  -> {res.track}  {subject[:50]}")
            else:
                skipped += 1
            continue

        if dry:
            print(f"  ADD      {sha}  (w{weight})  {subject[:50]}")
        else:
            b = bl.emit("commit", subject, source, weight=weight, at=iso, hint=hint)
            print(f"  add      {sha}  -> {b.track if b else '?'}  {subject[:50]}")
        added += 1

    repaired = _repair_unrouted(store, router, dry)

    print(f"\n[seed] {'(dry-run) ' if dry else ''}added={added} rerouted={rerouted} "
          f"skipped={skipped} repaired_unrouted={repaired}")

    if not dry:
        from core.narrative.chronicler import Chronicler
        rep = Chronicler(beat_log=bl, store=store).chronicle_all()
        print(f"[seed] chronicled {rep['chapters']} chapters across {rep['tracks']} tracks "
              f"({rep['total_beats']} beats); story -> {rep['story_md']}")


if __name__ == "__main__":
    main()
