//! {"name": "ray-aa3", "kind": "helper", "cat": "E5", "family": "E", "version": "1.0.0", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["John C. Hart, 'Sphere tracing: a geometric method for the antialiased ray tracing of implicit surfaces' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): the pixel as a cone, and the closest approach of a near miss as the coverage of a disk cut by a straight edge",
//!   "Wikipedia, 'Circular segment' (https://en.wikipedia.org/wiki/Circular_segment): the area of a disk beyond a chord",
//!   "Inigo Quilez, 'Antialias, sort of' (https://www.shadertoy.com/view/llXGR4): one ray, partial coverage at every near intersection"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Coverage in [0, 1] of a pixel, modelled as a disk one pixel across, by a straight silhouette edge. aaConeCoverage(minDistOverT, pixelAngle) takes the smallest d / t a march recorded (rmSphereTrace's .z) and the camera's pixel angle: it is 1 for minDistOverT <= 0.5 pixelAngle (every hit, since rmEpsilon stops at half a pixel), 0.5 at one pixel and 0 from 1.5 pixels, the disk's area beyond an edge placed a whole pixel outside the true surface so the ramp meets the hits without a step; the half-coverage line therefore sits one pixel outside the true silhouette. ACCEPTED, NOT A DEFECT (batch-B review, 2026-10-13): a marched silhouette antialiased this way reads about one pixel fat. The fatness comes from the hits, not from this ramp: every ray that passes within half a pixel of a surface already stops as a hit at coverage 1, so a ramp centred on the true silhouette would put a step between the hits and the near misses, which shows as a ring. A pixel-exact edge needs the true surface: aaDiscriminantEdge for an analytic object (its half-coverage line sits on the rim), or a march whose hits are refined to the surface before this is applied. aaDiscriminantEdge(disc, px) takes a ray-quadric discriminant that crosses 0 at the silhouette and grows inward (for a unit ray and a sphere of radius r: r^2 minus the squared closest distance of the ray to the centre, about 2r times the distance inside the rim) and px, one pixel in the same units (2 r pixelAngle t for that sphere): 0.5 exactly on the rim, 1 half a pixel inside, 0 half a pixel outside.",
//!  "note": "A march answers hit or miss, and that boolean IS the staircase: rendering at a higher resolution only draws a finer staircase (shader-craft floor 6). The closest approach the march already measured turns the boolean into coverage for the price of one min() a step: composite the near-miss band over the background with it (a near miss is by definition next to the rim it smooths, so shade it with the rim's colour). Never antialias a silhouette with fwidth or dFdx of anything downstream of the march; the derivative of a jump is a spike. For an analytic object (glass marble, bubble, planet) the discriminant gives the exact edge, and the same number says 'do not refract this close to the rim' and where to darken a silhouette. Wrong looks like a one-pixel bright or dark ring at the silhouette (coverage that does not meet the hits at 1), a halo two pixels wide (the march's pixelAngle and this one disagree), or edges whose softness changes with resolution (a px that is not one pixel).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "ray-aa3.card", "twin": "arsenal/shaders/twins/ray.py",
//!  "status": "P0",
//!  "exemplars": ["XsSGDh", "NslGRN"],
//!  "learn": ["SR 7.1", "SR 7.2", "SR 7.3", "study:XsSGDh 6.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the geometry and the sources credited above.
//
// WHY. A pixel is not a point; it is a small cone of directions. Near a silhouette part of that cone hits the object
// and part misses, and the honest colour is the mix. Assume the edge is straight at the pixel's scale and the covered
// part of the pixel disk is a circular segment, whose area has a closed form: (acos x - x sqrt(1 - x^2)) / pi for an
// edge x radii from the centre.

// Silhouette coverage from the closest angular approach of a march (its d / t), for pixels of angle pixelAngle.
float aaConeCoverage(float minDistOverT, float pixelAngle) {
    // where the edge crosses the pixel disk, in disk radii: -1 at half a pixel of clearance (fully covered), +1 at 1.5
    float across = clamp(2.0 * minDistOverT / max(pixelAngle, 1e-12) - 2.0, -1.0, 1.0);
    float segment = acos(across) - across * sqrt(max(1.0 - across * across, 0.0));
    return segment / PI;
}

// Coverage from a ray-quadric discriminant disc (positive inside the silhouette) and px, one pixel in disc's units.
float aaDiscriminantEdge(float disc, float px) {
    // the rim's place across the pixel disk, in disk radii: 0 on the rim, -1 half a pixel inside (fully covered)
    float across = clamp(-2.0 * disc / max(px, 1e-12), -1.0, 1.0);
    float segment = acos(across) - across * sqrt(max(1.0 - across * across, 0.0));
    return segment / PI;
}
