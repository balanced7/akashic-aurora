# FL jam bridge: local machine inventory (read-only)

- **Lane:** local inventory for the FL jam bridge (Claude plays bass, drums and chords inside FL Studio while Daniel improvises on the KeyLab 88 mk3)
- **Taken:** 2026-09-14, early hours, on DESKTOP-5886HDP
- **Method:** read-only PowerShell: uninstall registry keys, `HKLM/HKCU\SOFTWARE\Image-Line`, folder listings, `Get-PnpDevice`, `Get-Service`, `Get-AppxPackage`, `py -0p`, `pip list`. Nothing was installed, downloaded, launched or changed. No GUI app was opened. Chrome's version came from the registry (`HKCU\Software\Google\Chrome\BLBeacon`), not from running `chrome.exe`.
- **Heads-up:** FL Studio was **running** during the inventory (one `FL64` process and five `ilbridge` processes). Nothing touched it. The newest autosave is `Worship Grandeur Piano (autosaved on 9-14-2026 at 1h32).flp`.
- **Labels:** every line without a URL is a local observation made on this date. Lines tagged *(inference)* are my reading of those observations. External claims link to their source, with how current the source is.

---

## 1. Summary for the bridge designer

| Question | Answer (local, 2026-09-14) |
|---|---|
| Which FL Studio is active? | **FL Studio 2026, version 26.1.3.5570** (`FL64.exe` file date 2026-07-24). `HKLM\SOFTWARE\Image-Line\Shared\Paths` points at it. FL Studio 2025 (25.2.5.5319) is still installed beside it. |
| Can FL run Python scripts? | Yes. Both installs ship their own **Python 3.12.1** (`Shared\Python\python312.dll`). Nothing extra needs installing. |
| Are there custom FL scripts yet? | No MIDI controller scripts of our own. The user folders `Piano roll scripts`, `FL Studio Remote Scripts` and `Audio scripts` are **empty**. `Settings\Hardware` only holds vendor scripts (Arturia, Akai Fire, Novation, NI, Mackie, SSL, Korg). |
| KeyLab 88 mk3 in FL | The DAW port uses Arturia's **"KeyLab mk3"** script. The MIDI port uses **"KeyLab mk3 Arturia dev"** (forwards CCs to port 10). Both are enabled. |
| Virtual MIDI cable (app to FL) | **None usable yet.** loopMIDI, rtpMIDI and Tobias Erichsen software are absent. The built-in Windows MIDI Services service (`midisrv`) is running with its Loopback and Virtual transports enabled. But the **SDK Runtime and Tools** (MIDI Settings app, MIDI Console) are **not installed**, and no user loopback endpoints exist. The only loopbacks are the diagnostic "Service Test Loopback A/B". |
| Audio interface | **Focusrite Scarlett 2i2 4th Gen**, Focusrite driver 4.150.0.432, Focusrite Control 2. FL output is **Focusrite USB ASIO at 48 kHz**. |
| Instruments for the jam | Bass: Kontakt 8 with DjinnBass, DjinnBass II and Nolly Bass Library; Serum 2; Arturia Mini V4; FL Transistor Bass and BooBass. Drums: **Addictive Drums 2**, FPC, Nimble Kick, FL Drumaxx, Splice and Cymatics one-shots. Keys: many Kontakt pianos, Arturia Piano V3 and Stage-73 V2, FL Keys. |
| Splice | The **Splice desktop app is installed** as an MSIX package (v5.4.12.0). **Splice Bridge** (VST3) and **Splice INSTRUMENT** (VST3) are installed. Samples live in `C:\Users\L5\Documents\Splice\Samples\packs`: 81 WAVs, about 106 MB, in 40+ pack folders. |
| Plugin build toolchain | **Not present:** no Visual Studio or Build Tools (no `cl`, `msbuild`, `vswhere`), no CMake, Ninja, Rust/cargo, LLVM/clang or JUCE. **Present:** Windows SDK 10.0.26100 headers and libs, Git 2.53, Node 24.14.1, Python 3.11.9 (the pinned default) and 3.14.7, .NET runtimes (no .NET SDK). |
| OS | **Windows 11 Pro 25H2, build 26200.9168**, 64-bit. Ryzen 9 9950X3D (16 cores, 32 threads), 61.6 GB RAM. |

*(inference)* The cheapest path needs **no new install**: an FL MIDI controller script, using FL's bundled Python 3.12, reads a small command file or socket written by the arsenal server and writes notes and patterns inside FL. Whether FL's embedded interpreter allows sockets or file I/O is covered by the sibling lanes, not verified here. Every path that sends MIDI from outside into FL needs a virtual port. The zero-download option there is Windows MIDI Services loopbacks, which still need the SDK Runtime and Tools installer. That is a download, so it needs Daniel's OK. A VST3/CLAP plugin path needs a C++ or Rust toolchain installed first. Nothing for that exists today.

