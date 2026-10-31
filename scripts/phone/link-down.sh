#!/data/data/com.termux/files/usr/bin/bash
# link-down -- close the phone's shell door (Termux:Widget button).
#
# WHAT "DOWN" MEANS HERE, stated because it is easy to mean the wrong thing: this stops the phone's sshd,
# which is the door the PC's PhoneLink watcher connects to. It does NOT turn the tailnet off -- that is
# the phone's own Tailscale switch, and cutting it would be a second, larger cut than this button claims
# to make. One button, one door.
#
# The mount on the PC side (drive P:) is NOT affected: rclone notices the door closing on its own.

set -u

SHELL_DOOR_PORT="${SHELL_DOOR_PORT:-8022}"
say()  { printf '%s\n' "$*"; }
warn() { printf '!'"'"' %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
termux_api() { if have termux-toast; then termux-toast -s "$1" >/dev/null 2>&1; fi; }

say "== link-down =="

if ! ss -ltn 2>/dev/null | grep -q ":${SHELL_DOOR_PORT}\b"; then
    say "sshd       already closed (nothing listening on :${SHELL_DOOR_PORT})"
    termux_api "link-down: already closed"
    exit 0
fi

# Only the daemon: `pkill -f sshd` would also match this script's own command line on some kernels.
pkill -x sshd >/dev/null 2>&1 || pkill -f "sshd -D" >/dev/null 2>&1
sleep 1

if ss -ltn 2>/dev/null | grep -q ":${SHELL_DOOR_PORT}\b"; then
    warn "sshd is STILL listening on :${SHELL_DOOR_PORT} -- it refused to stop"
    termux_api "link-down: sshd is still up"
    exit 1
fi

say "sshd       stopped; :${SHELL_DOOR_PORT} is closed"
say "tailnet    untouched (that switch belongs to the Tailscale app, not this button)"
termux_api "link-down: sshd closed"
exit 0
