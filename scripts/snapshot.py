"""Snapshot the current Bifrost session for later resume. Run before shutting down."""
import sys, os
# REPO ROOT, not scripts/ -- `py scripts/snapshot.py` puts the SCRIPT's dir on sys.path, so
# the one-dirname version could never import core.* and this backup door was dead on every
# invocation (found 2026-07-31, mid-shutdown, which is precisely when a backup tool fails).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.comm.session_state import save, list_snapshots

label = sys.argv[1] if len(sys.argv) > 1 else ""
result = save(label=label)
if result["ok"]:
    print(f"💾 SAVED: {result['path']}")
    print(f"   Running agents: {result['running']}")
    print(f"   Online agents:  {result['online']}")
    print(f"\n   Resume tomorrow with: py scripts/snapshot.py --resume")
    print(f"   Or from the Bifrost UI: click 🔄 Resume")
else:
    print(f"❌ FAILED: {result.get('error', 'unknown')}")

# Also show available snapshots
snaps = list_snapshots()
if snaps:
    print(f"\n   {len(snaps)} saved session(s):")
    for s in snaps[:5]:
        print(f"   - {s['file']}: {s['label']} ({s['running_agents']} agents)")
