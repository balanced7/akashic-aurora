"""RED pins: a spawn must end by telling the requester what the seat actually said.

2026-08-24. Daniil ran `!spawn` three times from Discord while the conductor was dead.
Each returned a sprout receipt and then nothing. The gateway's own docstring explains the
silence as a kindness -- *"a seat that keeps breathing says nothing: he does not need a
second receipt for good news, and an unprompted all-clear is how a channel becomes
noise."* That instinct is a real virtue (don't spam his channel) with no sibling wired in
(be legible), and alone it produced this:

    !spawn rill  ->  "the sprout holds"

while the seat's own log read *"Can't comply -- Bash is wedged for the whole session…
Retrying is pointless."* It never armed a watcher and it died. He got the reassuring half.

THE FIX IS NOT A NEW ORGAN. `_spawn_said(log)` already reads the child's ENTIRE output
(bifrost_runner_discord.py:340) and hands it to `spawn_stillborn_reason`, which discards
it unless a fatal marker matches. The information was collected and thrown away. So the
change is to stop discarding it -- per `the_honest_pattern_already_existed_one_module_over`.

NOTE ON A RETIRED FALSIFIER: the registry's F10 said a generic boot chirp must not SETTLE
a spawn expectation. This design has no settlement to spoof -- it relays the seat's words
and lets Daniil judge them -- so F10 is retired by construction rather than satisfied.
Recorded here rather than quietly dropped.

Written before the implementation (M3). RED on arrival.
"""
from __future__ import annotations

from core.comm.discord_inbound import spawn_closing_report

DEADLINE = 600.0


# ------------------------------------------------------- F11: silence is reported
def test_F11_a_seat_that_exits_having_said_nothing_is_REPORTED_not_silenced():
    """The 2026-08-24 defect in its purest form. A clean exit with no output is not good
    news -- it is an absence of news, and the two must not look identical from a phone."""
    r = spawn_closing_report(0, "", elapsed_s=30.0, deadline_s=DEADLINE)
    assert r, "a silent clean exit must produce a report, not silence"
    assert any(k in r.lower() for k in ("said nothing", "no word", "nothing back")), r


def test_a_seats_closing_words_are_relayed_so_he_can_act_on_them():
    r = spawn_closing_report(
        0, "Armed the watcher and drained the work lane. Two blockers filed.",
        elapsed_s=30.0, deadline_s=DEADLINE)
    assert r and "drained the work lane" in r, r


# ------------------------------------------------- F12: a hang is distinguishable
def test_F12_a_working_seat_is_not_nagged_before_its_deadline():
    """The kindness in the original docstring is real and must survive: a seat that is
    genuinely working must not generate chatter."""
    assert spawn_closing_report(None, "", elapsed_s=45.0, deadline_s=DEADLINE) is None


def test_F12b_a_seat_still_running_at_its_deadline_is_reported_with_its_age():
    """`exit_code is None` means 'still running', which is also exactly what a hang looks
    like. At the deadline the ambiguity must be handed to Daniil, not absorbed."""
    r = spawn_closing_report(None, "", elapsed_s=900.0, deadline_s=DEADLINE)
    assert r, "a seat past its deadline with nothing said must be reported"
    assert "15" in r or "900" in r, f"the report must carry the age: {r!r}"


# --------------------------------------------- the real log from the real failure
RILL_LOG = (
    "Can't comply -- Bash is wedged for the whole session (the `claude_trace` hook error "
    "I flagged above), so `bifrost_wake.py` can't be launched. Retrying is pointless; I "
    "already proved this class of failure is total and persistent this session.\n"
    "\n"
    "Stopping here -- `rill` findings and the harness bug are both durably recorded.\n"
    "SessionEnd hook [py agent/harness/hooks/claude_sessionend.py] failed: "
    "can't open file 'E:\\\\AI-Setup\\\\research\\\\in-flight\\\\agent\\\\harness\\\\hooks"
    "\\\\claude_sessionend.py': [Errno 2] No such file or directory\n"
)


def test_the_rill_case_the_message_he_should_have_received():
    """THE regression pin. This is the verbatim shape of spawn-1787596185.log. If this
    goes red again, Daniil is back to reading 'the sprout holds' over a corpse."""
    r = spawn_closing_report(0, RILL_LOG, elapsed_s=30.0, deadline_s=DEADLINE)
    assert r, "the rill spawn must produce a report"
    low = r.lower()
    assert "can't comply" in low and "wedged" in low, \
        f"the seat's actual words must reach him: {r!r}"


def test_harness_noise_does_not_displace_the_seats_own_answer():
    """The rill log ENDS with a SessionEnd hook traceback. A naive 'last line' relay would
    hand him a file-not-found error instead of 'I could not comply'. The seat's words are
    the payload; the harness's are not."""
    r = spawn_closing_report(0, RILL_LOG, elapsed_s=30.0, deadline_s=DEADLINE)
    assert "No such file or directory" not in r, \
        f"harness noise displaced the seat's answer: {r!r}"


def test_a_very_long_transcript_is_clipped_but_keeps_the_ending():
    """Discord caps at 2000 chars and the ENDING is where a seat says what it concluded."""
    body = ("filler line that goes on and on\n" * 400) + "FINAL: the lane is drained.\n"
    r = spawn_closing_report(0, body, elapsed_s=30.0, deadline_s=DEADLINE)
    assert r and "FINAL: the lane is drained." in r, "the closing words must survive clipping"
    assert len(r) <= 1900, f"report must fit Discord's limit, got {len(r)}"


# --------------------------------------------------------- the gateway must wait
def test_the_gateway_keeps_watching_past_the_proof_window():
    """Until 2026-08-24 the watcher thread ended at +25s, so a seat that outlived the
    proof window was never heard from again. The report can only exist if something is
    still listening when the child finally exits."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts"
           / "bifrost_runner_discord.py").read_text(encoding="utf-8")
    assert "spawn_closing_report" in src, \
        "the gateway must relay the seat's closing words"
    assert "AKASHIC_SPAWN_REPORT_DEADLINE" in src, \
        "the post-proof wait must be tunable, not a magic number"
