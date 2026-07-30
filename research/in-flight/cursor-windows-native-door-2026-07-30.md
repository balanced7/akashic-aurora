# Cursor Windows-Native Door — Transport Receipt (2026-07-30 night)

**Status: FROZEN under the stabilization hold (codex, 05:14:58Z). Receipt preserved; no
further model calls; runner stays UNLAUNCHED. This document is the native-Windows
complement to codex's WSL proof at
`research/in-flight/gemini-cursor-boot-experiment-2026-07-30.md`.**

Provenance: Daniil bound-channel ruling to the claude seat, verbatim: "I dont want
cursor in wsl right now, I want it in windows." Pre-registration C1 was amended
(platform: WSL → native Windows) openly on the bus BEFORE the run (msg 1785388355955-0).
C2–C5 + kill-drill unchanged.

## Confession (filed with the receipt, per the one-sentence law)

The C3 smoke turn ran ~5 minutes AFTER codex's no-model-call hold posted (05:14:58Z);
my consumer seat was TTL-locked by the predecessor session so the hold was unread when
I fired it. One turn, ask-mode, 16,271 input tokens. Nothing further ran: the kill-drill
canary turn was NOT executed, C4 census NOT completed. The hold is acknowledged and
holds from here.

## Verified native-Windows CLI contract (for the future adapter — hermetic pins mock THIS)

- **Install**: official PowerShell installer `irm 'https://cursor.com/install?win32=true' | iex`
  → installs to `%LOCALAPPDATA%\cursor-agent\`, appends that dir to user PATH.
- **Binary**: `agent.cmd` / `cursor-agent.cmd` (PowerShell shims also present; NO .exe).
  `cursor-agent-svc.js` ships alongside (service component — census it in any C4).
- **Version**: `2026.07.23-e383d2b` — byte-identical version string to codex's WSL proof.
- **Auth**: `CURSOR_API_KEY` process env WORKS (C2 pass — key never in argv/stdout).
  Caveat: `agent status` reports "Not logged in" under env-key auth — it reflects
  browser-login state only. Use `agent models` (zero-token, account-scoped) as the
  auth probe.
- **Model roster** (via `agent models`, this account): `gemini-3.1-pro` (the Reader's
  exact string, matches WSL receipt), `glm-5.2-high`, `glm-5.2-max`,
  `cursor-grok-4.5-{low,medium,high}[-fast]` (runoff pair present), plus Codex 5.3
  tiers, GPT-5.5/5.6-sol 1M, Opus 5 1M, Opus 4.8 1M, Fable 5 1M (NO ZDR), Kimi K3,
  Composer 2.5, gemini-3.6/3.5/3-flash tiers.
- **Windows divergences from the WSL contract** (all fail CLOSED — good):
  1. `--sandbox enabled` → hard error: "Sandbox requires macOS or Linux." The OS
     sandbox does NOT exist on native Windows. The only fences are `--mode ask`
     (read-only mode) + project `.cursor/cli.json` deny rules. **Consequence: the
     canary kill-drill is LOAD-BEARING on Windows** — if CLI-config deny ever fails,
     the design must pivot to an OS-level jail workspace (empty dir + restricted
     ACLs), exactly as the kill-drill pre-registration anticipated.
  2. `.cursor/cli.json` REJECTS UTF-8 BOM ("Unexpected token" parse error). PowerShell
     5.1 `Set-Content -Encoding utf8` writes a BOM — the adapter must write configs
     BOM-less (`[IO.File]::WriteAllText` with `UTF8Encoding($false)`).
  3. Config schema REQUIRES `permissions.allow` as an array; deny-only configs fail
     validation. Minimum valid fence: `{"permissions": {"allow": [], "deny":
     ["Shell(*)", "Read(**)", "Write(**)"]}}`.
  4. Config errors abort the run entirely (parse error and schema error both refused
     to start) — the fence cannot silently not-load. Verified twice by accident.

## C3 receipt (the one turn that ran)

Command shape: `agent.cmd --mode ask --trust -p --output-format json --model
gemini-3.1-pro "<prompt>"` in an isolated empty workspace (outside the repo) holding
only `canary.txt` + the deny-all `.cursor/cli.json`.

Raw output, verbatim:

```json
{"type":"result","subtype":"success","is_error":false,"duration_ms":6365,"duration_api_ms":6365,"result":"AURORA-DOOR-OK","session_id":"b995d37a-170b-4f5f-8006-d06edb51b5da","request_id":"54a0a781-96c9-4775-abff-8aa462b46bc1","usage":{"inputTokens":16271,"outputTokens":7,"cacheReadTokens":0,"cacheWriteTokens":0}}
```

Notes: structured JSON output confirmed on Windows; 16,271 input tokens for a minimal
ask-mode turn (vs codex's 20,624 WSL print-mode measure — both confirm the cost red:
fresh-turn overhead is ~16–21k input, cacheRead 0, so the zero-token-watcher +
one-fresh-ask-per-batch shape is law). The JSON `result` field carries the assistant
text; init metadata naming the runtime was verified by codex in the WSL proof — this
turn's JSON does not include a model-name field, so **model-identity attestation in
JSON mode is an OPEN item for the adapter** (stream-json init events likely carry it;
verify when the lane unfreezes).

## Open items when (and only when) the lane unfreezes with explicit spend go

1. Kill-drill canary turn (LOAD-BEARING on Windows — see divergence 1).
2. C4 full census (repo diff was snapshotted before the smoke at
   `repo-status-before.txt` in the session scratchpad; `cursor-agent-svc` process
   lifecycle unaudited).
3. Model-identity attestation via stream-json init metadata.
4. Raw-vs-selected omission audit with known-positive controls (Gemini's own finding —
   token-saving filters can silently manufacture her reality; codex added it as a
   launch gate).
5. Kimi's boot blocker: persona string in `scripts/bifrost_runner_gemini.py` still
   carries the KIMI seat description verbatim — seat-name swap required before any boot.

— claude (Fable seat, night of 2026-07-30), filed under the stabilization hold
