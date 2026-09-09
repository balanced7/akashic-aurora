"""sid8 DISCRIMINATES -- RED first (defer 7e2670d54e, filed 2026-08-26).

WHY: every per-seat key is `<agent>#<sid8>`, and six call sites each derived sid8 as an
independent `str(sid)[:8]`. That slice is only a discriminator while the id's entropy sits
in its head. DSH session ids are `session-<uuid>`, so for every web seat the head is the
literal scheme word: bifrost:worklive:dsh_agent#session- (live on the shared Redis as the
seatseen witness `bifrost:seatseen:dsh_agent#session-`). Two concurrent web seats shared ONE
presence row, and -- worse than filed -- go_offline for the departing seat DELETED the
living seat's worklive key, so a goodbye rendered a healthy peer OFFLINE. The bus plane has
the same slice at _my_sid8/to_incarnation, so exporting BIFROST_INCARNATION=session-<uuid>
(the documented advice) collides the seat inbox and the seat cursor the same way.

THE GUARANTEE THESE PIN: two distinct session ids OF THE FLEET'S SHAPES (bare uuid, '<pid>-<agent>',
8-char pins, 'seat-NNNN', and any '<scheme-words>-<uuid>' id such as 'session-<uuid>' or
'dsh-session-<uuid>') WHOSE 8-CHARACTER ENTROPY HEADS DIFFER always map to two distinct incarnation
keys, on every plane that keys by sid8 -- roster (worklive/seatseen), seat inbox, seat
cursor, and the eye's standpoint -- through ONE derivation, core.comm.bus.sid8, that is
byte-identical for every existing fleet shape (bare UUIDs, '<pid>-<agent>', 8-char pins,
'seat-0001') and idempotent, so every existing `<AGENT>#<SID[:8]>` pin and the operator
dialect (boot prints 'session ed728d23'; bifrost-send --to-incarnation <sid8>) keep working.

  P0  DERIVATION: one shared sid8(); UUIDs unchanged, scheme-prefixed hex ids yield their
      hex head, idempotent, 'seat-0001' (4 hex after the dash) untouched.
  P1  TWO ROWS: two 'session-<uuid>' seats heartbeat -> two roster rows, sid8 = each hex
      head, never the scheme word.
  P2  A GOODBYE IS NOT A KILL: go_offline for seat A leaves seat B LIVE.
  P3  BUS: BIFROST_INCARNATION='session-<uuid>' -> _my_sid8() and Bus(incarnation=...) are
      the hex head.
  P4  EYE: whoami() keys the standpoint by the hex head -- two web seats never share one.
  P5  DELIVERY: directed mail to 'session-<A>' reaches seat A and is invisible to seat B.

Namespace-isolated (T039 precedent); throwaway namespaces are swept at teardown so their
24h seatseen witnesses do not outlive the run on the shared Redis.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT = "dsh_agent"
A_HEX = "aaaa1111-2222-3333-4444-555555555555"
B_HEX = "bbbb6666-7777-8888-9999-000000000000"
SID_A = "session-" + A_HEX          # the DSH shape, verbatim (session-<uuid>)
SID_B = "session-" + B_HEX
A8, B8 = A_HEX[:8], B_HEX[:8]

_MINTED = []


def _client():
    from core.comm.bus import _connect
    c = _connect()
    if c is None:
        pytest.skip("Redis not running -- these pins need the live bus")
    return c


def _ns(tag: str) -> str:
    ns = f"t7e2670{tag}{uuid.uuid4().hex[:6]}"
    _MINTED.append(ns)
    return ns


@pytest.fixture(autouse=True)
def _restore_env_and_sweep_keys():
    """These pins impersonate seats by mutating process env; never leak that to later tests
    (the T069 order-coupling class). And sweep the throwaway namespaces afterwards."""
    saved = {k: os.environ.get(k)
             for k in ("BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID", "BIFROST_NAMESPACE")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        from core.comm.bus import _connect
        c = _connect()
        for ns in _MINTED:
            keys = list(c.keys(f"{ns}:*")) if c is not None else []
            if keys:
                c.delete(*keys)
    except Exception:
        pass
    _MINTED.clear()


def _rows(ns):
    from core.comm import roster
    return [r for r in roster.roster(ns) if r.get("agent") == AGENT]


def _as_seat(sid: str) -> None:
    os.environ["BIFROST_INCARNATION"] = sid
    os.environ["CLAUDE_CODE_SESSION_ID"] = sid


def test_p0_one_derivation_byte_identical_for_every_existing_shape():
    from core.comm.bus import sid8   # RED at HEAD: the shared derivation does not exist
    plain = "ed728d23-1f2e-4a5b-8c9d-0e1f2a3b4c5d"
    assert sid8(plain) == plain[:8], "a bare UUID must derive exactly as today ([:8])"
    assert sid8("aaaa1111") == "aaaa1111", "an 8-char pin sid is its own sid8"
    assert sid8("3708-deepseek") == "3708-dee", "'<pid>-<agent>' runner ids are unchanged"
    assert sid8("seat-0001") == "seat-000", (
        "a word-dash prefix with fewer than 8 hex chars after it is NOT a scheme prefix "
        "(tests/test_dsh_contract.py pins dsh_agent#seat-000)")
    assert sid8("deadbeef-cafe1234abcd") == "deadbeef", (
        "a word made only of hex digits is a hex HEAD, not a scheme word: the derivation "
        "must never discard entropy (tests/test_t108_s4_reaper_hardening.py pins deadbeef-...)")
    assert sid8(SID_A) == A8, f"'session-<uuid>' must yield the uuid's hex head, got {sid8(SID_A)!r}"
    assert sid8(sid8(SID_A)) == sid8(SID_A), "idempotent: a tail parsed from a key derives to itself"
    assert sid8("") == "" and sid8(None) == "", "empty in, empty out (no seat -> no key)"


def test_p1_two_prefixed_seats_render_two_rows():
    from core.comm import roster
    ns = _ns("p1")
    _client()
    assert roster.heartbeat(ns, AGENT, SID_A, phase="idle")["ok"]
    assert roster.heartbeat(ns, AGENT, SID_B, phase="idle")["ok"]
    rows = _rows(ns)
    got = sorted(r["sid8"] for r in rows)
    assert len(rows) == 2, (
        f"CONSTANT DISCRIMINATOR: two 'session-<uuid>' seats rendered {len(rows)} row(s) "
        f"with sid8 {got} -- the [:8] slice of a scheme-prefixed id is the scheme word, so "
        f"both seats keyed one presence row (defer 7e2670d54e)")
    assert got == sorted([A8, B8]), f"sid8 must be each seat's hex head, got {got}"
    assert all(r["state"] == "LIVE" for r in rows), f"both seats just beat: {rows}"
    assert not any(r["sid8"] == "session-" for r in rows)


def test_p2_a_goodbye_never_erases_the_living_seat():
    from core.comm import roster
    ns = _ns("p2")
    c = _client()
    roster.heartbeat(ns, AGENT, SID_A, phase="idle")
    roster.heartbeat(ns, AGENT, SID_B, phase="idle")
    assert roster.go_offline(ns, AGENT, SID_A)["ok"]
    rows = {r["sid8"]: r["state"] for r in _rows(ns)}
    assert rows.get(B8) == "LIVE", (
        f"A DEPARTING SEAT ERASED A LIVING ONE: go_offline(A) deleted the key seat B beats "
        f"on, so B renders {rows.get(B8) or rows} -- worse than the defer filed (roster {rows})")
    assert rows.get(A8) == "OFFLINE", f"A declared its departure and must render OFFLINE: {rows}"
    assert c.exists(f"{ns}:worklive:{AGENT}#{B8}"), "B's own worklive key must survive A's goodbye"


def test_p3_bus_incarnation_is_the_hex_head_not_the_scheme_word():
    from core.comm.bus import Bus
    _as_seat(SID_A)
    assert Bus._my_sid8() == A8, (
        f"_my_sid8() under BIFROST_INCARNATION={SID_A!r} is {Bus._my_sid8()!r}: the seat "
        f"inbox and seat cursor of EVERY web seat collide on '#session-'")
    b = Bus(AGENT, namespace=_ns("p3"), promote=False, incarnation=SID_A)
    assert b._incarnation == A8, f"Bus(incarnation=...) lane cursor key: {b._incarnation!r}"
    assert b._seat_cursor_key(Bus._my_sid8()).endswith(f"#{A8}")


def test_p4_eye_standpoint_is_per_incarnation():
    from core.eye.position import whoami
    _as_seat(SID_A)
    me = whoami(AGENT)
    _as_seat(SID_B)
    other = whoami(AGENT)
    assert me == f"{AGENT}#{A8}", f"the eye keys a standpoint by the hex head, got {me!r}"
    assert other == f"{AGENT}#{B8}" and other != me, (
        f"two web seats must never share one standpoint (they would poison each other's "
        f"`since=`): {me!r} vs {other!r}")


def test_p5_directed_mail_to_a_prefixed_seat_routes_by_hex_head():
    from core.comm.bus import Bus
    ns = _ns("p5")
    _client()
    sender = Bus("deepseek", namespace=ns, promote=False)
    body = f"for-seat-A-{ns}"
    assert sender.send(AGENT, "note", body, meta={"to_incarnation": SID_A})

    _as_seat(SID_B)                                  # the theft ordering: B drains first
    seen_b = " | ".join(str(m.content) for m in Bus(AGENT, namespace=ns, promote=False).inbox(advance=True))
    assert body not in seen_b, (
        f"TWIN THEFT: seat B consumed mail directed to seat A -- both seats derive the same "
        f"'#session-' seat stream, so B's read IS A's read. B saw: {seen_b[:200]}")

    _as_seat(SID_A)
    seen_a = " | ".join(str(m.content) for m in Bus(AGENT, namespace=ns, promote=False).inbox(advance=True))
    assert body in seen_a, f"seat A must still receive its own directed mail: {seen_a[:200] or '(nothing)'}"


# ---------------------------------------- 6: the reviewers' cases (Heimdall fan-out db2abef2, 2026-09-08)
def test_p6_one_derivation_lives_in_seat_identity_and_bus_reexports_it():
    """Lens 2 refused to approve blind: every key builder and compare must speak ONE rule.
    seat_identity is the lowest layer (no bus dependency), so the rule lives there; bus.sid8
    IS that function, and the fallback id a hook mints for an unbound DSH seat carries the
    hex head, never the scheme word (two unbound web seats must not share 'unknown-session-')."""
    from core.comm import seat_identity as si
    from core.comm import bus as busmod
    assert busmod.sid8 is si.sid8
    uid = si.unknown_id("session-7ed91e83-1111-2222-3333-444444444444")
    assert uid.endswith("7ed91e83") and not uid.endswith("session-"), uid


def test_p7_a_nested_scheme_strips_to_the_hex_head():
    """Lens 0: 'dsh-session-<uuid>' collided under a single-word strip; every scheme word goes."""
    from core.comm.seat_identity import sid8
    full = "7ed91e83-1111-2222-3333-444444444444"
    assert sid8("dsh-session-" + full) == "7ed91e83"
    assert sid8("session-" + full) == "7ed91e83"
    assert sid8("SESSION-" + full) == "7ed91e83"
    assert sid8(sid8("dsh-session-" + full)) == "7ed91e83"


def test_p8_too_little_entropy_after_a_scheme_is_a_documented_non_shape_not_a_silent_collision():
    """Lens 0 named 'session-', 'session-abc', 'session-1234567': fewer than 8 hex characters after
    the scheme cannot key a seat, so the rule keeps the plain head slice -- byte-identical to the
    old behaviour, and stated here as the limit of the guarantee rather than hidden inside it."""
    from core.comm.seat_identity import sid8
    for sid in ("session-", "session-abc", "session-1234567"):
        assert sid8(sid) == str(sid)[:8], sid
    assert sid8("ab-cdef1234-5678") == "ab-cdef1", "a pure-hex 'word' is entropy, never a scheme"
    assert sid8("") == "", "an empty id is no seat and no key; the loud fallback lives in unknown_id()"
    from core.comm.seat_identity import unknown_id
    assert unknown_id("") == "unknown-unknown", "the unbound fallback stays loud, as before"


def test_p9_a_scheme_before_a_bare_8_hex_token_is_not_stripped_because_it_would_collide_with_a_pin():
    """Heimdall lens 0, round 2: sid8('session-aaaa1111') must not equal sid8('aaaa1111') -- an 8-char
    pin is a fleet shape, so a scheme is stripped only when a UUID-shaped tail (8 hex THEN a hyphen)
    follows. The real DSH id 'session-<uuid>' still strips; the bare-token form keeps its head."""
    from core.comm.seat_identity import sid8
    assert sid8("session-aaaa1111") == "session-"
    assert sid8("session-aaaa1111") != sid8("aaaa1111") == "aaaa1111"
    assert sid8("session-aaaa1111-2222-3333-4444-555555555555") == "aaaa1111"


def test_p10_the_sync_verb_derives_its_mailbox_incarnation_from_the_env_through_the_one_rule(monkeypatch):
    """Heimdall lens 2, round 2: cmd_bifrost_sync trusted a raw AKASHIC_SESSION8; a full 'session-<uuid>'
    there would hand the mailbox an incarnation that disagrees with every key builder."""
    import agent_cli
    full = "session-7ed91e83-1111-2222-3333-444444444444"
    assert agent_cli._sid8_of(full) == "7ed91e83"
    src = open(agent_cli.__file__, encoding="utf-8", errors="replace").read()
    assert '_inc = (_sid8_of(os.environ.get("AKASHIC_SESSION8"))' in src


def test_p11_the_discriminator_is_eight_characters_of_entropy_not_the_whole_id():
    """Heimdall final check (b87851bb): a scheme-prefixed uuid and a bare uuid with the SAME 8-hex
    head share a key. So do two bare uuids with the same head, and always have -- the incarnation
    discriminator is the 8-character entropy head, not an injective function of the id. The
    guarantee above is scoped to ids whose entropy heads differ; this pin states the limit."""
    from core.comm.seat_identity import sid8
    assert sid8("session-aaaa1111-2222-3333-4444-555555555555") == sid8("aaaa1111-9999-8888-7777-666666666666") == "aaaa1111"
    assert sid8("aaaa1111-0000-1111-2222-333333333333") == sid8("aaaa1111-9999-8888-7777-666666666666"), "pre-existing, by design"
