//! {"name": "noise-mask", "kind": "mask", "from": "value-noise-3d", "note": "A drifting noise mask. Feed it to mix-blend to dissolve one field into another unevenly, which is the thing a linear chain simply cannot express. Needs value-noise-3d.", "order": 50, "cat": "mask", "in": {}, "out": {"m": "float"}}
m = smoothstep(0.35, 0.75, fbm3(vec3(uv*2.2, u_time*0.12)));
