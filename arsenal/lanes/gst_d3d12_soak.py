"""arsenal.lanes.gst_d3d12_soak -- Lane B.1 receipt: GStreamer D3D12 decode soak.

Proves native GPU decode (d3d12h265dec) whose frames stay in D3D12 memory all the way to the
sink, under a soak:
  pass 1      one unsynced pass over the whole file (throughput)
  passes 2..  real-time paced passes (sync=true), looping the file until --duration seconds

CLI:
    python arsenal\\lanes\\gst_d3d12_soak.py [--file PATH] [--duration SECONDS] [--out-dir DIR]

Writes <out-dir>\\lane-b1-gst-d3d12-soak-<YYYYmmdd-HHMMSS>.json. Exit code: 0 when the verdict
passes, 1 when it fails, 2 when gst-launch-1.0 or the input file is missing.

Why a gst-launch-1.0 subprocess instead of PyGObject: the GStreamer 1.28.7 install ships
PyGObject in lib\\site-packages, but its extension is built for CPython 3.9
(_gi.cp39-win_amd64.pyd). Python 3.11 only loads .cp311-win_amd64.pyd or .pyd files, so
`import gi` fails with "cannot import name '_gi'". The receipt re-runs that check and records
the result. Standard library only; headless (frames end in fakevideosink, no window).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

GST_ROOT = Path(r"C:\Users\L5\AppData\Local\Programs\gstreamer\1.0\msvc_x86_64")
GST_LAUNCH = GST_ROOT / "bin" / "gst-launch-1.0.exe"
GST_INSPECT = GST_ROOT / "bin" / "gst-inspect-1.0.exe"
GST_DISCOVERER = GST_ROOT / "bin" / "gst-discoverer-1.0.exe"
GST_SITE_PACKAGES = GST_ROOT / "lib" / "site-packages"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = r"E:\Video Output E\2026-09-13 14-21-37.mp4"
DEFAULT_DURATION_S = 600.0
DEFAULT_OUT_DIR = _REPO_ROOT / "state" / "arsenal" / "receipts"

API = "arsenal.receipt/v0"
LANE = "B.1"
TITLE = "GStreamer D3D12 H.265 decode stays in D3D12 memory under a real-time soak"

DECODER_NAME = "dec"
FPS_SINK_NAME = "fps"
FPS_UPDATE_INTERVAL_MS = 1000
D3D12_CAPS_FEATURE = "memory:D3D12Memory"

# -v prints caps and fpsdisplaysink reports, -m prints bus messages (QoS drops),
# -e sends EOS on shutdown, --no-position keeps progress lines out of stdout.
LAUNCH_FLAGS = ["-v", "-m", "-e", "--no-position"]
# GST_DEBUG=*:2 makes GStreamer print its ERROR and WARN debug lines on stderr.
GST_ENV = {"GST_DEBUG": "*:2", "GST_DEBUG_NO_COLOR": "1"}

MAX_DROP_RATE = 0.001            # 0.1 %
MAX_WORKING_SET_GROWTH_MB = 64.0
MIN_SOAK_PASS_S = 5.0            # skip a final soak pass shorter than this
MAX_STORED_WARNINGS = 200        # per pass; the total count is always kept


# ---------------------------------------------------------------------------------------------
# Parsing helpers for gst-launch-1.0 -v / -m output (pure functions, covered by tests)
# ---------------------------------------------------------------------------------------------

def parse_fps_message(line: str) -> dict | None:
    """Parse an fpsdisplaysink last-message notification.

    fpsdisplaysink writes "rendered: R, dropped: D, current: C, average: A", or, for an
    interval that saw drops, "rendered: R, dropped: D, fps: C, drop rate: X". R and D are
    cumulative. Returns None for any other line.
    """
    marker = ": last-message = "
    if marker not in line:
        return None
    element, message = line.strip().split(marker, 1)
    fields = {}
    for part in message.split(", "):
        key, sep, value = part.partition(": ")
        if not sep:
            return None
        try:
            # A comma decimal separator (non-English locale) survives the ", " split.
            fields[key.strip()] = float(value.strip().replace(",", "."))
        except ValueError:
            return None
    if "rendered" not in fields or "dropped" not in fields:
        return None
    return {
        "element": element,
        "rendered": int(fields["rendered"]),
        "dropped": int(fields["dropped"]),
        "current_fps": fields.get("current", fields.get("fps")),
        "average_fps": fields.get("average"),
        "drop_rate": fields.get("drop rate"),
    }


_CAPS_LINE_RE = re.compile(
    r"^(?P<element>/\S+?)\.(?P<pads>Gst\w*Pad:[^\s:.]+(?:\.Gst\w*Pad:[^\s:.]+)*): caps = (?P<caps>.*)$"
)


def parse_caps_line(line: str) -> dict | None:
    """Parse a caps notification such as
    "/GstPipeline:pipeline0/GstD3D12H265Dec:dec.GstPad:src: caps = video/x-raw(...), ...".

    Ghost pads show up as a pad chain ("fps.GstGhostPad:sink.GstProxyPad:proxypad1").
    """
    match = _CAPS_LINE_RE.match(line.strip())
    if not match:
        return None
    element_path = match.group("element")
    pads = match.group("pads").split(".")
    pad_type, _, pad_name = pads[-1].partition(":")
    return {
        "element_path": element_path,
        "element_name": element_path.rsplit("/", 1)[-1].partition(":")[2],
        "pad_name": pad_name,
        "ghost": len(pads) > 1 or pad_type in ("GstGhostPad", "GstProxyPad"),
        "caps": match.group("caps"),
    }


def decoder_src_caps(caps_events: list[dict], decoder_name: str = DECODER_NAME) -> list[str]:
    """Every caps string negotiated on the decoder's src pad, in order."""
    return [event["caps"] for event in caps_events
            if event["element_name"] == decoder_name and event["pad_name"] == "src"
            and not event["ghost"]]


def final_sink_caps(caps_events: list[dict], sink_bin_name: str = FPS_SINK_NAME) -> dict:
    """Caps on the innermost real sink pad inside the fpsdisplaysink bin: the pad that actually
    receives the buffers (fpsdisplaysink and fakevideosink are bins that only ghost it)."""
    def inside_sink_bin(path: str) -> bool:
        return any(segment.partition(":")[2] == sink_bin_name for segment in path.split("/"))

    candidates = [event for event in caps_events
                  if event["pad_name"] == "sink" and not event["ghost"]
                  and inside_sink_bin(event["element_path"])]
    if not candidates:
        return {"element_path": None, "caps": []}
    deepest = max(candidates, key=lambda event: event["element_path"].count("/"))["element_path"]
    return {"element_path": deepest,
            "caps": [event["caps"] for event in candidates if event["element_path"] == deepest]}


def all_d3d12(caps_list: list[str]) -> bool:
    """True only if caps were seen and every negotiation kept the D3D12 memory feature."""
    return bool(caps_list) and all(D3D12_CAPS_FEATURE in caps for caps in caps_list)


