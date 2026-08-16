#!/usr/bin/env python3
"""Git pre-commit backstop (Concurrency design C4).

Defense-in-depth beneath the per-agent editor hooks (C0/C2): reject a commit that stages
a file a PEER holds an advisory lock on -- regardless of which agent, or which missing
per-agent hook, produced it. Keyed on AKASHIC_AGENT_ID; if unset (e.g. a human commit) it
fails OPEN. A non-zero exit aborts the commit (standard git-hook contract -- here exit 1
is correct; the exit-2 rule was specific to Claude Code PreToolUse, not git hooks).

Install once per clone/worktree:  py scripts/githooks/install_git_hooks.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def _staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def check_staged(files, agent, client=None):
    """Return (ok, reason). ok=False -> abort the commit. With an `agent` id, only a PEER's lock
    blocks (you may commit files you hold). WITHOUT one we can't verify ownership, so we fail
    CLOSED on any staged locked file (teaching the fix) rather than silently allowing -- an unset
    id must not disable the backstop (the RC-01 fail-open). Lock layer unavailable -> allow."""
    try:
        from core.comm.locks import path_conflict
    except Exception:
        return True, ""
    who_me = agent or "(unidentified)"
    conflicts = []
    for f in files:
        try:
            c = path_conflict(f, who_me, client=client)
        except Exception:
            continue
        if c.get("conflict"):
            conflicts.append((f, c.get("held_by")))
    if not conflicts:
        return True, ""
    body = "\n".join(f"  {f} -> locked by {who}" for f, who in conflicts)
    if not agent:
        return False, ("pre-commit BLOCKED: AKASHIC_AGENT_ID is not set, so lock ownership can't be "
                       "verified and you staged file(s) a peer may hold a lock on:\n" + body +
                       "\nSet AKASHIC_AGENT_ID=<your agent id> (e.g. in .claude/settings.json env).")
    return False, ("pre-commit BLOCKED: you staged file(s) a peer holds an advisory lock on:\n" + body +
                   "\nCommit only files you hold, or coordinate via the bus (see docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md C2/C4).")


def _comprehensibility_fast():
    """The drift immune system's FAST checks (stale-ref + filename-case) as a commit-time backstop --
    so drift can't reach the shared repo via `mirror`/`git commit`, not just `ship.py` (property
    UNBYPASSABLE). Fail-OPEN on a guard CRASH (a broken guard must never brick every commit; CI + ship
    run the full guard anyway); real drift fails CLOSED. Emergency bypass: `git commit --no-verify`."""
    # T104 moved this checker into scripts/checkers/ and this invocation was not updated. Python
    # then exited rc=2 ("can't open file") -- not the rc==1 main() blocks on, and not an exception
    # the fail-open except could catch -- so this gate silently no-opped on EVERY commit from the
    # move until 2026-08-01 while reporting green. Fail-open on a guard CRASH is deliberate policy
    # (a broken guard must never brick every commit). Fail-open on a guard that ISN'T THERE is a
    # wiring defect, and it is invisible precisely because absence looks exactly like success.
    checker = os.path.join(ROOT, "scripts", "checkers", "check_comprehensibility.py")
    if not os.path.exists(checker):
        return 2, ("pre-commit: comprehensibility checker MISSING at " + checker +
                   " -- this gate is NOT running. Wiring defect, not drift: fix the path.\n")
    try:
        r = subprocess.run([sys.executable, checker, "--fast"],
                           capture_output=True, text=True, timeout=60)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception:
        return 0, ""   # guard crashed/slow -> fail open, per the policy in the docstring


# --------------------------------------------------------------------------- WRITE-EDGE GATES
# Root-cause fix, 2026-08-01, after CI sat red for 30 consecutive days. The repo had five good
# guardrails, four debt allowlists and a suite baseline -- and enforced NONE of it at the moment
# of authorship. The loop from "author a violation" to "learn about it" was commit -> push ->
# 40s of CI -> a red badge, which is too slow to change behaviour, delivered to nobody, and
# self-severing: once the badge sits red a NEW red carries no information. That is how thirty
# days passed unnoticed. These two functions move the gates to the write.

GUARDRAILS = ("check_boundaries", "check_doc_freshness", "check_comprehensibility",
              "check_wiring", "check_door_parity", "check_kind_policy")

# GENERATED, not authored. Committing a derivative and then gating on its freshness is a
# category error: every code commit invalidates it, so the gate fires on whoever commits next
# rather than on whoever caused it. Measured: regenerated twice in one hour, stale both times.
# The commit REGENERATES them; it does not check them.
GENERATORS = ("gen_arch_index", "gen_physics_sheet", "gen_master_map",
              "gen_doors", "gen_prior_art_register", "gen_ports")

BASELINE_PATH = os.path.join(ROOT, "state", "ci", "guardrail_baseline.json")

_VIOLATION_LINE = re.compile(r"^(?:FAIL:|\s+-\s+\[)")


def _count_violations(text: str) -> int:
    """Count REAL violations, never allowlist entries.

    check_boundaries prints its known-debt ALLOWLIST in the same '- [rule] path' shape as a
    violation; only the lines under the VIOLATIONS heading are real. A naive line match read
    13 where the truth was 1 -- and a baseline built from a wrong count is not a ratchet, it
    is a rubber stamp with room to absorb twelve new violations silently.
    """
    itemised, summaries, in_violations = 0, 0, False
    for ln in (text or "").splitlines():
        stripped = ln.strip()
        if stripped.startswith("VIOLATIONS"):
            in_violations = True
            continue
        if stripped.startswith(("Known debt", "PASS")):
            in_violations = False
            continue
        if stripped.startswith("FAIL:"):
            in_violations = False
            summaries += 1
            continue
        if in_violations and stripped.startswith("- ["):
            itemised += 1
    # Itemised wins when present: check_boundaries prints BOTH an itemised list and a trailing
    # "FAIL: new boundary violation(s)" summary, so adding them double-counts. Every checker
    # emits one form or the other, and a ratchet with slack in it quietly absorbs real debt.
    return itemised or summaries


def guardrail_counts(names=GUARDRAILS) -> dict:
    """{guardrail: violation_count}. A CRASHED guardrail returns -1 and NEVER counts as zero.

    Absence must not look like success -- that is the exact defect recorded above this function
    for the comprehensibility gate, which silently no-opped for weeks while reporting green.
    """
    out = {}
    for name in names:
        path = os.path.join(ROOT, "scripts", "checkers", name + ".py")
        if not os.path.exists(path):
            out[name] = -1
            continue
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", path], capture_output=True,
                               text=True, timeout=120, cwd=ROOT,
                               stdin=subprocess.DEVNULL, close_fds=True)
            out[name] = 0 if r.returncode == 0 else max(
                1, _count_violations((r.stdout or "") + (r.stderr or "")))
        except Exception:
            out[name] = -1
    return out


def _load_baseline():
    """(counts, status) where status is 'present' | 'missing' | 'unreadable' (T178).

    THREE STATES, NOT ONE FALSY. The first version collapsed every failure -- including
    file-not-found -- into {}, and ratchet_ok read {} as "nothing to ratchet against" and
    PASSED. The baseline is gitignored by `state/*` and nothing generated it, so the write-edge
    ratchet silently did not run for anyone who had not hand-built one. Absence looked like
    success, one function below the docstring warning about exactly that.
    """
    if not os.path.exists(BASELINE_PATH):
        return {}, "missing"
    try:
        import json
        with open(BASELINE_PATH, encoding="utf-8") as fh:
            return json.load(fh).get("counts", {}), "present"
    except Exception:
        return {}, "unreadable"


def read_baseline() -> dict:
    """The counts alone (back-compat). Anything that must tell a MISSING baseline from an
    empty one -- which is the whole T178 defect -- uses _load_baseline instead."""
    return _load_baseline()[0]


def ensure_baseline(live=None) -> tuple:
    """(created, note). Resolve absence LOUDLY; never let it read as success.

    Two cases, both of which used to mean "no enforcement and no notice":
      * no baseline file at all -- every fresh clone, and CI
      * a guard in GUARDRAILS with no entry, which ratchet_ok never compared because it
        iterates the BASELINE's keys. That is why check_kind_policy (T177) enforced on
        exactly one workstation: it blocked nobody, and it protected nobody.

    Both are adopted at TODAY's count, because a commit cannot be blamed for debt that
    predates it -- the same reasoning that made the ratchet counted rather than absolute.
    From the next commit on that debt may fall or hold, and may never rise.

    Adoption is the side effect; ratchet_ok stays a predicate.
    """
    import json
    now = guardrail_counts() if live is None else live
    counts, status = _load_baseline()
    if status == "unreadable":
        return False, ("baseline at %s is UNREADABLE -- refusing to overwrite it blindly. Fix "
                       "or delete it; a corrupt ratchet must not be silently replaced."
                       % BASELINE_PATH)

    # A guard that CRASHED reports -1. Adopting that as a debt level would launder a broken
    # guard into an allowance, so it is left out and ratchet_ok fails on it instead.
    adopt = {k: v for k, v in now.items() if k not in counts and v >= 0}
    if status == "present" and not adopt:
        return False, ""

    merged = dict(counts)
    merged.update(adopt)
    payload = {}
    if status == "present":
        try:
            with open(BASELINE_PATH, encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            payload = {}
    payload["counts"] = merged
    payload.setdefault("_why", "Write-edge ratchet baseline. Debt may fall or hold; it may "
                               "never rise without editing this file in the same commit.")
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    if status == "missing":
        return True, ("no guardrail baseline existed -- created %s adopting today's debt %s. "
                      "Enforcement starts NOW; it was not running before this."
                      % (BASELINE_PATH, merged))
    return True, ("guardrail(s) with no baseline entry were never being compared: adopted %s at "
                  "today's level. They enforce from the next commit on." % adopt)


def ratchet_ok(baseline=None, live=None):
    """(ok, message). Debt may fall or hold; it may never RISE.

    An absolute gate over a dirty baseline can never pass, so it teaches everyone to ignore it
    -- and an ignored gate is how a 30-day outage goes unnoticed. A counted baseline makes green
    achievable TODAY at the current debt level while making the debt monotonically
    non-increasing. Pay it down and re-baseline; you can never quietly add to it.
    """
    if baseline is None:
        base, status = _load_baseline()
        if status != "present":
            return False, ("no readable guardrail baseline at %s (%s). A MISSING baseline is "
                           "UNKNOWN debt, NEVER zero -- this gate used to pass here, which is "
                           "how it silently did not run on any fresh clone (T178). Let the hook "
                           "materialise one via ensure_baseline()." % (BASELINE_PATH, status))
    else:
        base = baseline
    now = guardrail_counts() if live is None else live
    if not base:
        return False, ("the guardrail baseline is EMPTY, so it ratchets nothing -- which is not "
                       "the same as clean. Populate it, or remove the gate deliberately.")
    worse = []
    for name, was in base.items():
        is_now = now.get(name, 0)
        if is_now == -1:
            worse.append("%s: the guardrail did not RUN (crash/missing) -- absence is not a pass"
                         % name)
        elif is_now > was:
            worse.append("%s: %d -> %d violation(s)" % (name, was, is_now))
    if worse:
        return False, ("guardrail debt INCREASED:\n    " + "\n    ".join(worse) +
                       "\n  Fix it, or pay something else down first. To accept a deliberate "
                       "rise, update state/ci/guardrail_baseline.json in the same commit so the "
                       "increase is a RECORDED decision rather than a silent one.")
    return True, ""


def regenerate_derived(stage: bool = True):
    """Run the generators and stage their output. Returns (ok, note).

    Fail-OPEN: a generator that breaks must never brick every commit in the repo (the standing
    policy one function above). But a generator that did not RUN is reported, never silent.
    """
    changed, broke = [], []
    for g in GENERATORS:
        path = os.path.join(ROOT, "scripts", "generators", g + ".py")
        if not os.path.exists(path):
            broke.append(g + " (missing)")
            continue
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", path], capture_output=True,
                               text=True, timeout=120, cwd=ROOT,
                               stdin=subprocess.DEVNULL, close_fds=True)
            if r.returncode != 0:
                broke.append(g)
        except Exception:
            broke.append(g)
    if stage:
        for doc in ("MODULE_INDEX.md", "PHYSICS.md", "MAP.md", "DOORS.md", "PRIOR_ART.md"):
            rel = "docs/" + doc
            try:
                d = subprocess.run(["git", "diff", "--quiet", "--", rel], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, close_fds=True)
                if d.returncode != 0:
                    subprocess.run(["git", "add", "--", rel], cwd=ROOT,
                                   capture_output=True, stdin=subprocess.DEVNULL,
                                   close_fds=True)
                    changed.append(rel)
            except Exception:
                pass
    note = ""
    if changed:
        note += "pre-commit: regenerated and staged %s\n" % ", ".join(changed)
    if broke:
        note += ("pre-commit WARNING: generator(s) did not run: %s -- derived docs may be stale "
                 "and the comprehensibility gate is not protecting you.\n" % ", ".join(broke))
    return (not broke), note


def main():
    ok, reason = check_staged(_staged_files(), os.getenv("AKASHIC_AGENT_ID"))
    if not ok:
        sys.stderr.write(reason + "\n")
        return 1

    # PRIVATE-PLANE LEAK GUARD, before anything is regenerated or ratcheted. Daniil's ruling
    # 2026-08-16: personal material never reaches the public repo. This runs FIRST and REFUSES
    # rather than warns, because the failure it prevents is unrecoverable once pushed -- and
    # because the live incident was caught by hand at push, which is the egress position his
    # ingress directive rejects. It fires on the STAGED set only, so it costs nothing on an
    # ordinary commit, and files inside the plane are exempt by design.
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))
        from core.trust.private_plane import report as _pp_report
        _pp = _pp_report(_staged_files())
        if _pp["findings"]:
            sys.stderr.write(
                "pre-commit BLOCKED: staged file(s) carry PRIVATE-PLANE identifiers.\n")
            for _f in _pp["findings"][:6]:
                sys.stderr.write(f"  {_f['path']}:{_f['line']} -- marker "
                                 f"{_f['marker']!r}\n    {_f['remedy']}\n")
            sys.stderr.write("  Existence metadata is a leak: an id or title alone is "
                             "enough, no body required.\n  Emergency bypass: "
                             "`git commit --no-verify` -- and if you use it, say so out "
                             "loud, because this one does not fail safe.\n")
            return 1
    except Exception:
        pass   # a guard that crashes must not wedge every commit; the checker run reports it

    # DERIVED DOCS FIRST: regenerate and stage BEFORE any freshness gate looks at them.
    # Ordering is the whole point -- checking a derivative before refreshing it is what made
    # the comprehensibility gate fire on people who had not caused the staleness.
    _ok_gen, _note = regenerate_derived()
    if _note:
        sys.stderr.write(_note)

    # Resolve an absent baseline (or an unadopted guard) LOUDLY before ratcheting -- otherwise
    # the gate below has nothing to compare against and used to call that a pass (T178).
    _b_created, _b_note = ensure_baseline()
    if _b_note:
        sys.stderr.write("pre-commit: " + _b_note + "\n")

    # THE RATCHET: debt may fall or hold, never rise.
    _r_ok, _r_msg = ratchet_ok()
    if not _r_ok:
        sys.stderr.write("pre-commit BLOCKED: " + _r_msg + "\n  Emergency bypass: "
                         "`git commit --no-verify`.\n")
        return 1

    rc, out = _comprehensibility_fast()
    if rc == 1:
        sys.stderr.write("pre-commit BLOCKED: comprehensibility drift (a stale repo reference or a "
                         "filename case-mismatch):\n" + out +
                         "\nFix it, or `git commit --no-verify` to bypass in a genuine emergency.\n")
        return 1
    if rc not in (0, 1):
        # Do NOT block -- fail-open on a non-working guard is the standing policy. But never let
        # a dead gate look like a passing one: the whole cost of this defect was its silence.
        sys.stderr.write("pre-commit WARNING: the comprehensibility gate did not run "
                         "(rc=%d). Commit allowed; the gate is not protecting you.\n%s" % (rc, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
