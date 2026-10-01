#!/usr/bin/env python3
"""Git pre-commit backstop (Concurrency design C4).

Defense-in-depth beneath the per-agent editor hooks (C0/C2): reject a commit that stages
a file a PEER holds an advisory lock on -- regardless of which agent, or which missing
per-agent hook, produced it. Keyed on AKASHIC_AGENT_ID; if unset (e.g. a human commit) it
fails OPEN. A non-zero exit aborts the commit (standard git-hook contract -- here exit 1
is correct; the exit-2 rule was specific to Claude Code PreToolUse, not git hooks).

This stage sees the STAGED FILES. It does not see the commit MESSAGE: git writes the message
file after pre-commit runs, so the private-plane message guard lives in the commit-msg stage
(scripts/githooks/commit_msg.py, defer dd0c36b406).

Install once per clone/worktree:  py scripts/githooks/install_git_hooks.py
"""

import os
import re
import subprocess
import sys


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


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
        return False, (
            "pre-commit BLOCKED: AKASHIC_AGENT_ID is not set, so lock ownership can't be "
            "verified and you staged file(s) a peer may hold a lock on:\n"
            + body
            + "\nSet AKASHIC_AGENT_ID=<your agent id> (e.g. in .claude/settings.json env)."
        )
    return False, (
        "pre-commit BLOCKED: you staged file(s) a peer holds an advisory lock on:\n"
        + body
        + "\nCommit only files you hold, or coordinate via the bus (see docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md C2/C4)."
    )


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
        return 2, (
            "pre-commit: comprehensibility checker MISSING at "
            + checker
            + " -- this gate is NOT running. Wiring defect, not drift: fix the path.\n"
        )
    try:
        r = subprocess.run([sys.executable, checker, "--fast"], capture_output=True, text=True, timeout=60)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception:
        return 0, ""  # guard crashed/slow -> fail open, per the policy in the docstring


# --------------------------------------------------------------------------- ATTRIBUTION GATE


def check_author_matches_seat(agent, author_ident):
    """T411: in a SEAT context, git must record the OPERATOR as both author and committer.

    REWRITTEN IN PLACE rather than deleted, because the rule was RULED ON, not abandoned --
    Daniel, 2026-09-26: "I want my name on it", then "my name shows up in the commiter field and
    author field ... I want to restore the green boxes". The superseded rule is stated here so a
    later reader sees a decision rather than a silent reversal.

    THE OLD RULE WAS "git's author must be that seat" (t384 ruling 2). It fixed a real defect
    measured at b66e6f67 -- a seat's work recorded against the machine owner -- and put the fix in
    the field GitHub renders and counts, so 598 commits ended up displaying an address belonging
    to no account. Attribution now lives on an internal plane
    (state/authorship/seats.jsonl, scripts/authorship_ledger.py) and the git identity fields name
    the person whose project it is.

    THE GUARD'S JOB IS UNCHANGED: make the launcher stamp's ABSENCE loud. Without it the stamp
    could silently stop working -- a launcher spawned without the env, a hand-relaunch that omits
    it -- and commits would drift back to whatever git config happened to be lying around. That is
    not hypothetical: 30 commits in this history were authored by "you@email.com", an unconfigured
    git crediting nobody, for five months.

    Silent outside seat context: a human at their own terminal has no AKASHIC_AGENT_ID and is
    never touched. Fails OPEN when git reports no identity: a guard that bricks every commit is
    worse than the drift it watches for (same policy as the comprehensibility backstop below).
    """
    if not agent:
        return True, ""  # not a seat context -- the human's own commit
    if not author_ident:
        return True, ""  # unreadable -> fail open, never brick the commit
    try:
        sys.path.insert(0, ROOT)
        from core.comm.seat_identity import git_identity_env

        want = git_identity_env(agent)
    except Exception:
        return True, ""  # guard unavailable -> fail open
    if not want:
        return True, ""  # malformed id: nothing to assert against
    expected = f"{want['GIT_AUTHOR_NAME']} <{want['GIT_AUTHOR_EMAIL']}>"
    fix = (
        f"Fix -- stamp the identity in the LAUNCHER that spawned this process, or for a\n"
        f"one-off:\n"
        f"  GIT_AUTHOR_NAME={want['GIT_AUTHOR_NAME']} "
        f"GIT_AUTHOR_EMAIL={want['GIT_AUTHOR_EMAIL']} \\\n"
        f"  GIT_COMMITTER_NAME={want['GIT_COMMITTER_NAME']} "
        f"GIT_COMMITTER_EMAIL={want['GIT_COMMITTER_EMAIL']} git commit ...\n"
        f"(Which seat did the work is recorded in state/authorship/seats.jsonl -- "
        f"`{_pyl()} scripts/authorship_ledger.py who <sha>`.)"
    )
    if not str(author_ident).startswith(expected):
        return False, (
            f"pre-commit BLOCKED: AKASHIC_AGENT_ID is '{agent}' but git will record the AUTHOR "
            f"as\n    {author_ident}\n"
            f"and the author field is what GitHub displays and counts, so this commit would not "
            f"carry the operator's name (T411).\nExpected: {expected}\n" + fix
        )

    # BOTH FIELDS, because GitHub renders and credits the committer too -- a correct author beside
    # a drifted committer still prints a foreign name on the project page and still costs a green
    # box. This half exists because the first pass at T411 put the seat here and that was refused.
    committer_ident = _git_committer_ident()
    if committer_ident and not str(committer_ident).startswith(expected):
        return False, (
            f"pre-commit BLOCKED: the AUTHOR is right but git will record the COMMITTER as\n"
            f"    {committer_ident}\n"
            f"which GitHub also renders and credits, so the commit would still not read as the "
            f"operator's (T411).\nExpected: {expected}\n" + fix
        )
    return True, ""