_QOS_RE = re.compile(
    r'^Got message #\d+ from element "(?P<element>[^"]+)" \(qos\): .*?'
    r"processed=\(guint64\)(?P<processed>\d+), dropped=\(guint64\)(?P<dropped>\d+)"
)


def parse_qos_message(line: str) -> dict | None:
    """Parse a QoS bus message printed by gst-launch -m. processed/dropped are cumulative
    per element; both the decoder and the sink post them when they drop a late frame."""
    match = _QOS_RE.match(line.strip())
    if not match:
        return None
    return {"element": match.group("element"),
            "processed": int(match.group("processed")),
            "dropped": int(match.group("dropped"))}


_DEBUG_LOG_RE = re.compile(r"^\d+:\d{2}:\d{2}\.\d+\s+\S+\s+\S+\s+(?P<level>[A-Z]+)\s")


def is_error_or_warning(line: str) -> bool:
    """GStreamer ERROR/WARN debug-log lines, gst-launch ERROR:/WARNING: reports and GLib
    criticals/warnings."""
    text = line.strip()
    if text.startswith(("ERROR:", "WARNING:")):
        return True
    match = _DEBUG_LOG_RE.match(text)
    if match:
        return match.group("level") in ("ERROR", "WARN")
    return "-CRITICAL **" in text or "-WARNING **" in text


_CLOCK_TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})(?:\.(\d+))?")


def parse_clock_time(text: str) -> float | None:
    """Seconds from a GstClockTime string such as "0:02:52.250000000"."""
    match = _CLOCK_TIME_RE.search(text)
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + float(f"0.{fraction or 0}")


def parse_execution_time(line: str) -> float | None:
    """gst-launch's "Execution ended after H:MM:SS.nnnnnnnnn" (time spent in PLAYING)."""
    text = line.strip()
    return parse_clock_time(text) if text.startswith("Execution ended after ") else None


def parse_framerate(caps: str | None) -> float | None:
    match = re.search(r"framerate=\(fraction\)(\d+)/(\d+)", caps or "")
    if not match or int(match.group(2)) == 0:
        return None
    return int(match.group(1)) / int(match.group(2))


def parse_d3d12_device_context(line: str) -> dict | None:
    """The decoder's D3D12 device, from gst-launch's "Got context from element 'dec':
    gst.d3d12.device.handle=context, ... adapter-luid=(gint64)N, ... description=(string)"..."" line."""
    text = line.strip()
    if not text.startswith("Got context from element") or "d3d12.device" not in text:
        return None
    device = {}
    for key, pattern in (("adapter_index", r"adapter-index=\(uint\)(\d+)"),
                         ("adapter_luid", r"adapter-luid=\(gint64\)(-?\d+)"),
                         ("device_id", r"device-id=\(uint\)(\d+)"),
                         ("vendor_id", r"vendor-id=\(uint\)(\d+)")):
        match = re.search(pattern, text)
        device[key] = int(match.group(1)) if match else None
    match = re.search(r'description=\(string\)"((?:[^"\\]|\\.)*)"', text)
    device["description"] = re.sub(r"\\(.)", r"\1", match.group(1)) if match else None
    return device


