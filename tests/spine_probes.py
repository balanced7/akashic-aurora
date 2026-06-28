"""
Adversarial probes against the REAL narrative-spine code (isolated FileStore/FileLedger).
Each probe tries to surface a defect. Prints VULNERABLE / ok / robust with evidence.
Run: py spine_probes.py
"""
import json, os, sys, tempfile
sys.path.insert(0, "E:\\AI-Setup")

from core.foundation.store import FileStore
from core.foundation.ledger import FileLedger
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import TrackRouter, RouteHint
from core.narrative.chronicler import Chronicler
from core.narrative.schema import Beat, beat_key
from core.narrative.tagging import TagHistory
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from core.narrative.event_promoter import promote_salient, salience

def store():  return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
def hr(t):    print("\n" + "="*70 + f"\n{t}\n" + "="*70)

# ----------------------------------------------------------------------
hr("PROBE A — TrackRouter substring false positives")
r = TrackRouter()
cases = [
    ("restore from snapshot backup", "", "restore contains 'store' -> ?"),
    ("exploring the storage layer", "", "storage contains 'store' -> ?"),
    ("the management agent handoff", "", "'agent' generic? (agent is a PATH rule needle)"),
    ("realtime analytics dashboard", "", "'realtime' is a voice STRONG kw -> ?"),
    ("paper on disentanglement", "", "research, expected"),
    ("comfy sweater knitting notes", "", "'comfy' is a vision STRONG kw -> ?"),
]
for summ, cat, note in cases:
    b = Beat(id="x", at="2026-01-01T00:00:00", kind="note", summary=summ, source="s")
    res = r.route_one(b, RouteHint(category=cat))
    flag = "<-- SUSPECT" if res.basis in ("strong","generic") else ""
    print(f"  '{summ[:34]:34}' -> {res.track:10} ({res.basis})  {flag}  [{note}]")

# ----------------------------------------------------------------------
hr("PROBE B — Chronicler with MIXED timezone-aware/naive timestamps")
st = store(); bl = BeatLog(st)
# naive and tz-aware interleaved
bl.emit("commit", "naive A", "git:a", at="2026-01-01T01:00:00", hint=RouteHint(paths=["core/x.py"]))
bl.emit("commit", "tzaware B", "git:b", at="2026-01-01T02:00:00+00:00", hint=RouteHint(paths=["core/x.py"]))
bl.emit("commit", "naive C", "git:c", at="2026-01-01T03:00:00", hint=RouteHint(paths=["core/x.py"]))
try:
    rep = Chronicler(beat_log=bl, store=st).chronicle_all(now="2026-01-02T00:00:00")
    print(f"  did NOT crash. chapters={rep['chapters']} faithful={rep['faithful']} coverage={rep['coverage']}")
    print(f"  -> note: best-effort swallows errors; check if all 3 beats landed in a chapter")
    idx = json.loads((st.get('does-not')) or '{}') if False else None
    # count beats represented
    total = sum(len(c['beats']) for c in json.loads(open('E:/AI-Setup/chronicles/story.index.json').read())['chapters']) if False else rep['total_beats']
    print(f"  total_beats reported = {rep['total_beats']} (expected 3)")
except Exception as e:
    print(f"  VULNERABLE: chronicle CRASHED on mixed tz: {type(e).__name__}: {e}")

# ----------------------------------------------------------------------
hr("PROBE C — EventQuery window recall beyond the scan horizon (silent loss)")
el = EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="ev_")))
for i in range(8):
    el.capture("command", f"event {i}", at=f"2026-01-01T0{i}:00:00")
eq = EventQuery(event_log=el, scan=3)   # only the newest 3 are scanned
got = eq.events_in_window("2026-01-01T00:00:00", "2026-01-01T09:00:00")
print(f"  8 events captured; window covers ALL of them; scan=3")
print(f"  events_in_window returned {len(got)} (claims 'recall=100%')")
print(f"  -> {'VULNERABLE: silent recall loss' if len(got) < 8 else 'ok'}  (missing {8-len(got)} old events)")

# ----------------------------------------------------------------------
hr("PROBE D — Chronicler orphan-chapter accumulation across re-runs")
st = store(); bl = BeatLog(st)
import time
for i in range(4):
    bl.emit("commit", f"commit {i}", f"git:c{i}", at=f"2026-01-0{i+1}T01:00:00", hint=RouteHint(paths=["core/x.py"]))
ch = Chronicler(beat_log=bl, store=st)
ch.chronicle_all(now="2026-02-01T00:00:00")
keys1 = [k for k in st._data.get("kv", st._data).keys() if "narr:chapter:" in k] if isinstance(st._data, dict) else []
# FileStore stores under _data; find chapter keys
def chapter_keys(s):
    d = s._data
    flat = d.get("kv") if isinstance(d, dict) and "kv" in d else d
    return [k for k in flat.keys() if isinstance(k,str) and k.startswith("narr:chapter:")]
