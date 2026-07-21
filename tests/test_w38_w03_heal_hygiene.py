"""W38 + W03 pins — the heal line stops shouting a subsystem's projection at fresh seats.

W38 (register-at-ship-time, the systemic wish; here its first concrete offender): the T095
mailbox is a SHADOW INDEX over the append-only lanes ("OBSERVATIONAL ONLY ... writes nothing
outside {ns}:mailbox:*", mailbox.py:1/16) -- a regenerable projection, ephemeral-by-design.
It was never registered in EPHEMERAL_PREFIXES, so its keys fell through to UNKNOWN and grew
every boot (1472 -> 1797 across one night, kimi's re-bite). Registering the family is the fix.

W03 (severity scope): the heal render's UNKNOWN line said "INVESTIGATE" in caps, reading as
the FRESH SEAT's task when it is fleet-hygiene about shared Redis/File divergence. Tag it.

  P1  a bifrost:mailbox:* key classifies EPHEMERAL (is_ephemeral_key True)
  P2  in the heal render, mailbox keys land in the QUIET ephemeral line, not UNKNOWN
  P3  a genuinely-unknown key still lands LOUD in UNKNOWN (no over-broad silencing)
  P4  every heal line carries a [fleet-hygiene] scope tag (W03: not the seat's task)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.packet_spec import is_ephemeral_key
from core.foundation.store import HybridStore


def test_p1_mailbox_family_is_ephemeral():
    assert is_ephemeral_key("bifrost:mailbox:answered")
    assert is_ephemeral_key("bifrost:mailbox:msg:claude:abc123")
    assert is_ephemeral_key("bifrost:mailbox:evicted:deepseek")
    assert is_ephemeral_key("bifrost:mailbox:z:kimi")


def test_p2_mailbox_keys_render_quiet():
    orphans = ["bifrost:mailbox:answered", "bifrost:mailbox:msg:claude:aaa",
               "bifrost:mailbox:pos:claude"]
    lines = HybridStore._render_orphans(orphans, file_fams=set())
    joined = "\n".join(lines)
    assert "UNKNOWN" not in joined, "a regenerable projection is never the loud signal"
    assert any("transport/control/telemetry" in l and "mailbox" in l for l in lines), \
        "mailbox keys land in the quiet ephemeral line"


def test_p3_genuine_unknown_still_loud():
    orphans = ["bifrost:mailbox:answered", "bifrost:genuinely_new_thing:x"]
    lines = HybridStore._render_orphans(orphans, file_fams=set())
    joined = "\n".join(lines)
    assert "1 UNKNOWN" in joined and "genuinely_new_thing" in joined, \
        "registering mailbox must not silence a real orphan"


def test_p4_heal_lines_carry_scope_tag():
    orphans = ["bifrost:genuinely_new_thing:x", "bifrost:mailbox:answered"]
    lines = HybridStore._render_orphans(orphans, file_fams=set())
    assert lines and all("[fleet-hygiene]" in l for l in lines), \
        "W03: heal lines are fleet-hygiene, never the fresh seat's task"
