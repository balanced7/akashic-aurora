"""The read-only pre-flight: is another seat mid-flight in my area, and has this been done?

`scout` builds its evidence pack live (ledger, locks, a role's own verdicts) and files what it
concludes UNadjudicated -- the file is a question for an operator, never a ruling, which is why
the verb says so on stderr every time.
"""
from __future__ import annotations

import json
import sys

from verbs.registry import verb


@verb(local=True, door_notes="CLI only; reads the scout organ under core/. Files an UNadjudicated verdict -- never a ruling. local=True because the body names a default wearer and a default filer.")
def cmd_scout(args):
    """T292: the scout verb -- one command for the read-only pre-flight.

    'Is another seat mid-flight in my area / has this been done already' -- answered from
    a pack built live (ledger, locks, the role's own verdicts), by a resident wearer
    (deepseek default) or a blind tier-0 branch. The verdict files itself under
    role=Scout and waits, visibly unadjudicated, for an operator to rule.
    """
    from core.fleet import scout as SC
    q = " ".join(args.text or []).strip()
    if not q:
        print("usage: py agent_cli.py scout \"is anyone mid-flight on <area>?\"",
              file=sys.stderr)
        return 2
    try:
        r = SC.scout_ask(q, wearer=args.wearer, by=(args.by or "claude"),
                         blind=bool(args.blind), question_shape=args.shape)
    except ValueError as e:
        print(f"[scout] {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(r, ensure_ascii=False, default=str))
        return 0 if r.get("ok") else 1
    secs = (r.get("pack_meta") or {}).get("sections") or {}
    bounds = ", ".join(f"{k}={v}" for k, v in sorted(secs.items()))
    print(f"# scout [{r['tier']}] ask {r['ask_id']}  (pack: {bounds})")
    print(r.get("answer") or f"(no answer -- {r.get('why') or 'ask failed'})")
    print(f"\n-- verdict filed unadjudicated. When you have CHECKED this answer: "
          f"py agent_cli.py resident adjudicate {r['ask_id']} --outcome confirmed|refuted "
          f"--by <operator>", file=sys.stderr)
    return 0 if r.get("ok") else 1