def percentile(values: list[float], pct: float) -> float | None:
    """Linear-interpolation percentile (numpy's default method); pct in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct / 100.0
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def linear_slope(xs: list[float], ys: list[float]) -> float | None:
    """Least-squares slope of ys over xs; None without at least two distinct xs."""
    n = len(xs)
    if n < 2:
        return None
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx


def luid_instance_key(luid: int) -> str:
    """Adapter LUID as it appears in GPU performance-counter instance names (lower-cased):
    129573 -> "0x00000000_0x0001fa25"."""
    return f"0x{(luid >> 32) & 0xFFFFFFFF:08x}_0x{luid & 0xFFFFFFFF:08x}"


# ---------------------------------------------------------------------------------------------
# Windows process memory and per-process GPU memory (ctypes, loaded lazily so the parsing
# helpers above import on any platform)
# ---------------------------------------------------------------------------------------------

class ProcessMemorySampler:
    """Working set and private bytes of one process, via GetProcessMemoryInfo."""

    def __init__(self, pid: int):
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                        ("PrivateUsage", ctypes.c_size_t)]

        self._ctypes = ctypes
        self._counters_type = PROCESS_MEMORY_COUNTERS_EX
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self._kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self._kernel32.OpenProcess.restype = wintypes.HANDLE
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
        self._psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        process_query_limited_information, process_vm_read = 0x1000, 0x0010
        self._handle = self._kernel32.OpenProcess(
            process_query_limited_information | process_vm_read, False, pid)
        if not self._handle:
            raise OSError(f"OpenProcess({pid}) failed, winerror {ctypes.get_last_error()}")

    def sample(self) -> tuple[int, int] | None:
        """(working_set_bytes, private_bytes), or None if the call failed."""
        counters = self._counters_type()
        counters.cb = self._ctypes.sizeof(counters)
        ok = self._psapi.GetProcessMemoryInfo(self._handle, self._ctypes.byref(counters),
                                              counters.cb)
        return (counters.WorkingSetSize, counters.PrivateUsage) if ok else None

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None


class GpuDedicatedMemoryCounter:
    """Dedicated GPU memory per process and adapter, from the PDH counter
    \\GPU Process Memory(pid_<pid>_luid_<high>_<low>_phys_<n>)\\Dedicated Usage."""

    COUNTER_PATH = r"\GPU Process Memory(*)\Dedicated Usage"
    _PDH_FMT_LARGE = 0x00000400
    _PDH_MORE_DATA = 0x800007D2

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class _Value(ctypes.Union):
            _fields_ = [("longValue", ctypes.c_long), ("doubleValue", ctypes.c_double),
                        ("largeValue", ctypes.c_longlong), ("AnsiStringValue", ctypes.c_char_p),
                        ("WideStringValue", ctypes.c_wchar_p)]

        class PDH_FMT_COUNTERVALUE(ctypes.Structure):
            _fields_ = [("CStatus", wintypes.DWORD), ("value", _Value)]

        class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
            _fields_ = [("szName", ctypes.c_wchar_p), ("FmtValue", PDH_FMT_COUNTERVALUE)]

        self._ctypes, self._wintypes = ctypes, wintypes
        self._item_type = PDH_FMT_COUNTERVALUE_ITEM_W
        pdh = self._pdh = ctypes.WinDLL("pdh")
        handle_p = ctypes.POINTER(wintypes.HANDLE)
        dword_p = ctypes.POINTER(wintypes.DWORD)
        pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, handle_p]
        pdh.PdhAddEnglishCounterW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, ctypes.c_size_t,
                                              handle_p]
        pdh.PdhCollectQueryData.argtypes = [wintypes.HANDLE]
        pdh.PdhGetFormattedCounterArrayW.argtypes = [wintypes.HANDLE, wintypes.DWORD, dword_p,
                                                     dword_p, ctypes.c_void_p]
        pdh.PdhCloseQuery.argtypes = [wintypes.HANDLE]
        for function in (pdh.PdhOpenQueryW, pdh.PdhAddEnglishCounterW, pdh.PdhCollectQueryData,
                         pdh.PdhGetFormattedCounterArrayW, pdh.PdhCloseQuery):
            function.restype = wintypes.DWORD

        self._query = wintypes.HANDLE()
        self._counter = wintypes.HANDLE()
        status = pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query))
        if status != 0:
            raise OSError(f"PdhOpenQueryW failed: {status:#x}")
        status = pdh.PdhAddEnglishCounterW(self._query, self.COUNTER_PATH, 0,
                                           ctypes.byref(self._counter))
        if status != 0:
            pdh.PdhCloseQuery(self._query)
            self._query = None
            raise OSError(f"PdhAddEnglishCounterW({self.COUNTER_PATH}) failed: {status:#x}")

    def sample(self, pid: int) -> dict | None:
        """{luid_instance_key: dedicated_bytes} for one process, summed over phys indexes.
        Empty before the process creates a GPU device; None if PDH reports an error."""
        ctypes, wintypes = self._ctypes, self._wintypes
        if self._pdh.PdhCollectQueryData(self._query) != 0:
            return None
        for _ in range(3):  # the instance list can grow between the size query and the read
            size, count = wintypes.DWORD(0), wintypes.DWORD(0)
            status = self._pdh.PdhGetFormattedCounterArrayW(
                self._counter, self._PDH_FMT_LARGE, ctypes.byref(size), ctypes.byref(count), None)
            if status == 0:
                return {}
            if status != self._PDH_MORE_DATA:
                return None
            buffer = ctypes.create_string_buffer(size.value)
            status = self._pdh.PdhGetFormattedCounterArrayW(
                self._counter, self._PDH_FMT_LARGE, ctypes.byref(size), ctypes.byref(count),
                buffer)
            if status == self._PDH_MORE_DATA:
                continue
            if status != 0:
                return None
            items = ctypes.cast(buffer, ctypes.POINTER(self._item_type))
            prefix = f"pid_{pid}_luid_"
            usage: dict[str, int] = {}
            for index in range(count.value):
                name = items[index].szName or ""
                if name.startswith(prefix) and items[index].FmtValue.CStatus in (0, 1):
                    luid = name[len(prefix):].split("_phys_")[0].lower()
                    usage[luid] = usage.get(luid, 0) + items[index].FmtValue.value.largeValue
            return usage
        return None

    def close(self) -> None:
        if self._query:
            self._pdh.PdhCloseQuery(self._query)
            self._query = None


def sample_until_exit(proc: subprocess.Popen, t0: float, timeout_s: float) -> dict:
    """Sample the process about once per second until it exits; kill it after timeout_s.
    Returns {"samples": [...], "notes": [...], "timed_out": bool}."""
    samples, notes = [], []
    memory = gpu = None
    try:
        memory = ProcessMemorySampler(proc.pid)
    except (OSError, AttributeError) as exc:
        notes.append(f"process memory not sampled: {exc}")
    try:
        gpu = GpuDedicatedMemoryCounter()
    except (OSError, AttributeError) as exc:
        notes.append(f"GPU dedicated memory not sampled: {exc}")
    timed_out = False
    try:
        while proc.poll() is None:
            elapsed = time.monotonic() - t0
            if elapsed > timeout_s:
                proc.kill()
                timed_out = True
                break
            sample = {"t_s": round(elapsed, 3), "working_set_bytes": None,
                      "private_bytes": None, "gpu_dedicated_by_luid": None}
            values = memory.sample() if memory else None
            if values and values[0] > 0:  # a process that just exited reads as 0
                sample["working_set_bytes"], sample["private_bytes"] = values
            if gpu:
                sample["gpu_dedicated_by_luid"] = gpu.sample(proc.pid)
            samples.append(sample)
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
    finally:
        if memory:
            memory.close()
        if gpu:
            gpu.close()
    proc.wait()
    return {"samples": samples, "notes": notes, "timed_out": timed_out}


# ---------------------------------------------------------------------------------------------
# Facts: machine, file, PyGObject option, pipeline
# ---------------------------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_text(argv: list[str], timeout_s: float = 60.0) -> tuple[int | None, str, str]:
    """Run a short helper command. Returns (exit_code, stdout, stderr); exit_code is None when
    the command could not run or timed out."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout_s, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, "", f"{type(exc).__name__}: {exc}"
    return done.returncode, done.stdout, done.stderr


_MACHINE_POWERSHELL = (
    "$v = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion); "
    "$o = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber; "
    "[pscustomobject]@{video_controllers = $v; os = $o} | ConvertTo-Json -Depth 4 -Compress"
)


def collect_machine_facts() -> dict:
    facts: dict = {"hostname": os.environ.get("COMPUTERNAME")}
    code, out, err = _run_text(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                _MACHINE_POWERSHELL])
    try:
        cim = json.loads(out) if code == 0 else None
    except json.JSONDecodeError:
        cim = None
    windows: dict = {}
    if cim:
        facts["gpus"] = [{"name": gpu.get("Name"), "driver_version": gpu.get("DriverVersion")}
                         for gpu in cim.get("video_controllers") or []]
        os_info = cim.get("os") or {}
        windows = {"caption": os_info.get("Caption"), "version": os_info.get("Version"),
                   "build": os_info.get("BuildNumber")}
    else:
        facts["gpus"] = f"Get-CimInstance failed: {(err or out).strip()[:300]}"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            build = winreg.QueryValueEx(key, "CurrentBuild")[0]
            windows["build_with_ubr"] = f"{build}.{winreg.QueryValueEx(key, 'UBR')[0]}"
            windows["display_version"] = winreg.QueryValueEx(key, "DisplayVersion")[0]
    except (ImportError, OSError):
        pass
    facts["windows"] = windows

    code, out, err = _run_text([str(GST_INSPECT), "--version"])
    facts["gst_inspect_version"] = (out.strip().splitlines() if code == 0
                                    else f"failed: {(err or out).strip()[:300]}")
    code, out, err = _run_text([str(GST_INSPECT), "d3d12h265dec"])
    long_name = re.search(r"Long-name\s+(.+)", out)
    rank = re.search(r"Rank\s+(.+)", out)
    facts["d3d12h265dec"] = ({"long_name": long_name.group(1).strip() if long_name else None,
                              "rank": rank.group(1).strip() if rank else None}
                             if code == 0 else f"failed: {(err or out).strip()[:300]}")
    return facts


def collect_file_facts(path: Path) -> dict:
    stat = path.stat()
    facts = {"path": str(path), "size_bytes": stat.st_size,
             "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
             .isoformat(timespec="seconds")}
    code, out, err = _run_text([str(GST_DISCOVERER), path.as_posix()], timeout_s=120.0)
    duration = re.search(r"Duration:\s*(\S+)", out) if code == 0 else None
    facts["duration_s"] = parse_clock_time(duration.group(1)) if duration else None
    facts["duration_source"] = ("gst-discoverer-1.0" if duration
                                else f"unknown: {(err or out).strip()[:300]}")
    return facts