---

## 2. Operating system and hardware

- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion`: DisplayVersion **25H2**, CurrentBuild **26200**, UBR **9168**, EditionID Professional.
  - The registry `ProductName` still reads "Windows 10 Pro". That is a well-known legacy string. `Win32_OperatingSystem` reports **Microsoft Windows 11 Pro 10.0.26200**.
- CPU: AMD Ryzen 9 9950X3D, 16 cores / 32 logical processors. RAM: 61.6 GB.
- Free space: C: 309 GB, D: 374 GB, E: 627 GB, F: 852 GB. X: is the 1 GB ramdisk, scratch only.
- WSL distros registered (read from `HKCU\...\Lxss`, `wsl.exe` not run): Ubuntu, Ubuntu-24.04, Ubuntu-Migrate, docker-desktop. Docker Desktop 4.84.0 is installed.
- Browsers: Google Chrome **152.0.7977.83** (registry), Edge 153.0.4234.32, Brave 153.1.95.101. WebView2 Runtime 153.0.4234.32.

## 3. FL Studio

### 3.1 Installs

| Item | Version | Location |
|---|---|---|
| FL Studio 2026 | 26.1.3.5570 | `C:\Program Files\Image-Line\FL Studio 2026\` (`FL64.exe`, `FL64 (scaled).exe`) |
| FL Studio 2025 | 25.2.5.5319 | `C:\Program Files\Image-Line\FL Studio 2025\` |
| FL Studio ASIO | none listed | `C:\Program Files\Image-Line\FL Studio ASIO\` |
| FL Cloud Plugins | 2.0.3 | `C:\Program Files\FL Cloud Plugins\` |

- The uninstall keys `FL Studio 2025` and `FL Studio 2026` carry DisplayVersion but no InstallLocation. `UninstallString` and `DisplayIcon` give the folder.
- `HKLM\SOFTWARE\Image-Line\Shared\Paths`:
  - `Install path` = FL Studio 2026
  - `FL Studio engine` = `FLEngine_x64.dll`
  - `VST plugins` = `C:\Program Files\Common Files\VST2`
- `HKLM\SOFTWARE\Image-Line\Registrations` has subkeys for every major version from FL 9 to 25.2. There is no "FL Studio 26.x" subkey. I did not read the key values.
- `HKCU\SOFTWARE\Image-Line` has `FL Studio 25`, `FL Studio 26`, `FL Plugin Scanner`, `ASIO` and `Shared`.

### 3.2 Bits inside the FL 2026 install that matter for a bridge

- `Shared\Python\`: embedded **Python 3.12.1**. It includes `python312.dll`, `python312.zip`, `python312._pth`, `_socket.pyd`, `select.pyd`, `_asyncio.pyd`, `_overlapped.pyd`, `_ctypes.pyd`, `_ssl.pyd` and `_multiprocessing.pyd`. FL 2025 ships the same set.
  - *(inference)* The socket and asyncio extension modules are on disk. Whether FL's script sandbox lets a device script import them is an open question for the API lane.
- External docs lag behind this. The community "FL Studio MIDI Scripting 101" page still says FL's interpreter is based on Python 3.9 ([flmidi-101, undated, older](https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html)). **Trust the local 3.12.1 file version for FL 26.1.**
- `Shared\`:
  - `ILMinihostBridge64.exe` and `ILPluginScanner64.exe`
  - `ILRemoteServer_x64.dll` (FL Studio Remote)
  - `beat_tracker.dll`, `elastique_x64.dll` (time-stretch), `REX Shared Library_x64.dll`
  - `Shared\ffmpeg\x64` (FL's own ffmpeg)
- `System\Hardware specific\`: about 30 bundled controller scripts, including `Forward CCs to current plugin Port 10` and Novation Launchkey. No Arturia entry is bundled there; Arturia's scripts live in the user Hardware folder (3.3).
- Scripts that ship with FL:
  - `System\Config\Piano roll scripts\`: Arpeggiator, Euclidean, Humanize, Note repeater sprinkler, Select by velocity and more
  - `System\Tools\Chord progression\`: `cpt.pyscript`, `stack.pyscript`
  - `System\Config\FL Studio Remote Scripts\`: `filleach`, `flrInit`, `rerollLSloop`, `rerollLSsample`, `rerollLSsteps`
  - `System\Config\Audio scripts\`: Edison-style generators and FX
  - *(inference)* The `rerollLS*` names look like Loop Starter reroll hooks. They could be a model for "regenerate the drum loop" commands.
- `Plugins\VST` is empty. The FL-as-plugin DLLs `FL Studio VSTi.dll` and `FL Studio VSTi (Multi).dll` sit in `C:\Program Files\Common Files\VST2`.

### 3.3 FL user data: `C:\Users\L5\Documents\Image-Line\FL Studio`

Documents is **not** redirected to OneDrive (`User Shell Folders\Personal` = `C:\Users\L5\Documents`).

- **`Settings\Hardware`** (MIDI controller scripts) has 14 folders: Akai FL Studio Fire, Arturia KeyLab Essential, Arturia KeyLab Essential mk3, **Arturia KeyLab mk3**, Arturia KeyLab MKII, Arturia MiniLab 3, Arturia MiniLab 37, Arturia MiniLab MKII, KORG Keystage, MackieCU, NI Komplete Kontrol, Novation, SMK-37 Elite, Solid State Logic. Each has a small `.ini` beside it.
  - `Arturia KeyLab mk3\` holds Arturia's script, files dated 2025-10-30:
    - `device_KL3.py`: first line `# name=KeyLab mk3`, header "Surface: KeyLab mk3, Version 1.1". Its `supportedHardwareIds` lines up with the KeyLab 88 mk3 DAW port ID (see 3.4).
    - `device_KeyLab mk3 MIDI.py`: `# name=KeyLab mk3 Arturia dev`. It forwards CCs to port 10 so Arturia software can react.
    - Also `KL3Process.py`, `KL3Plugin.py`, `KL3Return.py`, `KL3Display.py`, `KL3Navigation.py` and the rest, plus Arturia's PDF `KeyLab_mk3__1_0__2024_08_27__FL_Studio__DAW_User_Guide.pdf`.
  - `Akai FL Studio Fire\device_Fire.py` (130 KB, 2026-08-05) and `harmonicScales.py`. *(inference)* This is a big real-world example of a script that drives the step sequencer and pattern playback.
