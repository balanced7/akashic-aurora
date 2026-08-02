//! {"name": "zoom-pulse", "kind": "domain", "from": "built for the domain layer", "note": "Breathing scale about the centre. The cheapest way to give a static source a heartbeat, and it stacks under everything else because it only touches magnitude.", "order": 50, "cat": "domain", "in": {"uv": "vec2"}, "out": {"uv": "vec2"}}
uv *= 1.0 + 0.35 * u_pulse * sin(u_time * 1.3);
