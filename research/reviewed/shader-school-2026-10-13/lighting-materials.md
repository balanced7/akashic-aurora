# Lighting, shading and materials for shader art

House shader school, 2026-10-13. Researcher topic 4 of 8. Written for a capable programmer who has
never written a shader, and for Daniel, who learns fast and likes hardware analogies.

Licence line: every technique below is described in my own words and in mathematics. Pointers into
the corpus (`state/arsenal/shaders/corpus/shaders/<id>/<file>:<line>`) are for study only; no
corpus code is reproduced here. The primitive API in section 16 is freshly written signatures with
contracts, no bodies copied from anywhere.

---

## 0. The whole topic on one page

A pixel's colour is an energy budget. Light arrives from a few places (a sun, the sky, other
surfaces, things that glow), each arrival is reduced by what blocks it (shadow, occlusion,
absorption), and the surface decides how much of what arrives leaves toward the camera, depending
on the angles involved (the material). Everything in this report is one of those three jobs:

| Job | Hardware analogy | Techniques in this report |
|---|---|---|
| **Sources**: where light comes from | the power supply rails | directional sun, point/spot, sphere and tube lights, procedural sky, environment maps, spherical-harmonic irradiance, emissive surfaces, glow |
| **Visibility**: what blocks it | the bus arbitration: who actually gets through | hard and soft shadows, ambient occlusion, specular occlusion, horizon occlusion, absorption (Beer-Lambert) |
| **Response**: what the surface sends to the eye | the transfer function of a filter | Lambert, wrap, Blinn-Phong, GGX/Cook-Torrance, Fresnel, subsurface fakes, refraction, dispersion, thin film, metals |

Ten laws the best shader artists actually follow (each is explained later):

1. **Work in linear light, encode once at the very end.** Colour pickers give sRGB; convert in, do
   all lighting in linear, tonemap, then encode to sRGB.
2. **Albedos are dim; lights are bright.** Real diffuse albedos are mostly 0.04-0.8, and iq keeps
   his under about 0.2 for outdoor scenes. "If you need a brighter image, make the lights
   brighter, not the materials" (Inigo Quilez, outdoors lighting article).
