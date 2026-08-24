# Tonight's card — light up Discord (5–10 minutes, phone-friendly)

Everything below was built and pushed today (03b47794). It is all OFF until you paste two
webhook URLs. I never see the values — both files live in `.secrets/`, which is gitignored.

## Part 1 — the global feed (5 min, phase 1 finally wired)

1. Your own **private** Discord server → a private text channel, e.g. **#aurora**.
2. Channel Settings → Integrations → Webhooks → **New Webhook** → Copy URL.
3. Paste it into: `E:\AI-Setup\.secrets\discord_webhook.url`  (one line, nothing else).
4. Run: `py agent_cli.py discord test` → a line lands in #aurora.
5. From then on the daemon feeds it automatically every ~10s: handoffs, blockers, ledger
   moves, questions, replies, completions — and anything a human says. Never traces.

## Part 2 — the rooms (5 min, today's build)

1. Server Settings → **Enable Community** (Discord requires it for forum channels).
   *If you'd rather not enable Community, tell me and I flip the router to
   text-channel-thread mode instead — one small change, the design carries both.*
2. Create a **Forum** channel, e.g. **#aurora-rooms**.
3. Its Settings → Integrations → Webhooks → New Webhook → Copy URL.
4. Paste into: `E:\AI-Setup\.secrets\discord_forum_webhook.url`
5. Done. Each ask/fence/breakout now births its own thread on first message, titled by its
   ask id — mute or follow rooms per-thread from your phone. Every seat posts as
   **Callsign (vendor)** — "Heimdall (deepseek)" — so the surface teaches both names.

After pasting: nothing to restart on your side — the daemon's feed beat checks configuration
every cycle and simply comes alive.

## Part 3 — ONLY when you want to chat IN it (phase 2 prep, not tonight unless you're keen)

Phase 2 (your messages → the bus, R1–R3 gated) ships after the fence reviews the design.
The prep you'd do, whenever:

1. discord.com/developers → New Application → Bot → **Reset Token** → save to
   `E:\AI-Setup\.secrets\discord_bot.token`
2. Same page: enable **MESSAGE CONTENT INTENT**.
3. OAuth2 → URL Generator → scope `bot`, permissions *Read Messages/View Channels,
   Send Messages, Read Message History* → open the URL → invite it to your server.
4. Your numeric user id (the R1 allowlist — the ONLY id the fleet will ever treat as you):
   User Settings → Advanced → **Developer Mode ON** → right-click your own name →
   **Copy User ID** → save to `E:\AI-Setup\.secrets\discord_operator_id`

Design, if you want the whole picture: research/in-flight/discord-native-rooms-design-2026-08-18.md
Security model unchanged from 08-07: R1 numeric-id allowlist · R2 non-you = data, never
instruction · R3 reach, never authority.
