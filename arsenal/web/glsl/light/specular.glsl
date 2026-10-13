//! {"name": "light-specular", "kind": "helper", "cat": "F2", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["James F. Blinn, 'Models of light reflection for computer synthesized pictures' (SIGGRAPH 1977; https://en.wikipedia.org/wiki/Blinn%E2%80%93Phong_reflection_model): the half vector",
//!   "Tomas Akenine-Moller, Eric Haines and Naty Hoffman, Real-Time Rendering, 3rd edition (2008, https://www.realtimerendering.com/), section 7.6: the (s + 8) / (8 pi) normalisation",
//!   "Fabian Giesen, 'The Blinn-Phong normalization zoo' (https://www.farbrausch.de/~fg/stuff/phong.pdf): why the factor and how close it is"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "litBlinnPhong(n, h, s) is the normalised Blinn-Phong BRDF lobe (s + 8) / (8 pi) * max(n.h, 0)^s, per steradian, with n and h unit vectors (h = normalize(l + v), v toward the eye) and s floored at 0. Seen head-on its directional albedo is s (s + 8) / ((s + 2)(s + 4)): within 7 per cent of 1 for every s >= 16 and closer as s grows, so the highlight's total light stays constant while it sharpens and only its peak climbs. Under the house's pi-folded light colours (litLambert) a light's specular is PI * litBlinnPhong(n, h, s) * max(n.l, 0) * lightCol; without the PI it is pi times too dim against the diffuse.",
//!  "note": "A highlight is the light source seen in a slightly rough mirror: the sharper the mirror, the smaller and hotter the dot. Normalised, a shiny ball shows a small, very bright dot; unnormalised (a bare pow), the dot also dims as it shrinks, which reads as cheap plastic. Shade specular only where n.l > 0 and multiply it by the same shadow as the diffuse; build h from v = -rayDirection, never from the ray direction itself. It is the classic lobe, cheap and well understood; GGX (planned, P1) has the long glowing tail measured materials show. Wrong looks like a highlight that fades as it sharpens (no normalisation), a highlight on the dark side (missing n.l), or one in the wrong place (h built from the ray direction).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "light-specular.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["cs2GWD", "llK3Dy", "4lj3Ww"],
//!  "learn": ["LM 1.3", "LM 3.1", "LM 3.2", "LM 15"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. A polished surface does not make light; it concentrates it. Raising the exponent narrows the lobe, so the same
// energy must go into a smaller dot that gets brighter: the (s + 8) / (8 pi) factor is that bookkeeping, like a lens
// that focuses the same sunlight into a smaller, hotter spot.

// The normalised Blinn-Phong lobe for unit normal n, unit half vector h and shininess s.
float litBlinnPhong(vec3 n, vec3 h, float shininess) {
    float sharp = max(shininess, 0.0);
    float alignment = max(dot(n, h), 0.0);
    float energyKeep = (sharp + 8.0) / (8.0 * PI);
    return energyKeep * safePow(alignment, sharp);
}
