"""T108 S4 reaper hardening pins -- RED against 2692203.

The original S4 pin proves one happy path: a witnessed-dead seat with one message is
re-homed once. These pins cover the failure boundaries an independent Codex + Kimi
fence reproduced against the live tree:

  H1  a failed send never becomes a permanent "already re-homed" marker;
  H2  recovered work preserves the original asker and remains answerable;
  H3  a page limit does not make item 51 unreachable forever;
  H4  the original clock actually governs freshness after re-home.
  H5  a full-session tombstone remains connected to its sid8 roster row;
  H6  the observational doctor does not mutate mail by running the reaper.
  H7  two live reapers serialize one message without duplicating the send.
  H8  the persistent reap cursor never advances across a failed delivery hole.

One runner-wide identity residual is pinned strict-xfail below: same-role work sent
to a particular session (for example Claude -> Claude#dead) must be distinguished
from an ordinary self echo after recovery.

They deliberately assert properties at the consumer boundary, not log text. Namespaces
are unique and exact-cleaned; no shared cursor or canonical task state is touched.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from core.comm import packet_spec, reaper, roster
from core.comm.bus import Bus
from scripts.bifrost_runner import should_answer


AGENT = "s4hardening"
SID = "deadbeef-0000-0000-0000-000000000000"


@pytest.fixture
def isolated_bus():
    ns = "t108s4h" + uuid.uuid4().hex[:10]
    saved = {key: os.environ.get(key) for key in (
        "BIFROST_NAMESPACE", "BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID")}
    os.environ["BIFROST_NAMESPACE"] = ns
    os.environ.pop("BIFROST_INCARNATION", None)
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    bus = Bus("s4-test", namespace=ns)
    if not bus.online:
        pytest.skip("Redis unavailable")
    try:
        yield ns, bus._client
    finally:
        keys = list(bus._client.scan_iter(match=f"{ns}:*"))
        if keys:
            bus._client.delete(*keys)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _seat_stream(ns: str) -> str:
    return f"{ns}:inbox:{AGENT}#{SID[:8]}"


def _add_seat_packet(client, ns: str, content: str, *, frm: str = "real_sender",
                     stream_id: str = "*", sent_at: object | None = None) -> str:
    meta = {"to_incarnation": SID}
    env = {
        "frm": frm,
        "to": AGENT,
        "kind": "request",
        "content": json.dumps(content),
        "ts": str(sent_at if sent_at is not None else time.time()),
        "meta": json.dumps(meta),
        "parts": "[]",
    }
    length, sha = packet_spec.compute_len_sha(env)
    packet_spec.stamp(env, length=length, sha=sha)
    return str(client.xadd(_seat_stream(ns), env, id=stream_id))


def _make_dead(client, ns: str) -> None:
    roster.heartbeat(ns, AGENT, SID[:8], phase="working", client=client)
    client.delete(f"{ns}:worklive:{AGENT}#{SID[:8]}")
    rows = [row for row in roster.roster(ns, client=client)
            if row.get("seat") == f"{AGENT}#{SID[:8]}"]
    assert rows and rows[0].get("state") == "DEAD"


def _role_rehome_fields(client, ns: str, original_mid: str):
    rows = client.xrange(f"{ns}:inbox:{AGENT}", min="-", max="+") or []
    for _mid, fields in rows:
        try:
            meta = json.loads(fields.get("meta") or "{}")
        except (TypeError, ValueError):
            meta = {}
        if str(meta.get("original_mid") or "") == str(original_mid):
            return dict(fields)
    return None


def test_h1_failed_send_does_not_poison_retry_marker(isolated_bus, monkeypatch):
    """Claim-before-act may serialize reapers, but a failed act must release its claim."""
    ns, client = isolated_bus
    original_mid = _add_seat_packet(client, ns, "retry-me")
    _make_dead(client, ns)
    real_send = Bus.send
    monkeypatch.setattr(Bus, "send", lambda self, *args, **kwargs: None)

    first = reaper.reap(ns, client=client)
    mark = f"{ns}:rehomed:{AGENT}#{SID[:8]}:{original_mid}"

    assert first == [], (
        "a send returning None was reported as a successful re-home; success receipts "
        "must contain only delivered work")
    assert not client.exists(mark), (
        "the failed send left the NX idempotence mark behind, so every later pass will "
        "skip the still-stranded message")

    monkeypatch.setattr(Bus, "send", real_send)
    second = reaper.reap(ns, client=client)
    assert len(second) == 1 and second[0].get("rehomed_mid"), (
        "a transient send failure must remain retryable on the next pass")


def test_h2_rehome_preserves_original_asker_and_is_answerable(isolated_bus):
    """Recovery must not turn somebody else's request into inert self-mail."""
    ns, client = isolated_bus
    original_mid = _add_seat_packet(client, ns, "answer-me", frm="real_sender")
    _make_dead(client, ns)

    records = reaper.reap(ns, client=client)
    fields = _role_rehome_fields(client, ns, original_mid)

    assert records and fields, "the recovered packet must be present on the role delivery path"
    frm = str(fields.get("frm") or "")
    kind = str(fields.get("kind") or "")
    assert frm == "real_sender", (
        f"re-home rewrote the asker from real_sender to {frm!r}; replies and expectations "
        "would now point at the wrong actor")
    assert should_answer(kind, frm, AGENT), (
        "every runner rejects self-originated mail; recovered work must remain answerable")


