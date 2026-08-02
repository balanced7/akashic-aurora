//! {"name": "screen-blend", "kind": "blend", "from": "standard", "note": "Screen: 1-(1-a)(1-b). Brightens without clipping the way addition does, so it is the safer choice when both inputs are already near the top of the range.", "order": 50, "cat": "blend", "in": {"col": "vec3", "colB": "vec3"}, "out": {"col": "vec3"}}
col = 1.0 - (1.0 - clamp(col,0.,1.)) * (1.0 - clamp(colB,0.,1.));
