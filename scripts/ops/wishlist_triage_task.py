#!/usr/bin/env python
"""The wishlist cadence, under the OS scheduler rather than in anyone's memory (2026-10-07).

WHY THIS EXISTS. Daniel, 2026-10-07, verbatim: *"I need to be better about checking those and
getting them built more frequently with a more regular cadance."* The prior seat's answer, which he
accepted and which this file implements, was that **the cadence should ARRIVE rather than be
remembered** -- the same argument mem_watch's installer makes about itself: *"A recorder that has to
be started by hand stops at the first reboot."* A review ritual that depends on someone recalling it
on a busy week is not a ritual, it is a wish about one.

The ledger it serves is `docs/WISHLIST.md`, whose charter says any seat may file the moment friction
is felt, with curation at *"natural gates"*. Filing works -- it is one command. Curation starved,
because filing is frictionless and curation was a doc edit nobody owned. That asymmetry is itself a
house lesson (`zero_is_not_no_silence_is_not_a_verdict`): an unowned manual step next to a
frictionless one always starves.

WHAT IT WILL NOT DO, AND WHY THAT IS THE POINT.

It **never edits the wishlist.** Not one byte. It proposes and nothing more. Three house rules
converge here and they all say the same thing:

  * the charter: *"Never delete -- declined wishes teach too."*
  * `a_competitive_position_claim_is_the_most_perishable_lesson_class`: PROPOSE, NEVER AUTO-RETIRE.
  * `a_verdict_on_a_newborn_must_engage_trajectory_not_position`: wish freely, curate at gates.

And a fourth reason that is just honest engineering: **"is this wish already built?" is not a
question a parser can answer.** It requires reading what the wish MEANS against what the code now
DOES. Anything claiming to have decided that automatically would be an instrument reporting green by
comparing a thing to itself -- the exact defect family that ate 2026-10-07 (seven of them in one
day). So this nominates CANDIDATES for a human look and says plainly which question it answered.

WHAT IT ACTUALLY CHECKS, in priority order -- the buckets ARE the ranking:

  1. FRESH -- filed since the last run. New friction is the most perishable; it is also the cheapest
     to act on, because whoever felt it still remembers why.
  2. LAND MISSING -- the wish's own ``Land:`` field names a repo path that no longer resolves. The
     wish cannot land where it says it should. Either it is misfiled or the target moved; both need
     a human, and neither is visible from the wish alone.
  3. LAND MOVED -- the ``Land:`` path exists AND its last commit is newer than the wish's filing
     date. That is a *candidate* for already-built, never a verdict: code changed near the place the
     wish pointed at. Highest-value bucket and the most easily over-read, so it is labelled as a
     question in the output, not an answer.
  4. STARVING -- oldest still-open. The tail nobody reaches. Included so age alone cannot hide a
     wish forever.

WHAT IT CANNOT SEE, stated here and reprinted in every report it writes, because a surface that does
not name its own bounds lends its silence the authority of a finding:

  * It cannot tell whether a wish is satisfied. See above. Buckets 2 and 3 are questions.
  * ``Land:`` is FREE PROSE. Path extraction is a heuristic (a ``/`` plus a known top-level
    directory or a file extension). A wish whose landing is described in words -- "the stop hook",
    "a substrate probe verb" -- yields no path and is simply not checked by buckets 2 and 3. That
    count is reported as ``no_land_path``, never folded into a clean number.
  * Git checks are BUDGETED. Beyond the budget, wishes go unchecked and are counted as
    ``skipped_over_budget`` -- unchecked, which is not the same as clean.
  * It reads only ``- [ ] W###`` entries, the format the ``wish`` door writes. The file also holds
    older dated prose sections; those are outside this instrument.

Run by hand::

    py scripts\\ops\\wishlist_triage_task.py --dry-run     # print, touch nothing
    py scripts\\ops\\wishlist_triage_task.py               # report + receipt + post to Daniel

Install the weekly task (idempotent, not admin)::

    powershell -ExecutionPolicy Bypass -File scripts\\ops\\install_wishlist_triage_task.ps1
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    # Module scope, once. gen_library.py's lazy per-function inserts left its first caller unable
    # to import at all, and the guard then failed open in silence.
    sys.path.insert(0, str(ROOT))

# A wish line, as the `wish` door writes it:
#   - [ ] W258 (10-07, claude) — body... Trigger: ... Land: ...
WISH_RE = r"^- \[ \] (W\d+) \((\d{2})-(\d{2}), ([^)]+)\)\s*[—-]\s*(.*)$"

# ...and the same line as HUMAN HANDS wrote it before the door existed. W60's attribution field is
# free prose containing an em-dash and an unclosed paren, so the strict form above misses it. That
# miss cost nothing visible and dropped it SILENTLY -- grep found 187 open wishes and the strict
# parser took 186, which is the found-vs-taken tautology (a_report_that_counts_survivors...) in
# miniature. Two stages, and every candidate line is accounted for: strict, fallback, or named as
# unparsed. Never a quiet drop.
WISH_ANY_RE = r"^- \[ \] (W\d+)\b"
WISH_HEAD_RE = r"^- \[ \] (W\d+) \((\d{2})-(\d{2})[,)]?\s*(.*)$"

# A path-shaped token inside free prose. Either a known top dir followed by a slash, or any
# slash-bearing token ending in a real extension. Deliberately conservative: a false path would
# manufacture a LAND MISSING finding, which is worse than declining to check.
TOP_DIRS = ("core/", "scripts/", "docs/", "tests/", "design/", "agent/", "arsenal/",
            "security/", "state/", "research/", "charters/")
PATH_RE = r"(?:(?:%s)[\w./-]+|[\w./-]+\.(?:py|md|json|ps1|js|yml|yaml|frag))" % "|".join(
    d.replace("/", r"/") for d in TOP_DIRS)

GIT_BUDGET = 70          # subprocess calls are the cost here, not tokens
SHORTLIST_PER_BUCKET = 3
DISCORD_LIMIT = 1800     # Discord caps a message at 2000; leave room for the frame


def main() -> int:
    # FIRST, before argparse and before importing anything that prints at import time. Under Task
    # Scheduler there is no console and CPython sets sys.stdout to None, so print() succeeds and
    # discards -- which would silently void the entire report, every week, forever.
    from core.infrastructure.background_stdio import repair_background_stdio
    log = repair_background_stdio("wishlist-triage")

    import argparse
    import json
    import os
    import re
    import subprocess
    import time
    from datetime import datetime, timedelta, timezone

    ap = argparse.ArgumentParser(description="Weekly wishlist triage: propose, never close.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the report; write no receipt and post nothing")
    ap.add_argument("--no-send", action="store_true", help="write the receipt but do not post")
    ap.add_argument("--budget", type=int, default=GIT_BUDGET, help="max git calls")
    args = ap.parse_args()

    started = time.time()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[wishlist-triage] {stamp} starting" + (f" (log: {log})" if log else ""))

    # Env override for the output dir -- the guard the neighbour task lacks, so a test run cannot
    # grow rows in the real state plane.
    out_dir = Path(os.environ.get("AKASHIC_WISHLIST_TRIAGE_DIR",
                                  str(ROOT / "state" / "wishlist" / "triage-receipts")))

    wishlist = ROOT / "docs" / "WISHLIST.md"
    if not wishlist.exists():
        print(f"[wishlist-triage] REFUSING: {wishlist} does not exist")
        return 1

    # ---------------------------------------------------------------- parse
    text = wishlist.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # FOUND: every line that declares itself an open wish, by the loosest possible test. This is
    # the denominator, and it is established BEFORE any parsing can narrow it.
    found = [ln for ln in lines if re.match(WISH_ANY_RE, ln)]

    wishes, unparsed, n_strict, n_fallback = [], [], 0, 0
    for line in found:
        seat, body, mm, dd = "", "", None, None
        m = re.match(WISH_RE, line)
        if m:
            wid, mm, dd, seat, body = m.groups()
            n_strict += 1
        else:
            h = re.match(WISH_HEAD_RE, line)
            if not h:
                unparsed.append(re.match(WISH_ANY_RE, line).group(1))
                continue
            wid, mm, dd, rest = h.groups()
            # The attribution ran into prose. Keep the wish, flag the attribution, lose nothing.
            seat, body = "attribution unparsed", rest
            n_fallback += 1

        # The door writes MM-DD with no year. Assume the most recent occurrence: if that date is in
        # the future, it belongs to last year.
        try:
            filed = datetime(now.year, int(mm), int(dd), tzinfo=timezone.utc)
            if filed > now + timedelta(days=1):
                filed = datetime(now.year - 1, int(mm), int(dd), tzinfo=timezone.utc)
        except ValueError:
            unparsed.append(wid)
            if m:
                n_strict -= 1
            else:
                n_fallback -= 1
            continue

        land = body.rsplit("Land:", 1)[1].strip() if "Land:" in body else ""
        paths = []
        for tok in re.findall(PATH_RE, land):
            tok = tok.rstrip(".,;")
            if "/" in tok or tok.endswith((".py", ".md", ".json", ".ps1")):
                paths.append(tok)
        wishes.append(dict(id=wid, filed=filed, seat=seat.strip(), land=land,
                           paths=sorted(set(paths)), headline=_headline(body)))

    # The arithmetic must CLOSE, and it must say so. An identity is checkable; a pile of counters
    # is not. If this ever fails to balance, the instrument is lying about its own population.
    balanced = len(found) == len(wishes) + len(unparsed)
    print(f"[wishlist-triage] found {len(found)} == taken {len(wishes)} "
          f"({n_strict} strict + {n_fallback} fallback) + unparsed {len(unparsed)}"
          f"{'' if balanced else '  <-- DOES NOT BALANCE'}")
    if unparsed:
        print(f"[wishlist-triage] unparsed: {', '.join(unparsed)}")

    if not wishes:
        print("[wishlist-triage] parsed ZERO open wishes -- the format may have changed. Refusing "
              "to report a clean sheet on a parse failure.")
        return 1

    # --------------------------------------------------- high-water mark
    # FRESH means "since the last run", which requires remembering the last run. Absent a prior
    # receipt, fall back to 7 days and SAY SO, rather than calling every wish fresh.
    prior_hwm, hwm_source = None, "no prior receipt -- defaulting to a 7-day window"
    try:
        prior = sorted(out_dir.glob("*.jsonl"))
        if prior:
            for ln in reversed(prior[-1].read_text(encoding="utf-8").splitlines()):
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if rec.get("at"):
                    prior_hwm = datetime.strptime(rec["at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=timezone.utc)
                    hwm_source = f"previous run at {rec['at']}"
                    break
    except (OSError, ValueError, json.JSONDecodeError) as e:
        hwm_source = f"prior receipt unreadable ({type(e).__name__}) -- 7-day window"
    cutoff = prior_hwm or (now - timedelta(days=7))

    # ---------------------------------------------------------- buckets
    fresh = [w for w in wishes if w["filed"] >= cutoff]
    checkable = [w for w in wishes if w["paths"]]
    no_land_path = len(wishes) - len(checkable)

    land_missing, land_moved, checked, skipped = [], [], 0, 0
    # Newest-first: a recent wish whose site just moved is the most likely already-built.
    for w in sorted(checkable, key=lambda x: x["filed"], reverse=True):
        if checked >= args.budget:
            skipped += 1
            continue
        missing = [p for p in w["paths"] if not (ROOT / p).exists()]
        if missing:
            w["missing"] = missing
            land_missing.append(w)
            checked += 1
            continue
        newest = None
        for p in w["paths"]:
            try:
                r = subprocess.run(["git", "log", "-1", "--format=%cI", "--", p],
                                   cwd=str(ROOT), capture_output=True, text=True,
                                   errors="replace", timeout=20)
                if r.returncode == 0 and r.stdout.strip():
                    ts = datetime.fromisoformat(r.stdout.strip())
                    newest = ts if newest is None or ts > newest else newest
            except (OSError, ValueError, subprocess.SubprocessError):
                continue
        checked += 1
        if newest and newest > w["filed"]:
            w["land_commit"] = newest.strftime("%Y-%m-%d")
            land_moved.append(w)

    shortlisted = {w["id"] for w in (fresh[:SHORTLIST_PER_BUCKET]
                                     + land_missing[:SHORTLIST_PER_BUCKET]
                                     + land_moved[:SHORTLIST_PER_BUCKET])}
    starving = [w for w in sorted(wishes, key=lambda x: x["filed"])
                if w["id"] not in shortlisted][:SHORTLIST_PER_BUCKET]

    # ----------------------------------------------------------- render
    report = _render(now, wishes, fresh, land_missing, land_moved, starving,
                     no_land_path, checked, skipped, hwm_source, SHORTLIST_PER_BUCKET,
                     len(found), unparsed, n_strict, n_fallback)
    print(report)

    receipt = {
        "at": stamp,
        # Not "did it run" -- whether the population balanced. An instrument that cannot account
        # for its own denominator has no business reporting ok.
        "ok": balanced and not unparsed,
        "seconds": round(time.time() - started, 1),
        "open_total": len(wishes),
        "found": len(found),
        "parsed_strict": n_strict,
        "parsed_fallback": n_fallback,
        "unparsed": unparsed,
        "population_balances": balanced,
        # found vs checked vs declined, never one clean number (a_report_that_counts_survivors...)
        "with_land_path": len(checkable),
        "no_land_path": no_land_path,
        "land_paths_checked": checked,
        "skipped_over_budget": skipped,
        "fresh": [w["id"] for w in fresh],
        "land_missing": [w["id"] for w in land_missing],
        "land_moved": [w["id"] for w in land_moved],
        "starving": [w["id"] for w in starving],
        "hwm_source": hwm_source,
        "closed_anything": False,   # structurally; this task holds no write door to the ledger
    }

    if args.dry_run:
        print("[wishlist-triage] --dry-run: no receipt, no post")
        return 0

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / (now.strftime("%Y-%m") + ".jsonl")).open("a", encoding="utf-8").write(
            json.dumps(receipt, ensure_ascii=False) + "\n")
        latest = out_dir.parent / "latest-triage.md"
        latest.write_text(report, encoding="utf-8")
        print(f"[wishlist-triage] receipt -> {out_dir / (now.strftime('%Y-%m') + '.jsonl')}")
        print(f"[wishlist-triage] report  -> {latest}")
    except OSError as e:
        # Never let the bookkeeping fail the job it records.
        print(f"[wishlist-triage] WARN could not write receipt ({type(e).__name__}: {e})")

    if not args.no_send:
        _post(report, ROOT)
    return 0


def _headline(body: str) -> str:
    """The bolded first clause if the wish has one, else its opening words."""
    import re
    m = re.search(r"\*\*(.+?)\*\*", body)
    s = m.group(1) if m else body
    s = s.split("Trigger:")[0].strip()
    return (s[:150] + "...") if len(s) > 150 else s


def _render(now, wishes, fresh, missing, moved, starving, no_land_path, checked, skipped,
            hwm_source, per_bucket, n_found, unparsed, n_strict, n_fallback) -> str:
    """ASCII only, deliberately.

    The first live run rendered every em-dash as a replacement character: this host's console is
    cp1252 and the report also travels to a webhook. The file write is utf-8 and was fine, so the
    mangling was display-only -- which is exactly the kind of defect that survives, because the
    artifact looks correct to whoever checks the artifact. Cheaper to be unambiguous than to chase
    an encoding through three surfaces.
    """
    def block(title, items, note, fmt):
        if not items:
            # Checked-and-empty is a real result and must read differently from never-looked.
            return [f"## {title}", "", "_none this pass (checked, genuinely empty)._", ""]
        out = [f"## {title}  ({len(items)})", "", f"_{note}_", ""]
        for w in items[:per_bucket]:
            out.append(fmt(w))
        if len(items) > per_bucket:
            out.append(f"- ...and {len(items) - per_bucket} more in the same bucket.")
        out.append("")
        return out

    pop = f"**{len(wishes)} wishes open.**"
    if unparsed or n_fallback:
        pop += (f" (population: {n_found} found = {n_strict} strict + {n_fallback} fallback"
                f" + {len(unparsed)} unparsed"
                + (f": {', '.join(unparsed)}" if unparsed else "") + ")")

    L = [f"# Wishlist triage -- {now.strftime('%Y-%m-%d')}", "",
         pop, f"Window: {hwm_source}.", "",
         "This report **proposes**. It has closed nothing and holds no door to do so -- "
         "curate with `py agent_cli.py wish-curate claude --id W### --as fold|keep|decline`.", ""]

    L += block("Fresh -- filed since the last pass", fresh,
               "Most perishable: whoever felt this friction still remembers why.",
               lambda w: f"- **{w['id']}** ({w['seat']}, {w['filed']:%m-%d}) -- {w['headline']}")
    L += block("Land missing -- the wish points at a path that is gone", missing,
               "A QUESTION, not a verdict: misfiled, or the target moved. Either way it cannot "
               "land where it says.",
               lambda w: f"- **{w['id']}** -- {w['headline']}\n"
                         f"    - unresolved: `{'`, `'.join(w['missing'])}`")
    L += block("Possibly already built -- landing site changed after filing", moved,
               "A QUESTION, not a verdict. Code moved near where this pointed; someone has to read "
               "the wish against the code. No parser can decide this.",
               lambda w: f"- **{w['id']}** -- {w['headline']}\n"
                         f"    - `Land:` last committed {w['land_commit']}, "
                         f"wish filed {w['filed']:%Y-%m-%d}")
    L += block("Starving -- oldest open, not surfaced above", starving,
               "Included so age alone cannot hide a wish forever.",
               lambda w: f"- **{w['id']}** ({w['filed']:%Y-%m-%d}) -- {w['headline']}")

    L += ["---", "", "### What this pass could NOT see", "",
          f"- **{no_land_path}** open wishes name no extractable path in `Land:` (it is free "
          "prose), so the two landing buckets never looked at them. Not clean -- unexamined.",
          f"- **{checked}** landing sites checked against git; **{skipped}** skipped over budget. "
          "Skipped means unchecked, not clean.",
          "- Whether any wish is *satisfied* was not assessed and cannot be by this instrument. "
          "Both landing buckets are questions for a reader.",
          "- Only `- [ ] W###` entries are read; older dated prose sections are out of scope.", ""]
    return "\n".join(L)


def _post(report: str, root: Path) -> None:
    """Hand Daniel the short form through the outbound feed, which is a one-way webhook."""
    import subprocess
    lines, body = report.splitlines(), []
    size = 0
    for ln in lines:
        if ln.startswith("### What this pass could NOT see"):
            break
        if size + len(ln) > DISCORD_LIMIT:
            body.append("...(truncated — full report in state/wishlist/latest-triage.md)")
            break
        body.append(ln)
        size += len(ln) + 1
    try:
        r = subprocess.run([sys.executable, "agent_cli.py", "discord", "send",
                            "--text", "\n".join(body), "--kind", "chat"],
                           cwd=str(root), capture_output=True, text=True,
                           errors="replace", timeout=60)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        print(f"[wishlist-triage] post rc={r.returncode} {out[:300]}")
    except (OSError, subprocess.SubprocessError) as e:
        # A delivery failure must be loud. A silent drop on an operator-addressed lane is the
        # defect class discord_seat_lane_silent_drop... was filed against.
        print(f"[wishlist-triage] WARN post failed ({type(e).__name__}: {e})")


if __name__ == "__main__":
    raise SystemExit(main())