def test_h3_repeated_passes_progress_beyond_first_page(isolated_bus, monkeypatch):
    """Marked entries on page one must not permanently hide unmarked page two."""
    ns, client = isolated_bus
    original_ids = [_add_seat_packet(client, ns, f"job-{i:02d}") for i in range(55)]
    _make_dead(client, ns)
    serial = iter(range(1000))
    monkeypatch.setattr(
        Bus, "send",
        lambda self, *args, **kwargs: f"rehomed-{next(serial)}")

    first = reaper.reap(ns, client=client, limit_per_seat=50)
    second = reaper.reap(ns, client=client, limit_per_seat=50)
    third = reaper.reap(ns, client=client, limit_per_seat=50)

    assert len(first) == 50
    assert len(second) == 5, (
        "the second pass reread the same 50 marked entries and never reached item 51")
    assert third == []
    assert {r["original_mid"] for r in first + second} == set(original_ids)
    cursor_key = f"{ns}:cursor:seat:{AGENT}#{SID[:8]}"
    assert client.hget(cursor_key, "reaper") == original_ids[-1], (
        "pagination reached item 55 but did not persist progress; every later tick would "
        "rescan the dead seat's whole history")


def test_h4_original_clock_drives_stale_gate_after_rehome(isolated_bus):
    """Carrying original_ts as dead metadata is not clock preservation."""
    ns, client = isolated_bus
    now_ms = int(time.time() * 1000)
    old_ms = now_ms - (7 * 3600 * 1000)
    original_ts = datetime.fromtimestamp(old_ms / 1000.0, timezone.utc).isoformat()
    original_mid = _add_seat_packet(
        client, ns, "old-request", stream_id=f"{old_ms}-0", sent_at=original_ts)
    _make_dead(client, ns)

    records = reaper.reap(ns, client=client)
    messages = Bus(AGENT, namespace=ns).inbox(limit=20, advance=False)
    recovered = [m for m in messages
                 if str((getattr(m, "meta", {}) or {}).get("original_mid") or "")
                 == original_mid]
    assert records and recovered, "precondition: the old request must be re-homed"

    fresh, stale_asks, stale_skips = packet_spec.partition_stale(
        recovered, now_ms=int(time.time() * 1000), stale_ms=6 * 3600 * 1000)
    assert not fresh and len(stale_asks) == 1 and not stale_skips, (
        "the re-home got a fresh stream id and bypassed the 6h stale-ask gate; "
        "meta.original_ts/original_mid is currently ignored downstream")


def test_h5_full_session_tombstone_reaches_sid8_roster_row(isolated_bus):
    """T086 ends a full session id; the seat directory must not discard that identity."""
    ns, client = isolated_bus
    original_mid = _add_seat_packet(client, ns, "ended-session")
    roster.heartbeat(ns, AGENT, SID, phase="working", client=client)
    client.set(f"{ns}:session:ended:{SID}", str(time.time()), ex=3600)

    rows = [row for row in roster.roster(ns, client=client)
            if row.get("seat") == f"{AGENT}#{SID[:8]}"]
    assert rows and rows[0].get("state") == "LIVE", (
        "precondition: worklive is still present, so only the durable tombstone proves death")
    assert rows[0].get("full_sid") == SID, (
        "the roster retained only sid8, making the full-id T086 tombstone unreachable")

    records = reaper.reap(ns, client=client)
    assert [record.get("original_mid") for record in records] == [original_mid], (
        "an ended session remained unreapable because _provably_dead checked its sid8 "
        "against a tombstone written under the full session id")


