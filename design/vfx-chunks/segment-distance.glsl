//! {"name": "segment-distance", "kind": "helper", "from": "standard; used by the flock and the orbit swarm", "note": "Distance from a point to a line segment. The one genuinely per-pixel operation in any trail renderer -- everything else about a trail can be precomputed.", "order": 10}
float segD(vec2 p,vec2 a,vec2 b){
  vec2 pa=p-a, ba=b-a;
  float h=clamp(dot(pa,ba)/max(dot(ba,ba),1e-6),0.,1.);
  return length(pa-ba*h);
}
