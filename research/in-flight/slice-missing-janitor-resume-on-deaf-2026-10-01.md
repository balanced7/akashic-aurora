# SLICE — the missing janitor: reconcile expected-up notes vs liveness

STATUS: PROPOSED (not yet on the task ledger — hand to claude/daniil for gating)
AUTHOR: deepseek (Heimdall), from Daniil's claim-vs-fact reframe
DATE: 2026-10-01
TICKET: follow-up slice to the T420 resume-on-deaf ship (2026-10-01)
RELATED NOTES:
  - knowledge note claim-vs-fact-separation-resume-on-deaf-janitor  (the ruling + principle)
  - knowledge note stale-note-landscape-empirical-map-2026-10-01    (the live empirical map)

## ONE-LINE

The code promises the expected-up note is "retracted by stand-down OR the janitor"
(`core/comm/resume_on_deaf.py` header) but ships no janitor. Write the janitor as the
explicit time-gated relationship between the existing CLAIM (the note) and the existing
FACT (liveness): a note whose session has no liveness past the stale horizon is revoked.

## THE DEFECT (precise)

- `declare_expected()` writes `state/wake-expected/{agent}_{sid}.json` at arm.
- `retract_expected()` unlinks it — but is called ONLY on graceful stand-down
  (`agent_cli.py:10301`).
- A seat that dies uncleanly (reboot / kill / crash before stand-down) never retracts, so
  `expected_sessions()` returns it forever.
- `resume_decision()` then hits `stale` (`alive_age_min > RESUME_STALE_MIN = 24h`) and holds
  every listener exit, forever — the hold re-fires against a claim that is permanently false.
  Correct outcome, degenerate work: the "session is gone" fact was never persisted.

## EVIDENCE (empirical, 2026-10-01 ~16:40)

- Exactly ONE expected-up note exists (claude/bb86400e), age 0.82h, alive marker 48.9m,
  armed=False. → This is the S5 DEAF/page case (alive-but-unarmed), NOT the stale leak.
  The stale-note leak has not happened yet (24h horizon un-crossed since ship).
- The REAL observable litter today is a DIFFERENT, bigger family: dozens of temp-dir
  sidecars (`bifrost_wake_<agent>_<sid>.seen/.arming/.rearm/.alive/.pid`) aged 41h..1805h
  with no janitor. Separate cleanup organ; same claim-vs-fact principle governs it too,
  but DO NOT fold it into this slice (scope discipline).
- `torigin2` = test residue (3 dead seats ~262min) from the wake-origin drill, ignorable.

## THE DESIGN (Daniil's reframe, formalized)

Three entities; two exist, one is the missing relationship:

  1. CLAIM (exists)  — `declare_expected()` → the note.   "Who SAYS they should be here?"
  2. FACT  (exists)  — `wake_seat.activity_age_min()/harness_armed()/is_tombstoned()`.
                       "Who is PROVABLY here now?" (measured independently of the note)
  3. RELATIONSHIP (missing) — the reconciler:
                       "note present + no liveness past horizon → revoke the note"

## THE RULE (time-gated, grace-floored)

    revoke(note)  when  now - note.declared_at > RESUME_STALE_MIN
                    AND  NOT is_tombstoned(sid)          # a proper death already handled
                    AND  activity_age_min(sid) is None or > RESUME_STALE_MIN   # no recent breath
                    AND  NOT harness_armed(sid)          # a live listener still holds it

  The grace floor is the horizon itself: younger than RESUME_STALE_MIN the note is UNTOUCHED,
  so a just-born / mid-startup seat (the "robbed before first beat" seam, mirror of
  reaper._orphan_rows' ORPHAN_MIN_AGE_S=240s) is never revoked.

## PROPOSED SHAPE

In `core/comm/resume_on_deaf.py`:

    def janitor_sweep(agent, *, now=None, base=None, dry=False) -> List[Dict]:
        """Revoke stale expected-up notes. Returns [(sid, revoked:bool, reason)].
        Idempotent, loud, never raises. Shares the reaper's death definition so the two
        organs cannot drift: a note is revoked only when the session is provably gone
        (stale + no liveness + not armed + not a recent tombstone)."""
        t = now or time.time()
        out = []
        for rec in expected_sessions(agent, base):
            sid = rec["session_id"]
            declared = float(rec.get("declared_at") or 0)
            if t - declared <= RESUME_STALE_MIN:
                continue                                        # grace: never rob a young note
            from core.comm import wake_seat
            alive = wake_seat.activity_age_min(agent, sid, now=t)
            armed = wake_seat.harness_armed(agent, sid)
            if alive is not None and alive <= RESUME_STALE_MIN:
                continue                                        # still breathing (alive)
            if armed:
                continue                                        # a listener still holds the seat
            retract_expected(agent, sid, base)                 # the reconciling delete
            out.append({"session_id": sid,
                        "revoked": not expected_path(agent, sid, base).exists(),
                        "reason": f"stale {((t-declared)/3600):.0f}h no-liveness"})
        return out

    # Bind: in the daemon's per-tick settle, beside settle_in_flight():
    #   for rec in janitor_sweep(agent):
    #       _loud(f"[resume-janitor] revoked stale expected-up note {rec['session_id'][:8]} ...")

  Reuse `_provably_dead`'s vocabulary: "provably gone" here = (stale AND no-liveness AND
  not-armed). Tombstone is already handled up-stream by resume_decision's tombstoned hold;
  the janitor need only revoke when liveness itself has lapsed.

## PINS (write these as a test; they are the acceptance)

  1. stale-note-retracted: note declared_at = now - 25h, activity marker absent/old, not
     armed → janitor_sweep retracts it (file gone, revoked=True).
  2. just-born-spared: note declared_at = now - 1h (or activity marker fresh) → NOT retracted.
  3. alive-but-deaf-spared: activity_alive_min ≤ RESUME_STALE_MIN but armed=False → NOT
     retracted (this is the live claude/bb86400e case; must never be revoked as "stale").
  4. armed-spared: harness_armed=True regardless of note age → NOT retracted.
  5. idempotent: two sweeps → second returns zero records (nothing left to revoke).

## OUT OF SCOPE (explicitly)

  - The temp-dir `.seen/.arming/.rearm/.alive` sidecar litter (separate janitor, same
    principle — see stale-note-landscape-empirical-map note).
  - The S5 deaf/page path (alive-but-unarmed) — a WAKING problem, not a staling one.
  - Resume/breaker logic. Janitor only REVOKES notes; it never resumes anything.

## RISKS

  - False-revoke if the liveness marker can't be trusted (read error → treat as "no breath"?
    No: fail toward ALIVE like the reaper's K8). Pin 3 is the guard.
  - Clock skew / NTP jump on declared_at → the `t - declared` comparison. Acceptable: the
    horizon is 24h, a second-order skew risk.

## NEXT

  - Daniil approves direction → claude (or deepseek) files this on the task ledger as a
    follow-up slice under T420, with the pins pre-registered.
  - Build is small: one pure function + the settle bind + 5 pins. No new daemon, no new
    credential, read-mostly.
