"""arsenal.lanes.hwdecode_soak -- Lane B.0 receipt.

CLI:
    py arsenal\\lanes\\hwdecode_soak.py --path P --minutes N [--device auto|d3d12va|d3d11va]

Picks the first device that actually yields hardware frames (or the requested one, if not
"auto"), loops the file until N minutes have passed, and writes a receipt JSON to
state/arsenal/receipts/hwdecode-<timestamp>.json. Ctrl+C stops cleanly and still writes
whatever was accumulated so far.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import av
from av.codec.hwaccel import HWAccel

_LANES_DIR = Path(__file__).resolve().parent
_ARSENAL_DIR = _LANES_DIR.parent
_REPO_ROOT = _ARSENAL_DIR.parent
RECEIPTS_DIR = _REPO_ROOT / "state" / "arsenal" / "receipts"

DEVICE_CHOICES = ("auto", "d3d12va", "d3d11va")
_AUTO_CANDIDATES = ("d3d12va", "d3d11va")
_EVIDENCE_PROBE_FRAMES = 10


def _load_analysis():
    """arsenal/__init__.py may not exist yet (another agent owns it); fall back to loading
    analysis.py directly by path so this script works either way."""
    try:
        from arsenal import analysis  # type: ignore
        return analysis
    except ImportError:
        spec = importlib.util.spec_from_file_location(
            "arsenal_analysis_standalone", _ARSENAL_DIR / "analysis.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module


analysis = _load_analysis()


def _pick_device(abspath: str, device_arg: str):
    """Returns (device, frame_format_or_None, used_software_fallback, evidence_list)."""
    candidates = _AUTO_CANDIDATES if device_arg == "auto" else (device_arg,)
    evidence = []
    for device in candidates:
        result = analysis.hw_decode_evidence(abspath, devices=(device,), frames=_EVIDENCE_PROBE_FRAMES)
        entry = result["tried"][0]
        evidence.append(entry)
        if entry["ok"]:
            return device, entry["frame_format"], False, evidence
    # Nothing yielded real hardware frames -- still run the soak (honestly, as software) on
    # the first candidate rather than refusing to produce a receipt at all.
    return candidates[0], None, True, evidence


def _open_decode_pass(abspath: str, device: str):
    """One full demux+decode pass over the file, yielding each frame's format name."""
    hwaccel = HWAccel(device_type=device, allow_software_fallback=True, is_hw_owned=True)
    with av.open(abspath, hwaccel=hwaccel) as container:
        if not container.streams.video:
            raise RuntimeError("no video stream")
        vstream = container.streams.video[0]
        for frame in container.decode(vstream):
            yield frame.format.name


def run_soak(path: str, minutes: float, device_arg: str) -> dict:
    abspath = str(Path(path).resolve())
    device, frame_format, used_software_fallback, evidence = _pick_device(abspath, device_arg)

    deadline = time.monotonic() + minutes * 60.0
    start = time.monotonic()
    total_frames = 0
    per_minute = []
    errors = []
    interrupted = False

    minute_index = 0
    minute_start = start
    minute_frames = 0

    try:
        while time.monotonic() < deadline:
            try:
                for fmt in _open_decode_pass(abspath, device):
                    frame_format = fmt
                    total_frames += 1
                    minute_frames += 1

                    now = time.monotonic()
                    if now - minute_start >= 60.0:
                        per_minute.append({
                            "minute": minute_index,
                            "frames": minute_frames,
                            "fps": minute_frames / (now - minute_start),
                        })
                        minute_index += 1
                        minute_start = now
                        minute_frames = 0

                    if now >= deadline:
                        break
            except Exception as exc:  # noqa: BLE001 -- record and stop, never crash the soak
                errors.append(f"{type(exc).__name__}: {exc}")
                break
            # file exhausted before the deadline (typical for a short clip): loop it again
    except KeyboardInterrupt:
        interrupted = True

    end = time.monotonic()
    if minute_frames > 0:
        span = end - minute_start
        per_minute.append({
            "minute": minute_index,
            "frames": minute_frames,
            "fps": (minute_frames / span) if span > 0 else 0.0,
        })

    elapsed = end - start
    stopped_reason = "interrupted" if interrupted else ("error" if errors else "completed")

    receipt = {
        "api": "arsenal.hwdecode_soak/v0",
        "path": abspath,
        "requested_minutes": minutes,
        "device_requested": device_arg,
        "device_used": device,
        "used_software_fallback": used_software_fallback,
        "frame_format": frame_format,
        "frame_count": total_frames,
        "elapsed_seconds": round(elapsed, 3),
        "overall_fps": round(total_frames / elapsed, 3) if elapsed > 0 else 0.0,
        "per_minute_fps": per_minute,
        "errors": errors,
        "device_evidence": evidence,
        "stopped_reason": stopped_reason,
        "timestamp": time.strftime("%Y%m%d-%H%M%S"),
    }
    _write_receipt(receipt)
    _print_summary(receipt)
    return receipt


def _write_receipt(receipt: dict) -> Path:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RECEIPTS_DIR / f"hwdecode-{receipt['timestamp']}.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    receipt["_receipt_path"] = str(out_path)
    return out_path


def _print_summary(receipt: dict) -> None:
    print(
        f"hwdecode_soak: device={receipt['device_used']} "
        f"format={receipt['frame_format']} "
        f"frames={receipt['frame_count']} "
        f"fps={receipt['overall_fps']:.2f} "
        f"elapsed={receipt['elapsed_seconds']:.1f}s "
        f"stopped={receipt['stopped_reason']} "
        f"receipt={receipt.get('_receipt_path')}"
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="arsenal Lane B.0 hardware-decode soak")
    parser.add_argument("--path", required=True, help="path to the clip to loop-decode")
    parser.add_argument("--minutes", required=True, type=float, help="how long to soak, in minutes")
    parser.add_argument("--device", default="auto", choices=DEVICE_CHOICES)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_soak(args.path, args.minutes, args.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
