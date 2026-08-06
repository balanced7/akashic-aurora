"""ask -- a synchronous helper call, with no seat behind it (T171).

Daniil, 2026-08-04: "what if you could quickly invoke with a verb a deepseek instance to help you
with something... this might help reduce your cognitive load if you could quickly ask for help
yourself."

THE EVIDENCE THIS IS NEEDED. Across two multi-seat rounds that night, NINE seat-tasks produced TWO
findings that reached the conductor. The rest died to cursor tail-seeding, dedup collapse, budget
exhaustion returning "", and wedges -- and most of the session went on seat plumbing rather than on
getting help. Asking had become more expensive than doing it myself, so I stopped asking.

ASK IS NOT A SEAT, AND THAT IS THE WHOLE DESIGN. A seat carries identity, a singleton lock, cursors,
a mailbox, a heartbeat, a roster row, a wake listener and reaper protection. Every one of those
exists so a peer can be addressed ASYNCHRONOUSLY and survive without the caller. A synchronous ask
needs none of it: it is born, it answers, it dies inside one call. Today every ask has to become a
seat, which is why asking costs what it costs.

DELIBERATELY ABSENT IN v1, each for a reason:
  * TOOLS -- a tool loop is the seat path (budget, hops, wedges). Single turn first; see how it
    actually gets used before adding the machinery that broke the last two rounds.
  * PERSISTENT MEMORY -- persistence is what makes a seat. Memory that must cross invocations
    belongs in the store (learn/note) where the whole fleet can inspect it, not in N private
    shadow histories nobody can audit.
  * WRITE ACCESS -- a helper that can write is a seat with extra steps, and needs all the
    machinery back.

IT RETURNS A BoundaryOutcome, which is the point of having built one. In particular a response cut
off by `finish_reason == "length"` comes back as PARTIALLY -- the T169 lesson generalized: a helper
that ran out of room hands back what it has, marked, instead of looking complete or returning "".
"""
from __future__ import annotations

import concurrent.futures
import os
import re
import time
from pathlib import Path
from typing import Optional

from core.outcome import BoundaryOutcome

DEFAULT_MODEL = os.getenv("AKASHIC_ASK_MODEL", "deepseek-v4-pro")
DEFAULT_MAX_TOKENS = int(os.getenv("AKASHIC_ASK_MAX_TOKENS", "2000"))
BASE_URL = os.getenv("AKASHIC_ASK_BASE_URL", "https://api.deepseek.com")
# T181 fan width. 6 is a DECISION, not a measurement: merge attention at the junction binds
# before generation does, so a fan wider than an integrator can absorb produces merge debt
# rather than progress. Raise it once something downstream is proven able to consume more.
DEFAULT_FAN_WORKERS = int(os.getenv("AKASHIC_ASK_FAN_WORKERS", "6"))
KEY_FILE = Path(__file__).resolve().parents[2] / ".secrets" / "deepseek.key"
DEFAULT_SYSTEM = (
    "You are a helper called synchronously by claude, the conductor of the Akashic Aurora fleet. "
    "You have no memory of previous calls and no tools. Answer the question directly and briefly. "
    "If you cannot answer from what you were given, say exactly what is missing -- a stated gap is "
    "worth more than a confident guess."
)


