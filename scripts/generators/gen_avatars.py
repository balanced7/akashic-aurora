"""Generate seat avatars from the Bifrost designation grammar (2026-08-18).

Family = the disc's fill. Team = the ring. Initial = the mark, until a seat's
self-selected emoji (which rides the USERNAME, not the image) makes the name its
own. Colors come from core/fleet/residents.py placements -- never a second
hand-kept table (Heimdall's drift warning, honored).

Run:  py scripts/generators/gen_avatars.py     -> assets/avatars/<callsign>.png
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from core.fleet import residents as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "avatars")

FAMILY_FILL = {"Amber": (232, 161, 60), "Onyx": (43, 43, 51), "Jade": (39, 161, 122)}
TEAM_RING = {"Blue": (59, 110, 245), "Red": (214, 69, 69)}
#: glyph color per family -- Onyx is dark, so its mark goes light.
MARK = {"Amber": (24, 18, 8), "Onyx": (235, 235, 242), "Jade": (10, 26, 20)}

SIZE = 256
RING_W = 18


def render(callsign: str, family: str, team: str) -> str:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = FAMILY_FILL.get(family, (110, 110, 110))
    ring = TEAM_RING.get(team, (160, 160, 160))
    d.ellipse([0, 0, SIZE - 1, SIZE - 1], fill=ring)
    d.ellipse([RING_W, RING_W, SIZE - 1 - RING_W, SIZE - 1 - RING_W], fill=fill)
    try:
        font = ImageFont.truetype("arialbd.ttf", 128)
    except OSError:
        font = ImageFont.load_default()
    letter = (callsign or "?")[0].upper()
    bbox = d.textbbox((0, 0), letter, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1]), letter,
           fill=MARK.get(family, (255, 255, 255)), font=font)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{callsign.lower()}.png")
    img.save(path)
    return path


def main() -> int:
    made = []
    for agent in ("claude", "deepseek", "kimi", "codex"):
        rec = R.get(agent)
        place = R.current_placement(agent)
        if not rec or not place:
            print(f"[avatars] {agent}: unplaced in the residents registry -- no avatar "
                  f"(honest absence; ratification mints the face)")
            continue
        cs = rec.get("callsign", agent)
        p = render(cs, place.get("family", ""), place.get("team", ""))
        made.append(p)
        print(f"[avatars] {cs}: {place.get('family')} disc, {place.get('team')} ring -> {p}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
