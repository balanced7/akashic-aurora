//! {"name": "filmic-curve", "kind": "modifier", "from": "the compositing shader Daniil pasted", "note": "pow(0.8) then a lift/roll. Lifted blacks and rolled whites are why film reads as film rather than as crushed digital. Lifts the floor OFF black, so it fights a true-black brief -- pick this or the black background, not both.", "order": 50, "cat": "tone", "in": {"col": "vec3"}, "out": {"col": "vec3"}}
col = pow(max(col,0.), vec3(0.8));
col = mix(vec3(0.06), vec3(0.94), col);
