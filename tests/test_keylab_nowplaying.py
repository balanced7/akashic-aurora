"""Windows' now-playing from ONE long-lived SMTC session manager per process (arsenal/keylab/nowplaying.py).

Measured 2026-10-29: Windows' NPSMSvc at 322-404 % of one core while the play tracker asked
GlobalSystemMediaTransportControlsSessionManager.request_async() for a new manager every 2 s and enumerated every
session (0 % with it suspended); beatsync.now_playing() did the same per call under the VJ engine's 2 s track thread.
These pin the fix against a fake winrt (tests/fake_winrt_smtc.py): one manager however often it is read, changes
arriving by event with no enumeration, a slow safety poll for a missed event, the recovery paths, the fallback with
no winrt, and the readers' outputs as they were (beatsync's {title, artist, status} and the VJ engine's track key).
No live SMTC call anywhere here.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from arsenal.keylab import beatsync as BS
from fake_winrt_smtc import PAUSED, PLAYING, FakeSmtc, until

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "arsenal" / "keylab" / "nowplaying.py"
PLAYLOG_DIR = Path(os.environ.get("PLAYLOG_DIR", r"E:\dev\playlog"))


def _np():
    from arsenal.keylab import nowplaying
    return nowplaying


@pytest.fixture(autouse=True)
def _fresh_process_watcher():
    """Each test starts and ends with no process-wide watcher (beatsync.now_playing reads through it)."""
    def drop():
        try:
            _np().shutdown()
        except ImportError:
            pass
    drop()
    yield
    drop()


@pytest.fixture
def fake(monkeypatch):
    return FakeSmtc().install(monkeypatch)


@pytest.fixture
def watchers():
    made = []

    def make(**kw):
        w = _np().Watcher(**kw).start()
        made.append(w)
        return w
    yield make
    for w in made:
        w.stop()


# --- beatsync.now_playing: what the VJ engine's track thread reads every 2 s ------------------------------------------

def test_beatsync_now_playing_asks_windows_for_one_manager_however_often_it_is_read(fake):
    fake.add_session("Chrome", "A video", "A channel", PLAYING, current=True)
    for _ in range(20):
        rec = BS.now_playing()
    assert rec == {"title": "A video", "artist": "A channel", "status": PLAYING}
    assert fake.managers == 1                        # was 20: a new manager per call
    assert fake.current_reads == 1 and fake.enumerations == 0
    assert fake.property_reads == 1                  # the other 19 reads were memory


def test_beatsync_now_playing_keeps_its_shape_and_the_engines_track_key(fake):
    from arsenal.keylab import vj as V
    s = fake.add_session("Spotify.exe", "Song  A", "Artist A", PLAYING, current=True)
    rec = BS.now_playing()
    assert rec == {"title": "Song  A", "artist": "Artist A", "status": PLAYING}
    assert V.track_key(rec) == ("artist a", "song a")
    fake.change(s, status=PAUSED)
    assert until(lambda: (BS.now_playing() or {}).get("status") == PAUSED)
    assert V.track_key(BS.now_playing()) is None     # a paused session is not the track
    fake.set_current(None)
    assert until(lambda: BS.now_playing() is None)


# --- the watcher --------------------------------------------------------------------------------------------------------

def test_a_track_change_and_a_pause_arrive_by_event_with_no_poll_and_no_enumeration(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") == {"app": "Spotify.exe", "title": "Song A", "artist": "Artist A", "status": PLAYING}
    enumerations, reads = fake.enumerations, fake.property_reads
    fake.change(s, title="Song B", artist="Artist B")
    assert until(lambda: (w.read("spotify") or {}).get("title") == "Song B")
    assert w.read("spotify") == {"app": "Spotify.exe", "title": "Song B", "artist": "Artist B", "status": PLAYING}
    fake.change(s, status=PAUSED)
    assert until(lambda: (w.read("spotify") or {}).get("status") == PAUSED)
    assert fake.managers == 1 and fake.enumerations == enumerations
    assert fake.property_reads == reads + 1          # the pause re-read the playback status only
    assert w.status()["stats"]["events"] >= 2


def test_the_spotify_pick_follows_spotify_not_the_current_browser_session(fake, watchers):
    fake.add_session("Chrome", "A video", "A channel", PLAYING, current=True)
    fake.add_session("Spotify.exe", "Song A", "Artist A", PAUSED)
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") == {"app": "Spotify.exe", "title": "Song A", "artist": "Artist A", "status": PAUSED}
    assert w.read(_np().CURRENT)["app"] == "Chrome"
    assert fake.managers == 1                        # both picks from the one manager


def test_spotify_closing_and_coming_back_is_followed_by_sessions_changed(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") is not None
    fake.remove_session(s)
    assert until(lambda: w.read("spotify") is None)
    s2 = fake.add_session("Spotify.exe", "Song C", "Artist C", PLAYING)
    assert until(lambda: (w.read("spotify") or {}).get("title") == "Song C")
    owners = [o for o, _ in fake.subscriptions()]
    assert not any(o is s for o in owners) and any(o is s2 for o in owners)
    assert fake.managers == 1


def test_the_safety_poll_catches_a_missed_event(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(safety_poll_s=0.2)
    assert w.read("spotify")["title"] == "Song A"
    fake.change(s, title="Song B", fire=False)       # Windows never told us
    assert until(lambda: (w.read("spotify") or {}).get("title") == "Song B", timeout=3.0)
    assert fake.managers == 1


def test_a_burst_of_events_is_read_once_it_lands(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(safety_poll_s=3600, coalesce_s=1.0)
    w.read("spotify")
    reads = fake.property_reads
    for i in range(10):
        fake.change(s, title=f"Song {i}")
    assert until(lambda: (w.read("spotify") or {}).get("title") == "Song 9", timeout=4.0)
    assert fake.property_reads - reads <= 2          # ten events, one or two reads


def test_without_winrt_it_is_none_at_once_and_the_thread_ends(monkeypatch, watchers):
    FakeSmtc.remove_winrt(monkeypatch)
    w = watchers()
    t0 = time.monotonic()
    assert w.read() is None and w.read("spotify") is None
    assert time.monotonic() - t0 < 1.0
    assert until(lambda: not w.alive) and w.available is False
    assert BS.now_playing() is None


def test_a_failing_manager_is_replaced_after_the_retry(fake, watchers):
    fake.fail_requests = 1
    fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(retry_s=0.05)
    assert until(lambda: w.read("spotify") is not None, timeout=3.0)
    assert fake.requests == 2 and fake.managers == 1
    assert w.status()["stats"]["errors"] == 1


def test_a_session_read_that_fails_is_none_then_recovers_on_the_same_manager(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    s.fail_reads = 1
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") is None
    assert until(lambda: w.read("spotify") is not None, timeout=4.0)   # re-picked REPICK_SOON_S later
    assert fake.managers == 1


def test_a_session_with_no_media_properties_yet_is_none(fake, watchers):
    s = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    s.no_properties = True
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") is None
    s.no_properties = False
    fake.change(s, title="Song A")
    assert until(lambda: w.read("spotify") is not None)


def test_stop_unsubscribes_everything_and_reads_none(fake, watchers):
    fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    w = watchers(safety_poll_s=3600)
    assert w.read("spotify") and w.read(_np().CURRENT)
    assert fake.subscriptions()                      # the manager's two events and the session's two
    assert not any(e == "timeline_properties_changed" for _, e in fake.subscriptions())   # fires every second
    w.stop()
    assert fake.subscriptions() == []
    assert w.read("spotify") is None and not w.alive


# --- the live check's tool (measure) ------------------------------------------------------------------------------------

TASKLIST = ('"svchost.exe","1204","BrokerInfrastructure,DcomLaunch,PlugPlay"\n'
            '"svchost.exe","9876","CDPUserSvc_4f1e2,NPSMSvc_4f1e2,WpnUserService_4f1e2"\n'
            '"python.exe","5555","N/A"\n')


def test_npsmsvc_pid_comes_from_the_svchost_that_hosts_it():
    NP = _np()
    assert NP.npsmsvc_pid(TASKLIST) == 9876
    assert NP.npsmsvc_pid('"svchost.exe","1","Dhcp"\n') is None


def test_measure_reports_npsmsvc_cpu_per_phase_and_the_old_read_is_one_manager_per_read(fake):
    NP = _np()
    fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    t = {"wall": 0.0, "cpu": 0.0, "rate": 0.25}

    def sleep(s):
        t["wall"] += s
        t["cpu"] += s * t["rate"]

    out = NP.measure(seconds=10, pick="spotify", poll_s=2.0, phases=("baseline", "old", "new"), pid=9876,
                     cpu=lambda pid: t["cpu"], clock=lambda: t["wall"], sleep=sleep)
    ph = out["phases"]
    assert out["npsmsvc_pid"] == 9876
    assert ph["baseline"]["npsmsvc_pct_of_one_core"] == pytest.approx(25.0) and ph["baseline"]["reads"] == 0
    assert ph["old"]["reads"] == 5 and ph["old"]["managers"] == 5            # the pre-fix read: one per read
    assert ph["new"]["reads"] == 5 and ph["new"]["managers"] == 1
    assert ph["new"]["last"] == {"app": "Spotify.exe", "title": "Song A", "artist": "Artist A", "status": PLAYING}
    assert fake.managers == 5 + 1                    # what Windows handed out: five for the old reads, one for new
    with pytest.raises(ValueError):
        NP.measure(seconds=1, phases=("baseline", "nwe"), pid=1, cpu=lambda pid: 0.0)


def test_a_zero_interval_cannot_spin_the_owner_thread():
    w = _np().Watcher(safety_poll_s=0, retry_s=0, coalesce_s=-1)
    assert w.safety_poll_s > 0 and w.retry_s > 0 and w.coalesce_s == 0


# --- the play tracker's copy -------------------------------------------------------------------------------------------

def test_the_play_trackers_copy_is_this_module():
    """playlog (outside this repo) keeps a byte-identical copy next to it; this says when the two have drifted."""
    copy = PLAYLOG_DIR / "nowplaying.py"
    if not copy.exists():
        pytest.skip(f"no play tracker copy at {copy}")
    norm = lambda b: b.replace(b"\r\n", b"\n")
    assert norm(copy.read_bytes()) == norm(MODULE.read_bytes()), f"copy {MODULE} over {copy}"
