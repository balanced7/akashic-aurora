"""W166 pins: a straggler is only a straggler if the packet is genuinely ABSENT from the lane.

MEASURED on prod, 2026-08-14, by comparing content hashes across the whole history rather
than trusting the alarm:

    bifrost:work:inbox:claude   191 entries with a sha
    bifrost:inbox:claude        192 entries with a sha
    on legacy but NOT on work     1     <- the only true failed lane write, ever
    on work but not on legacy     0

One. And a single drain had just reported TEN "LEGACY STRAGGLER(S) ... lane write failed
upstream (defect signal, investigate the sender side)".

THE BUG IS IN THE TEST, NOT THE TRANSPORT. `stragglers` is computed as "legacy messages whose
dedup key is not in `seen`", where `seen` holds the dedup keys from THIS batch's work read.
The two lanes are read from independently-positioned cursors -- measured skew that day: 33
unread on work, 49 unread on legacy -- so every packet the work read had already passed, or
had not yet reached, surfaced as a "failed lane write". It is reporting CURSOR SKEW as a
TRANSPORT DEFECT.

THE COST WAS REAL AND IT WAS PAID BY OTHER SEATS. kimi diagnosed the redelivery storm as
"sender-side (reply_id settle T026/RB-29, cursor T044/T045)" and adopted a hold-silence policy
on that basis; the alarm's own text says "investigate the sender side". A message that is
fluent, specific and actionable-sounding while being wrong ~90% of the time is the exact bar
this house adopted from Clarke & Dawe: it responds without answering.

WHAT THIS SLICE DOES NOT CHANGE: delivery. Returning the legacy copy is CORRECT -- at-least-
once, and RB-26 consumers are idempotent by design. Only the CLAIM is fixed. A diagnostic that
cries wolf is worse than no diagnostic, because it spends other people's attention.
"""
import pytest

from core.comm import bifrost_api as A


class _FakeStream:
    """Minimal stand-in: knows which shas exist on the lane."""

    def __init__(self, shas):
        self._shas = set(shas)

    def sha_on_lane(self, sha):
        return sha in self._shas


def test_c1_a_packet_present_on_the_lane_is_NOT_a_straggler():
    """The 90% case. It was written to the lane; the reader's cursor simply had not
    reached it, or had already passed it."""
    assert A.classify_straggler("abc", lane_has=lambda s: True) == "cursor-skew"


def test_c2_a_packet_ABSENT_from_the_lane_IS_a_straggler():
    """The 1-in-192 case: a genuine failed lane write, and the only one worth the alarm."""
    assert A.classify_straggler("abc", lane_has=lambda s: False) == "lane-write-failed"


def test_c3_an_unreadable_lane_reports_UNKNOWN_never_a_defect_claim():
    """If the membership check itself fails, the honest answer is 'cannot tell'. Guessing
    'lane write failed' here is how the original alarm earned its false positives."""
    def boom(_):
        raise RuntimeError("redis down")
    assert A.classify_straggler("abc", lane_has=boom) == "unknown"


def test_c4_a_packet_with_no_sha_is_unknown_not_a_defect():
    assert A.classify_straggler("", lane_has=lambda s: False) == "unknown"
    assert A.classify_straggler(None, lane_has=lambda s: False) == "unknown"


def test_c5_the_render_only_says_LANE_WRITE_FAILED_for_the_real_class():
    """The words that sent another seat's investigation to the wrong subsystem."""
    real = A.render_straggler_summary({"lane-write-failed": 1, "cursor-skew": 0, "unknown": 0})
    assert "lane write failed" in real.lower()
    assert "investigate the sender side" in real.lower()


def test_c6_pure_cursor_skew_does_NOT_claim_a_transport_defect():
    out = A.render_straggler_summary({"lane-write-failed": 0, "cursor-skew": 10, "unknown": 0})
    low = out.lower()
    assert "lane write failed" not in low
    assert "investigate the sender side" not in low
    assert "cursor" in low, "it should name the real condition, not merely stay quiet"


def test_c7_a_mixed_batch_reports_BOTH_counts_rather_than_the_louder_one():
    """Ten skew and one real failure is a different situation from eleven of either, and
    collapsing them is what hid the single genuine defect for a whole day."""
    out = A.render_straggler_summary({"lane-write-failed": 1, "cursor-skew": 10, "unknown": 2})
    assert "1" in out and "10" in out and "2" in out


def test_c8_an_all_clear_batch_renders_nothing():
    """Silence is correct when there is nothing to say -- the alarm should not fire at all
    on a healthy drain, which is the state it spent the day failing to recognise."""
    assert A.render_straggler_summary({"lane-write-failed": 0, "cursor-skew": 0,
                                       "unknown": 0}) == ""
