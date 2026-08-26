"""A cross-process exclusive file lock.

Born 2026-08-26 from a message that was admitted and then silently lost. The inbox
that doubles as the bridge's idempotency ledger was updated by a read-modify-write with
no lock at all, under a ThreadingHTTPServer with no thread cap -- so two concurrent
admits each read the file, each appended their own row, each wrote a temp file with the
SAME fixed name, and raced os.replace. The loser's message vanished without an error.

Threads alone do not cover it: the inbox is also written by CLI processes. So the lock
has to be one the operating system arbitrates, not one that lives in a single
interpreter. `run_job.publish_fence` already implements this shape, but core/ may not
import from scripts/, so the primitive lives here where both planes can reach it.

Deliberately small: a sidecar `.lock` file, an OS advisory lock on one byte of it, a
bounded wait, and a context manager. No lock directories, no PID files, no staleness
heuristics -- the kernel drops the lock when the holder dies, which is the one
correctness property a hand-rolled lock file cannot give you.
"""
from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Iterator, Union

try:                                    # Windows
    import msvcrt
except ImportError:                     # pragma: no cover - POSIX
    msvcrt = None                       # type: ignore[assignment]

try:                                    # POSIX
    import fcntl
except ImportError:                     # pragma: no cover - Windows
    fcntl = None                        # type: ignore[assignment]

DEFAULT_TIMEOUT_S = 10.0
_POLL_S = 0.01


class LockTimeout(RuntimeError):
    """The lock was held by someone else for longer than the caller was willing to wait."""


def _try_lock(fh) -> bool:
    """One non-blocking attempt. True if we now hold the lock."""
    try:
        if msvcrt is not None:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
    except OSError:
        return False
    return False                        # no locking primitive at all


def _unlock(fh) -> None:
    with contextlib.suppress(OSError):
        if msvcrt is not None:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def exclusive(target: Union[str, os.PathLike],
              *, timeout: float = DEFAULT_TIMEOUT_S) -> Iterator[bool]:
    """Hold an exclusive cross-process lock for `target` while the block runs.

    Yields True when the lock is genuinely held, False when this platform offers no
    locking primitive at all. It NEVER yields while someone else holds it -- on
    contention past `timeout` it raises LockTimeout, because a lock that quietly
    degrades to "carry on unprotected" is the same silent-loss bug in a new costume.
    """
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")

    # "a+" so the byte we lock exists without ever truncating a peer's lock file.
    with open(lock_path, "a+", encoding="utf-8") as fh:
        if msvcrt is None and fcntl is None:                 # pragma: no cover
            yield False
            return
        fh.seek(0)
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            if _try_lock(fh):
                break
            if time.monotonic() >= deadline:
                raise LockTimeout(
                    f"could not lock {lock_path.name} within {timeout:.1f}s -- "
                    f"another process is holding it")
            time.sleep(_POLL_S)
        try:
            yield True
        finally:
            _unlock(fh)
