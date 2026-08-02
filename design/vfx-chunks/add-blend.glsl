//! {"name": "add-blend", "kind": "blend", "from": "standard", "note": "Straight addition. Correct for LIGHT -- two emitters in the same space add, they do not average -- which is why it is the default for combining fields rather than mix.", "order": 50, "cat": "blend", "in": {"col": "vec3", "colB": "vec3"}, "out": {"col": "vec3"}}
col = col + colB;
