# Per-key lights for the piano page

Filed 2026-09-14 by a research seat for Vandor. This is research and design only: nothing was bought, downloaded, installed or flashed, and no code under `arsenal/` was changed.

Daniel asked on Discord: "I am wondering if there are any light systems out there that we could link up to have individual keys light up!"

**Short answer.** Yes. The option that fits our stack best is a do-it-yourself strip of addressable LEDs (WS2812B, 144 per metre) along the back of the KeyLab's keys, run by an ESP32 board with the WLED firmware. The arsenal server streams it one full frame at a time over UDP, using WLED's DRGB or DDP realtime protocols. That is the only route that can show all the page's layers on the physical keys: Daniel's pitch colours, Claude's moonlight, ghost chords, Try-mode targets and chord suggestions.

- **Commercial light bars** are built around their own learning apps. None of them documents a way for a PC to set any colour on any key.
- **Keyboards with lit keys** are not worth leaving the KeyLab 88 mk3 for. The one serious 88-key option (NI Kontrol S88 MK3, $1,299) has no documented third-party light control on Windows.

Every option below needs a purchase, plus a firmware flash or software install. Each one needs Daniel's OK first.

Confidence labels used below: **high** (primary source read), **medium** (secondary source or a summary of one), **low** (inference or unverified).

---

## 0. What the page already has for lights to reuse

These are local facts, read from the repo on 2026-09-14.

- **Daniel's colour.** `noteColor(midi, vel)` in `arsenal/web/piano.js:338` builds OKLCH pitch colours in linear RGB. Brightness is pulled toward the palette's mean luminance, so velocity sets brightness rather than the note name (`LUMA_PULL = 0.65`). A strip can use the same function, so the keys match the screen.
- **Claude's colour.** Moonlight `#C8DCFF` (`arsenal/web/piano/glass.js:30`, `MOON`). The jam spec's C12 rule is that Claude is "never pitch-tinted", capped at 0.75 of Daniel's glow. A key held by both shows Daniel's colour with a moonlight rim (`research/in-flight/piano-jam-2026-09-14/jam-spec.md`, lines 67 and 593).
- **Ghost states.** The spec defines four: `target` (breathing 0.92-1.00 at 0.5 Hz), `incoming`, `hold` and `found`. Found "pulses once in size ... never in brightness" (jam-spec lines 594-598, 691).
- **Invariant INT 1.** Cue notes never reach `detect()`, the log, the key tracker or rarity (jam-spec line 66). A lights output must only *read* state and never feed anything back into it.
- **Transport.** The server is stdlib `ThreadingHTTPServer` (`arsenal/serve.py:18, 657`). It already brokers Claude's cues (`POST /api/piano/cue`, `GET /api/piano/cues` as an event stream).
  - Python's stdlib `socket` can send UDP, so a UDP light sender needs **no pip install**.
  - The page already opens Web MIDI *output* ports (`arsenal/web/piano/cues.js:1245 midiSend`, `:1358` output listing).
- **Planned MIDI and FL work.** MIDI out and FL Studio routing are v2 and wait for "Daniel approves a loopback download" (jam-spec lines 111, 1504).

---

## 1. Products

