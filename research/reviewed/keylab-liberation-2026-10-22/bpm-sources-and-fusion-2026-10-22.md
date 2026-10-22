# BPM databases + librosa fusion to seed the live beat detector

> Provenance: Claude Code workflow `wa4rlk1e3`, run 2026-10-22 by claude (Vandor) for Daniel, reviewed by claude before filing.
> Raw per-lane results: `bpm-sources-and-fusion-2026-10-22.raw.json` in this folder. Status: research record, not a ruling.

I have full grounding now. The key discovery: this isn't greenfield — `arsenal/keylab/` already implements both halves, and the real code uses **aubio**, not librosa, which changes the seed mechanism the FINDINGS assumed. Here is the synthesized build plan.

---

# Build plan: seed `arsenal/keylab` beat detection from BPM databases + find the real LED ceiling

## 0. What already exists (grounding — this is not greenfield)

- `arsenal/keylab/beatsync.py` — the realtime loop. Reads **WASAPI loopback** (so it's source-agnostic: Spotify/YouTube/FL all drive it identically) and runs `aubio.tempo("default", 1024, 512, rate)`. Already reads **Windows SMTC** via `now_playing()` → `{title, artist, status}`. Stated limitation: aubio reports half/double tempo on some tracks; no seed.
- `arsenal/keylab/ledframe.py` — `PadRenderer`, a **delta renderer** that is already the "cleverer than the hardware" lever: pads *latch*, so it diffs the 12-pad buffer and sends only changed pads (walking dot = 1–2 packets/frame instead of 12). Tracks a compression ratio.
- `arsenal/keylab/__main__.py` — the `bench` verb (host→driver throughput + paced visual-ceiling ramp) and `PAD_GAP = 0.008`.
- `winmidi.py` — `MidiOut.send_sysex` blocks until the driver accepts (1s deadline poll); `MidiIn` can capture SysEx (for screen-grammar work).

**Confirmed-on-hardware facts, dated 2026-10-22 in the code** (these are receipts, not guesses):
- Device **hard-freezes on ~36 SysEx packets in one tight burst** (needs a power cycle). **12 is the measured safe ceiling.**
- REQ byte `0x00` renders true RGB on DAW-bank pads; `0x02` came out white (colour ignored).
- `ledframe` runs `gap=0.006`, `burst=10` (an extra 4× breath every 10 packets).

**The single most important correction to the FINDINGS:** the FINDINGS' third research front is entirely about `librosa.feature.tempo(start_bpm=…, std_bpm=…)`. **The live loop uses aubio, and `aubio.tempo()` has no `start_bpm`/prior parameter.** You cannot inject a DB seed into aubio as a prior. The seed must enter a different way (see §3). This is the thing that would have burned a build cycle if taken from the FINDINGS as-is.

---

## 1. `bpm.py` — which sources, in what order, exact requests

Reconciling the three research fronts (they partly disagree on AcousticBrainz; the truth is: **submissions froze Feb 2022 but the READ API is live and returned HTTP 200 today** — alive but stale, nothing post-2022).

Priority chain for an `"Artist - Title"` string:

**Source 1 — GetSongBPM (primary; direct name lookup).** Free, needs a free key + a **mandatory visible backlink to getsongbpm.com** (account suspended without it), 3000 req/hr.
- Current host `https://api.getsong.co/`; legacy `https://api.getsongbpm.com` as fallback.
- `GET /search/?api_key=KEY&type=both&lookup=song:on my mind artist:shift k3y` (urlencoded) → array of matches with `id`.
- `GET /song/?api_key=KEY&id=<id>` → `song.tempo` (string integer — validate for null/empty).
- Header alt: `X-API-KEY: KEY`.
- **Open item:** Cloudflare blocks anonymous fetch, so field names beyond `tempo` are reconstructed from third-party clients. Do one live call with the real key to confirm shape + which host answers before wiring in.

**Source 2 — MusicBrainz → AcousticBrainz (keyless; older catalog).**
- `GET https://musicbrainz.org/ws/2/recording/?query=artist:"Shift K3Y" AND recording:"On My Mind"&fmt=json&limit=3` → `recordings[0].id` (MBID). **Mandatory** descriptive `User-Agent: AkashicKeyLab/1.0 ( rubandan@gmail.com )`; **~1 req/s** or you get 503 on *all* requests.
- `GET https://acousticbrainz.org/api/v1/<mbid>/low-level` (no key) → `rhythm.bpm` (float; it's an Essentia estimate, not editorial). High-level endpoint does **not** carry tempo.
- Bulk: `/api/v1/low-level?recording_ids=<m1>;<m2>&features=rhythm.bpm` (≤25 MBIDs). Coverage check: `/api/v1/count?recording_ids=<mbid>` (0 = not covered → fall through).
- **Gotcha:** misses anything after ~2022; 2024 tracks return 404 here.

**Source 3 — Deezer (keyless; low-weight cross-check).**
- `GET https://api.deezer.com/search?q=<artist title>` → `data[0].id` → `GET https://api.deezer.com/track/<id>` → `bpm` float. **Treat `bpm:0` as "missing", not "no beat"** — it returned 0 for both tracks tested. Vote only, never trust alone.

**Deliberately excluded:** Spotify audio-features (**dead, 403 since 2024-11-27**); ReccoBeats (free/no-key but keys off a Spotify *track ID*, not artist+title — only usable after an ID-resolution hop); Tunebat (paid/Cloudflare scrape-only); RapidAPI "Song BPM" (not clearly maintained).

**Module shape:** one `lookup(artist, title) -> list[Source(name, bpm, weight, confidence)]`, each source isolated in try/except (fail-soft per AGENTS.md), **cached by `(artist.lower(), title.lower())`** on disk/JSON — SMTC fires the same track repeatedly and the rate limits (MB 1/s, GetSongBPM 3000/hr) demand it. A free-key-absent run must still work off sources 2+3.

---

## 2. Fusing multiple DB values + one local measurement → one trusted BPM

**Do not naive-average.** Different pressings legitimately differ (observed: 123 BPM album vs 130 BPM DJ-mix for the same track), and detectors lock to 2×/½×/1.5× octaves. Algorithm:

1. Gather all answering DB values + one local measurement (librosa one-shot on a ~15 s warmup buffer — see §3).
2. **Octave-fold** every value into one reference band (e.g. 70–140 BPM) by ×2/÷2 so half/double collapse together.
3. **Cluster + median** the folded values; discard a lone outlier >8% from the cluster.
4. The cluster median is the **seed**. Keep a confidence = (how many sources agreed within tolerance). A single-source seed is "weak"; 2+ agreeing is "trusted".
5. Record which octave was chosen so the live detector's output can be snapped back to it.

`snap_to_octave(detected, anchor, factors=(0.5, 2/3, 1, 1.5, 2))` → the multiple of `detected` nearest `anchor` in **log2** space, clamped to 40–300 BPM. This is the deterministic half/double fix and the only place the seed needs to touch the live path.

---

## 3. Feeding the seed to the realtime loop (the aubio correction)

Because `aubio.tempo()` takes **no tempo prior**, the clean architecture is two-stage, not "pass start_bpm to aubio":

- **Warmup (one-shot, seeded):** buffer ~12–15 s of loopback at the start of a track (SMTC title-change is the trigger). Run `librosa.feature.tempo(onset_envelope=…, start_bpm=seed, std_bpm=1.0, aggregate=np.median, max_tempo=300)` with the §2 DB seed as `start_bpm` and a **tight** `std_bpm` — this is where librosa's prior genuinely helps. `snap_to_octave` its result against the DB seed → the **locked anchor BPM**.
- **Live march (aubio, unchanged for phase):** keep `aubio.tempo` running for **onset/phase** — it already flags the actual beats, so the visual march stays musical even when its printed BPM octave is wrong. Use the locked anchor only to: (a) display the true BPM, (b) **octave-gate** aubio's `get_bpm()` (snap it to the anchor before any tempo-derived animation), and (c) **phase-predict**: once anchored, you know the beat *period*, so you can schedule the next pad repaint at `last_beat + 60/anchor_bpm` and correct phase from aubio onsets rather than waiting for them — tighter timing and it rides through aubio's dropouts.

If you'd rather stay single-engine, keep aubio for onsets and compute the seeded global BPM with librosa only during warmup — don't try to retrofit a prior into aubio.

**Also wire beatsync → PadRenderer:** `beatsync.run()` currently sends all 12 pads inline with a crude `MIN_LIGHT_GAP=0.12` guard and does **not** use `ledframe.PadRenderer`. Routing it through `PadRenderer` gives the delta compression for free (most beat animations change 1–2 pads) and keeps every frame structurally under the 12-packet freeze ceiling. This is the highest-value refinement already sitting on the table.

**Honest gotchas:** GetSongBPM/Tunebat Cloudflare-block anonymous fetch (confirm shape with a real key); AcousticBrainz is blind post-2022; Deezer bpm is usually 0; MusicBrainz text match can mis-resolve on dirty SMTC strings (remixes, "feat.", bracket tags) — normalize the title before querying and keep the local measurement as the always-available ground truth. Net latency of the DB chain (MB 1 req/s + two hops) is ~1–3 s, which is why it's a **warmup seed**, not a per-beat call.

---

## 4. LED send-limit testing (the half the FINDINGS skipped — but the code already probes it)

The research fronts all flagged this as "separate workstream, not investigated." It's actually the more mature half in-repo. The honest state: `bench` measures **host→driver accept time**, which is *not* the device's render ceiling — the firmware has a bounded `LedStrip` queue and the real limit shows as **visible lag/stall**, so it needs eyes on the pads. Test plan to find the true ceiling empirically and exploit the latch:

1. **Burst-size sweep (find the freeze cliff precisely).** The code asserts ~36 freezes / 12 safe. Instrument it: send bursts of N packets with **zero** inter-packet gap, N = 12,16,20,24,28,32,36, power-cycling between runs, and log the largest N that renders cleanly. Pin the exact cliff rather than the inherited "~36".
2. **Gap vs. burst trade (two-axis).** For each burst size, sweep `gap` = 0 / 2 / 4 / 6 / 8 ms. The hypothesis to test: a longer gap lets a *larger* burst through safely (the queue drains between packets). Output a small grid: `(burst, gap) → clean? | stalled | froze`. This replaces the single `PAD_GAP=0.008` guess with a measured safe frontier.
3. **Sustained-rate ceiling.** Use `bench --hz` ramp (20→40→60→80→120 Hz) watching for the first visible stall; that Hz × packets-per-frame is the real sustained budget.
4. **Beat the hardware with the latch (the clever part, already half-built).** The lever is `ledframe`'s delta send: effective frame rate scales with *pads that changed*, not 12. Quantify it — run each animation (march/pulse/rainbow-scroll) through `PadRenderer` and read its `compression` stat; a walking dot should sustain far higher frame rates than a full-repaint at the same packet budget because it only spends 1–2 packets/frame. Combine with #2: pick the (burst, gap) that keeps even the rare full-repaint frame under the measured cliff, then let the diff do the rest.
5. **Receipts.** Per drill doctrine, each confirmed limit gets a dated line (the code already stamps 2026-10-22 findings) — a limit without a dated, eyes-on receipt is presumed unverified.

The hardware needs the KeyLab physically in DAW mode (close FL so it doesn't contend for the DAW port), so #1–#4 are bench runs Daniel executes with the board in front of him; the harness and logging I/we build, the visual verdict is his.

---

**Net:** build `bpm.py` as a fail-soft, cached `lookup()` over GetSongBPM (keyed) + MusicBrainz→AcousticBrainz + Deezer; fuse by octave-fold-then-median, not mean; seed a **librosa** warmup pass (not aubio — aubio has no prior) and use the result only as an octave anchor + phase predictor over the existing aubio onset march; and route `beatsync` through the existing `PadRenderer`. The LED ceiling is a two-axis (burst × gap) bench sweep that pins the real freeze cliff and then exploits the pad latch to render far under it. Files to touch: new `arsenal/keylab/bpm.py`; edits to `beatsync.py` (seed hook + PadRenderer wiring); extend the `bench` verb for the burst×gap grid. The one blocker on the BPM half is the free GetSongBPM key (Daniel must register it and host the required backlink); everything else is keyless and buildable now.