"""T292 RED -- the scout: the first calibrated role, worn not owned.

DANIIL'S FRAME (2026-08-12, verbatim): "I believe managing context and setting up helper
functions and roles will play a significant part in it." The scout is the first role built
on the T290 verdict planes: a read-only pre-flight answering "is another seat mid-flight in
my area" and "has this been done already" -- the two questions whose wrong answers cost
rebuilds and collisions (the next-focus scout design; intent.py found doorless by it).

THE LAWS (fence r2 reconciliation, docs/library/design/20260812_fence-r2-reconciliation_825c9a.md):

  THE CUSTODIAN IS THE BUILDER (Navi C3, accepted amended): the pack is MECHANICAL,
  rebuilt from live sources on every call -- ledger, locks, scout verdicts. A curated
  pack rots; a built pack cannot.

  ROLE-SCOPED, NOT WEARER-SCOPED (Heimdall C3): the role's memory is the verdicts filed
  under role=Scout, whoever wore it. Wearer B reads wearer A's record, or the role has
  no continuity and the design is decoration.

  READ-ONLY, CITATIONS REQUIRED (the charter): a scout cites ledger ids, lock holders
  and ask_ids from the pack; an absence claim states the search performed. It proposes
  nothing and builds nothing -- "the fleet scouts; he judges."

Pins:
  P1  planted in-flight drill: a CLAIMED ledger row and a LIVE lock appear in the pack
      with their ids and holders -- citations, not vibes
  P2  settled-work drill: a DONE row appears under RECENTLY DONE, so "has this been done"
      is answered by the row rather than by a rebuild proposal
  P3  role memory is role-scoped: a Scout verdict filed by wearer A appears in the pack
      built for wearer B
  P4  scout_ask pipeline (scripted client, zero live spend): answers ride back; the
      verdict files under wearer AND role; the assignment is recorded ONCE -- a second
      call adds no duplicate assignment event; blind=True files agent='blind' and skips
      the assignment (no identity sheet, nothing to wear)
  P5  bounds honesty (T120): the pack meta declares each section and its count; an empty
      section renders '(none)' -- absence visible, never missing

Run: py -m pytest tests/test_t292_scout_role.py -q
"""
import os
import re
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from core.fleet import scout as S  # noqa: E402
from core.fleet import residents as R  # noqa: E402
from core.fleet import verdicts as V  # noqa: E402


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


class _Resp:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})(),
                                       "finish_reason": "stop"})()]
        self.usage = None


class _Scripted:
    """The t182/t281 harness shape: a fake client keyed by prompt substring."""
    def __init__(self, table):
        class _Completions:
            @staticmethod
            def create(model=None, messages=None, max_tokens=None, **kw):
                prompt = messages[-1]["content"]
                for key, text in table.items():
                    if key in prompt:
                        return _Resp(text)
                return _Resp("unscripted")
        self.table = table
        self.chat = type("Chat", (), {"completions": _Completions()})()


def _propose(title):
    rc, out, err = run("task", "propose", title)
    assert rc == 0, f"drill propose failed: {err or out}"
    m = re.search(r"proposed (T\d+)", out)
    assert m, f"no task id in: {out}"
    return m.group(1)


def _make_resident(agent, callsign, peer="navi_t292"):
    """The FULL ceremony through the real doors -- seed a receipt the nominee authored,
    nominate by a peer, ratify by a human. A shortcut here would test a registry that
    production never sees."""
    rc, out, err = run("learn", agent, "--experiment", f"t292_receipt_{agent}",
                       "--tried", "t292 drill receipt", "--result", "seeded")
    assert rc == 0, f"receipt seed failed: {err or out}"
    rec = R.nominate(nominee=agent, callsign=callsign,
                     receipts=[f"t292_receipt_{agent}"], by=peer)
    R.ratify(nominee=agent, callsign=callsign, by="daniil")
    return rec


