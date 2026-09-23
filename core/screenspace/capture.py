"""Screenspace capture substrate — mss one-shot -> ScreenFrame (T386 §1.3, §2, §4.3).

This is the PIXEL half of the observe organ. It produces a ``ScreenFrame``: the
raw capture plus its physical metadata (dimensions, DPI scale, sha256) and — when
a budget is passed — a SERVER-SIDE pre-resized PNG so the long edge never exceeds
the budget (§2: "oversized images are REJECTED by the API, not shrunk", so the
engine owns the resize; the API rejection is the failure that motivated it, not
the enforcement).

DPI: PER_MONITOR_AWARE_V2 is declared at module import (§4.3: "physical pixels
end-to-end; downscale returns scale factor"). This is a per-process Windows
context flag; it is a no-op import on non-Windows and must be set before any
UI/display call.

Fail-soft substrate: ``mss`` is an OPTIONAL host-installed package (not in
requirements.txt). If it is absent, or there is no interactive display, or the
screen cannot be captured, ``capture.screen`` returns a structured
``ScreenFrame`` with ``available=False`` and ``refused`` fields set — never a
bare exception that would take down the caller, and never a fabricated frame.
The contract (structured fields) is satisfied regardless; the PIXELS are the
part that degrades honestly in a headless context.

Design invariants this substrate enforces (§4.4):
  - Screenshots are in-memory and transient by default (``persist=False``); the
    engine never writes a full-screen frame to a durable path unless asked.
  - Pre-resize to an explicit long-edge budget happens here, before return.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple


def _declare_dpi_awareness() -> None:
    """PER_MONITOR_AWARE_V2 (§4.3). No-op on non-Windows; best-effort on Windows."""
    try:
        import ctypes

        # PROCESS_PER_MONITOR_DPI_AWARE = 2 (Windows >= 8.1). Declared once, before
        # any display/window call, so physical pixels are authoritative end-to-end.
        _ = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001 — fail-soft: DPI awareness is a posture, not a gate
        pass


_declare_dpi_awareness()


def _load_mss():
    """Lazy, fail-soft loader for the optional mss substrate."""
    try:
        import mss  # type: ignore

        return mss
    except Exception:  # noqa: BLE001 — optional substrate; absence is a contract-relevant fact
        return None


@dataclass
class ScreenFrame:
    """The raw capture result (substrate altitude). Pixels plus physical truth.

    ``available`` is the honest bit: False means the substrate/display refused and
    ``pixels`` is None — NOT an empty/black frame, which would be a privacy-adjacent
    lie (cf. §4.5 locked-workstation: a capture of the secure desktop is a hole).
    """

    available: bool = False
    pixels: Optional[bytes] = None                      # PNG bytes when available
    width: int = 0
    height: int = 0
    dpi_scale: float = 1.0
    ts_ms: int = 0
    source: str = "mss"
    sha256: str = ""
    long_edge_budget: Optional[int] = None               # the budget that was applied
    resized: bool = False                                # True if we downscaled
    refuse_reason: Optional[str] = None                  # set when available=False
    transient_path: Optional[str] = None                 # only when caller persists

    def to_dict(self) -> dict:
        """Structured form (never a bare string) — the §4.1 provenance surface."""
        return {
            "available": self.available,
            "width": self.width,
            "height": self.height,
            "dpi_scale": self.dpi_scale,
            "ts_ms": self.ts_ms,
            "source": self.source,
            "sha256": self.sha256,
            "long_edge_budget": self.long_edge_budget,
            "resized": self.resized,
            "refuse_reason": self.refuse_reason,
        }


def _png_from_shot(shot_image) -> Tuple[int, int, bytes]:
    """Drain one mss screenshot into raw RGB -> PNG bytes; returns (w, h, png)."""
    # shot_image is a PIL.Image in mss >= 6; older versions give a raw byte str.
    from PIL import Image  # type: ignore

    img = shot_image if isinstance(shot_image, Image.Image) else Image.frombytes(
        "RGB", shot_image.size, shot_image.rgb
    )
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size

    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return w, h, buf.getvalue()


def _resize_to_budget(pixels: bytes, width: int, height: int, budget: int):
    """Pre-resize PNG so long edge <= budget (§2 L5 bar). Returns (png, w, h, resized)."""
    long_edge = max(width, height)
    if long_edge <= budget:
        return pixels, width, height, False
    from PIL import Image  # type: ignore

    import io

    scale = budget / float(long_edge)
    nw = max(1, int(round(width * scale)))
    nh = max(1, int(round(height * scale)))
    img = Image.open(io.BytesIO(pixels))
    img = img.resize((nw, nh), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), nw, nh, True


def screen(region=None, downscale_budget: Optional[int] = None) -> ScreenFrame:
    """One-shot full-screen (or region) capture -> ScreenFrame.

    Args:
        region: optional scope for a sub-region (reserved; full-screen is the v1
            shape, region crops are an L4 optimization that arrives with the
            cached-walk engine — currently ignored rather than half-implemented).
        downscale_budget: long-edge pixel budget (§2). When set, the returned
            pixels are pre-rescaled so ``max(width, height) <= budget`` SERVER-SIDE,
            before any caller could hand them to an API that would REJECT oversize.
            Default None = no resize (caller accepts the reject risk).

    Returns a structured ScreenFrame — never a bare byte string, never raises on
    substrate absence/headless/locked-desktop (those are honest refusals, not
    crashes).
    """
    frame = ScreenFrame(ts_ms=int(time.time() * 1000), long_edge_budget=downscale_budget)

    mss = _load_mss()
    if mss is None:
        frame.refuse_reason = "substrate-unavailable:mss-not-installed"
        return frame

    try:
        with mss.mss() as sct:
            if not sct.monitors:
                frame.refuse_reason = "no-display"
                return frame
            # monitors[0] is the virtual "all screens" bounding box.
            shot = sct.grab(sct.monitors[0])
    except Exception as exc:  # noqa: BLE001 — headless / locked / driver failure
        frame.refuse_reason = f"capture-refused:{type(exc).__name__}"
        return frame

    try:
        width, height, png = _png_from_shot(shot)
    except Exception as exc:  # noqa: BLE001 — PIL absent or bad pixels
        frame.refuse_reason = f"encode-failed:{type(exc).__name__}"
        return frame

    if downscale_budget and downscale_budget > 0:
        png, width, height, resized = _resize_to_budget(
            png, width, height, downscale_budget
        )
        frame.resized = resized

    frame.available = True
    frame.pixels = png
    frame.width = width
    frame.height = height
    frame.sha256 = hashlib.sha256(png).hexdigest()
    return frame
