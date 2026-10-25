"""The VJ colour-theme library (arsenal/web/vj-themes.json) against the KeyLab pad rule and the saturated-red rule, in
Python's own colorsys: the rule tests/test_keylab_w0.py applies to the chord colours, applied here to every pad stand-in.
The full checks (the module, the fader walk, bar-quantised changes, keys, sections) are in tests/vj_themes.test.mjs; this
file guards that the JavaScript port of the rule agrees with the canonical one (spec receipt A4, "Node and pytest")."""

import colorsys
import json
from pathlib import Path

import pytest

LIBRARY = json.loads((Path(__file__).resolve().parent.parent / "arsenal" / "web" / "vj-themes.json").read_text("utf-8"))
THEMES = LIBRARY["themes"]
WASH_ZONE = (15.0, 100.0)   # as tests/test_keylab_w0.py: orange through lime renders close to white on the pads
ROLES = ("A", "B", "W")


def _rgb(hexcode):
    return tuple(int(hexcode[i:i + 2], 16) for i in (1, 3, 5))


def _lin(c):
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _saturated_red(hexcode):
    r, g, b = _rgb(hexcode)
    lr, lg, lb = _lin(r), _lin(g), _lin(b)
    return (r / max(1, r + g + b)) >= 0.8 or (lr / max(1e-12, lr + lg + lb)) >= 0.8


def _laser_hex(theme, role):
    return theme.get("beam", {}).get(role) or theme[role]


@pytest.mark.parametrize("theme", THEMES, ids=[t["id"] for t in THEMES])
def test_every_pad_stand_in_reads_on_the_pads(theme):
    for role in ROLES:
        rgb = _rgb(theme["led"][role])
        if rgb == (255, 255, 255):
            continue
        h, _l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
        h *= 360
        assert s > 0.5, f"{theme['id']} led.{role} {theme['led'][role]} is too unsaturated to read on the pads"
        assert not (WASH_ZONE[0] <= h <= WASH_ZONE[1]), f"{theme['id']} led.{role} (hue {h:.0f}) washes to white"
    for role, level in theme.get("led_level", {}).items():
        assert theme["led"][role] == "#ffffff" and 0 < level <= 1, f"{theme['id']} led_level.{role}"


@pytest.mark.parametrize("theme", THEMES, ids=[t["id"] for t in THEMES])
def test_no_saturated_red_in_a_strobing_role(theme):
    held = set(theme["held"])
    for role in ROLES:
        if _saturated_red(theme[role]) or _saturated_red(_laser_hex(theme, role)):
            assert role in held, f"{theme['id']} {role} is saturated red but not held"
    emitted = list(theme["lasers"]) + theme["strobe"]["triple"] + theme["strobe"]["flicker"] + theme["burst"]
    for role in emitted:
        assert role not in held, f"{theme['id']} emits its held role {role}"
        assert not _saturated_red(_laser_hex(theme, role)), f"{theme['id']} laser {role} {_laser_hex(theme, role)}"
    flash = "#ffffff" if theme["fx"]["flash"] == "white" else theme[theme["fx"]["flash"]]
    assert not _saturated_red(flash), f"{theme['id']} flash {flash}"


def test_six_distinct_saturated_reds_and_a_fader_detent_for_every_theme():
    reds = {theme[r] for theme in THEMES for r in ROLES if _saturated_red(theme[r])}
    assert sorted(reds) == ["#85063f", "#ab0a1c", "#d63b09", "#db0001", "#ea7720", "#ff1a3c"]
    order = LIBRARY["fader_order"]
    assert sorted(order) == sorted([t["id"] for t in THEMES] + ["custom"])
    assert len(THEMES) == 21 and len({t["family"] for t in THEMES}) == 8
