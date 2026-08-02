//! {"name": "vignette-cubic", "kind": "modifier", "from": "the compositing shader Daniil pasted", "note": "Aspect-corrected, cubic falloff, normalised by the ACTUAL corner distance. A smoothstep starts shading from the centre outward (dimming); a cubic stays flat across the middle and falls only near the corners (framing). Normalising by 0.7071 instead of the true corner blacks out the sides of a widescreen display -- that bug is why this is a chunk and not retyped each time.", "order": 50}
{
  float asp = u_res.x/u_res.y;
  vec2 vuv = gl_FragCoord.xy/u_res; vuv.x = (vuv.x-0.5)*asp+0.5;
  float vd = length(vuv-0.5)/length(vec2(0.5*asp,0.5));
  col *= mix(1.0, 1.0 - pow(clamp(vd*0.94,0.,1.),3.0), 0.60);
}
