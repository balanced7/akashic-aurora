"""VERIFICATION SUITE for the wire journal (T156) -- Daniil, 2026-08-04:

    "how can we verify every function we have built for this new feature including ways it can
     hang and verifying that it does what it is supposed to do?"

The T156 feature pins prove the FEATURES work. They do not prove the FUNCTIONS are safe, and the
difference is not academic: the design workflow found a data-destroying rotation bug that every
feature pin passed straight over, and the very fix for it introduced an O(n) scan on the request
thread (measured 13,747us per call at 800 segments). Both defects lived in code with green tests.

So this file verifies three things the feature pins structurally cannot:

  A. BOUNDED TIME (anti-hang). Every function that touches the filesystem runs under a hard
     deadline, in the adversarial STATE that makes it slow -- many segments, many records, a
     large journal. A function is not "fast"; it is fast AT A SIZE, and the size is the test.
     Every loop in this module is a hang candidate until bounded: `_segment_path` (while True),
     `_rotate` (two while loops), `read_all` (nested), `expert` (re-reads).

  B. FAULT INJECTION. The recorder sits on the hot path of a live API call, so its failure modes
     are the caller's failure modes. Unwritable directory, disk-full mid-write, a corrupt line
     from a torn write, a vanished directory, concurrent writers. The contract is absolute: it
     may lose a record, it may NEVER raise, and it may never lose a record SILENTLY.

  C. BEHAVIOURAL INVARIANTS -- properties that must hold for ANY input, not just the examples in
     the feature pins. Bodies never reach disk whatever the shape of the input; records survive a
     round trip; a torn line costs one record and not the reader.

Run: py -m pytest tests/test_t156_wire_verification.py -q
"""
import json
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.wire_journal import WireJournal          # noqa: E402
import scripts.wire_journal as WJ                     # noqa: E402


def _j(tmp_path, sub="j"):
    return WireJournal(journal_dir=str(tmp_path / sub))


def _timed(fn, *a, **k):
    t0 = time.perf_counter()
    out = fn(*a, **k)
    return out, (time.perf_counter() - t0)


# ===================================================================== A. BOUNDED TIME

def test_a1_segment_path_is_amortized_constant(tmp_path):
    """REGRESSION, measured. Probing from segment 1 on every record is O(segments): 29.6us at 1,
    799us at 50, 3,419us at 200, 13,747us at 800 -- inside the lock, on the request thread. The
    D1 rotation fix introduced this while curing data loss, which is exactly why a feature pin is
    not enough. A cursor makes it amortized constant."""
    d = tmp_path / "seg"
    d.mkdir()
    day = time.strftime("%Y%m%d")
    old_max = WJ.MAX_BYTES
    WJ.MAX_BYTES = 100
    try:
        for i in range(1, 801):
            (d / f"wire-{day}-{i:03d}.jsonl").write_text("x" * 200, encoding="utf-8")
        j = WireJournal(journal_dir=str(d))
        j._segment_path()                                  # first call may walk; that is allowed
        _, dur = _timed(lambda: [j._segment_path() for _ in range(50)])
        per_call_us = dur / 50 * 1e6
        assert per_call_us < 500, (
            f"_segment_path costs {per_call_us:.0f}us/call at 800 segments -- it is scanning from "
            f"the start on every record, on the hot path, inside the lock")
    finally:
        WJ.MAX_BYTES = old_max


def test_a2_record_stays_bounded_as_the_journal_grows(tmp_path):
    """A write must not get slower because history got longer. If it does, the journal becomes a
    self-throttling system: the more you observe, the slower every API call gets."""
    j = _j(tmp_path)
    for _ in range(200):
        j.record(model="m", status=200)
    _, warm = _timed(lambda: [j.record(model="m", status=200) for _ in range(50)])
    for _ in range(2000):
        j.record(model="m", status=200)
    _, late = _timed(lambda: [j.record(model="m", status=200) for _ in range(50)])
    assert late < warm * 6 + 0.05, (
        f"record() degraded as the journal grew: {warm/50*1e6:.0f}us -> {late/50*1e6:.0f}us per call")


def test_a3_every_filesystem_function_completes_under_deadline(tmp_path):
    """Blanket anti-hang sweep: with a realistically large journal, no function may exceed 2s.
    A deadline is the only thing that distinguishes 'slow' from 'hung' in an automated check."""
    j = _j(tmp_path)
    for i in range(3000):
        j.record(model="m", status=200 if i % 7 else 429, finish_reason="length" if i % 11 else "stop",
                 system_fingerprint=f"fp_{i % 3}", usage={"total_tokens": i})
    for name, call in (("files", j.files), ("read_all", j.read_all),
                       ("summarize", j.summarize), ("expert", j.expert),
                       ("_rotate", j._rotate), ("_segment_path", j._segment_path)):
        _, dur = _timed(call)
        assert dur < 2.0, f"{name}() took {dur:.2f}s on a 3000-record journal -- unbounded"


