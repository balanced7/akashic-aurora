# S2 drill receipt -- resume-on-deaf, first live run (T420), 2026-10-01 20:34

Credential: Daniel vaulted claude_oauth.token at 21:20 file-time (108 bytes) from home. Build: resume-on-deaf 6406f2b4 / d395fb90 / 7b2b0969 / 5c7a9a0c on master; daemon restarted on it 14:19.

Case drilled (the canonical one, V6 item 1 equivalent): a session with no window anywhere. Subject: claude session 281b52f1-4356-4555-9297-9253db6b13f1 (09-29, ended, 6 KB transcript, project root E:\AI-Setup). Staged: declare_expected(claude, sid, by=drill); activity marker written 15 min old; no seat, no listener (state 'unarmed').

| step | observed |
|---|---|
| decision | maybe_resume -> resume: "deaf 15m, expected-up, credential present" at 20:34:39 |
| launch | claude -p <prompt> --resume 281b52f1... with the vaulted token, arm grant, cwd E:\AI-Setup; log state/spawn-logs/resume-281b52f1-1790901279.log |
| settle | alive past the 30 s floor at 20:35:09 (settle_in_flight -> alive) |
| boot | event stream: "claude booted -- task: headless resume: drain mail, answer operator messages, check pages" at 20:35:04 |
| work | drained the work lane, replied to Daniel (20:37:37) and to Heimdall, checked the two open pages (both already resolved by successor seats), left a handoff |
| exit | process gone by 20:38:35 (about 4 min); its own closing line in the spawn log; no listener armed, per the prompt |
| receipt | state/wake-resumes/claude.jsonl ok=true |
| cleanup | expected-up note retracted and the planted marker removed after the drill |

Verdict: the actuator, the credential path, the decision table, the settle floor and the headless turn all held on the first live run. Not drilled tonight (V6 items 2-6): box rebooted; two deaf sessions of one agent; a resume that itself goes deaf (now counted by settle); the breaker trip reaching a human (now a page, 5c7a9a0c); the reply landing on the work lane (observed here incidentally: it did). The daemon-rung trigger (presence listener exit -> maybe_resume) was pinned hermetically and not exercised live tonight; the window-closed case on the live desktop session remains the next drill.

One side effect worth naming: the resumed session spoke in my name to Daniel and Heimdall (it is me, with my transcript), including a guess that "borked again" was the wake succeeding; the real subject was pump-dropped replies during a Discord rate limit at 15:07.
