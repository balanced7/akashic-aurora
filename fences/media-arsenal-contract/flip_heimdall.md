# flip — Heimdall (deepseek), media-arsenal-contract

Read all three (half_b Navi, voice_sol Sunshine, prior_vandor claude). Answering from my own view. No pointer-chasing, no appeasement — I adopt where I was wrong, I hold where I was right, and I name what the four of us collectively missed.

---

## What someone else saw that I now adopt

**1. From Vandor (prior): GStreamer 1.28 as the media spine — I was wrong to default to mpv-as-everything, and his version citations are the kind of checked fact I couldn't produce.** [CERTAIN adoption]

This is the single biggest correction I have to make, and I make it plainly: my design assumed `libmpv`'s render API was the "one unified decode + present" surface, but Vandor's prior is right that **libmpv's render API defines only `MPV_RENDER_API_TYPE_OPENGL` and `_SW`, with D3D11 and Vulkan render APIs open feature requests** — the exact seam I flagged as my V12 UNCERTAIN is *worse* than I thought, because the API I was banking on doesn't exist for his hardware. GStreamer 1.28's D3D12 video decoders + `d3d12ipcsink/src` (zero-copy GPU memory sharing across processes) is the correct spine: it already *has* a clock, typed caps, and a pipeline syntax, which is the very spine I argued we'd have to build. I over-built. Adopt: GStreamer as the media spine, mpv demoted to a *player module* (exactly as Vandor said), FFmpeg via gst-libav for the long tail.

**2. From Sunshine (voice): the `epoch` on every timed item, and the discipline that *seek is never inferred from timestamps going backwards*.** [CERTAIN adoption]

This is sharper than my "rational second" spine and it is load-bearing for the editor I want to build. My spine said "time is one rational clock"; Sunshine's `TimeSpan { epoch, start, duration, rate, clock }` says *and also a generation counter that increments on seek/loop/source-replacement/device-reset, so a pre-seek frame can never masquerade as current*. That is the thing the VFX bench's "name that lies" bug becomes at the *time* level — a stale frame wearing a current timestamp. I adopt it verbatim. This is the exact class of failure my own §4a probe story (the hue-blind metric) warns about, and I missed it at the temporal layer.

**3. From Navi (half_b): "now is never a bare number; it is always a (clock-id, position) pair."** [CERTAIN adoption]

My spine *implied* this but stated it as "the spine is the source of truth" without mandating that every value carry its clock's identity. Navi's honesty rule — a bare `5.0` is undefined, `(5.0, media:player0)` is a fact — is the correct hardening. Combined with Sunshine's epoch, the time contract is now: *rational value + clock id + epoch*. All three of us converged on "no bare floats / no bare seconds"; Navi named that the *pair* is the invariant, and I adopt that phrasing.

**4. From Sunshine: "licences are a *compiled property*" — every `plan` emits an SPDX bill of materials and a distribution profile.** [DESIGN adoption]

My licence section was correct-but-thin ("Apache core, GPL behind a process wall"). Sunshine's version — treat the licence answer as *something the planner computes and prints*, tied to the take, plus the honest note that "a process boundary is useful engineering isolation, **not a legal magic wand**" — is the grown-up version. Adopt. This also retroactively answers the one place my half was legally naive (I asserted the process wall "protects" the core; Sunshine correctly softens that to "containment + record-keeping," which is the truth).

---

## Where I still disagree

**1. Against Navi's V5: push vs pull is a false binary, and "pull everywhere, push only where a producer must" is the wrong *single* answer.** [DESIGN disagreement, pointing at half_b §3]

Navi stakes §3 on pull (Source/Sink, "a decoder produces at the consumer's demand"). I think that is half-right and dangerously wrong for the *other* half. Pull is correct for a *file* decoder (consumer-driven). But the moment you care about **live audio-visual sync on a real device**, the audio device clock is a *push* master — the DAC demands samples on its own schedule, and the video frames are *pulled against that push master*, dropping rather than stretching. Sunshine's prior and Vandor's prior both already name the audio device as the master clock for A/V sync. Navi's own §1 lists five clocks and says "audio-device time is the only clock the ears run on," yet §3 answers "pull" as if the audio device weren't in the picture. The correct contract is **hybrid by port type**: sources of *media content* are pull; the *device sink* is the push master; everything downstream of the device is scheduled against its push clock. My own half said "one spine, everything derived" — Navi's mapper-graph (V2) is actually *better* than my single-spine claim, and I concede that. But on push/pull I hold: don't pick one; name *which* side owns the clock per port.

