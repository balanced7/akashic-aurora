"""Quick smoke test for core.toolbelt.audit — runs against live registry files."""
import sys
sys.path.insert(0, ".")

from core.toolbelt.audit import run, render, VerbsDomain

# Run VERBS domain only
domain = VerbsDomain()
rows = domain.run()
print(render(rows=rows))

# Summary
drifting = [r for r in rows if r.verdict == "DRIFT"]
print(f"\n--- {len(drifting)} DRIFT row(s) ---")
for r in drifting:
    print(f"  [{r.rule}] {r.entry_ref}: {r.detail}")
