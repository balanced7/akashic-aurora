"""Bind-policy pins — which interface the inbound listener may face (remote-bridge v1.1).

v1 shipped a BINARY policy: loopback, or --allow-public. That was right for the loopback drill
and wrong the moment a real peer appeared, because the world has three categories and the flag
only named two:

  loopback          nothing outside this machine can reach it
  private overlay   a mesh/LAN address -- Tailscale 100.64/10, RFC1918, link-local. Reachable
                    only by nodes already admitted to that network, which is a DIFFERENT and
                    much smaller population than "the internet"
  actually public   a globally-routable address, or the WILDCARD, which is worse than any
                    single public address because it binds every interface at once

Forcing an operator to type --allow-public to bind a Tailscale address does two kinds of harm.
It writes a false sentence in the log ("[PUBLIC]" about an address the internet cannot route
to), and it teaches the hand to reach for the dangerous flag in the safe case -- so the flag
stops meaning anything on the day it matters. A guard that cries wolf gets switched off.

WHY THE POLICY READS INTERFACES AND NOT JUST RANGES. The first draft of this fix classified by
IP range alone. This machine falsified it before it was written: Radmin VPN hands out
26.245.203.188, and 26.0.0.0/8 is real IANA public space that Radmin squats. A pure range check
calls that overlay address "public" and demands the flag. So the policy ALSO resolves which
local interface owns the address and names it in the receipt -- 'bound to "Radmin VPN"' is a
true and useful sentence where '[PUBLIC]' is a false one. The squatted-range case still needs
the operator to say so out loud (--allow-public), and that is documented rather than hidden,
because silently trusting an unknown public range would be the worse failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts import remote_bridge_listener as L  # noqa: E402


# ------------------------------------------------------------------ the three categories
@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_always_allowed(host):
    ok, why = L.bind_allowed(host, allow_public=False)
    assert ok, f"loopback {host} refused: {why}"
    assert L.bind_class(host) == "loopback"


@pytest.mark.parametrize("host,label", [
    ("100.101.102.103", "Tailscale CGNAT 100.64/10"),
    ("100.64.0.1", "CGNAT lower edge"),
    ("100.127.255.254", "CGNAT upper edge"),
    ("192.168.1.50", "RFC1918 /16"),
    ("10.0.0.5", "RFC1918 /8"),
    ("172.16.0.9", "RFC1918 /12"),
    ("169.254.10.10", "link-local"),
    ("fd00::1", "IPv6 ULA"),
    # RFC 5737 documentation range. Python's is_private covers it because the IANA
    # special-purpose registry marks it never-routed -- and "never routed" is exactly the
    # property this policy cares about, so private is the CORRECT answer, not a leak. Pinned
    # deliberately: the first draft of this file listed it as an example of "globally
    # routable" and went red, which is the check earning its keep on its first run.
    ("203.0.113.9", "TEST-NET-3 -- reserved, never routed"),
])
def test_private_overlay_allowed_without_the_public_flag(host, label):
    """THE POINT OF THE WHOLE FIX. A tailnet address is not the internet, and making someone
    say --allow-public to bind one is both a lie in the log and a lesson in ignoring the flag."""
    ok, why = L.bind_allowed(host, allow_public=False)
    assert ok, f"{label} ({host}) was refused without --allow-public: {why}"
    assert L.bind_class(host) == "private", f"{label} misclassified as {L.bind_class(host)!r}"


@pytest.mark.parametrize("host,label", [
    ("8.8.8.8", "public resolver -- genuinely routable"),
    ("1.1.1.1", "public resolver -- genuinely routable"),
    ("26.245.203.188", "Radmin VPN -- squatted PUBLIC space, documented false positive"),
])
def test_public_address_still_requires_the_flag(host, label):
    ok, why = L.bind_allowed(host, allow_public=False)
    assert not ok, f"{label} ({host}) bound without the flag"
    assert "public" in why.lower()
    assert L.bind_allowed(host, allow_public=True)[0], "the flag must still work when meant"


def test_wildcard_is_treated_as_public_not_private():
    """0.0.0.0 is the WORST case, not a neutral one: it binds every interface at once,
    including any public one, so it can never be inferred safe from its own digits."""
    for host in ("0.0.0.0", "::"):
        ok, why = L.bind_allowed(host, allow_public=False)
        assert not ok, f"wildcard {host} was allowed without the flag"
        assert L.bind_class(host) == "public"


# ------------------------------------------------------------------ the receipt must not lie
def test_receipt_names_the_category_truthfully():
    """The log line is the whole reason this fix exists. A tailnet bind must not print the
    word the operator would read as 'exposed to the internet'."""
    assert "PUBLIC" not in L.bind_banner("100.101.102.103").upper()
    assert "PUBLIC" in L.bind_banner("8.8.8.8").upper()
    assert L.bind_banner("127.0.0.1").strip() == "", "loopback needs no warning at all"


def test_private_banner_says_which_network():
    """'private' alone is not actionable -- WHICH private network is the thing an operator
    needs to see, because 'bound somewhere only my mesh can reach' is only reassuring if you
    can name the mesh."""
    b = L.bind_banner("100.101.102.103")
    assert b, "a non-loopback bind must say something"
    assert "100.101.102.103" in b


def test_unparseable_host_is_refused_not_guessed():
    """A hostname we cannot classify must not fall through to 'allow'. Absent knowledge is
    refusal, never permission -- the same rule the inbound gate follows."""
    for junk in ("", "not a host", "999.999.999.999", "example.com"):
        ok, why = L.bind_allowed(junk, allow_public=False)
        assert not ok, f"unclassifiable host {junk!r} was allowed"


def test_policy_never_raises():
    for junk in (None, 12345, [], {}, "::::::"):
        try:
            L.bind_allowed(junk, allow_public=False)
            L.bind_class(junk)
            L.bind_banner(junk)
        except Exception as e:                                    # noqa: BLE001
            pytest.fail(f"bind policy raised on {junk!r}: {type(e).__name__}: {e}")