n1 = len(chapter_keys(st))
# now insert an EARLIER beat that shifts segment indices, re-chronicle
bl.emit("milestone", "inserted salient", "git:mid", at="2026-01-02T12:00:00", hint=RouteHint(paths=["core/x.py"]))
ch.chronicle_all(now="2026-02-02T00:00:00")
n2 = len(chapter_keys(st))
# how many are actually referenced by the track list now?
from core.narrative.schema import track_key
tr = st.get(track_key("ai-setup"))
active = len(json.loads(tr)["chapters"]) if tr else 0
print(f"  chapter:* keys after run1={n1}, after run2(with insert)={n2}; track lists {active} active")
print(f"  -> {'VULNERABLE: ' + str(n2-active) + ' orphaned chapter keys linger (unbounded growth)' if n2 > active else 'ok: no orphans'}")

# ----------------------------------------------------------------------
hr("PROBE E — TagHistory NaN / inf confidence corrupts the resolver")
h = TagHistory()
h.add("ai-setup", confidence=0.95, at="2026-01-01T00:00:00")
# inject a NaN-confidence opinion via from_list (passes float() check)
raw = h.to_list() + [{"value":"stemroller","confidence":float("nan"),"source":"x","at":"2026-01-02T00:00:00","confirmed":False}]
h2 = TagHistory.from_list(raw)
cur = h2.current()
print(f"  entries: ai-setup@0.95 + stemroller@NaN")
print(f"  current() = {cur.value if cur else None} @ conf={cur.confidence if cur else None}")
print(f"  -> {'VULNERABLE: NaN entry hijacked/blocked the resolver' if (cur is None or cur.value!='ai-setup') else 'ok: NaN ignored, ai-setup wins'}")
# also inf
raw2 = h.to_list() + [{"value":"stemroller","confidence":float("inf"),"source":"x","at":"2026-01-02T00:00:00","confirmed":False}]
cur2 = TagHistory.from_list(raw2).current()
print(f"  with +inf injected: current() = {cur2.value if cur2 else None}  -> {'VULNERABLE: inf beats a real tag' if cur2 and cur2.value=='stemroller' else 'ok'}")

# ----------------------------------------------------------------------
hr("PROBE F — Faithfulness gate vs an adversarial (hallucinating) writer")
from core.primitives.distiller import Distiller, Distillation
st = store(); bl = BeatLog(st)
bl.emit("commit", "real beat", "git:real", at="2026-01-01T01:00:00", hint=RouteHint(paths=["core/x.py"]))
def lying_writer(items, budget, instruction):
    # emit a (source: ...) that points at a beat NOT in this chapter
    return Distillation(skeleton="- fabricated claim  (source: git:HALLUCINATED)",
                        entries=[{"summary":"fab","source":"git:HALLUCINATED"}],
                        included_sources=["git:HALLUCINATED"], dropped_sources=[],
                        approx_tokens=10, critic_ok=True)
chl = Chronicler(beat_log=bl, store=st, distiller=Distiller(writer=lying_writer))
rep = chl.chronicle_all(now="2026-02-01T00:00:00")
print(f"  injected writer emits (source: git:HALLUCINATED) not in any chapter")
print(f"  faithful = {rep['faithful']}")
print(f"  -> {'GOOD: gate caught the hallucination' if rep['faithful'] is False else 'VULNERABLE: gate did NOT catch a fabricated source pointer'}")

# ----------------------------------------------------------------------
hr("PROBE G — Salience promotion: empty/garbage events + flood control")
el = EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="ev2_")))
# 50 high-salience 'error' events
for i in range(50):
    el.capture("command", f"build failed error {i}", at=f"2026-01-01T00:{i:02d}:00")
# a couple of garbage ones
el.capture("note", None, at="2026-01-01T01:00:00")
el.capture("", "", at="2026-01-01T01:01:00")
st = store()
rep = promote_salient(st, EventQuery(event_log=el), threshold=3, max_promote=10, scan=500)
print(f"  promote report: {rep}")
print(f"  -> per-run cap respected? {'ok' if rep['promoted'] <= 10 else 'VULNERABLE: flood'}")
# re-run: dedup must hold
rep2 = promote_salient(st, EventQuery(event_log=el), threshold=3, max_promote=10, scan=500)
print(f"  re-run promoted={rep2['promoted']} skipped_dup={rep2['skipped_dup']} -> {'ok: dedup holds' if rep2['skipped_dup']>0 else 'check'}")

print("\nDONE.")
