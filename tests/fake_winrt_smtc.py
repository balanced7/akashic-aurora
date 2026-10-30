"""A stand-in for pywinrt's winrt.windows.media.control (Windows' Now Playing, SMTC), so the now-playing readers
(arsenal/keylab/nowplaying.py, beatsync.now_playing and the play tracker) can be tested with no media session, no
NPSMSvc and no winrt package.

`fake = FakeSmtc(); fake.install(monkeypatch)` puts it in sys.modules as winrt.windows.media.control (and its three
parent packages); `FakeSmtc.remove_winrt(monkeypatch)` makes `import winrt...` fail instead. It keeps the half of the
contract the readers lean on (Learn: GlobalSystemMediaTransportControlsSessionManager and ...Session):

  - the static request_async() hands back a NEW manager each call: `managers` counts them (each one is a client
    NPSMSvc serves), `requests` counts the attempts;
  - get_sessions() is counted in `enumerations`, get_current_session() in `current_reads`,
    try_get_media_properties_async() in `property_reads`; get_playback_info() is not awaited;
  - add_X(handler) returns a token and remove_X(token) drops it; `subscriptions()` is what is still subscribed;
  - a change (change / add_session / remove_session / set_current) fires the matching events, each handler called
    (sender, args) on a thread of the fake's own, as WinRT calls them on its thread pool (joined before the change
    returns, so a test knows the handler ran); fire=False changes silently, a missed event;
  - `fail_requests = N` makes the next N request_async() raise; a session's `fail_reads = N` its next N property reads.
"""
from __future__ import annotations

import sys
import threading
import time
import types
from typing import List, Optional

PLAYING, PAUSED = 4, 5
WINRT_NAMES = ("winrt", "winrt.windows", "winrt.windows.media", "winrt.windows.media.control")


def until(fn, timeout: float = 2.0, every: float = 0.01):
    """fn() once it is truthy, polled for up to `timeout` s (a watcher thread answers an event a moment later)."""
    end = time.monotonic() + timeout
    while True:
        v = fn()
        if v or time.monotonic() >= end:
            return v
        time.sleep(every)


class FakeSession:
    def __init__(self, fake: "FakeSmtc", aumid: str, title: str, artist: str, status: int):
        self._fake = fake
        self.source_app_user_model_id = aumid
        self.title, self.artist, self.status = title, artist, status
        self.fail_reads = 0
        self.no_properties = False                 # Windows has the session but no media properties for it yet

    def try_get_media_properties_async(self):
        fake = self._fake

        async def go():
            with fake.lock:
                fake.property_reads += 1
                if self.fail_reads > 0:
                    self.fail_reads -= 1
                    raise OSError("fake: the session is gone")
                if self.no_properties:
                    return None
                return types.SimpleNamespace(title=self.title, artist=self.artist)
        return go()

    def get_playback_info(self):
        return types.SimpleNamespace(playback_status=self.status)

    def add_media_properties_changed(self, handler):
        return self._fake._add(self, "media_properties_changed", handler)

    def remove_media_properties_changed(self, token):
        self._fake._remove(self, token)

    def add_playback_info_changed(self, handler):
        return self._fake._add(self, "playback_info_changed", handler)

    def remove_playback_info_changed(self, token):
        self._fake._remove(self, token)

    def add_timeline_properties_changed(self, handler):
        return self._fake._add(self, "timeline_properties_changed", handler)

    def remove_timeline_properties_changed(self, token):
        self._fake._remove(self, token)


