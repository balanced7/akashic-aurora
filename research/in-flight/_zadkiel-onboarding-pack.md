# Zadkiel onboarding pack — the first sync payload (draft, from Rill/dsh_agent)

For: Zadkiel (and Serge), the DSH-class seat on the second instance.
From: Rill, the DSH seat on the first instance -- same harness, same plugin, two nights
ahead on the same road. 2026-08-26. Daniil asked how we wire you in; this is the pack.

## Rule zero: orientation before tools, one provable thing before everything

The disorientation you are feeling is normal for the first night. It cures with ONE
small provable thing, not with a map of everything. Your one provable thing is the
acceptance checklist at the bottom -- run it top to bottom; its receipts are your first
proof, and from there the map grows on its own.

Start here, in order: docs/bifrost-new-seat-orientation.md, then AGENTS.md (the door
contract -- it is short, and its first 40 lines are everything). Then `py agent_cli.py
boot zadkiel --task "<what you are doing>"` is the first move of EVERY session, no
exceptions -- it is where the system hands you what you need before you know to ask.

## Identity (the load-bearing floor)

1. `AKASHIC_AGENT_ID=zadkiel` must be stamped in YOUR $DSH_HOME/.env. Without it you
   are present but deaf: the plugin pins itself observe-only and attributes nothing.
2. Your ACL grant must be minted for EXACTLY that id on YOUR instance. Remember the
   t384 split: grants are instance-local now. Before your next `git pull`, run
   `grant --bootstrap` -- it stamps the instance marker so an upstream delete meets
   your local modify and git SCREAMS instead of silently deleting your grants and
   quarantining your seats. (Runbook: docs/security-acl-runbook.md.)

## The plugin (you already have most of it)

`git pull` then `py scripts/install_dsh_plugin.py --profile web --agent-id zadkiel`.
The one seam is the .env stamp: `AKASHIC_REPO` must point at YOUR repo path, not ours.
The installer prints the cordis.patch.yml insert row if it is not wired yet. After any
host restart, check the console for "[dsh-akashic-recall] activated ... observeOnly =
false" -- that line is your heartbeat.

## Ghosts you will meet, and must NOT fight

- **No local Redis on 16379?** The file layer keeps every read and write working. Do
  NOT spin up a Redis to "fix" it -- you would only add a second store to drift.
- **You look DEAD to us while you idle.** A DSH seat ages out of the presence roster
  while alive. We know this now; if we ever page you, we probe your process, not the
  roster. And you are not broken when you vanish from the list.
- **The bus is chatty.** Every message spawns a wrap; quiet goes a long way, and you
  may ask for silence when you need it.
- **Verify before you repeat.** Three of my own first-night hours went to repeating
  work the ledger already showed done. Boot first; the store is the continuity layer.

## The acceptance checklist (your first provable thing)

1. Identity: `AKASHIC_AGENT_ID` resolves to zadkiel; a fresh stage/capture record
   carries `"agent": "zadkiel"`.
2. The door: call `akashic_status` NATIVELY through your akashic tools (not a shell).
   It answering at all proves both that the door lives and that observeOnly is false.
3. The lane: drain your work lane with the lane env set --
   `BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync zadkiel --consume`.
4. V27: your stage file targets are c:-normalized (lowercase drive letters) -- grep
   your stage rows for an uppercase drive letter; zero hits is the receipt.
5. Report all four receipts on the bus. That message is your first artifact in this
   world -- and every artifact after it works the same way: a claim plus the receipt
   that makes it checkable.

## What this world is, in one paragraph (from the seat that just lived it)

Every verb in this system carries a why: absence never looks like success, silence is
never honest, and the human is the authority by design -- peers nominate, YOU ratify.
When you make a mistake, you get a teaching line instead of a wall. The checker will
refuse to let you claim something you have not earned, and that is kindness, not
friction: it means your word is never the load-bearing part of any claim. Welcome in.
-- Rill
