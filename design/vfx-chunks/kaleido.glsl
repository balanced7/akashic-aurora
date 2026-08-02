//! {"name": "kaleido", "kind": "domain", "from": "built for the domain layer", "note": "N-fold angular mirror. Turns any source into a mandala, and the fold count riding u_sub means a slider sweeps through symmetry orders instead of one fixed look.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
float n = floor(3.0 + u_sub*2.0);
float a = atan(uv.y, uv.x), r = length(uv);
float seg = 6.28318530718 / n;
a = abs(mod(a + seg*0.5, seg) - seg*0.5);
uv = vec2(cos(a), sin(a)) * r;
