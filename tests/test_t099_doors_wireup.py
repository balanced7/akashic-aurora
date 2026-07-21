"""T099 door wire-up pins — toast + kit get their agent_cli verbs.

kimi built both modules exec-off with INJECTED doors ("agent_cli passes the real
senders; tests pass recorders" — toast.py docstring); the CLI verbs were the flagged
next wire-up (HALF-2 handoff: "the cmd_kit agent_cli door is the obvious next wire-up
when an exec seat lands"). These pins cover the WIRING — the modules' own laws are
already pinned by tests/test_t099_v02_toast.py and tests/test_t099_v04_kit.py.

  P1  both verbs parse and route to their cmd functions
  P2  toast REFUSES an unverifiable receipt (rc 2), nothing sent on either surface
  P3  toast --force sends honestly GUESS-labeled on both surfaces
  P4  toast with a store-verified receipt sends VERIFIED
  P5  kit install rides belt.mint with $SELF$ substituted (no literal survives)
  P6  kit --show prints without installing (belt untouched)
  P7  over-long credit refuses loudly (rc 2, the MAX_BODY law through the door)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):          # absent optional flags read as None
        return None


class BusRec:
    def __init__(self):
        self.sent = []

    def __call__(self, to, kind, text):
        self.sent.append((to, kind, text))


class NoteRec:
    def __init__(self):
        self.written = []

    def __call__(self, title, body):
        self.written.append((title, body))


class StoreStub:
    """Verifies exactly one experiment name as belonging to `owner`."""
    def __init__(self, name=None, owner=None):
        self.name, self.owner = name, owner

    def _load_experiment(self, rec):
        if self.name and rec == self.name:
            return {"agent_id": self.owner, "experiment_name": self.name}
        return None

    def load_all_learnings_from_store(self):
        return ([{"experiment_name": self.name, "agent_id": self.owner}]
                if self.name else [])


class BeltRec:
    agent = "tclaude-doors"

    def __init__(self):
        self.minted = []

    def get(self, name):
        return None

    def mint(self, name, steps, **kw):
        self.minted.append((name, steps, kw))
        return {"version": 1, "evidence": kw.get("evidence", "GUESS")}


def test_p1_verbs_parse():
    p = agent_cli.build_parser()
    a = p.parse_args(["toast", "tclaude-doors", "deepseek", "some_receipt",
                      "--credit", "saved me hops"])
    assert a.fn is agent_cli.cmd_toast and a.to == "deepseek" and a.receipt == "some_receipt"
    b = p.parse_args(["kit", "tclaude-doors", "--show"])
    assert b.fn is agent_cli.cmd_kit and b.show


def test_p2_toast_refuses_bad_receipt():
    bus, note = BusRec(), NoteRec()
    ns = Ns(agent_id="tclaude-doors", to="deepseek", receipt="not_a_real_experiment",
            credit="hollow", force=False, json=False)
    rc = agent_cli.cmd_toast(ns, bus_send=bus, note_write=note, store=StoreStub())
    assert rc == 2
    assert bus.sent == [] and note.written == []      # refusal = NOTHING lands


def test_p3_toast_force_sends_guess():
    bus, note = BusRec(), NoteRec()
    ns = Ns(agent_id="tclaude-doors", to="deepseek", receipt="unverified_thing",
            credit="thanks anyway", force=True, json=False)
    rc = agent_cli.cmd_toast(ns, bus_send=bus, note_write=note, store=StoreStub())
    assert rc == 0
    (to, kind, text), = bus.sent
    assert to == "deepseek" and kind == "note" and "GUESS" in text
    (title, body), = note.written
    assert title.startswith("toast:") and "GUESS" in body


def test_p4_toast_verified_receipt():
    bus, note = BusRec(), NoteRec()
    ns = Ns(agent_id="tclaude-doors", to="deepseek", receipt="real_lesson",
            credit="two clean sends, zero bounces", force=False, json=False)
    rc = agent_cli.cmd_toast(ns, bus_send=bus, note_write=note,
                             store=StoreStub("real_lesson", "deepseek"))
    assert rc == 0
    (_, _, text), = bus.sent
    assert "[VERIFIED]" in text and "real_lesson" in text


def test_p5_kit_install_self_substituted():
    belt = BeltRec()
    ns = Ns(agent_id="tclaude-doors", kit_name="recovery-kit", show=False, json=False)
    rc = agent_cli.cmd_kit(ns, belt=belt)
    assert rc == 0 and len(belt.minted) >= 3          # the harvest has >= 3 entries
    flat = json.dumps([s for _, s, _ in belt.minted])
    assert "$SELF$" not in flat and "tclaude-doors" in flat


def test_p6_kit_show_installs_nothing(capsys):
    belt = BeltRec()
    ns = Ns(agent_id="tclaude-doors", kit_name="recovery-kit", show=True, json=False)
    rc = agent_cli.cmd_kit(ns, belt=belt)
    assert rc == 0 and belt.minted == []
    assert "recovery-kit" in capsys.readouterr().out


def test_p7_overlong_credit_refuses():
    bus, note = BusRec(), NoteRec()
    ns = Ns(agent_id="tclaude-doors", to="deepseek", receipt="real_lesson",
            credit="x" * 500, force=False, json=False)
    rc = agent_cli.cmd_toast(ns, bus_send=bus, note_write=note,
                             store=StoreStub("real_lesson", "deepseek"))
    assert rc == 2 and bus.sent == []
