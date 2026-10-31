#!/data/data/com.termux/files/usr/bin/bash
# link-up -- bring the PC's door back, from the phone (Termux:Widget button).
#
# WHY THIS LIVES ON THE PHONE, in the words of the day it was asked for: on 2026-10-31 the S24's
# Tailscale had been offline for 18 hours, so the PC could not reach it and nothing on the PC could fix
# that. Anything whose job is to RESTORE THE LINK has to run on the side that is still up. This script is
# that side.
#
# What it does, in order, and nothing else:
#   1. starts the phone's sshd (the shell door the PC's PhoneLink watcher connects to on :8022),
#   2. brings the Tailscale app to the front (its own toggle then connects -- this script does NOT flip
#      a system setting, because Termux cannot and should not),
#   3. prints what is up and what is MISSING, in plain words, so a half-install is never silent.
#
# WHAT IT WILL NOT DO: change a phone setting, install a package, or touch any directory outside
# Termux's own $HOME. If something needed for the link is absent, it says which piece and where to get it.
#
# The two companions are link-status (what the link looks like right now) and link-down (close the door).
# Install all three as Termux:Widget buttons; see README.md beside this file.

set -u

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SHELL_DOOR_PORT="${SHELL_DOOR_PORT:-8022}"
TAILSCALE_PKG="${TAILSCALE_PKG:-com.tailscale.ipn}"
MISSING=""
say()  { printf '%s\n' "$*"; }
warn() { printf '!'"'"' %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Termux:API is optional but it is how the result reaches him when the widget runs headless. Its absence
# is reported, never hidden: a silent no-op is the failure mode this whole file exists to avoid.
termux_api() {
    if have termux-toast; then termux-toast -s "$1" >/dev/null 2>&1; fi
}

say "== link-up =="

# ---- 1. the shell door -------------------------------------------------------------------------
if have sshd; then
    if ss -ltn 2>/dev/null | grep -q ":${SHELL_DOOR_PORT}\b"; then
        say "sshd       already listening on :${SHELL_DOOR_PORT}"
    else
        # sshd daemonises itself; its failure is readable from the exit status.
        if sshd >/dev/null 2>&1; then
            sleep 1
            if ss -ltn 2>/dev/null | grep -q ":${SHELL_DOOR_PORT}\b"; then
                say "sshd       STARTED on :${SHELL_DOOR_PORT}"
            else
                warn "sshd ran but nothing is listening on :${SHELL_DOOR_PORT} (check: sshd -D -e)"
                MISSING="${MISSING} sshd-listening"
            fi
        else
            warn "sshd failed to start (check: sshd -D -e; the host keys may need: ssh-keygen -A)"
            MISSING="${MISSING} sshd-start"
        fi
    fi
else
    warn "openssh is not installed: run  pkg install openssh"
    MISSING="${MISSING} openssh"
fi

# ---- 2. Tailscale, brought to the front ---------------------------------------------------------
# A Termux process cannot toggle the Android VPN itself. What it CAN do is put the app's own toggle one
# tap away, which is the difference between "unreachable for 18 hours" and "fixed in two taps".
if have am || have monkey; then
    if pm list packages 2>/dev/null | grep -q "^package:${TAILSCALE_PKG}$"; then
        ACTIVITY=""
        if have cmd; then
            ACTIVITY="$(cmd package resolve-activity --brief "$TAILSCALE_PKG" 2>/dev/null | tail -n 1)"
        fi
        case "$ACTIVITY" in
            */*) am start -n "$ACTIVITY" >/dev/null 2>&1 || ACTIVITY="" ;;
        esac
        if [ -z "$ACTIVITY" ] && have monkey; then
            monkey -p "$TAILSCALE_PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
        fi
        say "tailscale  app brought to the front -- confirm its switch is ON"
    else
        warn "${TAILSCALE_PKG} is not installed on this phone"
        MISSING="${MISSING} tailscale-app"
    fi
else
    warn "neither 'am' nor 'monkey' is available, so Tailscale cannot be raised"
    MISSING="${MISSING} am"
fi

# Keep Termux alive long enough for the PC's watcher (it polls; it does not need a fast phone).
if have termux-wake-lock; then
    termux-wake-lock >/dev/null 2>&1 && say "wake-lock  held, so Termux is not frozen while the PC looks"
else
    warn "Termux:API not installed: no toast, no wake-lock (install Termux:API from F-Droid, then: pkg install termux-api)"
    MISSING="${MISSING} termux-api"
fi

# ---- 3. the verdict ----------------------------------------------------------------------------
if [ -n "$MISSING" ]; then
    say ""
    say "LINK NOT FULLY UP. Missing:${MISSING}"
    termux_api "link-up: incomplete --${MISSING}"
    exit 1
fi
say ""
say "LINK UP: the PC's PhoneLink watcher can now find this phone (sshd :${SHELL_DOOR_PORT} + tailnet)."
say "If the PC still cannot see it, open Tailscale on THIS phone and check the switch."
termux_api "link-up: sshd is up; tailnet needs the Tailscale switch"
exit 0
