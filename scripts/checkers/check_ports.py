"""check_ports -- what is listening, what it belongs to, and what nobody declared.

Daniil 2026-08-10: "How do we make scanning for ports in use and what they belong to as easy
as our wiring check?"

So this copies check_wiring's ergonomics deliberately: one command, one verdict line, a
--report mode for the map, a frozen baseline that FAILS OPEN, [NEW] marking so old debt does
not block a commit, and failure text that names every way out.

THE ONE STRUCTURAL DIFFERENCE, and it is the whole reason a port checker is not just a
grep. check_wiring reconciles TWO planes -- defined vs reachable. Ports have THREE:

    DECLARED   config.PORT_REGISTRY
    IN CODE    port literals in live source
    LISTENING  live sockets + container publishes

Three planes means three ways to disagree, and only ONE of them is a defect the author can
fix, which is why only that one is a gate:

    in code, not declared   -> DRIFT. Someone bound a port nobody wrote down. GATED.
    listening, not declared -> a service nobody registered. REPORTED, never gated: the
                               listener may not be ours at all.
    declared, not listening -> AMBIGUOUS, and this is the trap. Nothing in a socket table
                               distinguishes "the service is down" from "the entry is
                               stale". Calling it stale asserts absence as fact -- the class
                               this repo broke at the guard-of-guards (T178, a missing
                               baseline returning {} and passing), in _receipt_author (T262,
                               a store outage rendering a verdict about a receipt), and in
                               the recall funnel. So it renders UNKNOWN. Always.

NO DOCKER IS ALSO UNKNOWN, not empty. A checker that requires a daemon is a checker that
gets disabled, and a container plane rendered as "nothing there" would be the same lie one
level down.

Run:  py scripts/checkers/check_ports.py            # gate (exit 1 on NEW undeclared drift)
      py scripts/checkers/check_ports.py --report   # the map: who owns what, and what is silent
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import config  # noqa: E402

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port_baseline.json")

#: Where a port literal in LIVE code counts as drift. Archive and vendored trees are excluded
#: by prefix rather than by name, so a new file under them cannot quietly re-enter the scan.
_SCAN_DIRS = ("core", "scripts", "agent")
_SCAN_FILES = ("agent_cli.py", "ai_setup_mcp.py", "bootstrap.py")
_EXCLUDE = ("_archive", "ComfyUI-Zluda", "__pycache__", "node_modules", ".claude")

#: MATCH THE MEANING, NOT THE NEIGHBOURHOOD. The first version of this flagged any 4-5 digit
#: number on a line mentioning "port", and measured 3 real findings against 6 false ones: a
#: citation year ("Park et al. 2023"), a 3600-second TTL, a "4867-key wall" in prose, a
#: timeout=30000 in milliseconds, and this file's own 65535 range bound. A gate at 33%
#: precision gets routed around -- check_wiring's comment makes exactly that point about the
#: cost of crying wolf. So the number must be attached to PORT SYNTAX, not merely nearby:
#:     --port 9000 | port=8787 | PORT = 8787 | "port": 8787 | http://host:11435
#: The third alternative was added after tightening LOST a real finding: CONTROL_PORT_BASE =
#: ... "47100" stopped matching because PORT sits inside a larger identifier and \bport\b
#: needs a word boundary. An identifier NAMED *PORT* assigned a number IS a port declaration,
#: so that shape is its own rule -- precision bought by dropping a true positive is not
#: precision, it is a narrower blind spot.
_PORT_LIT = re.compile(
    r"""(?:
          (?:--)?\bports?\b["']?\s*[=:]?\s*["']?(?P<a>\d{4,5})\b   # port=N, --port N, "port": N
        | ://[\w.\-\[\]]+:(?P<b>\d{4,5})\b                          # scheme://host:N
        | \b[A-Z][A-Z0-9_]*PORT[A-Z0-9_]*\s*=[^\n]*?["']?(?P<c>\d{4,5})\b   # SOME_PORT_X = N
        )""", re.I | re.X)

UNKNOWN = "UNKNOWN"


# ------------------------------------------------------------------ plane 3: what is listening

def listening_ports():
    """Host sockets in LISTENING state. Returns (set_of_ports, ok) -- ok=False means the probe
    itself failed, which renders UNKNOWN rather than an empty set."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return set(), False
    ports = set()
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        m = re.search(r":(\d+)\s+\S+\s+LISTENING", line)
        if m:
            ports.add(int(m.group(1)))
    return ports, True


def container_ports():
    """{port: container_name} for RUNNING containers. (map, ok) -- ok=False renders UNKNOWN.

    Skippable via AKASHIC_PORTS_NO_DOCKER so the degrade path is testable without uninstalling
    docker, and so a CI box without a daemon behaves identically to one that has it down.
    """
    if os.getenv("AKASHIC_PORTS_NO_DOCKER"):
        return {}, False
    try:
        out = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return {}, False
        raw = out.stdout
    except Exception:
        return {}, False
    found = {}
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        name, ports = line.split("\t", 1)
        for m in re.finditer(r":(\d+)(?:-(\d+))?->", ports):
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.group(2) else lo
            for p in range(lo, hi + 1):
                found[p] = name.strip()
    return found, True


# ------------------------------------------------------------------ plane 2: literals in code

def _scan_files():
    for f in _SCAN_FILES:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            yield p
    for d in _SCAN_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not any(e in x for e in _EXCLUDE)]
            if any(e in dirpath for e in _EXCLUDE):
                continue
            for fn in filenames:
                if fn.endswith(".py"):
                    yield os.path.join(dirpath, fn)


def code_ports():
    """{port: [ "relpath:line", ... ]} for port-looking literals in LIVE code.

    Deliberately conservative: a number only counts when its LINE mentions a port-ish word.
    A wide net here would flood the gate with timeouts and byte sizes, and a gate that cries
    wolf gets routed around -- check_wiring's own comment makes that point about false
    positives, and it cost a week there.
    """
    hits = {}
    for path in _scan_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except Exception:
            continue
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("#"):
                continue
            for m in _PORT_LIT.finditer(line):
                raw = m.group("a") or m.group("b") or m.group("c")
                p = int(raw)
                if 1024 <= p <= 65535:
                    hits.setdefault(p, []).append(f"{rel}:{i}")
    return hits


# ------------------------------------------------------------------ the ratchet

def load_baseline(path=BASELINE_PATH):
    """Frozen known-undeclared literals. FAILS OPEN: a missing baseline freezes nothing and
    does not crash -- the same choice check_wiring makes, and for the same reason."""
    try:
        with open(path, encoding="utf-8") as fh:
            return {int(k) for k in json.load(fh).get("ports", [])}
    except Exception:
        return set()


def band_of(port):
    for lo, hi, world in config.PORT_BANDS:
        if lo <= port <= hi:
            return world
    return None


def report():
    reg = config.PORT_REGISTRY
    listen, listen_ok = listening_ports()
    cont, cont_ok = container_ports()

    print("PORT MAP  --  declared / in-code / listening\n")
    print(f"{'PORT':>6}  {'WORLD':<9} {'STATE':<10} {'OWNER':<38} WHAT")
    for port in sorted(reg):
        e = reg[port]
        if not listen_ok:
            state = UNKNOWN
        elif port in listen:
            state = "listening"
        else:
            # AMBIGUOUS: down or stale, and the socket table cannot tell. Never "stale".
            state = UNKNOWN
        owner = e.get("owner", "?")
        if port in cont:
            owner = f"{cont[port]} (running)"
        print(f"{port:>6}  {e.get('world','?'):<9} {state:<10} {owner[:38]:<38} {e.get('what','')}")

    print(f"\n  legend: listening = seen in the socket table | {UNKNOWN} = registered but "
          f"silent, which is\n          EITHER the service is down OR the entry is stale -- "
          f"nothing here can tell those apart.")
    if not listen_ok:
        print("          (the socket probe itself failed, so every state above is UNKNOWN)")
    if not cont_ok:
        print(f"          (docker unavailable -- the container plane is {UNKNOWN}, not empty)")

    # A report where 30 of 30 rows are Windows service ports is a report nobody reads twice.
    # Split by whether the listener could plausibly be OURS: a port inside a band we claim, or
    # one a container published, is a real finding; everything else is the machine's business.
    undeclared = sorted(p for p in listen if p not in reg and 1024 <= p <= 65535)
    ours = [p for p in undeclared if band_of(p) or p in cont]
    theirs = [p for p in undeclared if p not in ours]

    print(f"\nUNREGISTERED, AND PLAUSIBLY OURS ({len(ours)}) -- in a band we claim, or a "
          f"container we run:")
    if not ours:
        print("  (none -- every listener in our bands is registered)")
    for p in ours:
        who = cont.get(p, "no container -- something in this repo bound it")
        band = band_of(p)
        note = f"  <-- inside the {band} band" if band else ""
        print(f"  {p:>6}  {who}{note}")

    print(f"\nOTHER LISTENERS ({len(theirs)}) -- outside every band we claim; the machine's own "
          f"services\n          and other apps. Listed with --verbose; not our concern by "
          f"construction, but\n          counted rather than hidden so a real service cannot "
          f"disappear into the silence.")
    if "--verbose" in sys.argv and theirs:
        for p in theirs:
            print(f"  {p:>6}  {cont.get(p, 'OS or another app')}")

    print("\nDYNAMIC BY DESIGN (no fixed port to register):")
    print("  runner control channels bind an EPHEMERAL loopback port per seat "
          "(core/comm/control_channel.py)\n  -- e.g. kimi on 127.0.0.1:47127 this session. "
          "They cannot be pre-registered by number,\n  which is why an unregistered listener "
          "in the high range is not automatically drift.")

    if config.PORT_RETIRED:
        print("\nRETIRED (never silently resurrect):")
        for p, why in sorted(config.PORT_RETIRED.items()):
            flag = "  *** LISTENING AGAIN ***" if p in listen else ""
            print(f"  {p:>6}  {why}{flag}")
    return 0


def gate():
    reg = config.PORT_REGISTRY
    baseline = load_baseline()
    hits = code_ports()
    known = set(reg) | set(config.PORT_RETIRED) | {config.PORT_TEST_UI_BASE, config.PORT_TEST_UI_MAX}
    drift = {p: locs for p, locs in hits.items()
             if p not in known and band_of(p) is None and p not in baseline}
    frozen = {p for p in hits if p in baseline}

    stale = sorted(p for p in baseline if p not in hits)
    if stale:
        print(f"note: {len(stale)} baseline entr(ies) no longer appear in code "
              f"({', '.join(str(p) for p in stale[:6])}) -- prune them so the ratchet cannot rot.")

    if drift:
        print(f"\nFAIL: {len(drift)} port literal(s) in live code that no registry declares "
              f"|  frozen backlog: {len(frozen)}\n")
        for p, locs in sorted(drift.items()):
            print(f"  {p}  ->  {', '.join(locs[:4])}{' ...' if len(locs) > 4 else ''}   [NEW]")
        print(f"\n  Fix it one of three ways: import the value from config.py, add the port to "
              f"config.PORT_REGISTRY with an owner, or -- if it is genuinely not a port -- add "
              f"it to\n  {os.path.relpath(BASELINE_PATH, ROOT).replace(os.sep, '/')} with a reason.")
        return 1

    print(f"PASS: every port literal in live code is declared, retired, or in a reserved band "
          f"({len(frozen)} on the frozen backlog, {len(reg)} registered).")
    return 0


def main():
    if "--report" in sys.argv:
        return report()
    return gate()


if __name__ == "__main__":
    sys.exit(main())
