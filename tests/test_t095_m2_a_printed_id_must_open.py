"""T095 M2 RED: every id the mailbox PRINTS is an id the mailbox REFUSES.

Found live 2026-09-23 by the claude seat, while answering a peer's request. I held the id
`e62c8c580979`, ran the documented door, and was told:

    [mailbox] no mailbox entry for sha e62c8c580979

and the honest reading of that sentence -- the one I nearly acted on -- is THE MESSAGE IS GONE.
It was not gone. It was in the mailbox the whole time under a 64-character sha, and the only
thing wrong was that I was holding a PREFIX of its name.

THE MEASUREMENTS, taken in one file, agent_cli.py:

    :7413  listings and the ghost sweep print   sha[:10]
    :7429  the open receipt echoes              sha[:12]
    :7455  the state receipt echoes             sha[:12]
    :7472  the intent receipt echoes            sha[:12]

So there are TWO truncation widths, the doors disagree with each other, and NEITHER width opens.
Every id this system shows a reader is an id it will then deny. A seat that copies what the
screen printed -- the single most obvious thing to do -- gets told the mail does not exist.

WHY THIS IS THE SAME DEFECT AS T222, which is why this file is named after it. That pin's own
ruling: "THE FIX IS THE RESOLVER, NOT THE POINTER ... Rewriting the pointer to name some other
door would just move the lie." Same here, and the tempting wrong fix has the same shape: widen
the print to 64 chars and call it done. That trades one friction for another (unreadable
listings) and leaves every id ALREADY IN CIRCULATION -- in handoffs, reports, chat scrollback,
peer messages -- still dead. The resolver is what has to learn to accept what the system says.

AND IT IS `zero is not no` ON THE IDENTIFIER PLANE. The refusal reports one state where there
are four, and the reader cannot tell them apart:

    exact      the key resolved
    prefix     the id names exactly one entry, and is simply shorter than the key
    ambiguous  the id names several entries -- a real question, needing more characters
    absent     no entry, at any length. THE ONLY ONE THE CURRENT TEXT ACTUALLY DESCRIBES.

Three of those four are the mailbox saying "your id is short" while the reader hears "your mail
is gone". This string has a history of exactly that lie and has never once, in the incidents on
record, actually meant absent:

    T133     it meant "the sha was computed on a different basis" (content-fallback vs packet sha)
    T222     it meant "that is a stream id, this door serves content shas"
    tonight  it means "that is a prefix"

Navi's refinement, which governs the fix: do NOT collapse the empty results into one boolean,
and do NOT add an `unknown` member -- a tri-state with an escape hatch is where absence hides.
Four named states, each earned by a lookup that actually ran.

RED by construction: `resolve_sha` does not exist yet. Do not weaken a pin to make it green.

Run::

    py -m pytest tests/test_t095_m2_a_printed_id_must_open.py -q
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

NS = "test-mbx-m2"

# The widths agent_cli.py actually prints today. If a door starts printing a different width,
# add it here -- this tuple is the contract "whatever we print, we accept".
PRINTED_WIDTHS = (10, 12)


def _mailbox():
    return importlib.import_module("core.comm.mailbox")


def _fake():
    from test_t095_m0_mailbox_shadow import _FakeRedis   # reuse the M0 double, do not fork it
    return _FakeRedis()


def _ingest(mbx, client, *, sid, content, frm="kimi", kind="request", sha=None):
    """Ingest one message. `sha` mimics a real packet sha (64 hex); omitting it exercises the
    content-fallback basis, which is SHORTER (42). Both are longer than anything we print, and
    the pins below must hold for either -- an id's length is not the contract, the round trip is.
    """
    fields = {"frm": frm, "to": "claude", "kind": kind, "ts": sid.split("-")[0],
              "content": content}
    if sha:
        fields["sha"] = sha
    return mbx._ingest_one(client, NS, "claude", "work_inbox", sid, fields)


# ------------------------------------------------- THE ROUND TRIP (the wiring, not the mechanism)

def test_m2_1_every_width_the_doors_print_is_a_width_that_opens():
    """THE PIN. Not "a resolver exists" -- take the id the screen shows and feed it back.

    T222's lesson, which I re-earned tonight: I verified a pointer by checking it was PRINTED and
    never ran the command it printed. This asserts the wiring, in both directions.
    """
    mbx = _mailbox()
    client = _fake()
    sha = _ingest(mbx, client, sid="1790215960175-0", content="the transcript question")
    # NOT `== 64`. The first draft asserted that, and it was wrong in an instructive way: a packet
    # sha is 64 hex but the content-fallback basis is 42, so the pin encoded ONE sha basis as
    # though it were the requirement. The actual contract is simply that the stored id is longer
    # than every width we print -- which is exactly why the round trip below can fail at all.
    assert sha and len(sha) > max(PRINTED_WIDTHS), f"unexpectedly short sha {sha!r}"

    for w in PRINTED_WIDTHS:
        shown = sha[:w]
        got = mbx.open(NS, "claude", shown, incarnation="pin-m2", client=client)
        assert got.get("ok"), (
            f"the mailbox printed {shown!r} at width {w} and then refused it: "
            f"{got.get('reason')!r}. An id the system shows a reader must be an id the system "
            f"accepts back."
        )
        assert got["sha"] == sha, "resolved to the wrong entry"
        assert got["body"] == "the transcript question"

    # And again with a real 64-hex packet sha -- the basis production mail actually carries, and
    # the one the live incident used. Covering only the fallback basis would leave the real path
    # untested by a pin that reads as though it covered everything.
    real = "e6" + "1a2b3c4d5e6f" * 5 + "0a"
    assert len(real) == 64
    sha64 = _ingest(mbx, client, sid="1790215960177-0", content="packet basis", sha=real)
    assert sha64 == real, f"ingest did not honour the packet sha: {sha64!r}"
    for w in PRINTED_WIDTHS:
        got = mbx.open(NS, "claude", sha64[:w], incarnation="pin-m2", client=client)
        assert got.get("ok"), f"64-hex packet sha refused at width {w}: {got.get('reason')!r}"
        assert got["sha"] == sha64 and got["body"] == "packet basis"


def test_m2_2_absent_is_reported_DIFFERENTLY_from_short():
    """`zero is not no`, on the identifier plane.

    A reader must be able to tell "your id is short" from "your mail is gone" WITHOUT opening the
    source, because the entire cost of this defect is that the two are currently one sentence.
    """
    mbx = _mailbox()
    client = _fake()
    sha = _ingest(mbx, client, sid="1790215960175-0", content="present and correct")

    absent = mbx.resolve_sha(NS, "claude", "f" * 40, client=client)
    assert absent["how"] == "absent", f"expected absent, got {absent['how']!r}"

    short = mbx.resolve_sha(NS, "claude", sha[:10], client=client)
    assert short["how"] == "prefix", f"expected prefix, got {short['how']!r}"
    assert short["sha"] == sha

    # And the human-facing sentence must differ too -- a distinction visible only in a dict field
    # is a distinction the reader at the terminal never sees.
    assert absent.get("reason") and absent["reason"] != short.get("reason", ""), (
        "absent and prefix produce the same prose; the terminal reader learns nothing"
    )


def test_m2_3_an_ambiguous_prefix_refuses_and_names_the_candidates():
    """Never silently pick one. Two entries sharing a prefix is a REAL question, and the answer
    is "give me more characters", with the candidates shown so the reader can."""
    mbx = _mailbox()
    client = _fake()
    a = _ingest(mbx, client, sid="1790215960175-0", content="first")
    b = _ingest(mbx, client, sid="1790215960176-0", content="second")
    assert a != b

    shared = ""
    for i in range(1, 65):
        if a[:i] == b[:i]:
            shared = a[:i]
        else:
            break

    if shared:
        amb = mbx.resolve_sha(NS, "claude", shared, client=client)
        assert amb["how"] == "ambiguous", f"expected ambiguous for {shared!r}, got {amb['how']!r}"
        assert amb.get("sha") is None, "an ambiguous id must NOT resolve to a guess"
        assert len(amb.get("candidates") or []) >= 2, "ambiguity reported without the candidates"
        assert all(c.startswith(shared) for c in amb["candidates"])

    # The property that holds regardless of which shas the fixture minted: a one-character prefix
    # of a mailbox holding two entries either resolves or is ambiguous -- never absent, and never
    # a silent pick. "The case did not arise" must never read as "the case passed".
    one = mbx.resolve_sha(NS, "claude", a[:1], client=client)
    assert one["how"] in ("exact", "prefix", "ambiguous"), (
        f"a live prefix reported {one['how']!r} -- absence is being used to mean short"
    )
    if one["how"] == "ambiguous":
        assert one.get("sha") is None


def test_m2_4_all_the_doors_accept_what_all_the_doors_print():
    """open / state_for / declare_intent each take a typed id, and each prints one. A fix that
    lands on `open` alone leaves a reader who ran `--state` in exactly the same hole."""
    mbx = _mailbox()
    client = _fake()
    sha = _ingest(mbx, client, sid="1790215960175-0", content="four doors")
    shown = sha[:12]

    st = mbx.state_for(NS, "claude", shown, client=client)
    assert st.get("found"), f"--state refused a printed id: {st!r}"
    assert st["sha"] == sha, "--state resolved to a prefix rather than the full sha"

    it = mbx.declare_intent(NS, "claude", shown, "act", incarnation="pin-m2", client=client)
    assert it.get("ok"), f"--intent refused a printed id: {it.get('reason')!r}"

    # The declaration must land on the FULL sha. Stored under the prefix it would sit under a key
    # nothing else queries, which is indistinguishable from never having declared at all.
    declared = mbx.intents_of(NS, "claude", sha, client=client)
    assert declared, (
        "the intent was filed under the prefix, not the resolved sha -- a declaration under a "
        "name no other reader looks up is a silent drop"
    )


def test_m2_5_the_exact_sha_still_works_unchanged():
    """The regression guard. Prefix resolution must not cost the exact path anything."""
    mbx = _mailbox()
    client = _fake()
    sha = _ingest(mbx, client, sid="1790215960175-0", content="exact still wins")

    r = mbx.resolve_sha(NS, "claude", sha, client=client)
    assert r["how"] == "exact" and r["sha"] == sha

    got = mbx.open(NS, "claude", sha, incarnation="pin-m2", client=client)
    assert got.get("ok") and got["body"] == "exact still wins"

def test_m2_6_a_capped_candidate_list_still_reports_the_TRUE_match_count():
    """The cap is fine. Reporting the cap AS the count is not.

    Written because I broke this twice inside ten minutes while fixing the defect above: the
    resolver caps `candidates` at 20, and two separate wrappers then reported len(candidates) as
    though it were the number of matches. Live, that printed "showing 10 of 20 that matched" when
    35 had actually matched -- a surface misreporting its own completeness, which is the same
    family as the refusal that could not tell absent from short.

    `matched` is the truth; `candidates` is a sample. A caller must be able to tell them apart.
    """
    mbx = _mailbox()
    client = _fake()
    made = [_ingest(mbx, client, sid=f"17902159601{i:02d}-0", content=f"m{i}",
                    sha=f"{'ab'}{i:062x}") for i in range(30)]
    assert len(set(made)) == 30, "fixture did not mint 30 distinct shas"

    r = mbx.resolve_sha(NS, "claude", "ab", client=client)
    assert r["how"] == "ambiguous"
    assert r["matched"] == 30, f"true match count lost: {r.get('matched')!r}"
    assert len(r["candidates"]) <= 20, "the cap is supposed to cap"
    assert r["matched"] > len(r["candidates"]), (
        "this fixture exists precisely to make the cap bite; if it does not, the pin proves nothing"
    )


def test_m2_7_the_state_survives_every_wrapper_between_resolver_and_caller():
    """Three wrappers in this module have each dropped a field from a richer answer they were
    handed. That is the recurring defect, more than the truncation itself: each hop re-derives a
    subset, and the reader ends up with the intersection of whatever everyone thought to forward.
    """
    mbx = _mailbox()
    client = _fake()
    _ingest(mbx, client, sid="1790215960175-0", content="a", sha="ab" + "0" * 62)
    _ingest(mbx, client, sid="1790215960176-0", content="b", sha="ab" + "1" * 62)

    for door, call in (
        ("open", lambda: mbx.open(NS, "claude", "ab", incarnation="pin-m2", client=client)),
        ("state_for", lambda: mbx.state_for(NS, "claude", "ab", client=client)),
        ("declare_intent", lambda: mbx.declare_intent(NS, "claude", "ab", "act",
                                                      incarnation="pin-m2", client=client)),
    ):
        out = call()
        assert out.get("how") == "ambiguous", f"{door} lost `how`: {out!r}"
        assert out.get("matched") == 2, f"{door} lost `matched`: {out!r}"
        assert out.get("candidates"), f"{door} lost `candidates`: {out!r}"
        assert out.get("reason"), f"{door} lost `reason`: {out!r}"