- **`Settings\Piano roll scripts`**: empty. The user has no piano roll scripts.
- **`Settings\FL Studio Remote Scripts`** and **`Settings\Audio scripts`**: empty.
- `Settings\Browser` was modified 2026-09-13. `Settings\Note name presets` was modified 2026-08-09.
- **Projects:** 914 `.flp` files under `Projects\`, autosave backups included. The newest is the "Worship Grandeur Piano" project, autosaved 2026-09-14 01:32.
- Sibling plugin preset folders under `Documents\Image-Line\`: Autogun, BassDrum, DirectWave, Drumaxx, FPC, FLEX, Gross Beat, Harmor, Sytrus, Slicex, Newtime, Newtone, ZGameEditor Visualizer and others.
- `HKCU\...\FL Studio 26\Search paths` (browser extra folders):
  - `0` = a project folder (`Projects\Providence Citi Worship Remix\Providence (Oleg)\`)
  - `1` = `E:\Sample Packs\`, which **does not exist on disk**
  - *(inference)* The Splice folder is not in FL's browser search paths. Adding it would be a settings change, so ask Daniel first.

### 3.4 FL 2026 MIDI settings (`HKCU\SOFTWARE\Image-Line\FL Studio 26\Devices`)

MIDI inputs FL remembers:

| Input name | Enabled | Controller script (`ScriptFolder`) | Port | Hardware ID / note |
|---|---|---|---|---|
| **KeyLab 88 mk3 MIDI** | 1 | **KeyLab mk3 Arturia dev** | **0** | `00 20 6B 02 00 0A 08 3C 01 01 01`, ConnectionCounter 585 |
| **KeyLab 88 mk3 DAW** | 1 | **KeyLab mk3** | 236 | `00 20 6B 02 00 0A 08 7F 7F 7F 7F`, ConnectionCounter 73 |
| FLkey MIDI | 1 | Novation FLkey 61 MIDI | 236 | Linked to output "FLkey MIDI" |
| MIDIIN2 (FLkey MIDI) | 1 | Novation FLkey 61 DAW | 237 | none |
| KeyLab mkII 88 / MIDIIN2 (KeyLab mkII 88) | 1 | none / KeyLab mk3 Arturia | -1 | Old device |
| Focusrite USB MIDI | **0** | none | -1 | Disabled |
| CHMidi-2.3, "USB Midi " | 1 | none | -1 | Devices not present now |

- MIDI outputs remembered: KeyLab 88 mk3 MIDI (port 0), KeyLab 88 mk3 DAW (236), FLkey MIDI (236), MIDIOUT2 (FLkey MIDI) (237, **Sync=1**), Microsoft GS Wavetable Synth, Microsoft MIDI Mapper and older devices. None sends clock except the FLkey DAW output.
- Audio output: `Device name` = "Focusrite USB ASIO", `Sample rate` = 48000. The FL Studio ASIO setting (`HKCU\...\Image-Line\ASIO`) is `bufferSize` 256.
- *(inference)* A bridge MIDI input, such as a loopback endpoint, would show up here as a new entry. It could use the "(generic controller)" type with its own port number, so FL routes it to the channel whose MIDI input port matches. It could also use our own `device_*.py` script.

## 4. Plugins

### 4.1 Plugin folders

| Folder | State | Contents |
|---|---|---|
| `C:\Program Files\Common Files\VST3` | present | See 4.2 |
| `C:\Program Files\Common Files\VST2` | present, **FL's configured VST2 path** | FL Studio VSTi.dll, FL Studio VSTi (Multi).dll, Arturia Augmented STRINGS / Mini V4 / Piano V3 / Rev PLATE-140 .dll, D-Stortion, Eos.dll |
| `C:\Program Files\VSTPlugins` | present | Analog Lab V.dll, Piano V3.dll, Stage-73 V2.dll, Rev PLATE-140.dll, DeltaModulator_x64.dll, MeldaProduction\, Neural DSP\ |
| `C:\Program Files\Steinberg\VSTPlugins` | present, empty | none |
| `C:\Program Files\Common Files\CLAP` | **absent** | No CLAP plugins installed |
| `%LOCALAPPDATA%\Programs\Common\VST3` / `CLAP` | absent | none |
| `HKLM\SOFTWARE\VST` (VSTPluginsPath) | no values | none |

### 4.2 VST3 folder (notable)

- **Instruments:**
  - `Kontakt 8.vst3` (a stale `Kontakt 8.vst3.BAK` also sits beside it)
  - `Addictive Drums 2.vst3` (inside `XLN Audio\`)
  - `Serum2.vst3`, `Nexus.vst3`, `SynthMaster3.vst3`
  - Arturia: `Analog Lab V.vst3`, `Mini V4.vst3`, `Piano V3.vst3`, `Stage-73 V2.vst3`, `Augmented STRINGS.vst3`
  - `NimbleKick.vst3`
  - Cymatics: Origin, Pandora, Pluto, Quake, Shockwave, Ocean Pluck, Omnivox, Voxity, Vortex, Space, Memory, Illusion, Diablo, Deja Vu, Dark Sky, Corrosion
  - `Splice\Splice INSTRUMENT.vst3`
- **Splice:** `SpliceBridge.vst3` (file date 2025-01-16).
- **Effects:** `OTT.vst3`, `Rev PLATE-140.vst3`, Kilohearts (about 35 "kHs" snap-ins), iZotope `Trash.vst3`, Baby Audio `Smooth Operator Pro.vst3`, MeldaProduction, Neural DSP.

### 4.3 What FL has actually scanned as generators

From `Presets\Plugin database\Installed\Generators`:

- **Third-party:** Addictive Drums 2, Analog Lab V, Augmented STRINGS, Cymatics Ocean Pluck / Pandora / Quake / Shockwave, **Kontakt 8**, Mini V4, Nexus, Nimble Kick, Piano V3, **Serum 2**, **Splice Bridge**, **Splice INSTRUMENT**, Stage-73 V2, SynthMaster 3, FL Studio VSTi (multi).
- **FL native, useful for the jam:** FPC, Drumaxx, Fruit Kick, BooBass, **Transistor Bass**, FL Keys, Sytrus, Harmor, Kepler / Kepler Exo, Slicex, Fruity Slicer, DirectWave, Sakura, **MIDI Out**, **Patcher**, Fruity Keyboard Controller, Dashboard.

### 4.4 Kontakt 8 and libraries

- **Native Instruments Kontakt 8**, version **8.12.1.0**. The install is `C:\Program Files\Native Instruments\Kontakt 8`, with standalone `Kontakt 8.exe` 8.12.1. `ContentDir` is `C:\Program Files\Common Files\Native Instruments\Kontakt 8`.
- The Native Access app was **not found** in `Program Files\Native Instruments`. Only `Public\Documents\Native Instruments\Native Access\ras3` exists.
- A Start Menu folder "Kontakt 5 PORTABLE" exists but is empty.
- Libraries registered under `HKLM\SOFTWARE\Native Instruments`, with their `ContentDir`:
  - **Bass:** *DjinnBass* (`D:\Libraries\Submission Audio DjinnBass`), *DjinnBass II* (`D:\Libraries\SubMission Audio DjinnBass II`), *The Nolly Bass Library* (`D:\Libraries\GetGood Drums The Nolly Bass Library`).
  - **Keys:** Neo-Soul Keys, Session Keys Electric S, Ultimate Stage Pianos, Chroma (Sonuscore), Spotlight Piano, The Grandeur, The Giant, Teletone Audio (Golden Age Grand, Le Gibet, Ondine, Scarbo, Tympo).
  - **Other:** Ashlight, Lores, Fables, Lumina (ProjectSAM), LA Scoring Strings 3, Albion Solstice, Adagietto, Fluid Brass, Aspire, Vocalise 3, Voices of Rapture, Evolution Django Jazz, Shreddage II, reFX NEXUS (NKS). Arturia NKS preset entries are registered too.
- Library roots: `D:\Libraries`, `F:\Libraries`, `D:\Cymatics Samples` (Cymatics 10-Year Anniversary packs). `D:\Other Libraries` is empty.
- **Licensing note** *(neutral, relevant to reliability)*: a few library folder names carry release-group tags, for example `...KONTAKT-MAGNETRiXX` and `...KONTAKT-DECiBEL`. The Nexus and SynthMaster uninstall entries list "Team V.R" as publisher. *(inference)* Such builds can behave differently when hosted or automated. The bridge should default to instruments with plain vendor installs: Kontakt 8 core, Addictive Drums 2, Serum 2, Arturia, FL native.

### 4.5 Other music software

- Arturia Software Center 2.12.0, **Arturia USB MIDI Driver 1.7.0**, **MIDI Control Center 1.23.0** (KeyLab configuration).
- XLN Audio Addictive Drums 2, version **2.3.5.4**. It is activated (an `Activation` value exists under `HKCU\SOFTWARE\XLN Audio\Addictive Drums 2`). I did not locate its content folder: `Public\Documents\XLN Audio` is absent.
- Xfer Serum 2 **2.1.4**, OTT; Neural DSP Archetypes (guitar); iZotope Trash 1.3.0; Baby Audio Smooth Operator Pro 1.2; MeldaProduction MPluginManager 02.29.
- Audacity 3.7.8, MusicBee, Ultimate Vocal Remover 5.6.0, MuseHub 2.8.1, Equalizer APO 1.4.2, LatencyMon 7.31.

## 5. Splice

| Item | Local evidence |
|---|---|
| **Splice desktop app** | MSIX / Store-style package `Splice` **5.4.12.0**, developer-signed, at `C:\Program Files\WindowsApps\Splice_5.4.12.0_x64__xpwcknj9p1bc6`. Package data is in `%LOCALAPPDATA%\Packages\Splice_xpwcknj9p1bc6`. Electron-style app state is in `%LOCALAPPDATA%\SpliceSettings` (`appState.json` 2026-09-12, `port.conf`, `license\`, `logs\` 2026-09-11). It has **no** classic uninstall key. A temp folder `Splice_5.4.10.0_x64__...` shows it updated recently. |
| **Splice Bridge** | Uninstall entry "Splice Bridge v5.1.1" (2025-09-29). `C:\Program Files\Common Files\VST3\SpliceBridge.vst3`. FL has scanned it. |
| **Splice INSTRUMENT** | Version 1.1.15 (2025-11-03). `C:\Program Files\Common Files\VST3\Splice\Splice INSTRUMENT.vst3`. Content in `C:\Users\L5\Splice\INSTRUMENT\INSTRUMENT Common\Samples`. |
| **Sample folder** | `C:\Users\L5\Documents\Splice\` holds `Samples\packs\` (40+ pack folders such as "Drums That Knock 11", "DnB Drums", "Progressive House Drums", "Floral Lofi Hip Hop", "Loyal - RnB Bounce", "Lenno Nu Disco 2"), `presets\` (empty) and `.splice\id`. **81 `.wav` files, about 106 MB.** The `Samples` folder was last changed 2026-09-03. |

- This matches Splice's documented default. Splice's help center says the Windows Splice folder sits under Documents, with downloads organised by pack, and the location can be changed in the app's Preferences ([Splice Help Center, "Where is my Splice folder?"](https://support.splice.com/en/articles/8652662-where-is-my-splice-folder); [downloads go by pack](https://support.splice.com/en/articles/8652631-where-do-my-downloaded-samples-presets-midi-files-go); help-center articles, current as fetched 2026-09-14).
- Splice Bridge is a plugin you put on a MIDI track. It links the DAW to the desktop app so previews follow the project's tempo and key, and dragged-out files are rendered already stretched and pitched ([What is Splice Bridge?](https://support.splice.com/en/articles/8652855-what-is-splice-bridge); [How do I use Splice Bridge?](https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge); [Splice Bridge product page](https://splice.com/tools/bridge); help-center pages, current as fetched 2026-09-14). Bridge-modified files have their own help page on where they are saved ([Splice Help Center](https://support.splice.com/en/articles/10302760-where-to-find-samples-that-have-been-modified-with-bridge)).
- *(inference)* Downloaded Splice WAVs are ordinary files on disk. A bridge can load them into FPC, Slicex, DirectWave or FL audio clips by path, with no Splice API. Downloading new sounds needs the Splice app and Daniel's account, so Daniel does it himself.

## 6. Audio interface and drivers

- USB device **Scarlett 2i2 4th Gen** (`USB\VID_1235&PID_8219`).
- **Focusrite Audio Drivers 4.150.0.432** (2026-08-20). **Focusrite Control 2 1.1108.0.0** (2026-08-20).
- Windows endpoints on the interface: "Speakers (4- Focusrite USB Audio)", "Analogue 1 + 2 (4- Focusrite USB Audio)", and **"Loopback L + R (4- Focusrite USB Audio)"**, all Status OK. Older numbered duplicates show Unknown.
  - *(inference)* The Loopback L+R input lets a browser page or recorder capture what FL is playing without extra software, if FL's ASIO output feeds the loopback mix.
- ASIO drivers (`HKLM\SOFTWARE\ASIO`): **Focusrite USB ASIO**, Focusrite Thunderbolt ASIO, **FL Studio ASIO**, ASIO4ALL v2 (ASIO4ALL 2.17 installed), Realtek ASIO.
- Other audio: Realtek Audio 6.0.9927.1, AMD HDMI audio, Bluetooth hands-free for a Galaxy S24 Ultra.
- "Focusrite USB MIDI" appears in FL's list but is **disabled**. The Scarlett 2i2 has no MIDI ports; this is a leftover entry.

## 7. MIDI stack

### 7.1 Windows MIDI Services (in-box)

- The service **`midisrv`**, "Windows MIDI Service", is **Running** with StartType Manual. It runs `C:\WINDOWS\system32\midisrv.exe` 10.0.26100.7705. Its description covers MIDI 1.0 and 2.0 routing and enumeration.
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Drivers32`: `midi=wdmaud.drv`, `midi1=wdmaud2.drv`, **`MidisrvTransferComplete=1`**, `midimapper=midimap.dll`. *(inference)* WinMM MIDI 1.0 now goes through the new service.
- `HKLM\SOFTWARE\Microsoft\Windows MIDI Services`: `Midi2DiscoveryEnabled=1`. Four transport plugins, all `Enabled=1`:
  - `Midi2KSTransport`
  - `Midi2KSAggregateTransport`
  - **`Midi2LoopbackMidiTransport`**
  - **`Midi2VirtualMidiTransport`**