_PYGOBJECT_CHECK = """\
import os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "lib", "site-packages"))
os.add_dll_directory(os.path.join(root, "bin"))
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
Gst.init(None)
print(Gst.version_string())
"""


def check_pygobject() -> dict:
    """Does GStreamer's bundled PyGObject import in this interpreter? Checked in a child
    process so a half-initialised gi module never lingers in this one."""
    code, out, err = _run_text([sys.executable, "-c", _PYGOBJECT_CHECK, str(GST_ROOT)])
    detail_lines = [line for line in (out if code == 0 else err).splitlines() if line.strip()]
    return {
        "python": sys.version.split()[0],
        "site_packages": str(GST_SITE_PACKAGES),
        "gi_extensions": sorted(p.name for p in (GST_SITE_PACKAGES / "gi").glob("_gi*.pyd")),
        "importable": code == 0,
        "detail": detail_lines[-1] if detail_lines else None,
    }


def build_pipeline(file_path: Path, sync: bool, eos_after: int, sleep_us: int = 0) -> list[str]:
    """gst-launch-1.0 pipeline tokens, one argv element each (so the spaced file location needs
    no shell quoting). sleep_us > 0 is only for the forced-drop calibration pass."""
    identity = ["identity", "name=cut", f"eos-after={eos_after}"]
    if sleep_us > 0:
        identity.append(f"sleep-time={sleep_us}")
    return [
        "filesrc", f"location={file_path.as_posix()}", "!",
        "qtdemux", "name=demux", "demux.video_0", "!",
        "h265parse", "name=parse", "!",
        # identity passes the encoded frames through untouched; eos-after=N ends the final
        # soak pass at the deadline (-1 = the whole file).
        *identity, "!",
        "d3d12h265dec", f"name={DECODER_NAME}", "!",
        f"video/x-raw({D3D12_CAPS_FEATURE})", "!",
        # fakevideosink behaves like a real video sink (qos=true, max-lateness 5 ms, crop and
        # overlay meta advertised), so late frames really are dropped and counted; a plain
        # fakesink never drops. Neither opens a window.
        "fpsdisplaysink", f"name={FPS_SINK_NAME}", "video-sink=fakevideosink name=sink",
        "text-overlay=false", f"sync={'true' if sync else 'false'}",
        f"fps-update-interval={FPS_UPDATE_INTERVAL_MS}",
    ]


def pipeline_string(tokens: list[str]) -> str:
    """The pipeline description as it would be typed, with spaced values quoted."""
    parts = []
    for token in tokens:
        key, sep, value = token.partition("=")
        parts.append(f'{key}="{value}"' if sep and " " in value else token)
    return " ".join(parts)


def inspect_property_default(inspect_text: str, name: str) -> str | None:
    """The "Default:" value of one property in gst-inspect-1.0 output."""
    match = re.search(rf"^\s+{re.escape(name)}\s*:.*?Default:\s*(\S+)", inspect_text,
                      re.MULTILINE | re.DOTALL)
    return match.group(1).rstrip(",") if match else None


def collect_sink_defaults() -> dict:
    """fakevideosink's drop-related defaults on this install; the soak does not override them."""
    code, out, err = _run_text([str(GST_INSPECT), "fakevideosink"])
    if code != 0:
        return {"error": f"gst-inspect-1.0 fakevideosink failed: {(err or out).strip()[:300]}"}

    def as_int(value: str | None) -> int | None:
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None

    return {"qos": inspect_property_default(out, "qos") == "true",
            "max_lateness_ns": as_int(inspect_property_default(out, "max-lateness")),
            "processing_deadline_ns": as_int(inspect_property_default(out, "processing-deadline")),
            "source": "gst-inspect-1.0 fakevideosink defaults"}


# ---------------------------------------------------------------------------------------------
# One pass = one gst-launch-1.0 process
# ---------------------------------------------------------------------------------------------

SINK_NAME = "sink"  # fakevideosink's name in build_pipeline (its inner fakesink is also "sink")
_MB = 1024 * 1024


def _mb(value: float | None) -> float | None:
    return None if value is None else round(value / _MB, 2)


