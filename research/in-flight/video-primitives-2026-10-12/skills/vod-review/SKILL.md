---
name: vod-review
description: Use when Daniel asks to analyze, review or coach his gameplay - "analyze my gameplay", "VOD review", "what did I do well", "what could I have done better", "why did I die", "how could that fight have gone better", "was that a good play", "review my game", "coach me" - for League of Legends recordings, replays or a match ID. Produces timestamped moment cards (good plays, deaths, fights) with evidence, and one or two rules to test in the next three games.
---

# VOD review

**Iron Law: judge decisions by what was knowable, never by how it turned out.** At every moment
ask "what could he see and know right then", rewind to before the decision, and keep hindsight
out of the verdict. Every claim cites a frame or a timeline event; anything inferred says so.

DRAFT 2026-10-12. Uses the `video-work` skill for all media handling (events, clock map, frames).

## Inputs

- the recording(s) (`E:/Video Output E/...`), live or replay;
- the Riot match + timeline (match ID; `riot/match.json`, `timeline.json`): exact kills, positions,
  items, gold and XP per minute;
- context: rank (Silver I), champion, role, the matchup. Coach at the level of the rank: deaths,
  waves, recalls, objectives and trades come before frame-perfect mechanics.

## Before judging any frame: whose vision is on screen?

Daniel's 2026-10-11 recordings are of the replay viewer with **Fog of War: All** (visible in the
bottom-left panel). That shows enemies he could NOT see. Never cite an enemy as "information he
had" from such a frame. Use his own minimap only if the fog is set to his team; otherwise reason
from the timeline (positions per minute, ward events) and say it is inferred. For future review
recordings, set the replay's Fog of War to his team first.

**The facecam covers most of the minimap** in those recordings (facecam box x 1320-1815,
y 738-1015 at 1080p; the minimap spans about x 1660-1920, y 820-1080). The coaching staple
"read the minimap 20 s before the death" is mostly impossible from these files: use the Riot
timeline's per-minute positions plus the kill positions instead, and label it. Suggest to Daniel
moving the facecam in OBS to the top-left or bottom-left for League (his call).

## Procedure (copy this checklist)

```
- [ ] 1. Events + clock map: `py -m arsenal.media clockmap <recording>` then
        `py -m arsenal.media events <recording> --match <id> --player <name>`: every kill, death,
        objective with game time AND every file time that shows it (replay passes included), plus
        merged fight windows. Look with `media filmstrip <recording> <t0> <t1>`, one image per moment.
- [ ] 2. Deaths pass: each death, from 40 s before to 5 s after
- [ ] 3. Fights pass: each merged fight window (2+ champions, 15 s before first event)
- [ ] 4. Skill pass: what was genuinely good (mechanics, trades, reads, matchup knowledge)
- [ ] 5. Macro pass: recalls, objective setup (where was he 30 s before each spawn), passive minutes, CS
- [ ] 6. Verdict: 1-2 rules for the next 3 games, one practice goal, all cards linked
```

**For every moment, record four things** (one card each):
1. **Information** - what he could see or know (minimap 20 s earlier, enemy missing, cooldowns
   visible, wave position, items, levels).
2. **Options** - what he could have done (2-3 real alternatives).
3. **Priority** - what mattered most right then (survive, wave, objective, tempo).
4. **Cue** - the thing to notice next time that would trigger the better option.

Death checklist: where was the wave; what did the minimap show 20 s before; was the killer
visible or missing; were summoners / ultimate up (his and theirs); was there vision; was the
recall overdue (gold unspent); was an objective about to spawn.

Fight checklist: who started it and why; numbers (3v4?); his position relative to the front line;
target selection; did he use the key cooldowns; when the fight was lost, the first irreversible
moment; one alternative that would likely have changed it.

Skill pass: name the specific skill and show it (a caught-axe chain, a trade timed on an enemy
cooldown, a flash that dodged a skillshot, a correct back-off when the jungler was shown). Say
plainly when something was excellent; praise needs the same evidence as criticism.

## Output

A moment card per item: game time and file time (clickable `&t=` if uploaded), a 6-frame strip,
what happened, the four fields, verdict (good / fine / costly), confidence (seen on screen vs
inferred from the timeline). Then the verdict: the 1-2 rules, the practice goal ("ward river
before pushing past half-lane" not "be more careful"), and a re-check after three games.

## Sources of the method

Three passes, one question per pass, deaths first, rewind 20 s and read the minimap:
https://www.lolsensei.com/en/blog/vod-review-self-analysis , https://riftrec.app/guides/how-to-review-a-league-vod/ ,
https://levellegendary.com/lol-vod-review/
