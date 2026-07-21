"""W38 systemic-half pins — check_boundaries rule 7: register-at-ship-time for Redis families.

The mailbox gap (1472->1797 UNKNOWN keys) happened because a new key family shipped
without a roster entry and nobody looked until boot noise. This guard makes the class
un-shippable: a core/comm module that constructs `{ns}:<family>:...` must have <family>
classified (ephemeral roster OR durable allowlist). A new unclassified family FAILS the
boundary check -- the register-at-ship-time enforcement W38 asked for.

  P1  families extracted from ns-key literals ({ns}:, {_ns()}:, {self.ns}:)
  P2  an unregistered family is flagged; a registered one (control) is not
  P3  a durable-allowlisted family is not flagged
  P4  the LIVE core/comm tree has zero unregistered families (the guard is GREEN now --
      proving this slice also registered the 5 latent gaps it first surfaced)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.check_boundaries as cb


def test_p1_extract_families():
    text = ('a = f"{ns}:mailbox:pos:{agent}"\n'
            'b = f"{_ns()}:control:paused"\n'
            'c = f"{self.ns}:work:inbox:{a}"\n'
            'd = "not a key at all"\n')
    fams = cb._ns_families(text)
    assert fams == {"mailbox", "control", "work"}


def test_p2_unregistered_flagged_registered_not():
    # 'control' is in the ephemeral roster (*:control:*); 'zzznewfamily' is not
    text = 'x = f"{ns}:control:paused"\ny = f"{ns}:zzznewfamily:thing"\n'
    unreg = cb._unregistered_families(text)
    assert "zzznewfamily" in unreg and "control" not in unreg


def test_p3_durable_allowlist_passes():
    text = 'x = f"{ns}:events:raw:{a}"\n'   # durable Store family, not ephemeral-by-design
    assert cb._unregistered_families(text) == set(), \
        "durable families are classified by the File-family check, allowlisted here"


def test_p4_live_core_comm_is_clean():
    # the systemic proof: after this slice registered activity/pages/reply_seen/seat/
    # session, the live transport keyspace has NO unclassified family.
    from pathlib import Path
    offenders = {}
    commdir = cb.ROOT / "core" / "comm"
    for p in commdir.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        unreg = cb._unregistered_families(p.read_text(encoding="utf-8", errors="replace"))
        if unreg:
            offenders[p.name] = unreg
    assert offenders == {}, f"unregistered Redis families still live: {offenders}"