def _progress(message: str) -> None:
    print(f"[gst_d3d12_soak {datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


class PassOutput:
    """Parses one gst-launch process's stdout and stderr as the lines arrive; events are
    stamped with seconds since launch."""

    def __init__(self, t0: float):
        self.t0 = t0
        self._lock = threading.Lock()
        self.fps_series: list[dict] = []
        self.caps_events: list[dict] = []
        self.qos: dict[str, dict] = {}
        self.decoder_drop_log_lines = 0
        self.warnings: list[dict] = []
        self.warnings_total = 0
        self.device: dict | None = None
        self.eos_t: float | None = None
        self.execution_s: float | None = None
        self.tails = {"stdout": deque(maxlen=20), "stderr": deque(maxlen=20)}
        self._follow = {"stdout": 0, "stderr": 0}

    def consume(self, stream, name: str) -> None:
        for raw in stream:
            self.handle(raw.rstrip("\r\n"), name, time.monotonic() - self.t0)

    def handle(self, line: str, stream: str, t: float) -> None:
        with self._lock:
            self.tails[stream].append(line)
            fps = parse_fps_message(line)
            if fps and fps.pop("element").rsplit(":", 1)[-1] == FPS_SINK_NAME:
                self.fps_series.append({"t_s": round(t, 3), **fps})
                return
            caps = parse_caps_line(line)
            if caps:
                self.caps_events.append(caps)
                return
            qos = parse_qos_message(line)
            if qos:
                entry = self.qos.setdefault(qos["element"],
                                            {"messages": 0, "dropped": 0, "processed": 0})
                entry["messages"] += 1
                entry["dropped"] = max(entry["dropped"], qos["dropped"])
                entry["processed"] = max(entry["processed"], qos["processed"])
                return
            if self.device is None:
                self.device = parse_d3d12_device_context(line)
            if line.startswith("Got EOS from element"):
                self.eos_t = t
            execution = parse_execution_time(line)
            if execution is not None:
                self.execution_s = execution
            if f"<{DECODER_NAME}> Dropping frame due to QoS" in line:
                self.decoder_drop_log_lines += 1
            matched = is_error_or_warning(line)
            if matched or self._follow[stream]:
                self.warnings_total += int(matched)
                if len(self.warnings) < MAX_STORED_WARNINGS:
                    self.warnings.append({"t_s": round(t, 3), "stream": stream, "line": line})
                # gst-launch follows ERROR:/WARNING: with "Additional debug info:" and a detail line.
                self._follow[stream] = (2 if line.startswith(("ERROR:", "WARNING:"))
                                        else max(0, self._follow[stream] - 1))


def summarize_pass_memory(samples: list[dict], window_start_s: float | None,
                          window_end_s: float | None, gpu_luid: str | None) -> dict:
    """Memory series for one pass plus stats over its steady window, which runs from the first
    fpsdisplaysink report (frames flowing, pools allocated) to EOS."""
    rows = []
    for sample in samples:
        by_luid = sample["gpu_dedicated_by_luid"]
        if by_luid is None:
            gpu = None
        elif gpu_luid is not None:
            gpu = by_luid.get(gpu_luid, 0)
        else:
            gpu = sum(by_luid.values())
        rows.append({"t_s": sample["t_s"], "working_set_mb": _mb(sample["working_set_bytes"]),
                     "private_mb": _mb(sample["private_bytes"]), "gpu_dedicated_mb": _mb(gpu)})
    steady = [row for row in rows
              if window_start_s is not None and row["t_s"] > window_start_s
              and (window_end_s is None or row["t_s"] <= window_end_s)]

    def stats(key: str) -> dict | None:
        points = [(row["t_s"], row[key]) for row in steady if row[key] is not None]
        if not points:
            return None
        xs, ys = [point[0] for point in points], [point[1] for point in points]
        slope = linear_slope(xs, ys)
        return {"start": ys[0], "end": ys[-1], "peak": max(ys), "growth": round(ys[-1] - ys[0], 2),
                "slope_mb_per_min": None if slope is None else round(slope * 60.0, 3)}

    return {
        "steady_window_s": [window_start_s, None if window_end_s is None else round(window_end_s, 3)],
        "steady_samples": len(steady),
        "working_set_mb": stats("working_set_mb"),
        "private_mb": stats("private_mb"),
        "gpu_dedicated_mb": stats("gpu_dedicated_mb"),
        "gpu_dedicated_adapter_luid": gpu_luid,
        "samples": rows,
    }


def sink_conditions(sync: bool, sink_defaults: dict) -> dict:
    """What makes the sink drop a frame in this pass. A frame can only be late (and dropped)
    when the sink syncs to the clock, sends QoS and has a finite max-lateness."""
    qos = sink_defaults.get("qos")
    max_lateness = sink_defaults.get("max_lateness_ns")
    return {
        "sink": "fakevideosink (inner fakesink named 'sink') inside fpsdisplaysink",
        "sync": sync,
        "qos": qos,
        "max_lateness_ns": max_lateness,
        "processing_deadline_ns": sink_defaults.get("processing_deadline_ns"),
        "conditions_source": sink_defaults.get("source", sink_defaults.get("error")),
        "late_frames_can_drop": bool(sync and qos and max_lateness is not None and max_lateness >= 0),
    }


def run_pass(kind: str, file_path: Path, *, sync: bool, eos_after: int,
             frames_expected: int | None, timeout_s: float, sink_defaults: dict,
             sleep_us: int = 0) -> dict:
    tokens = build_pipeline(file_path, sync, eos_after, sleep_us)
    argv = [str(GST_LAUNCH), *LAUNCH_FLAGS, *tokens]
    started_at = utc_now()
    t0 = time.monotonic()
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", env={**os.environ, **GST_ENV})
    output = PassOutput(t0)
    readers = [threading.Thread(target=output.consume, args=(proc.stdout, "stdout"), daemon=True),
               threading.Thread(target=output.consume, args=(proc.stderr, "stderr"), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        sampling = sample_until_exit(proc, t0, timeout_s)
    finally:
        if proc.poll() is None:  # interrupted: never leave gst-launch running
            proc.kill()
            proc.wait()
    for reader in readers:
        reader.join(timeout=10)
    wall_s = time.monotonic() - t0

    dec_caps = decoder_src_caps(output.caps_events)
    sink = final_sink_caps(output.caps_events)
    last = output.fps_series[-1] if output.fps_series else None
    luid = (luid_instance_key(output.device["adapter_luid"])
            if output.device and output.device.get("adapter_luid") is not None else None)
    zero_qos = {"messages": 0, "dropped": 0, "processed": 0}
    qos_elements = sorted(set(output.qos) | {DECODER_NAME, SINK_NAME})
    reporters = {DECODER_NAME: "decoder: GstVideoDecoder posts a QoS message per dropped late frame",
                 SINK_NAME: "sink: GstBaseSink posts a QoS message per dropped late buffer"}
    drop_counts = [{"source": "qos_bus_messages", "element": element,
                    "reporter": reporters.get(element, "element QoS messages"),
                    **output.qos.get(element, zero_qos)} for element in qos_elements]
    drop_counts.append({"source": "gst_debug_log", "element": DECODER_NAME,
                        "reporter": "decoder WARN lines 'Dropping frame due to QoS' (GST_DEBUG=*:2)",
                        "dropped": output.decoder_drop_log_lines})
    drop_counts.append({"source": "fpsdisplaysink_last_message", "element": FPS_SINK_NAME,
                        "reporter": "fpsdisplaysink: sink-side drops only, as of its last 1000 ms report",
                        "dropped": last["dropped"] if last else None})

    result = {
        "kind": kind,
        "sync": sync,
        "eos_after_frames": eos_after if eos_after >= 0 else None,
        "identity_sleep_us": sleep_us or None,
        "pipeline": pipeline_string(tokens),
        "argv": argv,
        "command_line": subprocess.list2cmdline(argv),
        "env": dict(GST_ENV),
        "started_at": started_at,
        "ended_at": utc_now(),
        "exit_code": proc.returncode,
        "timed_out": sampling["timed_out"],
        "wall_s": round(wall_s, 3),
        "execution_ended_after_s": output.execution_s,
        "eos_received": output.eos_t is not None,
        "decoder_device": output.device,
        "caps": {"decoder_src": dec_caps, "sink_pad_element": sink["element_path"],
                 "sink_pad": sink["caps"]},
        "d3d12_memory_at_decoder_src": all_d3d12(dec_caps),
        "d3d12_memory_at_sink": all_d3d12(sink["caps"]),
        "framerate": parse_framerate(dec_caps[-1] if dec_caps else None),
        "frames": {
            "expected": frames_expected,
            "rendered_at_last_fps_report": last["rendered"] if last else None,
            "last_fps_report_t_s": last["t_s"] if last else None,
            "average_fps_at_last_report": last["average_fps"] if last else None,
            "note": "fpsdisplaysink reports every 1000 ms; frames after its last report are "
                    "not in rendered_at_last_fps_report",
        },
        "drops": {
            "sink_conditions": sink_conditions(sync, sink_defaults),
            "counts": drop_counts,
            "gated": {"source": "qos_bus_messages", "elements": qos_elements,
                      "dropped": sum(output.qos.get(e, zero_qos)["dropped"] for e in qos_elements)},
        },
        "fpsdisplaysink_series": output.fps_series,
        "errors_warnings_total": output.warnings_total,
        "errors_warnings": output.warnings,
        "memory": {
            **summarize_pass_memory(sampling["samples"],
                                    output.fps_series[0]["t_s"] if output.fps_series else None,
                                    output.eos_t, luid),
            "sampler_notes": sampling["notes"],
        },
    }
    if proc.returncode != 0 or sampling["timed_out"]:
        result["output_tail"] = {name: list(lines) for name, lines in output.tails.items()}
    _progress(f"{kind} pass: exit={proc.returncode} wall={wall_s:.1f}s "
              f"d3d12_at_sink={result['d3d12_memory_at_sink']} "
              f"qos_dropped={result['drops']['gated']['dropped']} "
              f"rendered@last_report={result['frames']['rendered_at_last_fps_report']}")
    return result


# ---------------------------------------------------------------------------------------------
# Soak orchestration, summary, verdict, receipt
# ---------------------------------------------------------------------------------------------

CALIBRATION_FRAMES = 300
# 25 ms per encoded frame before the decoder feeds it at ~40 fps against the 60 fps clock, so
# frames arrive late and both the decoder and the sink must drop.
CALIBRATION_SLEEP_US = 25_000
# A calibration pass that reaches EOS takes about 9 s. On long files it can stall instead
# (see the stall investigation in the 2026-09-13 B.1 receipt), so it is cut off early.
CALIBRATION_TIMEOUT_S = 30.0

PRIOR_FORCED_DROP_PROBE = {
    "provenance": "scratch probe run on 2026-09-13 before this lane existed; not part of this run",
    "file": r"E:\Video Output E\2026-09-06 10-32-02.mp4",
    "forcing_condition": "identity eos-after=300 sleep-time=25000 before d3d12h265dec, sync=true, "
                         "fakevideosink",
    "result": "fpsdisplaysink reported dropped 5 (rendered 6) at its last report, 7.5 s into a "
              "14.4 s pass; the decoder logged 288 'Dropping frame due to QoS' WARN lines; "
              "294 QoS bus messages",
}

NOTES = [
    "Earlier numbers for this lane counted no drops by construction. The 2026-09-13 smoke run "
    "(fpsdisplaysink video-sink=fakesink sync=false: rendered 786, dropped 0) used fakesink, whose "
    "defaults on this install are qos=false and max-lateness=-1, so it never drops a late frame; "
    "and with sync=false no frame is ever late. The QoS-message counts in this receipt are the "
    "lane's first real drop counts.",
    "fpsdisplaysink's dropped figure only sees sink-side drops (and only as of its last 1000 ms "
    "report). In the forced-drop probe the decoder dropped 288 frames while fpsdisplaysink "
    "reported 5, so the verdict gates on QoS bus messages from the decoder and the sink.",
]

KNOWN_WARNINGS = [
    ("d3d11debuglayer", "D3D11 debug-layer report while D3D11 devices are disposed, before the "
                        "pipeline starts; seen in every probe run on this machine"),
    ("qtdemux_parse_segments", "OBS edit list: the segment runs a few ms past the declared movie "
                               "duration; qtdemux extends the segment"),
    ("No value transform to serialize field 'context'",
     "printed when gst-launch -m serializes the decoder's have-context message"),
]


def _steady_rows(memory: dict) -> list[dict]:
    start, end = memory["steady_window_s"]
    return [row for row in memory["samples"]
            if start is not None and row["t_s"] > start and (end is None or row["t_s"] <= end)
            and row["working_set_mb"] is not None]


def summarize_soak_memory(synced: list[dict]) -> dict:
    """Memory across the synced passes. Every pass is its own process, so after the warm-up
    pass, growth is judged both inside each pass and from the start of the first post-warm-up
    pass to the end of the last one."""
    def working_set(p: dict) -> dict | None:
        return p["memory"]["working_set_mb"]

    first = working_set(synced[0]) if synced else None
    last = working_set(synced[-1]) if synced else None
    result: dict = {
        "model": "one gst-launch process per pass, sampled at 1 Hz; steady window = first "
                 "fpsdisplaysink report to EOS; the first synced pass is the warm-up",
        "working_set_start_mb": first["start"] if first else None,
        "working_set_end_mb": last["end"] if last else None,
        "working_set_growth_mb": round(last["end"] - first["start"], 2) if first and last else None,
        "gpu_dedicated_peak_mb": max((p["memory"]["gpu_dedicated_mb"]["peak"] for p in synced
                                      if p["memory"]["gpu_dedicated_mb"]), default=None),
        "post_warmup": None,
    }
    post = synced[1:]
    if not post or not all(working_set(p) for p in post):
        return result
    within = [working_set(p)["growth"] for p in post]
    cross = round(working_set(post[-1])["end"] - working_set(post[0])["start"], 2)
    xs = [p["soak_offset_s"] + row["t_s"] for p in post for row in _steady_rows(p["memory"])]
    ys = [row["working_set_mb"] for p in post for row in _steady_rows(p["memory"])]
    slope = linear_slope(xs, ys)
    within_slopes = [working_set(p)["slope_mb_per_min"] for p in post
                     if working_set(p)["slope_mb_per_min"] is not None]
    private = [p["memory"]["private_mb"]["growth"] for p in post if p["memory"]["private_mb"]]
    gpu = [p["memory"]["gpu_dedicated_mb"]["growth"] for p in post if p["memory"]["gpu_dedicated_mb"]]
    result["post_warmup"] = {
        "passes": [p["index"] for p in post],
        "max_within_pass_growth_mb": max(within),
        "cross_pass_growth_mb": cross,
        "working_set_growth_mb": max(max(within), cross),
        "slope_mb_per_min": None if slope is None else round(slope * 60.0, 3),
        "max_within_pass_slope_mb_per_min": max(within_slopes, default=None),
        "private_max_within_pass_growth_mb": max(private, default=None),
        "gpu_dedicated_max_within_pass_growth_mb": max(gpu, default=None),
    }
    return result


def summarize(passes: list[dict], duration_s: float) -> dict:
    synced = [p for p in passes if p["kind"] == "synced"]
    throughput = next((p for p in passes if p["kind"] == "throughput"), None)

    rendered = sum(p["frames"]["rendered_at_last_fps_report"] or 0 for p in synced)
    expected = (sum(p["frames"]["expected"] for p in synced)
                if synced and all(p["frames"]["expected"] for p in synced) else None)
    by_source: dict[str, int] = {}
    for p in synced:
        for count in p["drops"]["counts"]:
            key = f"{count['source']}:{count['element']}"
            by_source[key] = by_source.get(key, 0) + (count["dropped"] or 0)
    gated = sum(p["drops"]["gated"]["dropped"] for p in synced)
    denominator = rendered + gated
    fps_values = [row["current_fps"] for p in synced for row in p["fpsdisplaysink_series"]
                  if row["current_fps"] is not None]

    def rounded(value: float | None) -> float | None:
        return None if value is None else round(value, 2)

    throughput_summary = None
    if throughput:
        execution_s = throughput["execution_ended_after_s"]
        expected_t = throughput["frames"]["expected"]
        per_second = round(expected_t / execution_s, 1) if expected_t and execution_s else None
        average = throughput["frames"]["average_fps_at_last_report"]
        throughput_summary = {
            "fps": average if average is not None else per_second,
            "fps_source": ("fpsdisplaysink average at its last report" if average is not None
                           else "expected frames / time in PLAYING"),
            "expected_frames_per_playing_second": per_second,
            "execution_ended_after_s": execution_s,
            "wall_s": throughput["wall_s"],
        }

    known = []
    for needle, explanation in KNOWN_WARNINGS:
        lines = sum(1 for p in passes for w in p["errors_warnings"] if needle in w["line"])
        if lines:
            known.append({"match": needle, "lines": lines, "explanation": explanation})

    return {
        "synced_passes": len(synced),
        "synced_wall_s": round(sum(p["wall_s"] for p in synced), 1),
        "requested_soak_s": duration_s,
        "total_frames": rendered,
        "total_frames_source": "sum over synced passes of fpsdisplaysink rendered at the last "
                               "report (each pass's final <1 s is not included)",
        "total_frames_expected": expected,
        "drops": {
            "gated_source": "qos_bus_messages from decoder and sink, synced passes only",
            "total_dropped": gated,
            "drop_rate": (gated / denominator) if denominator else None,
            "drop_rate_denominator": "total_frames + total_dropped",
            "by_source": by_source,
            "sink_conditions": synced[0]["drops"]["sink_conditions"] if synced else None,
        },
        "current_fps": {"samples": len(fps_values), "p50": rounded(percentile(fps_values, 50)),
                        "p5": rounded(percentile(fps_values, 5)),
                        "min": rounded(min(fps_values, default=None)),
                        "max": rounded(max(fps_values, default=None))},
        "throughput": throughput_summary,
        "memory": summarize_soak_memory(synced),
        "errors_warnings_total": sum(p["errors_warnings_total"] for p in passes),
        "known_warnings": known,
    }


def build_verdict(passes: list[dict], summary: dict, calibration: dict | None,
                  interrupted: bool) -> dict:
    """The soak verdict (decode path) and the calibration record (the drop instrument) are
    separate claims: the calibration never changes the soak verdict, and the status line
    states both."""
    reasons: list[str] = []
    all_ok = True

    def record(ok: bool, text: str) -> None:
        nonlocal all_ok
        all_ok = all_ok and ok
        reasons.append(("ok: " if ok else "FAIL: ") + text)

    if interrupted:
        record(False, "the run was interrupted before the soak finished")

    at_sink = sum(1 for p in passes if p["d3d12_memory_at_sink"])
    record(bool(passes) and at_sink == len(passes),
           f"memory:D3D12Memory reached the innermost sink pad in {at_sink}/{len(passes)} passes")

    drops = summary["drops"]
    synced = [p for p in passes if p["kind"] == "synced"]
    if not synced:
        record(False, "no synced pass ran, so drops were not measured")
    else:
        rate = drops["drop_rate"]
        ok = drops["total_dropped"] == 0 or (rate is not None and rate < MAX_DROP_RATE)
        rate_text = "n/a" if rate is None else f"{rate:.4%}"
        record(ok, f"synced passes dropped {drops['total_dropped']} frames by the gated count "
                   f"(qos_bus_messages, decoder + sink), rate {rate_text}, limit 0.1%")

    post = summary["memory"]["post_warmup"]
    if post is None:
        record(False, "working-set growth after warm-up not measured: it needs a second synced "
                      "pass with memory samples")
    else:
        record(post["working_set_growth_mb"] < MAX_WORKING_SET_GROWTH_MB,
               f"working-set growth after warm-up {post['working_set_growth_mb']:.2f} MB "
               f"(within-pass max {post['max_within_pass_growth_mb']:.2f} MB, cross-pass "
               f"{post['cross_pass_growth_mb']:.2f} MB), limit {MAX_WORKING_SET_GROWTH_MB:.0f} MB")

    failed = [f"pass {p['index']} ({p['kind']}) exit={p['exit_code']}"
              f"{' timed out' if p['timed_out'] else ''}"
              for p in passes if p["exit_code"] != 0 or p["timed_out"]]
    record(bool(passes) and not failed,
           f"all {len(passes)} passes exited 0" if not failed else "failed: " + "; ".join(failed))

    detected = bool(calibration and calibration["gated_count_detected_drops"])
    completed = bool(calibration and calibration["completed"])
    if calibration is None:
        calibration_text = "calibration not run, so the zero-drop result is unproven"
    elif detected and completed:
        calibration_text = "calibration saw drops and completed"
    elif detected:
        calibration_text = "calibration saw drops but stalled before EOS (open finding)"
    elif completed:
        calibration_text = "calibration saw no drops, so the zero-drop result is unproven"
    else:
        calibration_text = ("calibration saw no drops and stalled before EOS, so the zero-drop "
                            "result is unproven")
    return {
        "status": f"soak {'PASS' if all_ok else 'FAIL'}; {calibration_text}",
        "soak_verdict": "pass" if all_ok else "fail",
        "pass": all_ok,
        "gated_drop_count": "qos_bus_messages from decoder and sink, synced passes only",
        "reasons": reasons,
        "calibration": None if calibration is None else {
            key: calibration[key]
            for key in ("drops_observed", "gated_count_detected_drops", "completed", "stall")},
    }


def measured_lists(passes: list[dict]) -> tuple[list[str], list[str]]:
    gpu_measured = any(p["memory"]["gpu_dedicated_mb"] for p in passes)
    measured = [
        "negotiated caps on the decoder src pad and on the innermost sink pad (gst-launch -v), per pass",
        "the decoder's D3D12 device: adapter LUID, vendor and device id, description",
        "fpsdisplaysink reports every 1000 ms: rendered, dropped, current and average fps",
        "drops per source: QoS bus messages from decoder and sink (gst-launch -m), decoder "
        "'Dropping frame due to QoS' WARN lines, and fpsdisplaysink's figure",
        "a forced-drop calibration pass showing the gated drop count registers drops",
        "GStreamer ERROR/WARN debug lines (GST_DEBUG=*:2) and gst-launch ERROR:/WARNING: reports",
        "working set and private bytes of each gst-launch process at 1 Hz (GetProcessMemoryInfo)",
        "exit code, wall time and time in PLAYING per pass",
    ]
    not_measured = [
        "GPU-side copies: D3D12Memory caps at the sink rule out a download to system memory, not "
        "a texture copy inside the GPU (for example a decoder output copy)",
        "presentation: frames end in fakevideosink, not a D3D12 swapchain (d3d12videosink opens "
        "a window)",
        "frames rendered after each pass's last fpsdisplaysink report (under 1 s per pass)",
        "memory growth across loops inside one long-lived process: every pass is a fresh "
        "gst-launch process",
        "TDR or device-removed events, GPU engine utilisation, CPU usage",
        "audio: only the video track is demuxed and decoded",
        "the file's exact frame count: expected frames are duration x framerate",
    ]
    if gpu_measured:
        measured.append("dedicated GPU memory of each gst-launch process on the decoder's adapter "
                        r"at 1 Hz (PDH \GPU Process Memory(*)\Dedicated Usage)")
    else:
        not_measured.append("dedicated GPU memory per process: the PDH counter returned no data")
    return measured, not_measured


def run_calibration(file_path: Path, framerate: float, sink_defaults: dict) -> dict:
    result = run_pass("calibration", file_path, sync=True, eos_after=CALIBRATION_FRAMES,
                      frames_expected=CALIBRATION_FRAMES, timeout_s=CALIBRATION_TIMEOUT_S,
                      sink_defaults=sink_defaults, sleep_us=CALIBRATION_SLEEP_US)
    return calibration_record(result, framerate)


def calibration_record(result: dict, framerate: float) -> dict:
    """The calibration entry for a finished calibration pass. Whether the gated count saw drops
    and whether the pass completed (reached EOS) are recorded as separate facts."""
    drops = result["drops"]["gated"]["dropped"]
    completed = result["exit_code"] == 0 and result["eos_received"] and not result["timed_out"]
    stall = None
    if not completed:
        decoder_qos = next((c for c in result["drops"]["counts"] if c["source"] == "qos_bus_messages"
                            and c["element"] == DECODER_NAME), {})
        ending = (f"killed by the pass timeout after {result['wall_s']:.1f} s" if result["timed_out"]
                  else f"exit code {result['exit_code']}")
        stall = {
            "summary": f"registered {drops} gated drops but stalled before EOS ({ending})",
            "exit_code": result["exit_code"],
            "timed_out": result["timed_out"],
            "eos_received": result["eos_received"],
            "wall_s": result["wall_s"],
            "decoder_qos_processed": decoder_qos.get("processed"),
            "last_fps_report_t_s": result["frames"]["last_fps_report_t_s"],
        }
    return {
        "name": "forced_drop",
        "purpose": "show the drop counters register drops before trusting a zero-drop soak; "
                   "excluded from the soak totals and not part of the soak verdict",
        "forcing_condition": f"identity sleep-time={CALIBRATION_SLEEP_US} us on each of "
                             f"{CALIBRATION_FRAMES} encoded frames before the decoder, sync=true, "
                             f"against a {framerate:g} fps clock",
        "expectation": "the gated count (qos_bus_messages, decoder + sink) is above zero and the "
                       "pass reaches EOS",
        "gated_count_detected_drops": drops > 0,
        "drops_observed": drops,
        "completed": completed,
        "stall": stall,
        "counts_by_source": {f"{c['source']}:{c['element']}": c["dropped"]
                             for c in result["drops"]["counts"]},
        "sink_conditions": result["drops"]["sink_conditions"],
        "prior_probe": PRIOR_FORCED_DROP_PROBE,
        "pass": result,
    }


def run_soak(file_path: Path, duration_s: float, out_dir: Path) -> tuple[dict, Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    started_at = utc_now()
    _progress(f"facts for {file_path}")
    machine = collect_machine_facts()
    file_info = collect_file_facts(file_path)
    pygobject = check_pygobject()
    sink_defaults = collect_sink_defaults()
    media_s = file_info["duration_s"]

    passes: list[dict] = []
    calibration = None
    interrupted = False
    try:
        throughput = run_pass("throughput", file_path, sync=False, eos_after=-1,
                              frames_expected=None, timeout_s=(media_s or 1800.0) * 2 + 60,
                              sink_defaults=sink_defaults)
        passes.append({"index": 1, **throughput})
        framerate = throughput["framerate"]
        frames_in_file = round(media_s * framerate) if media_s and framerate else None
        passes[0]["frames"]["expected"] = frames_in_file

        if throughput["exit_code"] == 0 and framerate:
            calibration = run_calibration(file_path, framerate, sink_defaults)
            soak_t0 = time.monotonic()
            while True:
                offset = time.monotonic() - soak_t0
                remaining = duration_s - offset
                if remaining < MIN_SOAK_PASS_S:
                    break
                if media_s and remaining < media_s:
                    eos_after, expected, media_len = int(remaining * framerate), None, remaining
                    expected = eos_after
                else:
                    eos_after, expected, media_len = -1, frames_in_file, media_s or 3600.0
                synced = run_pass("synced", file_path, sync=True, eos_after=eos_after,
                                  frames_expected=expected, timeout_s=media_len * 1.25 + 60,
                                  sink_defaults=sink_defaults)
                passes.append({"index": len(passes) + 1, "soak_offset_s": round(offset, 3),
                               **synced})
                if synced["exit_code"] != 0 or synced["timed_out"]:
                    break  # stop rather than keep re-driving a failing GPU path
    except KeyboardInterrupt:
        interrupted = True

    summary = summarize(passes, duration_s)
    verdict = build_verdict(passes, summary, calibration, interrupted)
    measured, not_measured = measured_lists(passes)
    receipt = {
        "api": API,
        "lane": LANE,
        "title": TITLE,
        "started_at": started_at,
        "ended_at": utc_now(),
        "interrupted": interrupted,
        "approach": {
            "driver": "gst-launch-1.0 subprocess per pass; caps and fpsdisplaysink reports (-v) "
                      "and QoS messages (-m) parsed from its output",
            "pygobject_check": pygobject,
        },
        "machine": machine,
        "file": file_info,
        "config": {
            "soak_duration_s": duration_s,
            "launch_flags": LAUNCH_FLAGS,
            "gst_env": GST_ENV,
            "fps_update_interval_ms": FPS_UPDATE_INTERVAL_MS,
            "sink_defaults": sink_defaults,
            "calibration": {"frames": CALIBRATION_FRAMES, "identity_sleep_us": CALIBRATION_SLEEP_US},
            "thresholds": {"max_drop_rate": MAX_DROP_RATE,
                           "max_working_set_growth_mb": MAX_WORKING_SET_GROWTH_MB,
                           "min_soak_pass_s": MIN_SOAK_PASS_S},
        },
        "notes": NOTES,
        "verdict": verdict,
        "summary": summary,
        "measured": measured,
        "not_measured": not_measured,
        "calibration": calibration,
        "passes": passes,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"lane-b1-gst-d3d12-soak-{stamp}.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt, out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="arsenal Lane B.1: GStreamer D3D12 decode soak receipt")
    parser.add_argument("--file", default=DEFAULT_FILE, help="clip to decode (default: %(default)s)")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_S,
                        help="seconds of real-time soak after the throughput and calibration "
                             "passes (default: %(default)s)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                        help="receipt directory (default: %(default)s)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    file_path = Path(args.file).resolve()
    if not GST_LAUNCH.is_file():
        print(f"gst-launch-1.0 not found: {GST_LAUNCH}", file=sys.stderr)
        return 2
    if not file_path.is_file():
        print(f"file not found: {file_path}", file=sys.stderr)
        return 2
    receipt, out_path = run_soak(file_path, args.duration, Path(args.out_dir))
    summary = receipt["summary"]
    print(f"receipt: {out_path}")
    print(f"status: {receipt['verdict']['status']}")
    for reason in receipt["verdict"]["reasons"]:
        print(f"  {reason}")
    print(f"frames={summary['total_frames']} gated_dropped={summary['drops']['total_dropped']} "
          f"fps_p50={summary['current_fps']['p50']} fps_p5={summary['current_fps']['p5']} "
          f"throughput_fps={(summary['throughput'] or {}).get('fps')}")
    return 0 if receipt["verdict"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
