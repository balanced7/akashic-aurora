#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: ringpulse
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// Ring pulse. Concentric rings marching outward, fading as they go.
// Written in Shadertoy dialect on purpose: iTime, iResolution.xy, iResolution.y, mainImage.
#define RINGS 5

float ring(vec2 p, float r, float w)
{
    return smoothstep(w, 0.0, abs(length(p) - r));
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float t = iTime;
    vec3 col = vec3(0.0);
    for (int i = 0; i < RINGS; i++)
    {
        float fi = float(i);
        float r = fract(t * 0.25 + fi / float(RINGS));
        float a = ring(uv, r * 0.95, 0.015 + r * 0.05) * (1.0 - r);
        col += a * vec3(0.45 + 0.35 * sin(fi + t), 0.55, 1.0);
    }
    fragColor = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