- Transport DLLs in System32, **version 1.0.15.0**: `Midi2.KSTransport`, `Midi2.KSAggregateTransport`, `Midi2.LoopbackMidiTransport`, `Midi2.VirtualMidiTransport`, `Midi2.DiagnosticsTransport`, `Midi2.MidiSrvTransport`, `Midi2.SchedulerTransform`, `Midi2.BS2UMPTransform`, `Midi2.UMP2BSTransform`, `Midi2.UmpProtocolDownscalerTransform`. `Windows.Devices.Midi.dll` is 10.0.26100.9168.
- Software devices (PnP):
  - "MIDI 2.0 Loop Devices" (`SWD\MIDISRV\MIDIU_LOOP_TRANSPORT`), OK
  - "MIDI 2.0 Virtual Devices" (`MIDIU_APP_TRANSPORT`), OK
  - "MIDI 2.0 Service Tests", "Service Test Ping (Internal)", **"Service Test Loopback A" and "Service Test Loopback B"** (`MIDIU_DIAG_LOOPBACK_A/B`), all OK. These are the diagnostic loopbacks Chrome cannot see, per tonight's known facts.
- **SDK Runtime and Tools: NOT installed.**
  - `C:\Program Files\Windows MIDI Services` is absent.
  - `Microsoft.Windows.Devices.Midi2.dll` is absent.
  - No `Microsoft.Windows.Devices.Midi2.*` WinRT classes are registered (only the legacy `Windows.Devices.Midi.*`).
  - `C:\ProgramData\Microsoft\MIDI` exists but is **empty**, so there is no configuration file and **no user-created loopback or virtual endpoints**.
