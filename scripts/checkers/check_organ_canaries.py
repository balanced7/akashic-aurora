"""check_organ_canaries -- does each organ still answer a question whose answer we know?

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS (2026-09-27). In one session this house found six broken organs, and every single
one surfaced because somebody happened to point something at it:

  * 877 of 1,436 cited commit SHAs resolved on one machine only -- unnoticed for 65 days (T410).
  * The Eye's connectome held ZERO edges, and five of its eight edge kinds have no writer at all.
  * 38 task rows aged 35-79 days were rendered to every seat's boot as the standing NEXT queue,
    with no age, because state_view() computes staleness only for PROPOSED.
  * 51 done rows lost their commit receipt to a history rewrite run hours earlier in the same
    session, by the seat that wrote this file.
  * `lookback`, the dedicated why/what organ, returned nothing above its relevance floor for two
    control questions whose answers are richly documented here (T412).
  * `events --kind X` silently does not filter, so every census run through it was diluted (T413).

The house has six pre-commit guardrails and ALL SIX read code or docs: check_boundaries,
check_doc_freshness, check_comprehensibility, check_wiring, check_door_parity, check_kind_policy.
Not one asks whether an organ still ANSWERS. A verb can pass every import-graph and door-parity
check while returning nothing, forever, and nothing notices -- which is exactly what `lookback`
did.

THE TECHNIQUE, taken from Sergey Nikitenko's Mnemosyne notebook (2026-09-27) with attribution.
He proved a capability was live by showing a REFUSAL REASON change -- `deny: unknown target`
instead of `deny: fabricated or unverifiable evidence` -- so the evidence had passed the
authenticity gate and only stopped for a missing target. A positive control on a negative result,
with no fixture to contaminate it. The generalisation: an organ is alive when it answers a question
you already know the answer to. That question is its canary.

WHY NOT A SEVENTH GUARDRAIL POINTED AT CODE. This one is pointed at the RUNNING SYSTEM, which is
the plane none of the other six can see. It is also deliberately cheap: a canary is one call whose
expected answer is already known, so the whole suite is seconds, not a test run.

EVERY CANARY CARRIES A RETIREMENT RULE. The house's own law: a capability without a retirement rule
is a debt with a nice interface, and every organ has a birth and no death. So a canary without a
`retire_when` is refused by this checker's own self-test -- see test_canaries_declare_their_own
death below. A canary that can never be retired becomes the next thing nobody prunes.

THIS CHECKER STARTS RED, ON PURPOSE. Three of its canaries fail today against real, filed defects
(T412, T413, and the empty connectome). RED-first is the house method: a checker that starts green
has not yet demonstrated it can see anything.

REPORT BY DEFAULT. `--gate` opts into failing the build.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PY = sys.executable


def run(*args, timeout=180):
    """A verb call. Returns (rc, combined output). Never raises -- a crashed organ is a finding."""
    try:
        p = subprocess.run([PY, *args], cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    except Exception as exc:
        return -2, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------- the canaries
# Each returns (verdict, detail). Verdict is one of:
#   "alive"      the organ answered, and the answer was the one we know
#   "dead"       the organ ran and did not answer -- the defect class this file exists for
#   "unchecked"  the canary itself could not run. NOT a pass. ZERO IS NOT NO.

ALIVE, DEAD, UNCHECKED = "alive", "dead", "unchecked"


def canary_lookback():
    """`lookback` must answer a why/what question whose answer is documented here.

    Measured 2026-09-27 (T412): lookback returned "nothing above the relevance floor" for TWO
    control questions whose answers are richly documented -- one written that same day, one months
    old -- so the failure is not freshness. Its layers are docs, research, notes, promoted,
    chapters and git.

    The control below: the drill-receipt doctrine is one of this house's most heavily recorded
    rules -- it appears in lessons, in docs, in state/drills/ receipts and in commit messages. If
    the rationale organ cannot reach THAT, it cannot reach anything.
    """
    q = "why does a recovery path need a drill receipt"
    rc, out = run("agent_cli.py", "lookback", q, "--layers", "2", "--per-layer", "4")
    if rc < 0:
        return UNCHECKED, f"lookback did not run: {out[:160]}"
    if "nothing above the relevance floor" in out.lower():
        return DEAD, ("returned nothing for a question whose answer is in lessons, docs, "
                      "state/drills/ AND commit messages (T412)")
    if not out.strip():
        return DEAD, "returned no output at all"
    return ALIVE, f"answered ({len(out.splitlines())} lines)"


def canary_events_kind_filter():
    """`events --kind X` must return only events of kind X.

    Measured 2026-09-26: `--kind file_edit` returned `learning` and `boot` rows. A filter that
    does not filter is worse than a missing one, because every census run through it looks valid.
    """
    want = "boot"
    rc, out = run("agent_cli.py", "events", "--kind", want, "--limit", "25", "--json")
    if rc < 0:
        return UNCHECKED, f"events did not run: {out[:160]}"
    try:
        payload = json.loads(out[out.index("["):out.rindex("]") + 1])
    except Exception:
        try:
            payload = json.loads(out)
        except Exception:
            return UNCHECKED, "could not parse the JSON envelope"
    rows = payload if isinstance(payload, list) else (payload.get("events") or [])
    if not rows:
        return UNCHECKED, "no events returned; nothing to judge"
    wrong = [r.get("kind") for r in rows if r.get("kind") != want]
    if wrong:
        seen = sorted(set(k for k in wrong if k))[:6]
        return DEAD, (f"--kind {want} returned {len(wrong)} of {len(rows)} rows of other kinds "
                      f"({', '.join(seen)}) -- the filter does not filter (T413)")
    return ALIVE, f"all {len(rows)} rows are kind={want}"


def canary_eye_freq():
    """`eye freq` must return a mechanical verdict for a phrase family whose answer we know.

    THE EYE'S load-bearing axis (T336): `eye freq` is the only door that returns a verdict on the
    OPERATOR'S OWN AXIS -- unheard / mentioned-once / recurring / standing-directive. A grep cannot
    produce it; it is a measurement, not a search. This canary asks a phrase family that IS
    documented here as recurring (`fan out`, from core/eye/directives.py's own founding wound: the
    operator said "remember to fan out so you dont get bogged down in mechanics" twice, lost it,
    and the Eye surfaced it only by accident). If the frequency organ cannot reach THAT, it cannot
    reach anything.

    Verdict is the canary's heartbeat: a run that exits 0 but prints no verdict line is DEAD (the
    organ ran and said nothing -- the exact class this whole checker exists to catch).
    """
    rc, out = run("agent_cli.py", "eye", "freq", "fan out", "fanout", "fan-out")
    if rc < 0:
        return UNCHECKED, f"eye freq did not run: {out[:160]}"
    if not out.strip():
        return DEAD, "eye freq returned no output at all"
    # A verdict line is the mechanical answer; its absence is silence wearing a zero exit code.
    verdicts = ("unheard", "mentioned-once", "recurring", "standing-directive")
    low = out.lower()
    if not any(v in low for v in verdicts):
        return DEAD, ("eye freq ran but returned no mechanical verdict for a known recurring "
                      "phrase family -- the measurement axis is silent")
    return ALIVE, f"eye freq answered with a verdict ({len(out.splitlines())} lines)"


def canary_find():
    """`find` must return, BY NAME, a file we know exists -- and name WHICH engine answered.

    This is the T278/T336 class one layer down from eye: `find` (the Search Everything verb) is
    the ONLY read verb not scoped to the project root. A file that landed outside the root is
    invisible to read_file/search_files/list_directory, so `find` is the locator of last resort.
    A canary that only checks "did it exit 0" would pass a find that returns a bare zero (the
    false-absence this module exists to prevent). So: ask for `agent_cli.py`, a file that MUST
    exist in every checkout, and require it to come back WITH an engine label.

    Also doubles as the platform smoke: on Windows it reports 'everything' (or 'walk' if
    Everything is absent, which is honest-but-degraded); on Linux 'fd'/'locate'/'' -- and the
    canary treats a named engine as alive regardless of which one, but DEAD if it returns no
    engine at all (a find that answers without saying how is a find that cannot be trusted).
    """
    rc, out = run("agent_cli.py", "find", "agent_cli.py", "--limit", "5")
    if rc < 0:
        return UNCHECKED, f"find did not run: {out[:160]}"
    if "agent_cli.py" not in out:
        return DEAD, ("find returned results but none was agent_cli.py -- a file that exists in "
                      "every checkout -- so the locator is lying or blind")
    # The engine label proves the answer knows its own authority (everything vs walk vs fd/locate).
    low = out.lower()
    if not any(e in low for e in ("everything", "walk", "[engine", "engine:", "fd", "locate")):
        return DEAD, "find returned agent_cli.py but named NO engine -- an answer with no authority"
    return ALIVE, f"find located agent_cli.py and named its engine ({len(out.splitlines())} lines)"


def canary_connectome_has_edges():
    """The Eye's connectome must hold edges, or say plainly that it is unbuilt.

    Measured 2026-09-26: the `edges` table held 0 rows while the same database held 48,702 events
    and 379,953 chain rows, so `eye trace` hit its empty-connectome guard and exited 2. Five of
    the eight declared edge kinds have no writer anywhere in the repo.
    """
    db = ROOT / "state" / "eye" / "eye.db"
    if not db.is_file():
        return UNCHECKED, "state/eye/eye.db is absent"
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=10)
        try:
            edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            events = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        finally:
            con.close()
    except Exception as exc:
        return UNCHECKED, f"could not read the index: {type(exc).__name__}: {exc}"
    if events and not edges:
        return DEAD, (f"0 edges beside {events:,} indexed events -- the typed connectome is "
                      f"empty, so `eye trace` cannot walk and 5 of its 8 edge kinds have no "
                      f"writer at all")
    if not events:
        return UNCHECKED, "the index holds no events; a canary here would measure nothing"
    return ALIVE, f"{edges:,} edges over {events:,} events"


def canary_recall_fires_on_seed():
    """recall-at must surface, AT THE TOOL-CALL SEAM (core.recall.at_action.recall_at), a
    lesson whose id is named in the SEED MANIFEST -- otherwise "install → recall works out of
    the gate" is asserted, never proven.

    This is a positive control on a negative result (Nikitenko, Mnemosyne): we already know the
    seeded lesson exists, so recall either surfaces it or is broken. It drives the REAL
    recall_at() function (the same one the PreToolUse hook and the CLI both call), not the
    knowledge_recall search verb, so it proves the injection path, not the lookup path.

    Provenance comes from the MANIFEST JOIN, not a stamp on the lesson (operator decision Q2,
    2026-10-27): the seed manifest records WHICH ids were carried. If the manifest carries only
    counts and no id list, this canary is UNCHECKED — it cannot name a lesson it did not seed,
    and ZERO IS NOT NO.

    retire_when defined separately in the registry (see CANARIES).
    """
    try:
        from core.recall.at_action import recall_at
        from core.comm.bus import get_bus
    except Exception as exc:
        return UNCHECKED, f"recall_at / bus import failed: {type(exc).__name__}: {exc}"

    # 1. The seed manifest names the carried lesson ids. Absent/unreadable -> can't claim.
    try:
        client = get_bus("organ-canary")._client
        if client is None:
            return UNCHECKED, "no store client -- cannot read the seed manifest"
        from core.world_seed import read_manifest
        manifest = read_manifest(client)
    except Exception as exc:
        return UNCHECKED, f"seed manifest unreadable: {type(exc).__name__}: {exc}"
    if not manifest:
        return UNCHECKED, ("no world:seed:manifest -- without a record of what was seeded, "
                           "recall firing on a lesson cannot be attributed to the seed")
    inv = manifest.get("lesson_inventory") or []
    if not inv:
        return UNCHECKED, ("the seed manifest carries no lesson_inventory -- it cannot name a "
                           "seeded lesson to prove. (lesson_inventory is the [{id,sha256,"
                           "generation}...] list the canary joins against; see spec (a.5).)")
    seeded_ids = [e.get("id") for e in inv if isinstance(e, dict) and e.get("id")]

    # 2. Pick ONE seeded lesson and draw a target from its own text, so the query is grounded
    #    in a lesson we KNOW exists, and recall must clear the floor against it.
    from core.learning.learning_store import get_learning_store
    try:
        ls = get_learning_store()
    except Exception as exc:
        return UNCHECKED, f"learning store unavailable: {type(exc).__name__}: {exc}"
    proven = None
    for sid in seeded_ids:
        rec = ls._load_experiment(str(sid).removeprefix("learn:experiment:"))
        if not rec:
            continue
        rec_text = " ".join(str(rec.get(k) or "") for k in
                            ("recommendation", "what_tried", "actual", "root_cause"))
        if rec_text.strip():
            proven = (sid, rec_text)
            break
    if proven is None:
        return UNCHECKED, f"{len(seeded_ids)} seeded ids named but none load a record with text"

    sid, text = proven
    # Inject the learning_store EXPLICITLY: recall_at(learning_store=None) reads a TTL disk
    # cache at %TEMP%/akashic_recall/lesson_items.json that is NOT world-scoped, so a beta
    # self-check would rank PROD's cached lessons (or a stale mix) and falsely report DEAD.
    # Passing the store bypasses the cache (documented: "an INJECTED store bypasses the cache")
    # and reads the LIVE seeded store the manifest names. (2026-10-29, found live while seeding
    # prod->beta: the canary reported the seeded lesson absent even though a direct read found it.)
    r = recall_at(command=text[:400], limit=5, count_surface=False,
                  learning_store=ls)
    if r.get("error"):
        return UNCHECKED, f"recall_at raised: {r.get('error')}: {r.get('error_detail','')}"
    sources = [str(l.get("source") or "") for l in r.get("lessons", [])]
    wanted = str(sid)
    if not wanted.startswith("learn:experiment:"):
        wanted = f"learn:experiment:{sid}"
    if wanted in sources:
        # Integrity check (spec a.5): if the manifest recorded a content hash for this lesson,
        # verify the CURRENT record's content matches -- recall firing on a drifted/edited copy
        # is a different fact from firing on our shipped bytes.
        want_hash = next((e.get("sha256") for e in inv
                          if isinstance(e, dict) and e.get("id") == wanted), None)
        if want_hash:
            import hashlib
            from core.world_seed import _content_bytes
            rec = ls._load_experiment(str(sid).removeprefix("learn:experiment:"))
            if rec and hashlib.sha256(_content_bytes(rec)).hexdigest() == want_hash:
                return ALIVE, (f"recall-at surfaced seeded lesson {sid} against its own text "
                               f"AND its content hash matches the seed inventory")
            return DEAD, (f"recall-at surfaced seeded lesson {sid} but its content hash "
                          f"MISMATCHES the seed inventory -- the surfaced lesson drifted from "
                          f"what was shipped")
        return ALIVE, f"recall-at surfaced seeded lesson {sid} against its own text"
    if not sources:
        return DEAD, (f"recall-at fired nothing for a seeded lesson's own text "
                      f"({sid}) -- the seam is live but blind to the seeded base")
    return DEAD, (f"recall-at surfaced {len(sources)} lesson(s) but NONE was the seeded "
                  f"{sid} -- the injection path is firing on something other than the seed")


def canary_ledger_receipts_resolve():
    """A terminal task row's commit must name code a clone can actually reach.

    Measured 2026-09-27: only 91 of 172 done rows (52.9%) pointed at a commit reachable from HEAD.
    51 were orphaned by the T411 history rewrite run hours earlier; 29 held the literal string
    'HEAD'; 19 held the placeholder 'deadbee'. A receipt that names no reachable code is not a
    receipt, and `py agent_cli.py sha <old>` exists precisely to repair the orphaned ones.
    """
    ledger = ROOT / "state" / "coord" / "tasks.json"
    if not ledger.is_file():
        return UNCHECKED, "state/coord/tasks.json is absent"
    try:
        rows = json.loads(ledger.read_text(encoding="utf-8")).get("tasks") or []
    except Exception as exc:
        return UNCHECKED, f"could not read the ledger: {exc}"
    terminal = [r for r in rows if r.get("status") == "done"]
    if not terminal:
        return UNCHECKED, "no done rows to judge"
    reach = set(subprocess.run(["git", "-C", str(ROOT), "rev-list", "HEAD"],
                               capture_output=True, text=True).stdout.split())
    prefixes = {s[:12] for s in reach}
    bad = []
    for r in terminal:
        c = str(r.get("commit") or "").strip()
        if not c:
            continue
        if c.upper() == "HEAD" or c.lower().startswith("deadbee"):
            bad.append((r.get("id"), c))
            continue
        if not any(p.startswith(c.lower()) or c.lower().startswith(p) for p in prefixes):
            bad.append((r.get("id"), c))
    if bad:
        return DEAD, (f"{len(bad)} of {len(terminal)} done rows name a commit that is not "
                      f"reachable from HEAD (placeholders, literal HEAD, or orphaned by a "
                      f"history rewrite) -- e.g. " +
                      ", ".join(f"{i}:{c[:10]}" for i, c in bad[:4]))
    return ALIVE, f"all {len(terminal)} done rows name reachable code"


def canary_approved_rows_age():
    """An approved row must be visibly ageing, or the NEXT queue lies about what is fresh.

    Measured 2026-09-27: state_view() computes age_days/stale ONLY for status == PROPOSED
    (core/coord/task_ledger.py:699), so 38 approved rows aged 35-79 days rendered into every
    seat's boot with no age at all, under a closing rule that says "Work only your assigned/NEXT
    task". This canary does not ask the ledger to be tidy -- it asks the SURFACE to show age.
    """
    import time
    try:
        from core.coord.task_ledger import state_view
    except Exception as exc:
        return UNCHECKED, f"could not import the ledger: {type(exc).__name__}: {exc}"
    try:
        # `now` is EPOCH SECONDS -- the module keeps itself pure and makes the caller own the
        # clock (task_ledger.py:684). Passing a datetime here silently yields no ages at all,
        # which is how this canary first reported UNCHECKED against a healthy import.
        view = state_view(now=time.time())
    except Exception as exc:
        return UNCHECKED, f"state_view raised: {type(exc).__name__}: {exc}"
    if not isinstance(view, dict):
        return UNCHECKED, f"state_view returned {type(view).__name__}, not the expected view"

    # `next` is the render every seat is told to work from: approved rows whose deps are done.
    nxt = [r for r in (view.get("next") or []) if isinstance(r, dict)]
    proposed = [r for r in (view.get("proposed") or []) if isinstance(r, dict)]
    if not nxt:
        return ALIVE, "the NEXT queue is empty; nothing can be presented as fresh"
    aged = sum(1 for r in nxt if r.get("age_days") is not None)
    if aged == len(nxt):
        return ALIVE, f"all {len(nxt)} NEXT rows carry an age"
    p_aged = sum(1 for r in proposed if r.get("age_days") is not None)
    return DEAD, (f"{len(nxt) - aged} of {len(nxt)} NEXT rows carry NO age_days while "
                  f"{p_aged}/{len(proposed)} proposed rows do -- staleness is computed only for "
                  f"PROPOSED (task_ledger.py:699), so a ratified intention is rendered to every "
                  f"seat's boot as indistinguishable from fresh work")


#: organ -> (callable, retire_when)
#:
#: `retire_when` is MANDATORY and is the whole reason this registry is allowed to exist. It states
#: the condition under which the canary should be DELETED -- not fixed, deleted -- because the
#: thing it watches has become structurally impossible. A canary whose death condition is "never"
#: is a debt with a nice interface.
CANARIES = {
    "recall-at surfaces a seeded lesson": (
        canary_recall_fires_on_seed,
        "retire when recall-at is retired as a verb, OR when seeding becomes structural so an "
        "unpopulated corpus is unrepresentable and the bootstrap gate asserts recall directly",
    ),
    "lookback answers a known question": (
        canary_lookback,
        "retire when lookback is retired as a verb, or when its rationale role is taken over by "
        "an organ with its own canary here",
    ),
    "events --kind actually filters": (
        canary_events_kind_filter,
        "retire when the events read path is replaced by a typed query layer whose filter is "
        "enforced by its schema rather than by a branch",
    ),
    "eye freq returns a verdict": (
        canary_eye_freq,
        "retire when eye freq is retired as a verb, or when the directive-watcher (core/eye/"
        "directives.py) is folded into a plane whose own liveness is proven by construction",
    ),
    "find locates a known file and names its engine": (
        canary_find,
        "retire when find is retired as a verb, or when the filesystem locator is replaced by an "
        "index whose presence is asserted at boot (never silently walked)",
    ),
    "the connectome holds edges": (
        canary_connectome_has_edges,
        "retire when eye trace is retired, or when the connectome is rebuilt on every ingest by "
        "construction so an empty table is unrepresentable",
    ),
    "done rows name reachable code": (
        canary_ledger_receipts_resolve,
        "retire when the ledger's commit field is validated at write time against a reachable "
        "object, which makes an unreachable receipt unrepresentable",
    ),
    "approved rows are visibly ageing": (
        canary_approved_rows_age,
        "retire when age is computed for every status by construction rather than per-status",
    ),
}


NL = chr(10)
BASELINE = "state/ci/organ_canary_baseline.json"


def _baseline():
    """The organs already known to be dead, as {name: reason}. A missing or unreadable baseline
    returns EMPTY, which makes the gate stricter rather than looser -- absence must never read
    as permission."""
    import json as _json
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         *BASELINE.split("/"))
        return dict((_json.load(open(p, encoding="utf-8")) or {}).get("dead") or {})
    except Exception:
        return {}


def report(gate=False, only=None):
    print("[organ-canaries] does each organ still answer a question whose answer we know?\n")
    dead, unchecked, alive = [], [], []
    for name, (fn, retire_when) in CANARIES.items():
        if only and only not in name:
            continue
        verdict, detail = fn()
        mark = {ALIVE: "ALIVE    ", DEAD: "DEAD     ", UNCHECKED: "UNCHECKED"}[verdict]
        print(f"  {mark} {name}")
        print(f"            {detail}")
        (alive if verdict == ALIVE else dead if verdict == DEAD else unchecked).append(name)
    print()
    print(f"  alive {len(alive)} | dead {len(dead)} | could-not-check {len(unchecked)}")
    if unchecked:
        print("  COULD-NOT-CHECK IS NOT A PASS -- nothing was measured for those.")
    if dead:
        print("\n  A dead organ passes every other guardrail in this repo: it imports, it is")
        print("  wired, its door matches its parity table, and it returns nothing. That is the")
        print("  gap this checker exists to close.")
    if gate:
        # A RATCHET, not an absolute. Five organs were already dead when this checker was
        # written; gating on them would have made the gate red on day one, which is exactly
        # how a gate stops carrying information (state/ci/guardrail_baseline.json, _why). A
        # RECORDED death is tolerated; a NEW one fails. The debt is frozen, not forgiven.
        known = _baseline()
        fresh = [n for n in dead if n not in known]
        revived = [n for n in known if n in alive]
        if revived:
            print(NL + f"[organ-canaries] {len(revived)} organ(s) came BACK: {chr(44).join(revived)}")
            print("  Remove them from state/ci/organ_canary_baseline.json to bank the paydown.")
        if fresh:
            print(NL + f"[organ-canaries] GATE FAIL -- {len(fresh)} NEWLY dead organ(s):")
            for n in fresh:
                print(f"    {n}")
            print("  Revive it, or record it in state/ci/organ_canary_baseline.json WITH A")
            print("  REASON in the same commit, so the death is a decision and not a drift.")
            return 1
        if dead:
            print(NL + f"[organ-canaries] {len(dead)} organ(s) dead, all RECORDED -- no new debt.")
        if unchecked:
            print(f"\n[organ-canaries] GATE FAIL -- {len(unchecked)} canary could not run; an "
                  f"unrunnable canary is an unwatched organ.")
            return 1
        # Say what actually happened. 'every organ answered' while five do not is the same
        # confident-zero this checker exists to catch, and a gate that misreports its own
        # verdict is worse than no gate at all.
        if dead:
            print(NL + f"[organ-canaries] gate ok -- no NEW debt "
                       f"({len(alive)} alive, {len(dead)} dead and recorded).")
        else:
            print(NL + f"[organ-canaries] gate ok -- all {len(alive)} organ(s) answered.")
    return 0


def self_test():
    """The registry's own invariant: every canary declares what would retire it."""
    missing = [n for n, (_fn, rw) in CANARIES.items() if not (rw or "").strip()]
    if missing:
        print(f"[organ-canaries] REGISTRY INVALID -- no retire_when on: {missing}")
        return 1
    print(f"[organ-canaries] registry ok -- {len(CANARIES)} canaries, all with a retirement rule")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate", action="store_true", help="fail on a dead or unrunnable organ")
    ap.add_argument("--only", help="run canaries whose name contains this substring")
    ap.add_argument("--registry", action="store_true",
                    help="check the registry's own invariant and exit")
    args = ap.parse_args(argv)
    if args.registry:
        return self_test()
    return report(gate=args.gate, only=args.only)


if __name__ == "__main__":
    sys.exit(main())
