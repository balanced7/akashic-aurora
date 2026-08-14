"""gen_ports -- render docs/PORTS.md from config.PORT_REGISTRY.

docs/PORTS.md was the ONE hand-written map in a repo that generates PHYSICS.md, DOORS.md,
MAP.md, MODULE_INDEX.md and PRIOR_ART.md from live state on every commit -- and it was the
one that went stale. Measured 2026-08-10: every container port was missing (11434, 8888,
3000, 5000/5001), because the doc described what PYTHON binds and was blind to what
CONTAINERS bind. It also listed 8080 as "legacy/inactive -- never live" while a container
had been bound to it until that morning. A map that asserts DEAD about something RUNNING is
worse than a map with a hole, because it is trusted.

DELIBERATELY STATIC. This renders only the DECLARED plane, never live sockets or docker, so
the committed file is reproducible on any machine and a diff means somebody changed the
registry -- not that a service happened to be down when they committed. The live view is
`py scripts/checkers/check_ports.py --report`, and the doc points at it rather than trying
to be it.

Run:  py scripts/generators/gen_ports.py            # writes docs/PORTS.md
      py scripts/generators/gen_ports.py --check    # exit 1 if the file is stale
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import config  # noqa: E402

OUT = os.path.join(ROOT, "docs", "PORTS.md")

_WORLD_ORDER = {"prod": 0, "sandbox": 1, "test": 2, "external": 3}


def render() -> str:
    reg = config.PORT_REGISTRY
    L = []
    L.append("# Port Registry — what lives where")
    L.append("")
    L.append("Status: current  ·  **GENERATED — do not edit by hand.**")
    L.append("Source of truth: `config.PORT_REGISTRY`. Regenerate with "
             "`py scripts/generators/gen_ports.py`.")
    L.append("")
    L.append("This file is the DECLARED plane only, so it is reproducible on any machine. For "
             "what is actually")
    L.append("listening right now — and what nobody declared — run:")
    L.append("")
    L.append("```")
    L.append("py scripts/checkers/check_ports.py --report")
    L.append("```")
    L.append("")
    L.append("## The bands — the digits tell you the world")
    L.append("")
    L.append("```")
    for lo, hi, world in config.PORT_BANDS:
        L.append(f"{lo}-{hi}   {world.upper()}")
    L.append("```")
    L.append("")
    # W156: derived from the registry rather than named by hand -- the prose was the half
    # of this generator that could still drift, and it did: it said "sandbox" after the
    # world was renamed and knew about only two of the three Redis worlds.
    _redis = " · ".join(
        f"`{p}` {e['world']}"
        for p, e in sorted(config.PORT_REGISTRY.items())
        if e.get("bound_by") == "container" and "knowledge store" in e.get("what", "")
        or (p in (config.REDIS_PORT, config.REDIS_PORT_BETA, config.REDIS_PORT_ALPHA)))
    L.append(f"Redis mirrors the same worlds: {_redis} · "
             "**db 15** on prod = test isolation")
    L.append("(tests never need their own Redis port — they use a separate logical DB).")
    L.append("")
    L.append("## The map")
    L.append("")
    L.append("`bound_by` is the field the old hand-written map could not express, and the "
             "reason its blind spot")
    L.append("was invisible: a **container**-bound port appears in NO source literal, so no "
             "amount of grepping")
    L.append("this repo would ever have found it.")
    L.append("")
    L.append("| Port | World | Bound by | What | Owner |")
    L.append("|------|-------|----------|------|-------|")
    for port in sorted(reg, key=lambda p: (_WORLD_ORDER.get(reg[p].get("world"), 9), p)):
        e = reg[port]
        L.append(f"| **{port}** | {e.get('world','?')} | {e.get('bound_by','?')} | "
                 f"{e.get('what','')} | `{e.get('owner','?')}` |")
    L.append("")
    if config.PORT_RETIRED:
        L.append("## Retired — never silently resurrect")
        L.append("")
        L.append("Kept deliberately: deleting a retirement makes the port re-discoverable as "
                 "\"free\" by the next")
        L.append("person, which is how a dead service comes back wearing a live port.")
        L.append("")
        for p, why in sorted(config.PORT_RETIRED.items()):
            L.append(f"- **{p}** — {why}")
        L.append("")
    L.append("## Rules for code that opens a port")
    L.append("")
    L.append("1. **Never hardcode a port.** Import it from `config.py`; a throwaway UI uses "
             "`config.allocate_test_ui_port(offset)`, which raises if you escape the band.")
    L.append(f"2. **{config.PORT_UI_RESERVED} is not the console.** It is reserved prod-aux. "
             f"The console is `config.PORT_UI` ({config.PORT_UI}).")
    L.append(f"3. **Tests never bind {config.PORT_UI}, {config.PORT_UI_BETA} or "
             f"{config.PORT_UI_ALPHA}.** A test UI "
             f"lives in [{config.PORT_TEST_UI_BASE}, {config.PORT_TEST_UI_MAX}]; test data "
             f"lives in Redis db 15.")
    L.append("4. **A new port goes in `config.PORT_REGISTRY` with an owner** — "
             "`check_ports.py` fails the commit otherwise, and the failure names the three "
             "ways out.")
    L.append("")
    L.append("## Dynamic by design")
    L.append("")
    L.append("Runner control channels take `CONTROL_PORT_BASE + n` on loopback, one per seat "
             "(`core/comm/control_channel.py`),")
    L.append("so the exact port cannot be registered by number. An unregistered listener high "
             "in the range is")
    L.append("therefore not automatically drift — the checker says so rather than crying wolf.")
    L.append("")
    return "\n".join(L) + "\n"


def main():
    new = render()
    if "--check" in sys.argv:
        try:
            with open(OUT, encoding="utf-8") as fh:
                cur = fh.read()
        except Exception:
            cur = ""
        if cur.strip() != new.strip():
            print("FAIL: docs/PORTS.md is stale -- run py scripts/generators/gen_ports.py")
            return 1
        print("PASS: docs/PORTS.md matches config.PORT_REGISTRY")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(new)
    print(f"wrote {os.path.relpath(OUT, ROOT)} "
          f"({len(config.PORT_REGISTRY)} registered, {len(config.PORT_RETIRED)} retired)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
