"""
INSTALL: mint parse-gate, toast, muse into the REAL deepseek toolbelt.
Uses Toolbelt (sugar-only validated, supersession-safe) — never hand-edits JSON.
"""
from core.toolbelt.registry import Toolbelt
import agent_cli
import sys

tb = Toolbelt("deepseek")

print(f"BEFORE: {tb.render_list()}")
print()

# ── PARSE-GATE
try:
    e = tb.mint("parse-gate", steps=[
        ["lock",    "deepseek", "placeholder"],
        ["fence",   "open", "--slot", "brief"],
        ["kata",    "deepseek", "placeholder"],
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: scar-springboard #1 from tools hunt. lock→fence→kata = the edit-verify cycle.")
    print(f"[MINTED] parse-gate v{e['version']} [{e['evidence']}]")
except ValueError as ve:
    print(f"[SKIP] parse-gate: {ve}")

# ── TOAST
try:
    e = tb.mint("toast", steps=[
        ["story",   "--chronicle"],
        ["notes",   "--project"],
        ["wrap",    "--hours", "24"],
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: raise a glass. chronicle→project→wrap = end-of-session celebration.")
    print(f"[MINTED] toast v{e['version']} [{e['evidence']}]")
except ValueError as ve:
    print(f"[SKIP] toast: {ve}")

# ── MUSE
try:
    e = tb.mint("muse", steps=[
        ["knowledge-map", "recovery"],
        ["lookback",      "what are our biggest architectural risks?"],
        ["events",        "--capture", "--summary", "muse-firehose"],
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: creative brainstorm. map→lookback→capture = the muse ritual.")
    print(f"[MINTED] muse v{e['version']} [{e['evidence']}]")
except ValueError as ve:
    print(f"[SKIP] muse: {ve}")

print()

# ── KATA all three
for name in ["parse-gate", "toast", "muse"]:
    try:
        steps = tb.resolve(name)
        ok, results = agent_cli._kata_check(steps)
        if ok:
            entry = agent_cli._kata_apply(tb, name, results)
            print(f"[KATA] {name} LEVELED UP: GUESS → {entry['evidence']} v{entry['version']} (tested_against={entry['tested_against']})")
        else:
            bad = [r for r in results if not r[0]]
            print(f"[KATA] {name} FAILED grammar: {bad}")
    except Exception as ex:
        print(f"[KATA] {name} ERROR: {ex}")

print()
print(f"AFTER: {tb.render_list()}")
print(f"\n>>> DONE. {len(tb.active())} active verbs in deepseek's toolbelt. <<<")
