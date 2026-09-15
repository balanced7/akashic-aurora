"""Coupling-census pins: the preset bank's audio-listening profile must be countable, and
the counter must not be fooled by the two ways a preset can look like it listens."""
from __future__ import annotations

from arsenal import presets as P

HEADER = '//! {{"id": "{id}", "name": "{name}", "author": "test"}}\n'
PROLOGUE = ("#version 300 es\n{header}precision highp float;\n"
            "in vec2 v_uv;\nout vec4 outColor;\nuniform sampler2D u_video, u_prev;\n"
            "uniform vec2 u_res, u_video_res;\nuniform float u_time;\n")


def _preset(tmp_path, pid, body):
    text = PROLOGUE.format(header=HEADER.format(id=pid, name=pid)) + body
    path = tmp_path / f"{pid}.frag"
    path.write_text(text, encoding="utf-8")
    return path


def test_declared_but_never_read_is_silent(tmp_path):
    """Seven audio uniforms declared, none referenced -- decoration, and the census says so."""
    p = _preset(tmp_path, "decorated", "uniform float u_beat, u_bass, u_mid, u_high, u_pulse, u_level, u_flux;\n"
                                      "void main() { outColor = vec4(v_uv, 0.0, 1.0); }\n")
    row = P.coupling(p)
    assert row["references"] == 0 and row["distinct"] == 0
    assert row["verdict"] == "silent"


def test_glow_only_is_cosmetic(tmp_path):
    p = _preset(tmp_path, "lamp", "uniform float u_pulse, u_beat;\n"
                                  "void main() { vec4 col = vec4(v_uv, 0.0, 1.0);"
                                  " col += col * (0.25 * (0.4 + u_pulse + u_beat));"
                                  " outColor = col; }\n")
    row = P.coupling(p)
    assert row["distinct"] == 2 and row["references"] == 2
    assert row["verdict"] == "cosmetic", row


def test_structural_use_is_listening_or_driven(tmp_path):
    p = _preset(tmp_path, "alive",
                "uniform float u_beat, u_bass, u_mid, u_high, u_pulse, u_level, u_flux;\n"
                "void main() { float z = 1.0 + 0.1 * u_beat; float w = u_bass * u_mid;"
                " float v = u_high + u_flux + u_pulse + u_level;"
                " outColor = vec4(v_uv * z, w + v, 1.0); }\n")
    row = P.coupling(p)
    assert row["distinct"] == 7 and row["references"] == 7
    assert row["verdict"] == "driven", row


def test_comments_do_not_count_as_use(tmp_path):
    p = _preset(tmp_path, "talker", "uniform float u_beat;\n"
                                    "// u_beat is mentioned here and must not count\n"
                                    "void main() { outColor = vec4(v_uv, 0.0, 1.0); }\n")
    row = P.coupling(p)
    assert row["references"] == 0, row


def test_the_real_bank_is_censused_without_raising():
    rows = P.coupling_table()
    assert rows, "the preset bank should not be empty"
    for r in rows:
        assert r["verdict"] in {"silent", "cosmetic", "listening", "driven"}
        assert r["references"] == sum(r["used"].values())
