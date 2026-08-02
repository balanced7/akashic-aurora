//! {"name": "plasma-field", "kind": "source", "from": "domain warp, from the marble interior", "note": "A 2D field warped by its own noise. The warp is the whole character: sampling noise at a position already displaced BY noise folds it into sheets and filaments instead of clouds. Needs value-noise-3d.", "order": 50, "cat": "field"}
vec3 q=vec3(uv*1.6,u_time*0.07);
float w=fbm3(q);
q+=vec3(w*1.7,w*1.2,-w*0.6);
float f=fbm3(q*1.4);
f=smoothstep(0.35,0.85,f);
col=mix(u_id0,u_id1,clamp(w*1.3,0.,1.))*f*1.6;
alpha=f;
