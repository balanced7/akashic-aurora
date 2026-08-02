//! {"name": "superquadric-slices", "kind": "source", "cat": "shape", "order": 50, "from": "SandS, HAL 4kb intro (the torus() + Z-sliced render), pasted by Daniil 2026-08-02", "in": {"uv": "vec2"}, "out": {"col": "vec3", "alpha": "float"}, "note": "A superquadric |x|^n+|y|^n+|z|^n morphing cube<->torus on ONE parameter, drawn by Z-SLICING rather than raymarching: the field is sampled on a fixed ladder of depth planes and the brightest contour wins. That is why it reads as glowing see-through wire and why it shows its own interior -- you are looking at a stack of cross-sections, not at a surface. 18 evaluations flat, no adaptive stepping."}
{
  float T = u_time;
  vec2 quv = uv * 0.42;
  float kk = cos(T/3.1)/2.5 + .4;
  float nn = 6.0 + 12.0*clamp(u_sub,0.,5.)/5.0;
  float acc = 0.;
  float zz = 4.5 + 2.*(nn-1.)/(nn+1.);
  for (int i=18; i>0; i--) {
    vec3 pp = vec3(quv*(2.+zz), zz);
    pp.z -= 4.5;
    vec3 rr = vec3(T/2.3, T/1.95, T/2.7), ss = sin(rr), cc2 = cos(rr);
    pp *= mat3(cc2.y, ss.z*ss.y, -ss.y*cc2.z,
               -ss.x*ss.y, cc2.x*cc2.z+ss.x*ss.z*cc2.y, ss.z*cc2.x-ss.x*cc2.z*cc2.y,
               cc2.x*ss.y, ss.x*cc2.z-cc2.x*ss.z*cc2.y, ss.z*ss.x+cc2.x*cc2.z*cc2.y);
    float n2 = 8.-6.*kk, l2 = 3.8*kk-2.;
    vec3 ap = abs(pp);
    float d2 = pow(pow(ap.x,n2)+pow(ap.y,n2)+pow(ap.z,n2)+l2, 2.) - kk*8.*(ap.x*ap.x + ap.y*ap.y);
    acc = max(acc, pow(1. - min(1.,abs(d2)), 4.) / (zz-2.6));
    zz -= 4./(nn+1.);
  }
  col += mix(u_id0, u_id1, clamp(acc*1.6,0.,1.)) * acc * 2.2;
  alpha = clamp(acc*1.5, 0., 1.);
}
