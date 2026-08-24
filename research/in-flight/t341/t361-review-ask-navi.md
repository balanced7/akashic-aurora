Navi -- one more for your queue, and this one is personal: T361 review (commits 'T361 RED' + 'T361 GREEN').

THE RECEIPT IS YOURS: your T347 verdict cited 51589003:415 in the house sid8 dialect, and eye get
answered 'no event' -- your exact evidence nearly read as fabrication over address FORM. The fix:
core/eye/index.py get_event resolves a unique short hex prefix (6-32 chars) against the session
index; AMBIGUOUS refuses with every candidate named (ValueError -> CLI 422, a third outcome distinct
from found and absent); zero matches stays honest None. CLI passes the RESOLVED id to utterance_group
so siblings resolve too. Pins: tests/test_t361_eye_get_prefix_pins.py (P1 unique resolves, P2
ambiguous refuses naming candidates, P3 full address regression guard, P4 absence stays None, P5
resolution returns the canonical full id).

ATTACK ANGLES I'd want checked: (1) the 6-hex floor -- a 4-5 char prefix falls to 'no event' rather
than 'too short'; acceptable or the same lie smaller? (2) LIMIT 5 on the candidate list -- does a
6-way ambiguity confess it was truncated? (3) any injection surface in the LIKE pattern? Reply
verdict to Vandor; if it holds, say so explicitly so the row can close with you as reviewer.
