"""bifrost.wake -- the canonical wake listener for a Bifrost agent (the receive/wake arm of bifrost.api).

Run in the BACKGROUND. It blocks on the agent's inbox + broadcast at ~zero cost and EXITS only when a
real message arrives -- which, in a harness that re-invokes an agent when its background task finishes
(e.g. Claude Code), wakes the otherwise-idle, turn-based agent exactly when there's mail. No polling, no
OS notification, no API key. It keeps waiting through pure trace/noise instead of exiting on it, and
holds a PID seat file while alive so a Stop hook can tell the agent is still wakeable.

THE SEAT IS PER-SESSION (T029 Wave 2, R1/R16): pass --session <id> and the seat file is
bifrost_wake_<agent>_<session>.pid -- concurrent sessions of one agent id each hold their own seat
and never fight over one file (the 2026-07-10 kill loop). Every live session with a seat wakes on
mail (fan-out by design; the ledger + locks absorb twins). Exit codes are operator-facing: ALL
benign endings (wake-worthy mail, quiet deadline, displaced seat, lost seat) exit 0 with a one-line
provenance -- nonzero means a real fault (1 wake error, 2 bus offline). Protocol + fence record:
docs/library/design/20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf.md.

REUSABLE ONBOARDING: any turn-based agent becomes bus-wakeable by arming its wake listener.

  py scripts/bifrost_wake.py --agent claude --session <session-id>   # per-session seat (preferred)
  py scripts/bifrost_wake.py --agent deepseek                        # legacy per-agent seat
"""
import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# T050 Q6: core.comm imports are LAZY (inside functions) so main() can write the wake seat
# within ~200ms of process start -- the heavy import chain was the arm-vs-stop-hook race
# window (five false blocks 2026-07-13/14). The seat path is constructed inline below with
# the exact convention claude_stop.py checks.

# Kinds that keep the watcher waiting: display-only firehose (trace), fold-into-current-task
# facts (steer -- when idle there is no current task; it surfaces at the next natural turn),
# and ledger control-plane markers (resolved / ledger_update, P3/T023: the wake report prints
# the full read-state-first ledger anyway, so a transition marker adds NOTHING wake-worthy --
# it insta-woke armed watchers three times on 2026-07-09 before this line existed; runners
# fold these hint-style instead).
# P0 (T017): 'reply' is deliberately WAKE-WORTHY -- a directed reply arriving while the agent
# idles is usually the answer to something it asked (T016: the eaten reply was a requested
# fenced report). The watcher only DETECTS; nothing here is consumed (see wake_block).
SKIP_KINDS = {"trace", "steer", "resolved", "ledger_update"}

# T045 lane mode (P4): in the work lane the firehose kinds can no longer appear, but the
# informational WORK kinds (note/status) must still not wake an idle seat -- an agent's
# plan-wall budget is spent per wake. The legacy set stays unchanged (strangler discipline).
SKIP_KINDS_LANE = SKIP_KINDS | {"note", "status"}

# T073 Phase 2 (reconciled spec docs/library/report/20260715_t073-wake-communicate-reconciliation-cla_a6fc12.md):
# the ALLOWLIST ratchet inverts the skip sets for the wake decision -- a NEW kind is
# silent-by-default until someone argues it onto this list (the check_door_parity
# pattern applied to kinds). Deviation from the design's six, flagged for verify:
# `nudge` is here because the fidelity ladder's barge-in MUST wake an idle seat.
WAKE_WORTHY_KINDS = frozenset(
    {"request", "handoff", "reply", "blocker", "question", "completion", "nudge"})


