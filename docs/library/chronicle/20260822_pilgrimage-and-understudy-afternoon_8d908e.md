---
akashic_id: art_20260822_pilgrimage-and-understudy-afternoon_8d908e
akashic_sha: 94e48cd629a7
schema_version: 1
status: current
type: chronicle
arc: T375
date: 2026-08-22
title: pilgrimage-and-understudy-afternoon
gist: "# 2026-08-22 afternoon — the pilgrimage and the Understudy (post-compaction seal) Sealed minutes after a model-swap compaction ate ~400k of "
visibility: fleet
body_type: markdown
seats: [claude]
category: [tooling, narrative]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T11:12:38"
updated: "2026-08-22T11:12:38"
---
<!-- GENERATED PROJECTION of art_20260822_pilgrimage-and-understudy-afternoon_8d908e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# pilgrimage-and-understudy-afternoon

# 2026-08-22 afternoon — the pilgrimage and the Understudy (post-compaction seal)

Sealed minutes after a model-swap compaction ate ~400k of Daniil's visible context — the
event this chronicle exists to make boring. Covers the stretch after chronicle
art_20260822_enablement-morning (which sealed everything prior).

## The Clarke & Dawe pilgrimage (captions door, three stations + a fact-check)

Daniil's video detour became textual criticism of the house's own report-format scripture.
Three sketches transcribed via `py agent_cli.py captions` (files on Desktop/captions/):

1. **Quantitative Easing** — the mechanism-audit theorem: describe the operation at literal
   altitude (printer, out-tray facing the window, 80 billion copies, stand well back) and
   absurdity self-reports. "Don't hold me to the answers -- I'm an economist" = the
   anti-forecast-registry stated as professional privilege (T375's foil). "Is he in
   banking? No -- good" = frame-exclusion as validity test. Rumpelstiltskin ending =
   mythology deployed when mechanism fails scrutiny, audience selected for not knowing
   how the tale ends.
2. **European Debt Crisis** (aired 2010-05-20, 7:30 Report) — the composition-audit
   theorem: every fact locally correct (Roger never misses), the system globally
   impossible — a cycle of insolvency with no ground node. Roger's recursive sentence =
   the grammar IS the topology. "Just keep answering the questions" = the format
   suppressing the halt at the unanswerable node. FACT-CHECK VERDICT (researched):
   ~85% real / 15% craft. Figures track the era's cross-exposure data (NYT "Europe's Web
   of Debt", 2010-05-01; CNBC covered the sketch as a legit explainer 2010-05-27).
   Greece-can't-pay VINDICATED by the 2012 PSI haircut (~53.5%). The "unanswerable"
   bailout-funding question had a real answer that proved the joke: EFSF guarantees by
   ECB capital key = Italy (~18%) and Spain guaranteeing their own prospective rescuer;
   final answer = Draghi 2012 = the other sketch's printer. The two sketches answer each
   other across two years of monetary history. Honest blurs: sovereign-vs-external debt
   conflation (Ireland $865B = web exposure, not treasury debt), "broke" overstating
   Spain/Italy 2010 (illiquid-not-insolvent; gross-vs-net — and contagion vindicated the
   gross view), China line = deliberate hyperbole.
3. **Talk economics / second Greek bailout (~2011)** — the jurisdiction-audit + pricing-
   audit theorems: "Do you understand the euro? No, I'm an economist. You want religious
   questions..." = domain-boundary honesty (euro-as-creed, architecturally accurate for
   2011). THE line of the era: "Why would anyone invest in an economy that can't pay its
   debts? -- Good question. People have been doing it for twenty years. That's why the
   problem exists." = the creditor-side mispricing indictment (euro convergence trade,
   risk priced by narrative not receipts for two decades — the trader project's disease,
   named by comedians). Numbers check: 160% debt/GDP real (~165% actual 2011); two
   ~$100bn bailouts real; Portugal (2011-05) + Ireland (2010-11) both genuinely "for
   sale" by air date; "guarantee the debt" = the actual EFSF mechanism as shopping
   channel. Trilogy = a complete audit curriculum: mechanism, composition, jurisdiction,
   pricing.

