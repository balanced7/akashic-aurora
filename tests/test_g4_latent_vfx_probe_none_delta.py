"""G4.P2 S latent fix: the VFX probes crashed on a pair with no opaque pixel in common.

pixel_delta()/chroma_delta() return None when no pixel is opaque in both images, and both probes
then formatted `{delta * 100:.1f}`, a TypeError that ended the run mid-report. Fully transparent
renders (an empty canvas, a failed capture) hit it. The probes now print "n/a" for the percentage.
"""

import struct
import zlib
from pathlib import Path

import pytest

from scripts import vfx_probe_chroma, vfx_probe_metrics


def _transparent_png(path: Path, w: int = 4, h: int = 4) -> None:
    """Write a filter-0 RGBA PNG with alpha 0 everywhere (the hand-rolled decoder reads filter 0 only)."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    raw = b"".join(b"\x00" + b"\x00" * (4 * w) for _ in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


def test_chroma_probe_reports_a_none_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The look-geodesic triplet, all transparent: the pairwise block prints n/a and the run ends."""
    for name in ("look-geodesic-original", "look-geodesic-neon-blue", "look-geodesic-ident-edges"):
        _transparent_png(tmp_path / f"{name}.png")
    monkeypatch.setattr(vfx_probe_chroma, "SNAPS", tmp_path)
    vfx_probe_chroma.main()  # TypeError: NoneType * int, before the fix
    out = capsys.readouterr().out
    assert "luminance_delta = None  (n/a pixels >10 luma diff)" in out
    assert "chroma_delta    = None  (n/a pixels >5 chroma diff)" in out
    assert "JUDGEMENT" in out


def test_metrics_probe_reports_a_none_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every probed render transparent: the sequential deltas print n/a and the run ends."""
    for name in (
        "look-geodesic-original",
        "look-geodesic-neon-blue",
        "look-geodesic-ident-edges",
        "neon-a-composing-claude",
        "neon-b-composing-blue",
        "neon-c-idle-blue",
        "ingest-geodesic-original",
        "ingest-ringpulse",
        "feed-thinking",
        "grid-thick-x-gap",
    ):
        _transparent_png(tmp_path / f"{name}.png")
    monkeypatch.setattr(vfx_probe_metrics, "SNAPS", tmp_path)
    vfx_probe_metrics.main()  # TypeError: NoneType * int, before the fix
    out = capsys.readouterr().out
    assert "None (n/a of non-transparent pixels changed by >10 lum)" in out
    assert "JUDGEMENT" in out