def _operator_ids() -> frozenset:
    """Senders whose mail wakes a seat REGARDLESS of kind (the operator override).
    Default covers the UI composer's frm=user stamp and Daniel's name; read
    per-call so drills can dial it (AKASHIC_OPERATOR_IDS, comma-sep, empty=off)."""
    raw = os.environ.get("AKASHIC_OPERATOR_IDS", "user,daniel")
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def _declared_intent_for(m, agent: str):
    """This agent's own declared intent about this exact message, or None.

    T133/M2. The pod design names the wake loop's structural cause precisely: "seen_by -- the
    watcher's vocabulary; today it has none". It has one now. A seat that already declared what it
    would do about a message has, by definition, dealt with it, and re-waking for it is the re-arm
    ritual in its purest form.

    Imported lazily and inside the try on purpose: this module is deliberately importable without
    the core.comm chain (T050 Q6, the fast path), and a wake decision must never depend on the
    mailbox being reachable.
    """
    from core.comm import mailbox
    meta = getattr(m, "meta", None) or {}
    fields = {"frm": str(getattr(m, "frm", "") or ""), "to": str(getattr(m, "to", "") or ""),
              "kind": str(getattr(m, "kind", "") or ""),
              "content": str(getattr(m, "content", "") or ""),
              "ts": str(getattr(m, "ts", "") or "")}
    sha, _basis = mailbox.identity_of(fields, meta if isinstance(meta, dict) else {})
    ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
    st = mailbox.state_for(ns, agent, sha)
    intent = (st or {}).get("intent") or {}
    return str(intent.get("intent") or "") or None


# A DECLARATION THAT MEANS "DONE WITH IT". `defer` is deliberately absent: it means "not yet", and
# treating it as settled would turn a debt the seat explicitly promised to repay into a silent loss.
_SETTLED_INTENTS = frozenset({"act", "decline"})


def _reply_is_settled(m, agent: str) -> bool:
    """Did this message already settle an expectation this seat was waiting on?

    Reads the T117-P8 once-only marker through the module-level predicate in
    core.comm.expectations, so the key shape has one spelling across write, sweep and here.
    Fails open (False -> still wake): missed mail is far worse than a spare re-arm.
    """
    try:
        from core.comm import expectations as _E
        rid = str(getattr(m, "id", "") or (getattr(m, "meta", None) or {}).get("reply_id") or "")
        if not rid:
            return False
        return _E.reply_has_settled(_E._client(), agent, rid)
    except Exception:
        return False


def wake_worthy(m, *, agent: str, incarnation: str = "") -> bool:
    """T073 Phase 1+2: ONE decision for 'does this message wake this seat'.

    Order matters: (1) EXPLICIT incarnation addressing overrides everything --
    meta.to_incarnation naming THIS session wakes it regardless of kind or frm (the
    sender's explicit intent; twin-sync pings ride kind=chat), and naming another
    incarnation never wakes this one. Targets are session-id prefixes (>=8 chars, the
    twin-sync convention). (2) The kind allowlist (ratchet). (3) Unaddressed same-agent
    mail stays skipped -- the safe echo default until T072's identity plumbing lets
    frm_incarnation be trusted for filtering. (4) Broadcast replies are room chatter
    (deepseek red-team F5)."""
    meta = getattr(m, "meta", None) or {}
    target = str(meta.get("to_incarnation") or "")
    if target:
        me = str(incarnation or "")
        return len(target) >= 8 and bool(me) and (me == target or me.startswith(target))
    # THE OPERATOR OUTRANKS THE ALLOWLIST (2026-07-15 live incident: Daniel's
    # "I'm back!" broadcast rode frm=user kind=inform -- the ladder's quiet tier --
    # and every idle claude seat slept through the human while the runner answered.
    # A sender DIMENSION, not a kind, so the ratchet's silent-by-default law for
    # new agent kinds stands untouched). Env-dialed; empty disables.
    if str(getattr(m, "frm", "")) in _operator_ids():
        return True
    kind = str(getattr(m, "kind", ""))
    if kind not in WAKE_WORTHY_KINDS:
        return False
    if str(getattr(m, "frm", "")) == agent:
        return False
    if kind == "reply" and str(getattr(m, "to", "")) == "*":
        return False
    # LAST, and deliberately so: this is the only check that costs a round trip, so it runs only
    # for mail that would otherwise wake the seat. Everything above is free.
    #
    # FAIL OPEN, and the direction matters more here than anywhere else in this slice: a mailbox
    # outage that silenced a seat would trade a bookkeeping fault for missed mail, which is far
    # worse than the re-arm it prevents. Note the operator override returned above, so this can
    # never become a second way to sleep through the human.
    try:
        if str(_declared_intent_for(m, agent) or "") in _SETTLED_INTENTS:
            return False
    except Exception:
        pass
    # W165: the SECOND notion of handled, and the gate knowing only the first is what pinned
    # this watcher fifteen times in one session. A declared intent (above) is how a HUMAN
    # marks mail finished. An ask answer is finished a different way: `ask --peer` polls it
    # NON-CONSUMINGLY by law (T196c, so sibling sessions keep their mail), the poll settles
    # the expectation, and nobody ever declares an intent on it. So `bifrost-sync --consume`
    # truthfully reported "no NEW mail" from its advanced cursor while this detector, which
    # reads the stream rather than the cursor, still saw the same replies forever. A session
    # that fenced three rounds manufactured three of its own blockers.
    #
    # Same fail-open direction as everything above it: unreadable marker -> still wake.
    try:
        if _reply_is_settled(m, agent):
            return False
    except Exception:
        pass
    return True


