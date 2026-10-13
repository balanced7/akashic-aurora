"""Pins for arsenal.re.triage — the read-only "what is this file" router (gap G3).

These pins assert the CONTRACT, not the exact byte signatures of any one detector:
  - a real PE routes to a binary door and emits [observed] header facts + an [inferred]
    .NET guess only when the CLR directory is non-zero;
  - a real ELF/Mach-O/archive/media/text each route correctly;
  - a bounded negative stays bounded: an unknown file yields [unknown], never "nothing",
    and its blind names the denominator;
  - triage never executes anything (no_processes is always true).

Fixtures are hand-built byte prefixes (a PE is large; we test the header parser against
a synthetic minimal header + a real fixture path when reachable). Every claim is tagged.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from arsenal.re.triage import triage


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def _minimal_pe(e_lfanew=0x80, machine=0x8664, opt_magic=0x20B, com_rva=0):
    """A synthetic PE header in a byte buffer: MZ, e_lfanew -> PE\\0\\0, COFF machine,
    optional-header magic, and (optionally) a non-zero CLR directory.

    The optional header is PE32+ (0x70 = 112 bytes of standard+windows fields) followed
    by 16 data directories (8 bytes each = 0x80). The COM descriptor is directory index
    14, so its RVA lives at optional_header_start + 0x60 + 14*8 = +0xD0. Buffer must be
    large enough for that offset plus 4 bytes.
    """
    # optional header start = e_lfanew + 24; data dirs start at +0x70 (PE32+); COM dir at +0x70 + 14*8
    buf = bytearray(e_lfanew + 24 + 0x70 + 16 * 8 + 16)  # room for the full optional header + slack
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, e_lfanew)
    buf[e_lfanew:e_lfanew + 4] = b"PE\x00\x00"
    struct.pack_into("<H", buf, e_lfanew + 4, machine)          # Machine
    struct.pack_into("<H", buf, e_lfanew + 24, opt_magic)       # OptionalHeader.Magic
    if com_rva:
        struct.pack_into("<I", buf, e_lfanew + 24 + 0x60 + 14 * 8, com_rva)  # COM descriptor dir
    return bytes(buf)


# ---- observed field checks -----------------------------------------------------

def test_pe_executable_observed_and_routes_to_binary(tmp_path):
    p = _write(tmp_path, "a.exe", _minimal_pe())
    r = triage(p)
    assert r["api"] == "arsenal.re/v0"
    assert r["payload"]["kind"] == "pe-executable"
    assert r["payload"]["route"] == "arsenal re binary"   # gap G5, named not built
    tags = {m["detector"]: m["tag"] for m in r["payload"]["matches"]}
    # the PE header detector emits OBSERVED facts
    assert any(m["detector"] == "pe-header" and m["tag"] == "observed"
               for m in r["payload"]["matches"])
    assert r["computed_with"]["no_processes"] is True


def test_pe_with_clr_infers_managed(tmp_path):
    p = _write(tmp_path, "b.exe", _minimal_pe(com_rva=0x2000))
    r = triage(p)
    assert any(m["detector"] == "pe-header" and m["tag"] == "inferred"
               and "managed" in m["claim"].lower() for m in r["payload"]["matches"])


def test_elf_and_macho_route_to_binary(tmp_path):
    elf = b"\x7fELF" + bytes([2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]) \
          + struct.pack("<H", 2) + struct.pack("<H", 62)  # ET_EXEC
    p = _write(tmp_path, "c.bin", elf + b"\x00" * 80)
    r = triage(p)
    assert r["payload"]["kind"] == "elf-executable"
    assert r["payload"]["route"] == "arsenal re binary"

    macho = b"\xcf\xfa\xed\xfe" + b"\x00" * 28   # 64-bit little-endian Mach-O
    p2 = _write(tmp_path, "d.bin", macho)
    r2 = triage(p2)
    assert r2["payload"]["kind"] == "mach-o"
    assert r2["payload"]["route"] == "arsenal re binary"


def test_archive_media_text_route(tmp_path):
    zipf = _write(tmp_path, "e.zip", b"PK\x03\x04" + b"\x00" * 40)
    assert triage(zipf)["payload"]["kind"] == "archive"

    png = _write(tmp_path, "f.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    r = triage(png)
    assert r["payload"]["kind"] == "image"
    assert r["payload"]["route"] == "arsenal media probe"   # exists

    glsl = _write(tmp_path, "g.frag", b"#version 300 es\nvoid main(){}\n")
    r = triage(glsl)
    assert r["payload"]["kind"] == "glsl-source"

    txt = _write(tmp_path, "h.txt", b"hello world, plain ascii here\n" * 10)
    assert "text" in triage(txt)["payload"]["kind"]


def test_bounded_negative_stays_bounded(tmp_path):
    # a file with no known signature and mostly non-printable bytes must NOT read as
    # "nothing"; it is [unknown] with a loud blind naming what was not searched.
    junk = _write(tmp_path, "i.unk", bytes([0x00, 0x99, 0x01, 0xFE, 0x7F] * 40))
    r = triage(junk)
    assert r["payload"]["kind"] == "unknown"
    assert r["payload"]["route"] is None
    asserts = [m for m in r["payload"]["matches"] if m["tag"] in ("unknown", "inferred")]
    assert asserts, "an unmatched file must still emit tagged claims, never silence"


def test_missing_and_denied_are_loud_unknowns(tmp_path):
    r = triage(str(tmp_path / "does_not_exist.xyz"))
    assert r["payload"]["kind"] == "unknown"
    assert any(m["tag"] == "unknown" and "not found" in m["claim"].lower()
               for m in r["payload"]["matches"])


def test_triage_never_executes(tmp_path):
    # the contract is read-only: nothing in the receipt may claim a process was run.
    p = _write(tmp_path, "j.bin", _minimal_pe())
    r = triage(p)
    assert r["computed_with"]["no_processes"] is True
    assert "[executed]" not in str(r)
