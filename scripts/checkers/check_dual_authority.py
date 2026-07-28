"""check_dual_authority -- two artifacts claiming one state must move together or die.

Born from the B incident (2026-07-28): store_state.db froze at Jul-25 23:28 while
store_state.json advanced to Jul-28 16:04 -- three days of split-brain found by a human
reading a board, not by an instrument. The board named the class the same day: "the
second half-abandoned migration this week to be found by accident. A checker that flags
dual authorities with diverging freshness ... would catch the class. Same pattern as
check_advertised_verbs: enumerate the promises, assert the wiring."

THE CLASS, not the instance: any pair of artifacts that both claim to hold the same
state (a .db and a .json; a mirror and its source) with freshness that has torn apart.
Three findings, in descending severity:

  STALE-AUTHORITY  the backend the flag SELECTS is the frozen twin. Every read is served
                   from a store that stopped moving -- the confidently-wrong answer,
                   which is the exact failure genus the SQLite backend exists to remove.
  DIVERGENT-DUAL   both twins exist and their mtimes have torn beyond the window. One of
                   them is an abandoned migration artifact; finish the cutover or retire
                   the twin. (This line fired retroactively on the live incident shape.)
  WAL-GROWTH       rider 1 of the WAL adoption lesson (measured 2026-07-26: one held
                   reader grew -wal to 523,272 bytes and blocked truncation): WAL size
                   is a health signal, surfaced here instead of discovered as disk
                   pressure.

A converging pair inside the window is NOT a failure: a deliberate dual-write cutover
window looks exactly like that, and punishing it would punish the only safe migration
shape (T044/T045 precedent). Divergence, not duality, is the defect.

SURFACE: doctor/standalone now; ship-gate wiring lands WITH the cutover flip commit --
gating every unrelated ship on a known in-flight migration would be noise, and the
checker's own birth state (firing on live repo) proves the signal works.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_WINDOW_HOURS = 24.0
# Alert at 8x the measured starvation probe (523,272 bytes): growth, not existence.
DEFAULT_WAL_ALERT_BYTES = 4 * 1024 * 1024


def _mtime(p: Path) -> Optional[float]:
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _age(now: float, ts: float) -> str:
    h = (now - ts) / 3600.0
    return f"{h / 24.0:.1f}d" if h >= 48 else f"{h:.1f}h"


def classify(json_path: Path, db_path: Path, backend_env: str = "",
             window_hours: float = DEFAULT_WINDOW_HOURS,
             wal_alert_bytes: int = DEFAULT_WAL_ALERT_BYTES,
             now: Optional[float] = None) -> List[Dict[str, str]]:
    """Pure classification: [(severity, code, line)] as dicts. No printing, no exit --
    the doctor and the CLI wrap this; the pins call it directly."""
    now = time.time() if now is None else now
    json_path, db_path = Path(json_path), Path(db_path)
    jm, dm = _mtime(json_path), _mtime(db_path)
    findings: List[Dict[str, str]] = []

    if jm is not None and dm is not None:
        lag_h = abs(jm - dm) / 3600.0
        if lag_h > window_hours:
            stale_is_db = dm < jm
            stale_name, stale_ts = (db_path.name, dm) if stale_is_db else (json_path.name, jm)
            fresh_name, fresh_ts = (json_path.name, jm) if stale_is_db else (db_path.name, dm)
            authority_is_db = (backend_env or "").strip().lower() == "sqlite"
            findings.append({
                "severity": "fail", "code": "DIVERGENT-DUAL",
                "line": f"{stale_name} froze {_age(now, stale_ts)} ago while {fresh_name} "
                        f"moved {_age(now, fresh_ts)} ago (tear {lag_h / 24.0:.1f}d > "
                        f"{window_hours:.0f}h window). Two artifacts claim one state; "
                        f"finish the cutover or retire the twin.",
            })
            if authority_is_db == stale_is_db:
                findings.append({
                    "severity": "fail", "code": "STALE-AUTHORITY",
                    "line": f"the SELECTED backend ({'sqlite' if authority_is_db else 'file'}) "
                            f"is the frozen twin -- every read is served from a store that "
                            f"stopped moving {_age(now, stale_ts)} ago.",
                })

    wal = Path(str(db_path) + "-wal")
    try:
        wal_size = os.path.getsize(wal)
    except OSError:
        wal_size = 0
    if wal_size > wal_alert_bytes:
        findings.append({
            "severity": "fail", "code": "WAL-GROWTH",
            "line": f"{wal.name} at {wal_size} bytes (> {wal_alert_bytes}). A long-lived "
                    f"reader is starving the checkpoint (measured shape, 2026-07-26); run "
                    f"wal_checkpoint(TRUNCATE) after the reader releases.",
        })
    return findings


def _defaults() -> Dict[str, Path]:
    base = Path(os.getenv("AI_SETUP", r"E:\AI-Setup")) / "session_logs"
    return {"json": base / "store_state.json", "db": base / "store_state.db"}


def main(argv=None) -> int:
    d = _defaults()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=str(d["json"]))
    ap.add_argument("--db", default=str(d["db"]))
    ap.add_argument("--window-hours", type=float, default=DEFAULT_WINDOW_HOURS)
    ap.add_argument("--wal-alert-bytes", type=int, default=DEFAULT_WAL_ALERT_BYTES)
    a = ap.parse_args(argv)

    findings = classify(Path(a.json), Path(a.db),
                        backend_env=os.getenv("AKASHIC_STORE_BACKEND", ""),
                        window_hours=a.window_hours, wal_alert_bytes=a.wal_alert_bytes)
    print(f"# dual-authority check -- {a.json} vs {a.db}")
    if not findings:
        print("PASS: no dual-authority tear (single authority, or twins converging).")
        return 0
    for f in findings:
        print(f"{f['severity'].upper()} [{f['code']}]: {f['line']}")
    print(f"\n{len(findings)} finding(s). Divergence, not duality, is the defect: a pair "
          f"that moves together is a cutover; a pair that tears is an abandonment.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
