#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;
uniform float u_sub;
uniform float u_gap;
uniform float u_spin;
uniform float u_pulse;
uniform float u_sat;
uniform vec3  u_tint;
uniform float u_dim;
uniform float u_wire;
uniform vec3  u_id0;
uniform vec3  u_id1;
uniform float u_round;
uniform float u_star;
uniform float u_see;
uniform float u_thick;

#define T (u_time)

// THE SHAPE. This is a SUPERQUADRIC -- |x|^n + |y|^n + |z|^n = const -- with two things layered on:
//   n = 8 - 6k   sweeps the exponent from 8 (hard cube) to 2 (sphere)
//   -k*8*(x^2+y^2) is a revolution term that hollows the middle into a torus
// so ONE parameter k walks the object cube -> rounded box -> torus. That is the whole morph, and
// it is three lines: no blend of two SDFs, no interpolation between meshes, just an exponent.
float sq(vec3 o, float k)
{
    o.z -= 4.5;
    vec3 r = vec3(T/2.3, T/1.95, T/2.7), s = sin(r), c = cos(r);
    o *= mat3(
         c.y,     s.z*s.y,            -s.y*c.z,
        -s.x*s.y, c.x*c.z+s.x*s.z*c.y, s.z*c.x-s.x*c.z*c.y,
         c.x*s.y, s.x*c.z-c.x*s.z*c.y, s.z*s.x+c.x*c.z*c.y
    );
    float n = 8.-6.*k, l = 3.8*k-2.;
    o = abs(o);
    return pow(pow(o.x,n)+pow(o.y,n)+pow(o.z,n)+l,2.)-k*8.*(o.x*o.x + o.y*o.y);
}

// Distance -> brightness. The 4th power is what turns a field into a THIN BRIGHT CONTOUR: only
// values very close to the isosurface survive it.
float wire(float d){ return pow(1. - min(1.,abs(d)), 4.); }

void main()
{
    vec2 uv = (gl_FragCoord.xy/u_res - 0.5) / vec2(1., u_res.y/u_res.x) * 1.4;
    uv *= 0.62;

    float k  = cos(T/3.1)/2.5 + .4;      // the morph driver: cube <-> torus, period ~19.5s
    float n  = 6.0 + 12.0*u_sub/5.0;     // slice count, on the bench's density knob
    float ct = 0.;

    // "Z-SLICED SPACE", the author's own name for it, and the reason this reads as glowing wire
    // rather than as a solid: it never marches. It evaluates the field on a fixed ladder of depth
    // planes and keeps the brightest contour each pixel sees. Cost is the slice count -- 18 field
    // evaluations, flat -- where a raymarch would be 40-100 and would return a SURFACE instead of
    // a stack of cross-sections.
    float z = 4.5 + 2.*(n-1.)/(n+1.);
    for (int i=18; i>0; i--)
    {
        vec3 p = vec3(uv*(2.+z), z);
        ct = max(ct, wire(sq(p,k))/(z-2.6));   // /(z-2.6): far slices dim, so depth reads
        z -= 4./(n+1.);
    }

    vec3 col = vec3(0., ct*ct, ct) * (0.9 + 0.6*u_dim);
    outColor = vec4(col, clamp(ct*1.4, 0., 1.));
}