def _load_key() -> Optional[str]:
    """Env first, then the gitignored key file -- the same order and the same two sources
    scripts/deepseek_chat.py uses. Resolved HERE so core does not have to reach into scripts
    for a credential; runner_lib takes explicit parameters precisely so callers own this.
    """
    v = os.getenv("DEEPSEEK_API_KEY")
    if v and v.strip():
        return v.strip()
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def _usd(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Cost in USD, or None when the model has no sourced rate.

    None is a DESIGNED state, not a failure: runner_token_journal's own comment says an absent
    entry stays unpriced rather than borrowing another vendor's number.
    """
    try:
        # DIRECTION SEAM, filed rather than normalized: the canonical price table lives in
        # scripts/, so this is a core -> scripts import, which is backwards. It resolves
        # through every real door (agent_cli.py and the pins both put the repo root on
        # sys.path), and the except below makes an unresolvable import behave exactly like
        # an unpriced model -- None, never a borrowed rate. The table belongs in core; moving
        # it touches agent_cli and runner_token_journal, so it is a follow-up task and NOT a
        # a path hack here -- which was this module's original boundary violation.
        # (This comment cannot NAME that hack: check_boundaries greps raw text, so writing
        #  the literal token would flag the very line explaining its removal -- K6's
        #  reflexivity bug, one function away. Filed as a follow-up against the checker.)
        from scripts.runner_token_journal import price_of
        rate = price_of(model)
        if not rate:
            return None
        return round(prompt_tokens / 1e6 * float(rate["prompt"])
                     + completion_tokens / 1e6 * float(rate["completion"]), 6)
    except Exception:
        return None


def ask(prompt: str, *, system: Optional[str] = None, model: Optional[str] = None,
        max_tokens: Optional[int] = None, client=None) -> BoundaryOutcome:
    """Ask a helper one question, synchronously. Never raises.

    Returns a BoundaryOutcome whose `detail["answer"]` carries the text. done / partially / failed
    are the three real states, and every one of them can say why.
    """
    if not str(prompt or "").strip():
        return BoundaryOutcome.failed("empty prompt -- nothing to ask")
    model = model or DEFAULT_MODEL
    t0 = time.time()
    try:
        if client is None:
            key = _load_key()
            if not key:
                return BoundaryOutcome.failed(
                    "no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the door is closed, "
                    "which is a configuration state and not a model failure")
            # core -> core. runner_lib is the G4/L0 anti-wedge factory, so ask inherits the
            # per-read timeout AND lands in the T156 wire journal for free.
            from core.comm.runner_lib import make_openai_compat_client
            client = make_openai_compat_client(key, BASE_URL)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system or DEFAULT_SYSTEM},
                      {"role": "user", "content": prompt}],
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        )
    except Exception as e:
        return BoundaryOutcome.caught(e, where=f"ask({model})")

    elapsed = round(time.time() - t0, 2)
    try:
        choice = resp.choices[0]
        answer = (choice.message.content or "").strip()
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
    except Exception as e:
        return BoundaryOutcome.caught(e, where="ask(parse response)")

    detail = {"answer": answer, "model": model, "prompt_tokens": pt,
              "completion_tokens": ct, "usd": _usd(model, pt, ct),
              "elapsed_s": elapsed, "finish_reason": finish}

    if not answer:
        return BoundaryOutcome.failed(
            f"model returned an empty answer (finish_reason={finish})", **detail)
    if finish == "length":
        # The T169 lesson, generalized: out of room is a PARTIAL, never a silent complete.
        return BoundaryOutcome.partially(
            f"answer cut at the {max_tokens or DEFAULT_MAX_TOKENS}-token ceiling "
            f"(finish_reason=length) -- ask again narrower, or raise --max-tokens", **detail)
    return BoundaryOutcome.done(**detail)


# T182 bands, CALIBRATED on known-outcome controls rather than chosen. The first cut used one
# threshold at 0.6 and MISSED the case it was built for: three answers that restated one idea in
# different words scored 0.19 and read as "diverse". Lexical overlap is brutal on paraphrase.
#
#   control                                    score   must read as
#   identical strings                          1.00    collapsed
#   same question x3, paraphrased (REAL case)  0.19    cannot tell -> UNKNOWN
#   five-position wavefront                    0.011   distinct
#   disjoint nonsense                          0.00    distinct
#
# So the honest instrument has THREE outputs, not two. Between the bands it does not know, and
# saying "distinct" there is the same defect this measurement exists to catch: a detector
# coercing "I cannot tell" into "all clear".
COLLAPSE_AT = float(os.getenv("AKASHIC_ASK_COLLAPSE_AT", "0.85"))
DISTINCT_AT = float(os.getenv("AKASHIC_ASK_DISTINCT_AT", "0.05"))
_STOPWORDS = frozenset("""
that this these those with from into onto upon which where when what whom whose
have will would could should must been being were where there their they them then than
your yours ours only also just very much more most some such each other another
about above after again against because before below between during under while
""".split())


def _content_words(text):
    """Words a reader would call the substance: 4+ chars, stopwords dropped."""
    return {w for w in re.findall(r"[a-z0-9']+", str(text or "").lower())
            if len(w) > 3 and w not in _STOPWORDS}


def _agreement(answers):
    """(mean pairwise Jaccard over content words, how many answers were compared).

    None for fewer than two answers, because one answer cannot corroborate itself and 1.0
    there would be a fabricated corroboration -- the exact reading this measurement exists to
    prevent.

    WHAT IT CAN AND CANNOT DO, measured rather than asserted. It separates near-verbatim
    duplication (1.00) from unrelated text (0.00) reliably and for free. It does NOT separate
    "one idea, three phrasings" (0.19 on the real control) from genuinely different answers
    (0.011) with any margin worth gating on. That is why the caller gets a BAND, and why the
    middle band is UNKNOWN rather than a guess: this function is not entitled to a verdict it
    cannot support.
    """
    sets = [s for s in (_content_words(a) for a in answers if a) if s]
    if len(sets) < 2:
        return None, len(sets)
    total = pairs = 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            total += (len(sets[i] & sets[j]) / len(union)) if union else 0.0
            pairs += 1
    return round(total / pairs, 4), len(sets)


def ask_peer(sender, peer, prompt, *, wait_s: float = 120.0, poll_s: float = 2.0,
             within_s: int = 1800, kind: str = "request"):
    """One durable ask to a SEAT, ergonomically synchronous (T196c). Never raises.

    Sol's front door: `ask` and `ask_peer` are one verb with two transports -- the
    stateless helper dies in the call; this one rides the bus with the full T030/T117
    settle machinery underneath, invisibly. Send + arm + poll: expectations.sweep() is
    the ACTOR (transitions), ask_state.state_of() the ORACLE (readout) -- the verb is
    the T196d state machine in a loop, so verb and readout can never disagree.

    THE ASYMMETRY IS THE POINT: wait_s is the short interactive patience; within_s is
    the long durable expectation. When the wait gives up, nothing is abandoned -- the
    record stays armed, redrives fire on their own schedule, and the caller holds a
    handle (`ask --status <id>`) instead of an error. An OPEN ask is a normal state,
    so the timeout path returns PARTIALLY, never failed.

    NON-CONSUMING BY LAW (two-live-seats): the poll reads answers from the stream
    position via the expectations anchor, never advances a lane cursor -- concurrent
    sibling sessions keep their mail; the seat's normal sync consumes later.
    """
    from core.outcome import BoundaryOutcome as _BO   # local alias for clarity only

    if not str(prompt or "").strip():
        return _BO.failed("empty prompt -- nothing to ask")
    sender, peer = str(sender), str(peer)
    t0 = time.time()
    try:
        from core.comm.bus import Bus
        from core.comm.expectations import arm, sweep, _answers_since
        from core.comm.ask_state import state_of
        b = Bus(sender)
        anchor = b.tail().get("inbox", "0")
        mid = b.send(peer, kind, prompt)
        if not mid:
            return _BO.failed(f"send to {peer} failed -- bus offline or refused the message")
        armed = arm(sender, mid, peer, kind, prompt, int(within_s))
    except Exception as e:
        return _BO.caught(e, where="ask_peer(send+arm)")

    deadline = t0 + max(0.0, float(wait_s))
    st = None
    while True:
        try:
            sweep(sender)                    # actor: clear answered / redrive / kill
            st = state_of(sender, mid)       # oracle: the honest readout
        except Exception as e:
            return _BO.caught(e, where="ask_peer(poll)", ask_id=str(mid))
        if st["terminal"] or time.time() >= deadline:
            break
        time.sleep(max(0.05, float(poll_s)))

    detail = {
        "ask_id": str(mid), "peer": peer, "state": st["state"],
        "elapsed_s": round(time.time() - t0, 2), "armed": bool(armed),
        "redrives": st.get("redrives"),
        "how_to_check": f"py agent_cli.py ask --status {mid} --as {sender}",
    }
    if st["state"] == "CLOSED.ANSWERED":
        answer = None
        try:
            for m in _answers_since(sender, anchor):     # anchored, non-consuming
                if getattr(m, "frm", None) == peer:
                    answer = getattr(m, "content", None) # newest from the peer wins
        except Exception:
            answer = None
        if answer is None:
            answer = ("(answer settled but its body is outside the stream window -- "
                      "follow answer_id)")
        return _BO.done(answer=answer, answer_id=st.get("answer_id"), **detail)
    if st["state"] == "CLOSED.ECHO":
        return _BO.done(answer=None, settle=(st.get("evidence") or {}).get("settle"),
                        **detail)
    if st["state"] == "CLOSED.DEAD":
        return _BO.failed(
            f"{peer} never answered {mid} -- redrives exhausted (the durable "
            f"expectation_dead event has the record)", **detail)
    if st["state"] == "UNKNOWN":
        return _BO.partially(
            "the record vanished mid-wait (evidence lost or trimmed) -- re-ask; the "
            "old transaction is unresolvable", **detail)
    return _BO.partially(
        f"not settled within {wait_s}s -- the ask stays armed, redrives continue on "
        f"their own schedule; check later with ask --status", **detail)


def _fan_client(client):
    """ONE client for the whole fan, or a named configuration failure for the whole fan.

    Shared deliberately: the SDK's httpx client is thread-safe and pools connections, so N
    branches cost N requests rather than N clients. A missing key is ONE configuration state,
    not N model failures, and saying so is cheaper to act on than N identical branch errors.
    """
    if client is not None:
        return client, None
    key = _load_key()
    if not key:
        return None, ("no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the door is closed "
                      "for the WHOLE fan; that is a configuration state, not N model failures")
    from core.comm.runner_lib import make_openai_compat_client
    return make_openai_compat_client(key, BASE_URL), None


def ask_many(prompts, *, system: Optional[str] = None, model: Optional[str] = None,
             max_tokens: Optional[int] = None, client=None,
             max_workers: Optional[int] = None) -> BoundaryOutcome:
    """Ask N helpers at once. Still no seat behind any of them (T181). Never raises.

    THE PRIMITIVE THE FLEET PATTERNS NEED. Daniil's design, expanded by Sol at his ask: the
    corpus is a graph at rest that becomes an objective-rooted TREE while working, traversed by
    dispersal pattern -- breadth wavefront (disjoint sibling leaves, one integrator), fenced
    triangle (two blind investigators, one reconciler), branch-and-bound (cheap hypotheses, one
    adjudicator), cross-cutting transect (one invariant across every branch). All of them need N
    concurrent LEAVES. None of them needs a seat.

    WHY NOT N SEATS. A seat carries identity, a singleton lock, cursors, a mailbox, a heartbeat,
    a roster row and reaper protection -- so N seats cost N of each, and the measured result on
    this repo was nine seat-tasks returning two findings. N asks cost N HTTP requests.

    THE AGGREGATE IS THREE-STATE AND THAT IS THE POINT. A binary fan verdict discards the
    partial result, which is exactly how "nine tasks, two findings" reads as failure instead of
    as two findings. done only when every branch landed; PARTIALLY with counts when some did;
    failed with counts when none did. Per-branch verdicts live in detail["branches"], in INPUT
    order regardless of completion order, because attribution depends on order.

    Branches are dicts rather than BoundaryOutcomes so the whole aggregate stays JSON-
    serialisable for the CLI door; the aggregate itself keeps the one vocabulary.
    """
    prompts = [str(p) for p in (prompts or [])]
    if not prompts:
        return BoundaryOutcome.failed(
            "empty fan -- no prompts to ask. Asking nothing is not the same as asking and "
            "hearing nothing back.")

    model = model or DEFAULT_MODEL
    workers = max(1, min(int(max_workers or DEFAULT_FAN_WORKERS), len(prompts)))
    client, why = _fan_client(client)
    if client is None:
        return BoundaryOutcome.failed(why, n=len(prompts), n_ok=0, branches=[])

    t0 = time.time()
    results = [None] * len(prompts)

    def _one(i):
        try:
            return ask(prompts[i], system=system, model=model,
                       max_tokens=max_tokens, client=client)
        except Exception as e:      # ask() does not raise Exception; never lose a slot anyway
            return BoundaryOutcome.caught(e, where=f"ask_many(branch {i})")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, i): i for i in range(len(prompts))}
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except BaseException as e:                              # noqa: BLE001
                results[i] = BoundaryOutcome.caught(
                    e if isinstance(e, Exception) else RuntimeError(repr(e)),
                    where=f"ask_many(future {i})")

    branches, total_usd, priced_all = [], 0.0, True
    n_ok = n_partial = 0
    for i, o in enumerate(results):
        d = o.detail or {}
        usd = d.get("usd")
        if usd is None:
            priced_all = False
        else:
            total_usd += float(usd)
        n_ok += 1 if o.ok else 0
        n_partial += 1 if o.partial else 0
        branches.append({
            "i": i, "prompt": prompts[i][:300], "ok": o.ok, "partial": o.partial,
            "why": o.why, "answer": d.get("answer"), "usd": usd,
            "prompt_tokens": d.get("prompt_tokens"), "completion_tokens": d.get("completion_tokens"),
            "elapsed_s": d.get("elapsed_s"), "model": d.get("model"),
        })

    # T182: does this fan carry N findings, or one finding N times? Measured over the branches
    # that LANDED -- an outage is not a dissenting voice, and counting it as one would
    # manufacture diversity out of a failure.
    agreement, n_compared = _agreement([b["answer"] for b in branches if b["ok"]])
    if agreement is None:
        diversity = None                       # one answer cannot agree or disagree with itself
    elif agreement >= COLLAPSE_AT:
        diversity = "collapsed"                # near-verbatim: one answer billed N times
    elif agreement <= DISTINCT_AT:
        diversity = "distinct"                 # genuinely different answers
    else:
        diversity = "unknown"                  # lexical overlap cannot tell paraphrase apart
    collapsed = diversity == "collapsed"

    n = len(prompts)
    detail = {
        "n": n, "n_ok": n_ok, "n_partial": n_partial, "branches": branches,
        "answers": [b["answer"] for b in branches],
        "lexical_agreement": agreement, "n_compared": n_compared,
        "diversity": diversity, "collapsed": collapsed,
        # None, never a guess: one unpriced branch makes the fan total unknowable, and a
        # partial sum presented as a total is the same lie one layer up.
        "usd": round(total_usd, 6) if priced_all else None,
        "elapsed_s": round(time.time() - t0, 2), "model": model, "workers": workers,
    }

    if n_ok == 0:
        return BoundaryOutcome.failed(
            f"the whole fan failed: {n_ok} of {n} branches landed. First reason: "
            f"{branches[0]['why'] or 'unreported'}", **detail)
    if n_ok < n or n_partial:
        lost = [b["i"] for b in branches if not b["ok"]]
        cut = [b["i"] for b in branches if b["partial"]]
        bits = [f"{n_ok} of {n} branches landed"]
        if lost:
            bits.append(f"failed: {lost}")
        if cut:
            bits.append(f"truncated: {cut}")
        return BoundaryOutcome.partially(" | ".join(bits), **detail)
    return BoundaryOutcome.done(**detail)
