//! {"name": "value-noise-3d", "kind": "helper", "from": "IQ Rainforest 4ttSWf, via the Wallis fog shader", "note": "Textureless 3D value noise. Chosen for volumetrics because a texture fetch per march step would dominate everything else in the loop. Needs h31.", "order": 20, "cat": "noise"}
float vn(vec3 x){
  vec3 i=floor(x), f=fract(x); f=f*f*(3.-2.*f);
  return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float fbm3(vec3 p){ return .55*vn(p)+.27*vn(p*2.1+7.3)+.13*vn(p*4.3+19.1); }
