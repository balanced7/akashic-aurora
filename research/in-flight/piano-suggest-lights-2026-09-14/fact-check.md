# Fact-check: key lights, the build plan, and the chord-suggestion theory

| | |
|---|---|
| Filed | 2026-09-14, adversarial fact-check seat for Vandor |
| Checked | `key-lights.md` (all product, protocol, latency, price, fit and project-status claims); `suggest-lights-plan.md` (the same kinds of claims, plus its lights design notes); `chord-suggestions.md` (theory claims and the worked example) |
| Method | Primary sources through WebFetch/WebSearch: vendor pages, WLED docs **and WLED source code**, GitHub API for licence and activity, manuals, open theory textbooks. Local, read-only: `py -m arsenal.practice name` on every worked-example voicing; `movement()` copied from `arsenal/pianocue_voicing.mjs:572` and re-run in the scratchpad; `choose_reading` read at `arsenal/practice.py:1475`; one read-only `Get-Service MidiSrv`. |
| Not done | No code under `arsenal/` edited, no server or browser started, nothing downloaded, installed or bought, no logins. The private performance log was not re-read; log counts are taken as given. |
| Verdicts | **CONFIRMED** (source read and agrees) · **CORRECTED** (source read and disagrees, or the claim needs a material qualifier) · **UNVERIFIED** (no primary source reached this pass) |

---

## 0. Corrections that change the recommendation

These six change what gets built or bought, or how. Everything else is detail (sections 1-3).

1. **Chrome throttles hidden tabs sooner than the plan assumes, which breaks the planned keepalive** (plan 3.3, 3.4 `lights.py`).
   - **The plan's claim:** Chrome slows timers "in a tab hidden for more than 5 minutes".
   - **What Chrome does:** a hidden page's timers are checked only **once per second** from the moment it is hidden. After 5 minutes (chained timers, 30 s of silence, no WebRTC) that drops to **once per minute** ([Chrome timer throttling](https://developer.chrome.com/blog/timer-throttling-in-chrome-88)).
   - **Why it fails:** the design has three pieces:
     - the page posts frames plus a heartbeat;
     - `lights.py` re-sends only "while the page posted within 1.5 s";
     - DRGB times out after 2 s.
     So a held, pedalled chord with no new MIDI events goes dark within seconds whenever the page is in the background. That is exactly the case where Daniel plays with FL Studio in front.
   - **Fix:** tie the server's re-send to connection liveness (an open event stream or long-poll from the page), not to timer posts. Or compose on the server, as `key-lights.md` originally proposed. The 2 s DRGB timeout still covers the server dying. The hardware pick (option A) is unchanged; the "page composes" design choice needs this change before L2.