def _hb_path(agent, session_id=None):
    from core.comm import wake_seat
    return wake_seat.seat_path(agent, session_id)


def _hb_path_fast(agent, session_id=None):
    """Seat path WITHOUT the core.comm import chain (T050 Q6) -- must mirror
    wake_seat.seat_path / claude_stop._seat_path exactly."""
    name = f"bifrost_wake_{agent}_{session_id}.pid" if session_id else f"bifrost_wake_{agent}.pid"
    return os.path.join(tempfile.gettempdir(), name)


def _hb_holder(path):
    """The pid recorded in the seat file, or None (unreadable/missing = seat lost)."""
    try:
        return int(open(path).read().strip())
    except Exception:
        return None


# ---------------------------------------------------------------- T073 Phase 3: long-lived watcher
def default_deadline_s() -> int:
    """R17: 4 hours is the arm-once default (deepseek Design 3); BIFROST_WAKE_DEADLINE_S
    dials it; BIFROST_WAKE_LONGLIVED=0 is the kill-switch back to the legacy 30 minutes."""
    try:
        env = os.getenv("BIFROST_WAKE_DEADLINE_S", "")
        if env:
            return max(60, int(env))
    except Exception:
        pass
    if os.getenv("BIFROST_WAKE_LONGLIVED", "1") == "0":
        return 1800
    return 14400


def rearm_trigger_path(agent: str, session_id: str = "", tmp: str = None) -> str:
    """The deadline self-cycle's note to the waking session (P8). Mirrors seat naming."""
    name = (f"bifrost_wake_{agent}_{session_id}.rearm" if session_id
            else f"bifrost_wake_{agent}.rearm")
    return os.path.join(tmp or tempfile.gettempdir(), name)


def write_rearm_trigger(agent: str, session_id: str = "", tmp: str = None) -> None:
    """R18: written ONLY on a deadline self-cycle -- never on mail exits (the session is
    already waking for work) and never on stand-downs (the seat owner re-arms via the
    stop-hook backstop; a trigger there would double-arm)."""
    try:
        with open(rearm_trigger_path(agent, session_id, tmp), "w", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] deadline self-cycle: re-arm the "
                    f"watcher ONCE -- BIFROST_WAKE_LANE=work py scripts/bifrost_wake.py "
                    f"--agent {agent}" + (f" --session {session_id}" if session_id else "") +
                    " (run_in_background; it stays armed for hours)")
    except Exception:
        pass


def clear_rearm_trigger(agent: str, session_id: str = "", tmp: str = None) -> None:
    """R19: arming IS the requested re-arm -- the trigger clears at arm time."""
    try:
        os.remove(rearm_trigger_path(agent, session_id, tmp))
    except Exception:
        pass