# ---------------------------------------------------------------- P1: in-flight drill
def test_p1_claimed_row_and_live_lock_surface_with_citations():
    tid = _propose("t292 drill: frobnicate the widget subsystem")
    rc, out, err = run("task", "approve", tid)
    assert rc == 0, err or out
    rc, out, err = run("task", "claim", tid, "--by", "drill_owner")
    assert rc == 0, err or out

    from core.comm.locks import LockManager
    lk = LockManager("drill_holder").acquire("core/widget_frobnicator.py",
                                             note="t292 drill lock")
    assert lk.get("ok") or lk.get("mine"), f"drill lock not acquired: {lk}"

    text, meta = S.build_pack()
    assert tid in text and "drill_owner" in text, (
        "P1: the claimed row surfaces WITH id and owner -- a scout that cannot cite the "
        "row cannot warn the caller off it")
    assert "widget_frobnicator" in text and "drill_holder" in text, (
        "P1: the live lock surfaces with path and holder")


# ---------------------------------------------------------------- P2: settled drill
def test_p2_done_row_answers_has_this_been_done():
    tid = _propose("t292 drill: build the gizmo deduplicator")
    for step in (("approve", tid), ("claim", tid, "--by", "drill_owner"),
                 ("verify", tid)):
        rc, out, err = run("task", *step)
        assert rc == 0, f"{step}: {err or out}"
    rc, out, err = run("task", "done", tid, "--commit", "deadbee",
                       "--verified-by", "t292 drill")
    assert rc == 0, err or out

    text, meta = S.build_pack()
    assert tid in text, (
        "P2: the DONE row is IN the pack -- 'has this been done' gets answered by the "
        "ledger row, never by a fresh proposal to rebuild it (the DONE-is-closed law)")


# ---------------------------------------------------------------- P3: role continuity
def test_p3_scout_memory_is_role_scoped_not_wearer_scoped():
    V.file_verdict(agent="p3_wearer_a", ask_id="scout-p3-1", question_shape="coverage",
                   gist="intent.py exists and has no door", role=S.SCOUT_ROLE)
    text, meta = S.build_pack(for_wearer="p3_wearer_b")
    assert "scout-p3-1" in text and "intent.py" in text, (
        "P3: wearer B reads wearer A's scout verdicts -- the role remembers, not the "
        "wearer (fence H-C3; without this the role is decoration)")


# ---------------------------------------------------------------- P4: the pipeline
def test_p4_scout_ask_files_once_and_returns():
    _make_resident("p4_scout_wearer", "Pathfinder")
    client = _Scripted({"anyone mid-flight": "No seat holds that area. UNKNOWN beyond pack."})

    r1 = S.scout_ask("is anyone mid-flight on the flux capacitor?",
                     wearer="p4_scout_wearer", by="claude", client=client)
    assert "No seat holds" in (r1.get("answer") or ""), f"P4: answer rides back: {r1}"
    assert r1.get("tier") == "resident"

    vs = V.verdicts(agent="p4_scout_wearer", role=S.SCOUT_ROLE)
    assert len(vs) == 1 and vs[0]["ask_id"] == r1["ask_id"], (
        "P4: the verdict filed under wearer AND role, joined to the returned ask_id")

    S.scout_ask("is anyone mid-flight on the flux capacitor?",
                wearer="p4_scout_wearer", by="claude", client=client)
    assigns = R.roles(agent="p4_scout_wearer", role=S.SCOUT_ROLE)
    assert len(assigns) == 1, (
        "P4: assign-once -- a second scout_ask with the same wearer adds no duplicate "
        "assignment event; the verdict stream records the acts, the sheet records the job")

    rb = S.scout_ask("is anyone mid-flight on the flux capacitor?",
                     wearer="p4_scout_wearer", by="claude", client=client, blind=True)
    assert rb.get("tier") == "blind"
    blind_vs = V.verdicts(agent="blind", role=S.SCOUT_ROLE)
    assert any(v["ask_id"] == rb["ask_id"] for v in blind_vs), (
        "P4: a blind scout files under agent='blind' (T261 tier vocabulary) and never "
        "touches the identity sheet")


# ---------------------------------------------------------------- P5: bounds honesty
def test_p5_pack_declares_its_bounds():
    text, meta = S.build_pack()
    secs = meta.get("sections") or {}
    for name in ("in_flight", "recently_done", "locks", "scout_memory"):
        assert name in secs, f"P5: section '{name}' declared in meta (T120: a partial "
        "surface states its bounds)"
    assert "(none)" in text or all(v for v in secs.values()), (
        "P5: an empty section renders '(none)' -- absence is visible, never missing")
