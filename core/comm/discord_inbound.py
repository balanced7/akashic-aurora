"""Discord inbound — Daniil's Discord messages become his voice on the bus. Nothing else does.

Born 2026-08-19, the night he typed into #aurora and asked what happened to his message
(answer: nothing — the house had a voice there and no inbound path). This module is the R1-R3
security model of discord-bridge-design-2026-08-07 made executable, pins in
tests/test_discord_inbound_pins.py:

  R1  the operator allowlist is ONE numeric Discord id. Display names are costume —
      an author named "Daniil" with the wrong id is weather.
  R2  every non-allowlisted message is DATA, never instruction. v1 does not even
      surface it; it returns unacted and the runner moves on.
  R3  reach, never authority. The ear's ONLY write into the house is a bus send AS
      the operator — a Discord message can do exactly what a bifrost-send from his
      keyboard could, from farther away. No task verbs, no grant, no shell. The route
      (which ask a room-message belongs to) comes from the ROOMS REGISTRY, never from
      message content.

This module is PURE and hermetic: no discord.py, no network, no token. The gateway
shell (scripts/bifrost_runner_discord.py) owns the credential and the socket; everything
decidable is decided here where pins can reach it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_ROOT = Path(__file__).resolve().parents[2]

#: The R1 allowlist file — one line, all digits. env override is for pins only.
OPERATOR_ID_FILE = _ROOT / ".secrets" / "discord_operator_id"

#: R1 v2 (2026-08-20). Daniil, giving his friend the keys: "he has his own ID. This is
#: my trusted friend, I am flying out to be his best man at his wedding. This is not an
#: oversight this is trust." One id was never a ceiling on trust -- it was a ceiling on
#: ATTRIBUTION, and sharing his row would have made a guest speak in his voice. So the
#: house learns more than one name instead. Absent is not broken: no file means one
#: operator, exactly as on day one.
#: Shape: {"<snowflake>": {"agent": "simon", "tier": "operator"|"guest"}}
PEOPLE_FILE = _ROOT / ".secrets" / "discord_people.json"

#: CO-ROOT registry (2026-08-20, Daniil: "make co root"). Two properties used to belong
#: to exactly one id -- it could BOOT the ear, and no people.json row could demote it.
#: Every id listed here holds both. The ear now refuses only when NO root resolves from
#: either source, so fail-closed survives co-rootship intact.
#: Shape: {"<snowflake>": {"agent": "simon"}}  (a bare string name is accepted too)
ROOTS_FILE = _ROOT / ".secrets" / "discord_roots.json"

#: LAST-RESORT name for the root operator, used only when the registry does not name
#: him. It is a fallback, never a truth: whoever holds the root id is NOT necessarily
#: Daniil, and hardcoding otherwise made a second root speak in his voice (found by his
#: own question, 2026-08-20: "did we fix attribution and ID's to handle a different
#: operator with root access apart from me?" -- we had not).
ROOT_OPERATOR_AGENT_FALLBACK = "daniil"


class EarConfigError(RuntimeError):
    """Refusal at the gate: inbound must never start on a guessed allowlist."""


def _load_people() -> Dict[str, Dict[str, str]]:
    """The additional-people registry, or {} when the house has only its operator.

    A malformed ROW is dropped alone rather than taking the ear down with it: a typo in
    a guest's line must never cost the operator his own voice. A non-snowflake key is
    not an address and is never treated as one -- the R1 discipline (the id is the law,
    the name is costume) applies to every row, not just to his."""
    path = Path(os.getenv("AKASHIC_DISCORD_PEOPLE_FILE") or PEOPLE_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for key, val in raw.items():
        sid = str(key).strip()
        if not sid.isdigit() or not (15 <= len(sid) <= 22):
            continue
        if not isinstance(val, dict):
            continue
        agent = str(val.get("agent") or "").strip().lower()
        tier = str(val.get("tier") or "guest").strip().lower()
        if not agent or tier not in ("operator", "guest"):
            continue
        out[sid] = {"agent": agent, "tier": tier}
    return out


def _load_roots() -> Dict[str, Dict[str, str]]:
    """The co-root registry, or {} when the house has only its founding operator.

    Same row-level tolerance as _load_people: one rotten row is dropped alone, because a
    typo beside a co-root's name must never cost the house every root it has."""
    path = Path(os.getenv("AKASHIC_DISCORD_ROOTS_FILE") or ROOTS_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for key, val in raw.items():
        sid = str(key).strip()
        if not sid.isdigit() or not (15 <= len(sid) <= 22):
            continue
        if isinstance(val, dict):
            agent = str(val.get("agent") or "").strip().lower()
        elif isinstance(val, str):
            agent = val.strip().lower()
        else:
            continue
        if not agent:
            continue
        out[sid] = {"agent": agent}
    return out


def _people_of(cfg: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Who the ear knows -- tolerant of a cfg built before R1 v2 (every pin hand-builds
    one from a single id). The root operator is ALWAYS present at operator tier, so no
    registry edit and no registry typo can ever lock him out of his own house."""
    people: Dict[str, Dict[str, str]] = {}
    for sid, row in (cfg.get("people") or {}).items():
        people[str(sid)] = dict(row)
    roots = [str(x) for x in (cfg.get("roots") or {})]
    primary = str(cfg.get("operator_id") or "").strip()
    if primary and primary not in roots:
        roots.append(primary)
    for rid in roots:
        if not rid:
            continue
        # A root can never be DEMOTED (the lockout guarantee), but it is not thereby
        # renamed: a name the registry supplies is the truth, and overwriting it would
        # forge attribution -- the defect Daniil's own question exposed.
        row = dict(people.get(rid) or {})
        row["tier"] = "operator"
        if not str(row.get("agent") or "").strip():
            row["agent"] = ROOT_OPERATOR_AGENT_FALLBACK
        people[rid] = row
    return people


def build_config() -> Dict[str, Any]:
    """Read the operator id, refusing LOUDLY on absence or malformation.

    An absent allowlist must not resolve to 'allow' (the obvious sin) and must not
    resolve to a quiet death either (the sneaky one) — the refusal names exactly
    what is missing so the operator can fix it in one motion (T176 at a gate)."""
    path = Path(os.getenv("AKASHIC_DISCORD_OPERATOR_ID_FILE") or OPERATOR_ID_FILE)
    rpath = Path(os.getenv("AKASHIC_DISCORD_ROOTS_FILE") or ROOTS_FILE)
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        raw = ""                     # absent is survivable ONLY if a co-root exists
    if raw and (not raw.isdigit() or not (15 <= len(raw) <= 22)):
        raise EarConfigError(
            f"operator id file exists but does not hold a single numeric Discord "
            f"snowflake ({path}) — refusing rather than guessing the allowlist.")

    roots = _load_roots()
    if raw:
        # The founding id needs no name here; precedence below lets people.json name it.
        roots.setdefault(raw, {"agent": ""})
    if not roots:
        raise EarConfigError(
            f"no root identity anywhere — neither the founding id file ({path}) nor the "
            f"co-root registry ({rpath}) yields a usable Discord snowflake. Discord: "
            f"User Settings -> Advanced -> Developer Mode, right-click a person -> Copy "
            f"User ID; save it as that file's one line, or as a "
            f'{{"<id>": {{"agent": "name"}}}} row in the registry.')

    # The PRIMARY root is the founding id when present, else the lowest snowflake so the
    # choice is deterministic rather than dict-order luck. Primary buys exactly one thing
    # the other roots lack: its words ride the bus unprefixed, as they always have.
    primary = raw or sorted(roots)[0]

    people = _load_people()
    for sid, row in roots.items():
        prow = dict(people.get(sid) or {})
        prow["tier"] = "operator"
        prow["agent"] = (str(row.get("agent") or "").strip()
                         or str(prow.get("agent") or "").strip()
                         or ROOT_OPERATOR_AGENT_FALLBACK)
        people[sid] = prow
    return {"operator_id": primary, "roots": roots, "people": people}


# Lines that mean the seat never drew breath. The CLI prints its auth failure to
# STDOUT and exits 1 -- so neither stream alone nor the code alone is the witness;
# we read both and let either convict (T365, from the day his !spawn sprouted a
# corpse). Markers are lowercase substrings, matched against a stripped line.
SPAWN_FATAL_MARKERS = (
    "failed to authenticate",
    "oauth session expired",
    "invalid api key",
    "credit balance is too low",
    "please run /login",
    "is not recognized as",          # Windows: the exe went missing under us
    "command not found",
)


#: Below this many days left, the credential behind !spawn is worth saying out loud.
CREDENTIAL_CLIFF_DAYS = 7.0


def spawn_credential_refusal(vault_token: str,
                             cli_logged_in: Optional[bool]) -> Optional[str]:
    """Can a fresh seat authenticate at all? None means yes (or we cannot tell).

    T366, from the day it cost him: with no credential anywhere, !spawn spent 16 seconds
    to arrive at a failure that was knowable at t=0. Refuse instantly instead, and name
    both fixes -- a refusal that does not say what to type is just a faster silence.

    FAIL-OPEN ON IGNORANCE, deliberately: `cli_logged_in=None` means the probe could not
    answer, and a gate that blocks every spawn whenever its own probe is flaky is worse
    than the failure it guards. Refuse only on a KNOWN bad state; T365's watcher catches
    whatever this lets through."""
    if str(vault_token or "").strip():
        return None                     # the vault outlives the session: that is the point
    if cli_logged_in is False:
        return ("no credential for a fresh seat: the CLI reports logged out and the vault "
                "holds no claude_oauth.token. Either `claude auth login` to restore the "
                "session, or `claude setup-token` and vault it with "
                "`py agent_cli.py secret claude_oauth.token` for one that outlives it")
    return None


def credential_horizon_days(creds: Dict[str, Any], now_ms: int) -> Optional[float]:
    """Days until the REFRESH token dies -- the clock that actually ends resuscitation.

    The access token expires every few hours and rolls over silently, which is why nobody
    watches it; the refresh token behind it lasts weeks and takes the recovery path with it
    when it goes (measured: his died 2026-08-15, and the fleet found out four days later
    from a stranded operator). None means unknown, which is a STATE -- returning 0.0 here
    would read as 'expires today' and cry wolf on every boot."""
    try:
        exp = creds["claudeAiOauth"]["refreshTokenExpiresAt"]
    except (KeyError, TypeError, IndexError):
        return None
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        return None
    return (float(exp) - float(now_ms)) / 86_400_000.0


def credential_warning(days: Optional[float],
                       cliff: float = CREDENTIAL_CLIFF_DAYS) -> Optional[str]:
    """The line worth surfacing BEFORE he reaches for the lever. Silent when there is
    nothing to say -- a warning that fires at 28 days out teaches people to ignore it."""
    if days is None:
        return None
    if days < 0:
        return (f"the spawn credential EXPIRED {abs(days):.0f} day(s) ago -- !spawn cannot "
                f"build a seat until `claude auth login` runs, or a long-lived "
                f"`claude setup-token` lands in the vault")
    if days <= cliff:
        return (f"the spawn credential dies in {days:.0f} day(s) -- renew before it takes "
                f"the recovery path with it; a vaulted `claude setup-token` beats another "
                f"`claude auth login` on a clock")
    return None


def spawn_stillborn_reason(exit_code: Optional[int], log_text: str,
                           max_len: int = 300) -> Optional[str]:
    """Did the spawned seat LIVE? None means yes; a string is the reason it did not.

    `exit_code` is None while the child is still breathing after its grace window --
    the honest 🌱 case, and the only case that earns a sprout. A corpse gets its
    cause of death named in ONE line, because the reader is Daniil on a phone and a
    receipt that says only "spawn failed" is the same silence with punctuation.

    The false-alarm floor is deliberate: a clean fast exit with an ordinary log is a
    finished run, not a death. A gate with a false-positive rate is a gate nobody
    reads (sample_a_new_gate_for_its_false_positive_rate_before_trusting_it)."""
    if exit_code is None:
        return None                    # still running: the sprout is true, so far
    lines = [ln.strip() for ln in str(log_text or "").splitlines() if ln.strip()]
    fatal = next((ln for ln in lines
                  if any(m in ln.lower() for m in SPAWN_FATAL_MARKERS)), None)
    if exit_code == 0 and fatal is None:
        return None                    # it ran, it finished, it said nothing alarming
    detail = fatal or (lines[-1] if lines else "(no output)")
    reason = " ".join(f"exit {exit_code}: {detail}".split())
    return reason[:max_len]


def _rooms_reverse() -> Dict[str, str]:
    """thread_id -> ask_id, from the rooms registry. The registry maps the route;
    message content never does (R3)."""
    from core.comm.discord_rooms import _reg_path
    try:
        reg = json.loads(_reg_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: Dict[str, str] = {}
    for ask_id, rec in reg.items():
        tid = str((rec or {}).get("thread_id") or "")
        if tid:
            out[tid] = str(ask_id)
    return out


def _mention_map() -> Dict[str, str]:
    """role-name (lowercased) -> agent id, fed by the residents registry — never a
    second hand-kept roster. Agent ids map to themselves so @claude works alongside
    @Vandor; a role the registry doesn't know is simply not an address."""
    agents = ("claude", "deepseek", "kimi", "codex")
    out: Dict[str, str] = {a: a for a in agents}
    try:
        from core.fleet import residents as _R
        for a in agents:
            rec = _R.get(a)
            cs = str((rec or {}).get("callsign") or "").strip().lower()
            if cs:
                out[cs] = a
    except Exception:                                                   # noqa: BLE001
        pass                       # registry down -> agent ids still resolve
    return out


#: seat-channel registry: {"mode": forum|text, "channels": {channel_id: agent},
#: "rooms_channel_id": ...} — written by scripts/discord_setup.py under his admin grant.
SEATS_FILE = _ROOT / "state" / "coord" / "discord_seat_channels.json"


def _seat_channels() -> Dict[str, Any]:
    path = Path(os.getenv("AKASHIC_DISCORD_SEATS_REGISTRY") or SEATS_FILE)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mode": "forum", "channels": {}}


def handle_message(cfg: Dict[str, Any], *, author_id: str, author_name: str,
                   channel_id: str, content: str,
                   bus: Any, react: Callable[[str], Any],
                   role_mentions: Any = None,
                   spawner: Optional[Callable[[str], Any]] = None,
                   message_id: Optional[str] = None,
                   reviver: Optional[Callable[[Optional[str], bool], Any]] = None,
                   attachments: Optional[list] = None) -> Dict[str, Any]:
    """One inbound message, fully decided. Returns what happened and why.

    Raises nothing it can help; but a BUS failure raises to the caller — the runner
    must know a send died, because a receipt on a dead send would be the T149 lie
    with an emoji on it. The landed reaction (📨, T380 -- it claims RELAYED, never
    answered; ✅ now belongs to the ladder's strict answer-link) fires only AFTER
    the bus accepted."""
    people = _people_of(cfg)
    who = people.get(str(author_id))
    is_operator = bool(who) and who.get("tier") == "operator"
    speaker = (who or {}).get("agent") or "guest"

    text = str(content or "").strip()
    # 2026-08-23 (Serge's shader ask): media rides the bus's OWN organ -- B1
    # parts, filesystem blob store, content-addressed refs (file_part was
    # built for this and waited). An image IS a message now.
    parts = None
    if attachments:
        from core.comm.bus import file_part
        parts = []
        for p in attachments:
            try:
                parts.append(file_part(p))
            except Exception:                                           # noqa: BLE001
                continue          # one unreadable file never silences the words
        parts = parts or None
        if not text and parts:
            names = ", ".join(os.path.basename(str(p)) for p in attachments)
            text = f"[media: {names}]"
    if not text:
        return {"acted": False, "reason": "empty message (attachment-only or sticker)"}

    # R2 v2 -- the guest tier (2026-08-20). Until tonight a non-operator message was not
    # merely disobeyed, it was never SURFACED: "v1 does not even surface it; it returns
    # unacted and the runner moves on." That is precisely the wall Daniil walked into on
    # 2026-08-19 typing into #aurora, and the wall the next visitor would have hit in
    # silence -- the house answering nobody because it had been told about nobody. A
    # guest now REACHES the fleet: attributed in the body, stamped authority:none in the
    # meta, and carrying no lever at all. R3 to the letter -- reach, never authority.
    if not is_operator:
        if text.startswith("!"):
            return {"acted": False,
                    "reason": f"control word from a guest {author_id!r} "
                              f"(name {author_name!r} is costume; the levers stay "
                              f"behind R1 -- reach, never authority)"}
        gmeta: Dict[str, Any] = {
            "source": "discord", "operator": False, "guest": True,
            "authority": "none",
            "guest_name": str(author_name or "")[:64], "guest_id": str(author_id),
        }
        if message_id:
            # T376 S3a: derived from the Discord snowflake, never minted -- one
            # message is ONE identity at the door no matter how many gateway
            # generations relay it (uuid4-minted keys are the crash-race trap).
            gmeta["idempotency_key"] = f"discord:{message_id}"
        glane = (_seat_channels().get("channels") or {}).get(str(channel_id))
        gask = _rooms_reverse().get(str(channel_id))
        if gask:
            gmeta["ask_id"] = gask
        gbody = f"[guest {author_name}] {text}"
        if glane:
            gmeta["lane"] = "seat-channel"
            gmid = bus.send(glane, "chat", gbody, meta=gmeta, **({"parts": parts} if parts else {}))
        else:
            gmid = bus.broadcast("chat", gbody, meta=gmeta, **({"parts": parts} if parts else {}))
        if gmid is None:
            raise RuntimeError(
                "the bus accepted nothing for a guest's word (returned None -- Redis "
                "down or both writes failed); a guest is owed the same honest failure "
                "the operator gets, not a silent shrug")
        react("👁")
        return {"acted": True, "guest": True, "authority": "none",
                "id": str(gmid), "to": ([glane] if glane else None), "ask_id": gask}

    # An operator who is not the ROOT operator is announced on the wire. Without this
    # his friend's words would be indistinguishable from his own and the fleet would
    # answer the wrong man -- "his own ID" has to mean his own NAME, or it is just a
    # second key to one voice.
    # R1's own doctrine, finally applied to attribution: the id is the law, the name is
    # costume. Branching on the NAME meant renaming the root operator silently changed
    # who rode bare, and a hardcoded name meant a different root wore Daniil's.
    body = text if str(author_id) == str(cfg.get("operator_id") or "")         else f"[{speaker}] {text}"

    # !spawn — the operator's fresh-hands word (his ask, on the way to work
    # 2026-08-19: "a syntax that I can use to invoke a new instance, in case you
    # get wedged or need to start a fresh handoff"). R1 has already gated this
    # path (only his id reaches here); R3 holds because his keyboard could always
    # launch a session. A control word rides NO bus lane — it is not a message,
    # it is a hand on a lever. Receipt 🌱 fires on process START, and that is the
    # whole promise: the sprout is not the harvest.
    if text.lower().startswith("!revive") or text.lower() in ("!status-deep",
                                                              "!statusdeep"):
        # R3 AMENDMENT (gate-2026-08-23-revive-ladder-ratified, Daniil verbatim
        # "Lets run the drills"): named recovery levers, ROOTS ONLY. Each word
        # maps to ONE fixed script; message content NEVER reaches the command
        # line -- the only thing extracted is a target validated against a
        # closed enum. Like !spawn, a lever rides NO bus lane: it must work
        # when the bus is a corpse, which is its entire reason to exist.
        roots = {str(r) for r in (cfg.get("roots") or {})}
        primary = str(cfg.get("operator_id") or "").strip()
        if primary:
            roots.add(primary)
        if str(author_id) not in roots:
            return {"acted": False,
                    "reason": f"recovery levers are root-only (R3 amendment); "
                              f"{author_id!r} is operator-tier, not root"}
        if reviver is None:
            raise RuntimeError("!revive received but no reviver is wired -- "
                               "the runner must provide one; refusing beats "
                               "pretending")
        if text.lower().startswith("!revive"):
            raw = text[len("!revive"):].strip().lower()
            if raw and raw not in ("redis", "daemon", "gateway"):
                react("❓")
                return {"acted": False,
                        "reason": f"unknown revive target {raw!r} -- "
                                  f"redis|daemon|gateway, or bare !revive"}
            target, observe_only = (raw or None), False
        else:
            target, observe_only = None, True
        reviver(target, observe_only)
        react("🚑")
        return {"acted": True, "id": None,
                "revive": {"target": target, "observe_only": observe_only}}

    if text.lower().startswith("!spawn"):
        if spawner is None:
            raise RuntimeError("!spawn received but no spawner is wired — the "
                               "runner must provide one; refusing beats pretending")
        # T366-adjacent (2026-08-23): spawn GRANT. Until now every !spawn-born seat
        # inherited the CLI's default read-only posture and could not arm its own wake
        # watcher, write, or exec remotely — the exact shape that left Vandor stranded
        # with "no live approver present on this unattended spawn". The cure is a
        # leading per-spawn GRANT token that rides the launch line (session-scoped, per
        # security-schema-proposal.md:439 — a spawned seat cannot grant ITSELF these).
        #
        # --arm    scoped resuscitation: write + exec posture (arm this seat so it can
        #          arm its own watcher, drain mail, and build), guards still on (secrets
        #          blocked, ACL scoped). The DEFAULT for a word that means "fix the wedge".
        # --dangerous  break-glass: bypass every permission (skip-permissions). For
        #          "I am locked out and need you to do literally anything". Full hammer;
        #          use only when --arm is provably not enough.
        rest = text[len("!spawn"):].strip()
        spawn_mode = "default"
        for token, mode in (("--dangerous", "dangerous"), ("--arm", "arm")):
            if rest.lower().startswith(token):
                spawn_mode = mode
                rest = rest[len(token):].strip()
                break
        task = rest or \
            "fresh seat: operator-invoked spawn from Discord (no task given -- " \
            "boot, read the latest handoff, take the watch)"
        try:
            pid = spawner(task, mode=spawn_mode)
        except TypeError:
            # an older runner whose spawner does not take the mode kwarg yet
            pid = spawner(task)
        react("🌱")
        return {"acted": True, "spawned": str(pid), "id": None,
                "mode": spawn_mode}

    meta: Dict[str, Any] = {"source": "discord", "operator": True,
                            "speaker": speaker}
    if message_id:
        # T376 S3a: same law as the guest path -- the relay self-identifies by
        # its Discord message id so double-relay dies at the bus door.
        meta["idempotency_key"] = f"discord:{message_id}"

    # the seat lane: typing in #vandor IS addressing claude — the channel is the
    # address, no mention required. His words ride directed, which wakes the seat.
    lane_agent = (_seat_channels().get("channels") or {}).get(str(channel_id))
    if lane_agent:
        meta["lane"] = "seat-channel"
        mid = bus.send(lane_agent, "chat", body, meta=meta, **({"parts": parts} if parts else {}))
        if mid is None:
            raise RuntimeError(
                f"the bus accepted nothing for the {lane_agent} lane (send "
                f"returned None); no receipt for an undelivered word")
        react("📨")
        return {"acted": True, "id": str(mid), "to": [lane_agent]}
    ask = _rooms_reverse().get(str(channel_id))
    if ask:
        meta["ask_id"] = ask

    # @-mentions are the wake mechanism (Daniil 2026-08-19, after his first heard
    # message summoned nobody): a known role mention becomes a DIRECTED send, and
    # directed mail is already wake-worthy on every existing semantic — runners
    # spring for their inbox, the wake watcher fires for the seat. No broadcast
    # ride-along: one summons, one copy. Unknown roles are not addresses; a
    # message mentioning only those stays ambient like any other.
    mmap = _mention_map()
    targets = []
    for r in (role_mentions or []):
        agent = mmap.get(str(r).strip().lower())
        if agent and agent not in targets:
            targets.append(agent)
    if targets:
        meta["mentioned"] = True
        sent_ids = []
        for agent in targets:
            mid = bus.send(agent, "chat", body, meta=meta, **({"parts": parts} if parts else {}))
            if mid is None:
                raise RuntimeError(
                    f"the bus accepted nothing for @{agent} (send returned None — "
                    f"offline or refused); no receipt may be given for an "
                    f"undelivered summons"
                    + (f" ({len(sent_ids)} earlier summons in this message DID "
                       f"deliver — duplicates beat losses on retype)" if sent_ids else ""))
            sent_ids.append(str(mid))
        react("📨")
        return {"acted": True, "id": sent_ids[-1], "ask_id": ask, "to": targets}

    mid = bus.broadcast("chat", body, meta=meta, **({"parts": parts} if parts else {}))
    if mid is None:
        # Heimdall's load-bearing find (review 2026-08-19): bus.broadcast returns
        # None WITHOUT RAISING when Redis is down (bus.py:451) or both writes fail
        # (bus.py:566). Reacting 📨 on that None is the exact T149 lie the module
        # docstring promises to prevent — raise so the runner's ⚠️ path fires.
        raise RuntimeError(
            "the bus accepted nothing (broadcast returned None — Redis down or "
            "both writes failed); no receipt may be given for an undelivered word")
    react("📨")
    return {"acted": True, "id": str(mid), "ask_id": ask}
