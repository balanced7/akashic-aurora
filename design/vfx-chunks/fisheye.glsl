//! {"name": "fisheye", "kind": "domain", "from": "built for the domain layer", "note": "Radial power curve: pincushion below 1, barrel above. Bends straight structure into something lens-like, which is why it pairs so well with tile and kaleido.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
float r = length(uv);
uv *= pow(max(r,1e-4), (0.55 + u_round*1.1)) / max(r,1e-4);
