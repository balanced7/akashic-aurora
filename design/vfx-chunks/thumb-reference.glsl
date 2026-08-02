//! {"name": "thumb-reference", "kind": "source", "from": "built for the thumbnail index", "order": 50, "cat": "field", "in": {}, "out": {"col": "vec3", "alpha": "float"}, "note": "Calibration ramp for thumbnails: 0->2.2 luminance across x, identity hue across y, banded. Not decorative -- it exists so two tone operators produce visibly DIFFERENT tiles, which pretty references cannot do."}
float rx = uv.x*0.5+0.5;
float ramp = rx*rx*2.2;
vec3 hue = mix(u_id0, u_id1, clamp(uv.y*0.5+0.5,0.,1.));
float band = mix(0.72, 1.0, step(0.5, fract((uv.y*0.5+0.5)*7.0)));
float vig = smoothstep(1.15, 0.2, length(uv));
col = hue * ramp * band * vig;
alpha = 1.0;
