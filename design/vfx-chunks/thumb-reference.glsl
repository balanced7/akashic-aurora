//! {"name": "thumb-reference", "kind": "source", "from": "built for the thumbnail index", "order": 50, "cat": "field", "in": {"uv": "vec2"}, "out": {"col": "vec3", "alpha": "float"}, "note": "Calibration ramp for thumbnails: 0->2.2 luminance across x, identity hue across y, banded, and slowly ROTATING. The motion is not decoration -- a domain operator that only bends space (kaleido, tile, fisheye) has nothing to reveal against a still reference, and its tile would sit motionless and read as a tone operator."}
vec2 ruv = uv;
float rot = u_time * 0.45;
ruv = mat2(cos(rot),-sin(rot),sin(rot),cos(rot)) * ruv;
ruv += vec2(sin(u_time*0.7), cos(u_time*0.53)) * 0.18;
float rx = ruv.x*0.5+0.5;
float ramp = rx*rx*2.2;
vec3 hue = mix(u_id0, u_id1, clamp(ruv.y*0.5+0.5,0.,1.));
float band = mix(0.72, 1.0, step(0.5, fract((ruv.y*0.5+0.5)*7.0)));
float vig = smoothstep(1.15, 0.2, length(uv));
col = hue * ramp * band * vig;
alpha = 1.0;
