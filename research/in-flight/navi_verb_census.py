#!/usr/bin/env python3
"""NAVI-1: verb census + family taxonomy. Read-only. Output: JSON to stdout.

Walks agent_cli.py's parser for all 88 verbs, cross-references the three seat
registries (data/verb-registry/{kimi,claude,deepseek}.json), and files every
verb into a newcomer-facing family. Also reports the allowlist diff: which
verbs the unattended-exec door (core/comm/toolbox.py) lets through vs which
it refuses.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- the door's allowlist, transcribed from core/comm/toolbox.py:1122 ---
DOOR_READ_VERBS = {
    "boot","delta","discover","recall","recall-at","list","notes","status",
    "stats","injections","harnesses","triage","recall-counters","task",
    "story","events","doctor","promoted","lookback","knowledge-map","fence",
    "flow","bifrost-sync","locks","unwedge","pulse","flightdeck",
}
DOOR_MUTATING_FLAGS = {"--commit","--consume","--apply","--fold","--capture","--promote"}

# --- census: every add_parser call in agent_cli.py ---
src = (ROOT / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
# top-level verbs: `x = sub.add_parser("name", help="...")`
verbs = {}   # name -> help
for m in re.finditer(r'sub\.add_parser\(\s*"([^"]+)"\s*,\s*help="([^"]*)"', src):
    verbs.setdefault(m.group(1), m.group(2))
# sub-verbs (resident X, doc X, eye X, tool X): captured with their parent's prefix below
subverbs = []   # (parent, name, help)
parent_of_var = {}
for m in re.finditer(r'(\w+)\s*=\s*sub\.add_parser\(\s*"([^"]+)"', src):
    parent_of_var[m.group(1)] = m.group(2)
for m in re.finditer(r'(\w+)\s*=\s*(\w+)\.add_parser\(\s*"([^"]+)"\s*,\s*help="([^"]*)"', src):
    var, parent_var, name, hlp = m.groups()
    # resolve parent's verb name if we know its variable
    pverb = parent_of_var.get(parent_var)
    if pverb and var != "sub":
        subverbs.append((pverb, name, hlp))

# --- seat registries ---
registries = {}
for seat in ("kimi", "claude", "deepseek"):
    p = ROOT / "data" / "verb-registry" / f"{seat}.json"
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        registries[seat] = {k: v for k, v in data.get("entries", {}).items()}

# --- families (NAVI-1 proposal) ---
# The shape: what the verb DOES for the seat, named for the mental model.
FAMILIES = {
    "ORIENT":   "where am I / what changed -- the seat wakes up",
    "REMEMBER": "the knowledge plane -- lessons, notes, recall",
    "COORDINATE": "the work ledger -- tasks, handoffs, locks, deferrals",
    "COMMUNE":  "the bus -- talking to peers, inbox, mail",
    "FLEET":    "liveness + pressure -- who is alive, who is wedged",
    "EYE":      "the transcript plane -- corpus reads, verbatim citations",
    "FORGE":    "make new verbs -- aliases, kits, play-tier, kata",
    "AUDIT":    "belief-vs-state -- instruments that check the instruments",
    "CEREMONY": "callsigns, seasons, gratitude -- the social fabric",
    "VAULT":    "secrets + credentials -- the one write-only door",
    "OUTSIDER": "doors that reach outside the fleet -- discord, captions, ask",
}

def family_of(verb):
    v = verb
    if v in ("boot","delta","status","discover","story","timeline","compare"): return "ORIENT"
    if v in ("learn","recall","list","recall-at","recall-feedback","recall-curate",
             "repeat","note","notes","wrap","lookback","knowledge-map","tag-anti-pattern",
             "injections","stats","triage","recall-counters","graduate","episode","log"): return "REMEMBER"
    if v in ("task","handoff","lock","unlock","locks","defer","followup","bench",
             "scout","audit","grant","seat-identity"): return "COORDINATE"
    if v in ("bifrost-sync","bifrost-send","bifrost-ack","bifrost-nudge","bifrost-fetch",
             "bifrost-pause","bifrost-resume","bifrost-skip-to-now","bifrost-drain",
             "bifrost-standby","mailbox","promoted","flow","capture","console-log",
             "events","stand-down"): return "COMMUNE"
    if v in ("doctor","pulse","flightdeck","unwedge","roster","fleet","harnesses"): return "FLEET"
    if v == "eye": return "EYE"
    if v in ("alias","run","kata","kit","tool"): return "FORGE"
    if v in ("suite-baseline","clobber-scan","tally","packet-trace","packet-stats"): return "AUDIT"
    if v in ("resident","season-score","toast"): return "CEREMONY"
    if v == "secret": return "VAULT"
    if v in ("ask","sift","discord","captions","friction","report","reentry","wish","doc"): return "OUTSIDER"
    return "UNSORTED"

rows = []
for name, hlp in sorted(verbs.items()):
    fam = family_of(name)
    in_door = name in DOOR_READ_VERBS
    rows.append({
        "verb": name, "family": fam, "door_read": in_door, "help": hlp,
        "gap": (fam != "UNSORTED" and not in_door and fam in
                ("ORIENT","REMEMBER","FLEET","EYE","AUDIT")),
    })

out = {
    "verbs": rows,
    "subverbs": [{"parent": p, "name": n, "help": h} for p, n, h in subverbs],
    "registries": {
        seat: {name: {"family": e.get("family", "UNSORTED"),
                      "evidence": e.get("evidence"),
                      "kind": e.get("kind"),
                      "version": e.get("version")}
               for name, e in entries.items()}
        for seat, entries in registries.items()
    },
    "door": {
        "read_verbs": sorted(DOOR_READ_VERBS),
        "mutating_flags": sorted(DOOR_MUTATING_FLAGS),
        "refused_but_live": sorted(set(verbs) - DOOR_READ_VERBS),
        "gated_but_gone": sorted(DOOR_READ_VERBS - set(verbs)),
    },
    "families": FAMILIES,
}
json.dump(out, sys.stdout, indent=1)
print()
