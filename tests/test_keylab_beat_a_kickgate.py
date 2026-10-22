"""Pin for the kick gate in beat_a (2026-10-22): kick_likeness() rates a synthetic drum loop high, and both a
hats-only synthetic and a sustained tone low. Plus a mutation receipt: mutating the relative-sharpness sign (the
load-bearing axis) flips the drum verdict and the pin goes RED. stdlib + numpy only, matching the licence firewall.
"""
import numpy as np

from arsenal.keylab import beat_a as A


def _band_hist_from_env(low_env, hat_env, n=256):
    """Build a synthetic band_hist from a low-band and a hats-band flux series (the gate only reads cols 0,1,3)."""
    h = np.zeros((n, 4), dtype=np.float32)
    h[:, 0] = low_env * 0.7
    h[:, 1] = low_env * 0.3
    h[:, 3] = hat_env
    return h


def test_kick_likeness_rates_synthetic_drums_high():
    # A kick loop: low band is SPIKY (one sharp pulse per beat), hats band is STEADY.
    n = 256
    low = np.zeros(n, dtype=np.float32)
    low[::32] = 10.0                        # sparse, tall kick spikes
    hat = np.full(n, 1.0, dtype=np.float32)  # steady hats
    h = _band_hist_from_env(low, hat, n)
    assert A.kick_likeness(h) >= A.KICK_GATE


def test_kick_likeness_rates_hats_only_low():
    # Hats-only: low band ~flat (no kick), hats band SPIKY -> relative sharpness goes negative.
    n = 256
    low = np.full(n, 0.1, dtype=np.float32)
    hat = np.zeros(n, dtype=np.float32)
    hat[::16] = 5.0
    h = _band_hist_from_env(low, hat, n)
    assert A.kick_likeness(h) < A.KICK_GATE


def test_kick_likeness_rates_sustained_tone_low():
    # Sustained tonal line: BOTH bands are flat (no transient anywhere) -> low sharpness, low magnitude ratio.
    n = 256
    low = np.full(n, 1.0, dtype=np.float32)
    hat = np.full(n, 1.0, dtype=np.float32)
    h = _band_hist_from_env(low, hat, n)
    assert A.kick_likeness(h) < A.KICK_GATE


def test_mutation_receipt_breaks_on_sign_flip():
    """The load-bearing axis is the SIGN of (low sharpness - hats sharpness). Flip it and the drum verdict, which
    was high above the gate, drops below: the pin is genuinely sensitive to the gate, not vacuous."""
    n = 256
    low = np.zeros(n, dtype=np.float32)
    low[::32] = 10.0
    hat = np.full(n, 1.0, dtype=np.float32)
    h = _band_hist_from_env(low, hat, n)
    base = A.kick_likeness(h)
    # Mutate: swap low/hat roles (make hats spiky, low steady) -- the opposite material.
    h_swap = _band_hist_from_env(hat, low, n)
    mutated = A.kick_likeness(h_swap)
    assert base >= A.KICK_GATE and mutated < A.KICK_GATE, (base, mutated)
