//! {"name": "swirl", "kind": "domain", "from": "built for the domain layer", "note": "Rotation by radius, so the centre stays put and the rim drags behind. The classic and still the best: it deforms without destroying, so whatever you feed it stays recognisable.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
float r = length(uv);
float a = (1.6 + u_star*2.0) / (1.0 + r*2.0) + u_time*0.15*(0.3+u_spin);
float c = cos(a), s = sin(a);
uv = mat2(c,-s,s,c) * uv;
