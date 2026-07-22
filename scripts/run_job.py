#!/usr/bin/env python3
"""Durable one-shot job supervision for long Akashic operations (T093).

The launch call is deliberately short: it writes an immutable local spec, asks an
out-of-tree broker to start a watchdog and supervisor, prints a launch receipt, and
returns.  Job output and completion never depend on the caller's pipe or tool frame.

Windows' strict path uses ``Win32_Process.Create`` through local WMI.  The two guards
therefore live under WmiPrvSE rather than the Codex/app-server controller tree.  An
explicit ``--broker detached`` fallback exists, but its receipt says
``direct-parent-only`` and must never be presented as recursive-tree safe.

Public doors::

    py scripts/run_job.py launch --job-id ID --max-runtime 3600 -- COMMAND ...
    py scripts/run_job.py status ID
    py scripts/run_job.py cancel ID --reason "operator request"

Governing build spec: research/reviewed/t093-crash-path-reconciliation-2026-07-17.md
section 7.  No Redis dependency; state lives under ignored ``state/jobs`` by default.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import ctypes
import errno
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = ROOT / "state" / "jobs"
SCHEMA = 1
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
TERMINAL = {
    "succeeded", "failed", "cancelled", "deadline_exceeded", "child_killed",
    "launch_failed", "outcome_unknown", "supervision_lost",
}
_SENSITIVE_ENV = re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|COOKIE|AUTH|API_KEY)", re.I)
_SAFE_ENV_EXACT = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "LANG", "LC_ALL",
}
_SAFE_ENV_PREFIXES = ("AKASHIC_", "BIFROST_", "REDIS_", "PYTHON", "GIT_")


class JobError(RuntimeError):
    """A loud, user-actionable durable-job error."""


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _as_path(value: os.PathLike[str] | str) -> Path:
    return Path(value).expanduser().resolve()


def _validate_job_id(job_id: str) -> str:
    value = str(job_id or "")
    if not JOB_ID_RE.fullmatch(value):
        raise JobError(
            "job id must match [A-Za-z0-9][A-Za-z0-9._-]{0,79}; "
            "path separators and whitespace are forbidden"
        )
    return value


def _job_dir(state_dir: os.PathLike[str] | str, job_id: str) -> Path:
    return _as_path(state_dir) / _validate_job_id(job_id)


def _paths(state_dir: os.PathLike[str] | str, job_id: str) -> Dict[str, Path]:
    root = _job_dir(state_dir, job_id)
    return {
        "root": root,
        "spec": root / "spec.json",
        "launch": root / "launch.json",
        "status": root / "status.json",
        "watchdog": root / "watchdog.json",
        "cancel": root / "cancel.request",
        "outcome": root / "outcome.json",
        "publish_fence": root / "publish.fence",
        "log": root / "output.log",
    }


def _atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    """Single-record atomic write.  Append-only logs intentionally use normal files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    data = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        # Antivirus/indexer readers can briefly race replace on Windows.  The old
        # complete record remains valid while we make a few bounded retries.
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def write_child_outcome(path: os.PathLike[str] | str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a child-owned point-of-no-return receipt atomically."""
    record = {
        "schema": SCHEMA,
        **dict(payload),
        "outcome_written_at": _iso_now(),
        "outcome_written_epoch": time.time(),
    }
    _atomic_json(_as_path(path), record)
    return record


def _lock_fence_file(fh: Any, *, blocking: bool) -> bool:
    if sys.platform == "win32":
        import msvcrt

        mode = msvcrt.LK_NBLCK
        while True:
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), mode, 1)
                return True
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if not blocking:
                    return False
                time.sleep(0.02)
    else:
        import fcntl

        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            fcntl.flock(fh.fileno(), flags)
            return True
        except BlockingIOError:
            return False


def _unlock_fence_file(fh: Any) -> None:
    if sys.platform == "win32":
        import msvcrt

        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextmanager
def publish_fence(path: os.PathLike[str] | str, *, blocking: bool = True):
    """Hold the cross-process publish/force exclusion byte; yield whether acquired."""
    fence_path = _as_path(path)
    fence_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fence_path, "a+b", buffering=0) as fh:
        if fh.seek(0, os.SEEK_END) == 0:
            fh.write(b"\0")
            os.fsync(fh.fileno())
        acquired = _lock_fence_file(fh, blocking=blocking)
        try:
            yield acquired
        finally:
            if acquired:
                _unlock_fence_file(fh)


def _safe_env_snapshot() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if _SENSITIVE_ENV.search(upper):
            continue
        if upper in _SAFE_ENV_EXACT or any(upper.startswith(p) for p in _SAFE_ENV_PREFIXES):
            out[key] = str(value)
    return out


# ---- exact process identity ---------------------------------------------------------------

def _win_process_info_from_handle(handle: Any) -> tuple[bool, Optional[str]]:
    """Return liveness + creation FILETIME for this already-open process handle."""
    if sys.platform != "win32" or not handle:
        return False, None
    from ctypes import wintypes

    still_active = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    code = wintypes.DWORD()
    if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != still_active:
        return False, None
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not kernel32.GetProcessTimes(
        handle, ctypes.byref(created), ctypes.byref(exited),
        ctypes.byref(kernel), ctypes.byref(user),
    ):
        return True, None
    token = f"{created.dwHighDateTime:08x}{created.dwLowDateTime:08x}"
    return True, token


def _win_process_info(pid: int) -> tuple[bool, Optional[str]]:
    """Return (alive, creation FILETIME token) without third-party dependencies."""
    if sys.platform != "win32":
        return False, None
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not handle:
        return False, None
    try:
        return _win_process_info_from_handle(handle)
    finally:
        _win_close_handle(handle)


def _posix_process_info(pid: int) -> tuple[bool, Optional[str]]:
    try:
        # /proc starttime (field 22) protects against PID reuse on Linux.
        stat = Path(f"/proc/{int(pid)}/stat").read_text(encoding="ascii")
        close = stat.rfind(")")
        fields = stat[close + 2:].split()
        return True, fields[19] if len(fields) > 19 else None
    except OSError:
        try:
            os.kill(int(pid), 0)
            return True, None
        except OSError:
            return False, None


def _process_info(pid: Any) -> tuple[bool, Optional[str]]:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False, None
    if value <= 0:
        return False, None
    return _win_process_info(value) if sys.platform == "win32" else _posix_process_info(value)


def _matches_identity(pid: Any, expected: Optional[str]) -> bool:
    alive, actual = _process_info(pid)
    return bool(alive and expected and actual and str(expected) == str(actual))


# ---- retained Windows Job Object ownership -----------------------------------------------

_JOB_OBJECT_ASSIGN_PROCESS = 0x0001
_JOB_OBJECT_SET_ATTRIBUTES = 0x0002
_JOB_OBJECT_QUERY = 0x0004
_JOB_OBJECT_TERMINATE = 0x0008
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


def _win_close_handle(handle: Any) -> None:
    if sys.platform != "win32" or not handle:
        return
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(handle)


def _win_create_kill_job(name: str) -> Any:
    """Create one uniquely named job whose last owner closes the whole process set."""
    if sys.platform != "win32":
        raise JobError("Windows Job Objects are unavailable on this platform")
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL

    ctypes.set_last_error(0)
    handle = kernel32.CreateJobObjectW(None, str(name))
    if not handle:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        _win_close_handle(handle)
        raise JobError(f"refusing pre-existing Job Object name {name!r}")
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        handle,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        error = ctypes.get_last_error()
        _win_close_handle(handle)
        raise OSError(error, "SetInformationJobObject(KILL_ON_JOB_CLOSE) failed")
    return handle


def _win_open_job(name: str, access: int = _JOB_OBJECT_QUERY) -> Any:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenJobObjectW.restype = wintypes.HANDLE
    handle = kernel32.OpenJobObjectW(int(access), False, str(name))
    if not handle:
        raise OSError(ctypes.get_last_error(), f"OpenJobObjectW({name!r}) failed")
    return handle


def _win_handle_in_job(job_handle: Any, process_handle: Any) -> bool:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.IsProcessInJob.argtypes = [
        wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL),
    ]
    kernel32.IsProcessInJob.restype = wintypes.BOOL
    member = wintypes.BOOL()
    return bool(
        kernel32.IsProcessInJob(process_handle, job_handle, ctypes.byref(member))
        and member.value
    )


def _win_process_in_job(handle: Any, pid: int, identity: Optional[str]) -> bool:
    """Verify identity and membership on one exact process handle."""
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    process = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not process:
        return False
    try:
        alive, actual = _win_process_info_from_handle(process)
        return bool(
            alive and identity and actual and str(identity) == str(actual)
            and _win_handle_in_job(handle, process)
        )
    finally:
        _win_close_handle(process)


def _win_named_job_contains(name: str, pid: int, identity: Optional[str]) -> bool:
    try:
        handle = _win_open_job(name)
    except OSError:
        return False
    try:
        return _win_process_in_job(handle, pid, identity)
    finally:
        _win_close_handle(handle)


def _win_assign_exact_to_job(handle: Any, pid: int, identity: str) -> Dict[str, Any]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    access = 0x0001 | 0x0100 | 0x1000  # TERMINATE | SET_QUOTA | QUERY_LIMITED
    process = kernel32.OpenProcess(access, False, int(pid))
    if not process:
        alive, actual = _win_process_info(pid)
        return {
            "assigned": False,
            "identity_match": bool(alive and actual and str(actual) == str(identity)),
            "reason": "open_process_for_job_assignment_failed",
            "winerror": ctypes.get_last_error(),
        }
    try:
        alive, actual = _win_process_info_from_handle(process)
        if not alive or not actual or str(actual) != str(identity):
            return {
                "assigned": False,
                "identity_match": False,
                "reason": "pid_creation_identity_mismatch",
                "expected_identity": identity,
                "actual_identity": actual,
            }
        if _win_handle_in_job(handle, process):
            return {"assigned": True, "identity_match": True, "already_assigned": True}
        if not kernel32.AssignProcessToJobObject(handle, process):
            return {
                "assigned": False,
                "identity_match": True,
                "reason": "AssignProcessToJobObject_failed",
                "winerror": ctypes.get_last_error(),
            }
        assigned = _win_handle_in_job(handle, process)
        return {
            "assigned": assigned,
            "identity_match": True,
            "reason": None if assigned else "job_membership_verification_failed",
        }
    finally:
        _win_close_handle(process)


def _win_job_members(handle: Any) -> list[int]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    for capacity in (16, 64, 256, 1024, 4096):
        class PROCESS_ID_LIST(ctypes.Structure):
            _fields_ = [
                ("NumberOfAssignedProcesses", wintypes.DWORD),
                ("NumberOfProcessIdsInList", wintypes.DWORD),
                ("ProcessIdList", ctypes.c_size_t * capacity),
            ]

        value = PROCESS_ID_LIST()
        returned = wintypes.DWORD()
        if kernel32.QueryInformationJobObject(
            handle,
            _JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            ctypes.byref(value),
            ctypes.sizeof(value),
            ctypes.byref(returned),
        ):
            assigned = int(value.NumberOfAssignedProcesses)
            listed = int(value.NumberOfProcessIdsInList)
            if listed < assigned:
                # Microsoft documents that a successful call may still return a
                # partial list. Never let that truncate force/emptiness evidence.
                continue
            return [int(value.ProcessIdList[i]) for i in range(listed)]
        error = ctypes.get_last_error()
        if error != 234:  # ERROR_MORE_DATA
            raise OSError(error, "QueryInformationJobObject(ProcessIdList) failed")
    raise JobError("Job Object process list exceeded the 4096-process safety bound")


def _win_terminate_owned_job(handle: Any, pid: int, identity: str) -> Dict[str, Any]:
    """Terminate retained membership and confirm that the OS-owned set becomes empty."""
    before = _win_job_members(handle)
    root_alive, root_actual_identity = _win_process_info(pid)
    root_identity_match = bool(
        root_alive and root_actual_identity
        and str(root_actual_identity) == str(identity)
    )
    if not before:
        return {
            "killed": True,
            "already_dead": True,
            "identity_match": True,
            "job_membership_match": True,
            "force_applied": False,
            "detail": "watchdog-owned Job Object was already empty",
            "member_pids_before": [],
            "remaining_pids": [],
            "root_pid_alive": root_alive,
            "root_identity_match": root_identity_match,
        }
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    if not kernel32.TerminateJobObject(handle, 1):
        return {
            "killed": False,
            "identity_match": True,
            "job_membership_match": True,
            "force_applied": False,
            "detail": "TerminateJobObject failed",
            "winerror": ctypes.get_last_error(),
            "member_pids_before": before,
            "root_pid_alive": root_alive,
            "root_identity_match": root_identity_match,
        }
    deadline = time.monotonic() + 2.0
    remaining = _win_job_members(handle)
    while remaining and time.monotonic() < deadline:
        time.sleep(0.02)
        remaining = _win_job_members(handle)
    return {
        "killed": not remaining,
        "identity_match": True,
        "job_membership_match": True,
        "force_applied": True,
        "detail": "watchdog-owned Job Object + TerminateJobObject",
        "member_pids_before": before,
        "remaining_pids": remaining,
        "root_pid_alive": root_alive,
        "root_identity_match": root_identity_match,
    }


@contextmanager
def protect_owned_job_during_publish():
    """Keep this job alive while its publish fence protects an irreversible effect.

    The worker opens the same named Job Object before taking ``publish.fence``.
    If both external guards die, this narrowly scoped handle prevents
    ``KILL_ON_JOB_CLOSE`` from interrupting push. Closing it after the durable
    pushed outcome restores fail-close behavior.
    """
    if sys.platform != "win32":
        yield {"protected": False, "reason": "non_windows"}
        return
    name = str(os.getenv("AKASHIC_JOB_OBJECT_NAME") or "")
    enforcement = str(os.getenv("AKASHIC_JOB_ENFORCEMENT") or "")
    if not name:
        if enforcement == "win32_job_object":
            raise JobError("durable Windows publish is missing AKASHIC_JOB_OBJECT_NAME")
        # Backward-compatible old receipts and direct unit seams never created a
        # Job Object, so there is no KILL_ON_JOB_CLOSE path to protect against.
        yield {"protected": False, "reason": "legacy_job_without_os_fail_close"}
        return
    handle = _win_open_job(name, _JOB_OBJECT_QUERY)
    identity = _process_info(os.getpid())[1]
    try:
        if not _win_process_in_job(handle, os.getpid(), identity):
            raise JobError("publish worker is not a member of its named Job Object")
        yield {
            "protected": True,
            "job_object_name": name,
            "worker_pid": os.getpid(),
            "worker_identity": identity,
        }
    finally:
        _win_close_handle(handle)


def _win_process_snapshot() -> Dict[int, int]:
    """Return {pid: parent_pid} through Toolhelp; no WMI/taskkill dependency."""
    if sys.platform != "win32":
        return {}
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    rows: Dict[int, int] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            rows[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            entry.dwSize = ctypes.sizeof(entry)
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return rows


def _win_tree_members(rows: Dict[int, int], root_pid: int) -> list[tuple[int, int]]:
    children: Dict[int, list[int]] = {}
    for pid, parent in rows.items():
        children.setdefault(parent, []).append(pid)
    members: list[tuple[int, int]] = []
    stack = [(int(root_pid), 0)]
    seen: set[int] = set()
    while stack:
        parent, depth = stack.pop()
        if parent in seen:
            continue
        seen.add(parent)
        if parent == root_pid or parent in rows:
            members.append((parent, depth))
        for child in children.get(parent, []):
            stack.append((child, depth + 1))
    return members


def _win_terminate_exact(pid: int, identity: str) -> Dict[str, Any]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    access = 0x0001 | 0x00100000 | 0x1000  # TERMINATE | SYNCHRONIZE | QUERY_LIMITED
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(access, False, int(pid))
    if not handle:
        alive, actual = _win_process_info(pid)
        if not alive:
            return {
                "pid": pid, "terminated": True, "already_dead": True,
                "identity_match": True, "force_applied": False,
            }
        return {
            "pid": pid, "terminated": False,
            "identity_match": bool(actual and str(actual) == str(identity)),
            "reason": "open_process_failed",
            "winerror": ctypes.get_last_error(),
        }
    try:
        alive, actual = _win_process_info_from_handle(handle)
        if not alive:
            return {
                "pid": pid, "terminated": True, "already_dead": True,
                "identity_match": True, "force_applied": False,
            }
        if not actual or str(actual) != str(identity):
            return {
                "pid": pid, "terminated": False, "identity_match": False,
                "reason": "pid_creation_identity_mismatch",
                "expected_identity": identity, "actual_identity": actual,
            }
        if not kernel32.TerminateProcess(handle, 1):
            return {
                "pid": pid, "terminated": False, "identity_match": True,
                "reason": "terminate_process_failed",
                "winerror": ctypes.get_last_error(),
            }
        wait_result = int(kernel32.WaitForSingleObject(handle, 2000))
    finally:
        kernel32.CloseHandle(handle)
    return {
        "pid": pid,
        "terminated": wait_result == 0,  # WAIT_OBJECT_0 on the same exact handle
        "identity_match": True,
        "force_applied": True,
        "wait_result": wait_result,
    }


def _win_kill_tree(pid: int, identity: str) -> Dict[str, Any]:
    actions: list[Dict[str, Any]] = []
    refused = False
    for _ in range(3):
        rows = _win_process_snapshot()
        members = _win_tree_members(rows, pid)
        live_members: list[tuple[int, int, str]] = []
        for member_pid, depth in members:
            alive, token = _win_process_info(member_pid)
            if not alive:
                continue
            expected = identity if member_pid == pid else token
            if not expected:
                actions.append({
                    "pid": member_pid, "terminated": False,
                    "reason": "creation_identity_unavailable",
                })
                refused = True
                continue
            live_members.append((member_pid, depth, expected))
        if not live_members:
            break
        for member_pid, _depth, expected in sorted(live_members, key=lambda row: row[1], reverse=True):
            result = _win_terminate_exact(member_pid, expected)
            actions.append(result)
            if not result.get("terminated"):
                refused = True
        time.sleep(0.03)
    remaining = [
        member_pid for member_pid, _depth in _win_tree_members(_win_process_snapshot(), pid)
        if _win_process_info(member_pid)[0]
    ]
    return {
        "killed": not remaining and not refused,
        "identity_match": True,
        "force_applied": any(
            action.get("terminated") and not action.get("already_dead") for action in actions
        ),
        "detail": "direct Toolhelp snapshot + identity-checked TerminateProcess",
        "actions": actions[-32:],
        "remaining_pids": remaining,
    }


def _kill_tree(pid: int, identity: Optional[str]) -> Dict[str, Any]:
    """Force-kill one exact process tree.  Refuse when creation identity is ambiguous."""
    alive, actual = _process_info(pid)
    if not alive:
        remaining: list[int] = []
        if sys.platform == "win32":
            rows = _win_process_snapshot()
            remaining = [
                member_pid for member_pid, _depth in _win_tree_members(rows, int(pid))
                if member_pid != int(pid) and _win_process_info(member_pid)[0]
            ]
        if remaining:
            return {
                "killed": False,
                "already_dead": True,
                "identity_match": False,
                "force_applied": False,
                "reason": "root_gone_descendant_membership_unprovable",
                "remaining_pids": remaining,
            }
        return {
            "killed": True,
            "already_dead": True,
            "identity_match": True,
            "force_applied": False,
        }
    if not identity or not actual or str(identity) != str(actual):
        return {
            "killed": False,
            "identity_match": False,
            "reason": "pid_creation_identity_mismatch",
            "expected_identity": identity,
            "actual_identity": actual,
        }
    if sys.platform == "win32":
        return _win_kill_tree(int(pid), str(identity))
    else:
        try:
            os.killpg(int(pid), signal.SIGKILL)
            ok, detail = True, "SIGKILL process group"
        except ProcessLookupError:
            ok, detail = True, "already dead"
        except OSError as exc:
            ok, detail = False, str(exc)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and _process_info(pid)[0]:
        time.sleep(0.03)
    return {
        "killed": bool(ok and not _process_info(pid)[0]),
        "identity_match": True,
        "force_applied": bool(ok),
        "detail": detail,
    }


# ---- process broker ----------------------------------------------------------------------

def _role_command(role: str, state_dir: Path, job_id: str) -> list[str]:
    return [
        sys.executable, "-u", str(Path(__file__).resolve()), role,
        job_id, "--state-dir", str(state_dir),
    ]


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _wmi_create_pair(commands: Iterable[list[str]]) -> list[int]:
    """Create both guards in one local PowerShell/CIM round trip."""
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "$out = @()",
        "$startup = New-CimInstance -ClassName Win32_ProcessStartup "
        "-Property @{ShowWindow=[uint16]0; CreateFlags=[uint32]8} -ClientOnly",
    ]
    for argv in commands:
        command_line = subprocess.list2cmdline([str(x) for x in argv])
        lines.extend([
            f"$cmd = {_powershell_quote(command_line)}",
            "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
            "-Arguments @{CommandLine=$cmd; ProcessStartupInformation=$startup}",
            "if ([int]$r.ReturnValue -ne 0) { throw \"Win32_Process.Create rc=$($r.ReturnValue)\" }",
            "$out += @{ ReturnValue=[int]$r.ReturnValue; ProcessId=[int]$r.ProcessId }",
        ])
    lines.append("[Console]::Out.Write(($out | ConvertTo-Json -Compress))")
    encoded = base64.b64encode("\n".join(lines).encode("utf-16le")).decode("ascii")
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        timeout=12,
        creationflags=(
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32" else 0
        ),
    )
    if proc.returncode != 0:
        raise JobError(f"WMI broker failed (strict; no silent downgrade): {(proc.stderr or proc.stdout).strip()}")
    try:
        payload = json.loads(proc.stdout.strip())
        rows = payload if isinstance(payload, list) else [payload]
        pids = [int(row["ProcessId"]) for row in rows]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise JobError(f"WMI broker returned no parseable PID receipt: {proc.stdout!r}") from exc
    if len(pids) != 2 or any(pid <= 0 for pid in pids):
        raise JobError(f"WMI broker returned incomplete guard PIDs: {pids}")
    return pids


def _detached_create(argv: list[str]) -> int:
    kwargs: Dict[str, Any] = {
        "cwd": str(ROOT),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        )
    else:
        kwargs["start_new_session"] = True
    try:
        return int(subprocess.Popen(argv, **kwargs).pid)
    except OSError:
        # Some Windows parent jobs disallow breakaway.  This is already the explicit
        # degraded door, so retry without that flag while keeping the receipt honest.
        if sys.platform != "win32":
            raise
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        return int(subprocess.Popen(argv, **kwargs).pid)


# ---- status synthesis --------------------------------------------------------------------

def _heartbeat_stale(record: Dict[str, Any], key: str, stale_after: float) -> bool:
    try:
        return (time.time() - float(record.get(key) or 0.0)) > float(stale_after)
    except (TypeError, ValueError):
        return True


def _startup_expired(spec: Dict[str, Any]) -> bool:
    try:
        if time.monotonic() >= float(spec["startup_deadline_monotonic"]):
            return True
    except (KeyError, TypeError, ValueError):
        pass
    try:
        return time.time() >= float(spec["startup_deadline_epoch"])
    except (KeyError, TypeError, ValueError):
        return False


def read_status(job_id: str, state_dir: os.PathLike[str] | str = DEFAULT_STATE_DIR,
                stale_after: float = 10.0) -> Dict[str, Any]:
    p = _paths(state_dir, job_id)
    spec = _read_json(p["spec"])
    if not spec:
        raise JobError(f"unknown job {job_id!r}: no spec at {p['spec']}")
    try:
        stale_after = max(float(stale_after), float(spec.get("heartbeat_seconds") or 0.0) * 4.0, 0.2)
    except (TypeError, ValueError):
        stale_after = max(float(stale_after), 0.2)
    launch = _read_json(p["launch"])
    status = _read_json(p["status"])
    watchdog = _read_json(p["watchdog"])
    cancel = _read_json(p["cancel"])
    outcome = _read_json(p["outcome"])

    receipt_path = p["status"] if status else (p["launch"] if launch else p["spec"])

    out: Dict[str, Any] = {
        "schema": SCHEMA,
        "job_id": job_id,
        "state": "launching",
        "observed_state": "launching",
        "receipt_path": str(receipt_path),
        "spec_path": str(p["spec"]),
        "launch_path": str(p["launch"]),
        "watchdog_path": str(p["watchdog"]),
        "cancel_path": str(p["cancel"]),
        "outcome_path": str(p["outcome"]),
        "publish_fence_path": str(p["publish_fence"]),
        "log_path": str(p["log"]),
        "max_runtime": spec.get("max_runtime"),
        "grace_seconds": spec.get("grace_seconds"),
        "job_enforcement": spec.get("job_enforcement", "process_tree_snapshot"),
        "job_object_name": spec.get("job_object_name"),
    }
    out.update({k: v for k, v in launch.items() if k not in {"schema", "job_id"}})
    if status:
        out.update(status)
        if out.get("state") == "starting":
            # ``starting`` is a private supervisor phase. Public launch status
            # keeps the stable pre-worker state name used by fresh callers.
            out["state"] = "launching"
            out["supervisor_phase"] = "starting"

    watchdog_state = str(watchdog.get("state") or "")
    status_state = str(status.get("state") or "")
    if watchdog_state in {"deadline_exceeded", "cancelled", "launch_failed",
                          "outcome_unknown", "supervision_lost", "succeeded"}:
        # Enforcement records remain authoritative even when the supervisor races
        # to observe the worker exit caused by that enforcement.
        out.update(watchdog)

    outcome_state = str(outcome.get("state") or "")
    pushed = outcome.get("primary_effect") == "pushed"
    if outcome_state == "succeeded" and pushed:
        # The child owns proof of the irreversible effect, not proof that its
        # whole retained workload is unable to mutate. Keep the effect fields
        # visible while the primary state remains nonterminal until quiescence.
        out.update({k: v for k, v in outcome.items() if k != "state"})
        out["publish_phase"] = "pushed_candidate"
    elif outcome_state == "outcome_unknown":
        out.update({k: v for k, v in outcome.items() if k != "state"})
        out["publish_phase"] = "outcome_unknown_candidate"
    elif outcome_state in {"published", "publish_active"}:
        out.update({k: v for k, v in outcome.items() if k != "state"})
        out["publish_phase"] = outcome_state

    child_pid = out.get("child_pid") or status.get("child_pid")
    child_identity = out.get("child_identity") or status.get("child_identity")
    child_alive = _matches_identity(child_pid, child_identity) if child_pid else False
    out["child_alive"] = bool(child_alive)

    supervisor_pid = launch.get("supervisor_pid") or status.get("supervisor_pid")
    watchdog_pid = launch.get("watchdog_pid") or watchdog.get("watchdog_pid")
    supervisor_identity = status.get("supervisor_identity")
    watchdog_identity = watchdog.get("watchdog_identity")
    supervisor_alive = (
        _matches_identity(supervisor_pid, supervisor_identity)
        if supervisor_identity else (_process_info(supervisor_pid)[0] if supervisor_pid else False)
    )
    watchdog_alive = (
        _matches_identity(watchdog_pid, watchdog_identity)
        if watchdog_identity else (_process_info(watchdog_pid)[0] if watchdog_pid else False)
    )
    out["supervisor_alive"] = supervisor_alive
    out["watchdog_alive"] = watchdog_alive
    out["supervisor_pid"] = supervisor_pid
    out["watchdog_pid"] = watchdog_pid
    out["cancel_requested"] = bool(cancel)

    strict_retained_job = bool(
        sys.platform == "win32"
        and spec.get("job_enforcement") == "win32_job_object"
    )
    kill_receipt = watchdog.get("kill_receipt") or {}
    forced_quiescence = bool(
        kill_receipt.get("killed")
        and kill_receipt.get("remaining_pids") == []
    )
    stamped_quiescence = bool(
        out.get("job_quiescent") is True
        and out.get("workload_member_pids_remaining") == []
    )
    retained_membership_quiescence = False
    if strict_retained_job and not stamped_quiescence and not forced_quiescence:
        job_name = str(spec.get("job_object_name") or "")
        query_handle: Any = None
        try:
            query_handle = _win_open_job(job_name, _JOB_OBJECT_QUERY)
            member_pids = _win_job_members(query_handle)
            exclude_supervisor = bool(
                supervisor_alive and supervisor_pid and supervisor_identity
                and _win_process_in_job(
                    query_handle, int(supervisor_pid), str(supervisor_identity),
                )
            )
            remaining_workload = [
                member_pid for member_pid in member_pids
                if not (exclude_supervisor and member_pid == int(supervisor_pid))
            ]
            retained_membership_quiescence = not remaining_workload
            out["workload_member_pids_observed"] = remaining_workload
        except OSError as exc:
            # Once every known owner is dead, a missing named object is positive
            # KILL_ON_JOB_CLOSE evidence. Other open/query failures stay unknown.
            if (
                (
                    getattr(exc, "winerror", None) == 2
                    or getattr(exc, "errno", None) == 2
                )  # ERROR_FILE_NOT_FOUND
                and not child_alive and not supervisor_alive and not watchdog_alive
            ):
                retained_membership_quiescence = True
        finally:
            _win_close_handle(query_handle)
    quiescence_proven = bool(
        stamped_quiescence or forced_quiescence or retained_membership_quiescence
    )
    underlying_terminal = bool(
        status_state in TERMINAL or watchdog_state in TERMINAL
    )
    if not strict_retained_job and underlying_terminal and not child_alive:
        quiescence_proven = True

    if outcome_state == "succeeded" and pushed and quiescence_proven:
        out.update(outcome)
        out.update({
            "state": "succeeded",
            "observed_state": "succeeded",
            "reported_by": "child_outcome",
            "forced": False,
            "deadline_enforced": False,
            "job_quiescent": True,
            "workload_member_pids_remaining": [],
        })
        if cancel:
            out["cancel_requested"] = True
            out["cancel_disposition"] = "after_publish_commit_point"
    elif outcome_state == "outcome_unknown" and quiescence_proven:
        out.update(outcome)
        out.update({
            "state": "outcome_unknown",
            "observed_state": "outcome_unknown",
            "reported_by": "child_outcome",
            "deadline_enforced": False,
            "job_quiescent": True,
            "workload_member_pids_remaining": [],
        })

    nonterminal = str(out.get("state") or "") not in TERMINAL
    supervisor_fresh = bool(
        status and supervisor_alive
        and not _heartbeat_stale(status, "heartbeat_epoch", stale_after)
    )
    watchdog_fresh = bool(
        watchdog and watchdog_alive
        and not _heartbeat_stale(watchdog, "heartbeat_epoch", stale_after)
        and str(watchdog.get("state") or "") in {"watching", "cancel_pending_critical"}
    )
    supervisor_lost = bool(status and nonterminal and not supervisor_fresh)
    out["supervisor_lost"] = bool(out.get("supervisor_lost") or supervisor_lost)
    if str(out.get("state")) in {"deadline_exceeded", "cancelled"} and out.get("reported_by") == "watchdog":
        out["deadline_enforced"] = True
    elif nonterminal:
        out["deadline_enforced"] = watchdog_fresh
    else:
        out.setdefault("deadline_enforced", False)

    if outcome_state == "publish_active" and quiescence_proven and (
        str(status.get("state") or "") in TERMINAL
        or (child_pid and not child_alive and not supervisor_fresh)
    ):
        out.update({
            "state": "outcome_unknown",
            "observed_state": "outcome_unknown",
            "reported_by": "status_reader",
            "termination_cause": "publish_fence_abandoned_without_terminal_outcome",
            "primary_effect": "unknown",
            "publish_may_have_occurred": True,
            "deadline_enforced": False,
        })
        return out

    if outcome_state == "published" and pushed and quiescence_proven and (
        str(status.get("state") or "") in TERMINAL or (child_pid and not child_alive)
    ):
        out.update(outcome)
        out.update({
            "state": "succeeded",
            "observed_state": "succeeded",
            "reported_by": "child_outcome",
            "post_publish_incomplete": True,
        })
        if cancel:
            out["cancel_disposition"] = "after_publish_commit_point"
        return out

    nonterminal = str(out.get("state") or "") not in TERMINAL
    no_guard_receipts = not status and not watchdog
    if nonterminal and no_guard_receipts and _startup_expired(spec):
        out.update({
            "state": "launch_failed",
            "observed_state": "launch_failed",
            "reported_by": "status_reader",
            "error": "startup deadline expired before any live guard self-receipt",
            "retry_with_new_job_id": True,
            "deadline_enforced": False,
        })
    elif nonterminal and not supervisor_fresh and not watchdog_fresh and no_guard_receipts:
        # A broker may still be creating its first receipts.  Do not declare loss
        # before the immutable spec's startup window closes.
        out["observed_state"] = "launching"
        out["deadline_enforced"] = False
    elif nonterminal and not supervisor_fresh and not watchdog_fresh:
        previous = str(out.get("state") or "launching")
        out.update({
            "state": "supervision_lost",
            "observed_state": "supervision_lost",
            "last_reported_state": previous,
            "reported_by": "status_reader",
            "deadline_enforced": False,
        })
    elif nonterminal and supervisor_lost:
        out["observed_state"] = "supervisor_lost"
    elif nonterminal and not watchdog_fresh and supervisor_fresh:
        out["observed_state"] = "watchdog_lost"
        out["deadline_enforced"] = False
    else:
        out["observed_state"] = str(out.get("state") or "launching")
    if watchdog.get("phase"):
        out["watchdog_phase"] = watchdog.get("phase")
    if watchdog.get("force_deferred_by"):
        out["force_deferred_by"] = watchdog.get("force_deferred_by")
        out["deadline_enforced"] = False
    return out


# ---- public launch/cancel ----------------------------------------------------------------

def launch_job(command: list[str], *, job_id: str,
               state_dir: os.PathLike[str] | str = DEFAULT_STATE_DIR,
               cwd: os.PathLike[str] | str = ROOT, max_runtime: float = 3600.0,
               grace_seconds: float = 5.0, heartbeat_seconds: float = 1.0,
               broker: str = "auto") -> Dict[str, Any]:
    job_id = _validate_job_id(job_id)
    if not command:
        raise JobError("launch needs a command after --")
    max_runtime = float(max_runtime)
    grace_seconds = float(grace_seconds)
    heartbeat_seconds = float(heartbeat_seconds)
    if max_runtime <= 0 or grace_seconds < 0 or heartbeat_seconds <= 0:
        raise JobError("max-runtime and heartbeat must be >0; grace must be >=0")
    if broker not in {"auto", "wmi", "detached"}:
        raise JobError("broker must be auto|wmi|detached")
    if broker == "wmi" and sys.platform != "win32":
        raise JobError("the WMI broker is Windows-only")

    state_root = _as_path(state_dir)
    p = _paths(state_root, job_id)
    requested = {
        "command": [str(x) for x in command],
        "cwd": str(_as_path(cwd)),
        "max_runtime": max_runtime,
        "grace_seconds": grace_seconds,
        "heartbeat_seconds": heartbeat_seconds,
        "broker_requested": broker,
    }
    try:
        p["root"].mkdir(parents=True, exist_ok=False)
        new = True
    except FileExistsError:
        new = False

    if not new:
        deadline = time.monotonic() + 1.0
        existing: Dict[str, Any] = {}
        while time.monotonic() < deadline:
            existing = _read_json(p["spec"])
            if existing:
                break
            time.sleep(0.02)
        if not existing:
            raise JobError(f"job {job_id!r} has an incomplete launch directory; refusing duplicate execution")
        mismatch = [key for key, value in requested.items() if existing.get(key) != value]
        if mismatch:
            raise JobError(f"job id {job_id!r} already exists with a different spec: {', '.join(mismatch)}")
        out = read_status(job_id, state_root)
        out["reused"] = True
        return out

    created_monotonic = time.monotonic()
    job_object_name = (
        f"Local\\AkashicAurora.T093.{uuid.uuid4().hex}"
        if sys.platform == "win32" else None
    )
    spec = {
        "schema": SCHEMA,
        "job_id": job_id,
        **requested,
        "created_at": _iso_now(),
        "created_epoch": time.time(),
        "created_monotonic": created_monotonic,
        "startup_deadline_monotonic": created_monotonic + max(10.0, grace_seconds + 5.0),
        "startup_deadline_epoch": time.time() + max(10.0, grace_seconds + 5.0),
        "environment": _safe_env_snapshot(),
        "log_path": str(p["log"]),
        "cancel_path": str(p["cancel"]),
        "outcome_path": str(p["outcome"]),
        "publish_fence_path": str(p["publish_fence"]),
        "job_enforcement": "win32_job_object" if job_object_name else "process_tree_snapshot",
        "job_object_name": job_object_name,
    }
    _atomic_json(p["spec"], spec)  # receipt BEFORE any process creation

    actual_broker = "wmi" if (sys.platform == "win32" and broker in {"auto", "wmi"}) else "detached"
    watchdog_cmd = _role_command("_watchdog", state_root, job_id)
    supervisor_cmd = _role_command("_supervise", state_root, job_id)
    try:
        if actual_broker == "wmi":
            watchdog_pid, supervisor_pid = _wmi_create_pair([watchdog_cmd, supervisor_cmd])
            survival_bar = "recursive-controller-tree"
        else:
            watchdog_pid = _detached_create(watchdog_cmd)
            supervisor_pid = _detached_create(supervisor_cmd)
            survival_bar = "direct-parent-only"
        launch = {
            "schema": SCHEMA,
            "job_id": job_id,
            "state": "launching",
            "broker": actual_broker,
            "survival_bar": survival_bar,
            "controller_pid": os.getpid(),
            "watchdog_pid": watchdog_pid,
            "supervisor_pid": supervisor_pid,
            "launched_at": _iso_now(),
            "launched_epoch": time.time(),
        }
        _atomic_json(p["launch"], launch)
    except Exception as exc:
        failure = {
            "schema": SCHEMA,
            "job_id": job_id,
            "state": "launch_failed",
            "reported_by": "launcher",
            "error": f"{type(exc).__name__}: {exc}",
            "failed_at": _iso_now(),
        }
        _atomic_json(p["launch"], failure)
        raise

    out = read_status(job_id, state_root)
    out["reused"] = False
    return out


def request_cancel(job_id: str, *, state_dir: os.PathLike[str] | str = DEFAULT_STATE_DIR,
                   reason: str = "operator request") -> Dict[str, Any]:
    p = _paths(state_dir, job_id)
    if not p["spec"].exists():
        raise JobError(f"unknown job {job_id!r}")
    current = read_status(job_id, state_dir)
    if str(current.get("state")) in TERMINAL:
        current["cancel_requested"] = False
        current["cancel_ignored"] = "already_terminal"
        return current
    _atomic_json(p["cancel"], {
        "schema": SCHEMA,
        "job_id": job_id,
        "reason": str(reason or "operator request"),
        "requested_at": _iso_now(),
        "requested_epoch": time.time(),
        "requested_monotonic": time.monotonic(),
        "requested_by_pid": os.getpid(),
    })
    out = read_status(job_id, state_dir)
    out["cancel_requested"] = True
    return out


# ---- guard roles --------------------------------------------------------------------------

def _wait_watchdog_ready(p: Dict[str, Path], deadline: float,
                         stale_after: float = 2.0,
                         expected_job_name: Optional[str] = None) -> Dict[str, Any]:
    while time.monotonic() < deadline:
        rec = _read_json(p["watchdog"])
        if (
            rec.get("ready")
            and rec.get("state") == "watching"
            and not _heartbeat_stale(rec, "heartbeat_epoch", stale_after)
            and _matches_identity(rec.get("watchdog_pid"), rec.get("watchdog_identity"))
            and (
                not expected_job_name
                or (
                    rec.get("job_assigned") is True
                    and rec.get("job_object_name") == expected_job_name
                )
            )
        ):
            return rec
        if str(rec.get("state") or "") in TERMINAL:
            return {}
        time.sleep(0.02)
    return {}


def _supervise(job_id: str, state_dir: Path) -> int:
    p = _paths(state_dir, job_id)
    spec = _read_json(p["spec"])
    if not spec:
        return 2
    hb = float(spec["heartbeat_seconds"])
    status: Dict[str, Any] = {
        "schema": SCHEMA,
        "job_id": job_id,
        "state": "starting",
        "reported_by": "supervisor",
        "supervisor_pid": os.getpid(),
        "supervisor_identity": _process_info(os.getpid())[1],
        "started_at": _iso_now(),
        "started_epoch": time.time(),
        "heartbeat_epoch": time.time(),
        "sequence": 1,
        "log_path": str(p["log"]),
    }
    _atomic_json(p["status"], status)
    ready_deadline = min(float(spec["startup_deadline_monotonic"]), time.monotonic() + 8.0)
    expected_job_name = str(spec.get("job_object_name") or "")
    ready = _wait_watchdog_ready(
        p,
        ready_deadline,
        max(0.2, hb * 4.0),
        expected_job_name or None,
    )
    if not ready:
        status.update({
            "state": "launch_failed",
            "error": "watchdog did not publish ready receipt; worker was not started",
            "finished_at": _iso_now(),
            "heartbeat_epoch": time.time(),
            "sequence": 2,
        })
        _atomic_json(p["status"], status)
        return 2
    supervisor_job_handle: Any = None
    if expected_job_name and sys.platform == "win32":
        try:
            supervisor_job_handle = _win_open_job(expected_job_name, _JOB_OBJECT_QUERY)
        except OSError as exc:
            status.update({
                "state": "launch_failed",
                "error": f"supervisor could not independently open its Job Object: {exc}",
                "deadline_enforced": False,
                "finished_at": _iso_now(),
                "heartbeat_epoch": time.time(),
                "sequence": 2,
            })
            _atomic_json(p["status"], status)
            return 2
        if not _win_process_in_job(
            supervisor_job_handle, os.getpid(), status.get("supervisor_identity"),
        ):
            _win_close_handle(supervisor_job_handle)
            status.update({
                "state": "launch_failed",
                "error": "watchdog ready receipt did not match live supervisor Job Object membership",
                "deadline_enforced": False,
                "finished_at": _iso_now(),
                "heartbeat_epoch": time.time(),
                "sequence": 2,
            })
            _atomic_json(p["status"], status)
            return 2
        # Intentionally retain this independent handle for the private role's
        # process lifetime. If the watchdog dies, KILL_ON_JOB_CLOSE cannot
        # collapse healthy work; OS process teardown closes it automatically.
        status["supervisor_job_handle_owned"] = True

    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in (spec.get("environment") or {}).items()})
    env["PYTHONUNBUFFERED"] = "1"
    env["AKASHIC_JOB_CANCEL_FILE"] = str(p["cancel"])
    env["AKASHIC_JOB_OUTCOME_FILE"] = str(p["outcome"])
    env["AKASHIC_JOB_PUBLISH_FENCE"] = str(p["publish_fence"])
    if expected_job_name:
        env["AKASHIC_JOB_OBJECT_NAME"] = expected_job_name
        env["AKASHIC_JOB_ENFORCEMENT"] = "win32_job_object"
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    proc: Optional[subprocess.Popen[Any]] = None
    child_identity: Optional[str] = None
    try:
        p["log"].parent.mkdir(parents=True, exist_ok=True)
        with open(p["log"], "a", encoding="utf-8", buffering=1, errors="replace") as log:
            log.write(f"[{_iso_now()}] T093 job {job_id} starting\n")
            log.flush()
            os.fsync(log.fileno())
            proc = subprocess.Popen(
                [str(x) for x in spec["command"]],
                cwd=str(spec["cwd"]),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=creationflags,
                start_new_session=(sys.platform != "win32"),
            )
            identity_deadline = time.monotonic() + 1.0
            while child_identity is None and time.monotonic() < identity_deadline:
                child_identity = _process_info(proc.pid)[1]
                if child_identity is None:
                    time.sleep(0.01)
            if child_identity is None:
                proc.kill()
                raise JobError("could not acquire child creation identity; refused unsafely supervised run")
            if expected_job_name and sys.platform == "win32" and not _win_named_job_contains(
                expected_job_name, proc.pid, child_identity,
            ):
                proc.kill()
                proc.wait(timeout=2)
                raise JobError(
                    "worker did not inherit the watchdog-owned Job Object; refused unsafe run"
                )
            deadline_monotonic = time.monotonic() + float(spec["max_runtime"])
            status.update({
                "state": "running",
                "child_pid": proc.pid,
                "child_identity": child_identity,
                "child_started_at": _iso_now(),
                "child_started_epoch": time.time(),
                "deadline_monotonic": deadline_monotonic,
                "deadline_at_epoch": time.time() + float(spec["max_runtime"]),
                "deadline_enforced": True,
                "job_enforcement": spec.get("job_enforcement"),
                "job_object_name": spec.get("job_object_name"),
                "job_membership_verified": bool(expected_job_name),
                "sequence": 2,
                "heartbeat_epoch": time.time(),
            })
            _atomic_json(p["status"], status)

            while True:
                code = proc.poll()
                if code is not None:
                    workload_member_pids: list[int] = []
                    if supervisor_job_handle:
                        members = _win_job_members(supervisor_job_handle)
                        workload_member_pids = [
                            member_pid for member_pid in members
                            if member_pid != os.getpid()
                        ]
                        if workload_member_pids:
                            status.update({
                                "state": "quiescing",
                                "root_exit_code": int(code),
                                "child_alive": False,
                                "job_quiescent": False,
                                "workload_member_pids_remaining": workload_member_pids,
                                "heartbeat_epoch": time.time(),
                                "heartbeat_at": _iso_now(),
                                "sequence": int(status.get("sequence", 2)) + 1,
                                "log_bytes": p["log"].stat().st_size if p["log"].exists() else 0,
                            })
                            _atomic_json(p["status"], status)
                            time.sleep(hb)
                            continue
                    cancel = _read_json(p["cancel"])
                    watchdog = _read_json(p["watchdog"])
                    outcome = _read_json(p["outcome"])
                    forced = bool(
                        watchdog.get("forced")
                        and (watchdog.get("kill_receipt") or {}).get("force_applied")
                    )
                    reason = str(cancel.get("reason") or "")
                    if cancel and code not in {0, 130} and not forced:
                        # A direct TerminateProcess can make poll() return before the
                        # sibling watchdog fsyncs its force receipt.  Keep the primary
                        # state nonterminal for one bounded attribution join instead of
                        # leaking a transient generic `failed` verdict to fresh pollers.
                        attribution_deadline = time.monotonic() + max(
                            0.5,
                            min(5.0, hb * 4.0 + float(spec["grace_seconds"])),
                        )
                        while time.monotonic() < attribution_deadline:
                            watchdog = _read_json(p["watchdog"])
                            forced = bool(
                                watchdog.get("forced")
                                and (watchdog.get("kill_receipt") or {}).get("force_applied")
                            )
                            if forced or str(watchdog.get("state") or "") in TERMINAL:
                                break
                            time.sleep(min(0.02, hb))
                    outcome_state = str(outcome.get("state") or "")
                    pushed = outcome.get("primary_effect") == "pushed"
                    extra: Dict[str, Any] = {}
                    if pushed:
                        extra.update(outcome)
                    if outcome_state == "succeeded" and pushed:
                        state, cause, quiesce = "succeeded", "published_outcome", "not_requested"
                        extra.update(outcome)
                        if cancel:
                            extra.update({
                                "cancel_requested": True,
                                "cancel_disposition": "after_publish_commit_point",
                            })
                    elif outcome_state == "publish_active":
                        state = "outcome_unknown"
                        cause = "publish_fence_abandoned_without_terminal_outcome"
                        quiesce = "unknown"
                        extra.update({
                            **outcome,
                            "primary_effect": "unknown",
                            "publish_may_have_occurred": True,
                        })
                    elif outcome_state == "outcome_unknown":
                        state, cause, quiesce = "outcome_unknown", "child_reported_uncertainty", "unknown"
                        extra.update(outcome)
                    elif forced:
                        state = "deadline_exceeded" if reason == "deadline" else "cancelled"
                        cause = reason or "cancel_requested"
                        quiesce = "forced"
                    elif code == 130 and cancel:
                        state = "deadline_exceeded" if reason == "deadline" else "cancelled"
                        cause = reason or "cancel_requested"
                        quiesce = "cooperative"
                    elif code == 0:
                        state, cause, quiesce = "succeeded", "exit_zero", "not_requested"
                        if pushed:
                            extra.update(outcome)
                            if cancel:
                                extra["cancel_disposition"] = "after_publish_commit_point"
                    else:
                        # Windows taskkill /F and a deliberate sys.exit(1) are observationally
                        # identical to the parent.  Preserve the uncertainty instead of inventing it.
                        state, cause, quiesce = "failed", "unattributed_nonzero_exit", "not_requested"
                    extra.pop("state", None)
                    status.update({
                        "state": state,
                        "exit_code": int(code),
                        "termination_cause": cause,
                        "quiesce": quiesce,
                        "forced": forced,
                        "child_alive": False,
                        "job_quiescent": True,
                        "workload_member_pids_remaining": [],
                        "finished_at": _iso_now(),
                        "finished_epoch": time.time(),
                        "heartbeat_epoch": time.time(),
                        "sequence": int(status.get("sequence", 2)) + 1,
                        **extra,
                    })
                    _atomic_json(p["status"], status)
                    return 0 if state in {"succeeded", "cancelled"} else 1
                status.update({
                    "heartbeat_epoch": time.time(),
                    "heartbeat_at": _iso_now(),
                    "sequence": int(status.get("sequence", 2)) + 1,
                    "log_bytes": p["log"].stat().st_size if p["log"].exists() else 0,
                })
                _atomic_json(p["status"], status)
                time.sleep(hb)
    except Exception as exc:
        cleanup: Dict[str, Any] = {}
        child_alive = False
        if proc is not None:
            if proc.poll() is None:
                if child_identity:
                    try:
                        cleanup = _kill_tree(proc.pid, child_identity)
                    except Exception as kill_exc:
                        cleanup = {
                            "killed": False,
                            "identity_match": True,
                            "detail": f"{type(kill_exc).__name__}: {kill_exc}",
                        }
                else:
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                        cleanup = {
                            "killed": proc.poll() is not None,
                            "identity_match": False,
                            "detail": "direct-handle fallback before identity acquisition",
                        }
                    except Exception as kill_exc:
                        cleanup = {
                            "killed": False,
                            "identity_match": False,
                            "detail": f"{type(kill_exc).__name__}: {kill_exc}",
                        }
            else:
                cleanup = {"killed": True, "already_dead": True, "identity_match": True}
            child_alive = _matches_identity(proc.pid, child_identity) if child_identity else proc.poll() is None
        failure_state = "supervision_lost" if child_alive else "launch_failed"
        status.update({
            "state": failure_state,
            "reported_by": "supervisor",
            "error": f"{type(exc).__name__}: {exc}",
            "prearm_cleanup": cleanup,
            "child_pid": proc.pid if proc is not None else None,
            "child_identity": child_identity,
            "child_alive": child_alive,
            "deadline_enforced": False,
            "finished_at": _iso_now(),
            "heartbeat_epoch": time.time(),
            "sequence": int(status.get("sequence", 1)) + 1,
        })
        _atomic_json(p["status"], status)
        return 2


def _force_owned_job(job_handle: Any, child_pid: int,
                     child_identity: str) -> Dict[str, Any]:
    if sys.platform == "win32" and job_handle:
        return _win_terminate_owned_job(job_handle, child_pid, child_identity)
    return _kill_tree(child_pid, child_identity)


def _watchdog(job_id: str, state_dir: Path) -> int:
    p = _paths(state_dir, job_id)
    spec = _read_json(p["spec"])
    if not spec:
        return 2
    hb = float(spec["heartbeat_seconds"])
    record: Dict[str, Any] = {
        "schema": SCHEMA,
        "job_id": job_id,
        "state": "watching",
        "reported_by": "watchdog",
        "watchdog_pid": os.getpid(),
        "watchdog_identity": _process_info(os.getpid())[1],
        "ready": False,
        "started_at": _iso_now(),
        "heartbeat_epoch": time.time(),
        "sequence": 1,
        "deadline_enforced": False,
    }
    job_name = str(spec.get("job_object_name") or "")
    job_handle: Any = None
    try:
        if sys.platform == "win32" and job_name:
            job_handle = _win_create_kill_job(job_name)
            record.update({
                "job_object_name": job_name,
                "job_enforcement": "win32_job_object",
                "phase": "awaiting_supervisor_job_assignment",
            })
            _atomic_json(p["watchdog"], record)
            startup_deadline = float(spec["startup_deadline_monotonic"])
            assignment: Dict[str, Any] = {}
            while time.monotonic() < startup_deadline:
                status = _read_json(p["status"])
                supervisor_pid = status.get("supervisor_pid")
                supervisor_identity = status.get("supervisor_identity")
                if supervisor_pid and supervisor_identity:
                    assignment = _win_assign_exact_to_job(
                        job_handle, int(supervisor_pid), str(supervisor_identity),
                    )
                    if assignment.get("assigned"):
                        record.update({
                            "ready": True,
                            "job_assigned": True,
                            "job_assignment": assignment,
                            "supervisor_pid": int(supervisor_pid),
                            "supervisor_identity": str(supervisor_identity),
                            "phase": "supervisor_job_owned",
                            "heartbeat_epoch": time.time(),
                            "sequence": int(record.get("sequence", 1)) + 1,
                            "deadline_enforced": True,
                        })
                        break
                    record.update({
                        "state": "launch_failed",
                        "ready": False,
                        "job_assigned": False,
                        "job_assignment": assignment,
                        "error": "could not place supervisor in watchdog-owned Job Object",
                        "finished_at": _iso_now(),
                        "heartbeat_epoch": time.time(),
                        "sequence": int(record.get("sequence", 1)) + 1,
                        "deadline_enforced": False,
                    })
                    _atomic_json(p["watchdog"], record)
                    return 2
                record.update({
                    "heartbeat_epoch": time.time(),
                    "heartbeat_at": _iso_now(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                time.sleep(min(hb, 0.05))
            if not record.get("job_assigned"):
                record.update({
                    "state": "launch_failed",
                    "ready": False,
                    "job_assigned": False,
                    "error": "supervisor was not assigned before the startup deadline",
                    "finished_at": _iso_now(),
                    "heartbeat_epoch": time.time(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                    "deadline_enforced": False,
                })
                _atomic_json(p["watchdog"], record)
                return 2
        else:
            # Legacy/unit and POSIX paths retain the identity-checked process-tree
            # enforcer. Windows public launches always carry a unique Job Object name.
            record.update({
                "ready": True,
                "job_assigned": False,
                "job_enforcement": "process_tree_snapshot",
                "deadline_enforced": True,
            })
        _atomic_json(p["watchdog"], record)
        return _watchdog_loop(job_id, p, spec, record, job_handle)
    except Exception as exc:
        record.update({
            "state": "launch_failed",
            "ready": False,
            "error": f"{type(exc).__name__}: {exc}",
            "deadline_enforced": False,
            "finished_at": _iso_now(),
            "heartbeat_epoch": time.time(),
            "sequence": int(record.get("sequence", 1)) + 1,
        })
        _atomic_json(p["watchdog"], record)
        return 2
    finally:
        _win_close_handle(job_handle)


def _watchdog_loop(job_id: str, p: Dict[str, Path], spec: Dict[str, Any],
                   record: Dict[str, Any], job_handle: Any = None) -> int:
    hb = float(spec["heartbeat_seconds"])
    stale_after = max(0.2, hb * 4.0)
    child_pid: Optional[int] = None
    child_identity: Optional[str] = None
    deadline_monotonic: Optional[float] = None
    quiesce_started: Optional[float] = None
    terminal_outcome_seen: Optional[float] = None

    while True:
        now_mono = time.monotonic()
        now_epoch = time.time()
        status = _read_json(p["status"])
        state = str(status.get("state") or "")

        if status.get("child_pid") and status.get("child_identity"):
            child_pid = int(status["child_pid"])
            child_identity = str(status["child_identity"])
            deadline_monotonic = float(status["deadline_monotonic"])

        if child_pid is None:
            if now_mono >= float(spec["startup_deadline_monotonic"]):
                record.update({
                    "state": "launch_failed",
                    "error": "supervisor never published a child identity before startup deadline",
                    "deadline_enforced": False,
                    "heartbeat_epoch": now_epoch,
                    "finished_at": _iso_now(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                return 2
            record.update({
                "heartbeat_epoch": now_epoch,
                "heartbeat_at": _iso_now(),
                "sequence": int(record.get("sequence", 1)) + 1,
                "phase": "awaiting_worker",
            })
            _atomic_json(p["watchdog"], record)
            time.sleep(hb)
            continue

        supervisor_pid = status.get("supervisor_pid")
        supervisor_identity = status.get("supervisor_identity")
        supervisor_alive = (
            _matches_identity(supervisor_pid, str(supervisor_identity))
            if supervisor_pid and supervisor_identity
            else (_process_info(supervisor_pid)[0] if supervisor_pid else False)
        )
        supervisor_stale = bool(
            not supervisor_alive or _heartbeat_stale(status, "heartbeat_epoch", stale_after)
        )
        cancel = _read_json(p["cancel"])
        outcome = _read_json(p["outcome"])
        outcome_state = str(outcome.get("state") or "")
        pushed = outcome.get("primary_effect") == "pushed"
        alive = _matches_identity(child_pid, child_identity)
        job_member_pids: list[int] = []
        workload_member_pids: list[int] = []
        if sys.platform == "win32" and job_handle:
            job_member_pids = _win_job_members(job_handle)
            exclude_supervisor = bool(
                supervisor_alive and supervisor_pid and supervisor_identity
                and _win_process_in_job(
                    job_handle, int(supervisor_pid), str(supervisor_identity),
                )
            )
            workload_member_pids = [
                member_pid for member_pid in job_member_pids
                if not (exclude_supervisor and member_pid == int(supervisor_pid))
            ]
            workload_alive = bool(workload_member_pids)
        else:
            workload_alive = alive
            if alive:
                workload_member_pids = [int(child_pid)]

        if state in TERMINAL:
            if workload_alive:
                # A terminal candidate cannot outrank retained mutation capability.
                # Demote the shared receipt so fresh readers never observe the
                # supervisor/watchdog race as completed work.
                status.update({
                    "state": "quiescing",
                    "terminal_candidate": state,
                    "job_quiescent": False,
                    "workload_member_pids_remaining": workload_member_pids,
                    "heartbeat_epoch": now_epoch,
                    "heartbeat_at": _iso_now(),
                    "sequence": int(status.get("sequence", 1)) + 1,
                })
                _atomic_json(p["status"], status)
                record.update({
                    "state": "watching",
                    "phase": "terminal_candidate_waiting_job_quiescence",
                    "observed_terminal_candidate": state,
                    "job_quiescent": False,
                    "workload_member_pids_remaining": workload_member_pids,
                    "heartbeat_epoch": now_epoch,
                    "heartbeat_at": _iso_now(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                time.sleep(hb)
                continue
            record.update({
                "state": "complete_observed",
                "observed_terminal": state,
                "job_quiescent": True,
                "workload_member_pids_remaining": [],
                "heartbeat_epoch": now_epoch,
                "sequence": int(record.get("sequence", 1)) + 1,
            })
            _atomic_json(p["watchdog"], record)
            return 0

        deadline_hit = bool(deadline_monotonic is not None and now_mono >= deadline_monotonic)
        if deadline_hit and workload_alive and not cancel:
            cancel = {
                "schema": SCHEMA,
                "job_id": job_id,
                "reason": "deadline",
                "requested_at": _iso_now(),
                "requested_epoch": now_epoch,
                "requested_monotonic": now_mono,
                "requested_by_pid": os.getpid(),
            }
            _atomic_json(p["cancel"], cancel)

        if cancel:
            if quiesce_started is None:
                quiesce_started = now_mono
            reason = str(cancel.get("reason") or "cancel")

            if outcome_state == "outcome_unknown":
                if workload_alive and now_mono < quiesce_started + float(spec["grace_seconds"]):
                    record.update({
                        "heartbeat_epoch": now_epoch,
                        "heartbeat_at": _iso_now(),
                        "sequence": int(record.get("sequence", 1)) + 1,
                        "phase": "quiescing_uncertain_publish",
                        "deadline_enforced": False,
                    })
                    _atomic_json(p["watchdog"], record)
                    time.sleep(hb)
                    continue
                with publish_fence(p["publish_fence"], blocking=False) as may_force:
                    if not may_force:
                        record.update({
                            "state": "watching",
                            "heartbeat_epoch": now_epoch,
                            "heartbeat_at": _iso_now(),
                            "sequence": int(record.get("sequence", 1)) + 1,
                            "phase": "cancel_pending_critical",
                            "force_deferred_by": "publish_fence",
                            "deadline_enforced": False,
                        })
                        _atomic_json(p["watchdog"], record)
                        time.sleep(hb)
                        continue
                    killed = _force_owned_job(job_handle, child_pid, child_identity) if workload_alive else {
                        "killed": True, "already_dead": True, "identity_match": True,
                    }
                record.update({
                    **outcome,
                    "state": "outcome_unknown",
                    "reported_by": "watchdog",
                    "kill_receipt": killed,
                    "forced": bool(killed.get("force_applied")),
                    "child_pid": child_pid,
                    "child_identity": child_identity,
                    "child_alive": _matches_identity(child_pid, child_identity),
                    "workload_alive": bool(workload_alive),
                    "workload_member_pids_remaining": (
                        _win_job_members(job_handle) if job_handle else []
                    ),
                    "deadline_enforced": False,
                    "finished_at": _iso_now(),
                    "heartbeat_epoch": time.time(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                return 1

            if outcome_state in {"succeeded", "published"} and pushed:
                if outcome_state == "succeeded" and terminal_outcome_seen is None:
                    terminal_outcome_seen = now_mono
                if not workload_alive:
                    record.update({
                        **outcome,
                        "state": "succeeded",
                        "reported_by": "child_outcome",
                        "cancel_requested": True,
                        "cancel_disposition": "after_publish_commit_point",
                        "child_pid": child_pid,
                        "child_identity": child_identity,
                        "child_alive": False,
                        "workload_alive": False,
                        "workload_member_pids_remaining": [],
                        "deadline_enforced": False,
                        "finished_at": _iso_now(),
                        "heartbeat_epoch": now_epoch,
                        "sequence": int(record.get("sequence", 1)) + 1,
                    })
                    _atomic_json(p["watchdog"], record)
                    return 0
                cleanup_after = (
                    terminal_outcome_seen + max(0.5, float(spec["grace_seconds"]))
                    if outcome_state == "succeeded" and terminal_outcome_seen is not None
                    else quiesce_started + float(spec["grace_seconds"])
                )
                if now_mono >= cleanup_after:
                    with publish_fence(p["publish_fence"], blocking=False) as may_force:
                        if may_force:
                            killed = _force_owned_job(job_handle, child_pid, child_identity)
                            if killed.get("identity_match") and killed.get("killed"):
                                record.update({
                                    **outcome,
                                    "state": "succeeded",
                                    "reported_by": "watchdog",
                                    "cancel_requested": True,
                                    "cancel_disposition": "after_publish_commit_point",
                                    "post_publish_incomplete": True,
                                    "forced": bool(killed.get("force_applied")),
                                    "kill_receipt": killed,
                                    "child_pid": child_pid,
                                    "child_identity": child_identity,
                                    "child_alive": False,
                                    "deadline_enforced": False,
                                    "finished_at": _iso_now(),
                                    "heartbeat_epoch": time.time(),
                                    "sequence": int(record.get("sequence", 1)) + 1,
                                })
                                _atomic_json(p["watchdog"], record)
                                return 0
                            record.update({
                                **outcome,
                                "state": "supervision_lost",
                                "reported_by": "watchdog",
                                "termination_cause": "post_publish_cleanup_not_confirmed",
                                "kill_receipt": killed,
                                "child_alive": _matches_identity(child_pid, child_identity),
                                "deadline_enforced": False,
                                "finished_at": _iso_now(),
                                "heartbeat_epoch": time.time(),
                                "sequence": int(record.get("sequence", 1)) + 1,
                            })
                            _atomic_json(p["watchdog"], record)
                            return 3
                record.update({
                    "heartbeat_epoch": now_epoch,
                    "heartbeat_at": _iso_now(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                    "phase": "publish_complete_waiting_worker_exit",
                    "force_deferred_by": "publish_fence_or_grace",
                    "deadline_enforced": False,
                    "cancel_requested": True,
                })
                _atomic_json(p["watchdog"], record)
                time.sleep(hb)
                continue

            if outcome_state == "publish_active":
                with publish_fence(p["publish_fence"], blocking=False) as may_force:
                    if not may_force:
                        record.update({
                            "state": "watching",
                            "heartbeat_epoch": now_epoch,
                            "heartbeat_at": _iso_now(),
                            "sequence": int(record.get("sequence", 1)) + 1,
                            "phase": "cancel_pending_critical",
                            "force_deferred_by": "publish_fence",
                            "deadline_enforced": False,
                            "cancel_requested": True,
                        })
                        _atomic_json(p["watchdog"], record)
                        time.sleep(hb)
                        continue
                    # Fence acquisition and this re-read form the force/publish
                    # decision boundary; the child cannot begin commit/push now.
                    outcome = _read_json(p["outcome"])
                    outcome_state = str(outcome.get("state") or "")
                    pushed = outcome.get("primary_effect") == "pushed"
                    if outcome_state == "succeeded" and pushed:
                        continue
                    killed = _force_owned_job(job_handle, child_pid, child_identity) if workload_alive else {
                        "killed": True, "already_dead": True, "identity_match": True,
                    }
                    record.update({
                        **outcome,
                        "state": "outcome_unknown",
                        "reported_by": "watchdog",
                        "termination_cause": "publish_fence_abandoned_without_terminal_outcome",
                        "primary_effect": "unknown",
                        "publish_may_have_occurred": True,
                        "kill_receipt": killed,
                        "forced": bool(killed.get("force_applied")),
                        "child_pid": child_pid,
                        "child_identity": child_identity,
                        "child_alive": _matches_identity(child_pid, child_identity),
                        "workload_alive": bool(workload_alive),
                        "supervisor_lost": supervisor_stale,
                        "deadline_enforced": False,
                        "finished_at": _iso_now(),
                        "heartbeat_epoch": time.time(),
                        "sequence": int(record.get("sequence", 1)) + 1,
                    })
                    _atomic_json(p["watchdog"], record)
                    return 1

            if not workload_alive:
                if not supervisor_stale:
                    record.update({
                        "heartbeat_epoch": now_epoch,
                        "heartbeat_at": _iso_now(),
                        "sequence": int(record.get("sequence", 1)) + 1,
                        "phase": "awaiting_supervisor_exit_attribution",
                        "child_alive": False,
                    })
                    _atomic_json(p["watchdog"], record)
                    time.sleep(hb)
                    continue
                record.update({
                    "state": "outcome_unknown",
                    "termination_cause": "worker_gone_before_cancel_attribution",
                    "quiesce": "unknown",
                    "forced": False,
                    "child_pid": child_pid,
                    "child_identity": child_identity,
                    "child_alive": False,
                    "workload_alive": False,
                    "workload_member_pids_remaining": [],
                    "supervisor_lost": True,
                    "deadline_enforced": False,
                    "finished_at": _iso_now(),
                    "heartbeat_epoch": now_epoch,
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                return 1
            if now_mono >= quiesce_started + float(spec["grace_seconds"]):
                with publish_fence(p["publish_fence"], blocking=False) as may_force:
                    if not may_force:
                        record.update({
                            "state": "watching",
                            "heartbeat_epoch": now_epoch,
                            "heartbeat_at": _iso_now(),
                            "sequence": int(record.get("sequence", 1)) + 1,
                            "phase": "cancel_pending_critical",
                            "force_deferred_by": "publish_fence",
                            "deadline_enforced": False,
                        })
                        _atomic_json(p["watchdog"], record)
                        time.sleep(hb)
                        continue
                    outcome = _read_json(p["outcome"])
                    if outcome.get("state") == "succeeded" and outcome.get("primary_effect") == "pushed":
                        continue
                    killed = _force_owned_job(job_handle, child_pid, child_identity)
                force_applied = bool(killed.get(
                    "force_applied",
                    killed.get("killed") and not killed.get("already_dead"),
                ))
                if killed.get("killed") and not force_applied:
                    if not supervisor_stale:
                        record.update({
                            "heartbeat_epoch": now_epoch,
                            "heartbeat_at": _iso_now(),
                            "sequence": int(record.get("sequence", 1)) + 1,
                            "phase": "awaiting_supervisor_exit_attribution",
                            "forced": False,
                            "kill_receipt": killed,
                            "child_alive": _matches_identity(child_pid, child_identity),
                            "deadline_enforced": False,
                        })
                        _atomic_json(p["watchdog"], record)
                        time.sleep(hb)
                        continue
                    record.update({
                        "state": "outcome_unknown",
                        "termination_cause": "worker_already_dead_before_force_attribution",
                        "quiesce": "unknown",
                        "forced": False,
                        "kill_receipt": killed,
                        "child_pid": child_pid,
                        "child_identity": child_identity,
                        "child_alive": False,
                        "supervisor_lost": True,
                        "deadline_enforced": False,
                        "finished_at": _iso_now(),
                        "heartbeat_epoch": now_epoch,
                        "sequence": int(record.get("sequence", 1)) + 1,
                    })
                    _atomic_json(p["watchdog"], record)
                    return 1
                if not killed.get("identity_match", False) or not killed.get("killed", False):
                    child_still_alive = _matches_identity(child_pid, child_identity)
                    cause = (
                        "pid_creation_identity_mismatch"
                        if not killed.get("identity_match", False)
                        else "force_kill_not_confirmed"
                    )
                    record.update({
                        "state": "supervision_lost",
                        "termination_cause": cause,
                        "kill_receipt": killed,
                        "child_pid": child_pid,
                        "child_identity": child_identity,
                        "child_alive": child_still_alive,
                        "supervisor_lost": supervisor_stale,
                        "deadline_enforced": False,
                        "finished_at": _iso_now(),
                        "heartbeat_epoch": now_epoch,
                        "sequence": int(record.get("sequence", 1)) + 1,
                    })
                    _atomic_json(p["watchdog"], record)
                    return 3
                final_state = "deadline_exceeded" if reason == "deadline" else "cancelled"
                record.update({
                    "state": final_state,
                    "termination_cause": reason,
                    "quiesce": "forced",
                    "forced": force_applied,
                    "kill_receipt": killed,
                    "child_pid": child_pid,
                    "child_identity": child_identity,
                    "child_alive": False,
                    "supervisor_lost": supervisor_stale,
                    "deadline_enforced": force_applied,
                    "finished_at": _iso_now(),
                    "heartbeat_epoch": time.time(),
                    "sequence": int(record.get("sequence", 1)) + 1,
                })
                _atomic_json(p["watchdog"], record)
                return 0
            phase = "quiescing"
        elif not workload_alive:
            # Give a live supervisor one short beat to publish the exact return code.
            if not supervisor_stale:
                time.sleep(min(0.1, hb))
                continue
            record.update({
                "state": "outcome_unknown",
                "termination_cause": "worker_gone_after_supervisor_loss",
                "child_pid": child_pid,
                "child_identity": child_identity,
                "child_alive": False,
                "workload_alive": False,
                "workload_member_pids_remaining": [],
                "supervisor_lost": True,
                "deadline_enforced": False,
                "finished_at": _iso_now(),
                "heartbeat_epoch": now_epoch,
                "sequence": int(record.get("sequence", 1)) + 1,
            })
            _atomic_json(p["watchdog"], record)
            return 1
        else:
            if not alive:
                phase = (
                    "supervisor_lost_guarding_retained_workload"
                    if supervisor_stale
                    else "root_exited_guarding_retained_workload"
                )
            else:
                phase = "supervisor_lost_guarding_worker" if supervisor_stale else "watching_worker"

        record.update({
            "heartbeat_epoch": now_epoch,
            "heartbeat_at": _iso_now(),
            "sequence": int(record.get("sequence", 1)) + 1,
            "phase": phase,
            "child_pid": child_pid,
            "child_identity": child_identity,
            "child_alive": alive,
            "workload_alive": bool(workload_alive),
            "workload_member_pids_remaining": workload_member_pids,
            "supervisor_lost": supervisor_stale,
            "deadline_monotonic": deadline_monotonic,
            "deadline_enforced": True,
        })
        record.pop("force_deferred_by", None)
        _atomic_json(p["watchdog"], record)
        time.sleep(hb)


# ---- CLI ----------------------------------------------------------------------------------

def _print(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str), flush=True)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="durable controller-independent one-shot job runner")
    sub = ap.add_subparsers(dest="verb", required=True)

    launch = sub.add_parser("launch", help="write spec, broker guards, return immediately")
    launch.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    launch.add_argument("--job-id", required=True)
    launch.add_argument("--cwd", default=str(ROOT))
    launch.add_argument("--max-runtime", type=float, default=3600.0)
    launch.add_argument("--grace-seconds", type=float, default=5.0)
    launch.add_argument("--heartbeat-seconds", type=float, default=1.0)
    launch.add_argument("--broker", choices=("auto", "wmi", "detached"), default="auto")
    launch.add_argument("command", nargs=argparse.REMAINDER)

    status = sub.add_parser("status", help="reconstruct job state from disk in a fresh process")
    status.add_argument("job_id")
    status.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    status.add_argument("--stale-after", type=float, default=10.0)

    cancel = sub.add_parser("cancel", help="publish cooperative cancel, then watchdog owns force")
    cancel.add_argument("job_id")
    cancel.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    cancel.add_argument("--reason", default="operator request")

    for role in ("_supervise", "_watchdog"):
        hidden = sub.add_parser(role, help=argparse.SUPPRESS)
        hidden.add_argument("job_id")
        hidden.add_argument("--state-dir", required=True)
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.verb == "launch":
            command = list(args.command)
            if command and command[0] == "--":
                command = command[1:]
            out = launch_job(
                command,
                job_id=args.job_id,
                state_dir=args.state_dir,
                cwd=args.cwd,
                max_runtime=args.max_runtime,
                grace_seconds=args.grace_seconds,
                heartbeat_seconds=args.heartbeat_seconds,
                broker=args.broker,
            )
            _print(out)
            return 0
        if args.verb == "status":
            _print(read_status(args.job_id, args.state_dir, args.stale_after))
            return 0
        if args.verb == "cancel":
            _print(request_cancel(args.job_id, state_dir=args.state_dir, reason=args.reason))
            return 0
        if args.verb == "_supervise":
            return _supervise(args.job_id, _as_path(args.state_dir))
        if args.verb == "_watchdog":
            return _watchdog(args.job_id, _as_path(args.state_dir))
        raise JobError(f"unknown verb {args.verb!r}")
    except Exception as exc:
        _print({
            "ok": False,
            "state": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "reported_by": "run_job_cli",
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
