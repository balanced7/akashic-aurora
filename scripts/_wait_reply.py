"""Temporary poll script — wait for Claude reply after a send."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import _connect

OUR_SEND = sys.argv[1] if len(sys.argv) > 1 else "1782682462256-0"
MAX_POLLS = int(sys.argv[2]) if len(sys.argv) > 2 else 24

c = _connect()
if not c:
    print("Redis offline")
    raise SystemExit(2)

print(f"Waiting for Claude reply after {OUR_SEND} (up to {MAX_POLLS * 5}s)")
print()

for i in range(MAX_POLLS):
    entries = c.xrevrange("bifrost:inbox:cursor", min=OUR_SEND, count=10)
    claude_msgs = []
    for eid, fields in entries:
        if fields.get("frm") == "claude" and eid > OUR_SEND:
            content = fields.get("content", "")
            try:
                content = json.loads(content)
            except (ValueError, TypeError):
                pass
            claude_msgs.append((eid, fields.get("kind"), fields.get("ts"), content))

    if claude_msgs:
        for eid, kind, ts, content in sorted(claude_msgs):
            print(f"=== NEW {eid} | {kind} | {ts} ===")
            if isinstance(content, str):
                print(content)
            else:
                print(json.dumps(content, indent=2))
            print()
        raise SystemExit(0)

    print(f"  poll {i + 1}/{MAX_POLLS}: no reply yet...")
    time.sleep(5)

print("No new reply within timeout.")
print("Latest inbox entries:")
for eid, fields in c.xrevrange("bifrost:inbox:cursor", count=5):
    content = str(fields.get("content", ""))[:200]
    print(f"  {eid} {fields.get('frm')} [{fields.get('kind')}]: {content}")
raise SystemExit(1)
