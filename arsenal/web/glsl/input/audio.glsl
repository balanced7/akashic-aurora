//! {"name": "input-audio", "kind": "helper", "cat": "L2", "family": "L", "version": "1.0.0", "order": 15,
//!  "license": "Apache-2.0",
//!  "credits": ["W3C, Web Audio API, the AnalyserNode (https://www.w3.org/TR/webaudio/): the 2048-point transform, the -100 to -30 dB byte mapping this module inverts",
//!   "Shadertoy's audio input (https://www.shadertoy.com/howto), as the house runtime packs it (arsenal/web/shaderlab/toy-runtime.js, packAudioTexture): 512 x 2, row 0 the spectrum, row 1 the waveform",
//!   "the MIDI Tuning Standard's equal temperament (A4 = 440 Hz = note 69), and the GPU and audio report, section 12 (research/reviewed/shader-school-2026-10-13/gpu-perf-glsl.md)"],
//!  "cost": {"class": "C1", "loop": "audBand: at most 64 taps", "tex": 64},
//!  "contract": "audSpectrum reads row 0 of the Shadertoy audio texture (any width, 2 rows) at u across the bins, filtered as the texture is, and returns the analyser's byte over 255: decibels mapped to 0..1, not amplitude; audWave reads row 1 back into -1..1 (byte 128 is silence and reads 0, as does a channel without two rows); audByteToDb and audByteToAmp undo the analyser's default -100..-30 dB mapping (byte 0 counts as silence: amplitude 0). audBand returns the MEAN LINEAR magnitude of the bins from hzLo to hzHi (either order; a 2048-point transform at sampleRate, so bin k is k * sampleRate / 2048 Hz), each byte turned back into amplitude by audByteToAmp, at most 64 texelFetch taps spread evenly when the band is wider, clamped to the texture (an empty channel reads 0). midiToHz, hzToMidi and pianoKeyToHz are equal temperament with A4 = 440 Hz (MIDI note 69, piano key 49); hzToMidi floors its input at 0.001 Hz. Honest while the host binds the real sampleRate and keeps the analyser's decibel range at its default.",
//!  "note": "MIDI tells a shader WHICH notes; audio tells it HOW they sound. Below G4 a semitone is narrower than one spectrum bin, so the piano's pitch comes from the note bus and the spectrum is for brightness, bloom and room. Sum bands with audBand, never by adding bytes: the bytes are decibels, and adding decibels is adding logarithms. A band wider than one pixel must be averaged, or bars flicker as partials drift between bins. Wrong looks like a dead bass end (linear taps that skip the low bins), bars that flicker on sustained notes (point samples), or everything 1.5 semitones flat at 48 kHz (a sample rate of 44,100 assumed).",
//!  "targets": {"glsl": "300es", "needs": ["texelFetch"]}, "card": "input-audio.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0", "exemplars": ["MdsXWM"], "learn": ["GP 12", "GP 12.7"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published specifications credited above.
//
// WHY. The audio texture is a spectrum analyser's display handed to the GPU: 512 columns of loudness, already in
// decibels and already squeezed into bytes. These helpers read it the way an engineer reads a meter bridge: one
// column, or a whole band averaged in real (linear) units, with the band edges in hertz rather than columns.

// Row 0 at u in 0..1 across the bins. Shadertoy's layout: bin k of a 2048-point transform (k * sampleRate / 2048 Hz)
// is the texel centred at u = (k + 0.5) / width, so a lookup by frequency adds that half texel.
float audSpectrum(sampler2D a, float u) {
    return texture(a, vec2(u, 0.25)).x;                    // v = 0.25 is the middle of row 0 of a 2-row texture
}

// Row 1, the waveform, at u across its 512 samples, back in -1..1 (the analyser writes floor(128 (1 + x)); 128 is
// silence and reads exactly 0).
float audWave(sampler2D a, float u) {
    if (textureSize(a, 0).y < 2) return 0.0;               // not the 2-row audio layout (an empty channel): silence
    return texture(a, vec2(u, 0.75)).x * (255.0 / 128.0) - 1.0;
}

// One spectrum byte (0..1) to decibels, through the analyser's default range: -100 dB at 0, -30 dB at 1.
float audByteToDb(float v) {
    return -100.0 + 70.0 * v;
}

// One spectrum byte (0..1) to linear amplitude, 10^(dB / 20). Byte 0 is at or below the floor: read as silence, 0.
// Bins must be in this form before they are summed or averaged; bytes are logarithms.
float audByteToAmp(float v) {
    return v > 0.0 ? exp2(audByteToDb(v) * (3.321928094887362 / 20.0)) : 0.0;   // log2(10) / 20
}

// Mean linear magnitude over the bins of [hzLo, hzHi].
float audBand(sampler2D a, float hzLo, float hzHi, float sampleRate) {
    float last = float(textureSize(a, 0).x - 1);
    if (last < 0.0) return 0.0;                            // nothing bound: silence
    float binsPerHz = 2048.0 / sampleRate;
    float kLo = clamp(floor(min(hzLo, hzHi) * binsPerHz + 0.5), 0.0, last);
    float kHi = clamp(floor(max(hzLo, hzHi) * binsPerHz + 0.5), kLo, last);
    float bins = kHi - kLo + 1.0;
    float stride = max(1.0, ceil(bins / 64.0));            // at most 64 taps, spread across the whole band
    float taps = floor((bins - 1.0) / stride) + 1.0;
    float gathered = 0.0;
    for (int bandTap = 0; bandTap < 64; bandTap++) {
        if (float(bandTap) >= taps) break;
        ivec2 spectrumTexel = ivec2(int(kLo + float(bandTap) * stride), 0);   // row 0, one bin
        float byteValue = texelFetch(a, spectrumTexel, 0).x;
        gathered += audByteToAmp(byteValue);
    }
    return gathered / taps;
}

// Equal temperament, A4 = 440 Hz = MIDI note 69.
float midiToHz(float m) {
    return 440.0 * exp2((m - 69.0) / 12.0);
}

float hzToMidi(float hz) {
    return 69.0 + 12.0 * log2(max(hz, 0.001) / 440.0);
}

// Piano keys 1..88: key 1 is A0 (27.5 Hz), key 49 is A4 (440 Hz), key 88 is C8.
float pianoKeyToHz(float key) {
    return 440.0 * exp2((key - 49.0) / 12.0);
}
