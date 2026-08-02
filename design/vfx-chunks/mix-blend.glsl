//! {"name": "mix-blend", "kind": "blend", "from": "standard", "note": "A straight 50/50 mix. Attach a mask to the mix port to make it uneven -- that edge is the one a chain cannot draw.", "order": 50, "cat": "blend", "in": {"col": "vec3", "colB": "vec3"}, "out": {"col": "vec3"}}
col = mix(col, colB, 0.5);