# ------------------------------------------------------------- S0-gamma: wake-detection dedup
# Trigger (note s0-gamma-wake-dedup, 2026-07-21; recovery arc S0 floor): ~6 wake cycles burned
# in one hour on LOGICAL duplicates -- dual-write twins (T039a/T044) and RB-26 redeliveries of
# mail this session had already been woken for but not yet consumed. The watcher is detect-only,
# so nothing ever advanced; every re-arm re-detected the same packet and spent another wake.
# Cure: remember what THIS SESSION was woken for, keyed by the packet's logical identity
# (frm, ts, kind) -- BifrostAPI._dedup_key's exact fields -- in a sidecar file that SURVIVES
# watcher exits (the burn is across arms, not within one). Scope laws:
#   PER-SESSION file (mirrors seat naming): another session still wakes on the same mail --
#     fan-out by design; the ledger + locks absorb twins.
#   DETECT-ONLY stays true: the consume path (bifrost-sync/work_drain) never reads this set;
#     a deduped twin remains fully consumable (RB-26: never drop a work-lane copy).
#   FAIL-OPEN: any sidecar error reads as never-seen -- a broken file can only cost an extra
#     wake, never a missed one.

SEEN_CAP = 1000   # newest-last trim on save; a session outliving 1000 wakes re-earns a twin wake


def seen_path(agent: str, session_id: str = "", tmp: str = None) -> str:
    """The dedup sidecar's path. Mirrors seat naming; removed on tombstone stand-down."""
    name = (f"bifrost_wake_{agent}_{session_id}.seen" if session_id
            else f"bifrost_wake_{agent}.seen")
    return os.path.join(tmp or tempfile.gettempdir(), name)


def logical_key(m) -> str:
    """A packet's dual-write-stable identity, joined for JSON: mirrors BifrostAPI._dedup_key
    (frm, ts, kind) -- twins carry identical env fields but different stream auto-ids."""
    return "|".join((str(getattr(m, "frm", "")), str(getattr(m, "ts", "")),
                     str(getattr(m, "kind", ""))))