2. **The DRGB timeout does not blank the strip by itself** (plan 3.1 "the strip blanks if arsenal dies", 3.2 "DRGB's timeout byte blanks the strip").
   - **WLED docs:** WLED returns to "normal mode" when the timeout expires ([WLED UDP realtime](https://kno.wled.ge/interfaces/udp-realtime/)).
   - **WLED source** (`realtimeLock`/`exitRealtime` in [udp.cpp](https://github.com/wled/WLED/blob/main/wled00/udp.cpp)):
     - Entering realtime while WLED is off sets brightness to its last "on" value.
     - Leaving realtime restores the previous brightness and **resumes whatever effect or preset was running**.
   - **So:** the failsafe blanks only if WLED's own state is **off** (or a black preset). `key-lights.md` said this; the plan dropped it.
   - **Fix:** add "WLED power off in normal mode" to L2 configuration, and make LR2 check it.
3. **The KeyLab's 5-pin MIDI Out does carry keyboard data, per Arturia's KeyLab mk3 manual.**
   - **What the manual says:** MIDI Out "will send USB and MIDI data to external devices, and can do so without a computer when powered with an optional power supply". Its **MIDI Thru** settings pass data between the USB and DIN connectors in either direction, both, or neither ([KeyLab mk3 manual, ManualsLib](https://www.manualslib.com/manual/3648617/Arturia-Keylab-Mk3.html)).
   - **Remaining doubt:** that listing names the 49 and 61 mk3, not the 88. So it is "almost certainly yes; confirm with one cable on the 88", not "unproven".
   - **What this opens:**
     - The standalone box and plug-and-play routes can take MIDI from the KeyLab's DIN Out with no rtpMIDI install. A Pi box needs a DIN-to-USB interface; Yan Niznik's build uses an iConnectivity mio ([build post](https://yanniznik.com/building-a-led-piano-visualizer/)).
     - USB-to-DIN Thru lets a page's Web MIDI output reach a DIN-attached light box *through* the KeyLab.
4. **Windows MIDI Services is already running on this machine** (the plan's open item; key-lights question 7).
   - **Local read-only check, 2026-09-14:** service `MidiSrv` ("Windows MIDI Service") is **Running** (start type Manual) on Windows 11 **25H2, build 26200.9168**.
   - **What that gives:**
     - Microsoft says every MIDI 1.0 port becomes multi-client under this service, and WebMIDI pages can use loopbacks "without any additional drivers or installs" ([Windows blog 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/)).
     - Under legacy WinMM, a port could be opened by one app at a time.
     - So the "updates blocked" worry does not apply: the page can probably hear the KeyLab while FL Studio also has it open.
   - **Still needs:**
     - A receipt: open the KeyLab in FL Studio and in the page at the same time.
     - *Creating* custom loopbacks still needs the separate SDK Runtime and Tools package (a download, and Daniel's OK).
   - **With fix 1:** the plan's question 3 default can become "the page may sit in the background", rather than "the page must stay in front".
5. **`readings.js` must copy `choose_reading`, which puts the page's name first.** It is not a "cheapest reading" rule (chord-suggestions 1.4, 2.2; plan 2.3, 2.5).
   - **What `choose_reading` does** (`practice.py:1475-1515`):
     - An unnamed cluster takes its cheapest reading.
     - A chord detect roots on the bass keeps detect's name.
     - An inversion with its 3rd keeps detect's name.
     - Only otherwise does a reading on the bass replace it, within `READING_MARGIN`.
   - **What the local runs show:** the *cheapest* readings of the chips' own voicings are wrong:

     | Chip voicing | Cheapest reading | What "Analysed as" keeps |
     |---|---|---|
     | `Dbmaj9/F` | `Fm7b13` (3m7b13, cost 1.45) | `Dbmaj9/F` |
     | `Ab9/Gb` | `Ebm(add11)(13)/Gb` | `Ab9/Gb` |
     | `Gdim7` | `Gm(add#11)(13)` | `Gdim7` |

   - **The risk:** a twin built as "cheapest reading" would read Daniel's accepted chip 1 as a 3m and suggest from the wrong row.
   - **Fix:** the plan's `readHeld({ midis, bassMidi, key, templates })` has no input for detect's result. It needs `info` (kind, root, suffix, cost) injected. SR1 would catch the mismatch, but the interface should be right from SG0.
6. **An applied dominant's deceptive resolution goes to the target's submediant, not its "relative"** (chord-suggestions 2.4, row "X^7").
   - **The rule:** V7/X resolves deceptively to vi/X (or VI/x); the textbook case is **V7/vi to IV** ([Puget Sound 17.6](https://musictheory.pugetsound.edu/mt21c/IrregularResoltionsOfSecondaryDominants.html); [Harmony and Musicianship with Solfège](https://pressbooks.pub/harmonyandmusicianshipwithsolfege/chapter/deceptive-resolutions-of-secondary-dominants/)).
   - **Where "relative" fails:** it matches only for major targets, where the relative minor is vi/X. For his real `3^7 -> 6m` it gives **1**; the correct deceptive chord is **4**.
   - **Also worth adding:** in pop, V/V often goes to IV or bVII.
   - **Fix:** change the rule to "the target's submediant", and the RULES data in SG4 with it.

---

## 1. `key-lights.md`

### 1.1 The KeyLab 88 mk3 and fit

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| K1 | 1295 x 323 x 113 mm, 15.7 kg | CONFIRMED | [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm); [Arturia 88 page](https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/overview) |
| K2 | Fatar TP/110 hammer action, aftertouch | CONFIRMED | Thomann; [Sound On Sound](https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii) (channel aftertouch; white keys 150 mm front to rear, 9 mm dip) |
| K3 | USB-C bus powered; DIN In and Out; sustain, expression and two aux pedal inputs | CONFIRMED | SOS: "four rear-panel pedal sockets, marked Sustain, Expression, Aux In 1 and Aux In 2"; Thomann: MIDI 1 In, 1 Out. **New:** the mk3 manual mentions an optional 12 V DC 1 A supply for use without a computer. |
| K4 | 12 lit pads, 3.5" screen, no per-key lights | CONFIRMED | Thomann, Arturia |
| K5 | Screen in the middle, faders and knobs on the right, mode buttons on the left | CONFIRMED (partly) | SOS puts faders and encoders upper right with pads to their left; Arturia puts the screen centrally. "Mode buttons left" not re-checked. |
| K6 | US$1,299 list | CORRECTED (context) | Arturia's own store shows $1,299, but street price is **$999** ([Sweetwater](https://www.sweetwater.com/store/detail/KeyLab88mk3Bk--arturia-keylab-88-mk3-88-key-weighted-hammer-action-keyboard-controller-black), SOS "$999 US"); Thomann $915. |
| K7 | A standard 88-key keyboard is about 123 cm; octave 164-165 mm; white key about 23.5 mm, black about 13.7 mm | CONFIRMED | [Wikipedia, Musical keyboard](https://en.wikipedia.org/wiki/Musical_keyboard); 52 x 23.5 = 1222 mm. (datagenetics' TLS certificate had expired, so it was not read.) |
| K8 | About 35 mm to spare at each end | CONFIRMED (arithmetic) | (1295 - 1222) / 2 = 36.5 mm. The end cheeks' real width is unmeasured. |
| K9 | Depth and height of the flat surface behind the keys unknown; Daniel measures | UNVERIFIED (still) | No source. SOS gives the 150 mm key length only. |
| K10 | "The usual place is a thin aluminium channel on that lip, lighting the back of each key" (Yan Niznik) | CORRECTED (wording) | His post says the profile sits "above the piano keys" on a Kawai ES6. "On that lip" and "lighting the back of each key" are inference. The "harsh" and "professional stage-like glow" quotes are CONFIRMED. |
| K11 | Whether DIN Out repeats the keybed is unverified; DINTHRU exists on the Essential mk3 | CORRECTED | See 0.3. The mk3 manual says MIDI Out sends keyboard data and offers USB/DIN Thru settings. The Essential mk3 FAQ returned 403; its DIN THRU description is corroborated only by a search snippet (medium). |

### 1.2 Commercial light bars

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| P1 | Piano LED Plus: USB-B or 5-pin MIDI; Bluetooth and Wi-Fi; app on iOS, Android, Mac, Windows | CONFIRMED | [pianoledshop en-us](https://pianoledshop.com/en-us/products/pianoledplus) |
| P2 | No per-key API; Amazon calls it "Synthesia ... Compatible" | CONFIRMED (no API documented) | The vendor page and FAQ mention neither Synthesia nor a PC or DAW mode. A Reverb listing title also says "Synthesia ... Compatible". A search summary says it links to Synthesia over Wi-Fi, but no vendor page shows how, so that is UNVERIFIED. Open question 6 stands. |
| P3 | "Less than 20 milliseconds" | CONFIRMED (vendor claim) | "< 20 ms" |
| P4 | Strip 123 x 1.3 x 0.4 cm, cuttable, self-adhesive | CONFIRMED except "self-adhesive" (UNVERIFIED) | Vendor. Also: control box 7.9 x 7.9 x 3.3 cm with a magnetic mount; USB-C power from a 5 V 3 A adapter. |
| P5 | White or black housing; LED colour range not stated | CONFIRMED | Vendor |
| P6 | EUR 179 on sale, EUR 199 list; 5,000+ tracks behind a paid tier | CONFIRMED (fetched 2026-09-14) | Premium EUR 9.90 per month or EUR 99 per year; free tier has 50 tracks. |
| P7 | Hi-Lite: Bluetooth 4.0 or micro-USB, its own app, works with Synthesia | CONFIRMED (Bluetooth and micro-USB); Bluetooth 4.0 medium; Synthesia UNVERIFIED | [CoolThings](https://www.coolthings.com/the-one-piano-hi-lite-led-guide/); retailer summaries |
| P8 | Red and blue only, one LED per key | CONFIRMED (colours, medium); UNVERIFIED (LED count) | Retailer text: red for right-hand notes, blue for left. |
| P9 | 48.3 x 0.9 x 0.8 in; needs mains power | CONFIRMED | CoolThings |
| P10 | "$179 in one article, date unclear" | CONFIRMED, date found | $179 at launch, CoolThings, 25 September 2017. A 2017 product; one Australian retailer lists AUD 636.84; current US stock unknown. |
| P11 | I-piano LED Visualizer (Etsy) | UNVERIFIED | Not fetched |

### 1.3 Open-source projects

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| O1 | Piano LED Visualizer, MIT | CONFIRMED | GitHub API: MIT; last push 2026-08-30; 767 stars (active). The README now targets Raspberry Pi OS Trixie. |
| O2 | Pi Zero WH or Zero 2 W; WS2812B "at least 1.5m with 144 diodes/meter"; 5 V 6 A; GPIO 18 | CONFIRMED except GPIO 18 (UNVERIFIED) | [README](https://raw.githubusercontent.com/onlaj/Piano-LED-Visualizer/master/README.md) |
| O3 | USB MIDI, RTP-MIDI (rtpMIDI on Windows), Bluetooth | CONFIRMED | [features.md](https://github.com/onlaj/Piano-LED-Visualizer/blob/master/Docs/features.md) |
| O4 | Synthesia "finger-based channel": velocity 1 lights a guide on channels 1-12, other velocities sound; colours per channel | CONFIRMED | features.md: "Channel 1-12 selects the hand/finger color", "note_on velocity 1 lights a guide", "velocity above 1 starts a note". The source is PLV's documentation; Synthesia's own keyboard page does not document the protocol. |
| O5 | Web UI on port 80; LED shift, reverse and count | CONFIRMED | features.md |
| O6 | Pi models other than the Zero lag badly | CONFIRMED | README: "many users reported problems with huge delay between key presses and lights reacting to it on Raspberrys other than Zero" |
| O7 | About $75-100 in parts | CONFIRMED | README |
| O8 | v1.6 released 2 March 2025 (timestamp handling, gamma correction) | CONFIRMED (date); UNVERIFIED (gamma) | GitHub API `published_at` 2025-03-02. (The rendered releases page, as summarised by WebFetch, said 2024; the API is authoritative.) Notes list "accurate MIDI timestamp handling", a pedal light mode and colour mapping; gamma is not named in the summary. |
| O9 | PianoLux ESP32: MIT; ESP32-S2 or S3 USB host; 144 or 72 per metre; USB host, rtpMIDI, Bluetooth, serial; Chrome or Edge only; no documented external per-key API | CONFIRMED | [README](https://github.com/serifpersia/pianolux-esp32); GitHub API: v1.12 released 2026-08-01 (active, 39 stars). |
| O9b | PianoLux has "Ten LED modes" | CORRECTED | **Six** modes (Default, Splash, Split, Random, Velocity, Animation); the Animation mode has ten patterns. |
| O10 | key_led: MIT; ItsyBitsy RP2040; 1 m WS2812 at 144 per metre; finger-based protocol; left blue, right green; 88 keys not tested | CONFIRMED | [touchgadget/key_led](https://github.com/touchgadget/key_led) |
| O10b | key_led: '1 LED per key by default ("too small")' | CORRECTED | The README says the default of 1 LED per key only works if each key is 1 LED wide; "it is closer to 2 LEDs per piano key". The "too small" phrase is about the strip: "1 meter is too small for a full sized 88 key piano keyboard". **Status:** last push December 2021, dormant. |
| O11 | key_led can be driven "from any app, including a Web MIDI page" | UNVERIFIED | Plausible (class-compliant USB MIDI), not tested or documented |
| O12 | PianoLights: ESP32, WS2812B at 144 per metre, Bluetooth MIDI, via Synthesia | CONFIRMED | [mrichana/PianoLights](https://github.com/mrichana/PianoLights). Add: no licence file, last push January 2024, 5 stars, at most 20 LEDs lit at once. Not a base to build on. |

### 1.4 Keyboards with lit keys

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| N1 | NI Kontrol S88 MK3 has an RGB Light Guide above each key | CONFIRMED (medium) | NI and retailer descriptions |
| N2 | Third-party control is reverse-engineered, macOS only, through NI's hardware-service socket; indexed palette; March 2026 and August 2026 milestones | CONFIRMED | [KompleteSynthesia #29](https://github.com/tillt/KompleteSynthesia/discussions/29): msgpack-RPC on a Unix socket (`odr_agent`); each colour byte is a palette index plus 2 intensity bits |
| N3 | SynthesiaKontrol supports MK1 and MK2 only | CONFIRMED | [README](https://github.com/ojacques/SynthesiaKontrol); the v1.6-v1.8 releases of 2026-08-17 added auto-detect and transpose, not MK3 |
| N4 | S88 MK3 $1,299, "the same as the KeyLab he already has" | CONFIRMED ($1,299); CORRECTED (comparison) | Sweetwater $1,299; Chuck Levin's $1,199; Equipboard from $930. The KeyLab's street price is $999, so the S88 costs about $300 more. The verdict ("No") stands. |
| N5 | TheONE TOP1X from $999 | CONFIRMED | [theonemusic](https://theonemusic.com/products/stage-digital-piano-sp-nex-smart-keyboard-pro): "From $999.00" (regular $1,299) |
| N6 | Casio LK-S450: 61 keys, lit keys, Chordana app, USB-MIDI, "about $200 class" | CONFIRMED except the price, which is CORRECTED | $299.99 on sale, $429.99 regular at one US dealer |

### 1.5 Geometry, WLED, power

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| G1 | 144 per metre is 6.94 mm per LED; about 3.4 LEDs per white key; a semitone is about 2 LEDs | CONFIRMED (arithmetic) | |
| G2 | "Two LEDs per semitone" drifts about 12 mm over 87 steps | CONFIRMED (arithmetic) | 0.139 mm x 87 = 12.1 mm |
| G3 | PLV's default offsets skip one LED above notes 55 and 92 | CONFIRMED | features.md: "offsets LEDs by 1 for notes bigger than 55 and by 1 for notes bigger than 92" |
| G4 | Black keys and white-key tails alternate at nearly even spacing behind the keys | UNVERIFIED | No readable source (datagenetics certificate expired). The calibration drill makes this moot. |
| W1 | DRGB and DNRGB on UDP 21324; byte 1 is a timeout in seconds, 255 means never; DRGB up to 490 LEDs, DNRGB up to 489 with a start index | CONFIRMED | [WLED UDP realtime](https://kno.wled.ge/interfaces/udp-realtime/). Source: `realtimeLock(udpIn[1]*1000+1, ...)`. DRGB's protocol byte is 2 ([LedFx](https://docs.ledfx.app/en/latest/configuring.html): "02" prefix on 21324), so the sender sketch is right. |
| W1b | The DRGB timeout is a failsafe if arsenal dies | CONFIRMED, with a qualifier | See 0.2: WLED resumes its normal state, and blanks only if that state is off. `key-lights.md` gave the qualifier; the plan dropped it. |
| W2 | DDP on 4048; WLED ignores timecodes | CONFIRMED | [WLED DDP](https://kno.wled.ge/interfaces/ddp/) |
| W3 | DDP header at most 10 bytes, against E1.31's 126 | UNVERIFIED | The blog returned 403 and the 3waylabs host refused connection again. WLED's FAQ confirms "smaller packet overhead" only qualitatively. |
| W4 | DDP push flag on the last packet; type `0x0B` for 8-bit RGB | CONFIRMED (behaviour); push-flag value medium | WLED source ([e131.cpp](https://github.com/wled/WLED/blob/main/wled00/e131.cpp)): it renders on a push flag (or on every packet until it has seen one), and treats any data type whose bits 3-5 are not `011` (RGBW) as RGB, so `0x0B` works. |
| W5 | LedFx defaults to DDP for WLED because of "better latency" | CONFIRMED | "better latency and no pixel count limits" |
| W6 | E1.31: 170 LEDs per universe; no more than 3 universes (510 LEDs) for a steady 40 fps | CONFIRMED | [WLED E1.31](https://kno.wled.ge/interfaces/e1.31-dmx/) (up to 9 adjacent universes overall) |
| W7 | JSON API `seg.i` sets individual LEDs; WebSocket; not a realtime stream | CONFIRMED | [JSON API](https://kno.wled.ge/interfaces/json-api/): chunks of at most 256 colours, never parallel calls, "use UDP Realtime or DDP" for streaming. The `ws://<ip>/ws` path was not re-fetched. |
| W8 | Serial Adalight or tpm2 at 115200 baud suits about "50-100 LEDs"; faster rates configurable | CONFIRMED | [WLED serial](https://kno.wled.ge/interfaces/serial/); up to 1,500,000 baud |
| W9 | QuinLED Dig-Uno pre-assembled: fuse, reverse-polarity protection, level shifters | CONFIRMED | [quinled.info](https://quinled.info/quinled-dig-uno/). The pre-assembled version is pre-flashed with WLED and has **optional Ethernet**, so the "Dig-Uno with Ethernet" pick is valid. |
| W10 | GLEDOPTO ESP32 WLED Ethernet controllers with fuse and level shifter, about $26-48 | CONFIRMED (medium) | GLEDOPTO EU store EUR 29.99-34.99 for Ethernet models (e.g. GL-C-616WL "Elite"); US eBay about $47.80; Amazon titles list a "20A pluggable fuse" and a level shifter. **Note (low, my advice):** a 20 A controller fuse does not protect a 6-10 A supply and 5 V strip; add an inline fuse sized to the supply. |
| S1 | 5 V only: more volts "WILL damage both LED strip and Raspberry Pi" | CONFIRMED | PLV README |
| S2 | About 60 mA per LED at full white | CONFIRMED | [Zaitronics](https://zaitronics.com.au/blogs/guides/ws2812b-led-power-requirements-rgb-strips-rings-matrices) |
| S2b | 144 per metre draws "about 25-29 W per metre at most" (BTF, Zaitronics) | CORRECTED | Zaitronics' own figure is **43.2 W/m** (144 x 60 mA x 5 V). BTF's listing (search summary; page returned 403) rates "Max 25 W/m" and recommends 5 V 6 A per metre. Real strips measure below the 60 mA theory. For 1.22 m: about 30 W (6.1 A) at BTF's rating, 10.6 A in theory. The 6-10 A supply plus the brightness limiter stands; buy the 10 A end if the limiter might ever be off. |
| S3 | "5V 6A is enough to light 172 LEDs @50% power" | CONFIRMED | PLV README |
| S4 | Set WLED's Auto Brightness Limiter "slightly below the rating of your power supply" | CONFIRMED | [WLED FAQ](https://kno.wled.ge/basics/faq/) |
| S5 | 500-1000 µF capacitor; 300-500 Ω data resistor at the strip end; 74AHCT125 or 74HCT245 level shifter | CONFIRMED | [Adafruit best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide (Best Practices page)) (capacitor rated 6.3 V or higher; connect ground first) |
| S6 | 22-18 AWG wire; inject power every 1-2 m | CONFIRMED | PLV README; Zaitronics |
| D1 | BTF's 144-per-metre strip is 12 mm wide | CONFIRMED (medium) | BTF listing via search summary |
| L1 | Strip write about 5.3 ms for 176 LEDs (800 kbps, about 30 µs per LED) | CONFIRMED | [Worldsemi datasheet](https://cdn.sparkfun.com/assets/e/6/1/f/4/WS2812B-LED-datasheet.pdf): 800 kbps, T0H+T0L about 1.25 µs, reset over 50 µs. WLED source calls `strip.show()` immediately on each DRGB packet; DDP waits for the push flag. |
| L2 | LedFx: "extremely latency sensitive and will expose weaknesses in your WiFi network"; disable Wi-Fi sleep; prefer Ethernet | CONFIRMED | [LedFx network](https://docs.ledfx.app/en/latest/troubleshoot/network.html); WLED E1.31 page; WLED FAQ ("QuinLED-Dig boards with ethernet or the Olimex ESP32-POE"; an external antenna "is significantly better than a PCB antenna") |
| L3 | People detect audio-visual offsets as small as 20 ms; musicians judge synchrony better | CONFIRMED | [PMC4451240](https://pmc.ncbi.nlm.nih.gov/articles/PMC4451240/). arXiv 2212.01686 was not fetched. |
| L4 | 240 fps is about 4.2 ms per frame | CONFIRMED (arithmetic) | |
| Q3 | "WLED advice: an RSSI of -70 dB or worse performs poorly" | CORRECTED (attribution and unit) | This is LedFx's page, not WLED's: "If you are -70 or worse, you are going to have a bad time" (dBm). |

### 1.6 Integration claims

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| I1 | Raw UDP from a page needs Direct Sockets, which is Isolated-Web-App only | CONFIRMED | [Chrome Direct Sockets](https://developer.chrome.com/docs/iwa/direct-sockets) |
| I2 | `http://localhost` is a secure context, so Web MIDI works there | CONFIRMED | [MDN secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts) |
| I3 | `MIDIOutput.send(data, timestamp)`; SysEx needs a permission | UNVERIFIED (not re-fetched) | Consistent with the Web MIDI spec |
| I4 | Windows 11 multi-client ports and built-in loopback; WebMIDI loopbacks with no drivers; custom loopbacks need the separate Tools download; phased rollout | CONFIRMED | Blog: "You can create your own loopback endpoints using the MIDI Settings app in the upcoming Windows MIDI Services Tools download"; `winget install Microsoft.WindowsMIDIServicesSDK` |
| I5 | Whether this machine has it is unverified; blocked updates suggest it may not | CORRECTED | See 0.4: `MidiSrv` is running on 25H2 build 26200.9168 |
| I6 | New: WLED applies its own brightness and gamma to realtime frames | CONFIRMED | WLED UDP realtime: "uses the current brightness and gamma correction settings". The physical colours will not equal the on-screen `noteColor` bytes unless gamma is turned off or modelled. LR1 byte parity still holds on the wire. |

---

## 2. `suggest-lights-plan.md` (product and technical claims)

| # | Claim | Verdict | Note |
|---|---|---|---|
| PL1 | 3.1 A: "a 2 s timeout, so the strip blanks if arsenal dies"; 3.2: "DRGB's timeout byte blanks the strip when frames stop" | CORRECTED | 0.2 |
| PL2 | 3.3: "Chrome slows timers in a tab hidden for more than 5 minutes" | CORRECTED | 0.1: once per second as soon as the tab is hidden, once per minute after 5 min. The 1 s re-send, 1.5 s freshness and 2 s timeout blank a held chord in a background tab. |
| PL3 | 3.3: "Web MIDI events still arrive while the tab is hidden" | UNVERIFIED | No primary source found. Needs a drill, with FL Studio in front, once multi-client (0.4) is proven. |
| PL4 | 3.1 A: controller about $26-48 (medium); total about $90-150 (low) | CONFIRMED (controller); UNVERIFIED (total) | W10 |
| PL5 | 3.1 A: "WLED firmware usually comes pre-flashed" | CONFIRMED (QuinLED pre-assembled); medium for GLEDOPTO | W9; GLEDOPTO sells these as WLED controllers |
| PL6 | 3.1 B: "Flashes WLED from its web installer" | CONFIRMED | WLED serial docs refer to the official web installer (Improv). It needs a Web Serial browser (Chrome or Edge), and it is a firmware download (Daniel's OK). |
| PL7 | 3.1 C: Piano LED Plus EUR 179-199, "less than 20 ms", only its own lessons | CONFIRMED | P1-P6 |
| PL8 | 3.1: S88 MK3 ($1,299) has no Windows light control | CONFIRMED | N2-N4 |
| PL9 | 3.1: the standalone PLV box costs about $75-100 and routing from the KeyLab is "unproven" | CONFIRMED (cost); CORRECTED (routing) | 0.3. It needs a DIN-to-USB MIDI interface for the Pi, about $30 in the Yan Niznik build. |
| PL10 | 3.4: budget formula `sum(rgb)/765 x 60 mA` | CONFIRMED (consistent with S2) | Conservative against BTF's 25 W/m rating |
| PL11 | 6: "Unverified and carried forward: ... whether the KeyLab DIN Out carries the keybed; ... Windows MIDI Services on this update-blocked machine" | CORRECTED | Both are now mostly answered (0.3, 0.4) |

---

## 3. `chord-suggestions.md` (theory and worked example)

### 3.1 Local reproduction (read-only runs)

`py -m arsenal.practice name <notes> --key "Db major"`, with movement from the bridge's own `movement()`:

| Voicing | Page namer | Analysed as | Cheapest reading | Movement from the held chord |
|---|---|---|---|---|
| held `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` | `Bbm11/Gb = 6m11/4` | `Gbmaj13#11 = 4maj13#11` ("the Lydian 4") | same; `6m11b13/4` listed third | n/a |
| `F2 Db3 F3 Ab3 C4 Eb4` | `Dbmaj9/F = 1maj9/3` | same | `Fm7b13` (3m7b13) | **3** |
| `Gb2 C3 Eb3 Ab3 Bb3 C4 Eb4` | `Ab9/Gb = 5^9/4` | same | `Ebm(add11)(13)/Gb` | **3** |
| `Gb2 Db3 Eb3 Ab3 A3 Db4 Eb4` | `Gbm6/9 = 4m6/9` (raw `F#m6/9`) | same (borrowed) | same | **4** |
| `Bb2 Db3 F3 Ab3 Bb3 C4 Eb4` | `Bbm11 = 6m11` | same | same | **4** |
| `G2 Db3 E3 Bb3 Db4 E4` | `Gdim7 = #4°7` | same (chromatic) | `Gm(add#11)(13)` | **6** |
| `F2 C3 E3 G3 A3 B3 D4` (all down a half step) | `Am11/F` | `Fmaj13#11` (3maj13#11 in Db; 4maj13#11 in C) | same | **7** |
| `Gb2 Db3 F3 Ab3 A3 C4 Eb4` (one-finger 4m) | unnamed (lists the notes) | `Gbm(maj9,#11,13)` | same | 1 |

### 3.2 Verdicts

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| T1 | The held voicing is `Gbmaj13#11 = 4maj13#11`; the page says `Bbm11/Gb = 6m11/4`; `practice name` lists `6m11b13/4` third | CONFIRMED | Local run; intervals from Gb: Db 5, F maj7, Ab 9, Bb 3, C #11, Eb 13 |
| T2 | "The Lydian 4": the 4 chord's #11 is already in the key | CONFIRMED | Lydian is the mode on the 4th degree; C is Db major's 7th |
| T3 | "The engine reads the held chord with the practice verbs' reading rules (bass-aware, cheapest reading)" | CORRECTED | 0.5: `choose_reading` keeps the page's name first; the twin needs detect's result as input |
| T4 | Each chip's "Page reads it as" column, including the unnamed one-finger 4m | CONFIRMED | 3.1 |
| T5 | Movements 3, 3, 4, 4, 6; 7 and 8 for the doors | CONFIRMED (3, 3, 4, 4, 6, 7); UNVERIFIED (8, the Bb door voicing is not given) | 3.1 |
| T6 | Hand descriptions: e.g. `Ab9/Gb` is "Db3 to C3, F3 to Eb3"; `Gdim7` is bass to G2, F3 to E3, C4 to Db4, Eb4 to E4, lift Ab3 | CONFIRMED | Pitch-class check of each result |
| T7 | `Ab9/Gb` is "a dominant 7th in disguise": the Gb bass falls to F, C rises to Db, "the textbook resolution" | CONFIRMED | This is V4/2 to I6: the 7th in the bass must resolve down to the 3rd, so the tonic arrives in first inversion ([Milne, The Dominant Seventh Chord](https://milnepublishing.geneseo.edu/fundamentals-function-form/chapter/19-the-dominant-seventh-chord/)). In the chip voicings C3 rises to Db3 while C4 stays as the maj7. |
| T8 | The score arithmetic (0.62, 0.52, 0.41, 0.37, 0.34) | CONFIRMED (arithmetic); CORRECTED (rule) | Section 2.6 says N "only counts for stretch candidates", yet `Ab9/Gb` (+0.05), `Bbm11` (+0.01) and `Gbm6/9` (+0.07) get it. Without N they score 0.47, 0.40 and 0.30. The slots come out the same, but the SG0 `chips_expected.json` fixture must choose one rule. H shares (45/110, 24/110, 19/110) are right, but the claimed k = 1 smoothing is not applied in the example. |
| T9 | Theory rows 1, 2m, 3m, 4, 5, 5sus, 6m, 2 (Lydian light), borrowed, minor | CONFIRMED | Standard functions: V7/IV (`1^7 -> 4`), V7/vi (`3^7 -> 6m`), vii°7/ii (`#1°7 -> 2m`), V7/V (`2^7 -> 5`), V7/ii (`6^7 -> 2m`), deceptive 5 to 6m and 5 to b6, minor plagal 4m to 1, Aeolian b6 b7 1, #iv°7 to I6/4 (a gospel staple: [Hear and Play](https://hearandplay.com/main/the-extended-resolution-of-the-4-diminished-seventh-chord/)); `1/3 -> b3°7 -> 2m7` as a chromatic passing diminished (medium). |
| T10 | Row X^7: "its target (1.0), the target's relative (0.5)" | CORRECTED | 0.6: the target's submediant (V7/vi to IV) |
| T11 | Row 2m's reason word "home-ward" | CORRECTED (internal) | Not in the fixed vocabulary (3.4) or the plan's `REASONS`; SR10 would fail on it. Use "lift" or add the word deliberately. |
| T12 | Chromatic slides: `4 -> #4°7 -> 1/5`; `1/3 -> b3°7 -> 2m7`; 4 to 4m by the 3rd alone | CONFIRMED | |
| T13 | Key-change hinges (1.3) and doors (2.4) | CONFIRMED (interval arithmetic) | Down a minor 3rd: the old 4 is 5 + 3 = 8 semitones above the new tonic, the b6, and the old 2 becomes the new 4. Down a half step: the old 4 slid down is the new 4. Up a whole step: the old 3m is the new 2m. Up a 4th: the old 5, made minor, is the new 2m. Db down a minor 3rd is Bb, and Gb is Bb's b6. |
| T14 | Deceptive "surprise" is 5 to 6m and 5 to b6; "borrowed colour" means the parallel minor | CONFIRMED | (b7 is also Mixolydian; the wording is fine) |
| T15 | 1.2: "The plain 5 (or 5^7) to 1 cadence is essentially absent" | UNVERIFIED, and in tension with 1.1 | Table 1.1 shows 1 coming 6 times out of 33 after a 5. The history verb's cadence count may measure something narrower (phrase ends). Reword to say both, e.g. "5 went to 1 in 6 of 33 moves, and never as a logged cadence". Log counts not re-run. |

---

## 4. What the research missed

| Item | Why it matters | Changes the pick? |
|---|---|---|
| **PartyKeys** ([developer site](https://developer.partykeys.com/), [protocol](https://protocol.partykeys.org/)): MIT open hardware; a **documented** SysEx per-key RGB message (`F0 05 30 7F 7F 20 00 15 ...`, colour split into 7-bit pairs); class-compliant USB MIDI, so Web MIDI can drive it directly | The only lit-key keyboard found with an open, documented per-key RGB protocol a Web MIDI page can send | **No.** 36-key modules (C3-B5; expands to 72 or 108), not weighted; its own protocol page cites about 200 ms latency. At most a desk companion for Try targets. |
| KeyLab mk3 can send DIN MIDI standalone with a 12 V supply | A light box could follow the keys with no PC at all | Strengthens the "fourth route" only |
| WLED's global brightness and gamma apply to realtime frames | Screen colour and key colour will differ unless calibrated | No; add to L5 or LR1 notes |
| WLED FAQ: an external-antenna ESP32 beats a PCB antenna for realtime | Relevant if option B (Wi-Fi) is chosen | No |

---

## 5. Open questions, updated

| key-lights # | Question | Status after this check |
|---|---|---|
| 1 | Depth and height of the surface behind the keys | Still open: measure it |
| 2 | Does DIN Out carry the keybed; is there a Thru? | **Mostly answered: yes** (mk3 manual: MIDI Out sends keyboard data; USB/DIN Thru settings). Confirm on the 88 with one cable. |
| 3 | Wi-Fi at the piano | Open. Threshold -70 dBm is from LedFx, not WLED. |
| 4 | Lights on camera | Open (Daniel) |
| 5 | When suggestions light | Open (design) |
| 6 | Does Piano LED Plus light notes from a computer on MIDI IN? | Open. Nothing on the vendor page or FAQ; the Synthesia-over-Wi-Fi claim is unsourced. Ask the vendor. |
| 7 | Windows MIDI Services on this machine | **Answered: present and running** (25H2, 26200.9168). A multi-client receipt is still needed; custom loopbacks still need the Tools download. |
| 8 | Retail prices | Controller prices medium-confirmed; strip, supply and channel prices still unverified |

## Sources

- WLED: [UDP realtime](https://kno.wled.ge/interfaces/udp-realtime/), [DDP](https://kno.wled.ge/interfaces/ddp/), [E1.31](https://kno.wled.ge/interfaces/e1.31-dmx/), [JSON API](https://kno.wled.ge/interfaces/json-api/), [Serial](https://kno.wled.ge/interfaces/serial/), [FAQ](https://kno.wled.ge/basics/faq/), source [udp.cpp](https://github.com/wled/WLED/blob/main/wled00/udp.cpp) and [e131.cpp](https://github.com/wled/WLED/blob/main/wled00/e131.cpp)
- LedFx: [configuring](https://docs.ledfx.app/en/latest/configuring.html), [network](https://docs.ledfx.app/en/latest/troubleshoot/network.html)
- Arturia and the KeyLab: [KeyLab 88 mk3 page](https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/overview), [KeyLab mk3 manual (ManualsLib)](https://www.manualslib.com/manual/3648617/Arturia-Keylab-Mk3.html), [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm), [Sound On Sound](https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii), [Sweetwater](https://www.sweetwater.com/store/detail/KeyLab88mk3Bk--arturia-keylab-88-mk3-88-key-weighted-hammer-action-keyboard-controller-black)
- Light bars and lit keyboards: [Piano LED Plus](https://pianoledshop.com/en-us/products/pianoledplus), [CoolThings Hi-Lite](https://www.coolthings.com/the-one-piano-hi-lite-led-guide/), [Sweetwater S88 MK3](https://www.sweetwater.com/store/detail/KontS3-88--native-instruments-kontrol-s88-mk3-88-key-smart-keyboard-controller), [KompleteSynthesia #29](https://github.com/tillt/KompleteSynthesia/discussions/29), [SynthesiaKontrol](https://github.com/ojacques/SynthesiaKontrol), [TheONE](https://theonemusic.com/products/stage-digital-piano-sp-nex-smart-keyboard-pro), [PartyKeys protocol](https://protocol.partykeys.org/)
- Open-source projects: [Piano LED Visualizer README](https://raw.githubusercontent.com/onlaj/Piano-LED-Visualizer/master/README.md), [features.md](https://github.com/onlaj/Piano-LED-Visualizer/blob/master/Docs/features.md), [PianoLux ESP32](https://github.com/serifpersia/pianolux-esp32), [key_led](https://github.com/touchgadget/key_led), [PianoLights](https://github.com/mrichana/PianoLights); GitHub API (`gh api repos/...`) for licences, last push and release dates
- Controllers and power: [QuinLED Dig-Uno](https://quinled.info/quinled-dig-uno/), [GLEDOPTO EU](https://www.gledopto.eu/gledopto-wled-controller-esp32-elite-2d-exmu_1), [Adafruit best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide (Best Practices page)), [Zaitronics](https://zaitronics.com.au/blogs/guides/ws2812b-led-power-requirements-rgb-strips-rings-matrices), [Worldsemi WS2812B datasheet](https://cdn.sparkfun.com/assets/e/6/1/f/4/WS2812B-LED-datasheet.pdf), [Yan Niznik build](https://yanniznik.com/building-a-led-piano-visualizer/)
- Browser and OS: [Chrome timer throttling](https://developer.chrome.com/blog/timer-throttling-in-chrome-88), [Chrome Direct Sockets](https://developer.chrome.com/docs/iwa/direct-sockets), [MDN secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts), [Windows MIDI Services blog](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/), [Windows MIDI Services](https://microsoft.github.io/MIDI/)
- Theory and perception: [Puget Sound 17.6, irregular resolutions](https://musictheory.pugetsound.edu/mt21c/IrregularResoltionsOfSecondaryDominants.html), [Harmony and Musicianship with Solfège](https://pressbooks.pub/harmonyandmusicianshipwithsolfege/chapter/deceptive-resolutions-of-secondary-dominants/), [Milne, The Dominant Seventh Chord](https://milnepublishing.geneseo.edu/fundamentals-function-form/chapter/19-the-dominant-seventh-chord/), [Hear and Play, #4 diminished](https://hearandplay.com/main/the-extended-resolution-of-the-4-diminished-seventh-chord/), [Wikipedia, Musical keyboard](https://en.wikipedia.org/wiki/Musical_keyboard), [PMC4451240](https://pmc.ncbi.nlm.nih.gov/articles/PMC4451240/)