### 1.1 The keyboard itself: Arturia KeyLab 88 mk3

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Size and weight | 1295 x 323 x 113 mm, 15.7 kg | [Arturia store](https://www.arturia.com/store/keylab-88-mk3), [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm) | high |
| Keybed | Fatar TP/110 hammer action, 88 weighted keys with aftertouch | [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm) | high |
| Rear ports | USB-C (bus powered), DIN MIDI in and out, sustain, expression and two aux pedal inputs | [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm), [MusicTech review](https://musictech.com/reviews/controllers/arturia-keylab-88-mk3-review-midi-keyboard/), [Sound On Sound](https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii) | high |
| Lights | 12 lit pads and a 3.5" screen; no per-key lights | [Thomann](https://www.thomannmusic.com/arturia_keylab_88_mk3_black.htm) | high |
| Control layout | Screen in the middle, faders and knobs on the right, mode buttons on the left, all in a panel behind the keys | [MusicTech](https://musictech.com/reviews/controllers/arturia-keylab-88-mk3-review-midi-keyboard/), [MusicRadar](https://www.musicradar.com/music-tech/midi-controllers/delivers-streamlined-daw-integration-with-an-excellent-hammer-action-keyboard-arturia-keylab-88-mk3-review) | medium |
| Price | US$1,299 list | [Arturia store](https://www.arturia.com/store/keylab-88-mk3) | high |

**Will a strip fit?**
- **Width: fits.** A standard 88-key keyboard is about 123 cm long ([datagenetics](http://datagenetics.com/blog/may32016/index.html); octave span 164-165 mm per [quadibloc](http://www.quadibloc.com/other/cnv05.htm)). The chassis is 1295 mm, so a 1.22 m strip fits inside it with roughly 35 mm to spare at each end. *(low: arithmetic from the numbers above)*
- **Depth and height: unknown.** No source gives the depth or height of the flat strip between the back of the keys and the control panel. **Daniel needs to measure it** (open question 1).
  - The usual place is a thin aluminium channel on that lip, lighting the back of each key ([Yan Niznik's build](https://yanniznik.com/building-a-led-piano-visualizer/)).
  - Use removable mounting rather than permanent adhesive on a $1,299 controller *(low: my recommendation)*.
- **Routing MIDI to a standalone box: unverified.** The KeyLab's only USB port goes to the PC. A standalone light box would have to take MIDI from the 5-pin DIN Out.
  - Arturia documents a `DINTHRU` port for the **KeyLab Essential mk3**, which passes MIDI from the computer out through its 5-pin connector ([Arturia FAQ](https://support.arturia.com/hc/en-us/articles/8841900354076-KeyLab-Essential-mk3-General-Questions)).
  - I found no source saying whether the full KeyLab 88 mk3's DIN Out repeats the keybed, or whether it has a DINTHRU port (open question 2).

### 1.2 Commercial light bars

| Product | How it is driven | Can a PC address keys freely? | Colours | Latency | Coverage and mounting | Price |
|---|---|---|---|---|---|---|
| **Piano LED Plus** | Connects to the piano by USB-B or 5-pin MIDI; Bluetooth and Wi-Fi to its own app on iOS, Android, Mac and Windows ([pianoledshop](https://pianoledshop.com/products/pianoledplus), [en-us page](https://pianoledshop.com/en-us/products/pianoledplus)) | **Not documented.** The app plays imported MIDI files. An Amazon listing calls it "Synthesia ... Compatible" ([Amazon](https://www.amazon.com/Piano-LED-Plus-Transparent-LED-strip/dp/B0C5Y6MKRG)). No per-key API found. | White or black strip housing; the LED colour range is not stated | "Less than 20 milliseconds" (vendor claim) | Strip 123 x 1.3 x 0.4 cm, can be cut for 61 or 76 keys; self-adhesive. Aimed at digital pianos. | EUR 179 on sale (EUR 199 list) |
| **The ONE Piano Hi-Lite** | Key sensors plus Bluetooth 4.0 or micro-USB; its own app; works with MIDI apps including Synthesia ([Amazon](https://www.amazon.com/ONE-Music-Group-Beginners-TOH1/dp/B075XLPBQT), [Dr Techlove](https://www.drtechlove.com.au/product/the-one-hi-lite-learning-system-piano-88-key-led-light-for-piano-learning-beginner/)) | Only through apps that support its lights; no open per-key API found | **Red and blue only**, one LED per key (88) | not published | Sits on top of any standard 88-key keyboard; 48.3 x 0.9 x 0.8 in; needs mains power ([CoolThings](https://www.coolthings.com/the-one-piano-hi-lite-led-guide/)) | $179 in one article, date unclear (medium) |
| **I-piano LED Visualizer** (Etsy) | Sold as a finished strip for MIDI keyboards up to 88 keys, with Synthesia support ([Etsy listing](https://www.etsy.com/listing/1334255377/i-piano-led-visualizer-light-strip)) | Unverified: Etsy blocked the fetch, so the hardware and firmware inside are unknown | unverified | unverified | up to 88 keys | unverified |

**Verdict.** None of these documents free per-key RGB control from a PC. The Hi-Lite's two colours cannot carry pitch colour plus moonlight at all. Piano LED Plus might light notes it receives on its MIDI IN from the computer, but that is undocumented (open question 6). *(medium)*

### 1.3 Open-source kits (buy the parts, flash a ready-made project)

| Project | Hardware | MIDI input | PC control of each key | Notes | Source |
|---|---|---|---|---|---|
| **Piano LED Visualizer** (onlaj, MIT) | Raspberry Pi Zero WH or Zero 2 W; WS2812B "at least 1.5m with 144 diodes/meter"; 5 V 6 A supply; data pin GPIO 18 | USB MIDI, RTP-MIDI over the network (rtpMIDI on Windows), Bluetooth | **Partly.** It follows Synthesia's "Finger-based channel" key-light protocol: notes with velocity 1 on channels 1-12 light as guides, other velocities sound. A PC can light keys by sending that protocol, but colours are set per channel, not per message. | Web UI on port 80; key alignment settings (LED offset, shift, reverse, LED count); Pi models other than the Zero were reported to lag badly; about $75-100 in parts; v1.6 released 2 March 2025 (timestamp handling, gamma correction) | [README](https://raw.githubusercontent.com/onlaj/Piano-LED-Visualizer/master/README.md), [features.md](https://github.com/onlaj/Piano-LED-Visualizer/blob/master/Docs/features.md), [Synthesia setup](https://github.com/onlaj/Piano-LED-Visualizer/discussions/521), [releases](https://github.com/onlaj/Piano-LED-Visualizer/releases) |
| **PianoLux ESP32** (MIT) | ESP32-S2 or S3 (USB host); WS2812 at 144 or 72 per metre | USB host, rtpMIDI over Wi-Fi, Bluetooth (experimental), serial | Its own web UI (Chrome or Edge only); no documented external per-key API | Ten LED modes | [GitHub](https://github.com/serifpersia/pianolux-esp32) |
| **key_led / synthesia_key_led** (MIT) | Adafruit ItsyBitsy RP2040 as a USB MIDI device; 1 m WS2812 at 144 per metre | USB MIDI in Synthesia's finger-based protocol | Yes, over USB MIDI from any app, including a Web MIDI page. Colours are hard-coded (left hand blue, right hand green); editing the code changes them. | 1 LED per key by default ("too small"); an 88-key layout was not tested | [touchgadget/key_led](https://github.com/touchgadget/key_led), [heyudude fork](https://github.com/heyudude/synthesia_key_led) |
| **PianoLights** | ESP32 with WS2812B at 144 per metre, Bluetooth MIDI | Bluetooth MIDI | via Synthesia | | [mrichana/PianoLights](https://github.com/mrichana/PianoLights) |

### 1.4 Keyboards with lit keys: worth switching?

| Keyboard | Lights | Third-party control | Price | Worth it for a KeyLab 88 mk3 owner? |
|---|---|---|---|---|
| **NI Kontrol S88 MK3** | A "Light Guide" with RGB lights above each key ([Sweetwater](https://www.sweetwater.com/store/detail/KontS3-88--native-instruments-kontrol-s88-mk3-88-key-smart-keyboard-controller)) | Reverse-engineered, **macOS only**, through NI's hardware service socket. Working scripts date from March 2026, lights plus MIDI together from August 2026. Colours are an indexed palette, not free RGB ([KompleteSynthesia discussion #29](https://github.com/tillt/KompleteSynthesia/discussions/29)). The older SynthesiaKontrol tool supports MK1 and MK2 only ([GitHub](https://github.com/ojacques/SynthesiaKontrol)). | $1,299 | **No.** It costs the same as the KeyLab he already has, gives no Windows path, and limits colours to a palette. |
| **The ONE TOP1X / Smart Piano** | Lit keys "linked seamlessly with app" | App only; no PC API found | from $999 ([TheONE](https://theonemusic.com/products/stage-digital-piano-sp-nex-smart-keyboard-pro)) | No: a beginner smart piano. |
| **Casio LK-S450** | Key Lighting System, **61 keys** | Chordana Play app; USB-MIDI | about $200 class (price not verified) | No: 61 keys. |

**Verdict.** A strip keeps his Fatar hammer-action keybed and gives full RGB under PC control. No lit-key keyboard I found offers that on Windows. *(medium)*

---

## 2. Building one yourself

### 2.1 Strip geometry and matching LEDs to keys

- **Spacing.** 144 LEDs per metre puts one LED every **6.94 mm** (1000 / 144).
- **Key pitch.** A standard octave is 164-165 mm across 7 white keys, about **23.5 mm per white key**. The black keys are about 13.7 mm wide ([quadibloc](http://www.quadibloc.com/other/cnv05.htm), [datagenetics](http://datagenetics.com/blog/may32016/index.html)).
  - That is about 3.4 LEDs per white key.
  - The average semitone step is 165 / 12 = 13.75 mm, which is almost exactly two LEDs (13.89 mm).
- **Drift.** "Two LEDs per semitone" gains about 0.14 mm per step. Across the 87 steps from A0 to C8 that adds up to **about 12 mm, close to 2 LEDs and half a white key**. *(low: arithmetic)*
  - This is why Piano LED Visualizer ships with default LED offsets that skip one LED above notes 55 and 92 ([features.md](https://github.com/onlaj/Piano-LED-Visualizer/blob/master/Docs/features.md)).
- **Count.** 88 keys span about 1223 mm, which is about **176 LEDs**. That matches the project's "172 LEDs" example and its "at least 1.5m" buying advice (the spare length leaves room to trim).
- **Black keys.** The strip lies *behind* the keys, where the white-key tails and the black keys alternate at a nearly even spacing. So one strip position per semitone works for black keys too; they need no second row. *(low: geometry inference; the calibration below makes it true on his keybed)*
- **Proposed mapping: a calibration drill, not a formula.**
  1. The page sweeps a single lit LED along the strip.
  2. Daniel presses the key under it.
  3. The page records `midi → [led indices]` for all 88 keys (about 2 minutes), with a two-point fit (A0, C8) as a quick fallback.
  4. It stores a `reverse` flag and the per-key map in `state/arsenal/lights/map.json`.
  5. White keys get about 3 LEDs (centre plus two edges), black keys 2. The edge LEDs stand in for the page's rims.

### 2.2 Controllers

**ESP32 running WLED** (strongest fit)
- Receives realtime frames over UDP. Two options:
  - **DRGB / DNRGB** on port **21324**. Byte 0 is the protocol and byte 1 is a **timeout in seconds**, after which WLED returns to normal mode (255 means never). DRGB carries up to 490 LEDs; DNRGB up to 489 per packet with a start index ([WLED UDP realtime](https://kno.wled.ge/interfaces/udp-realtime/)).
  - **DDP** on port **4048** ([WLED DDP](https://kno.wled.ge/interfaces/ddp/)). Its header is at most 10 bytes, against E1.31's 126 ([coral blog, via search](https://blog.jonasbengtson.se/ddp-distributed-display-protocol)). LedFx defaults to DDP for WLED because it has "better latency" ([LedFx config](https://docs.ledfx.app/en/latest/configuring.html)). WLED ignores DDP timecodes.
  - The DDP flag and data-type bytes (push flag on the last packet of a frame, type `0x0B` for 8-bit RGB) come from secondary sources; the 3waylabs spec host refused the connection during this research ([elektroda](https://www.elektroda.com/news/news4040325.html)). *(medium)*
- **E1.31/sACN** is capped for DMX compatibility: 170 LEDs per universe, and no more than 3 universes (510 LEDs) for a steady 40 fps ([WLED E1.31](https://kno.wled.ge/interfaces/e1.31-dmx/)). DRGB and DDP suit a 176-LED strip better.
- **JSON API.** Individual LEDs can be set with `{"seg":{"i":[...]}}` over HTTP or a WebSocket at `ws://<ip>/ws` ([JSON API](https://kno.wled.ge/interfaces/json-api/), [WebSocket](https://kno.wled.ge/interfaces/websocket/)). This makes a zero-server prototype possible, but a JSON state update is not a realtime frame stream. *(medium)*
- **Serial.** Adalight and tpm2 over serial at 115200 baud, fine for about "50-100 LEDs"; faster rates are configurable ([WLED serial](https://kno.wled.ge/interfaces/serial/)). This is a wired path if Wi-Fi is poor.
- **Ready-made controller boards.**
  - The pre-assembled **QuinLED Dig-Uno** has a fuse, reverse-polarity protection and level shifters ([quinled.info](https://quinled.info/quinled-dig-uno/)).
  - **GLEDOPTO** sells ESP32 WLED controllers, including an Ethernet model with a fuse and level shifter, for about $26-48 ([Amazon](https://www.amazon.com/GLEDOPTO-Controller-Channel-Outputs-Ethernet/dp/B0G2RQBW9J); price from a search summary, medium).

**Raspberry Pi Zero 2 W with Piano LED Visualizer.** See 1.3. It is best as a standalone box that works with any app. Other colours only arrive through its Synthesia-style channel protocol or its own modes.

**Arduino-class USB-MIDI device** (RP2040, or ESP32-S3 with TinyUSB). The board shows up as a MIDI port, so a Web MIDI page can drive it directly.
- [ESP32USBMIDI example](https://github.com/esp32beans/ESP32USBMIDI), [Espressif USB device stack](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/usb_device.html).
- MIDI has no RGB note message, so colours would be a channel palette or SysEx. SysEx needs the page to request sysex permission ([MDN MIDIOutput.send](https://developer.mozilla.org/en-US/docs/Web/API/MIDIOutput/send)).
- Needs custom firmware.

### 2.3 Power and safety

- **5 V only.** "using power supply with more Volt WILL damage both LED strip and Raspberry Pi" ([PLV README](https://raw.githubusercontent.com/onlaj/Piano-LED-Visualizer/master/README.md)). Feed the strip's +5 V from the supply, never from the controller board, and join the grounds.
- **Current.**
  - About 60 mA per LED at full white ([Zaitronics](https://zaitronics.com.au/blogs/guides/ws2812b-led-power-requirements-rgb-strips-rings-matrices)). 144 per metre draws about 25-29 W per metre at most ([BTF-LIGHTING](https://www.btf-lighting.com/products/ws2812b-led-pixel-strip-30-60-74-96-100-144-pixels-leds-m), Zaitronics).
  - 176 LEDs at full white would be about **10.6 A** (worst case) *(low: arithmetic)*.
  - Real use (a chord of up to 10 keys, 2-3 LEDs each, coloured) is far lower. The project's example is "5V 6A is enough to light 172 LEDs @50% power".
  - Use a **UL-listed 5 V 6-10 A supply** and set WLED's **Auto Brightness Limiter** "slightly below the rating of your power supply" ([WLED FAQ](https://kno.wled.ge/basics/faq/)).
- **Protecting the strip.** Per [Adafruit NeoPixel best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide (Best Practices page)):
  - a 500-1000 µF capacitor across the supply;
  - a 300-500 Ω resistor on the data line, at the strip end;
  - a **level shifter** (74AHCT125 or 74HCT245) from a 3.3 V ESP32 or Pi to the 5 V strip. The pre-assembled Dig-Uno and GLEDOPTO boards include one.
- **Wiring.** 22-18 AWG ([PLV README](https://raw.githubusercontent.com/onlaj/Piano-LED-Visualizer/master/README.md)). Voltage drop needs injection on runs over 1-2 m ([Zaitronics](https://zaitronics.com.au/blogs/guides/ws2812b-led-power-requirements-rgb-strips-rings-matrices)); a 1.22 m strip is borderline, so feeding both ends is cheap insurance.
- **Enclosure.** Keep the mains side of the supply enclosed. Choose a fused controller. *(low: standard practice)*

### 2.4 Diffusers and looks on camera

- A bare strip looks "harsh". An aluminium profile with a diffuser gives a "professional stage-like glow" ([Yan Niznik](https://yanniznik.com/building-a-led-piano-visualizer/)). BTF's 144-per-metre strip is 12 mm wide ([BTF-LIGHTING](https://www.btf-lighting.com/products/ws2812b-led-pixel-strip-30-60-74-96-100-144-pixels-leds-m)), so it needs a channel with an inner width of at least 12 mm.
- A black PCB disappears against the black KeyLab.
- **For TikTok:** keep brightness low so the phone camera does not clip, and test for rolling-shutter banding from LED dimming before a real shoot *(low: unverified, needs a test clip)*.

### 2.5 Latency budget

Two kinds of light have different budgets:
1. **Daniel's own notes** must feel instant.
2. **Claude's cues, ghosts, Try targets and suggestions** are known ahead of time. The server can send them on schedule, so their latency is a scheduling problem, not a transport problem.

| Stage | Estimate | Basis |
|---|---|---|
| Keybed → USB → Chrome Web MIDI event | a few ms (unmeasured) | *low* |
| Page → arsenal server on localhost | about 1-2 ms per HTTP POST on keep-alive (unmeasured) | *low* |
| Server → ESP32 over Wi-Fi (UDP) | variable, from a few ms up to a stutter; Ethernet is steadiest | "extremely latency sensitive and will expose weaknesses in your WiFi network" ([LedFx network](https://docs.ledfx.app/en/latest/troubleshoot/network.html)); disable Wi-Fi sleep, use Ethernet for best results ([WLED FAQ](https://kno.wled.ge/basics/faq/), [E1.31 page](https://kno.wled.ge/interfaces/e1.31-dmx/)) |
| Strip data write | about 5.3 ms for 176 LEDs (24 bits at 800 kbps, about 30 µs per LED) | [WS2812B datasheet](https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf) |
| **Target for his notes** | **≤ 20 ms from key press to light** | matches the commercial claim of "less than 20 milliseconds" ([pianoledshop](https://pianoledshop.com/en-us/products/pianoledplus)); in some experiments people detect audio-visual offsets as small as 20 ms, and musicians judge synchrony better than most ([arXiv 2212.01686](https://arxiv.org/pdf/2212.01686), [PMC4451240](https://pmc.ncbi.nlm.nih.gov/articles/PMC4451240/)) |

**Receipt drill.** Under our drill doctrine this path is presumed broken until measured. Film a key press and the strip together in 240 fps slow motion, count frames from key-down to light-on (about 4.2 ms per frame), and file the dated figure. Do this before claiming any latency.

---

## 3. Integration with our stack

### Path A: arsenal composes frames and streams UDP (DRGB or DDP) to WLED (recommended)

```
KeyLab --USB--> Chrome page (Web MIDI) --state diffs (POST)--> arsenal serve.py
                                                                 |  already knows Claude's cues
                                                                 v
                                            lights compositor (60 Hz only while anything is lit)
                                                                 |  UDP DRGB :21324 (timeout 2 s)
                                                                 v
                                                  ESP32 + WLED --> 176-LED strip
```

- **What the page sends.** Low-rate *state*, not frames:
  - `his: {midi, vel, down|pedal-held|off}`;
  - `ghost: {notes, state: target|incoming|hold|found}`;
  - `suggest: {notes, strength}`;
  - `try: {target_notes}`.
  - Claude's own cue notes the server already holds, so they need no round trip through the page.
- **Who composes.** The server builds the 176 RGB values with one layer order and a brightness budget.
- **Protocol.** DRGB's **per-packet timeout byte** is a built-in failsafe: if arsenal dies, WLED leaves realtime mode after 2 s instead of freezing on stuck notes. Set WLED's normal-mode preset to off or a dim idle. DDP is the alternative if we want LedFx-standard framing.
- **Installs.** None on the PC: the stdlib `socket` sends UDP. The browser cannot send UDP itself. Standard pages are limited to HTTP, WebSocket and WebRTC; raw UDP needs Chrome's Direct Sockets API, which is limited to Isolated Web Apps ([Chrome Direct Sockets](https://developer.chrome.com/docs/iwa/direct-sockets)). So the server sends.
- **Good:** any colour on any key, every page layer, Claude's cues light even from a background tab, and one frame buffer the page can also draw.
- **Bad:** Wi-Fi jitter (choose an Ethernet board, or check signal at the piano), a new always-on sender to supervise, and the ESP32 must be bought and flashed.
- **Needs Daniel's OK for:** buying the strip, a 5 V supply, an ESP32 WLED controller and an aluminium diffuser channel; flashing WLED firmware (a download).

**Light grammar sketch.** This maps jam-spec 8.5 onto LEDs. Rims map to edge LEDs, and "size" pulses map to spreading onto neighbouring LEDs.

| Layer | On the strip |
|---|---|
| Daniel, key down | `noteColor(midi, vel)` pitch colour on all of the key's LEDs; velocity sets brightness |
| Daniel, held by the pedal | same hue at about 35% (his pedalled harmony stays visible after his hand lifts) |
| Claude's hand | moonlight `#C8DCFF`, at most 0.75 of Daniel's brightness for the same velocity, never pitch-tinted |
| Both on one key | Daniel's colour in the centre, moonlight on one edge LED (the "thin moonlight rim") |
| Ghost `target` | dim moonlight breathing at 0.5 Hz |
| Ghost `incoming` | moonlight on edge LEDs only |
| Ghost `hold` | steady dim moonlight on the centre LED |
| `found` | one 200 ms spread onto neighbouring LEDs, never brighter (the spec's "size, never brightness") |
| Chord suggestion | a dim moonlight layer on the suggested voicing, shown only after he has held a chord for a while or asked (courtesy rules, like remote ghosts waiting). The dwell time and alternatives are for the suggestion design to decide. |
| Budget | global cap plus WLED's current limiter |

Pitch colour stays his alone (C12). Nothing the lights draw ever feeds `detect()`, the log or rarity (INT 1).

**A zero-purchase first step.** Draw the 176-LED frame as a thin "virtual strip" bar on the page from the same compositor. Daniel can judge the grammar with no hardware, and the frame later ships to WLED unchanged. *(low: design proposal)*

**Sender sketch** (design only; not placed in `arsenal/`):

```python
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def send_drgb(host, rgb_bytes, timeout_s=2):          # rgb_bytes: 176*3 bytes, strip order
    sock.sendto(bytes([2, timeout_s]) + rgb_bytes, (host, 21324))   # DRGB, max 490 LEDs
```

### Path B: the page's Web MIDI output drives a USB-MIDI LED board

- **How it works.** The page already opens Web MIDI output ports (`cues.js`). A USB-MIDI board (RP2040 `key_led`, or an ESP32-S3 with TinyUSB) appears as a port. `localhost` counts as a secure context, so Web MIDI works over plain `http://localhost` ([MDN secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts)).
- **Good:** wired, with no Wi-Fi jitter; no server change; `MIDIOutput.send(data, timestamp)` can schedule ghosts ahead ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MIDIOutput/send)).
- **Bad:**
  - Colour must be encoded as a channel palette, or SysEx with sysex permission.
  - It needs custom firmware and an IDE install.
  - Lights stop when no page tab holds the port.
  - It adds the MIDI-echo risk the jam spec already guards against (jam-spec line 100). The LED port must never appear as a MIDI *input* the page ranks.
- **Needs:** a board and strip purchase; Arduino IDE or CircuitPython install.

### Path C: the lights read MIDI themselves (standalone box, the page optional)

- **How it works.** Piano LED Visualizer or PianoLux lights Daniel's notes from MIDI with no page involved, so it also works while he plays straight into FL Studio. Getting MIDI to the box is the snag:
  - **Through the KeyLab's DIN Out**, if it repeats the keybed. Unverified (open question 2); it may also need a DIN-to-USB interface (the PLV author uses an iConnectivity mio).
  - **From the PC over rtpMIDI.** That needs the rtpMIDI install on Windows ([features.md](https://github.com/onlaj/Piano-LED-Visualizer/blob/master/Docs/features.md)).
- **Page layers.** The page could show ghosts and Try targets by sending Synthesia finger-based guide notes (velocity 1, channels 1-12) to that port. Colours would be per channel, so moonlight is possible but pitch-colour-per-note is not.
- **Windows 11 now has multi-client MIDI ports and built-in loopback.** WebMIDI pages can use loopback endpoints "without any additional drivers or installs". *Creating* custom loopbacks needs the separate "Windows MIDI Services Tools download", rolling out in phases ([Windows blog, 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/)).
  - This lowers the cost of Path C and of the jam spec's v2 MIDI out.
  - Whether Daniel's machine already has it is unverified. The "Windows updates blocked" security posture suggests it may not (open question 7).
- **Good:** works in FL Studio with the page closed; mature projects; web UIs.
- **Bad:** no free RGB per note from our layers; one more box to power and keep on the network; DIN or rtpMIDI routing still to prove; Pi models other than the Zero lag.
- **Needs:** a Pi Zero 2 W, strip and supply purchase (plus a MIDI interface); an OS image download; an rtpMIDI install on the PC.

### Path D: the vendor app (Piano LED Plus or Hi-Lite)

Plug it in and follow the app's songs. It cannot show the page's chords, Claude or suggestions (no documented API). **Needs:** a purchase and a phone or PC app install.

---

## 4. Recommendations

| | **Budget** | **Best DIY (recommended)** | **Plug-and-play** |
|---|---|---|---|
| What | Bare ESP32 dev board + 74AHCT125 level shifter + 2 m WS2812B at 144 per metre (black PCB) + UL 5 V 6-10 A supply + capacitor and resistor + aluminium diffuser channel; WLED; **Path A** | Pre-assembled WLED controller with fuse and level shifter, **with Ethernet** (QuinLED Dig-Uno pre-assembled, or a GLEDOPTO Ethernet model) + the same strip, supply and diffuser, fed from both ends; **Path A**; calibration drill; latency receipt | **Piano LED Plus** (EUR 179-199), on the KeyLab's DIN MIDI if that carries the keybed, or a ready-made Piano LED Visualizer box (the Etsy I-piano) if Daniel mainly wants his own notes lit in any app |
| Rough cost | about $50-80 in parts *(low: estimate; retail prices not verified)*; PLV's comparable parts list is quoted at $75-100 | about $90-150 *(low: estimate)*; GLEDOPTO controllers were listed at about $26-48 *(medium)* | EUR 179-199 *(high, vendor page)* |
| Shows pitch colour, moonlight, ghosts, Try, suggestions | yes, all | yes, all | **no.** The vendor app's own lessons only; a PLV box gets Synthesia-style guide colours per channel |
| Latency | Wi-Fi dependent; must be measured | steadiest (Ethernet, plus the DRGB timeout failsafe) | "less than 20 ms" claimed |
| Honest trade-offs | soldering and wiring a 5 V, 6-10 A supply; you own the safety; Wi-Fi jitter | costs more; still a DIY mount on a $1,299 controller (lip depth unmeasured); an Ethernet cable to the piano | cannot follow Claude or the jam space; routing from the KeyLab unproven; lock-in to an app or subscription (5,000+ tracks behind a paid tier) |
| Purchases, downloads, installs (all need Daniel's OK) | parts purchase; WLED firmware flash | parts purchase; WLED firmware (often pre-flashed on these boards) | device purchase; app install; possibly a MIDI cable |

**My pick: the Best DIY option on Path A.** It is the only one where the keys speak the same visual language as the page: his pitch colours, and Claude's moonlight ghosts for chord suggestions and Try targets. It needs no software install on the PC, and its failsafe is built into the protocol. Suggested order:
1. Build the virtual strip on the page, with no purchase.
2. Daniel measures the KeyLab's lip.
3. Buy the parts after his OK.
4. Run the calibration drill.
5. Take the 240 fps latency receipt.

**Not recommended:** buying a lit-key keyboard (the S88 MK3 has no Windows light path; the others are beginner or 61-key instruments), and the Hi-Lite (red and blue only).

---

## 5. Open questions

1. How deep and how tall is the flat surface between the back of the KeyLab 88 mk3's keys and its control panel? Can a 12 mm strip in a diffuser channel sit there without touching the keys or the faders? (No source found; measure with a ruler.)
2. Does the KeyLab 88 mk3's 5-pin MIDI Out carry the keybed's notes while it is on USB, and does it have a `DINTHRU` port like the Essential mk3? This decides Path C and the plug-and-play routing.
3. Is Wi-Fi good at the piano (WLED advice: an RSSI of -70 dB or worse performs poorly), or can an Ethernet cable reach it?
4. Does Daniel want lights visible in his TikTok shots, where brightness, banding and a diffuser matter, or subtle lights for practice?
5. When should chord suggestions light up (held-chord dwell, a pad press, Try mode only)? This must be agreed with the suggestion design so the lights never tell him what to play uninvited.
6. Does Piano LED Plus light notes received on its MIDI IN from a computer outside its app? It is undocumented; ask the vendor before buying.
7. Is Windows MIDI Services already enabled on this machine, given that Windows updates are blocked? This affects Path C and the jam spec's v2 loopback.
8. Retail prices for the strip, supply, channel and boards were not verified from shop pages (the searches did not show prices). Re-check at purchase time.
