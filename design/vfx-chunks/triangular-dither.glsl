//! {"name": "triangular-dither", "kind": "modifier", "from": "adapted from the fog shaders' march jitter", "note": "A DIFFERENCE of two hashes gives a triangular distribution -- the correct shape for breaking quantisation, effective at about half the amplitude uniform noise needs. Amplitude is ~1.6/255: a darker image needs LESS grain, not more, while still needing one code value to break ramps. Must be LAST, at the quantisation step.", "order": 50}
{
  float n1=fract(sin(dot(gl_FragCoord.xy+u_time*1.7,vec2(12.9898,78.233)))*43758.5453);
  float n2=fract(sin(dot(gl_FragCoord.yx-u_time*1.3,vec2(63.7264,10.8730)))*32168.4321);
  col += (n1-n2)*(1.6/255.0);
}