3. **One light rig, separate visibility per light.** Key light gets the shadow ray; fill and sky
   get ambient occlusion. Never put ambient occlusion on the key light (iq says it looks "horribly
   CG").
4. **Specular is not a sticker.** It is Fresnel times a microfacet distribution times masking,
   and it is shadowed exactly like the diffuse from the same light.
5. **Fresnel everywhere.** Every surface becomes a mirror at grazing angles; the floor value (F0)
   is about 0.04 for nearly every non-metal and is the coloured "base colour" for metals.
6. **Metals have no diffuse.** A metal is entirely reflection, so its look *is* its environment.
   A metal in a flat grey world looks like grey plastic.
7. **Roughness is perceptual; square it.** Artists dial "roughness"; the maths uses
   alpha = roughness squared.
8. **Shadows and occlusion from a distance field are almost free per sample, not free in total.**
   Budget them like memory reads: count `map()` calls per pixel.
9. **Glow must be integrated, not counted.** Anything accumulated along a march must be weighted
   by step length, or it changes when the step count changes.
10. **Calibrate with known targets.** A grey ball, a chrome ball, and the white furnace test (a
    white object in a uniformly white world must vanish) catch most lighting bugs blind.

---

## 1. The physics in plain words

### 1.1 Quantities you actually need

- **Radiance** (L): how bright a ray is. Every pixel stores the radiance of the camera ray through
  it. Radiance is constant along a ray in empty space; that is why a far white wall is as bright
  per pixel as a near one, just smaller.
- **Irradiance** (E): how much light power lands on a patch of surface, summed over all incoming
  directions. A sun with intensity I, at angle theta from the surface normal, delivers
  `E = I * cos(theta) = I * max(dot(n, l), 0)`. The cosine is just geometry: a beam hitting at a
  slant spreads over more area (like a torch beam on the floor becoming an ellipse).
- **BRDF** (bidirectional reflectance distribution function), written `f(l, v)`: for light arriving
  from direction `l` and the eye in direction `v`, the fraction of irradiance that leaves as
  radiance toward the eye. It is the material's transfer function.

### 1.2 The one equation

The reflectance (rendering) equation, in words: outgoing radiance toward the eye equals emitted
radiance plus the sum, over every incoming direction on the hemisphere above the surface, of
(incoming radiance) times (BRDF) times (cosine of the incoming angle).

```
L_out(v) = L_emit + integral over hemisphere of  L_in(l) * f(l, v) * max(dot(n,l), 0)  dl
```

Real-time shading is the art of approximating that integral cheaply:

- a **punctual light** (sun, point light) is a single direction, so the integral collapses to one
  term: `L_out = f(l, v) * I_light * max(dot(n,l),0) * visibility`;
- **ambient / sky / environment** light comes from everywhere, so we use precomputed or closed-form
  stand-ins (hemisphere gradients, spherical harmonics, prefiltered maps) times an occlusion
  estimate.

Hardware analogy: the integral is a dot product between two "signals over the sphere", the
lighting and the material lobe. Cheap shading is choosing a basis in which that dot product is a
handful of multiply-adds instead of thousands of samples.

### 1.3 Energy conservation, and the pi

A surface cannot reflect more than it receives. For the perfectly matte (Lambertian) surface with
albedo `rho` (fraction of light reflected, 0..1), the BRDF is the constant `rho / pi`. The `1/pi`
appears because integrating `cos(theta)` over a hemisphere gives `pi`, so the constant must be
divided by pi for the total reflected power to equal `rho` times the received power.

Shader-art convention: almost everyone folds the pi into the light colour, writing
`col = albedo * lightColour * max(dot(n,l),0)`. That is fine as long as it is done consistently.
Mixing conventions (Lambert with pi, specular without) makes specular look five times too strong
or too weak. The house library must pick one and say so (section 16 picks "pi folded into lights",
with GGX terms carrying their own normalisation).

### 1.4 Linear light and the display

Monitors expect sRGB-encoded values (roughly value^(1/2.2)). Lighting maths only works on linear
values: adding two lights must add their energies. Rules:

- Convert every hand-picked colour from sRGB to linear before using it as albedo or light colour.
- Do all lighting, fog and glow in linear, in high dynamic range (values above 1 are allowed).
- Tonemap (compress HDR into 0..1; the house already owns `tanh-tonemap` and
  `superlinear-highlight` chunks in `design/vfx-chunks/`), then encode to sRGB, then dither.

iq's outdoors article makes the point that once you are linear, plain `dot(n,l)` gives realistic
falloff and you stop needing hacks to "soften" diffuse.

---

## 2. Diffuse response

### 2.1 Lambert

`diffuse = albedo * max(dot(n, l), 0)` (pi folded). The clamp matters: a negative dot means the
light is behind the surface.

### 2.2 Non-physical but useful softeners

- **Half-Lambert** (Valve, Mitchell, McTaggart and Green, SIGGRAPH 2006): remap `dot(n,l)` from
  -1..1 to 0..1 by halving and adding a half, then square: `(0.5*dot(n,l) + 0.5)^2`. The back of an
  object keeps shape instead of going flat black. Not energy-conserving; it is a stylisation.
- **Wrap lighting** (Simon Green, GPU Gems 1 ch. 16): `(dot(n,l) + w) / (1 + w)`, clamped, with
  wrap `w` in 0..1. Light wraps past the terminator (the line between lit and unlit), which reads
  as softness or translucency. Steve McAuley and Stephen Hill showed it needs an extra division by
  `(1 + w)` to conserve energy: `(dot(n,l) + w) / (1 + w)^2`.
- **Terminator scatter colour** (Green; also used for skin by iq in "Selfie Girl",
  corpus `WsSBzh/image.glsl:521`): on the dark side just past the terminator add a band of warm
  colour whose width is the subsurface radius. Light penetrates skin a few millimetres, so the
  shadow edge on skin is red, not grey.

### 2.3 Physically richer diffuse

- **Burley / Disney diffuse** (Brent Burley, SIGGRAPH 2012): Lambert times two Fresnel-like
  factors, one for the light angle and one for the view angle:
  `f_d = (albedo/pi) * (1 + (F90 - 1)(1 - NoL)^5) * (1 + (F90 - 1)(1 - NoV)^5)`,
  with `F90 = 0.5 + 2 * roughness * LoH^2` (`LoH` is the cosine between light and half vector).
  Rough surfaces get brighter at grazing angles (retro-reflection, the "dusty" rim of velvet and
  clay); smooth ones get slightly darker there. Filament and Karis both judged it not worth its
  cost for real-time; for shader art it is a cheap way to make clay and fabric read correctly.
- **Earl Hammon (GDC 2017)** derived a diffuse model from the same GGX microsurface as the
  specular, so diffuse and specular agree on roughness. Worth knowing; rarely needed in art.
- **Oren-Nayar** (1994) is the classic rough-diffuse model (moon, plaster). Burley is cheaper and
  close enough.

### 2.4 Sky (hemisphere) light

The sky is a big dome light. A normal pointing straight up sees the whole sky; a normal pointing
sideways sees half; pointing down sees none (but sees the ground). Two cheap forms:

- `skyAmount = 0.5 + 0.5 * n.y`. This is exact, not a hack: a plane tilted by angle theta from
  vertical, under a uniformly bright sky dome and with nothing in the way, receives
  `(1 + cos(theta)) / 2` of the irradiance a level plane gets.
- iq often takes the square root of that, which keeps sideways faces brighter; see the "sky" block
  in `Xds3zN/image.glsl:568` (MIT licensed).
- A **hemisphere light** mixes two colours: `mix(groundColour, skyColour, 0.5 + 0.5*n.y)`. The
  ground colour is a free fake of light bouncing off the floor.

### 2.5 The directional-derivative trick (iq)

For a distance field or a density field, the diffuse term along one light can be computed with
one extra field evaluation instead of a full normal: the change of the field when stepping a
small `eps` toward the light, divided by `eps`, *is* `dot(gradient, l)`, which for a distance
field is `dot(n, l)`. iq reports about 3.5 times faster than gradient-then-dot for one light. It
is the standard way to light volumetric clouds. It stops paying off after three or four lights.

---

## 3. Specular, the classic way

### 3.1 Phong and Blinn-Phong

- **Phong** (Bui Tuong Phong, 1975): reflect the light about the normal, `r = reflect(-l, n)`, and compare it with the
  view: `spec = max(r·v, 0)^s` where `s` is shininess.
- **Blinn-Phong** (Jim Blinn, 1977): use the **half vector** `h = normalize(l + v)` (the direction a
  microscopic mirror would need to face to bounce `l` into `v`) and compute `max(dot(n,h),0)^s`.
  Cheaper and closer to measured materials, and it is the conceptual bridge to microfacets.

### 3.2 Normalisation: why unnormalised Blinn-Phong is wrong

Raising the exponent makes the highlight smaller; unnormalised it also makes it *darker in total*,
which is backwards (a polished surface concentrates energy, it does not lose it). Multiplying by a
normalisation factor keeps the total reflected energy constant:

- Phong lobe: multiply by `(s + 2) / (2*pi)`.
- Blinn-Phong as a BRDF: the common approximation is `(s + 8) / (8*pi)` (Real-Time Rendering;
  derivations by Fabian Giesen and Christian Schüler).

On screen: with normalisation, a shiny ball shows a small *very bright* dot; without it, a small
*dim* dot, which reads as plastic.

### 3.3 Exponent to roughness

Walter et al. (2007) give the equivalence between a Blinn-Phong exponent `s` and the Beckmann/GGX
width `alpha`: `s = 2/alpha^2 - 2`. Use it to port old shaders to the microfacet model.

### 3.4 Two-lobe specular

Measured materials have a sharp core and a long glowing tail around highlights (Burley 2012
showed this across the MERL database). A cheap way to fake the tail with Blinn-Phong is two lobes,
one tight and strong, one wide and weak. iq does exactly this in "Snail" (`ld3Gz2/image.glsl:643`).
GGX has the long tail built in, which is the main reason it replaced Blinn-Phong.

---

## 4. Microfacet theory: Cook-Torrance with GGX

### 4.1 The model

Imagine the surface as millions of tiny perfect mirrors (microfacets), each facing a slightly
different direction. Only the facets whose normal equals the half vector `h` can bounce light from
`l` into `v`. The specular BRDF (Cook and Torrance 1982; modern form as in Karis 2013 and Filament):

```
f_spec(l, v) = D(h) * F(v, h) * G(l, v, h) / (4 * NoL * NoV)
```

- **D**, the normal distribution function: what fraction of facets face `h`. A histogram of facet
  orientations. Smooth surface = tall narrow spike; rough = wide low hill.
- **F**, Fresnel: how much a facet reflects at this angle (section 5).
- **G**, geometric masking-shadowing: the fraction of those facets that are neither hidden from the
  eye nor shadowed from the light by neighbouring bumps. Like occupancy: the facets exist but the
  bus is blocked.
- **4 NoL NoV**: the Jacobian (change-of-variables factor) between "facet normals" and
  "light/view directions". It is why grazing views get brighter specular and why `G` must cancel it
  at grazing angles (otherwise you divide by zero).

Many engines fold `G / (4 NoL NoV)` into one **visibility term V**, so `f_spec = D * V * F`.

### 4.2 D: GGX (Trowbridge-Reitz)

Trowbridge and Reitz (1975) wrote the distribution; Walter et al. (2007) brought it to graphics as
GGX. With `alpha = roughness^2`:

```
D(h) = alpha^2 / ( pi * ( NoH^2 * (alpha^2 - 1) + 1 )^2 )
```

At `NoH = 1` (facets facing straight at h) it peaks at `1/(pi*alpha^2)`: smooth surfaces have a
huge, tiny peak. The long tail is what gives GGX highlights their soft glow.

Anisotropic GGX (brushed metal, hair-like streaks) uses two alphas along tangent and bitangent:
`alpha_t = alpha*(1+a)`, `alpha_b = alpha*(1-a)` for anisotropy `a` in -1..1 (Kulla's
parametrisation as reproduced in Filament), and replaces `NoH^2*(alpha^2-1)+1` by the ellipse
`(t.h/alpha_t)^2 + (b.h/alpha_b)^2 + NoH^2`, with prefactor `1/(pi*alpha_t*alpha_b)`.

### 4.3 Why alpha = roughness squared

Karis (UE4) and Burley both found that squaring makes the slider perceptually even. Without it,
everything interesting happens in the bottom 5% of the slider.

### 4.4 G / V: Smith masking-shadowing

Eric Heitz (2014) showed that the Smith family is the right one and explained the height-correlated
form. Three versions in order of cost:

1. **Separable Schlick-Smith** (Karis): `G1(x) = NoX / (NoX*(1-k) + k)`, `G = G1(l)*G1(v)`.
   `k = alpha/2` for environment lighting. For punctual lights Karis remaps roughness to
   `(roughness+1)/2` before squaring, giving `k = (roughness+1)^2 / 8`, to tame "hot" rims on very
   smooth surfaces.
2. **Height-correlated Smith visibility** (Heitz; Filament's choice):
   `V = 0.5 / ( NoL*sqrt(NoV^2*(1-alpha^2) + alpha^2) + NoV*sqrt(NoL^2*(1-alpha^2) + alpha^2) )`.
   This already includes the `1/(4 NoL NoV)`.
3. **Fast approximation** (Filament, after Hammon): drop the square roots:
   `V = 0.5 / ( NoL*(NoV*(1-alpha) + alpha) + NoV*(NoL*(1-alpha) + alpha) )`.

### 4.5 Putting a light together

For one light of radiance colour `C`, direction `l`, visibility (shadow) `S`:

```
NoL = max(dot(n,l), 0)
radiance_out = C * S * NoL * ( diffuseColour * Fd  +  D * V * F )
```

where `Fd = 1` for Lambert (pi folded into C) or the Burley factor. Note the shadow multiplies the
specular too; iq's primitives shader shows the habit of multiplying specular by the shadowed
diffuse term (`Xds3zN/image.glsl:561`).

### 4.6 The metallic workflow (Burley 2012, Karis 2013, Filament)

Four numbers describe almost every opaque material:

- **baseColor**: albedo for non-metals, reflectance colour (F0) for metals; sRGB-picked, convert.
- **metallic**: 0 or 1 in practice (in-between only for blends, e.g. dust on metal).
- **roughness**: perceptual, 0..1; `alpha = roughness^2`.
- **reflectance** (non-metals only): Filament maps it as `F0 = 0.16 * reflectance^2`, so the default
  0.5 gives F0 = 0.04. (UE4 uses `F0 = 0.08 * specular` with default 0.5.)

Resolve:

```
diffuseColour = (1 - metallic) * baseColor
F0            = mix(vec3(0.16*reflectance^2), baseColor, metallic)
alpha         = clamp(roughness^2, alpha_min, 1)
```

LearnOpenGL's warning worth repeating: the Fresnel term already *is* the "specular fraction", so do
not multiply the specular by an extra `ks`.

### 4.7 Energy loss at high roughness, and its fix

The single-bounce microfacet model ignores light that bounces between facets more than once, so
rough surfaces (especially rough metals) come out too dark. Krzysztof Narkowicz's white furnace
test makes this visible: a rough sphere with F0 = 1 inside a uniformly white world should vanish,
and instead it shows a dark rim and a darker body as roughness increases.

Fixes, cheapest first:

- **Kulla-Conty style compensation** (Kulla and Conty, SIGGRAPH 2017; Lagarde's variant in
  Filament): multiply the specular by `1 + F0 * (1/E_white - 1)`, where `E_white` is the
  directional albedo of the BRDF with F0 = 1 at this roughness and view angle (the "A + B" of the
  environment BRDF in 8.4).
- **Fdez-Agüera (JCGT 2019)** for image-based lighting: if the single-scatter specular energy is
  `FssEss = F0*A + B` and the white-F0 energy is `Ess = A + B`, then `Ems = 1 - Ess` is what is
  lost; the average Fresnel over the hemisphere is `Favg = F0 + (1 - F0)/21` (closed form for
  Schlick: the cosine-weighted average of `(1 - mu)^5` over `mu = cos(theta)` in 0..1 is
  `integral of 2*mu*(1 - mu)^5 dmu = 2 * (1! * 5!)/7! = 1/21`); summing the geometric series of extra bounces gives a multiple-scatter term
  `Fms*Ems` with `Fms = FssEss*Favg / (1 - Ems*Favg)`. For dielectrics the diffuse then gets what
  is left: `diffuse weight = albedo * (1 - (FssEss + Fms*Ems))`. Total cost: a few multiply-adds.

### 4.8 Minimum roughness, and specular aliasing

Filament clamps `alpha >= 0.089` because half-precision floats underflow in `1/alpha^4`. The house
uses `highp`, so the precision reason mostly goes away, but the visual one does not: a perfectly
smooth surface with a point light produces a highlight smaller than a pixel, which flickers as
things move (**specular aliasing**, "fireflies"). Remedies:

- clamp alpha to a small minimum (try 0.002-0.01 in fp32 for analytic lights);
- **geometric specular anti-aliasing** (Kaplanyan 2016; Tokuyoshi and Kaplanyan 2019; the form
  used in Filament and HDRP): measure how fast the normal changes across the pixel with screen-space
  derivatives, `variance ~ scale * (|dFdx(n)|^2 + |dFdy(n)|^2)`, and add a clamped amount of it to
  `alpha^2`. Filament's defaults are a scale near 0.15 and a clamp near 0.2;
- distance-based normal smoothing, as afl_ext does in the MIT-licensed ocean
  (`MdXyzX/image.glsl:202`): blend the normal toward the average surface normal as distance grows.

---

## 5. Fresnel

### 5.1 What it is

At a boundary between two materials, part of the light reflects and part enters. The reflected
fraction depends on the angle: at normal incidence it is small (F0), at grazing incidence it rises
to 1. Every material does this; it is why a lake mirrors the far shore but lets you see the bottom
at your feet.

### 5.2 F0 from the index of refraction

For a non-metal with index of refraction (IOR) `n` against air:

```
F0 = ((n - 1) / (n + 1))^2
```

Water (1.33) gives 0.02; glass and most plastics (1.5) give 0.04; diamond (2.42) gives about 0.17.
This is why "0.04 for every non-metal" works so well.

### 5.3 Schlick's approximation

Christophe Schlick (1994):

```
F(theta) = F0 + (1 - F0) * (1 - cos(theta))^5
```

Use `cos(theta) = dot(v, h)` inside the microfacet BRDF and `dot(n, v)` for environment and rim
effects. Karis gives a spherical-Gaussian form that replaces the fifth power with
`2^((-5.55473*c - 6.98316)*c)` for `c = cos(theta)`, slightly cheaper on old hardware. A variant
with an explicit grazing value `F90` (Filament) lets specular occlusion or clear-coat reduce the
grazing peak.

### 5.4 The exact dielectric Fresnel, and total internal reflection

For glass you need the exact form when light goes from dense to less dense (from inside glass out
to air), because past the **critical angle** nothing exits: **total internal reflection** (TIR).
Sébastien Lagarde's "Memo on Fresnel equations" gives the unpolarised result, with
`eta = n_transmitted / n_incident` and `c = cos(theta_incident)`:

```
g^2 = eta^2 - 1 + c^2         (if g^2 < 0: TIR, F = 1)
g   = sqrt(g^2)
F   = 0.5 * ((g - c)/(g + c))^2 * (1 + ((c*(g + c) - 1)/(c*(g - c) + 1))^2)
```

Schlick fails from the dense side unless you feed it the *transmitted* angle's cosine, and it
never produces TIR on its own. Practical rule: use Schlick for the outside, exact (or
"Schlick plus a TIR test") for the inside of glass.

### 5.5 Metals

Metals have a complex IOR `n + ik` per wavelength, giving coloured F0 and a coloured grazing
transition. Formula at normal incidence: `F0 = ((n-1)^2 + k^2) / ((n+1)^2 + k^2)`. In RGB
rendering Naty Hoffman's "Fresnel Equations Considered Harmful" (2019) argues Schlick with a
coloured F0 matches measured metals better than RGB-sampled exact Fresnel; Ole Gulbrandsen's
"Artist Friendly Metallic Fresnel" (JCGT 2014) gives an artist parametrisation by reflectivity and
**edge tint** (the colour at grazing angles) that maps back to `n, k`.

F0 for common metals (Filament's table, given as sRGB colours to paste into a picker; convert to
linear before use):

| Metal | F0 (sRGB) |
|---|---|
| Silver | 0.97, 0.96, 0.91 |
| Aluminium | 0.91, 0.92, 0.92 |
| Gold | 1.00, 0.85, 0.57 |
| Copper | 0.97, 0.74, 0.62 |
| Iron | 0.77, 0.78, 0.78 |

Chromium sits around linear 0.55 grey (Real-Time Rendering's table). Non-metal F0 is linear 0.02
(water) to 0.05 (glass, plastic), gemstones up to about 0.17.

### 5.6 "Fresnel" in shader-art code is often a rim term

Many shaders write `pow(1 - dot(n, v), p)` with `p` between 1 and 5 and no F0 floor, and call it
Fresnel. It is really a **rim light**: an artistic edge glow. The house `sphere-glass` chunk uses
an exponent of 3.2 this way. That is a legitimate art primitive, but it should be named
`rim`, not Fresnel, so nobody mixes it into a physically based path where it would double-count.
Seascape (TDM, `Ms2SD1/image.glsl:110`) uses a cubed rim capped at 0.5 to blend refraction and sky
reflection; afl_ext's ocean (`MdXyzX/image.glsl:205`) uses true Schlick with F0 = 0.04.

---

## 6. Light sources

### 6.1 Directional (sun)

A direction and a colour. No falloff. The sun has an angular radius of about 0.27 degrees, which
is why sun shadows are sharp at contact and blur with distance (section 7.2).

### 6.2 Point and spot lights

- Inverse-square falloff: irradiance falls as `1/d^2`. Clamp `d^2` from below (Filament uses
  `max(d^2, 0.01^2)`) to avoid infinity at the light.
- Windowing so lights end at a radius `r` (Karis 2013; Filament):
  `falloff = clamp(1 - (d/r)^4, 0, 1)^2 / max(d^2, eps^2)`.
- Spot cone: `clamp((dot(l, spotDir) - cosOuter) / (cosInner - cosOuter), 0, 1)`, squared for a
  smoother edge.

### 6.3 Area lights: sphere and tube

Real lights have size; large lights make broad soft highlights on smooth surfaces. The
**representative point** method (Karis 2013): instead of the light's centre, use the point on the
light closest to the reflection ray. For a sphere light with centre vector `L` (from shaded point)
and reflection direction `r`:

```
toRay   = dot(L, r) * r - L
closest = L + toRay * clamp(radius / length(toRay), 0, 1)
```

then shade with `l = normalize(closest)`. To keep energy right, widen the distribution:
`alpha' = clamp(alpha + radius / (c * distance), 0, 1)` and scale the specular by
`(alpha / alpha')^2`. Alex Tardif's write-up uses `c = 2`; I could not open Karis's notes PDF to
confirm his constant (the file exceeds the fetch limit), so treat `c` as 2 to 3 and verify against
the notes before pinning it. A tube light first finds the closest point on the segment to the
reflection ray, then applies the sphere step with the tube radius.

### 6.4 iq's outdoor rig (key, sky, bounce)

From Inigo Quilez's "outdoors lighting" article, and visible in many of his corpus shaders:

| Light | Direction | Colour / intensity (relative) | Visibility |
|---|---|---|---|
| **Key (sun)** | the sun | warm yellow-white, about 1.2-1.6 | soft shadow ray, **no AO** |
| **Sky (fill)** | straight down from above | blue, about 0.15-0.2 | ambient occlusion |
| **Bounce (indirect)** | horizontal, opposite to the sun (negate sun x and z, zero y) | warm, about 0.3 | ambient occlusion |

With albedos near 0.2, a sunlit pixel lands near 0.5 linear. Two extra tricks iq uses:

- **Coloured penumbra**: raise the shadow value to slightly different powers per channel (red
  softest), so shadow edges go warm before going dark, as they do in sunlight scattered by air.
- **Back and "sss" fills** in `Xds3zN/image.glsl:579-592`: a dim back light that fades with height
  (light bouncing off the ground), and a term `(1 - NoV)^2 * AO` that brightens silhouettes a
  little; it reads as atmosphere and translucency.

Many of Shane's and nimitz's shaders use the same skeleton with different numbers. The point is
not the numbers; it is that each light has a *role* and its own visibility.

### 6.5 Emissive surfaces

Emission is added, never multiplied by albedo, never shadowed. In HDR it can be far above 1 and
let the tonemapper and bloom carry it. See section 12.

---

## 7. Visibility: shadows and occlusion from distance fields

A signed distance field (SDF) answers "how far is the nearest surface from this point?". That one
answer powers all of the following. Each `map()` (SDF) evaluation is the unit of cost; count them.

### 7.1 Hard shadows

March from the shaded point toward the light. If the SDF ever gets below a small epsilon, the
point is in shadow. Start at `tmin` (0.01-0.05 of scene scale) or offset along the normal,
otherwise the ray hits its own surface (**shadow acne**: speckled dark dots on lit faces).

### 7.2 Soft shadows: the k*h/t penumbra (iq)

While marching toward the light, at each step you know `h` (distance to nearest geometry) and `t`
(distance travelled). The ratio `h/t` is roughly the angle by which the ray misses the occluder,
seen from the shaded point. Keep the minimum of `k*h/t` over the march; that is the fraction of a
light of angular size about `1/k` that is visible:

```
res = min over steps of clamp(k * h / t, 0, 1)
shadow = smoothstep-like remap of res
```

Large `k` = small light = sharp shadow; `k` 4-16 is typical, 32+ for a sun. Penumbrae widen with
distance from the contact point, exactly like real shadows. iq advances by `clamp(h, minStep,
maxStep)` and stops when `res` is tiny or `t > tmax`; his MIT-licensed reference is
`Xds3zN/image.glsl:449`.

**Sebastian Aaltonen's improvement** (GDC 2018, Claybook): the classic version only checks the
march points, so it misses the true closest approach that happens *between* steps, giving banding
and light leaks around sharp corners. Using the previous step's distance `r1` and the current
`r2`, triangulate the closest point: `y = r2^2 / (2*r1)`, `d = sqrt(r2^2 - y^2)`, and use
`k * d / max(0, t - y)` instead of `k*h/t`.

**Inner penumbra** (later addition in iq's article): let the ray continue a little *into*
geometry (negative distances), map the result from -1..1 with a smoothstep, and you get both
halves of the penumbra (the part inside the geometric shadow too), which is closer to ground truth
than the one-sided version.

Cost: 16-64 SDF evaluations per light per pixel. Budget a bounding volume (iq clips `tmax` to the
top of the scene's bounding slab).

### 7.3 Analytic shadows and occlusion for simple shapes

For spheres, boxes and capsules there are closed forms (iq's articles on sphere soft shadows and
sphere ambient occlusion). Sphere occlusion of a point with normal `n`, sphere centre offset `d`
(from point to centre) and radius `r`, when the sphere is above the horizon:

```
occlusion = dot(n, normalize(d)) * r^2 / |d|^2
visibility = 1 - occlusion
```

It depends only on `r/|d|`: a bigger sphere farther away occludes identically. Costs one inverse
square root, no march. Ideal for moving balls, particles and the house's closed-form sphere chunk.

### 7.4 Ambient occlusion from SDFs

**Ambient occlusion (AO)** estimates how much of the sky a point can see. In crevices it is low.

**The normal-line method** (Alex Evans, "Fast Approximations for Global Illumination on Dynamic
Scenes", SIGGRAPH 2006; popularised by iq in "Rendering Worlds with Two Triangles", 2008): sample
the SDF at a few points along the normal, at heights `h_i`. On an open flat surface the SDF at
height `h` equals `h`. If anything is nearby, it is less. Sum the shortfall with weights that fade
with height:

```
occ = sum over i of  w_i * (h_i - map(p + n * h_i))       (w_i decaying, e.g. 0.95^i or 1/2^i)
ao  = clamp(1 - strength * occ, 0, 1)
```

iq's 2008 slides say this costs about 5 evaluations, cheaper than the primary ray. His modern
version (`Xds3zN/image.glsl:493`) uses 5 heights from 0.01 to 0.13 and multiplies by a
`0.5 + 0.5*n.y` term so down-facing surfaces see less sky.

**Hemisphere sampling** (iq's "Snail", `ld3Gz2/image.glsl:432`): sample in many directions around
the normal (32 in Snail) with random lengths. Smoother, more correct, much costlier. Use it when the
subject is the hero and is not raymarched many times.

**Multi-bounce AO** (Jimenez, Wu, Pesce and Jarabo, "Practical Real-Time Strategies for Accurate
Indirect Occlusion", SIGGRAPH 2016): plain AO assumes crevice walls are black, so it over-darkens
bright materials. Their fit maps visibility `A` and albedo `rho` to a corrected value:

```
a = 2.0404*rho - 0.3324
b = 4.7951*rho - 0.6417
c = 2.7552*rho + 0.6903
G = max(A, a*A^3 - b*A^2 + c*A)       (per colour channel)
```

On screen: white plaster corners stay light; red crevices go deeper red instead of grey. It is a
few multiply-adds and costs nothing extra.

**Where AO goes**: multiply the sky and bounce fills by AO. Not the sun (that has its shadow ray).
Not emission.

### 7.5 Specular occlusion and horizon occlusion

AO is for diffuse. Reflections in crevices also need darkening, but differently: smooth surfaces
viewed head-on should keep their reflections more than rough ones.

- **Lagarde's empirical specular occlusion** (Frostbite, SIGGRAPH 2014; also in Filament):
  `specAO = clamp((NoV + ao)^(2^(-16*alpha - 1)) - 1 + ao, 0, 1)`. For rough surfaces it returns
  AO unchanged; for smooth ones it relaxes AO at normal incidence and tightens it at grazing.
- **Cone intersection** (Jimenez et al. 2016, GTSO): model visibility as a cone around the
  **bent normal** (the average unoccluded direction) with half-angle from `cos = sqrt(1 - AO)`, model
  the specular lobe as a cone around the reflection vector, and use the solid-angle overlap.
  Precise; needs a bent normal.
- **Horizon occlusion** (Jeff Russell, Marmoset): with bumped normals, reflection vectors can point
  *into* the surface and pick up sky that cannot be there. Fade: `h = clamp(1 + k*dot(r, nGeom),
  0, 1)`, multiply by `h^2`. Simplest raymarch variant: afl_ext forces the reflection's y upward
  (`MdXyzX/image.glsl:209`).

---

## 8. Environment and image-based lighting

### 8.1 Procedural environments (the shader-art default)

Most Shadertoy masterpieces never touch a texture for lighting. The environment is a function of
direction: a vertical gradient (zenith, horizon, ground), a sun disc plus a halo (`pow(max(dot(rd,
sun),0), p)` at two exponents), and maybe clouds. Reflections call the same function with the
reflection vector. Two classic cheap reflection tricks:

- iq's **sky specular**: `smoothstep(-0.2, 0.2, r.y)` times Fresnel times a soft shadow along `r`
  (`Xds3zN/image.glsl:572-576`). The smoothstep width is a crude "prefilter": a sharp horizon line
  blurred by roughness. Make the width depend on roughness and you have a procedural rough
  reflection.
- **Studio environments for metals**: a few bright rectangles (softboxes) on a dark dome. Metals
  need *contrast* in the environment; a soft gradient makes chrome look like grey plastic. Again,
  widen the softbox edges with roughness.

### 8.2 Spherical-harmonic irradiance

For diffuse lighting from a whole environment, Ramamoorthi and Hanrahan (SIGGRAPH 2001) showed
that 9 numbers per colour channel (spherical harmonics up to order 2: a constant, three linear and
five quadratic terms) reproduce irradiance with about 1% average error, because the cosine lobe
blurs away all fine detail. Evaluation for unit normal `(x, y, z)` is a quadratic polynomial:

```
E(n) = c1*L22*(x^2 - y^2) + c3*L20*z^2 + c4*L00 - c5*L20
     + 2*c1*(L2m2*x*y + L21*x*z + L2m1*y*z)
     + 2*c2*(L11*x + L1m1*y + L10*z)
c1 = 0.429043  c2 = 0.511664  c3 = 0.743125  c4 = 0.886227  c5 = 0.247708
```

(`L2m2` means coefficient l=2, m=-2, and so on; their paper uses z as up.) Krzysztof Narkowicz's
"Physically Based Shading" shader in the corpus (`4sSfzK/image.glsl:378`) uses a hard-coded St.
Peter's Basilica coefficient set. Hardware analogy: SH is a low-pass filter's coefficient table.
The cosine lobe *is* the low-pass filter, so storing only the low frequencies loses nothing you
could see in diffuse.

### 8.3 Cubemaps and prefiltering

With a cubemap you can blur by roughness: sample the reflection direction at a mip level
proportional to roughness (`lod = perceptualRoughness * maxMip`). It is not a correct GGX
convolution (box-filtered mips are the wrong shape), but it is the shader-art standard. Reinder
Nijhoff's "Old watch (IBL)" (`lscBW4`, CC BY-NC-SA) uses Shadertoy cubemap mips, remapped to look
more HDR, and says plainly in its header that this is a shortcut and links a path-traced version
for comparison.

### 8.4 The split-sum approximation (Karis 2013)

The full environment specular integral is split into two separately precomputed factors:

```
specular_IBL ~= [ prefiltered environment at (r, roughness) ] * [ F0 * A(NoV, roughness) + B(NoV, roughness) ]
```

The first factor is the environment blurred by the GGX lobe (assuming normal = view = reflection,
which loses the stretched reflections at grazing angles). The second, `A` and `B`, is the BRDF
integrated against a white environment, stored as a small 2D table (the "DFG" or "environment
BRDF" lookup table). Reinder computes that table once into a Shadertoy buffer.

**No-texture version** (Karis 2014, "Physically Based Shading on Mobile", fitted after Lazarov's
Black Ops II approximation). With perceptual roughness `r` and `NoV`:

```
        x        y         z        w
c0     -1     -0.0275   -0.572    0.022
c1      1      0.0425    1.04    -0.04

q  = r * c0 + c1                       (4-vector, component by component)
s  = min(q.x^2, 2^(-9.28 * NoV)) * q.x + q.y
A  = -1.04 * s + q.z
B  =  1.04 * s + q.w
```

Then `specular = prefiltered * (F0 * A + B)`, optionally with the multiple-scattering correction
of 4.7. This is the single most useful formula for raymarched metals with a procedural sky.

### 8.5 Real reflections in a raymarcher

You can also march the reflection ray for one bounce and shade what it hits (Shane does this in
many shaders, BigWings teaches it in "Raymarched Reflections"). It doubles the cost of every
reflecting pixel and the second hit usually gets a cheaper shading path (no AO, simple shadow).
Blend between the marched reflection (near) and the environment function (far or missed).

---

## 9. Subsurface scattering fakes

**Subsurface scattering (SSS)**: light enters a material (skin, wax, jade, milk, leaves, marble),
bounces around inside, and exits elsewhere, softening lighting and letting light through thin
parts. True SSS is expensive; these fakes cover nearly all art needs.

### 9.1 Wrap and terminator colour (front-lit softness)

Section 2.2. Wrap softens; a warm band past the terminator (iq's skin, Green's GPU Gems chapter)
says "this is flesh". Cheap: no extra SDF evaluations.

### 9.2 Back-lit translucency (Barré-Brisebois and Bouchard, GDC 2011, Frostbite 2)

Light passing through a thin object toward the eye. Distort the light vector by the normal so the
effect follows the surface shape, then compare with the view:

```
lt   = l + n * distortion                 (distortion ~0.1-0.5)
glow = pow(clamp(dot(v, -lt), 0, 1), power) * scale
sss  = lightColour * attenuation * (glow + ambientTranslucency) * thinness
col += albedo * sss
```

`thinness` is 1 where the object is thin. They baked it as a "local thickness" map from inverted
ambient occlusion; in a raymarcher we can compute it (9.3).

### 9.3 Thickness from a distance field

March a few steps *into* the object along `-n` (or along the refracted view direction, as noby's
MIT-licensed "Goo" does after a suggestion from Shane, `lllBDM/buf_a.glsl:128`) and accumulate how
negative the SDF is. A deep interior gives large negative sums (thick), a thin fin gives small ones
(thin). iq's "Snail" `calcSSS` (`ld3Gz2/image.glsl:448`) samples random directions around the
inward normal, like AO turned inside out. 5-12 evaluations.

### 9.4 Beer-Lambert absorption

Light travelling a distance `d` through a coloured medium loses energy exponentially:
`T = exp(-sigma * d)` per channel. Choosing `sigma` is easier backwards (Khronos
`KHR_materials_volume`): pick the colour `c` that white light should become after travelling a
distance `D`; then `sigma = -ln(c) / D` and `T(d) = c^(d/D)`. Thicker means more saturated and
darker, exactly what makes jade, beer and deep water read correctly. Combine with 9.3 thickness for
a single-call "the thick part is deep red, the thin edge is pale orange".

### 9.5 Height and crest glow on water

Seascape (`Ms2SD1/image.glsl:119`) and afl_ext's ocean (`MdXyzX/image.glsl:213`) add water colour
proportional to height above the mean surface: wave crests are thin, so light passes through them.
A one-line SSS fake that is pure observation.

---

## 10. Glass, refraction, dispersion, caustics

### 10.1 Snell's law and refract()

Light bends entering a denser medium: `n1 * sin(theta1) = n2 * sin(theta2)`. GLSL's
`refract(I, N, eta)` takes the incident direction, the normal facing the incoming ray, and
`eta = n_from / n_to` (1/1.5 entering glass, 1.5 leaving it). It returns the zero vector when there
is no transmitted ray: total internal reflection. Test for it (tdhooper's "Fractured Orb",
`ttycWW/buffer_a.glsl:490`, and Shane's "Refractive Polyhedron", `DtjSWh/buffer_a.glsl:769`) and
reflect instead.

### 10.2 Four levels of glass, cheapest first

1. **Environment-only glass** (Shane, "Abstract Glassy Field", `4ttGDH/image.glsl:306`): at the
   first hit compute both the reflection and the refraction vector and look both up in the
   environment function; mix by Fresnel. No second march. Reads as glass on blobby shapes.
2. **Closed-form solids**: a sphere's entry and exit are closed form (one square root each), so
   two refractions cost almost nothing; the house `sphere-glass` chunk is the start of this.
3. **Two-sided SDF march**: after refracting in, march *inside* by negating the SDF (inside, the
   distance is negative; flip its sign so sphere tracing still works). Find the exit, refract out
   (handling TIR), apply Beer-Lambert for the inside distance, then sample the environment or march
   the scene. Virgill's "Rhodium liquid carbon" (`llK3Dy/buf_a.glsl:74-88`) marches inside,
   shades the inner exit surface and subtracts intensity with inner distance. Each extra bounce is
   another march.
4. **Bounce trees**: every interface splits light into reflected and refracted parts, so N
   interfaces make 2^N paths. Practical shaders follow one path (the refracted one, or the stronger
   one), fold the other in from the environment function weighted by Fresnel, and cap at 3-6
   bounces (Shane's polyhedron loops a fixed number of times, `DtjSWh/buffer_a.glsl:595-780`).

For rasterised meshes (three.js) the standard is **screen-space refraction**: render the scene
behind the glass to a texture, then sample it at an offset given by the refracted vector (Maxime
Heckel's 2023 article walks through it, including a back-face pass for double-sided glass).

### 10.3 Dispersion (rainbows from glass)

IOR depends on wavelength: blue bends more than red. That is **dispersion**, measured by the **Abbe
number** `V = (n_d - 1) / (n_F - n_C)`, using the Fraunhofer lines F (486.13 nm, blue),
d (587.56 nm, yellow) and C (656.27 nm, red). Low V means strong dispersion: rutile about 10,
polycarbonate 32, diamond and water about 55, crown glass about 59 (KHR_materials_dispersion).

- **Cauchy's equation** gives IOR at any wavelength: `n(lambda) = A + B / lambda^2`. Solve A and B
  from `n_d` and `V`: `B = ((n_d - 1)/V) / (1/lambda_F^2 - 1/lambda_C^2)`, `A = n_d - B/lambda_d^2`.
- **Three-channel dispersion** (Khronos): `halfSpread = (n_d - 1) * 0.5 / V`; IORs for red, green,
  blue are `n_d - halfSpread`, `n_d`, `n_d + halfSpread`. Trace each channel separately (3x cost,
  only after the first interface; the first hit is shared). Looks like chromatic aberration with
  hard colour fringes.
- **Spectral sampling**: trace N wavelengths (6-16), each with its own IOR, and convert each to an
  RGB weight with a smooth spectral curve (Alan Zucconi's "Improving the rainbow" series compares
  bump-function fits). **Normalise the weights so a flat spectrum sums to exactly white**, or white
  light turns pink or green. Heckel's article does a cheaper variant: many samples with slightly
  shifted IOR per channel to smear the fringes.
- **Stochastic spectral + accumulation**: pick one random wavelength per pixel per frame, map it
  to an IOR (`ttycWW` blends IOR from 1.2 to 1.8 across its wavelength variable), trace, tint by
  that wavelength's colour, and average over frames in a buffer. Gives the most beautiful results
  at the cost of noise until convergence; needs the feedback rules in the house shader-craft skill.

### 10.4 Caustics

**Caustics** are the bright networks of light focused by curved glass or water (the dancing lines
on a pool floor). Fakes, cheapest first:

1. **Iso-line of a noise** (iq, "Dolphin", `4sS3zG/image.glsl:519-524`): sum two scrolling noise
   lookups, then take `1 - smoothstep(0, w, |value - 0.5|)` at two widths. Wherever the noise
   crosses its midpoint you get a thin bright line; overlapping scrolling layers make the network.
   Multiply the receiver's lighting by `1 + k * caustic`.
2. **Iterated warp with inverse distances** (joltz0r on GLSL Sandbox; made tileable by Dave Hoskins,
   "Tileable Water Caustic", `MdlXz8`): repeatedly warp the coordinate with sines and cosines of
   itself and time, add `1/length(...)` of a scaled coordinate each iteration, then push the sum
   through a steep power curve. The inverse distances make sharp filaments.
3. **Voronoi edges**: distance to the nearest Voronoi border (iq's "Voronoi - distances", `ldl3W8`,
   MIT), animated and thresholded, makes cell-shaped caustics; better for swimming-pool floors.
4. **Area ratio from derivatives** (Evan Wallace, WebGL Water, 2011; followed by Maxime Heckel's
   2024 caustics article): for each point on the water surface, compute where light would land on
   the floor before refraction (straight down) and after (along the refracted ray). Using
   `dFdx` and `dFdy`, measure the little area each covers; brightness equals
   `area_before / area_after`. Light concentrated into a smaller area gets brighter. Physically
   motivated and cheap, but it needs the light-space geometry rendered into a buffer.

Rule for all of them: caustics are light, so they add to (or multiply up) the *lit* part of the
receiver and must be killed by shadow.

---

## 11. Thin-film iridescence

### 11.1 The physics

A soap bubble, an oil slick, a beetle shell, heat-tinted titanium: a transparent film a few hundred
nanometres thick sits on top of something. Light reflects from the film's top and from its bottom;
the two reflections interfere. Where their wavelengths line up (constructive) that colour is
reinforced, elsewhere cancelled.

- **Optical path difference**: `OPD = 2 * n_film * d * cos(theta_t)`, where `d` is thickness and
  `theta_t` the refracted angle inside the film, `cos(theta_t) = sqrt(1 - (sin(theta_i)/n_film)^2)`
  (derivation in Alan Zucconi's "The Mathematics of Thin-Film Interference").
- **Phase**: `phi = 2*pi*OPD/lambda`, plus a half-wave (pi) flip at every reflection off a higher-IOR
  medium. For a soap film in air only the top reflection flips, so constructive interference
  happens at `OPD = (m + 1/2) * lambda`.
- **Two-beam reflectance** at one wavelength, with `R1` the top-surface reflectance and `R2` the
  bottom (both from Fresnel):
  `R(lambda) ~= R1 + R2 + 2*sqrt(R1*R2)*cos(phi + phaseShifts)`.
  This ignores the infinite series of further internal bounces (the full Airy sum); fine for art.
- **Viewing angle** changes `theta_t`, so the colour shifts as you tilt (goniochromism).
- **Thickness** sets the palette: under about 100 nm you see dark (destructive for all colours);
  100-400 nm gives the vivid bubble colours (Khronos defaults are 100-400 nm, film IOR 1.3); well
  above a micron the colours wash out to white.

### 11.2 Evaluating it in RGB

- **Three wavelengths only** (650, 510, 475 nm, one per channel): cheap and fine for thin films.
  For thick films it **aliases**: the cosine oscillates many times across the visible band, and
  three samples produce garish false colours where reality is washed-out white.
- **Spectral integration**: evaluate 8-16 wavelengths and weight each by its RGB response (via a
  smooth spectral approximation), normalised to white. Washes out correctly with thickness.
- **Belcour and Barla (SIGGRAPH 2017)**: integrate the interference term analytically in Fourier
  space against the eye's colour-matching curves, which anti-aliases the spectrum and handles
  roughness. This is what `KHR_materials_iridescence` adopts: the iridescent Fresnel *replaces* `F`
  in the BRDF.
- **Art shortcut**: iq's cosine palette `colour(t) = a + b*cos(2*pi*(c*t + d))` indexed by
  `t = thickness * cos(theta_t)` gives plausible iridescence with no physics. It looks right in
  motion but never washes out and has no correct angle dependence; label it as a stylisation.

### 11.3 Making it look right

Thickness must vary: drive it with slowly flowing noise (bubbles swirl, oil spreads in bands), and
make it thinner at the top of a bubble (gravity drains it). Multiply by a normal Fresnel so the
effect is strongest where the surface is reflective. Put a dark or coloured base under the film:
iridescence is a reflection effect and disappears over bright diffuse bases.

---

## 12. Emissive glow accumulation

### 12.1 Emission is additive HDR

`col += emissive` after lighting. Emission is not shadowed, not multiplied by albedo, and usually
far above 1. The tonemapper must have a shoulder (the house `tanh-tonemap` chunk) or bright things
merge into flat white plateaus; a **hot-core** colour ramp (saturated at low intensity, whitening as
intensity rises) is how neon, plasma and fire read as bright rather than just coloured.

### 12.2 Three ways to make glow around things

1. **Accumulate during the march.** At every sphere-tracing step add a function of the distance
   `d` to the nearest glowing object: `glow += f(d)`. Free (the march happens anyway), and the
   march naturally takes small steps near surfaces, so glow concentrates there.
   Problem: it depends on how many steps happened, so changing the step count, the epsilon or the
   scene elsewhere changes the glow; it also bands. XT95's "Flame" (`MdX3zr/image.glsl:34-44`)
   literally uses the iteration count after entering the flame as the glow value.
   **Fix**: treat it as an integral of an emission density along the ray:
   `glow += density(d) * stepLength`. An important identity: in sphere tracing the step length *is*
   `d`, so the popular "add colour divided by distance each step" (Xor's GM Shaders volumetric
   tutorial, followed by a `tanh` tonemap) is exactly the Riemann sum of an emission density
   proportional to `1/d^2`: an inverse-square glow around every surface. Knowing that, you can
   swap in other densities on purpose (`exp(-k*d)` for a tight halo, `1/(1 + k*d^2)` for a soft one).
2. **Closest-approach glow.** Track the minimum distance the ray ever got to the glowing object
   and use `exp(-k * minDist)`. Stable and step-independent, but it cannot express depth (two
   glowing tubes in a row glow like one).
3. **Analytic in-scattering from a point light** (Miles Macklin, 2010): the glow of a point light in
   uniform fog seen along a ray segment is the integral of `1/(distance to light)^2` along the
   segment. Write the squared distance at ray parameter `t` as `(t + b)^2 + h^2` where
   `b = dot(rd, ro - lightPos)` and `h^2 = |ro - lightPos|^2 - b^2` (the squared closest approach).
   The integral from 0 to `tmax` is closed form:
   `(atan((tmax + b)/h) - atan(b/h)) / h`.
   Exact, cheap, step-free, and correctly cut off by walls when `tmax` is the hit distance. This is
   the right primitive for halos around lamps and orbs; segments and tube lights have similar
   closed forms.

### 12.3 Glow must respect occlusion

Glow accumulated behind a wall shows through the wall unless you stop accumulating at the hit
point, or multiply each contribution by the transmittance so far. The house aurora light bed
already marches a participating medium; its trails are attenuated by the measured transmittance
(see the shader-craft skill's ceiling notes). Same rule here.

### 12.4 Bloom

Physically, glare around bright lights comes from the eye and lens. In a single-pass Shadertoy-style
shader, analytic glow (12.2) stands in for it. In multipass, threshold HDR values, blur at several
scales and add (sonicether's "Gargantua With HDR Bloom", `lstSRS`, is a corpus example). Bloom is
covered more fully by the post-processing researcher.

---

## 13. Metals and liquid metal

### 13.1 What makes metal read as metal

- No diffuse at all (`diffuseColour = 0`). All colour is in F0.
- F0 is high (0.5-1.0) and, for gold and copper, coloured. Edges go toward white (Schlick) or toward
  an edge tint (Gulbrandsen).
- The environment is the material. Chrome is a mirror of a high-contrast world: a sharp horizon, a
  bright sky over a dark ground, a few hot softboxes. Give it that and it reads instantly.
- Roughness spreads reflections; brushed metal is anisotropic GGX with the long axis across the
  brushing; hammered metal is a bumpy normal at small scale.
- Rough metals need energy compensation (4.7) or they turn murky.

### 13.2 Liquid metal (mercury, T-1000, Rhodium-style blobs)

- **Shape**: smooth-union (smooth minimum) blobs with flowing noise displacement. Liquid surfaces
  are smooth at small scale (surface tension), so keep high-frequency noise *out* of the normal.
- **Material**: metallic 1, roughness 0.02-0.1, neutral bright F0 (mercury and chrome sit around
  linear 0.55-0.8 grey; tint slightly for "alien" metals).
- **Lighting**: environment specular through the split-sum (8.4) with a studio or sky function,
  plus one or two sphere lights for sharp hot highlights. Specular occlusion in the folds between
  blobs (7.5) is what sells the creases.
- **Extras**: a thin-film layer for heat-tinted or "oil on chrome" looks; inner glow for sci-fi
  liquids (Virgill's "Rhodium liquid carbon" mixes an inner refraction pass with a volumetric glow
  march, `llK3Dy/buf_a.glsl:140-160`); clear-coat (a second GGX lobe with F0 = 0.04 on top, Filament
  section on clear coat) for candy or car-paint metal.
- **Mistake to avoid**: adding a diffuse term "so it is not too dark". It turns liquid metal into
  grey plastic. Brighten the environment instead.

---

## 14. Putting it together

### 14.1 The house per-pixel order of operations

```
1. Hit:        p, t, material id         (primary march)
2. Normal:     n (tetrahedral, 4 map calls, epsilon scaled with t)   [iq normalsSDF article]
3. Material:   baseColor (sRGB->linear), metallic, roughness, reflectance, emissive, extras
4. Resolve:    diffuseColour, F0, alpha (+ specular anti-aliasing)
5. Per light:  l, radiance * falloff * shadow;  diffuse + D*V*F;  translucency if any
6. Ambient:    sky irradiance (hemisphere or SH) * diffuseColour * multiBounce(AO)
               + environment specular * (F0*A + B) [+ multi-scatter] * specOcclusion * horizon
7. Emission:   + emissive
8. Medium:     fog / atmosphere: col * extinction + inscatter (iq fog article: colour the fog by
               the sun direction; height fog has a closed form)
9. Glow:       + analytic or integrated glow, attenuated by transmittance
10. Display:   exposure -> superlinear highlight -> tanh tonemap -> linear to sRGB -> static dither
```

### 14.2 Cost table (SDF evaluations per shaded pixel)

| Stage | Typical evaluations | Notes |
|---|---|---|
| Primary march | 30-150 | dominates; iq's 2008 talk measured 60% of evaluations on primary rays |
| Normal | 4 | tetrahedral; 6 for central differences |
| Soft shadow | 16-64 per light | bound `tmax`; skip when `NoL <= 0` |
| AO, normal-line | 5 | |
| AO, hemisphere | 16-32 | hero objects only |
| Thickness for SSS | 5-12 | |
| Marched reflection | another full march + cheap shading | per reflective pixel |
| Glass | (bounces) x march | dispersion multiplies after the first interface |
| Analytic sphere AO / shadow / in-scatter | 0 | closed form; use whenever the shape allows |

House floor reminder (shader-craft skill): cost is pixels x march steps x emitters on a host with a
display-driver crash history. A lighting change that adds a march adds a whole primary-ray budget.

### 14.3 Calibration targets (see bugs blind)

- **White furnace test** (Narkowicz): uniform environment of 1, material with albedo 1 or F0 1. The
  object should vanish. Dark rims mean energy loss; bright rims mean double-counted Fresnel or a
  missing normalisation.
- **Grey ball and chrome ball** (the VFX industry's HDRI reference pair): albedo 0.18 diffuse
  sphere and F0 = 1, alpha ~ 0 mirror sphere, both in the scene's lighting. The grey ball shows the
  key/fill balance; the chrome ball shows what metals will reflect.
- **Roughness sweep**: a row of spheres from roughness 0 to 1, dielectric row and metal row. The
  highlight should shrink and intensify smoothly; no step in brightness mid-row.
- **Exposure readout**: a lit 0.2-albedo surface should land near 0.5 linear (iq's rule).

### 14.4 A practice ladder (from zero to expert)

Each rung adds one idea and has a visible pass condition. Done in the VFX bench, one sketch per
rung, so every later rung reuses the earlier primitives (the module promise, practised).

1. **Lambert sphere** with a closed-form ray-sphere hit, linear lighting, sRGB encode. Pass: the
   terminator is a smooth falloff, not a hard line, and halving the light halves the energy.
2. **Blinn-Phong, normalised.** Pass: raising shininess makes a smaller *brighter* dot.
3. **GGX + Smith + Schlick** on a roughness sweep of spheres, dielectric row and metal row. Pass:
   white furnace test shows only the known rough-metal darkening; add energy compensation and it
   mostly disappears.
4. **SDF scene + iq-style rig**: key with soft shadow, sky with normal-line AO, bounce. Pass: grey
   ball reads as outdoors at noon; no AO on the key.
5. **Environment**: procedural sky, analytic environment BRDF, specular occlusion. Pass: a chrome
   ball shows the horizon; a rough gold ball shows a warm blurred horizon, not grey plastic.
6. **Translucency**: thickness from the SDF, Beer-Lambert, back-lit translucency on a jade dragon
   or a leaf. Pass: thin edges glow and shift hue toward the pale end; thick parts saturate.
7. **Glass**: one-hit environment glass, then a two-sided march with TIR, then three-channel
   dispersion. Pass: no black edges; white light stays white through a flat slab.
8. **Thin film** on a bubble: 3-wavelength version, then spectral. Pass: thick regions wash out to
   white in the spectral version and do not in the 3-wavelength one (you have *seen* aliasing).
9. **Glow**: march-accumulated glow, then the step-length-weighted version, then the analytic point
   in-scatter. Pass: halving the march epsilon changes the first and not the last two.
10. **Liquid metal hero**: smooth-union blobs, metal F0, studio environment, sphere lights,
    specular occlusion in the creases, tanh tonemap. Pass: Daniel's eye (the ceiling gate).

---

## 15. Common mistakes and how to see them on screen

| What you see | Cause | Fix |
|---|---|---|
| Washed-out, milky image; gradients look wrong; adding lights looks muddy | lighting in sRGB, or gamma applied twice / never | linear in, one encode out |
| Whole scene too bright, low contrast, shadows full of colour | albedos near 1 | albedos 0.04-0.8, brighten lights instead |
| Flat, "CG" look with dark halos under everything | AO multiplied into the key light | AO on fills only; key gets a shadow ray |
| Speckled dark dots or stripes on lit faces | shadow acne: shadow ray starts inside the surface | start at `tmin` or offset along `n` |
| Bands in soft penumbrae, light leaking at sharp corners | classic `k*h/t` missing closest approach between steps | Aaltonen triangulation, more steps, smaller max step |
| Black pixels or black blotches that flicker | NaN: `pow` of a negative base, `normalize(vec3(0))`, `sqrt` of negative, divide by `NoV = 0` | clamp bases to >= 0, add tiny epsilons, clamp NoV to ~1e-4 |
| Specular sparkle crawling on smooth curved surfaces | specular aliasing: sub-pixel highlights | minimum alpha, geometric specular AA, distance normal smoothing |
| Highlights on the dark side of objects | specular not multiplied by `NoL` or the shadow | shade specular only where `NoL > 0`, times shadow |
| Highlight in the wrong place | half vector built from the ray direction instead of the view direction (`v = -rd`) | `h = normalize(l + v) = normalize(l - rd)` |
| Bright white halo around every object | rim "Fresnel" with no F0 floor, added on top of a real Fresnel | name it rim, use one or the other |
| Shiny plastic look on metal | metal given a diffuse term, or white specular on gold | metallic: diffuse 0, coloured F0 |
| Rough metal goes dark and dull | single-scatter energy loss | energy compensation (4.7) |
| Reflections leaking light in creases, glowing sky in cavities | no specular or horizon occlusion | specular AO, horizon fade |
| Glass edges black | TIR handled as "no light" | reflect on TIR, keep tracing or use the environment |
| Glass looks like a hole cut in the scene | no Fresnel reflection on the surface | always add the Fresnel-weighted reflection |
| Dispersion turns white light pink or green | spectral weights do not sum to white | normalise the weights |
| Iridescence garish at large thickness | 3-wavelength aliasing | spectral sampling or Belcour-Barla |
| Glow changes when step count or scene changes; glow bands | glow counted per step | integrate density x step length, or analytic glow |
| Glow visible through walls | accumulation not stopped at the hit / not attenuated | stop at hit, multiply by transmittance |
| Bright things merge into one flat white | no tonemap shoulder | tanh or filmic tonemap before encode |
| Distant terrain shading crawls and sparkles | constant normal epsilon | scale epsilon with distance (iq normalsSDF) |
| Fog a flat grey sheet | constant fog colour | sun-tinted fog (iq), separate extinction and inscatter per channel |
| Shader compile is slow or WebGL context dies | `map()` inlined many times (normal, AO, shadow) | iq's trick: evaluate `map()` inside a loop with a non-constant zero bound so it is inlined once |

---

## 16. Primitive API for the house library

Conventions (binding for every function below):

- GLSL ES 3.00 (WebGL2), `precision highp float`, matching the house template.
- All colours linear RGB. Directions are unit vectors. `n` = surface normal, `v` = direction from
  the point toward the eye (`-rd`), `l` = direction from the point toward the light.
- Lights carry pi folded into their colour; Lambert is `albedo * NoL`; GGX terms carry their own
  normalisation.
- `perceptualRoughness` is the slider value; `alpha` is its square. Functions say which they take.
- Prefix `lit_` for the whole lighting library, so modules never collide with other libraries.
- **SDF-dependent primitives** (marked [SDF]) call `float lit_sceneDist(vec3 p);`, which the host
  shader must define before including the module. GLSL has no function pointers, so this is the
  linker's "external symbol" pattern: the library declares, the scene defines.
- Loop counts are capped by compile-time constants (`LIT_MAX_SHADOW_STEPS`, `LIT_MAX_TAPS`), with
  a runtime parameter that breaks early, per the shader-craft floor ("loop bounds are constant").
- Each group maps naturally to a `design/vfx-chunks` category (`cat`) and later to an
  `arsenal.module/v0` manifest with a `shader` block as Heimdall's unified-module report proposes.

### 16.1 core (conventions and conversions)

```glsl
vec3  lit_srgbToLinear(vec3 c);       // exact piecewise sRGB decode; call on every picked colour before lighting
vec3  lit_linearToSrgb(vec3 c);       // exact piecewise sRGB encode; the last colour op before dither
float lit_luminance(vec3 c);          // Rec.709 luminance of a linear colour (0.2126, 0.7152, 0.0722)
float lit_pow5(float x);              // x^5 by multiplication; x expected in [0,1]
vec3  lit_safeNormalize(vec3 v);      // normalize that returns (0,1,0) instead of NaN for a zero vector
```

### 16.2 diffuse

```glsl
float lit_lambert(vec3 n, vec3 l);                         // max(dot(n,l),0); pi folded into the light
float lit_halfLambert(vec3 n, vec3 l);                     // (0.5*NoL+0.5)^2; non-physical shape-keeper for back faces
float lit_wrapDiffuse(vec3 n, vec3 l, float w);            // energy-normalised wrap, (NoL+w)/(1+w)^2 clamped; w in [0,1]
float lit_burleyDiffuse(float NoL, float NoV, float LoH, float perceptualRoughness); // Disney factor (no 1/pi); grazing retro-reflection on rough
float lit_skyVisibility(vec3 n);                           // 0.5+0.5*n.y: fraction of an unoccluded upper dome a normal faces
vec3  lit_hemisphereLight(vec3 n, vec3 skyCol, vec3 groundCol); // sky/ground gradient irradiance by n.y
float lit_dirDerivDiffuse(float fieldHere, float fieldTowardLight, float eps); // NoL from one extra field sample (iq); SDF convention, flip args for densities
vec3  lit_terminatorScatter(float NoL, vec3 scatterCol, float width); // warm band past the terminator; zero on the lit side
```

### 16.3 specular and microfacet BRDF

```glsl
float lit_blinnPhong(vec3 n, vec3 h, float shininess);     // normalised Blinn-Phong, (s+8)/(8pi)*NoH^s
float lit_shininessFromAlpha(float alpha);                 // s = 2/alpha^2 - 2 (Walter 2007), for porting old shaders
float lit_ggxD(float NoH, float alpha);                    // Trowbridge-Reitz/GGX NDF, alpha^2/(pi*(NoH^2*(alpha^2-1)+1)^2)
float lit_ggxDAniso(float NoH, float ToH, float BoH, float alphaT, float alphaB); // anisotropic GGX NDF
float lit_smithVis(float NoV, float NoL, float alpha);     // height-correlated Smith visibility, includes 1/(4 NoL NoV)
float lit_smithVisFast(float NoV, float NoL, float alpha); // sqrt-free approximation of lit_smithVis
float lit_smithG1Schlick(float NoX, float k);              // Schlick-Smith one-sided masking; k=alpha/2 (IBL) or (r+1)^2/8 (punctual)
vec3  lit_specGGX(vec3 n, vec3 v, vec3 l, vec3 F0, float alpha); // D*V*F for one light; caller multiplies by NoL*radiance*shadow
float lit_specAAAlpha(vec3 n, float alpha);                // widens alpha by screen-space normal variance (geometric specular AA); n must be continuous
vec3  lit_energyCompensation(vec3 F0, float Ewhite);       // 1 + F0*(1/Ewhite - 1); multiply into specular to restore rough-surface energy
```

### 16.4 Fresnel

```glsl
vec3  lit_fresnelSchlick(vec3 F0, float cosTheta);                // F0 + (1-F0)(1-c)^5
vec3  lit_fresnelSchlickF90(vec3 F0, vec3 F90, float cosTheta);   // Schlick with explicit grazing value
float lit_fresnelDielectric(float cosI, float eta);               // exact unpolarised; eta = n_t/n_i; returns 1 at total internal reflection
vec3  lit_fresnelConductor(float cosI, vec3 n, vec3 k);           // exact complex-IOR Fresnel per channel
vec3  lit_fresnelEdgeTint(vec3 reflectivity, vec3 edgeTint, float cosI); // artist metal Fresnel (Gulbrandsen 2014) via n,k mapping
float lit_f0FromIor(float ior);                                   // ((ior-1)/(ior+1))^2 against air
float lit_rim(float NoV, float power);                            // (1-NoV)^power: an ART rim term, deliberately not called Fresnel
```

### 16.5 materials

```glsl
struct LitMaterial {
  vec3  baseColor;            // linear
  float metallic;             // 0..1, 0 or 1 in practice
  float perceptualRoughness;  // slider value
  float reflectance;          // non-metals: F0 = 0.16*reflectance^2 (0.5 -> 0.04)
  vec3  emissive;             // linear HDR, added unlit
};
struct LitSurface {
  vec3  diffuseColor;  vec3 F0;  float alpha;
};
LitSurface lit_resolveMaterial(LitMaterial m, float alphaMin); // metallic workflow resolve (Burley/Karis/Filament); clamps alpha
vec3  lit_shadeLight(LitSurface s, vec3 n, vec3 v, vec3 l, vec3 radiance); // diffuse + GGX for one light; radiance already includes falloff and shadow
LitMaterial lit_materialPreset(int id); // named presets: gold, silver, copper, iron, chrome, water, glass, plastic, skin, jade (F0 table in section 5.5)
```

### 16.6 light sources

```glsl
float lit_inverseSquare(float dist, float radius);         // 1/max(d^2,eps^2) * clamp(1-(d/r)^4,0,1)^2 windowed falloff
float lit_spotCone(vec3 l, vec3 spotDir, float cosOuter, float cosInner); // smooth angular falloff, squared
vec3  lit_sphereLightPoint(vec3 toCenter, vec3 r, float radius); // representative point on a sphere light nearest the reflection ray
vec3  lit_tubeLightPoint(vec3 toA, vec3 toB, vec3 r, float radius); // representative point on a capsule light
float lit_areaAlpha(float alpha, float radius, float dist);  // widened alpha for area-light energy normalisation (constant to verify, section 6.3)
```

### 16.7 visibility (shadows and occlusion)

```glsl
float lit_hardShadow(vec3 ro, vec3 rd, float tmin, float tmax);              // [SDF] 0 or 1
float lit_softShadow(vec3 ro, vec3 rd, float tmin, float tmax, float k);     // [SDF] min(k*h/t) penumbra, smoothstepped; k ~ 1/light size
float lit_softShadowTri(vec3 ro, vec3 rd, float tmin, float tmax, float k);  // [SDF] Aaltonen closest-approach version; fewer bands at corners
float lit_softShadowInner(vec3 ro, vec3 rd, float tmin, float tmax, float k);// [SDF] allows negative distances for the inner penumbra
vec3  lit_colouredPenumbra(float shadow, vec3 exponents);                    // per-channel power so shadow edges warm before darkening
float lit_aoNormal(vec3 p, vec3 n, float reach, int taps);                   // [SDF] Evans/iq normal-line AO; ~5 taps
float lit_aoHemisphere(vec3 p, vec3 n, float reach, int taps);               // [SDF] directional AO over the hemisphere; hero objects
float lit_sphereOcclusion(vec3 p, vec3 n, vec4 sphere);                      // closed-form occlusion by a sphere (xyz centre, w radius)
float lit_sphereSoftShadow(vec3 ro, vec3 rd, vec4 sphere, float k);          // closed-form soft shadow from a sphere
vec3  lit_aoMultiBounce(float ao, vec3 albedo);                              // Jimenez 2016 cubic fit; never darker than ao
float lit_specularOcclusion(float NoV, float ao, float alpha);              // Lagarde empirical specular AO from diffuse AO
float lit_horizonFade(vec3 r, vec3 nGeom, float k);                          // fades reflections that point below the geometric surface
```

### 16.8 environment

```glsl
vec3  lit_skyGradient(vec3 dir, vec3 zenith, vec3 horizon, vec3 ground);     // procedural environment
vec3  lit_studioEnv(vec3 dir, float perceptualRoughness);                    // dark dome with softboxes whose edges widen with roughness (metals)
vec3  lit_skySpecular(vec3 r, float perceptualRoughness, vec3 skyCol);       // horizon step blurred by roughness (iq-style sky specular, generalised)
vec3  lit_shIrradiance(vec3 n, vec3 sh[9]);                                  // Ramamoorthi-Hanrahan 9-coefficient irradiance with c1..c5
vec3  lit_cubePrefiltered(samplerCube env, vec3 r, float perceptualRoughness, float maxMip); // textureLod at roughness-proportional mip
vec2  lit_envBRDFApprox(float NoV, float perceptualRoughness);              // analytic split-sum (A,B): specular = prefiltered*(F0*A+B)
vec3  lit_iblSpecular(vec3 prefiltered, vec3 F0, float NoV, float perceptualRoughness); // split-sum with multiple-scattering correction (Fdez-Aguera)
vec3  lit_iblDiffuseWeight(vec3 albedo, vec3 F0, float NoV, float perceptualRoughness); // diffuse share left after single+multi specular
```

### 16.9 translucency (subsurface fakes)

```glsl
float lit_thicknessSDF(vec3 p, vec3 dirIn, float reach, int taps);          // [SDF] 0 = paper thin, 1 = solid over reach
vec3  lit_beer(vec3 sigma, float dist);                                      // exp(-sigma*dist) transmittance
vec3  lit_sigmaFromColour(vec3 colourAtDist, float dist);                    // -ln(c)/dist (KHR_materials_volume parametrisation)
vec3  lit_translucency(vec3 n, vec3 v, vec3 l, float thinness, vec4 params); // Barre-Brisebois/Bouchard: params = distortion, power, scale, ambient
vec3  lit_crestGlow(float heightAboveMean, vec3 waterCol, float k);          // thin-crest transmission fake for water
```

### 16.10 optics (glass, dispersion, caustics)

```glsl
bool  lit_refractTIR(vec3 i, vec3 n, float eta, out vec3 t);   // Snell; false means total internal reflection (reflect instead)
float lit_iorCauchy(float lambdaNm, float iorD, float abbe);  // IOR at a wavelength from n_d and Abbe number
vec3  lit_iorRGB(float iorD, float abbe);                      // per-channel IORs, half-spread (n_d-1)*0.5/V (Khronos)
vec3  lit_spectrumToRGB(float lambdaNm);                       // smooth spectral weight, normalised so a flat spectrum sums to white
float lit_causticIsoline(float field, float width);           // bright line where a noise field crosses 0.5
float lit_causticAreaRatio(vec3 posBefore, vec3 posAfter);    // dFdx/dFdy area ratio before/after refraction (Wallace)
vec3  lit_glassEnv(vec3 rd, vec3 n, float ior, vec3 tint);    // one-hit glass: env(reflect) and env(refract) mixed by Fresnel; host defines lit_env(dir)
vec3  lit_glassMarch(vec3 ro, vec3 rd, float ior, vec3 sigma, int bounces); // [SDF] two-sided march: refract in, absorb, refract out or TIR
```

### 16.11 thin film

```glsl
vec3  lit_thinFilm(float cosI, float thicknessNm, float filmIor, float baseIor, int wavelengths); // two-beam interference integrated to RGB; replaces F
vec3  lit_thinFilmPalette(float cosI, float thickness, vec3 phase);  // cosine-palette stylisation; not physical, never washes out
```

### 16.12 emission and glow

```glsl
float lit_glowStep(float d, float stepLen, float k);             // density(d)*stepLen: step-count-independent march glow
float lit_glowClosest(float minDist, float k);                   // exp(-k*minDist) closest-approach glow
float lit_pointInscatter(vec3 ro, vec3 rd, vec3 lightPos, float tmax); // closed-form integral of 1/dist^2 along the ray (Macklin)
vec3  lit_hotCore(vec3 tint, float intensity);                   // saturated at low intensity, whitening as intensity rises
```

### 16.13 rigs (composites; "tweak one module and everything updates")

```glsl
struct LitOutdoorRig { vec3 sunDir; vec3 sunCol; vec3 skyCol; vec3 bounceCol; float shadowK; vec3 penumbraExp; };
vec3  lit_rigOutdoor(LitSurface s, vec3 p, vec3 n, vec3 v, LitOutdoorRig rig); // [SDF] key+shadow, sky+AO, bounce+AO, specular, multi-bounce AO
vec3  lit_rigStudio(LitSurface s, vec3 n, vec3 v, float ao);                    // environment-only studio lighting for metals and product shots
vec3  lit_rigNight(LitSurface s, vec3 p, vec3 n, vec3 v, vec3 lightPos, vec3 lightCol); // [SDF] one point light, inverse square, soft shadow, inscatter halo
```

### 16.14 debug and calibration

```glsl
vec3  lit_debugNaN(vec3 c);                       // magenta for NaN or Inf, else c
vec3  lit_debugHeat(float x);                     // false colour for AO, shadow, thickness or step counts
float lit_furnaceValue(LitSurface s, vec3 n, vec3 v); // shading under a uniform white environment; should be 1 for albedo/F0 = 1
```

That is about 80 functions in 14 groups. The rigs are where the "tweak one module and every surface
updates" promise lives: every house surface (aurora bed, avatar styles, first-light, moonwater,
piano visuals) should call a rig or `lit_shadeLight`, never hand-roll its own Lambert.

---

## 17. Study map into the corpus (pointers only)

| Technique | Shader (author, licence) | Where |
|---|---|---|
| Whole reference rig: sun + soft shadow, sky + AO, back, rim-fill, Schlick on specular | Raymarching - Primitives (iq, **MIT**) `Xds3zN` | `image.glsl:449` shadow, `:493` AO, `:549-592` rig |
| Hemisphere AO, SDF-based SSS, two-lobe specular, per-channel grade | Snail (iq, CC BY-NC-SA) `ld3Gz2` | `image.glsl:432`, `:448`, `:620-645` |
| Skin terminator scatter | Selfie Girl (iq, CC BY-NC-SA) `WsSBzh` | `image.glsl:521` |
| GGX + SDF thickness SSS | Goo (noby, **MIT**) `lllBDM` | `buf_a.glsl:101-150` |
| BRDF explorer, SH irradiance, analytic env BRDF | Physically Based Shading (knarkowicz, CC BY-NC-SA) `4sSfzK` | `image.glsl:209-230`, `:378`, `:401` |
| Split-sum IBL with a computed BRDF table | Old watch (IBL) (reinder, CC BY-NC-SA) `lscBW4` | `buffer_b.glsl`, `image.glsl` header |
| Multi-bounce refraction, TIR, metal and glass | Refractive Polyhedron (Shane, CC BY-NC-SA) `DtjSWh` | `buffer_a.glsl:554-780` |
| One-hit environment glass | Abstract Glassy Field (Shane, CC BY-NC-SA) `4ttGDH` | `image.glsl:300-315` |
| Stochastic spectral dispersion | Fractured Orb (tdhooper, CC BY-NC-SA) `ttycWW` | `buffer_a.glsl:482-492` |
| Inner refraction + glow volume, liquid look | Rhodium liquid carbon (Virgill, CC BY-NC-SA) `llK3Dy` | `buf_a.glsl:74-160` |
| Noise iso-line caustics | Dolphin (iq, CC BY-NC-SA) `4sS3zG` | `image.glsl:519-524` |
| Warp-and-inverse-distance caustic | Tileable Water Caustic (Dave_Hoskins after joltz0r, CC BY-NC-SA) `MdlXz8` | `image.glsl` |
| Water: Schlick, crest SSS, normal smoothing, upward reflection | Very fast procedural ocean (afl_ext, **MIT**) `MdXyzX` | `image.glsl:200-216` |
| Rim-blend sea, height SSS | Seascape (TDM, CC BY-NC-SA) `Ms2SD1` | `image.glsl:109-122` |
| Step-count glow | Flame (XT95, CC BY-NC-SA) `MdX3zr` | `image.glsl:34-44` |
| HDR bloom | Gargantua With HDR Bloom (sonicether, CC BY-NC-SA) `lstSRS` | `buf_a.glsl:130` |
| Terrain soft shadows, fog, sun | Elevated (iq, CC BY-NC-SA) `MdX3Rr` | `buffer_a.glsl:135`, `:237-259` |

The three MIT-licensed shaders (`Xds3zN`, `lllBDM`, `MdXyzX`) are the safest to study closely; even
so, the house library is written fresh from the mathematics above.

---

## 18. Sources

Primary sources first, then tutorials. Each line says what it teaches.

### Historical originals (cited for the names in the text)
- Bui Tuong Phong, "Illumination for Computer Generated Pictures" (CACM 1975) - https://doi.org/10.1145/360825.360839 - the Phong reflection lobe.
- James F. Blinn, "Models of Light Reflection for Computer Synthesized Pictures" (SIGGRAPH 1977) - https://doi.org/10.1145/563858.563893 - the half vector and Blinn-Phong.
- T. S. Trowbridge and K. P. Reitz, "Average Irregularity Representation of a Rough Surface for Ray Reflection" (JOSA 1975) - https://doi.org/10.1364/JOSA.65.000531 - the distribution later named GGX.
- Robert L. Cook and Kenneth E. Torrance, "A Reflectance Model for Computer Graphics" (ACM TOG 1982) - https://doi.org/10.1145/357290.357293 - the D*F*G microfacet specular form.
- Michael Oren and Shree K. Nayar, "Generalization of Lambert's Reflectance Model" (SIGGRAPH 1994) - https://doi.org/10.1145/192161.192213 - rough diffuse.
- Tomas Akenine-Möller, Eric Haines, Naty Hoffman et al., "Real-Time Rendering", 4th ed. - https://www.realtimerendering.com/ - reference tables (metal F0, Blinn-Phong normalisation) and the whole field in one book.

### Foundations and microfacet models
- Brian Karis, "Real Shading in Unreal Engine 4" (SIGGRAPH 2013 course notes) - https://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf - the UE4 model: GGX, alpha = roughness^2, Schlick-Smith k, spherical-Gaussian Fresnel, split-sum IBL, windowed falloff, sphere/tube lights. (Mirror: https://cdn2.unrealengine.com/Resources/files/2013SiggraphPresentationsNotes-26915738.pdf. The PDF exceeded my fetch limit; details confirmed through Filament, LearnOpenGL, Tardif and the course listings.)
- Brian Karis, "Specular BRDF Reference" (2013) - http://graphicrants.blogspot.com/2013/08/specular-brdf-reference.html - every common D, G and F term side by side.
- Brian Karis, "Physically Based Shading on Mobile" (2014) - https://www.unrealengine.com/en-US/blog/physically-based-shading-on-mobile - the analytic environment BRDF fit.
- Dimitar Lazarov, "Getting More Physical in Call of Duty: Black Ops II" (SIGGRAPH 2013) - https://blog.selfshadow.com/publications/s2013-shading-course/lazarov/s2013_pbs_black_ops_2_notes.pdf - the original analytic environment BRDF.
- Brent Burley, "Physically-Based Shading at Disney" (SIGGRAPH 2012) - https://media.disneyanimation.com/uploads/production/publication_asset/48/asset/s2012_pbs_disney_brdf_notes_v3.pdf - principled parameters, Burley diffuse, measured-material observations (long specular tails).
- Romain Guy and Mathias Agopian, Filament "Physically Based Rendering in Filament" - https://google.github.io/filament/Filament.md.html - the clearest complete real-time material model: height-correlated V, f0 mapping, metal table, clear coat, anisotropy, cloth, energy compensation, light units.
- Bruce Walter, Stephen Marschner, Hongsong Li, Kenneth Torrance, "Microfacet Models for Refraction through Rough Surfaces" (EGSR 2007) - https://cseweb.ucsd.edu/~viscomp/classes/cse168/sp25/readings/EGSR07-btdf.pdf - GGX introduced to graphics, rough refraction, Blinn exponent mapping.
- Eric Heitz, "Understanding the Masking-Shadowing Function in Microfacet-Based BRDFs" (JCGT 2014) - https://jcgt.org/published/0003/02/03/paper.pdf - why Smith, and the height-correlated form.
- Christopher Kulla and Alejandro Conty, "Revisiting Physically Based Shading at Imageworks" (SIGGRAPH 2017) - https://blog.selfshadow.com/publications/s2017-shading-course/imageworks/s2017_pbs_imageworks_slides.pdf - energy compensation for multiple scattering.
- Carmelo J. Fdez-Agüera, "A Multiple-Scattering Microfacet Model for Real-Time Image-based Lighting" (JCGT 2019) - https://jcgt.org/published/0008/01/03/paper.pdf - multi-scatter IBL using the same split-sum table; Favg closed form; dielectric diffuse share.
- Earl Hammon Jr., "PBR Diffuse Lighting for GGX+Smith Microsurfaces" (GDC 2017) - https://media.gdcvault.com/gdc2017/Presentations/Hammon_Earl_PBR_Diffuse_Lighting.pdf - diffuse consistent with the GGX surface; cheap Smith approximation.
- Krzysztof Narkowicz, FurnaceTest - https://github.com/knarkowicz/FurnaceTest - the white furnace test and GGX/Smith energy loss.
- Joey de Vries, LearnOpenGL "PBR Theory" - https://learnopengl.com/PBR/Theory - gentle derivation of the reflectance equation and Cook-Torrance.

### Fresnel
- Christophe Schlick, "An Inexpensive BRDF Model for Physically-based Rendering" (Computer Graphics Forum, 1994) - https://doi.org/10.1111/1467-8659.1330233 - the fifth-power Fresnel approximation.
- Sébastien Lagarde, "Memo on Fresnel equations" (2013) - https://seblagarde.wordpress.com/2013/04/29/memo-on-fresnel-equations/ - exact dielectric and conductor Fresnel, TIR, where Schlick fails.
- Naty Hoffman, "Fresnel Equations Considered Harmful" (MAM 2019) - https://diglib.eg.org/items/677f583f-aedf-4a6c-8516-1e7e10838136 - why Schlick beats RGB exact Fresnel for metals.
- Ole Gulbrandsen, "Artist Friendly Metallic Fresnel" (JCGT 2014) - https://jcgt.org/published/0003/04/03/paper.pdf - reflectivity plus edge tint for metals.

### Diffuse, wrap and translucency
- Jason Mitchell, Gary McTaggart, Chris Green, "Shading in Valve's Source Engine" (SIGGRAPH 2006) - https://advances.realtimerendering.com/s2006/Chapter7-Shading_in_Valve's_Source_Engine.pdf - half-Lambert.
- Simon Green, "Real-Time Approximations to Subsurface Scattering" (GPU Gems 1, ch. 16) - https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-16-real-time-approximations-subsurface-scattering - wrap lighting, terminator scatter colour, depth-based absorption.
- Stephen Hill, "Righting Wrap (Part 1)" (2011) - https://blog.selfshadow.com/2011/12/31/righting-wrap-part-1/ - energy-conserving wrap normalisation (building on Steve McAuley).
- Colin Barré-Brisebois and Marc Bouchard, "Approximating Translucency for a Fast, Cheap and Convincing Subsurface Scattering Look" (GDC 2011) - https://www.colinbarrebrisebois.com/2011/03/07/gdc-2011-approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look/ - the distorted-light-vector translucency used in Frostbite 2.
- Khronos, KHR_materials_volume - https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_volume/README.md - Beer-Lambert with attenuation colour and distance.

### Shadows, occlusion, distance-field lighting
- Inigo Quilez, "Outdoors lighting" - https://iquilezles.org/articles/outdoorslighting/ - key/sky/bounce rig, linear space, dim albedos, no AO on the key.
- Inigo Quilez, "Soft shadows in raymarched SDFs" - https://iquilezles.org/articles/rmshadows/ - the k*h/t penumbra, Aaltonen's improvement, inner penumbra.
- Sebastian Aaltonen, "GPU-based clay simulation and ray-tracing tech in Claybook" (GDC 2018) - https://media.gdcvault.com/gdc2018/presentations/Aaltonen_Sebastian_GPU_Based_Clay.pdf - the improved SDF soft shadow, SDF ray tracing in production.
- Inigo Quilez, "Rendering Worlds with Two Triangles" (NVScene 2008) - https://iquilezles.org/articles/nvscene2008/rwwtt.pdf - SDF AO (crediting Alex Evans), soft shadows, cost breakdown.
- Alex Evans, "Fast Approximations for Global Illumination on Dynamic Scenes" (SIGGRAPH 2006) - https://advances.realtimerendering.com/s2006/Chapter9-Fast_Approximations_for_Global_Illumination_on_Dynamic_Scenes.pdf - origin of distance-field AO.
- Inigo Quilez, "Sphere ambient occlusion" - https://iquilezles.org/articles/sphereao/ - closed-form occlusion by a sphere.
- Inigo Quilez, "Normals for an SDF" - https://iquilezles.org/articles/normalsSDF/ - tetrahedral normals, distance-scaled epsilon, the anti-inlining loop.
- Inigo Quilez, "Directional derivative" - https://iquilezles.org/articles/derivative/ - one-sample diffuse for volumes and terrain.
- Jorge Jimenez, Xianchun Wu, Angelo Pesce, Adrian Jarabo, "Practical Real-Time Strategies for Accurate Indirect Occlusion" (SIGGRAPH 2016) - https://www.iryoku.com/downloads/Practical-Realtime-Strategies-for-Accurate-Indirect-Occlusion.pdf - GTAO, the multi-bounce AO fit, cone-based specular occlusion.
- Sébastien Lagarde and Charles de Rousiers, "Moving Frostbite to Physically Based Rendering" (SIGGRAPH 2014) - https://seblagarde.wordpress.com/2015/07/14/siggraph-2014-moving-frostbite-to-physically-based-rendering/ - empirical specular occlusion, light units, many production details.
- Jeff Russell, "Horizon Occlusion for Normal Mapped Reflections" (Marmoset) - https://marmosetco.tumblr.com/post/81245981087 - fading reflections that point below the surface.
- Yusuke Tokuyoshi and Anton Kaplanyan, "Improved Geometric Specular Antialiasing" (I3D 2019) - https://www.jp.square-enix.com/tech/library/pdf/ImprovedGeometricSpecularAA.pdf - roughness widening from normal variance.

### Environment lighting
- Ravi Ramamoorthi and Pat Hanrahan, "An Efficient Representation for Irradiance Environment Maps" (SIGGRAPH 2001) - https://cseweb.ucsd.edu/~ravir/papers/envmap/envmap.pdf - 9-coefficient SH irradiance and its constants.
- Inigo Quilez, "Fog" - https://iquilezles.org/articles/fog/ - sun-coloured fog, separate extinction and inscattering, analytic height fog.

### Glass, dispersion, caustics
- Maxime Heckel, "Refraction, dispersion, and other shader light effects" (2023) - https://blog.maximeheckel.com/posts/refraction-dispersion-and-other-shader-light-effects/ - screen-space refraction, per-channel IOR dispersion, back-face pass.
- Maxime Heckel, "Shining a light on Caustics with Shaders and React Three Fiber" (2024) - https://blog.maximeheckel.com/posts/caustics-in-webgl/ - derivative-based caustics, credits Evan Wallace.
- Evan Wallace, "Rendering Realtime Caustics in WebGL" and WebGL Water (2011) - https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c and https://madebyevan.com/webgl-water/ - the area-ratio caustic method (medium page refused my fetch; method confirmed via Heckel).
- Khronos, KHR_materials_dispersion - https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_dispersion/README.md - Abbe number, Cauchy, Fraunhofer lines, per-channel IOR spread.
- Martijn Steinrucken (The Art of Code), "Live Coding: Bending Light" and "Raymarched Reflections" - https://www.youtube.com/watch?v=NCpaaLkmXI8 and https://www.youtube.com/watch?v=beNDx5Cvt7M - refraction and reflection in a raymarcher, taught live.

### Thin film and spectral colour
- Laurent Belcour and Pascal Barla, "A Practical Extension to Microfacet Theory for the Modeling of Varying Iridescence" (SIGGRAPH 2017) - https://belcour.github.io/blog/research/publication/2017/05/01/brdf-thin-film.html - anti-aliased thin-film Fresnel in RGB.
- Khronos, KHR_materials_iridescence - https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_iridescence/README.md - production parametrisation of Belcour-Barla (thickness range, film IOR, replacing F).
- Alan Zucconi, "The Mathematics of Thin-Film Interference" (2017) - https://www.alanzucconi.com/2017/07/25/the-mathematics-of-thin-film-interference/ - OPD derivation, phase flips, the two-beam model.
- Alan Zucconi, "Improving the Rainbow" (2017) - https://www.alanzucconi.com/2017/07/15/improving-the-rainbow/ - wavelength-to-RGB approximations compared.
- Inigo Quilez, "Palettes" - https://iquilezles.org/articles/palettes/ - the cosine palette used for stylised iridescence.

### Glow and volumes
- Miles Macklin, "In-Scattering Demo" (2010) - https://blog.mmacklin.com/2010/05/29/in-scattering-demo/ - closed-form point-light inscattering along a ray.
- Xor, "Volumetric Raymarching" (GM Shaders) - https://mini.gmshaders.com/p/volumetric - colour divided by distance per step, tanh tonemap.

### Area lights
- Alex Tardif, "Area Lights" - https://alextardif.com/arealights.html - sphere and tube representative points and alpha widening after Karis.

### House documents read for this report
- `design/vfx-chunks/sphere-glass.glsl`, `tanh-tonemap.glsl`, `superlinear-highlight.glsl` - the existing chunk format and the rim-vs-Fresnel note.
- `.claude/skills/shader-craft/SKILL.md` - house floor (highp, constant loop bounds, cost, tonemap order).
- `research/reviewed/shader-school-2026-10-13/heimdall-unified-module-system-blind-half-b.md` - the module format the primitive groups should land in.
