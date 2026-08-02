//! {"name": "ripple", "kind": "domain", "from": "built for the domain layer", "note": "Radial sine displacement travelling outward. Reads as a disturbance PROPAGATING rather than a surface wobbling, because the phase depends on radius and time together.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
float r = length(uv);
uv += normalize(uv + 1e-6) * sin(r*(6.0+u_sub*2.0) - u_time*2.2) * (0.06 + 0.10*u_pulse);
