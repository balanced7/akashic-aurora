//! {"name": "desaturate-unsensed", "kind": "modifier", "from": "the avatar state codebook", "note": "Drives saturation from u_sat so 'we cannot see this agent' renders as grey rather than as a colour that means something else. Absence of colour is the honest rendering of absence of data.", "order": 50}
col = mix(vec3(dot(col,vec3(0.299,0.587,0.114))), col, u_sat);
