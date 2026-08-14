"""W162 pins: the T108 dedupe family is classified, and the spelling fork is named.

check_boundaries' redis-family rule fired for the FIRST time on 2026-08-14 (W161 put the repo
root on sys.path, so its `from core.comm.packet_spec import is_ephemeral_key` stopped failing
open). It surfaced four unregistered families. This slice closes the one that is unambiguously
live, and deliberately leaves three alone.

THE SPELLING FORK, which is the actual finding and the reason this needed reading rather than
registering:

    EPHEMERAL_PREFIXES contains  '*:seatseen:*'    -- 19 live keys in prod
    bus.py:971 constructs        '{ns}:seat_seen:' --  0 live keys

Two different families one underscore apart. `seatseen` is seat PRESENCE. `seat_seen` is the
T108 dual-delivery dedupe mark: a real consume does SET NX EX 1200 on the packet sha so the
legacy straggler copy of the same packet is dropped. Its zero live keys are not evidence of
dead code -- the TTL is 1200s, so an empty scan only means no straggler arrived in the last
twenty minutes, and a drain earlier that day reported exactly one.

EPHEMERAL, not durable: the family exists to expire. A 1200s TTL is the mechanism, so the
roster is its home and DURABLE_FAMILIES would be a lie about its lifetime.

WHAT THIS SLICE DELIBERATELY DOES NOT TOUCH. The other three -- role_queue.py's {ns}:role,
{ns}:rolefence, {ns}:rolegen -- carry NO TTL, have ZERO live keys, sit in a module
check_wiring lists as built-ahead with no production consumer, and that file is MODIFIED in
prod's working tree by another seat right now. Classifying the key families of a module
someone else is still writing is guessing on their behalf, and a wrong classification is
worse than an unregistered one: it would tell the heal machinery to treat their state as
expendable. Flagged to that lane instead.
"""
from core.comm.packet_spec import is_ephemeral_key


def test_f1_the_T108_dedupe_mark_is_classified_ephemeral():
    """bus.py:971's key. It expires by design (SET NX EX 1200), so the roster is correct
    and DURABLE_FAMILIES would misstate its lifetime."""
    assert is_ephemeral_key("bifrost:seat_seen:abc123") is True


def test_f2_the_namespaced_form_classifies_too():
    """Drills and tests flip BIFROST_NAMESPACE, so the pattern must not assume 'bifrost'."""
    assert is_ephemeral_key("test-w162:seat_seen:abc123") is True


def test_f3_the_OTHER_spelling_still_classifies_and_is_a_different_family():
    """seatseen is seat PRESENCE (19 live keys); seat_seen is the dedupe mark. Registering
    one must never have silently covered the other -- that is what let the fork survive."""
    assert is_ephemeral_key("bifrost:seatseen:claude#6f44fe5f") is True


def test_f4_the_three_role_families_are_still_UNREGISTERED_on_purpose():
    """A pin that records a deliberate omission, so the next reader knows it was a decision
    and not an oversight -- and so that whoever finishes role_queue.py sees the gate is
    waiting on THEM. If this pin starts failing, someone classified them: good, delete it."""
    for fam in ("role", "rolefence", "rolegen"):
        assert is_ephemeral_key(f"bifrost:{fam}:agent:msg") is False, (
            f"{fam} became ephemeral -- if that was deliberate, delete this pin and lower "
            f"the check_boundaries baseline in the same commit")
