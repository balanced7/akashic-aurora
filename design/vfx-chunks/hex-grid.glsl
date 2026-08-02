//! {"name": "hex-grid", "kind": "source", "from": "the avatar's tiling, flattened to 2D", "note": "A flat hex lattice. Cheap -- one fract and a couple of dots, no march -- and it is the same tiling the geodesic avatar wears, so a composition using it reads as family rather than as a borrowed texture.", "order": 50, "cat": "shape"}
{
  vec2 p=uv*(3.0+u_sub);
  p.x*=1.1547;
  vec2 a=mod(p,vec2(1.,1.732))-vec2(.5,.866);
  vec2 bb=mod(p+vec2(.5,.866),vec2(1.,1.732))-vec2(.5,.866);
  vec2 g=dot(a,a)<dot(bb,bb)?a:bb;
  float e=abs(max(abs(g.x)*.866+g.y*.5,g.y));
  float line=smoothstep(0.02+u_gap,0.0,0.5-e);
  float pulse=.5+.5*sin(u_time*.8+floor(p.y)*.7+floor(p.x)*.4);
  col+=mix(u_id0,u_id1,pulse)*line*(0.35+0.9*pulse);
  alpha=line;
}
