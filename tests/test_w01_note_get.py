"""W01 pins — `note <me> --get <id-or-title>`: read ONE full note body, no JSON pipe dance.

Wish W01 (kimi 07-18, re-bitten by the fable seat 07-21: three fumbled calls to read
where-we-are's body at boot). Resolution law: exact id first (superseded ids are legal
archaeology, labeled); then normalized-title match among ACTIVE notes (the head).
  P1  parser accepts --get
  P2  exact id resolves, superseded copies render labeled
  P3  bare title resolves the newest ACTIVE head
  P4  title matching only superseded notes = teaching error naming the newest ghost id
  P5  no match = loud error, rc 1
  P6  --json emits the full record
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.learning.agent_memory import Decision


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


def _dec(id, title, body, superseded=False, at="2026-07-21T01:00:00"):
    return Decision(id=id, title=title, status="decided", context="ctx-" + id,
                    decision=body, rationale=[], alternatives=[], consequences={},
                    created_at=at, superseded=superseded)


class FakeMem:
    def __init__(self, decisions):
        self._d = decisions

    def get_decisions(self, days=30, include_superseded=False):
        return [d for d in self._d if include_superseded or not d.superseded]


MEM = FakeMem([
    _dec("ADR_new", "where-we-are", "the CURRENT state", at="2026-07-21T02:00:00"),
    _dec("ADR_old", "where-we-are", "the OLD state", superseded=True),
    _dec("ADR_ghost", "dead-arc", "retired arc", superseded=True),
])


def test_p1_parser_accepts_get():
    p = agent_cli.build_parser()
    a = p.parse_args(["note", "claude", "--get", "where-we-are"])
    assert a.get == "where-we-are" and a.fn is agent_cli.cmd_note


def test_p2_exact_id_even_superseded(capsys):
    rc = agent_cli.cmd_note(Ns(agent_id="c", get="ADR_old", json=False), mem=MEM)
    out = capsys.readouterr().out
    assert rc == 0 and "the OLD state" in out and "SUPERSEDED" in out


def test_p3_title_resolves_active_head(capsys):
    rc = agent_cli.cmd_note(Ns(agent_id="c", get="where-we-are", json=False), mem=MEM)
    out = capsys.readouterr().out
    assert rc == 0 and "the CURRENT state" in out and "SUPERSEDED" not in out


def test_p4_superseded_only_title_teaches(capsys):
    rc = agent_cli.cmd_note(Ns(agent_id="c", get="dead-arc", json=False), mem=MEM)
    out = capsys.readouterr().out
    assert rc == 1 and "ADR_ghost" in out and "superseded" in out.lower()


def test_p5_no_match_is_loud(capsys):
    rc = agent_cli.cmd_note(Ns(agent_id="c", get="never-existed", json=False), mem=MEM)
    assert rc == 1 and "no note" in capsys.readouterr().out.lower()


def test_p6_json_full_record(capsys):
    rc = agent_cli.cmd_note(Ns(agent_id="c", get="ADR_new", json=True), mem=MEM)
    rec = json.loads(capsys.readouterr().out)
    assert rc == 0 and rec["decision"] == "the CURRENT state" and rec["id"] == "ADR_new"
