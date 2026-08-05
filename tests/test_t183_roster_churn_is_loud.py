"""PRE-REGISTERED ACCEPTANCE (T183) -- per-agent roster that makes churn LOUDER, not quieter.

THE SITUATION. 49 roster rows for 8 logical agents (kimi 15, claude 14), 46 of them DEAD. Not a
bug in the witness: T147 made sid8 pid-derived, so every restart mints a new seat identity, and
the deliberate 24h seatseen rule (F1 -- a seat that EVER beat renders DEAD rather than vanishing,
because silent absence is reserved for seats that never existed) faithfully remembers each one.

MY FIRST DESIGN WAS WRONG AND A FENCED WAVEFRONT KILLED IT. I proposed collapsing the render to
one line per agent with a COUNT of dead incarnations. Two independent positions refuted it:

  * the status-quo defender, with the decisive scenario: an agent crash-looping every four
    minutes shows as one green row with a dead count. "The on-call engineer sees a green dot and
    goes back to bed." The raw view would have shown six deaths clustered in an hour.
  * the reaper's advocate, separately: a single count hides whether deaths occurred in the last
    minute or over days, masking instability and identity churn.

Both are one finding, and it is the invariant this whole arc keeps rediscovering -- collapsing
coerces "this agent is thrashing" into "this agent is live". This time inside my own proposal.

SO: THE COUNT IS NOT THE SIGNAL, THE RATE IS. A per-agent line carries best state, the live
incarnation, total dead, and DEATHS IN THE LAST HOUR, flagging CHURNING above a threshold. That
beats both alternatives: the raw view makes you INFER churn by squinting at 49 last-beat ages;
this states it.

  K1  one line per logical agent, and no agent disappears
  K2  best state wins -- 1 LIVE among 14 DEAD reads LIVE, with the live incarnation named
  K3  deaths inside the window are counted separately from total dead
  K4  CHURNING fires on a crash-loop and stays silent for an old graveyard   (branch 3's case)
  K5  the graveyard size is still reported -- summarising is not hiding
  K6  a fully dead agent still appears; an agent's absence must never be a rendering artifact

Run: py -m pytest tests/test_t183_roster_churn_is_loud.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm.roster import by_agent  # noqa: E402


def _row(agent, state, age, sid8="aaaa1111", seq=0):
    return {"agent": agent, "state": state, "beat_age_s": age, "sid8": sid8,
            "seat": f"{agent}#{sid8}", "phase": "sync", "seq": seq}


def test_k1_one_line_per_agent_and_nobody_vanishes():
    rows = [_row("kimi", "DEAD", 500), _row("kimi", "LIVE", 2), _row("claude", "LIVE", 1),
            _row("deepseek", "DEAD", 9000)]
    got = by_agent(rows)
    assert {g["agent"] for g in got} == {"kimi", "claude", "deepseek"}
    assert len(got) == 3


def test_k2_best_state_wins_and_names_the_live_incarnation():
    rows = [_row("kimi", "DEAD", 5000, sid8="dead0001")] * 14
    rows.append(_row("kimi", "LIVE", 3, sid8="live9999"))
    g = by_agent(rows)[0]
    assert g["state"] == "LIVE", "one living incarnation makes the agent live"
    assert g["live_sid8"] == "live9999", "and the reader must be told WHICH one to address"


def test_k3_recent_deaths_are_counted_apart_from_total_deaths():
    rows = ([_row("kimi", "DEAD", 60)] * 3            # three inside the hour
            + [_row("kimi", "DEAD", 80000)] * 10)     # ten ancient
    g = by_agent(rows, churn_window_s=3600)[0]
    assert g["n_dead"] == 13
    assert g["deaths_in_window"] == 3, "the rate is the signal; the total is only context"


def test_k4_churning_fires_on_a_crash_loop_and_not_on_an_old_graveyard():
    """BRANCH 3'S SCENARIO, PINNED. An agent dying every four minutes must not render as a
    green dot. An agent with an old graveyard and a steady heartbeat must not cry wolf."""
    crash_loop = [_row("canary", "LIVE", 2)] + [_row("canary", "DEAD", 240 * i)
                                                for i in range(1, 7)]
    g = by_agent(crash_loop, churn_window_s=3600, churn_at=3)[0]
    assert g["state"] == "LIVE", "it IS currently up -- that part of the green dot was true"
    assert g["churning"] is True, (
        "six deaths in the last hour is a death spiral; rendering it as one LIVE row is how "
        "the on-call engineer goes back to bed")
    assert g["deaths_in_window"] == 6

    settled = [_row("kimi", "LIVE", 2)] + [_row("kimi", "DEAD", 40000 + 100 * i)
                                           for i in range(1, 15)]
    q = by_agent(settled, churn_window_s=3600, churn_at=3)[0]
    assert q["churning"] is False, (
        "fourteen deaths from yesterday with a healthy beat today is not a spiral -- a flag "
        "that fires on every long-lived agent is a flag nobody reads")


def test_k5_summarising_is_not_hiding():
    rows = [_row("kimi", "LIVE", 2)] + [_row("kimi", "DEAD", 50000)] * 14
    g = by_agent(rows)[0]
    assert g["n_total"] == 15 and g["n_dead"] == 14, (
        "the graveyard size stays visible -- this view compresses the render, not the record")


def test_k6_a_fully_dead_agent_still_appears():
    rows = [_row("ghost", "DEAD", 70000), _row("ghost", "DEAD", 71000)]
    g = by_agent(rows)[0]
    assert g["agent"] == "ghost" and g["state"] == "DEAD"
    assert g["live_sid8"] is None, "no living incarnation must read as None, never as a stale one"
