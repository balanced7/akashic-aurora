//! {"name": "torus-ring", "kind": "source", "from": "standard SDF torus, marched", "note": "A rotating torus. Included because a ring reads as MOTION in a way a sphere cannot -- the silhouette changes as it turns, so the eye gets told the object is three-dimensional without any lighting cue. Needs rot2.", "order": 50, "cat": "shape", "in": {}, "out": {"col": "vec3", "alpha": "float"}}
{
  vec3 ro=vec3(0,0,-3.4), rd=normalize(vec3(uv,2.2));
  float t=0.; float hit=0.; vec3 p;
  for(int i=0;i<40;i++){
    p=ro+rd*t;
    vec3 q=p; pR(q.yz,u_time*0.35*(0.3+u_spin)); pR(q.xy,u_time*0.21);
    float d=length(vec2(length(q.xz)-1.0,q.y))-0.28;
    if(d<0.002){ hit=1.; break; }
    t+=d*0.85; if(t>8.) break;
  }
  if(hit>0.5){
    float sh=1.-clamp((t-2.2)/2.2,0.,1.);
    col+=mix(u_id0,u_id1,sh)*(0.25+0.9*sh);
    col+=u_tint*0.35*sh;
    alpha=1.;
  }
}