def _git_author_ident():
    """What git WILL record as author for this commit (env, else config)."""
    return _git_var("GIT_AUTHOR_IDENT")


def _git_committer_ident():
    """What git WILL record as committer. Checked separately from the author because the two can
    be set independently, and T411 needs BOTH to be the operator -- a correct author beside a
    drifted committer is exactly the half-fix that was refused."""
    return _git_var("GIT_COMMITTER_IDENT")


def _git_var(name):
    try:
        r = subprocess.run(["git", "var", name], capture_output=True, text=True, timeout=10, cwd=ROOT)
        return (r.stdout or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- WRITE-EDGE GATES
# Root-cause fix, 2026-08-01, after CI sat red for 30 consecutive days. The repo had five good
# guardrails, four debt allowlists and a suite baseline -- and enforced NONE of it at the moment
# of authorship. The loop from "author a violation" to "learn about it" was commit -> push ->
# 40s of CI -> a red badge, which is too slow to change behaviour, delivered to nobody, and
# self-severing: once the badge sits red a NEW red carries no information. That is how thirty
# days passed unnoticed. These two functions move the gates to the write.

GUARDRAILS = (
    "check_boundaries",
    "check_doc_freshness",
    "check_comprehensibility",
    "check_wiring",
    "check_door_parity",
    "check_kind_policy",
)

# GENERATED, not authored. Committing a derivative and then gating on its freshness is a
# category error: every code commit invalidates it, so the gate fires on whoever commits next
# rather than on whoever caused it. Measured: regenerated twice in one hour, stale both times.
# The commit REGENERATES them; it does not check them.
GENERATORS = (
    "gen_arch_index",
    "gen_physics_sheet",
    "gen_master_map",
    "gen_doors",
    "gen_prior_art_register",
    "gen_ports",
)

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
            r = subprocess.run(
                [sys.executable, "-X", "utf8", path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            out[name] = 0 if r.returncode == 0 else max(1, _count_violations((r.stdout or "") + (r.stderr or "")))
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
        return False, (
            f"baseline at {BASELINE_PATH} is UNREADABLE -- refusing to overwrite it blindly. Fix "
            "or delete it; a corrupt ratchet must not be silently replaced."
        )

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
    payload.setdefault(
        "_why",
        "Write-edge ratchet baseline. Debt may fall or hold; it may "
        "never rise without editing this file in the same commit.",
    )
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    if status == "missing":
        return True, (
            f"no guardrail baseline existed -- created {BASELINE_PATH} adopting today's debt {merged}. "
            "Enforcement starts NOW; it was not running before this."
        )
    return True, (
        f"guardrail(s) with no baseline entry were never being compared: adopted {adopt} at "
        "today's level. They enforce from the next commit on."
    )


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
            return False, (
                f"no readable guardrail baseline at {BASELINE_PATH} ({status}). A MISSING baseline is "
                "UNKNOWN debt, NEVER zero -- this gate used to pass here, which is "
                "how it silently did not run on any fresh clone (T178). Let the hook "
                "materialise one via ensure_baseline()."
            )
    else:
        base = baseline
    now = guardrail_counts() if live is None else live
    if not base:
        return False, (
            "the guardrail baseline is EMPTY, so it ratchets nothing -- which is not "
            "the same as clean. Populate it, or remove the gate deliberately."
        )
    worse = []
    for name, was in base.items():
        is_now = now.get(name, 0)
        if is_now == -1:
            worse.append(f"{name}: the guardrail did not RUN (crash/missing) -- absence is not a pass")
        elif is_now > was:
            worse.append("%s: %d -> %d violation(s)" % (name, was, is_now))
    if worse:
        return False, (
            "guardrail debt INCREASED:\n    "
            + "\n    ".join(worse)
            + "\n  Fix it, or pay something else down first. To accept a deliberate "
            "rise, update state/ci/guardrail_baseline.json in the same commit so the "
            "increase is a RECORDED decision rather than a silent one."
        )
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
            r = subprocess.run(
                [sys.executable, "-X", "utf8", path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            if r.returncode != 0:
                broke.append(g)
        except Exception:
            broke.append(g)
    if stage:
        for doc in ("MODULE_INDEX.md", "PHYSICS.md", "MAP.md", "DOORS.md", "PRIOR_ART.md"):
            rel = "docs/" + doc
            try:
                d = subprocess.run(
                    ["git", "diff", "--quiet", "--", rel], cwd=ROOT, stdin=subprocess.DEVNULL, close_fds=True
                )
                if d.returncode != 0:
                    subprocess.run(
                        ["git", "add", "--", rel],
                        cwd=ROOT,
                        capture_output=True,
                        stdin=subprocess.DEVNULL,
                        close_fds=True,
                    )
                    changed.append(rel)
            except Exception:
                pass
    note = ""
    if changed:
        note += "pre-commit: regenerated and staged {}\n".format(", ".join(changed))
    if broke:
        note += (
            "pre-commit WARNING: generator(s) did not run: {} -- derived docs may be stale "
            "and the comprehensibility gate is not protecting you.\n".format(", ".join(broke))
        )
    return (not broke), note


def main():
    ok, reason = check_staged(_staged_files(), os.getenv("AKASHIC_AGENT_ID"))
    if not ok:
        sys.stderr.write(reason + "\n")
        return 1

    # ATTRIBUTION GATE (t384): in a seat context, git's author must be that seat. Runs
    # early and cheap -- a commit that would land under the wrong name should be refused
    # before any generator regenerates anything on its behalf.
    ok, reason = check_author_matches_seat(os.getenv("AKASHIC_AGENT_ID"), _git_author_ident())
    if not ok:
        sys.stderr.write(reason + "\n")
        return 1

    # PRIVATE-PLANE LEAK GUARD, before anything is regenerated or ratcheted. Daniil's ruling
    # 2026-08-16: personal material never reaches the public repo. This runs FIRST and REFUSES
    # rather than warns, because the failure it prevents is unrecoverable once pushed -- and
    # because the live incident was caught by hand at push, which is the egress position his
    # ingress directive rejects. It fires on the STAGED set only, so it costs nothing on an
    # ordinary commit, and files inside the plane are exempt by design.
    #
    # The COMMIT MESSAGE is guarded too -- a derived description of the work does not inherit
    # its sources' visibility; four messages published artifact names and ids on 2026-08-16
    # while every staged file was clean -- but NOT from here. git writes the message file
    # AFTER this stage runs, so a scan from pre-commit read the PREVIOUS commit's message: a
    # marker-naming message passed its own commit, the clean commit after it was refused, and
    # in a linked worktree (`.git` is a file) the read failed and the scan silently never ran.
    # The commit-msg stage is handed the live message: scripts/githooks/commit_msg.py
    # (defer dd0c36b406).
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from core.trust.private_plane import report as _pp_report

        _pp = _pp_report(_staged_files())
        if _pp["findings"]:
            sys.stderr.write("pre-commit BLOCKED: staged file(s) carry PRIVATE-PLANE identifiers.\n")
            for _f in _pp["findings"][:6]:
                sys.stderr.write(f"  {_f['path']}:{_f['line']} -- marker {_f['marker']!r}\n    {_f['remedy']}\n")
            sys.stderr.write(
                "  Existence metadata is a leak: an id or title alone is "
                "enough, no body required.\n  Emergency bypass: "
                "`git commit --no-verify` -- and if you use it, say so out "
                "loud, because this one does not fail safe.\n"
            )
            return 1
    except Exception:
        pass  # a guard that crashes must not wedge every commit; the checker run reports it

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
        sys.stderr.write("pre-commit BLOCKED: " + _r_msg + "\n  Emergency bypass: `git commit --no-verify`.\n")
        return 1

    rc, out = _comprehensibility_fast()
    if rc == 1:
        sys.stderr.write(
            "pre-commit BLOCKED: comprehensibility drift (a stale repo reference or a "
            "filename case-mismatch):\n"
            + out
            + "\nFix it, or `git commit --no-verify` to bypass in a genuine emergency.\n"
        )
        return 1
    if rc not in (0, 1):
        # Do NOT block -- fail-open on a non-working guard is the standing policy. But never let
        # a dead gate look like a passing one: the whole cost of this defect was its silence.
        sys.stderr.write(
            "pre-commit WARNING: the comprehensibility gate did not run "
            "(rc=%d). Commit allowed; the gate is not protecting you.\n%s" % (rc, out)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
