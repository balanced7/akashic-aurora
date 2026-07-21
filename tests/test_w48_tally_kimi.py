"""W48 pins — tally: the blind-counter consensus matrix (kimi builder round 2026-07-21).

Design: kimi's tools-hunt #4 (research/reviewed/kimi-tools-hunt-tonight-2026-07-21.md);
charter brief research/briefs/kimi-builder-tally-brief-2026-07-21.md. tally <opening-file>
scans research/ for counter files that NAME the opening, aligns their Q-ids
(Q1/Q2/... / B1/B2/...), and prints the agree/conflict matrix so the committer sees
consensus at a glance instead of eyeballing 2-3 blind counters. Born from the seat-zero
counter's consensus math ending on an unverified "if deepseek's counters land compatible."

  P1  find_counters matches a real opening->counter pair by basename/slug, excludes the
      opening itself, and ignores files that never name it
  P2  extract_positions parses the spec forms: "Q1 AMEND ..." -> {Q1: AMEND};
      "B3 KEEP + AMEND" -> {B3: KEEP} (first verdict word wins)
  P3  the TITLE TRAP: "B1 — stale-directive kill: KEEP, re-scoped + AMEND." yields
      {B1: KEEP}, NOT KILL -- a slice title can carry a vocab word; the verdict follows
      the colon. "(parenthetical): VERDICT" plays by the same rule, and a prose q-id
      citation ("the Q7 consensus") never parses (anchored lines only)
  P4  matrix marks AGREE when two counters share a verdict and CONFLICT when they differ
  P5  PARTIAL when some authors are silent -- and a ONE-VOICE row never reads AGREE
      (2-of-3 cannot be pronounced from a single counter: the seat-zero lesson, made a law)
  P6  empty research dir -> empty matrix, no crash; render carries the 0/0/0 tally line
  P7  author derivation handles both filename orders: kimi-seat-zero-counter-... -> kimi;
      packet-routing-counter-deepseek-... -> deepseek
  P8  LIVE dogfood: the real seat-zero opening + kimi's real counter -> kimi column with
      B1=KEEP and Q1=AGREE; the counter-BRIEF (names the opening, carries no verdict
      lines) lands in mentions, NOT as a column -- mentions are not counters
  P9  CLI wiring: the verb parses to cmd_tally; happy path rc 0 end-to-end through the
      parser. SKIP-STATE 2026-07-21: the builder allowlist (security/acl.json kimi
      record) covers core/toolbelt/** + tests/** but NOT agent_cli.py -- the verb door
      rides the fence seat (W46 precedent @ef20dac: modules self-serve, wiring fenced;
      W50 names the genus). The wiring seat: remove the skip, paste the two blocks
      below into agent_cli.py (parser block after the clobber-scan parser block at
      ~line 3994, cmd function after cmd_clobber_scan's end ~line 4367), pin goes GREEN.
      WIRED by claude's fence mid-round (concurrent with the live build; skip removed).
  P10 the POSSESSIVE trap (live catch): "B4's baseline). Recommendation: adopt X" is
      prose, not a verdict header -- the apostrophe satisfies \b, and last-wins let it
      clobber the real B4=KEEP with ADOPT on the REAL counter. Possessive q-ids never
      parse; the live B4 row reads KEEP.

PASTE BLOCK 1 -- parser (after the clobber-scan parser block):

    ta = sub.add_parser("tally", help="W48 (kimi): blind-counter consensus matrix -- "
                                      "scan research/ for counters naming an opening, "
                                      "align their Q-ids, print agree/conflict at a glance")
    ta.add_argument("opening", help="the opening file (repo-relative or absolute)")
    ta.add_argument("--research-dir", default="research",
                    help="directory scanned for counters (default: research)")
    ta.add_argument("--json", action="store_true", help="emit the matrix as JSON")
    ta.set_defaults(fn=cmd_tally)

PASTE BLOCK 2 -- cmd (after cmd_clobber_scan, before cmd_unwedge):

def cmd_tally(args):
    '''tally <opening-file> [--research-dir research]: the blind-counter consensus
    matrix (W48, kimi builder round). Finds counter files that NAME the opening, aligns
    their Q-ids, and prints agree/conflict/partial per row. READ-ONLY; a reviewer aid,
    not a gate -- ONE VOICE never reads as consensus.'''
    from core.toolbelt import tally as tl
    try:
        out = tl.run(str(getattr(args, "opening", "") or ""),
                     research_dir=str(getattr(args, "research_dir", "") or "research"),
                     as_json=bool(getattr(args, "json", False)))
    except Exception as e:
        print(f"[tally] {type(e).__name__}: {e}")
        return 2
    print(out)
    return 0
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.toolbelt import tally as tl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(d, name, text):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


OPENING_NAME = "seat-zero-brief-opening-claude-2026-07-21.md"
OPENING_TEXT = ("# Seat-Zero Brief (opening position)\n\n"
                "- **B1 — stale-directive kill.** COUNTER-Q1 (deepseek): auto vs prompt?\n"
                "- **B2 — note drill verb.**\n"
                "- **B3 — standing queue.** COUNTER-Q2: registry vs ledger tag?\n")


def test_p1_find_counters_matches_naming_files_only(tmp_path):
    research = str(tmp_path / "research")
    os.makedirs(os.path.join(research, "drafts"))
    os.makedirs(os.path.join(research, "reviewed"))
    opening = _write(os.path.join(research, "drafts"), OPENING_NAME, OPENING_TEXT)
    counter = _write(os.path.join(research, "reviewed"),
                     "kimi-seat-zero-counter-2026-07-21.md",
                     "Counter to: research/drafts/" + OPENING_NAME + "\n**B1: KEEP**\n")
    _write(os.path.join(research, "reviewed"), "kimi-unrelated-2026-07-21.md",
           "nothing to do with any opening\n")
    found = tl.find_counters(opening, research)
    assert [os.path.basename(f) for f in found] == ["kimi-seat-zero-counter-2026-07-21.md"], \
        "the counter names the opening's basename; the opening itself and unrelated files stay out"


def test_p2_extract_positions_spec_forms():
    pos = tl.extract_positions("Q1 AMEND the ordering pin\nB3 KEEP + AMEND\n")
    assert pos == {"Q1": "AMEND", "B3": "KEEP"}, \
        "spec forms: first verdict word after the q-id wins"


def test_p3_title_trap_and_parenthetical_and_prose():
    # the slice TITLE 'stale-directive kill' carries a vocab word; the verdict follows
    # the colon. A naive first-vocab-word scan reads KILL -- the exact cry-wolf this
    # tool exists to refuse (kimi's own real counter is the fixture).
    pos = tl.extract_positions(
        "**B1 — stale-directive kill: KEEP, re-scoped + AMEND.**\n"
        "  **Q1 (auto vs prompt): AGREE with auto-with-tombstone.**\n"
        "the Q7 consensus was never a verdict line\n"
        "- Q9 maybe KEEP maybe KILL, undecided prose has no colon and parses honestly\n")
    assert pos.get("B1") == "KEEP", f"title trap defused: {pos}"
    assert pos.get("Q1") == "AGREE", f"parenthetical then colon: {pos}"
    assert "Q7" not in pos, "a prose citation is not an anchored verdict line"
    assert pos.get("Q9") == "KEEP", "no colon: first verdict word after the q-id"


def test_p4_matrix_agree_and_conflict(tmp_path):
    research = str(tmp_path / "research")
    os.makedirs(research)
    opening = _write(research, OPENING_NAME, OPENING_TEXT)
    c1 = _write(research, "kimi-seat-zero-counter-2026-07-21.md",
                "Counter to: " + OPENING_NAME + "\nB1: KEEP\nQ1: AGREE\nB2: KEEP\n")
    c2 = _write(research, "deepseek-seat-zero-counter-2026-07-21.md",
                "Counter to: " + OPENING_NAME + "\nB1: KEEP\nQ1: DISAGREE\nB2: KEEP\n")
    m = tl.matrix(opening, [c1, c2])
    assert m["status"]["B1"] == "AGREE" and m["status"]["B2"] == "AGREE"
    assert m["status"]["Q1"] == "CONFLICT", "AGREE vs DISAGREE must read CONFLICT"


def test_p5_partial_and_no_one_voice_consensus(tmp_path):
    research = str(tmp_path / "research")
    os.makedirs(research)
    opening = _write(research, OPENING_NAME, OPENING_TEXT)
    c1 = _write(research, "kimi-seat-zero-counter-2026-07-21.md",
                "Counter to: " + OPENING_NAME + "\nB1: KEEP\nQ1: AGREE\n")
    c2 = _write(research, "deepseek-seat-zero-counter-2026-07-21.md",
                "Counter to: " + OPENING_NAME + "\nB1: KEEP\n")  # silent on Q1
    m = tl.matrix(opening, [c1, c2])
    assert m["status"]["Q1"] == "partial", "a silent author makes the row partial"
    one = tl.matrix(opening, [c1])
    assert one["status"]["B1"] == "partial" and one["status"]["Q1"] == "partial", \
        "ONE VOICE never reads AGREE -- 2-of-3 cannot be pronounced from a single counter"


def test_p6_empty_research_dir_no_crash(tmp_path):
    research = str(tmp_path / "research")
    os.makedirs(research)
    opening = _write(research, OPENING_NAME, OPENING_TEXT)
    m = tl.matrix(opening, tl.find_counters(opening, research))
    assert m["rows"] and m["authors"] == []
    out = tl.render(m)
    assert "0 agree / 0 conflict" in out and "0 partial" in out


def test_p7_author_derivation_both_filename_orders():
    opening = "research/drafts/packet-routing-opening-claude-2026-07-17.md"
    assert tl._author("research/reviewed/kimi-seat-zero-counter-2026-07-21.md",
                      "research/drafts/" + OPENING_NAME) == "kimi"
    assert tl._author("research/drafts/packet-routing-counter-deepseek-2026-07-17.md",
                      opening) == "deepseek", "author-last order resolves too"


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(REPO, "research", "drafts", OPENING_NAME)),
    reason="the live seat-zero fixture is not in this tree")
def test_p8_live_seat_zero_dogfood():
    opening = os.path.join(REPO, "research", "drafts", OPENING_NAME)
    found = tl.find_counters(opening, os.path.join(REPO, "research"))
    names = {os.path.basename(f): f for f in found}
    assert "kimi-seat-zero-counter-2026-07-21.md" in names, "kimi's real counter is found"
    m = tl.matrix(opening, found)
    assert m["cells"].get("B1", {}).get("kimi") == "KEEP", \
        f"the title-trap row on the REAL counter reads KEEP, not KILL: {m['cells'].get('B1')}"
    assert m["cells"].get("Q1", {}).get("kimi") == "AGREE"
    mentioned = [os.path.basename(x) for x in m["mentions"]]
    assert "kimi-seat-zero-counter-brief-2026-07-21.md" in mentioned, \
        "the brief NAMES the opening but carries no verdict lines -> mention, not a column"
    assert "kimi-seat-zero-counter-brief-2026-07-21.md" not in str(m["authors"])
    assert all(s == "partial" for s in m["status"].values()), \
        "one filed counter -> every row partial; the tool refuses one-voice consensus"


def test_p9_cli_wiring_parses_to_cmd_tally(tmp_path):
    import agent_cli
    research = str(tmp_path / "research")
    os.makedirs(research)
    opening = _write(research, OPENING_NAME, OPENING_TEXT)
    ns = agent_cli.build_parser().parse_args(["tally", opening, "--research-dir", research])
    assert ns.fn is agent_cli.cmd_tally
    assert ns.fn(ns) == 0


def test_p10_possessive_prose_never_clobbers_a_verdict():
    # LIVE catch 2026-07-21: kimi's real counter line "  B4's baseline). **Recommendation:
    # adopt W38 ..." anchored on B4 (the apostrophe satisfies \b), and last-wins overwrote
    # the real "**B4 — suite-baseline receipt: KEEP + AMEND.**" with ADOPT. A possessive
    # q-id is prose, never a verdict header.
    pos = tl.extract_positions(
        "**B4 — suite-baseline receipt: KEEP + AMEND.**\n"
        "  B4's baseline). **Recommendation: adopt W38 at ship time.**\n"
        "  Q2's answer, looking back: REJECT the framing.\n")
    assert pos.get("B4") == "KEEP", f"possessive prose must not parse, let alone clobber: {pos}"
    assert pos.get("Q2") is None, f"a possessive line carries no verdict: {pos}"


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(REPO, "research", "reviewed",
                                    "kimi-seat-zero-counter-2026-07-21.md")),
    reason="the live seat-zero fixture is not in this tree")
def test_p10b_live_b4_reads_keep_not_adopt():
    opening = os.path.join(REPO, "research", "drafts", OPENING_NAME)
    m = tl.matrix(opening, tl.find_counters(opening, os.path.join(REPO, "research")))
    assert m["cells"].get("B4", {}).get("kimi") == "KEEP", \
        f"the live regression: B4 is KEEP + AMEND, never the possessive line's ADOPT: " \
        f"{m['cells'].get('B4')}"