def load_seen(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            keys = json.load(f)
        return [k for k in keys if isinstance(k, str)] if isinstance(keys, list) else []
    except Exception:
        return []


def save_seen(path: str, keys: list) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(keys[-SEEN_CAP:], f)
    except Exception:
        pass


def watch(agent: str, total_deadline_s: int, inner_block_ms: int, *,
          api=None, hb_path: str = None, my_pid: int = None,
          session_id: str = "", seen_file: str = None) -> int:
    from core.comm.bifrost_api import BifrostAPI
    api = api if api is not None else BifrostAPI(agent)
    if not api.online_now:
        print("BIFROST_WAKE: bus OFFLINE (Redis unreachable)")
        return 2
    api.online()
    hb = hb_path if hb_path is not None else _hb_path(agent, session_id or None)
    me = my_pid if my_pid is not None else os.getpid()
    lane = f"{agent}/{session_id}" if session_id else agent
    # Seat CREATION belongs to main() (the arm moment); watch() only tracks the seat it was
    # given. Seat-loss is a TRANSITION (held it, lost it) -- an embedder calling watch()
    # without ever seating keeps the old contract and never has files written for it.
    had_seat = _hb_holder(hb) == me
    # S0-gamma: the session's already-woken-for memory (helpers above). Loaded once per arm;
    # persisted only when a wake delivers something NEW (twin-only and quiet exits change nothing).
    sf = seen_file if seen_file is not None else seen_path(agent, session_id)
    seen_keys = load_seen(sf)
    seen_set = set(seen_keys)
    twins = 0
    # KNOWN SEAM (2026-07-24, measured live): wake_block's LOCAL cursor can sit far behind
    # the group cursors, so a fresh session's first arms replay already-handled history one
    # page per wake until the S0-gamma sidecar converges (live: 3 arms, 13+5 historic
    # messages, twins 4->16 -- self-limiting, bounded by SEEN_CAP). An arm-time baseline
    # sweep was tried and REVERTED here: it also swallows genuinely-waiting mail, which the
    # arm-onto-pending contract (test_wake_detect pins) requires to wake. The honest fix is
    # a session-scoped read cursor -- T095 mailbox-over-the-log / T106-A1 own that seam.
    # (T073: the skip-set assignment that lived here is gone -- wake_worthy() is the sole
    # wake gate; SKIP_KINDS/SKIP_KINDS_LANE remain for the lane-mode arm-time pending check.)
    out, seen = [], []
    steers = 0            # skipped steers are counted so the quiet exit says "check at next boot"
    deadline = time.time() + total_deadline_s
    chunk_s = max(1.0, inner_block_ms / 1000.0)
    cycled = False
    while not out:
        # T073 P8: near-deadline SELF-CYCLE -- exit before a block would overshoot the
        # deadline, leaving a re-arm trigger. The exit re-invokes the owning session
        # (harness-tracked task completion); its first cheap action is one re-arm.
        if time.time() + chunk_s >= deadline:
            write_rearm_trigger(agent, session_id)
            cycled = True
            break
        # T086 S1 (watcher leg): a TOMBSTONED session's watcher stands down instead of
        # completing a task into a dead session (the C1-5 resurrection vector). Checked
        # per chunk (cheap file-exists); probe errors read not-tombstoned (fail open).
        if session_id:
            try:
                from core.comm import wake_seat as _ws
                if _ws.is_tombstoned(session_id):
                    try:
                        os.remove(sf)   # S0-gamma P7: dead-by-record -> no orphan sidecar
                    except OSError:
                        pass
                    print(f"BIFROST_WAKE: standing down for {lane} (session tombstoned -- "
                          f"ended by record, T086 S1) -- benign")
                    return 0
            except Exception:
                pass
        # Singleton per SEAT (newest-wins): a later same-session watcher overwrites the seat;
        # the older one must stand down instead of double-reading the bus. Detect-only makes a
        # brief overlap harmless, but two watchers on ONE seat = two wakes for one message.
        # Both endings are BENIGN -> exit 0 (a nonzero exit badges a FAILED task into a live
        # session -- the Wave 2 phantom-failure fix); the printed line is the provenance.
        holder = _hb_holder(hb)
        if holder is not None and holder != me:
            print(f"BIFROST_WAKE: standing down for {lane} (seat now owned by pid {holder}) -- benign")
            return 0
        if holder is None and had_seat:
            # Our seat vanished under us (janitor/migration/manual clean). The old code kept
            # watching INVISIBLY here (the seatless fail-open, battery sec. 6 flaw c); the owning
            # session's stop hook sees no seat and re-arms, so we stand down loudly instead.
            print(f"BIFROST_WAKE: standing down for {lane} (seat lost -- heartbeat file gone) -- benign")
            return 0
        if holder == me:
            had_seat = True              # seat observed OURS at least once -> loss is detectable
        try:
            msgs = api.wake_block(timeout_ms=inner_block_ms)
        except Exception as e:
            print("WAKE_ERROR: " + str(e)); return 1
        for m in msgs:
            frm = str(getattr(m, "frm", "?"))
            kind = str(getattr(m, "kind", "?"))
            seen.append(f"{frm}:{kind}")
            if kind == "steer":
                steers += 1
            # T073: the whole wake decision lives in wake_worthy() -- allowlist ratchet,
            # explicit incarnation addressing, echo + room-chatter skips (pins P1-P11).
            if not wake_worthy(m, agent=agent, incarnation=str(session_id or "")):
                continue
            # S0-gamma: a logical twin of mail this session was ALREADY woken for (dual-write
            # copy or RB-26 redelivery of the still-unconsumed original) spends no wake.
            k = logical_key(m)
            if k in seen_set:
                twins += 1
                continue
            seen_set.add(k)
            seen_keys.append(k)
            out.append({"frm": frm, "kind": kind, "text": str(getattr(m, "content", "") or "")[:2000]})
    if out:
        save_seen(sf, seen_keys)   # S0-gamma: delivered -> remembered (before any print can throw)
    # Read-state-first (Slice C): the governed task ledger prints BEFORE the messages, so a waking
    # agent obeys DONE/NEXT and never acts on a stale backlog message. Fail-open.
    try:
        from core.coord.task_ledger import format_state
        print(format_state(agent=agent, now=time.time()))   # P5: stale proposals labeled at wake
    except Exception:
        pass
    deduped = f"; {twins} twin(s) deduped" if twins else ""
    twin_tag = f" ({twins} twin(s) deduped)" if twins else ""
    if out:
        print(f"BIFROST WAKE -- messages for {agent}{twin_tag} (DETECTED, not consumed -- read them via "
              f"bifrost-sync/inbox):")
        print(json.dumps(out, indent=1))          # ensure_ascii=True -> cp1252-safe stdout on Windows
    elif cycled:
        # C1-6 diagnostic: ELAPSED is the truth; the configured total alone masked a
        # phantom early-cycle (2026-07-16: "after 4.0h" on a minutes-old watcher).
        elapsed_s = time.time() - (deadline - total_deadline_s)
        print(f"BIFROST_WAKE: deadline self-cycle for {lane} after {elapsed_s / 3600.0:.2f}h "
              f"elapsed (configured {total_deadline_s / 3600.0:.1f}h, chunk {chunk_s:.0f}s) -- "
              f"re-arm trigger written; relaunch ONCE (saw: " + ", ".join(seen[-8:]) + deduped + ")")
    else:
        queued = f"; {steers} steer(s) queued for next boot" if steers else ""
        print(f"BIFROST_WAKE: quiet for {agent} (saw: " + ", ".join(seen[-12:]) + queued + deduped + ")")
    return 0


def _migrate_legacy_ghost(agent: str) -> None:
    """K6 one-time self-heal: a pre-Wave-2 name-keyed watcher is invisible to the per-session
    seats (different file) and its code has no seat-lost stand-down -- it would double-wake
    until its deadline. At the first session-scoped arm, retire it: verify identity via one
    process snapshot, kill only a verified watcher, remove the legacy seat, log provenance.
    The single remaining live-process kill in the protocol, bounded to the migration moment."""
    from core.comm import wake_seat
    legacy = wake_seat.seat_path(agent, None)
    if not os.path.exists(legacy):
        return
    pid = wake_seat.read_pid(legacy)
    try:
        if pid is not None and pid != os.getpid():
            snap = wake_seat.process_snapshot()
            if snap is None:
                wake_seat.append_provenance(agent, f"K6 migration deferred: snapshot unavailable "
                                                   f"(legacy seat pid {pid} left in place)")
                return                       # K8 direction: cannot verify -> touch nothing
            if pid in snap and wake_seat.is_watcher(pid, snap):
                wake_seat.taskkill(pid)
                wake_seat.append_provenance(agent, f"K6 migration: killed legacy name-keyed ghost "
                                                   f"watcher pid {pid}")
        os.remove(legacy)
        wake_seat.append_provenance(agent, "K6 migration: legacy seat file removed")
    except Exception:
        pass                                 # best-effort; the janitor sweeps stragglers


def main() -> int:
    ap = argparse.ArgumentParser(description="Block until a Bifrost message wakes this agent.")
    ap.add_argument("--agent", default="claude", help="the agent whose inbox to watch")
    ap.add_argument("--session", default="", help="owning session id -> per-session seat (Wave 2)")
    ap.add_argument("--deadline", type=int, default=None,
                    help="seconds before an idle self-cycle (default: 4h long-lived watcher, "
                         "T073 P3; BIFROST_WAKE_DEADLINE_S dials, BIFROST_WAKE_LONGLIVED=0 "
                         "reverts to the legacy 1800)")
    ap.add_argument("--block", type=int, default=120_000, help="ms per inner blocking read")
    a = ap.parse_args()
    if a.deadline is None:
        a.deadline = default_deadline_s()
    # T050 Q6: SEAT FIRST -- write it before any heavy import/work so the stop hook's check
    # sees an armed listener within ~200ms of launch (the race was the import chain).
    hb = _hb_path_fast(a.agent, a.session or None)
    me = os.getpid()
    try:
        with open(hb, "w") as f:
            f.write(str(me))
    except Exception:
        pass
    if a.session:
        _migrate_legacy_ghost(a.agent)
    clear_rearm_trigger(a.agent, a.session)   # R19: this arm IS the requested re-arm
    try:
        return watch(a.agent, a.deadline, a.block, hb_path=hb, my_pid=me, session_id=a.session)
    finally:
        # Remove the seat only if it is still OURS -- a newer watcher may have taken it
        # (newest-wins singleton); deleting its seat would un-arm a live listener.
        try:
            if _hb_holder(hb) == me:
                os.remove(hb)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