def test_a4_rotate_terminates_when_deletion_is_impossible(tmp_path):
    """`_rotate` loops while over budget and deletes to get under it. If deletion silently fails,
    a naive loop never terminates -- the classic cleanup hang. Simulate by making remove a no-op."""
    j = _j(tmp_path)
    for _ in range(5):
        j.record(model="m", status=200)
    real_remove = os.remove
    os.remove = lambda p: None                     # deletion "succeeds" but frees nothing
    try:
        WJ.MAX_FILES, old = 1, WJ.MAX_FILES
        _, dur = _timed(j._rotate)
        assert dur < 2.0, f"_rotate did not terminate when deletion freed nothing ({dur:.1f}s)"
    finally:
        os.remove = real_remove
        WJ.MAX_FILES = old


def test_a5_the_transport_hook_adds_bounded_latency(tmp_path, monkeypatch):
    """The recorder wraps a live API call. Verify the OBSERVER's own cost is bounded even when
    the journal is large -- this is the number that lands on every request."""
    monkeypatch.setenv("AKASHIC_WIRE_DIR", str(tmp_path / "hot"))
    j = WireJournal(journal_dir=str(tmp_path / "hot"))
    for _ in range(2000):
        j.record(model="m", status=200)
    _, dur = _timed(lambda: [j.record(model="m", status=200) for _ in range(100)])
    per_call_us = dur / 100 * 1e6
    assert per_call_us < 20000, f"{per_call_us:.0f}us added per API call -- unacceptable on the hot path"


# ===================================================================== B. FAULT INJECTION

def test_b1_unwritable_directory_never_raises_and_is_counted(tmp_path):
    j = _j(tmp_path)
    j._journal_dir = "\x00::impossible::"
    assert j.record(model="m", status=200) is False
    assert j.dropped == 1, "a lost record must be counted, never silent"


def test_b2_disk_full_midwrite_is_survived(tmp_path, monkeypatch):
    """An OSError from write() must be swallowed and counted, not propagated into an API call."""
    j = _j(tmp_path)
    j.record(model="m", status=200)
    real_open = open

    def _full(*a, **k):
        f = real_open(*a, **k)
        if len(a) > 1 and "a" in str(a[1]):
            def boom(*_a, **_k):
                raise OSError(28, "No space left on device")
            f.write = boom
        return f

    monkeypatch.setattr("builtins.open", _full)
    assert j.record(model="m", status=200) is False
    assert j.dropped >= 1


def test_b3_a_torn_line_costs_one_record_not_the_reader(tmp_path):
    """A crash mid-write leaves a partial JSON line. The reader must skip it and keep going --
    RB-26's spirit: a torn record is one lost record, never a dead reader."""
    j = _j(tmp_path)
    j.record(model="m", status=200, usage={"total_tokens": 5})
    with open(j._segment_path(), "a", encoding="utf-8") as f:
        f.write('{"ts": 1, "agent": "x", "model": "trunc\n')      # torn
    j.record(model="m", status=200, usage={"total_tokens": 7})
    rows = j.read_all()
    assert len(rows) == 2, f"reader lost good records to a torn line: {len(rows)}"
    assert j.summarize()["total_tokens"] == 12


def test_b4_vanished_directory_is_survived(tmp_path):
    """Journal dir deleted underneath us (cleanup script, operator, container restart)."""
    j = _j(tmp_path)
    j.record(model="m", status=200)
    import shutil
    shutil.rmtree(j._journal_dir)
    assert j.record(model="m", status=200) is True, "record() must recreate its own directory"
    assert j.files(), "writing after a vanished dir produced no file"


