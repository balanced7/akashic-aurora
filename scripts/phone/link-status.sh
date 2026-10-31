#!/data/data/com.termux/files/usr/bin/bash
# link-status -- what the link looks like RIGHT NOW, from the phone (Termux:Widget button).
#
# THE HONESTY RULE, and it is the same one the PC panel follows: a check that cannot run reports
# UNKNOWN, never a confident DOWN. Answering "no sshd" when the truth is "this phone has no `ss`
# installed" sends the reader hunting a fault that does not exist, and the reader here is holding a phone
# in another room.
#
# It prints one line per rung: the shell door, the tailnet, the Termux pieces the widgets need, and
# whether the PC panel is reachable THROUGH the tunnel (a plain HTTP GET to the forwarded port -- which
# only answers if the whole chain is up, so it is the one line that is a measurement of everything).

set -u

SHELL_DOOR_PORT="${SHELL_DOOR_PORT:-8022}"
PANEL_PORT="${PANEL_PORT:-8789}"
TAILSCALE_PKG="${TAILSCALE_PKG:-com.tailscale.ipn}"
say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

say "== link-status =="

# ---- the shell door -----------------------------------------------------------------------------
if have ss; then
    if ss -ltn 2>/dev/null | grep -q ":${SHELL_DOOR_PORT}\b"; then
        say "sshd        UP    listening on :${SHELL_DOOR_PORT}"
    else
        say "sshd        DOWN  nothing on :${SHELL_DOOR_PORT} -- tap link-up"
    fi
else
    say "sshd        UNKNOWN  no 'ss' command (pkg install iproute2); cannot say whether it listens"
fi

# ---- the tailnet --------------------------------------------------------------------------------
# Termux cannot read Android's VPN state. What it CAN say is whether the app is installed and whether
# the phone holds a tailnet-shaped address, and both of those are stated as what they are.
if pm list packages 2>/dev/null | grep -q "^package:${TAILSCALE_PKG}$"; then
    say "tailscale   installed (its switch is the phone's own; this script cannot read it)"
else
    say "tailscale   NOT INSTALLED (${TAILSCALE_PKG})"
fi
TAILNET_IP="$(ip -4 addr 2>/dev/null | grep -o '100\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}' | head -n 1)"
if [ -n "${TAILNET_IP}" ]; then
    say "tailnet ip  ${TAILNET_IP}  (an interface holds a 100.x address)"
else
    say "tailnet ip  UNKNOWN  no 100.x address is visible to Termux (this is not proof the tailnet is off)"
fi

# ---- the Termux pieces -------------------------------------------------------------------------
if have termux-toast; then say "Termux:API  installed"; else say "Termux:API  MISSING -- no toast, no wake-lock"; fi
if have sshd;      then say "openssh    installed"; else say "openssh    MISSING -- pkg install openssh"; fi

# ---- the one end-to-end measurement ------------------------------------------------------------
# The PC panel is only reachable at this phone's own 127.0.0.1 through the PhoneLink watcher's tunnel.
# If this answers, sshd + the tunnel + the PC panel are ALL up. If it does not, any of the three could be
# the missing piece -- so the line names all three rather than blaming one.
if have curl; then
    if curl -fsS --max-time 4 "http://127.0.0.1:${PANEL_PORT}/api/health" >/dev/null 2>&1; then
        say "PC panel    UP    http://127.0.0.1:${PANEL_PORT} answers through the tunnel"
    else
        say "PC panel    UNREACHABLE  no answer on 127.0.0.1:${PANEL_PORT}"
        say "                   (ssh door, the PhoneLink watcher's -R forward, or the PC panel process)"
    fi
else
    say "PC panel    UNKNOWN  no curl (pkg install curl)"
fi

exit 0