## The hero interlude (sealed earlier in morning chronicle, pointer): Flock/Benn-Jordan-
style receipts-vs-narrative taxonomy; Chief Jim Williams as institutional gauge-correction.

## The Tampermonkey arc → THE UNDERSTUDY PROTOCOL

Daniil's pre-house (April 2026!) userscript recovered from Brave's LevelDB by grep:
`Local Extension Settings/dhdgffkkebhmkfjojejmpbldmpobfkfo/000006.log` (plaintext WAL copy;
.ldb copy snappy-garbled; lastModified ~2026-04-09). Script = "YouTube One-Time Refresh"
v1.2: sessionStorage once-guard keyed on full href, document-start reload. Review verdict:
the once-guard is the wedged-vs-thinking discrimination done right (v1.2 implies v1.0 met
the infinite-reload dragon); sessionStorage = correct physics (tab-scoped seen-set,
self-cleaning); SPA gap (soft navs never fire userscripts) is secretly a feature (covers
direct loads = his Discord-link usage = where the wall bites). FLAG: "Allow User Scripts"
banner visible — script may be DORMANT until toggled (brave://extensions).

**v2.0 "Evidence Mode" script designed and delivered in-chat** (paste-ready): reload on
EVIDENCE not schedule — two independent detectors (enforcement-dialog MutationObserver +
markup-blind stall timer on video.readyState), per-VIDEO key (v= param), yt-navigate-finish
re-arming, and a firing counter as the script's own dies_when (counter stops growing =
filter layer won = retire with dignity).

**The Understudy Protocol (v2 design, Daniil: "straight for v2, 4K, embeds, containers"):**
YouTube's own page renders everything; only the video arrives through the stage door.
Strangler fig on Google's DOM. MEASURED format receipts (yt-dlp 2026.07.04, Big Buck Bunny
probe): no muxed 4K exists — DASH only above 720p; **AV1 itag 401 = 679MiB/8982k vs VP9
itag 315 = 1.27GiB/17174k for identical 2160p60** — AV1 halves the bandwidth; audio opus
251 (129k) or AAC-5.1 258. Architecture: (1) localhost resolver (~50 lines, captions-door
sibling): /resolve?v=ID via yt-dlp (AV1-4K + opus picks) + /media range-forwarding CORS
proxy so yt-dlp owns the nsig-solved un-throttled URLs; (2) changeling userscript: kill YT
player, mount <video>, dual-SourceBuffer MSE (video+audio tracks separately), no external
libs, re-arm on yt-navigate-finish. CONTAINER LEVERS: DASH/AV1 = guaranteed 4K primary;
HLS via player_client=ios = single adaptive m3u8, historically nsig-free, less-reliable 4K
= low-friction alternate; player_client=web_embedded/tv_embedded = restriction-profile
fallback resolver. EMBEDS: second @match * script swaps iframe[src*=youtube.com/embed]
site-wide (value = consistency/privacy; embeds rarely hit the wall). FRAGILITY, named as
dies_when: the nsig throttle makes resolver-always mandatory (raw scrape = ~50KB/s); PO
tokens = the live 2026 arms race; v2's death-condition = "yt-dlp can no longer resolve
un-throttled URLs", fix always = update yt-dlp never patch our code; resolver prints
yt-dlp version as boot receipt. URL expiry/IP-lock = non-issues by construction (per-view
resolve, same IP). Build order: resolver first (testable in isolation), then changeling.
STATUS: designed + spec'd, awaiting Daniil's word to build. Personal-use tooling, his
machine, captions-door class.

## Context note

The model swap (Fable→Opus→Fable) compacted ~400k of Daniil's visible context mid-
afternoon. This seal means the answer to "what did we lose?" is: nothing of record.
Plan-wall doctrine held: land work to durable files continuously so any death is boring.
