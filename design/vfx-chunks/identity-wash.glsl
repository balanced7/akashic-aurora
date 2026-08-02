//! {"name": "identity-wash", "kind": "modifier", "from": "the avatar identity gradient", "note": "Pulls the image toward the agent's identity gradient without overriding the state hue. Keeps the WHO/WHAT split intact: identity tints the body, state owns the accents.", "order": 50}
col = mix(col, col*mix(u_id0,u_id1,clamp(gl_FragCoord.x/u_res.x,0.,1.))*2.0, 0.35);
