"""W46 pins — the followup verb (kimi's first self-serve build, builder round 2026-07-21).

Design: kimi's own tools-hunt #2 (docs/library/report/20260721_tools-hunt-tonight-s-edition-kimi-2026-0_974493.md);
charter brief docs/library/brief/20260721_kimi-builder-brief-followup-verb-first-s_2d53b3.md. Fire-and-forget
charter verdicts get a question-back channel: one verb writes BOTH halves — the verdict
file's `## Open Questions` block (q-id'd question line) AND the W33 defer queue (the
responsible seat's next boot surfaces it; the discharge receipt points at the answered
block). Convention: `- Q# (date, by -> to) OPEN: ask`; answering flips OPEN -> ANSWERED.

  P1  question lands inside an existing Open Questions block with the minted q-id;
      surrounding content preserved
  P2  the defer item carries the pointer: file + q-id + ask in cmd, responsible seat in
      why, by=asker, needs=write (answering means editing the file)
  P3  missing verdict file REFUSES loudly — and queues NOTHING (file-half first, so a
      refusal can never leave a pointer at a question that was never written)
  P4  the block is created if absent (appended at EOF), prior content byte-preserved
  P5  q-ids mint collision-free against Q-ids anywhere in the file (body Q7 -> next Q8)
  P6  a replayed ask is idempotent (RB-26 crash-redelivery law): one question line, one
      pending defer item, same ids, reuse reported
  P7  door hygiene: path outside the repo root refuses; empty ask / empty --to refuse;
      every refusal leaves the queue untouched
  P8  CLI wiring: the verb parses to cmd_followup; happy path rc 0 end-to-end through
      the parser; a missing file exits rc 2 with a loud line and queues nothing.
      SKIP-STATE 2026-07-21: the builder allowlist (security/acl.json kimi record)
      covers core/toolbelt/** + tests/** but NOT agent_cli.py -- the verb door itself
      rides the fence seat (toast/kit precedent @e3049f7: modules self-serve, wiring
      fenced). W50 filed. The wiring seat: remove the skip, paste the two blocks
      below into agent_cli.py (parser block after `df.set_defaults(fn=cmd_defer)`,
      cmd function after cmd_defer's end), this pin goes GREEN.

PASTE BLOCK 1 -- parser (after the defer parser block):

    fu = sub.add_parser("followup", help="the question-back channel for fire-and-forget "
                                         "charters (W46): append a q-id'd question to a "
                                         "verdict file's Open Questions block AND defer it "
                                         "to the responsible seat's next boot")
    fu.add_argument("agent_id", help="you (the asking seat)")
    fu.add_argument("--on", required=True, metavar="VERDICT_FILE",
                    help="the verdict file to question (repo-relative or absolute; must exist)")
    fu.add_argument("--ask", required=True, help="the question text")
    fu.add_argument("--to", required=True,
                    help="the responsible seat the question defers to (their boot surfaces it)")
    fu.add_argument("--needs", default="write",
                    help="capability the answering seat needs (default write: it edits the file)")
    fu.set_defaults(fn=cmd_followup)

PASTE BLOCK 2 -- cmd (after cmd_defer, before cmd_kit):

def cmd_followup(args):
    '''followup <me> --on <verdict-file> --ask "..." --to <seat> [--needs write]: the
    question-back channel for fire-and-forget charters (W46). One verb writes both
    halves: the q-id'd question into the file's ## Open Questions block + the W33
    defer item the responsible seat's next boot surfaces. File-half first;
    replay-safe (RB-26); refusals queue nothing.'''
    from core.toolbelt import followup as fq
    try:
        res = fq.file_followup(str(getattr(args, "on", "") or ""), by=args.agent_id,
                               to=str(getattr(args, "to", "") or ""),
                               ask=str(getattr(args, "ask", "") or ""),
                               needs=str(getattr(args, "needs", "") or "write"))
    except (ValueError, FileNotFoundError) as e:
        print(f"[followup] REFUSED: {e}")
        return 2
    if res["reused_line"]:
        print(f"[followup] {res['qid']} already OPEN in {res['path']} "
              f"(replayed ask -- no duplicate written)")
    else:
        made = "created ## Open Questions + " if res["created_block"] else ""
        print(f"[followup] {made}appended {res['qid']} to {res['path']} "
              f"({args.agent_id} -> {args.to})")
    if res["reused_defer"]:
        print(f"[followup] defer item [{res['defer_id']}] already pending -- nothing re-filed")
    else:
        print(f"[followup] defer item [{res['defer_id']}] filed -- "
              f"{args.to}'s next boot surfaces it")
    print(f"  discharge loop: {args.to} answers {res['qid']} in the file "
          f"(flip OPEN -> ANSWERED), then")
    print(f"  py agent_cli.py defer {args.to} --done {res['defer_id']} "
          f"--receipt \"answered {res['qid']}: ...\"")
    return 0
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.coord import defer_queue as dq
from core.toolbelt import followup as fq


@pytest.fixture()
def stage(tmp_path, monkeypatch):
    """Repo root + queue both sandboxed to tmp_path (the dq.QUEUE_PATH pattern)."""
    monkeypatch.setattr(fq, "ROOT", str(tmp_path))
    monkeypatch.setattr(dq, "QUEUE_PATH", str(tmp_path / "defer_queue.json"))
    return tmp_path


def _write(root, name, text):
    p = root / name
    p.write_text(text, encoding="utf-8")
    return p


def _qline(qid, ask):
    return re.compile(r"- %s \(\d{4}-\d{2}-\d{2}, kimi -> deepseek\) OPEN: %s"
                      % (qid, re.escape(ask)))


def test_p1_question_lands_inside_block_with_qid(stage):
    f = _write(stage, "verdict.md",
               "# Verdict\n\nbody citing Q1 consensus\n\n## Open Questions\n\n"
               "- Q2 (2026-07-21, claude -> deepseek) OPEN: earlier one\n\n"
               "## Next\n\ntail\n")
    res = fq.file_followup("verdict.md", by="kimi", to="deepseek", ask="is n=1 enough?")
    assert res["qid"] == "Q3" and res["created_block"] is False
    text = f.read_text(encoding="utf-8")
    m = _qline("Q3", "is n=1 enough?").search(text)
    assert m, "q-id'd question line appended"
    assert text.index("## Open Questions") < m.start() < text.index("## Next"), \
        "the line lands INSIDE the block, before the next heading"
    assert "## Next\n\ntail\n" in text, "surrounding content preserved"


def test_p2_defer_item_carries_the_pointer(stage):
    _write(stage, "v.md", "# V\n\n## Open Questions\n")
    res = fq.file_followup("v.md", by="kimi", to="deepseek", ask="the ask text")
    items = dq.pending()
    assert len(items) == 1
    it = items[0]
    assert it["id"] == res["defer_id"] and it["by"] == "kimi"
    assert it["needs"] == "write", "answering means editing the verdict file"
    assert "Q1" in it["cmd"] and "v.md" in it["cmd"] and "the ask text" in it["cmd"], \
        "cmd points at the question: file + q-id + ask"
    assert "deepseek" in it["why"], "why names the responsible seat"
    stored = json.load(open(dq.QUEUE_PATH, encoding="utf-8"))
    assert len(stored["items"]) == 1, "queue file valid + holds the item"


def test_p3_missing_verdict_file_refuses_and_queues_nothing(stage):
    with pytest.raises(FileNotFoundError):
        fq.file_followup("nope.md", by="kimi", to="deepseek", ask="x")
    assert dq.pending() == [], "file-half first: a refusal never points at an unwritten question"


def test_p4_block_created_if_absent(stage):
    body = "# Verdict\n\nno block here\n"
    f = _write(stage, "v.md", body)
    res = fq.file_followup("v.md", by="kimi", to="deepseek", ask="first q")
    assert res["created_block"] is True and res["qid"] == "Q1"
    text = f.read_text(encoding="utf-8")
    assert text.startswith(body), "prior content byte-preserved"
    assert "## Open Questions" in text
    assert _qline("Q1", "first q").search(text)


def test_p5_qid_never_collides_with_body_qids(stage):
    _write(stage, "v.md", "# V\n\nsee the Q7 consensus and the Q2 race\n")
    res = fq.file_followup("v.md", by="kimi", to="deepseek", ask="q")
    assert res["qid"] == "Q8", "minting scans the WHOLE file, not just the block"


def test_p6_replayed_ask_is_idempotent(stage):
    f = _write(stage, "v.md", "# V\n")
    a = fq.file_followup("v.md", by="kimi", to="deepseek", ask="same ask")
    b = fq.file_followup("v.md", by="kimi", to="deepseek", ask="same ask")
    assert (a["qid"], a["defer_id"]) == (b["qid"], b["defer_id"])
    assert b["reused_line"] and b["reused_defer"]
    text = f.read_text(encoding="utf-8")
    assert text.count("same ask") == 1, "one question line, not two"
    assert len(dq.pending()) == 1, "one pending defer item, not two"


def test_p7_door_hygiene_refusals(stage, tmp_path):
    outside = tmp_path.parent / "outside_root.md"
    outside.write_text("# x\n", encoding="utf-8")
    with pytest.raises(ValueError):
        fq.file_followup(str(outside), by="kimi", to="deepseek", ask="q")
    _write(stage, "v.md", "# V\n")
    with pytest.raises(ValueError):
        fq.file_followup("v.md", by="kimi", to="deepseek", ask="   ")
    with pytest.raises(ValueError):
        fq.file_followup("v.md", by="kimi", to="", ask="q")
    assert dq.pending() == [], "every refusal leaves the queue untouched"


@pytest.mark.skip(reason="agent_cli.py is outside the builder allowlist -- the verb "
                         "wiring rides the fence seat (paste blocks in the module "
                         "docstring); unskip when cmd_followup lands")
def test_p8_cli_wiring_and_refusal_rc(stage, capsys):
    p = agent_cli.build_parser()
    a = p.parse_args(["followup", "kimi", "--on", "v.md",
                      "--ask", "is it enough?", "--to", "deepseek"])
    assert a.fn is agent_cli.cmd_followup
    f = _write(stage, "v.md", "# V\n\n## Open Questions\n")
    assert a.fn(a) == 0
    out = capsys.readouterr().out
    assert "Q1" in out and "deepseek" in out
    assert "is it enough?" in f.read_text(encoding="utf-8")
    assert len(dq.pending()) == 1

    b = p.parse_args(["followup", "kimi", "--on", "gone.md", "--ask", "x", "--to", "deepseek"])
    assert b.fn(b) == 2
    assert "REFUSED" in capsys.readouterr().out
    assert len(dq.pending()) == 1, "the refusal queued nothing"