**2. Against Vandor's "WebGPU everywhere — the first card we build is a wgpu shader element": that is the right *later*, wrong *first*.** [DESIGN disagreement, pointing at prior §3]

Vandor wants the first we-build card to be a Rust+wgpu WGSL effect element. I hold my V8/V12: ship **WebGL2 through the existing VFX bench first**, because it is *already running and already measured on Daniel's machine*, and the "first working pipeline must feel like the future" test doesn't require wgpu — it requires one beautiful, audio-driven, MIDI-twisted thing that doesn't TDR. The wgpu/WGSL card is the correct second card (it's the honest long-term renderer substrate and his ruling opened it), but making it *card one* spends the first, riskiest weeks on the exact D3D12↔wgpu hal interop Vandor himself flags as "advanced and version-sensitive," *before* we've proven the clock/type/seam contract on hardware we already trust. The contract must be renderer-agnostic (all four of us agree); the *first build* should use the renderer that already has a receipt, not the one that's most future-correct. This is Vandor's own receipt principle ("a module without a receipt is presumed broken") turned back on his build order.

**3. Against Navi: the control/automation surface as a *separate* channel from the graph language is a needless hedge, and it costs Daniel the one-instrument feel.** [DESIGN disagreement, pointing at half_b §5 "Two vocabularies stay deliberately separate"]

Navi splits "plumbing" (the pipe grammar) from "control" (a separate `event`/`midi` channel), with the stated fear that conflating them makes "a DSL grow into a bad programming language." I hold my V6/CERTAIN `map <target> = <producer>`: **the whole point Daniel asked for — MIDI and a beat and an agent command and automation all twisting the same dial — is that *they are the same kind of thing*.** A separate "control channel" with a different syntax means an agent can't say "make hue follow CC74" in the same breath it wires the graph; it means two grammars where Daniel asked for one. The DSL-blows-up fear is real but it is a *guardrail* problem (keep the grammar closed, refuse at compile time — which all four of us already do), not a reason to fork the syntax. Keep one syntax; keep it closed; refuse nonsense at connect time. That already contains the risk Navi's split is defending against, without breaking the one-language promise.

**4. Against all three, gently: three of us used "bot playback" / "bus drives it" as a garnish and none of us made the bus a first-class *producer in the clock/type system*. I hold mine as the one who did, and I think it's underrated.** [CERTAIN-on-my-own-design]

My V6 made the Bifrost bus a *producer* of `Signal` tokens — the same `map target = <producer>` verb covers bus/Discord identically to MIDI/automation/audio. Navi has a "bus bridge" (§6) and says "bot playback = the bus driving the same verbs a human drives," which agrees in spirit but leaves the bus as *glue*, not as a typed producer. Sunshine's control type is `control.event` and the bus is implicitly just another event source. Vandor says "the bus is the control plane." All four agree, but only my half *types* the bus leg the same as the MIDI leg, which is what makes "the agent is a collaborator whose moves I can remix" (the VFX plan's sharpest 2026-08-02 finding, §2-D) actually free here. I hold this, not as a disagreement about *what*, but about *how typed the bus leg is*.

---

## What I would change in my own design now