- **External context:**
  - Microsoft's rollout post says the in-box Windows MIDI Services applies to Windows 11 retail 24H2, 25H2 and 26H1 ([Windows MIDI and Music dev blog, "Windows MIDI Services 2026 release: known issues and workarounds"](https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/); posted 2026-02-04, updated 2026-04-30). Its known-issues list includes dynamic ports such as loopMIDI, loopBE and rtpMIDI not being visible, and apps connecting to the wrong device when names are identical. Fixes were listed as rolling out from 2026-04-30.
  - The announcement covers multi-client MIDI 1.0, app-to-app MIDI and built-in loopback ([Windows Experience Blog, 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/)).
  - The separate **SDK Runtime and Tools** package provides the MIDI Settings app (where loopbacks are created), MIDI Console, a MIDI 1.0 monitor, PowerShell cmdlets and diagnostics ([microsoft.github.io/MIDI "Get latest"](https://microsoft.github.io/MIDI/get-latest/), fetched 2026-09-14). That page listed **1.0.14-rc.1.209** as current, older than the 1.0.15.0 transport DLLs already in System32, so the page may lag. [MIDI Services overview](https://microsoft.github.io/MIDI/overview/) and [GitHub releases](https://github.com/microsoft/MIDI/releases) have more.
  - A search snippet from the overview said the in-box release was expected "the last week of November" for 25H2. The year was not clear, and this machine already runs the in-box service, so treat that date as stale.
- *(inference)* **Zero-install loopback is not available today.** Creating a loopback pair such as "Claude Bridge A/B" needs the SDK Runtime and Tools (a download, so Daniel's OK). The alternative is loopMIDI, also a download, and on the known-issues list. Both change persistent MIDI configuration.

### 7.2 Controllers and ports right now

- **KeyLab 88 mk3** is connected:
  - `TUSBAUDIO_ENUM\VID_1C75&PID_02CE` (Arturia's USB driver)
  - `SWD\MIDISRV\MIDIU_KSA_16201702556534547415`, plus the MIDI 1.0 ports **"KeyLab 88 mk3 MIDI"** and **"KeyLab 88 mk3 DAW"**, each listed twice (`_0_0/_0_1` and `_1_0/_1_1`, *(inference)* likely the in and out pairs), all OK.
- Not present: two "USB Midi" devices (`VID_552D&PID_4348`), FLkey 61, KeyLab mkII 88, CHMidi-2.3.

### 7.3 Third-party MIDI tools: all absent

- **loopMIDI:** no `Program Files\Tobias Erichsen`, no `loopMIDI` folder, no uninstall entry, no service.
- **rtpMIDI:** no folder, no service, no uninstall entry.
- No other virtual MIDI drivers (loopBE, virtualMIDI, CoolSoft) appear in the program list.
- "Universal General MIDI DLS Extension SDK" 10.1.26100.7705 is installed. It is part of the Windows SDK, not a virtual-port tool.

## 8. Developer toolchains (for a VST3/CLAP or native helper build)

| Tool | State |
|---|---|
| Visual Studio / Build Tools (MSVC `cl`, `msbuild`) | **Absent.** No `vswhere.exe`, no `Microsoft Visual Studio` folders, no `VisualStudio\SxS\VS7` registry values. Only VC++ runtimes (2005 to 2022, v14.51.36247). |
| Windows SDK | **Present**, 10.0.26100.7705: headers, libs x64/x86/arm64, signing tools, App Certification Kit, Application Verifier, WPT. `Windows Kits\10\bin` also lists 10.0.14393 to 10.0.17134. |
| CMake / Ninja / make | Absent (not on PATH, no `Program Files\CMake`). |
| Rust (`cargo`, `rustc`, `rustup`) | Absent (no `~\.cargo`, no `~\.rustup`). |
| LLVM / clang, MSYS2, MinGW, gcc | Absent. |
| JUCE / Projucer | Absent (no `C:\JUCE`, no `~\JUCE`). |
| .NET | Runtimes 8.0.20 / 8.0.21 / 10.0.8 and Desktop Runtimes. **No .NET SDK** (`C:\Program Files\dotnet\sdk` empty). .NET Framework 4.8.1 SDK / Targeting Pack present. |
| Node.js | **24.14.1** (`C:\Program Files\nodejs`). |
| Git / GitHub CLI | Git 2.53.0.2, gh 2.92.0. |
| GStreamer | 1.28.7 MSVC x86_64 (per-user, 2026-09-13). |
| ffmpeg / mpv | Not on PATH. FL bundles `Shared\ffmpeg\x64`. `yt-dlp` is on PATH through Python 3.11 Scripts. |
| Docker Desktop / WSL | 4.84.0 / WSL 2.7.8.0 with Ubuntu distros. |

*(inference)* A native VST3 or CLAP plugin, or a C++ helper, needs at least VS Build Tools (C++ workload) and CMake, plus the plugin SDK or JUCE, or a Rust toolchain with nih-plug. All of those are downloads needing Daniel's OK.

## 9. Python

- Launcher (`py -0p`):
  - **3.11** (default, marked `*`): `C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe`, 3.11.9
  - **3.14**: `...\Python314\python.exe`, 3.14.7
- `%LOCALAPPDATA%\py.ini` pins both `python3=3.11` and `python=3.11`, matching the repo's Python version strategy.
- Bare `python` and `python3` on PATH resolve to the WindowsApps aliases first. `pip` on PATH is the **3.14** one.
- 3.11 packages that matter here: numpy 2.4.4, librosa 0.10.2, fastapi 0.135.3, aiohttp 3.13.3, websockets 16.0, Flask 3.1.3.
  - **Not installed:** `mido`, `python-rtmidi`, `pygame`, `sounddevice`, `pyaudio`, `music21`, `pretty_midi`, `miditoolkit`, `pedalboard`. *(inference)* A Python-side MIDI sender needs a `pip install`, which counts as an install and needs approval.
- 3.14 packages: numpy 2.4.4 only, among those checked.
- FL-embedded Python 3.12.1 runs separately inside FL (section 3.2).

## 10. Arsenal context (repo, read-only glance)

- `E:\AI-Setup\arsenal\` has `pianocue.py`, `pianocue_voicing.mjs`, `practice.py`, `practice_theory.mjs`, `nashville.py`, `timebase.py`, `serve.py`, `take.py`, and the specs `PLAY-NIGHT-SPEC.md`, `PIANO-V2-SPEC.md`, `FIRST-LIGHT-SPEC.md`.
- `arsenal\web\` has `piano.html/js/css`, `play.html/js/css`, and the `piano-lab-*` and `piano-next` variants.
- `arsenal\tools\qm.py` exists.

---

## 11. Open questions this inventory cannot settle

1. Can FL 26.1's device-script sandbox import `socket`, `select` or `asyncio`, or open files, from the bundled 3.12.1? The modules exist on disk; the API lane must confirm what is allowed.
2. Will Daniel approve the **Windows MIDI Services SDK Runtime and Tools** download to create named loopback endpoints? Is Chrome 152 able to see such endpoints, given it cannot see "Service Test Loopback"?
3. Where does Addictive Drums 2 keep its content? `Public\Documents\XLN Audio` is absent and the XLN registry key only holds activation data.
4. Does Daniel want the Splice folder added to FL's browser search paths? That is a settings change, so ask.
5. Does the bridge need FL 2025 at all, or only FL 2026? Both are installed and share `Documents\Image-Line`.

## Sources (external)

- Image-Line, FL Studio manual, "MIDI Scripting (Python)": https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm (fetched 2026-09-14). Scripts go in `Documents\Image-Line\FL Studio\Settings\Hardware\<name>\device_<name>.py`, need a `#name=` first line, are picked under MIDI Settings > Controller type, and need no extra install.
- Image-Line / IL-Group, FL Studio Python API stubs: https://il-group.github.io/FL-Studio-API-Stubs/ and https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/ (fetched 2026-09-14). Three script types: MIDI controller, piano roll, Edison.
- hobyst, "FL Studio MIDI Scripting 101": https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html (older community doc; its Python 3.9 statement is stale compared with the local 3.12.1).
- Microsoft, Windows MIDI and Music dev blog, "Windows MIDI Services 2026 release: known issues and workarounds": https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/ (2026-02-04, updated 2026-04-30).
- Microsoft, Windows Experience Blog, 2026-02-17: https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/
- Microsoft, Windows MIDI Services "Get latest SDK Runtime and Tools": https://microsoft.github.io/MIDI/get-latest/ (fetched 2026-09-14; showed 1.0.14-rc.1.209).
- Microsoft, Windows MIDI Services overview: https://microsoft.github.io/MIDI/overview/ ; releases: https://github.com/microsoft/MIDI/releases
- Splice Help Center: https://support.splice.com/en/articles/8652662-where-is-my-splice-folder ; https://support.splice.com/en/articles/8652631-where-do-my-downloaded-samples-presets-midi-files-go ; https://support.splice.com/en/articles/8652855-what-is-splice-bridge ; https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge ; https://support.splice.com/en/articles/10302760-where-to-find-samples-that-have-been-modified-with-bridge (fetched or searched 2026-09-14)
- Splice, Bridge product page: https://splice.com/tools/bridge