def test_h6_doctor_is_observational_and_does_not_reap(monkeypatch, capsys):
    """A diagnostic read must not secretly become the writer that moves durable mail."""
    import agent_cli
    from core.comm import doctor

    calls = []
    monkeypatch.setattr(doctor, "examine_fleet",
                        lambda agents, page_notes=False: {
                            "agents": [], "findings": [], "summary": "doctor: healthy"})
    monkeypatch.setattr(doctor, "known_agents", lambda: [])
    monkeypatch.setattr(doctor, "examine_services", lambda: [])
    monkeypatch.setattr(reaper, "reap", lambda ns: calls.append(ns) or [])

    rc = agent_cli.cmd_doctor(SimpleNamespace(
        agents=None, page=False, progress=False, json=True))

    assert rc == 0
    assert calls == [], (
        "doctor invoked the S4 reaper while claiming to diagnose fleet state; "
        "mail movement belongs behind the explicit roster --reap maintenance action")
    capsys.readouterr()


def test_h7_live_reapers_serialize_one_send(isolated_bus, monkeypatch):
    """The transient claim closes the ordinary two-writer race without poisoning retries."""
    ns, client = isolated_bus
    original_mid = _add_seat_packet(client, ns, "race-me")
    _make_dead(client, ns)
    send_started = threading.Event()
    release_send = threading.Event()
    sends = []

    def slow_send(self, *args, **kwargs):
        sends.append((self.agent_id, args))
        send_started.set()
        assert release_send.wait(timeout=3), "test harness failed to release the first send"
        return "rehomed-once"

    monkeypatch.setattr(Bus, "send", slow_send)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(reaper.reap, ns, client=client)
        assert send_started.wait(timeout=3), "precondition: first reaper must hold the claim"
        second = pool.submit(reaper.reap, ns, client=client)
        second_records = second.result(timeout=3)
        release_send.set()
        first_records = first.result(timeout=3)

    assert len(sends) == 1, "two live reapers both sent the same stranded packet"
    assert second_records == []
    assert [record.get("original_mid") for record in first_records] == [original_mid]


def test_h8_reap_cursor_never_crosses_a_failed_hole(isolated_bus, monkeypatch):
    """Later successes stay reachable, but cannot make an earlier failed item disappear."""
    ns, client = isolated_bus
    original_ids = [_add_seat_packet(client, ns, f"hole-{i}") for i in range(3)]
    _make_dead(client, ns)
    calls = iter([None, "later-1", "later-2"])
    monkeypatch.setattr(Bus, "send", lambda self, *args, **kwargs: next(calls))

    first = reaper.reap(ns, client=client)
    cursor_key = f"{ns}:cursor:seat:{AGENT}#{SID[:8]}"

    assert [record.get("original_mid") for record in first] == original_ids[1:]
    assert str(client.hget(cursor_key, "reaper") or "0") == "0", (
        "the reap cursor crossed a failed first message and made its retry unreachable")

    monkeypatch.setattr(Bus, "send", lambda self, *args, **kwargs: "retried")
    second = reaper.reap(ns, client=client)

    assert [record.get("original_mid") for record in second] == [original_ids[0]]
    assert client.hget(cursor_key, "reaper") == original_ids[-1], (
        "after the hole closed, the cursor did not compact across already-finished later work")


@pytest.mark.xfail(strict=True, reason=(
    "PRE-REGISTERED identity residual: preserving frm is insufficient when the original "
    "ask was same-role but cross-session. Runners need rehomed_from-aware echo filtering "
    "and original_mid logical reply identity across every provider."))
def test_h9_self_directed_seat_work_remains_answerable_after_rehome(isolated_bus):
    """The canonical Claude -> Claude#dead recovery is work, not an echo."""
    ns, client = isolated_bus
    original_mid = _add_seat_packet(client, ns, "same-role-work", frm=AGENT)
    _make_dead(client, ns)

    records = reaper.reap(ns, client=client)
    fields = _role_rehome_fields(client, ns, original_mid)
    assert records and fields
    meta = json.loads(fields.get("meta") or "{}")

    assert should_answer(
        str(fields.get("kind") or ""), str(fields.get("frm") or ""), AGENT, meta)
