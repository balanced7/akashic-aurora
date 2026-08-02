//! {"name": "hash31", "kind": "helper", "from": "used everywhere today", "note": "Cheap 3D hash. Good enough for value noise, not good enough for anything that must not band.", "order": 10}
float h31(vec3 p){ return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453123); }
