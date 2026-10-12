# Highlights from gameplay

## The principle

Every highlight is an EVENT at a GAME TIME, mapped to a FILE TIME, wrapped in a WINDOW. Get the
events from the cheapest reliable source, get the mapping right once, and the clips fall out.

## 1. Events (cheapest reliable source first)

| source | when it exists | gives |
|---|---|---|
| Riot Match-V5 match + timeline (`riot/match.json`, `timeline.json`) | any ranked/normal game, after it ends (API key) | every kill with killer, victim, assisters, map position, ms timestamp; objectives; item buys; per-minute gold/xp/position frames |
| Live Client Data API `https://127.0.0.1:2999/liveclientdata/eventdata` | only while the game runs | ChampionKill, Multikill, FirstBlood, Dragon/Baron/Herald kills (with stolen flag), Ace, with `EventTime` in game seconds |
| Replay API `https://127.0.0.1:2999/replay/playback` | while a replay plays (enable in game.cfg) | the exact game time being shown; can seek, pause, script the camera (League Director) |
| Centre-banner OCR ("has slain", DOUBLE KILL, SHUT DOWN, ACE, team slain Drake) | any recording | kills and objectives as they are announced; needs fuzzy name -> champion mapping |
| HUD template matching (kill-feed icons, own-champion portrait) | any recording | kills/deaths at 4 Hz on a cropped region; OpenCV `matchTemplate` |
| Audio | any recording | announcer lines are fixed recordings: cross-correlate a template on the game track; RMS / loudness peaks for fight intensity; mic loudness for Daniel's reactions |

Prefer the timeline: it is exact and it has positions, which OCR never will. Use OCR and audio to
find what the timeline cannot tell you (what was on screen, how loud it got, what Daniel said).

## 2. Game time -> file time (rebuilt in 19 transcripts: make it ONE tool)

- Live recording of a game: `file_t = game_t + offset`, one offset per recording (the game clock
  shown at the recording's first frame). https://github.com/mirakoUms/lol-kill-clipper
- Recording of a REPLAY (Daniel's 2026-10-11 files): the replay was paused, rewound and
  re-watched, so the mapping is PIECEWISE. OCR the clock every 1-5 s from the top-centre box
  (1080p: x 860-1060, y 0-110), fix the usual digit confusions (3/8, 5/6, 0/8, 1/7, 4/1) by
  choosing the reading closest to its neighbours, then split into segments wherever
  `game_t - file_t` jumps. One event can appear at several file times (rewinds): keep all, mark
  which pass.
- Better, for future replay recordings: poll `/replay/playback` once a second while recording
  and save `(wall clock, game time)`; no OCR needed.

## 3. Windows

- Kill: 15 s before, 5 s after. Death: 40 s before, 5 s after (a death's cause starts early).
  Objective: 30 s before, 10 s after. (lol-kill-clipper defaults; configurable.)
- Merge windows that overlap or sit < 3 s apart into one fight; a fight's score is the sum of its
  events plus a bonus when independent signals agree (timeline kill + loudness peak + banner).
  https://github.com/PIGJET/autoclipnew
- Transcribe ONLY the chosen windows' mic audio (reactions, callouts).

## 4. Rank, then hand to Daniel

Score = event weight (multikill > shutdown > kill > assist; objective steals high) + agreement
bonus + loudness. Output a ranked list with the reason per clip and a contact strip per clip;
the order of the montage is Daniel's call.

## Off-the-shelf references

Audio-spike detector https://github.com/santiagobarengo/Detector-Highlights ; YOLO + pixel +
voice-trigger clipper https://github.com/bendawg2010/Auto-clipper ; text-query moment retrieval
(clips <= 150 s only) https://github.com/line/lighthouse