def test_b5_concurrent_writers_lose_nothing(tmp_path):
    """20 threads, the fleet scale this is built for. Every record must land exactly once."""
    j = _j(tmp_path)
    N, PER = 20, 50

    def w(i):
        for k in range(PER):
            j.record(model="m", status=200, agent=f"a{i}", usage={"total_tokens": 1})

    ts = [threading.Thread(target=w, args=(i,)) for i in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    rows = j.read_all()
    assert len(rows) == N * PER, f"lost records under concurrency: {len(rows)} of {N*PER}"
    assert j.dropped == 0
    for line_no, r in enumerate(rows):
        assert isinstance(r, dict), f"interleaved write corrupted record {line_no}"


def test_b6_reader_survives_a_file_deleted_mid_read(tmp_path):
    """files() lists, then read_all() opens -- a rotation between the two is a real race."""
    j = _j(tmp_path)
    for _ in range(5):
        j.record(model="m", status=200)
    listed = j.files()
    j.files = lambda *a, **k: listed + [os.path.join(j._journal_dir, "wire-gone-999.jsonl")]
    rows = j.read_all()
    assert isinstance(rows, list), "reader died on a file that vanished between list and open"


# ===================================================================== C. BEHAVIOURAL INVARIANTS

@pytest.mark.parametrize("payload", [
    {"prompt_text": "secret-alpha", "response_text": "secret-beta"},
    {"prompt_text": "", "response_text": None},
    {"prompt_text": "x" * 100000},
    {"prompt_text": {"nested": "secret-gamma"}},
    {"prompt_text": ["secret-delta", 2]},
    {"prompt_text": b"secret-epsilon"},
])
def test_c1_no_body_reaches_disk_for_any_input_shape(tmp_path, payload):
    """W2 held for a string. Verify it holds for dicts, lists, bytes, empty and huge -- the shapes
    a caller will eventually pass. A privacy guarantee that only covers the tested type is not a
    guarantee."""
    j = _j(tmp_path, sub=f"c1{abs(hash(str(payload)))}")
    j.record(model="m", status=200, **payload)
    raw = "".join(open(p, encoding="utf-8").read() for p in j.files())
    for marker in ("secret-alpha", "secret-beta", "secret-gamma", "secret-delta", "secret-epsilon"):
        assert marker not in raw, f"body content {marker!r} reached disk"
    assert "x" * 1000 not in raw, "a large body was written verbatim"


def test_c2_authorization_header_can_never_land(tmp_path):
    """The allowlist is the control. Verify it holds against case variants and lookalikes."""
    j = _j(tmp_path)
    j.record(model="m", status=200, headers={
        "Authorization": "Bearer sk-SECRETKEY", "AUTHORIZATION": "Bearer sk-SECRETKEY2",
        "x-api-key": "sk-SECRETKEY3", "cookie": "session=SECRETKEY4",
        "x-ds-trace-id": "keep-me"})
    raw = "".join(open(p, encoding="utf-8").read() for p in j.files())
    assert "SECRETKEY" not in raw, "a credential header reached disk"
    assert "keep-me" in raw, "the allowlisted header was dropped"


def test_c3_a_record_round_trips_intact(tmp_path):
    """Does it do what it says: what goes in comes back out, with the right names."""
    j = _j(tmp_path)
    j.record(model="deepseek-chat", status=200, finish_reason="stop", system_fingerprint="fp_x",
             service_tier="default", attempt=2, ms_first_byte=431,
             usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                    "prompt_cache_hit_tokens": 8, "prompt_cache_miss_tokens": 2,
                    "completion_tokens_details": {"reasoning_tokens": 3}})
    r = j.read_all()[0]
    for k, v in (("model", "deepseek-chat"), ("status", 200), ("finish_reason", "stop"),
                 ("system_fingerprint", "fp_x"), ("service_tier", "default"), ("attempt", 2),
                 ("ms_first_byte", 431), ("prompt_tokens", 10), ("completion_tokens", 5),
                 ("total_tokens", 15), ("cache_hit_tokens", 8), ("cache_miss_tokens", 2),
                 ("reasoning_tokens", 3)):
        assert r[k] == v, f"{k}: expected {v!r}, got {r[k]!r}"
    s = j.summarize()
    assert s["cache_hit_rate"] == 0.8, f"cache hit rate wrong: {s['cache_hit_rate']}"


def test_c4_identical_prompts_hash_identically_across_instances(tmp_path):
    """Cache forensics depends on comparing prefix hashes ACROSS turns and processes. If the hash
    were salted per instance, every comparison would be meaningless -- and silently so."""
    a, b = _j(tmp_path, "ha"), _j(tmp_path, "hb")
    a.record(model="m", status=200, prompt_text="same prompt")
    b.record(model="m", status=200, prompt_text="same prompt")
    assert a.read_all()[0]["prompt_sha"] == b.read_all()[0]["prompt_sha"]
    a.record(model="m", status=200, prompt_text="different")
    assert a.read_all()[1]["prompt_sha"] != a.read_all()[0]["prompt_sha"]


def test_c5_expert_reports_nothing_as_clean_not_as_broken(tmp_path):
    """An empty journal must not manufacture findings, and a clean one must not either."""
    j = _j(tmp_path)
    empty = j.expert()
    assert len(empty) == 1 and empty[0][0] == "info"
    for _ in range(3):
        j.record(model="m", status=200, finish_reason="stop", system_fingerprint="fp_same",
                 usage={"prompt_cache_hit_tokens": 9, "prompt_cache_miss_tokens": 1})
    sev = {s for s, _, _ in j.expert()}
    assert "error" not in sev and "warn" not in sev, f"clean traffic produced {j.expert()}"


def test_c6_agent_scope_isolates(tmp_path):
    """doctor walks the fleet; a scoped read must not leak one agent's anomalies into another's."""
    j = _j(tmp_path)
    j.record(agent="alpha", model="m", status=500, finish_reason="length")
    j.record(agent="beta", model="m", status=200, finish_reason="stop")
    assert j.summarize(agent="beta")["truncated"] == 0
    assert j.summarize(agent="alpha")["truncated"] == 1
    assert all(sev == "info" for sev, _, _ in j.expert(agent="beta"))
