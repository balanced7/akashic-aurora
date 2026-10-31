# The phone side: three Termux:Widget buttons, and how they get there

Daniel, 2026-10-31: *"can we build a management app for our connections and services on my phone?"* —
and the reason the link part belongs here rather than on the PC: on that same day the phone's Tailscale
had been **offline for 18 hours**, so the PC could not reach it and nothing running on the PC could fix
that. The side that is still up has to be the side that can restore the link.

Three scripts, one button each:

| script | the button's job |
|--------|------------------|
| `link-up.sh` | start the phone's `sshd` (the door the PC connects to on `:8022`) and bring the Tailscale app to the front so its own switch is one tap away |
| `link-down.sh` | close that door. **Not** the tailnet — that switch belongs to the Tailscale app, and a button that quietly did both would be claiming more than it does |
| `link-status.sh` | what each rung looks like right now, with `UNKNOWN` where Termux genuinely cannot look |

## What Daniel installs (from **F-Droid**, not Play — Termux's Play build is deprecated)

1. **Termux** — https://f-droid.org/packages/com.termux/
2. **Termux:Widget** — the home-screen buttons. https://f-droid.org/packages/com.termux.widget/
3. **Termux:API** — optional but recommended: it is what lets a button say what it did
   (`termux-toast`) and keeps Termux from being frozen while the PC looks for it (`termux-wake-lock`).
   https://f-droid.org/packages/com.termux.api/

Then, inside Termux:

```
pkg update && pkg install openssh iproute2 curl
mkdir -p ~/.shortcuts/tasks
```

## Getting the scripts onto the phone

`push-to-phone.ps1` does it from the PC, over the **existing** `ssh s24` path that PhoneLink already
uses — and only when the phone answers. It writes into `~/.shortcuts/tasks/` (Termux's own folder) and
touches nothing else on the phone: no settings, no other package, no system directory.

```
powershell -File E:\AI-Setup\scripts\phone\push-to-phone.ps1
powershell -File E:\AI-Setup\scripts\phone\push-to-phone.ps1 -WhatIf   # say what it would do
```

If the phone is unreachable, the script says so and stops. It does **not** pretend, and it does not try
to wake the phone — that is what the buttons on the phone are for.

## Placing the buttons

Long-press the home screen → **Widgets** → **Termux:Widget** → drag a **Task** widget out → choose
`link-up`, `link-down`, `link-status`. Each becomes a one-tap button.

## Why the scripts refuse to be clever

* **They never change an Android setting.** A Termux process cannot toggle the VPN, and a script that
  tried would either fail silently or need permissions the phone should not grant. What it does instead
  is bring the Tailscale app up so the switch is one tap away — the honest version of the same help.
* **A missing piece is named, never swallowed.** No `openssh` → the line says `pkg install openssh`. No
  `ss` → the sshd rung reads `UNKNOWN` rather than `DOWN`, because "I could not look" and "it is off"
  are different sentences.
* **`link-status` ends with one end-to-end measurement**: a GET to the PC panel on this phone's own
  `127.0.0.1:8789`, which only answers when sshd *and* the PhoneLink tunnel *and* the PC panel are all
  up. One line that is worth more than the three rungs above it, and it says which three things it
  cannot distinguish when it fails.
