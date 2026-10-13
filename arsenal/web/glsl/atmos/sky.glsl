//! {"name": "atmos-sky", "kind": "helper", "cat": "G6", "family": "G", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'outdoors lighting' and 'fog' (https://iquilezles.org/articles/outdoorslighting/, https://iquilezles.org/articles/fog/): a sky from a zenith and a horizon colour, warmed toward the sun",
//!   "Sebastien Hillaire, 'A Scalable and Production Ready Sky and Atmosphere Rendering Technique' (EGSR 2020, https://sebh.github.io/publications/egsr2020.pdf): why the horizon is pale and the sunward horizon warm (Rayleigh and Mie scattering over a longer path)"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "skyGradient(rd, toSun, zenith, horizon, sunTint) mixes three linear colours; rd and toSun are unit vectors, y up. With e = max(rd.y, 0): exactly zenith overhead (e = 1), the horizon colour at and below the horizon (e = 0), and mix(zenith, horizonColour, (1 - e)^k) between. horizonColour is mix(horizon, sunTint, glow) and k is mix(6, 1.5, glow), where glow = lowSun * f^4, f = 0.5 + 0.5 dot(rdFlat, toSun) with rdFlat the direction lifted to the horizon when below it, and lowSun = 1 - smoothstep(0, 0.6, toSun.y): so the band is thin away from the sun and wide toward a low (or set) sun, whose horizon takes sunTint, and a sun higher than about 37 degrees leaves the horizon its own colour all round. Below the horizon a direction takes the horizon colour of its azimuth. Every result lies within the three colours (a mix, never an extrapolation).",
//!  "note": "The backdrop of every outdoor or night scene in one call: a deep zenith, a paler horizon, and a warm glow that hugs the horizon under a low sun and spreads up toward it. For a pre-dawn or aurora sky put the sun a few degrees below the horizon with a dim rose sunTint and a near-black zenith; for day, a blue zenith and a pale horizon. Composite emissive things (stars, aurora) ADD over it, and use the same horizon colour as the fog colour of the ground (fogExp) so they meet without a line. It is a painted sky, not a scattering simulation: no sun disk, no multiple scattering, no colour of its own. Wrong looks like a glow opposite the sun (toSun negated), a hard line at the horizon (fog colour and horizon colour differ), or a warm horizon under a midday sun (sunTint where horizon was meant).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "atmos-sky.card",
//!  "twin": "arsenal/shaders/twins/atmos.py", "status": "P0", "exemplars": ["ttScDc", "XtS3DD"],
//!  "learn": ["VA 4.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. Looking straight up you see through the thinnest air, so the sky is deepest there; toward the horizon the path
// through the air grows many times longer, scattered light piles up and the sky pales. Toward a low sun that long path
// has lost its blue on the way, so the horizon there glows warm, and the glow widens the closer you look to the sun.

// A sun-aware sky from three colours: zenith overhead, horizon at the horizon, warmed toward a low sun.
vec3 skyGradient(vec3 rd, vec3 toSun, vec3 zenith, vec3 horizon, vec3 sunTint) {
    float elevation = min(max(rd.y, 0.0), 1.0);           // sin of the elevation, 0 at and below the horizon
    vec3 lifted = vec3(rd.x, max(rd.y, 0.0), rd.z);                     // below the horizon: its horizon azimuth
    lifted *= inversesqrt(max(dot(lifted, lifted), 1e-12));
    float facing = 0.5 + 0.5 * dot(lifted, toSun);                      // 1 looking at the sun, 0 away from it
    float lowSun = 1.0 - smoothstep(0.0, 0.6, toSun.y);
    float facing2 = facing * facing;
    float glow = lowSun * facing2 * facing2;
    vec3 horizonColour = mix(horizon, sunTint, glow);
    float band = pow(1.0 - elevation, mix(6.0, 1.5, glow));                    // thin away from the sun, wide toward it
    return mix(zenith, horizonColour, band);
}