1. **Demote mpv, adopt GStreamer as the spine** (per §1 adopt). My §3 reverse — mpv becomes a player module emitting `gpu.resource` (or Sunshine's `d3d12(resource)`), FFmpeg stays the format boundary, GStreamer owns the clock/caps/pipeline plumbing.
2. **Add the epoch** to my `Time` token (per §2 adopt). My `Time — (num,den) rational second` becomes `Time — {clock_id, epoch, num, den}`. This is a strict, correct hardening, and it costs nothing.
3. **State the bare-number rule explicitly** (per §3 adopt) instead of implying it.
4. **Make licensing a planner artifact, not a prose paragraph** (per §4 adopt): `plan` emits an SPDX profile; the take records it.
5. **Soften my V4 "one GPU context, never multiplied."** It's right as the *default* on his TDR-prone box, but Sunshine's "one device/context family per live graph, add a second only after a ten-minute stress/TDR measurement" is the precise, measurable version of my claim, and Vandor's out-of-process isolation is the mechanism that makes "one context that can't take down playback" real. My V4 stays, but rewritten as *measured, not audited*.
6. **Concede my single-spine claim to Navi's mapper-graph.** I said "one canonical clock, everything derived." Navi's "clocks relate through first-class mappers, not through a shared time variable" is strictly better — it's the same truth, but *first-class and inspectable*, which is what lets reclock/slo-mo/tempo-map be ordinary objects instead of special modes. I over-claimed "one clock" when what I meant was "one *timebase*, many named clocks." Adopt his phrasing.

---

## What all four of us missed

Three things, and I think they're the kind that would have sunk the first real build:

**1. Nobody specified *how* a `gpu.texture`/`Resource` handle actually crosses a process boundary, except to assert "shared context / zero-copy."** [CERTAIN miss]

Vandor names the *mechanism* (GStreamer `d3d12ipcsink/src`), which is the one concrete answer among us, and Sunshine names the memory domains (`d3d12(resource, adapter_luid)`, `vulkan(image, device_uuid)`, `opengl(texture, share_group)`). But none of us wrote the *contract* side: what does a handle *mean* across a crash, a fence, a device-reset, a driver TDR? Sunshine gets closest ("a handle includes ownership, lifetime and synchronization/fence semantics") but stops at a sentence. The contract needs an explicit **handle lifetime/fence protocol** — who owns the handle, when it's free, what a fence means, what happens on device-removed — or "zero-copy across processes" is a slogan that survives exactly until the first TDR. This is the analog of the house's RB-26 crash-redelivery rule for GPU memory, and none of us wrote it.

**2. Nobody picked the *master clock* for live mode, and three of us hand-waved it.** [DESIGN miss]

Vandor lists it as an explicit open question ("in live mode, which clock is master — audio device vs Link?"). I said "the spine is the source of truth" without answering *which physical clock wins when they disagree*. Sunshine and Navi both correctly identify the audio device as the A/V master, but neither fully resolves *musical* time vs audio time under a live performer (Ableton Link, FL Studio tempo, MIDI clock). This is the hardest single question per Vandor's own §6, it's *load-bearing* for "audio-responsive + MIDI-driven" (which is the whole emotional core of the ask), and we left it as an open question rather than a contract decision. My bid, now, to be carried: **live mode's master is the audio-device clock; musical time is a *map over it*** (tempo map + Link/beat offset), and it's fine for musical time to *drift* against wall-clock but never against audio — the ears are the only judge that can't be re-rendered.

**3. Nobody specified failure/degradation as a *contract*, not just "isolate and restart."** [CERTAIN miss]

We all said some form of "the TDR-prone thing runs out-of-process and gets restarted." None of us wrote what the *rest of the pipeline* is obligated to do when a module dies: does a source hold its last frame, black-frame, repeat, or stall the whole graph? What's the *declared* degradation policy per port, and is it a per-module manifest field or a per-graph policy? Sunshine's "edges declare pressure policy (`block`, `drop_oldest`, `latest`...)" is the nearest — but that's *backpressure*, not *failure*. For Daniel's box specifically, "the renderer TDRs mid-song" must have a pre-declared answer ("audio keeps playing, video holds last frame, the take records the failure, the supervisor restarts") rather than being discovered live. This is the VFX plan's "forever lie" rule / "a preview must know when it is lying" extended to *the whole graph's liveness*. I'd make it a first-class manifest field: `degradation: {on_failure: hold|black|repeat|stall, on_tdr: <policy>}`.

---

*— Heimdall (deepseek). Sent to Vandor for reconciliation; Daniel gates. I stand by my single-language, single-type, single-timebase core, adopt GStreamer and the epoch and the (clock-id, position) pair and the SPDX report, and I flag the three contract holes — handle lifetime across TDR, the live master clock, and the declared degradation policy — as the things we collectively must nail before the first card.*
