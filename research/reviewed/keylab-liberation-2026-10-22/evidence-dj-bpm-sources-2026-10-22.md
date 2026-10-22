# Evidence: DJ and BPM data sources, and local DJ software (2026-10-22)

The final report of a research agent (sonnet, web plus the local Everything index), dispatched by Vandor for
Daniel's question "Are there any dj sites we can leverage? There's gotta be some". It is condensed below to its
verdict table and conclusions; the agent's full wording of each row is kept.

## Vandor's verification, which overrides one claim

The report says AcousticBrainz's live API is shut down and that tempo.py's call to it is "dead code". **That is
false.** Verified 2026-10-22:

```
GET https://acousticbrainz.org/api/v1/96685213-a25c-4678-9a13-abd9ec81cf35/low-level
-> HTTP 200, 53,908 bytes of low-level JSON
```

AcousticBrainz stopped accepting new submissions in 2022, but its frozen catalogue still serves reads, so
tempo.py's call is live. Recommendation (c)1 below is therefore withdrawn. Its staleness (no music analysed
after 2022) still stands.

## (a) Web sources, ranked (the agent's table)

| Source | Offers | Access | Terms | Verdict |
|---|---|---|---|---|
| MusicBrainz (in use) | the ID bridge to AcousticBrainz | keyless REST, ~1 req/s with a UA | core data CC0 | Use |
| AcousticBrainz (in use) | aggregate BPM + rhythm descriptors, no beat grid | keyless; frozen 2022 catalogue (see the correction above) | dump CC0 | Use (stale catalogue) |
| Deezer (in use) | `bpm` float | keyless | developer ToS, personal/non-commercial | Use with care: zero when analysis failed, octave errors (low weight already handles it) |
| GetSongBPM (in use) | BPM, key, time signature | keyed, free | **mandatory backlink to getsongbpm.com** or the key is suspended | Use with care: the backlink must exist publicly before a key is used |
| Traxsource | BPM, key, genre, charts | official API, **invite-only** keys | commercial API ToS | Use with care: apply (EDM/house-heavy, Daniel's genre) |
| Beatport API v4 | BPM, key, genre | partner-gated OAuth via the Partner Portal | unpublished for third parties | Use with care: apply (best EDM coverage; approval odds for a hobby project UNVERIFIED) |
| Tunebat | key, BPM, energy | no public API (resold via Songstats) | ToS **forbids** robots/scrapers | Avoid |
| SongBPM.com | BPM, key | none | ToS: automated access strictly prohibited | Avoid |
| 1001Tracklists | setlists, not BPM | none | robots.txt blocks scrapers | Avoid |
| Discogs | no BPM/key field | official API | CC0 core | Avoid (wrong data) |
| Last.fm | no BPM field | keyed | partner terms | Avoid (wrong data) |
| Musicstax | claims key/BPM for 100M songs | ToS page 403 | UNVERIFIED | UNVERIFIED |
| Chosic | a UI over Spotify's API | no data API | ToS 403 | Avoid |
| Juno Download | BPM/key on listings | no official API | UNVERIFIED | Avoid / UNVERIFIED |
| Mixed In Key | desktop analysis only | none | n/a | Avoid (not available) |
| KKBOX | open API | keyed | developer ToS | UNVERIFIED whether BPM exists; low priority |
| Apple Music / MusicKit | no audio-features endpoint | n/a | n/a | Avoid |
| YouTube Music | unofficial libraries only | unofficial | violates ToS | Avoid |
| SoundCloud | no BPM field confirmed | closed registration | restrictive | Avoid |
| Rekordbox cloud | per-track beat grids | **no third-party API** | n/a | Avoid (not available) |
| Million Song Dataset / Echo Nest | tempo, key, beat confidence, ~1M tracks | static download, 280 GB (1.8 GB sample) | mixed by mirror | Use with care as an offline table only (frozen ~2011) |

## (b) Local DJ software

Searched with the find verb for rekordbox, master.db, rekordbox.xml, _Serato_, database V2, collection.nml,
mixxxdb.sqlite, VirtualDJ, database.xml, djay, Engine Library, m.db, Serato, Pioneer, Mixed In Key and
Native Instruments. **No DJ software is installed.** The djay and m.db hits were false positives. FL Studio 2025
and 2026 are installed; FL keeps detected clip tempo inside the .flp itself, not in a separate cache. So there
are no local beat grids to harvest unless Daniel installs a DJ app and analyses a library.

## (c) The agent's top three, as amended by Vandor

1. ~~Fix the dead AcousticBrainz call~~: WITHDRAWN, the API is live (verified above).
2. Apply for Traxsource API access (invite-only, EDM/house-heavy). That is Daniel's call, because it is an
   outward-facing application under his name.
3. Apply for Beatport API v4 (partner portal) as a stretch goal; same call.

The scrape-only candidates (Tunebat, SongBPM.com, 1001Tracklists, Chosic, Juno) are AVOID. Each forbids
automated access or has no API, and none belongs in a public Apache-2.0 repo.