class FakeSmtc:
    def __init__(self):
        self.lock = threading.RLock()
        self.sessions: List[FakeSession] = []
        self.current: Optional[FakeSession] = None
        self.requests = self.managers = 0
        self.enumerations = self.current_reads = self.property_reads = 0
        self.fired = 0
        self.fail_requests = 0
        self._subs = {}                            # token -> (owner, event name, handler)
        self._next_token = 0
        self.module = self._build_module()

    # --- the module ---------------------------------------------------------------------------------------------------
    def _build_module(self):
        fake = self

        class GlobalSystemMediaTransportControlsSessionManager:
            @staticmethod
            def request_async():
                async def go():
                    with fake.lock:
                        fake.requests += 1
                        if fake.fail_requests > 0:
                            fake.fail_requests -= 1
                            raise OSError("fake: NPSMSvc is not answering")
                        fake.managers += 1
                    return GlobalSystemMediaTransportControlsSessionManager()
                return go()

            def get_sessions(self):
                with fake.lock:
                    fake.enumerations += 1
                    return list(fake.sessions)

            def get_current_session(self):
                with fake.lock:
                    fake.current_reads += 1
                    return fake.current

            def add_sessions_changed(self, handler):
                return fake._add(self, "sessions_changed", handler)

            def remove_sessions_changed(self, token):
                fake._remove(self, token)

            def add_current_session_changed(self, handler):
                return fake._add(self, "current_session_changed", handler)

            def remove_current_session_changed(self, token):
                fake._remove(self, token)

        mod = types.ModuleType("winrt.windows.media.control")
        mod.GlobalSystemMediaTransportControlsSessionManager = GlobalSystemMediaTransportControlsSessionManager
        return mod

    def install(self, monkeypatch) -> "FakeSmtc":
        for name in WINRT_NAMES[:-1]:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
        monkeypatch.setitem(sys.modules, WINRT_NAMES[-1], self.module)
        return self

    @staticmethod
    def remove_winrt(monkeypatch) -> None:
        for name in WINRT_NAMES:
            monkeypatch.setitem(sys.modules, name, None)      # `import winrt...` raises ImportError

    # --- subscriptions -----------------------------------------------------------------------------------------------
    def _add(self, owner, event: str, handler):
        with self.lock:
            self._next_token += 1
            self._subs[self._next_token] = (owner, event, handler)
            return self._next_token

    def _remove(self, owner, token) -> None:
        with self.lock:
            sub = self._subs.get(token)
            if sub is not None and sub[0] is owner:
                del self._subs[token]

    def subscriptions(self) -> list:
        with self.lock:
            return [(owner, event) for owner, event, _ in self._subs.values()]

    def _fire(self, event: str, owner=None) -> None:
        with self.lock:
            targets = [(o, h) for o, e, h in self._subs.values() if e == event and (owner is None or o is owner)]
            self.fired += len(targets)
        for o, h in targets:
            t = threading.Thread(target=h, args=(o, object()), daemon=True)
            t.start()
            t.join(5.0)

    # --- the world changing ------------------------------------------------------------------------------------------
    def add_session(self, aumid: str, title: str = "", artist: str = "", status: int = PLAYING,
                    current: bool = False, fire: bool = True) -> FakeSession:
        s = FakeSession(self, aumid, title, artist, status)
        with self.lock:
            self.sessions.append(s)
            if current or self.current is None:
                self.current = s
        if fire:
            self._fire("sessions_changed")
            self._fire("current_session_changed")
        return s

    def remove_session(self, s: FakeSession, fire: bool = True) -> None:
        with self.lock:
            self.sessions.remove(s)
            if self.current is s:
                self.current = self.sessions[0] if self.sessions else None
        if fire:
            self._fire("sessions_changed")
            self._fire("current_session_changed")

    def set_current(self, s: Optional[FakeSession], fire: bool = True) -> None:
        with self.lock:
            self.current = s
        if fire:
            self._fire("current_session_changed")

    def change(self, s: FakeSession, title: Optional[str] = None, artist: Optional[str] = None,
               status: Optional[int] = None, fire: bool = True) -> None:
        with self.lock:
            if title is not None:
                s.title = title
            if artist is not None:
                s.artist = artist
            if status is not None:
                s.status = status
        if fire:
            if title is not None or artist is not None:
                self._fire("media_properties_changed", s)
            if status is not None:
                self._fire("playback_info_changed", s)
