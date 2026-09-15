# Clickable practice excerpts

Start the local player once:

```powershell
py -m arsenal.replay serve
```

Then make a link to a passage:

```powershell
py -m arsenal.pianocue replay-link latest 3:43 --seconds 12 --label "Listen to the bass"
```

The result is a Markdown link suitable for a chat reply. Use `--json` for the URL,
resolved session, start/end and speed. `latest` becomes an explicit session ID when
the link is made. The verb reads the requested passage to check it exists, but sends
no cue and plays no sound. The player has Play/Pause, Start over, seeking, speed and
loop controls. Changing speed preserves pitch.

The chord strip follows the passage. Hover a chord or the note roll to see its
name, notes and highlighted keyboard; click to hear that voicing together.
Clicking pauses the passage without moving its playhead. Press Play passage to
continue. Keyboard focus previews a chord; Enter/Space auditions it.

Chord windows reuse the practice segmenter over the replay's sounding durations,
including notes ringing under sustain and notes carried into the excerpt. This
groups a developing arpeggio instead of naming each key press separately. The
browser names the resulting voicings with the piano's own pure THEORY block.
These are harmony readings, so a moving melody can contribute extra colour notes.
Auditions use representative pitches and velocities from the window, without
adding a missing third or bass octave. Saved answers use their frozen replay.

This uses `pianocue.build_replay_cue` and the existing `createClaudeVoice` /
`createCuePlayer`. MIDI onsets, velocities and pedal-aware sound durations are
reconstructed with the keys synth; it is not the recorded instrument audio. Notes
already ringing at a cut or seek are re-attacked. The existing engine groups carried
notes with the same end time and averages their velocities. Avoid cutting into a
held chord when that distinction matters.

The companion listens only on `127.0.0.1:8796`. It serves the player assets and a
bounded excerpt endpoint. It can also save explicitly marked musical answers in
its private conversation directory; it never writes to a performance log. It has
no MIDI output, bus listener, practice recorder or jam transport. It works alongside an older arsenal server
without restarting the piano. A link works on this machine while the companion is
running; posting it in Discord does not upload audio or make it remotely accessible.
Private session data remains in `state/arsenal/performance`; do not commit real
session links or excerpts. `--root` on the server and the link verb must match when
using an alternate session store. `--port` on both commands changes the default.

To immediately replay on the existing piano page, the original verb remains:

```powershell
py -m arsenal.pianocue replay latest 3:43 --seconds 12
```

That command broadcasts a cue; use `replay-link` when the listener should choose
when to start. Closing or hiding the standalone player pauses its sound.

## Conversation cards and played answers

The piano's **Conversation** button opens a scrollable drawer. On the first load
after installing it, refresh the piano page, or open `/piano?conversation=1`.
The separate card view is `http://127.0.0.1:8796/web/conversation.html`.

Each question has source excerpts with the same replay controls. **Play an answer**
pauses the reference audio and marks this piano tab's practice clock. Play a phrase,
optionally type a note, then **Save my answer**. Answers are at most 60 seconds;
reaching that boundary saves the first minute without stopping ordinary practice.
The saved answer appears on the card and can be replayed. Cancel saves no answer.
The normal practice log remains the source of notes throughout.

Publish cards and read replies with:

```powershell
py -m arsenal.replay cards --from-json state/arsenal/replay/cards-draft.json
py -m arsenal.replay responses --json
```

Cards live in `state/arsenal/replay/conversation.json`; answers in its `responses/`
directory. Each answer includes its question, take, exact start/end, optional text,
and a frozen replay cue. Cuts use the log's page-time origin (`pageSec(clock())`),
not the animation's time since startup. Reloading or changing the source take during
an answer refuses the save rather than attaching another take. Pending uploads must
finish before saving. POST accepts JSON from the player origin and is limited to
the explicit answer endpoint; replay GET requests remain read-only.

Publishing validates every clip before replacing the card collection. Responses
are separate, so republishing cards preserves them. The UI does not summon an agent
or promise an automatic answer: read `responses`, analyze the referenced playing,
and publish follow-up questions for the next exchange. Real cards and answers are
private local state and must never be included in a commit.
