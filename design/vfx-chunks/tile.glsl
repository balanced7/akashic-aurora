//! {"name": "tile", "kind": "domain", "from": "built for the domain layer", "note": "Repeat space on a lattice. One object becomes a field of them -- and because it happens in the DOMAIN, every copy animates in step with the original rather than being a stamped duplicate.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
float k = 1.0 + floor(u_sub);
uv = fract(uv * k * 0.5 + 0.5) * 2.0 - 1.0;
