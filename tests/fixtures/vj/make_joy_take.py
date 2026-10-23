"""Write state/arsenal/keylab/joy_take_events.json (gitignored): Daniel's Joy to the World take as the VJ page receives it.

    py tests/fixtures/vj/make_joy_take.py <notes>      # a score-log JSON note list, or the .flp itself
    py tests/fixtures/vj/make_joy_take.py --refresh    # re-run the engine on the notes the fixture already keeps

The take is the newest score-log pattern of Worship Grandeur Piano.flp (pattern 7, stretch 2: 1378 notes, D-flat major,
ending on D-flat 4 struck 89 times over a walking bass). The project carries no tempo, so it plays at the replay's
assumed 100 BPM, as `py -m arsenal.keylab vj --replay-midi` would play it. arsenal.keylab.vj.replay_events runs the
notes through the engine's own path (note events, the key, the keys' chord names after the settle) on a simulated
clock. The fixture keeps the notes (the source: [on_s, off_s, key, velocity 1..127]) and what the page acts on, one row
per event:

    [t, "n", key, vel]   note on (vel 0..1)        [t, "f", key]   note off        [t, "c", name]   chord (keys)

tests/vj_core.test.mjs replays the events through the page's PedalDetector; tests/test_keylab_vj.py checks they are
still exactly what the engine produces from the notes (rerun this script when the engine's chord naming changes).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from arsenal.keylab import vj as V  # noqa: E402

# the take is Daniel's own playing: written to the gitignored state/ folder, never into the public repo
OUT = HERE.parents[2] / "state" / "arsenal" / "keylab" / "joy_take_events.json"


def rows(events) -> list:
    out = []
    for t, e in events:
        if e["t"] == "note":
            out.append([t, "n", e["key"], e["vel"]] if e["on"] else [t, "f", e["key"]])
        elif e["t"] == "chord":
            out.append([t, "c", e["name"]])
    return out


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    if argv[0] == "--refresh":
        # the engine changed (chord naming, the settle, chordsense on the keys): the same notes, the events anew
        if not OUT.exists():
            print(f"no fixture to refresh at {OUT}: make it from the take's notes first")
            return 1
        doc = json.loads(OUT.read_text(encoding="utf-8"))
        rp = V.Replay([tuple(n) for n in doc["note_list"]], doc.get("replay", "joy"))
        doc["events"] = rows(V.replay_events(rp))
        OUT.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"refreshed {OUT} ({len(doc['events'])} rows)")
        return 0
    rp = V.load_replay(argv[0])
    doc = {
        "what": "Daniel's Joy to the World take (Worship Grandeur Piano.flp score log, pattern 7, stretch 2) as the VJ "
                "page receives it from `vj --replay-midi`: arsenal.keylab.vj.replay_events on a simulated clock",
        "replay": rp.label,
        "notes": len(rp.notes),
        "seconds": round(rp.seconds, 3),
        "rows": "[t, 'n', key, vel] note on | [t, 'f', key] note off | [t, 'c', name] keys chord",
        "events": rows(V.replay_events(rp)),
        "note_list": [list(n) for n in rp.notes],
    }
    OUT.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(doc['events'])} rows, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
