#!/usr/bin/env python3
"""The failsafe deadman's scheduled body -- reads the expectation, speaks if it is wrong.

Registered as a Windows Scheduled Task beside the four Aurora jobs already running
(AkashicAurora-TranscriptArchive-Daily and siblings), because the OS scheduler is the one layer we
do not have to keep alive ourselves -- which is the honest answer to "who watches the watcher".

DEPENDS ON NOTHING IT WATCHES. No redis, no bus, no lane, no agent_cli verb: a JSON file, a clock,
and a write-only webhook. Bifrost being wedged is the case this exists for, so touching Bifrost
would reproduce control_channel.py's original wound.

Run:  pyw E:\\AI-Setup\\scripts\\ops\\failsafe_watcher.py
      py  scripts/ops/failsafe_watcher.py --dry     (decide + print, never post)

Exit codes (what the scheduler's LastTaskResult means): 0 = silent-and-correct OR alarm
delivered; 1 = an alarm was DUE and the webhook POST failed -- 0x1 in Task Scheduler is
always "the deadman tried to speak and could not", never a healthy path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.comm import failsafe as F  # noqa: E402


def _webhook() -> str:
    """The operator's own feed. Read through the ONE vault function so AKASHIC_SECRETS_DIR can
    redirect it -- a module-path constant is unisolatable, and this house has already had a test
    post to a real Discord surface because of one."""
    try:
        from core.comm.secret_intake import secrets_dir
        return (secrets_dir() / "discord_webhook.url").read_text(encoding="utf-8").strip()
    except Exception:                                                   # noqa: BLE001
        return ""


def _post(text: str) -> bool:
    url = _webhook()
    if not url:
        return False
    try:
        body = json.dumps({"content": text[:1900]}).encode("utf-8")
        # Discord's Cloudflare front 403s (error 1010) the default Python-urllib signature.
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "AkashicFailsafe/1 (deadman watcher)"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except Exception:                                                   # noqa: BLE001
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="out-of-band deadman for a declared run")
    ap.add_argument("--path", default=None, help="expectation file (default: state/expect/)")
    ap.add_argument("--dry", action="store_true", help="decide and print; never post")
    args = ap.parse_args()

    path = args.path or F.default_path()
    doc = F.load(path)
    alarm = F.verdict(doc)

    if alarm is None:
        # Silence is the overwhelmingly common outcome and it is CORRECT. Say so only on --dry,
        # so the scheduled run leaves no noise behind.
        if args.dry:
            state = "no expectation on disk" if doc is None else (
                "stood down" if not doc.get("active") else "checkpoint fresh")
            print(f"[failsafe] silent -- {state}")
        return 0

    if args.dry:
        print(f"[failsafe] WOULD POST: {alarm}")
        return 0

    posted = _post(alarm)
    if posted:
        F.mark_alarmed(path)             # start the cooldown only once it actually went out
    print(f"[failsafe] {'posted' if posted else 'POST FAILED'}: {alarm}")
    return 0 if posted else 1


if __name__ == "__main__":
    raise SystemExit(main())
