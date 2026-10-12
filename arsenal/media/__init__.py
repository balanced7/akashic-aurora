"""arsenal.media -- the house video toolbox: one place every agent, the editor and the coaching runs call.

v0, 2026-10-12. The decisions behind it are in arsenal/media/README.md. Every primitive returns a dict carrying
`api`, `source`, `params`, `computed_with`, its payload and `blind` (what it cannot see), and writes the same dict
as a receipt under state/arsenal/receipts/media/<verb>/.

Imports here stay lazy: `py -m arsenal.media doctor` must not pay for numpy, PyAV or OpenCV.
"""

API = "arsenal.media/v0"


def api(verb: str) -> str:
    """The api tag of one primitive's result, e.g. api("cut") -> "arsenal.media.cut/v0"."""
    return f"arsenal.media.{verb}/v0"
