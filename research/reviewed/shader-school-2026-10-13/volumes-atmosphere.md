# Volumes and the sky: a full-fidelity study for the house shader school

- **Topic:** volumetrics and the sky. Covers Beer-Lambert transmittance, phase functions, multiple scattering, the powder effect, the Nubis clouds (Guerrilla Games, 2015 to 2023), the Frostbite and Unreal sky, atmosphere and clouds (Hillaire, 2015 to 2020), fog, god rays, aurora curtains, nebulae, density fields made from noise, adaptive steps, jitter, and temporal reprojection.
- **Author:** Vandor (the claude seat), one of eight researchers in the 2026-10-13 shader school.
- **Date:** 2026-10-13.
- **Licence line:** this report contains no corpus code. Techniques are described in my own words and in mathematics. Pointers such as `XtGGRt/image.glsl:58` refer to read-only files under `state/arsenal/shaders/corpus/`. Equations are given as mathematics, credited to the people who published them. Direct quotes are kept under 15 words and attributed.
- **Who it is for:** a capable programmer who has never written a shader and wants to reach expert level, and Daniel, who learns fast and likes the hardware analogy for each idea.

---

## 0. The whole subject in one page

A *volume* is anything light passes **through**, as opposed to bouncing **off**: fog, cloud, smoke, sky, aurora, nebula. Real-time renderers draw volumes with a **ray march**. For each pixel you shoot a ray from the eye. You walk along it in small steps, and at each step you ask two questions:

1. **How much stuff is here?** This is the *density field*, usually built from noise.
2. **How much light does this stuff send toward the eye?** This is *lighting*: light from the sun, attenuated by whatever lies between the sun and this point, then redirected toward the eye according to the *phase function*.

You add up those contributions front to back. Each one is dimmed by everything already in front of it (the *transmittance*). You stop when the ray leaves the volume or nothing behind could still show through.

Almost everything else in this report is one of three things:

- **Physics that makes the march correct.** Beer-Lambert, phase functions, multiple scattering, energy-conserving integration.
- **Engineering that makes it affordable.** Bounds, adaptive steps, cheap and expensive samples, look-up tables (LUTs), jitter, temporal reprojection.
- **Art direction that makes it beautiful.** Weather maps, height profiles, erosion, the powder effect, the silver lining, aurora colour by altitude.

The best practitioners keep these three clearly separate. They make the physics correct first, so that the art controls behave predictably and the engineering cannot change the picture.

**Hardware analogy for the whole thing.** A ray march works like a long chain of neutral-density filters, each with a faint lamp inside it. Each filter passes a fraction of what is behind it (transmittance). Each lamp adds its own light (in-scattering or emission). The pixel is what comes out of the front of the chain. Optical depth is literally measured in **nepers**: logarithmic attenuation that **adds** along the chain, just as decibels add through a signal chain, while the linear gains multiply.

---

## 1. The physics, plainly

### 1.1 Participating media and their four coefficients

A *participating medium* is a volume full of particles that "participate" in light transport. When light crosses a short distance `ds`, four things can happen. Each has a coefficient measured in "per metre" (m⁻¹): the probability per metre that the event happens.

| Event | Symbol | What happens | Visual result |
|---|---|---|---|
| Absorption | σa (sigma-a) | A photon is swallowed and becomes heat | Darkens; dark smoke, soot |
| Out-scattering | σs (sigma-s) | A photon is knocked out of the ray | Darkens what is behind |
| In-scattering | σs again | Light from elsewhere is knocked **into** the ray | Brightens; the glow of fog |
| Emission | ε or σa·Le | The medium itself glows | Fire, aurora, nebula gas |

- **Extinction** is σt = σa + σs: everything that removes light from the ray.
- **Single-scattering albedo** is ρ = σs / σt, a number from 0 to 1. ρ ≈ 0 gives soot. ρ ≈ 1 gives clouds, air and snow, where light almost never dies and only changes direction. Hillaire's Frostbite notes cite measurements (Hess, Koepke and Schult, 1998) of water clouds with ρ ≈ 1 and extinction of roughly 0.04 to 0.06 m⁻¹ for stratus and 0.05 to 0.12 m⁻¹ for cumulus.
- **Mean free path** is 1/σt: the average distance a photon travels before something happens to it. In a cumulus this is about 8 to 25 metres.

### 1.2 Beer-Lambert: the one law everything rests on

Over a tiny distance `ds`, the fraction of light removed is σt·ds. That gives a differential equation:

  dL/ds = −σt(s) · L

Its solution is

  L(s) = L(0) · exp(−τ),  where  τ = ∫₀ˢ σt(s′) ds′

- τ (tau) is the **optical depth**: extinction summed along the path.
- **Transmittance** is T = e^(−τ), the fraction that gets through.
- For a uniform medium, T = e^(−σt·d).

Three consequences are worth memorising:

1. **Optical depths add and transmittances multiply.** You can cut a path into steps and multiply the step transmittances. This is what makes ray marching legal. (Decibels and gains, again.)
2. **One mean free path lets through 1/e ≈ 37 %.** Three let through 5 %. Five let through under 1 %.
3. **A real cumulus is optically enormous.** With σt ≈ 0.05 to 0.12 m⁻¹, one kilometre of cloud has τ ≈ 50 to 120, so T ≈ e⁻⁵⁰, which is effectively zero. Sunlight that has scattered only once cannot reach the inside of a cloud. Every bit of brightness you see deep in a cumulus is light that has bounced many times. That single fact explains why multiple scattering (§1.6) is not a refinement for clouds; it is the whole look.

Wavelength matters. σ can differ per colour channel, so T becomes an RGB triple (vec3). In air, blue light is scattered more than red, which is why the sky is blue and sunsets are red (§4).

### 1.3 The volume rendering equation (front-to-back form)

The light arriving at the eye along a ray of length D is:

  L_eye = T(0, D) · L_background + ∫₀ᴰ T(0, t) · [ σs(t) · L_in(t) + ε(t) ] dt

where the **in-scattered radiance** at a point is

  L_in(t) = Σ_lights p(θ) · V(t) · E_light + (ambient term) + (multiple-scattering term)

- **p(θ)** is the phase function (§1.5): how much of the light arriving from the light's direction turns toward the eye.
- **V(t)** is visibility toward the light: the light's own transmittance through the medium, which gives *volumetric shadow* (self-shadowing), multiplied by any opaque shadow map.
- **E_light** is the light's illuminance.

In words: every point on the ray glows by (how much stuff) × (how much light reaches it) × (how much of that light turns toward me). The glow is then dimmed by everything between that point and my eye.

Emissive media (aurora, nebula gas, fire) use the ε term. Aurora is so thin at 100 km altitude that it is effectively **pure emission, with no absorption and no scattering** (Lawlor and Genetti, 2011). Its march is just a sum of glow, which makes it the easiest volume to get right physically.

### 1.4 Integrating it: the step that most shaders get subtly wrong

The integral is evaluated as a loop. Cut the ray into segments of length Δ. Inside a segment, treat σs, σt and L_in as constant. Keep two running values: accumulated light **C** (starting at 0) and transmittance **T** (starting at 1).

**The naive loop.** Add the slice's light as `C += T · σs · L_in · Δ`, then update `T *= exp(−σt · Δ)`. This is what most beginner shaders do, including many famous Shadertoys.

Hillaire showed in his 2015 Frostbite talk and his 2016 course notes that **both possible orderings are wrong**:

- **Light first, then transmittance.** This uses the transmittance at the *front* of the slice for the whole slice, so it ignores the dimming that happens inside the slice. The result is too bright, and for dense media it **creates energy**: once σt·Δ > 1, a slice contributes more than 100 % of its light.
- **Transmittance first, then light.** This dims each slice by its own full thickness. The result is too dark.

Either way, **brightness depends on step size**. Halve the step count and the picture changes, which ruins adaptive stepping. Toft, Bowles and Zimmermann (Studio Gobo, 2016) show the same brightness-depends-on-step-length artifact.

**The energy-conserving fix** (Hillaire 2015 and 2016; Toft et al. 2016) integrates exactly across the segment:

  ∫₀^Δ T · e^(−σt·x) · σs · L_in dx = T · σs · L_in · (1 − e^(−σt·Δ)) / σt = T · ρ · L_in · (1 − e^(−σt·Δ))

So the loop body becomes:

  α = 1 − exp(−σt · Δ)      (this slice's opacity)
  C += T · ρ · L_in · α
  T *= (1 − α)

This is a lovely result: **a slice contributes its albedo × the light reaching it × its own opacity.** It is exactly the "over" operator from alpha compositing, applied front to back. Hillaire's notes show the effect: a dense medium needed 512 steps to converge with the naive rule and about 21 with this one.

How wrong is the naive version? The ratio naive / correct = σtΔ / (1 − e^(−σtΔ)):

| σt·Δ | Naive is too bright by |
|---|---|
| 0.1 | 5 % |
| 0.5 | 27 % |
| 0.64 | 35 % |
| 2.0 | 131 % |

The row σt·Δ = 0.64 is the house light bed at full density (§12).

**Numerical care.** When σt → 0, the expression (1 − e^(−x))/x is 0/0. Hillaire clamps σt to a tiny epsilon. A more robust approach evaluates the factor with a short series below a threshold: (1 − e^(−x))/x ≈ 1 − x/2 + x²/6 for x < 10⁻³. This avoids the float32 cancellation in 1 − 0.9999999.

**Emission** integrates the same way: `C += T · ε · (1 − e^(−σt·Δ)) / σt`. When σt = 0 this becomes `T · ε · Δ`, which is the pure aurora case.

**A refinement that has not shipped.** In his 2020 Physically Based Shading course talk, Hillaire derived a version in which the light's shadow value varies linearly from the start to the end of the segment instead of staying constant. It sharpens cloud shapes, but it divides by σt², needs clamping, and he described it as a bit unstable. It is worth knowing, but keep the constant-shadow version as the house default.

### 1.5 Phase functions: where the light turns

A phase function p(θ) is a probability distribution over directions. θ is the angle between the light's original direction of travel and its new one. It integrates to 1 over the sphere, so it has units of per steradian (sr⁻¹). Its **mean cosine** is called g, the asymmetry:

- g > 0: mostly forward scattering (droplets, haze).
- g = 0: symmetric scattering.
- g < 0: mostly backward scattering.

**Antenna analogy.** A phase function is the radiation pattern of a scatterer. Isotropic scattering is an omnidirectional antenna. Strong forward scattering is a high-gain dish pointed down the original beam.

**The sign convention trap.** The "forward peak" must line up with looking *toward* the light. Let `rd` be the camera ray direction (eye into the scene) and `toSun` the direction from the point toward the light. Light travels along −toSun and reaches the eye travelling along −rd, so the scattering cosine is μ = dot(−toSun, −rd) = **dot(rd, toSun)**.

House rule: **μ = dot(viewRayDir, dirToLight)**, and positive g means "glows around the light when you look at it." Sources differ. GLtracy's sample, for instance, uses `dot(dir, −l)` together with a *negative* g (`lslXDr/image.glsl:116-120`), and the two minus signs cancel. If your halo appears **opposite** the sun, flip one sign.

**The family you need:**

- **Isotropic:** p = 1/(4π) ≈ 0.0796.
- **Rayleigh** (molecules much smaller than the wavelength; the sky): p(μ) = 3/(16π) · (1 + μ²). It has two gentle lobes, forward and back.
- **Henyey-Greenstein (HG)**, introduced by Henyey and Greenstein in 1941 for dust between the stars:

  p_HG(μ, g) = (1 − g²) / (4π · (1 + g² − 2gμ)^(3/2))

  It is normalised, its mean cosine is exactly g, and it costs one power function. Its forward peak value is (1 + g)/(4π(1 − g)²). At g = 0.8 that is about 45 times brighter than isotropic; at g = 0.99 it is about 20,000 times. This is why silver linings need HDR (high dynamic range) and no clamping, which Schneider explicitly mentions for Nubis. Its backward value (1 − g)/(4π(1 + g)²) is about 16 times *darker* than isotropic at g = 0.8, which is why a single strong lobe makes clouds dull and dark when the sun is behind you.
- **Schlick's approximation** of HG (from Hillaire's 2016 notes): use k ≈ 1.55g − 0.55g³ and p = (1 − k²)/(4π(1 − kμ)²) with the house sign convention. It avoids the 3/2 power, but its error grows for |g| near 1, which weakens the silver lining.
- **Cornette-Shanks (1992)**, a Mie-like lobe with Rayleigh's (1 + μ²) shape built in:

  p_CS = (3/(8π)) · (1 − g²)(1 + μ²) / ((2 + g²)(1 + g² − 2gμ)^(3/2))

  Hillaire's 2020 atmosphere uses it for aerosols with g = 0.8.
- **Draine (2003)**, which generalises both:

  p_D(μ; g, α) = p_HG(μ, g) · (1 + αμ²) / (1 + α(1 + 2g²)/3)

  α = 0 gives HG; α = 1 gives Cornette-Shanks; g = 0 with α = 1 gives Rayleigh.
- **Dual-lobe HG** (Hillaire 2016): lerp(p_HG(g₀), p_HG(g₁), w). A strong forward lobe plus a weak backward lobe keeps clouds detailed when the sun is behind the camera.
- **Schneider's "silver lining" control** (Nubis, 2017): take the max of a baseline HG with g ≈ 0.6 and `silver_intensity × HG(0.99 − silver_spread)`. A max of lobes is not normalised, so energy is not conserved. Schneider presented it frankly as an art control, a band-aid he planned to replace.
- **The best analytic fit to real droplets today:** Jendersie and d'Eon (NVIDIA, SIGGRAPH 2023 Talks) blend an HG peak with a Draine body:

  p = (1 − w_D) · p_HG(g_HG) + w_D · p_D(g_D, α)

  All four parameters are fitted from one intuitive input, the mean droplet diameter d in micrometres (valid for 5 < d < 50):
  - g_HG(d) = exp(−0.0990567/(d − 1.67154))
  - g_D(d) = exp(−2.20679/(d + 3.91029) − 0.428934)
  - α(d) = exp(3.62489 − 8.29288/(d + 5.52825))
  - w_D(d) = exp(−0.599085/(d − 0.641583) − 0.665888)

  At d = 20 µm this gives g_HG ≈ 0.995, g_D ≈ 0.59, α ≈ 27 and w_D ≈ 0.50. It matches about 95 % of the Mie energy (the forward half), but not the fogbow or glory back-peaks. Hillaire's suggestion for those (2020): use a tabulated Mie phase function (from the MiePlot program) for the single-scattering pass only, and HG for the multiple-scattering octaves.

**What real cloud scattering looks like.** Water droplets produce a very sharp forward spike, a broad body, a *fogbow* around 120° from forward, and a *glory* near direct backscatter (Bouthors et al. 2008; Hillaire 2016). A single HG lobe has none of the back structure. That is acceptable for games, but it is why path-traced references look richer.

### 1.6 Multiple scattering: the look of clouds

Single scattering assumes each photon scatters once on its way to the eye. With albedo near 1 and τ near 100, real light scatters hundreds of times. Without some treatment of this, clouds look like grey smoke with bright rims: Hillaire calls it the dirty, smoky look. Path tracing gets it right but is far out of budget in real time. Production film rendering uses unbiased *delta tracking* and *ratio tracking* (Fong, Wrenninge, Kulla and Habel, Production Volume Rendering, 2017; Novák et al., 2018). Real time uses one of these approximations instead.

**(a) Octaves of single scattering** (Wrenninge, Kulla and Lundqvist, "Oz: the Great and Volumetric", 2013; adopted by Frostbite in 2016 and by Unreal in 2020). Compute single scattering N times and sum. For octave n (n = 0 … N−1), replace:

  σs → σs · aⁿ    σt (for the light's shadow only) → σt · bⁿ    g → g · cⁿ

with 0 < a, b, c < 1. Each higher "octave" stands for light that has bounced more. That light is dimmer (aⁿ), has effectively travelled through more medium, so its shadow is softer (bⁿ), and it is more uniform in direction (cⁿ·g).

- **Energy rule:** keep **a ≤ b**. Otherwise the scattering an octave adds exceeds the extinction it implies (Hillaire 2016).
- **Cost:** you compute the light's optical depth τ_L once and reuse it, adding only an exp and a phase evaluation per octave.
- **In practice:** Frostbite shipped N = 2.
- **Weakness:** it cannot represent sideways spread or a cone of scattering.

**(b) Schneider's two-Beer max** (Nubis, 2017): light energy = max(e^(−τ), 0.7 · e^(−0.25·τ)). This is a second, softer Beer curve that pushes light deeper into the cloud, taken with a max rather than a sum and faded out as you look toward the sun. It is cheaper than octaves and art-tuned.

**(c) Probability fields** (Nubis Evolved 2022 and Nubis Cubed 2023). Schneider treats multiple scattering geometrically. The cloud's own *dimensional profile* (a 0-to-1 gradient from outside to inside; §2.3) is the probability that light has been redirected. It is attenuated by a Beer curve, relaxed toward the sun and toward the cloud's interior. The result is the **inner glow**, like a flashlight behind thick cotton. Ambient light uses (1 − profile)^0.5, scaled in 2023 by e^(−summed density toward the sky) so that clouds under clouds get darker.

**(d) The sky's multiple scattering as a feedback loop** (Hillaire, EGSR 2020). For the atmosphere, Hillaire makes three assumptions:

1. Light that has scattered two or more times is uniform throughout a point's neighbourhood.
2. Its phase function is isotropic.
3. Visibility can be ignored for it.

Then two integrals over the sphere of directions around a point x do the work:

- **L₂ (second order).** Integrate, over all directions, the single-scattered light that would arrive at x from that direction, computed with unit sun illuminance and including the ground bounce, times the isotropic phase 1/(4π).
- **f_ms (transfer factor, unitless, between 0 and 1).** Integrate, over all directions, ∫σs·T dt along that direction, times 1/(4π). This is the fraction of light at x that the neighbourhood sends back to x after one more isotropic scatter.

Every further order multiplies by f_ms once more, so the total is a geometric series:

  Ψ_ms = L₂ · (1 + f_ms + f_ms² + …) = **L₂ / (1 − f_ms)**

**Amplifier analogy:** this is closed-loop gain = 1/(1 − loop gain). The first echo is L₂, and the room feeds back a fraction f_ms each round trip.

Ψ_ms depends only on altitude and the sun's zenith angle, so it lives in a tiny 32×32 LUT. At render time it is added to single scattering as σs · Ψ_ms · E_sun.

- Quality: 64 directions for high quality; for low-end hardware, just 2 directions (up and down) with the result doubled.
- Caveats (Hillaire, 2020 PBS course): accuracy drops for anisotropic phase functions (the strong Mie lobe), and the hue drifts for very dense coloured atmospheres.

### 1.7 The powder effect: dark edges on the sunny side

**Observation** (Schneider and Vos, SIGGRAPH 2015). Look at a cumulus with the sun behind you and the bulging, sun-facing edges are slightly **darker** than the crevices between bulges. A former Blue Sky colleague, Matt Wilson, likened it to piles of powdered sugar, and the name stuck.

**Why it happens.** In-scattered light at a point comes from the medium around it. A point right at the surface has little cloud around it to send light back toward you. A point a little deeper has more neighbours contributing. Beer's law alone says the surface is brightest. The powder term says the *probability of in-scattering toward the viewer* starts low at the surface and rises with depth.

**The math.** Schneider modelled the in-scatter probability as 1 − e^(−2τ) and multiplied it with Beer's law:

  E = e^(−τ) · (1 − e^(−2τ))

The GPU Pro 7 chapter (2016), and the many implementations reproduced from it, scale this by 2. With the 2, the curve is zero at τ = 0, peaks at τ = ln(3)/2 ≈ 0.55 with value ≈ 0.77, then follows Beer's tail.

**It is view-dependent.** It shows only when you look *away* from the light. Fade it toward 1 (no effect) as μ → 1. Schneider ramped it with the view-to-light angle.

**The critique.** Hillaire (2020) points out that it is not multiple scattering and does not conserve energy. Overdone, it gives a "dirty cotton" look. Unreal's alternative stays physically based: **lower the albedo near cloud edges**, where density is low, through the material graph, so rays at the edges carry less scattered light. Hillaire compares it to ambient occlusion: wrong, but it helps visually. Keep it subtle.

**How Nubis evolved it.**
- **2017:** replaced powder with an *in-scatter probability* = depth term × vertical term. The depth term is 0.05 plus a low-detail density sample raised to a power that changes with height. The vertical term is a ramp that darkens cloud bottoms, because nothing bright lies below a cloud.
- **2022 and 2023:** replaced that with the dimensional-profile probability fields described in §1.6(c).

---

## 2. Density fields from noise

### 2.1 The noise toolbox

| Noise | What it looks like | Use in volumes |
|---|---|---|
| **Value noise** | Smoothed random lattice | Cheapest base; blobby |
| **Gradient (Perlin) noise** | Smooth, connected, "wispy" | Connected cloud masses, stratus |
| **Worley (cellular) noise, F1** (Worley 1996) | Distance to the nearest random point; web-like | **Inverted** (1 − F1), it becomes packed round billows: cumulus cauliflower |
| **Perlin-Worley** (Schneider 2015) | Perlin dilated by inverted Worley | Keeps Perlin's connectedness and adds billows. Schneider (2017) presents it as remapping the Perlin value using the inverted Worley as the new floor |
| **fBm** (fractional Brownian motion) | Sum of octaves: frequency × lacunarity (≈ 2) and amplitude × gain (≈ 0.5) per octave | Multiscale detail. Rotate the domain between octaves to hide lattice alignment |
| **Ridged fBm** | 1 − abs(noise) per octave | Sharp creases: nebula filaments |
| **Domain warp** | Sample noise at a position displaced by noise | Swirls and folds without a fluid simulation |
| **Curl noise** (Bridson, Houriham and Nordenstam, 2007) | Curl of a noise vector field, so it is divergence-free | Fake turbulent flow that never piles up or thins out; Schneider uses a 2D curl texture to distort detail noise |
| **Trig and "spiral" noises** | Sums of sin/cos with the domain rotated a little each octave (otaviogood's spiral noise; nimitz's deformed periodic grids) | Textureless and fast, which matters when a 3D texture fetch per step would dominate (`MsVXWW/image.glsl:47-81`, `3l23Rh/image.glsl:44-51`) |
| **Alligator noise** (SideFX) | Layered-Worley look with more cloud-like lacunarity | Nubis Cubed's billows; "curly alligator" (inverted, then curl-distorted) for wisps |

**Texture budgets that shipped** (Schneider 2015):
- one 128³ RGBA 3D texture: Perlin-Worley plus three Worley octaves, for the base shape;
- one 32³ RGB 3D texture: Worley octaves, for detail;
- one 128² RGB 2D texture: curl noise.

The whole sky's unique memory was about 20 MB. Frostbite collapsed the base noise into a single-channel volume texture to cut bandwidth (Hillaire 2016). Generators: Hillaire's TileableVolumeNoise (MIT licence) and Guerrilla's Houdini noise generator.

**Level of detail (LOD) by distance.** Distant samples don't need high octaves.
- Inigo Quilez's cloud demo drops octaves with log₂ of distance (`XslGRr/image.glsl:166`, read-only; see §11).
- Nubis Cubed raises the 3D texture's mip level with log₂(1 + distance × k), worth about 15 %.

**"Twice-folded" noise** (Schneider 2023). Expand a noise value to the range −1 to 1, take abs, rescale, and take abs again. The result looks higher in frequency without another texture fetch. It was used only near the camera, blended in over 50 to 150 m.

### 2.2 Shaping: remap beats multiply

Schneider's central modelling tool is the **remap** (called "fit" in Houdini and "setRange" in Maya):

  remap(v, a, b, c, d) = c + (v − a) · (d − c) / (b − a)

Using noise to *erode* a shape by remapping, instead of multiplying by it, keeps the **core** of a cloud dense and only carves the **edges**. Schneider's analogy is carving clay in which the detail is already embedded and only revealed by the carving.

**The shaping stack** (Schneider 2015 and 2017; Hillaire 2016):

1. **Height profile.** Density versus normalised height h ∈ [0, 1] inside the cloud layer. It is a ramp up at the bottom times a ramp down at the top. For stratus, the 2017 talk gives remap(h, 0, 0.1, 0, 1) × remap(h, 0.2, 0.3, 1, 0). A *cloud type* value from 0 to 1 shifts these breakpoints (0 = stratus, 0.5 = stratocumulus, 1 = cumulus). Frostbite instead reads the profile from a small artist-painted "cloud type" texture: height on y, type on x, and erosion amount in a second channel. Height profiles also make the *bottoms* wispy, because density is reduced there.
2. **Coverage.** A 0-to-1 value per map position. Applied as a remap threshold, it makes clouds **inflate and deflate** smoothly as coverage changes. Sources disagree on the polarity: the 2017 slide remaps with the coverage value as the floor. **Test the sign by sweeping coverage up and checking that the sky fills.**
3. **Base shape.** The low-frequency noise multiplied by (or remapped with) profile × coverage.
4. **Detail erosion.** Subtract or remap with high-frequency noise, **only where the base is non-zero**. Inverted Worley at the cloud base gives wisps there; curl noise distorts the detail coordinates.
5. **Wind.** Offset the sample position by wind × time. **Skew with height**: Schneider adds height × wind × 500 m, because wind changes with altitude. Animating the detail noise but **not** the coverage keeps an art-directed arrangement stable while it appears to evolve ("pseudomotion").
6. **Anvils.** Raise coverage to a power below 1 near the top of the layer, so cumulonimbus tops spread out.
7. **Weather map.** A 2D texture over the world.
   - Nubis 2015: R = coverage, G = precipitation, B = type.
   - Nubis 2017: R and G = two coverage variants (Perlin for connected masses, Perlin-Worley for islands), B = type.
   - Frostbite: R = density, G = type index.

   Precipitation pushes toward cumulonimbus and increases absorption, so rain clouds darken. Painting black onto the map makes a hole where the art director wants one (Schneider 2017).

### 2.3 From 2.5D to voxels: where Nubis ended up

- **2.5D (2015 to 2022).** 2D "Nubis Data Fields" (min height, max height, coverage, top type, bottom type) are decompressed in the shader into a 3D *dimensional profile*, then up-rezzed with 3D noise.
  - The *vertical profile* method (for unreachable tropospheric clouds) gives profile = vertical_profile × coverage.
  - The *envelope* method (for fly-through orographic clouds) gives profile = top gradient × bottom gradient × edge gradient.
  - Density = saturate(noise − (1 − profile)): the inverse profile is subtracted from the noise.
- **Voxels (2023, the Burning Shores DLC).** Clouds are grown with a fluid solver in Houdini and composited into what Schneider calls "Frankencloudscapes". They are stored as **512×512×64** voxel volumes at **8 m** per voxel. The channels are: dimensional profile (made from a signed distance field (SDF) of the cloud, so there is a clean outside-to-inside gradient), detail type, and density scale. They are BC6-compressed, about 17 MB.
- **Up-rez instead of brute resolution.** Detail noise erodes the 8 m profile down to about **0.5 m** apparent precision at sample time. A dense explicit grid cost over 30 ms; the up-rez cost about 10 ms before ray-march optimisations. The lesson Schneider draws: perceived complexity matters, not voxel count. **Balance memory fetches against arithmetic.**

**SDF-shaped volumes.** For hero shapes and stylised clouds (Wallis 2020; Heckel 2023), use density = clamp(−sdf × k, 0, 1) + noise. Any signed distance field (spheres, tori, blended with smooth-min) becomes a cloud. This is how to make "a cloud shaped like X".

---

## 3. Marching: the loop, made fast and clean

### 3.1 Bounds: never march empty space you can rule out analytically

- **Slab** (a flat cloud layer between y₀ and y₁): solve for t where the ray enters and leaves. This makes it trivial to skip the march entirely when looking down from above the layer (`XslGRr/image.glsl:128-150` shows the case analysis).
- **Spherical shell** (curved Earth, clouds that dip below the horizon, an atmosphere): intersect two spheres. A spherical cloud layer is what makes clouds descend correctly into the horizon. Shrinking the radius "forces the scale" (Schneider 2015).
- **Box or sphere** around a local volume (an aurora box, a nebula sphere).
- **Float precision at planet scale.** A camera on a 6,360,000 m sphere in float32 has about 0.5 m of position resolution. The ray-sphere term `dot(o, o) − R²` subtracts two numbers near 4×10¹³ and loses most of its digits, which shows up as noisy horizons and rings. Fixes:
  1. Work in **kilometres** for the atmosphere.
  2. Compute `dot(o,o) − R²` as `h · (2R + h)` from the altitude h directly.
  3. Use the numerically stable quadratic: q = −b − sign(b)·√disc, then t₀ = q and t₁ = c/q.

### 3.2 Step strategies

| Strategy | Rule | Who uses it | Trade-off |
|---|---|---|---|
| Uniform | Δ = length / N | Teaching, aurora boxes (`ttScDc/image.glsl:221`) | Wastes steps in empty regions |
| Distance-proportional | Δ = max(Δmin, k·t) | Quilez's clouds (`XslGRr/image.glsl:160`); Nubis vertical-profile clouds (3 m plus about 60 m per 16 km of distance, 2022) | Matches pixel footprint growth; cheap |
| Optical-depth-limited | Δ ≤ τ_target / σt | General expert practice | Keeps each slice's opacity small, so integration error stays small |
| Cheap/expensive two-mode | Big steps with a low-detail sample until density > 0; step **back** once; small full-detail steps; return to cheap after about 10 consecutive empty samples | Schneider 2015 and 2017 | Huge win: detail noise only near clouds |
| Density-driven | The smooth density doubles as a distance proxy: step = f(density) | nimitz, Protean clouds (`3l23Rh/image.glsl:88`, about 40 % faster) | Needs a smooth field |
| SDF hybrid | Δ = max(sdf(p), adaptive(t)) + jitter | Nubis Cubed (adaptive = max(1 m, 0.08·√t)) | SDF leaps between clouds; the adaptive term takes over inside them |
| 2D distance field | Read a distance-to-nearest-curtain map; step up to 1000 km in empty sky, 2 km inside curtains | Lawlor and Genetti's aurora | Skipping is 3.5 times faster than naive stepping |
| Polynomial stride | Δᵢ grows like i^p | nimitz aurora sheets (`XtGGRt/image.glsl:66`) | Dense near the bright lower edge, sparse in the faint tall rays |
| Split resolution | Render < 200 m at 480×270 and > 200 m at 960×540 | Nubis Cubed, for its 40 and 60 Hz modes | About 50 % saving; pixelation shows only on dense sharp features |

**The invariant: if you vary Δ, you must use the energy-conserving integration from §1.4**, or brightness will follow your step size. Protean clouds handles its irregular steps for fog with a related trick. It evaluates fog as the **difference of an analytic fog integral** between consecutive rendered steps (`3l23Rh/image.glsl:84-86`), so skipped steps cannot lose or double-count fog.

### 3.3 The light march (self-shadowing)

For every view sample you need the optical depth toward the light. A naive approach is N_view × N_light density samples: 64 × 6 = 384 evaluations per pixel. The cures, roughly in order of sophistication:

- **Cone sampling** (Schneider 2015). Take 6 samples in a cone toward the sun at increasing spacing, with the last placed far away to catch shadows from distant clouds. The cone spread smooths the banding of so few samples and blends in neighbouring density, which gives a soft ambient feel. Switching light samples to the cheap shader once the view alpha passes 0.3 made it twice as fast. In 2017: 5 cone samples with decreasing LOD.
- **Only light where density is non-zero** (Nubis 2017: 8.1 → 3.34 ms on PS4).
- **One-sample directional derivative** (Quilez). Lighting ≈ clamp((density(p) − density(p + ε·L)) / k). One extra sample replaces a whole light march. It is not physically based, but it is very cheap (`XslGRr/image.glsl:175`).
- **Precomputed summed density** (Nubis Cubed). The first 2 light samples are taken live. The rest come from a 256×256×32 voxel grid of precomputed optical depth toward the sun, rebuilt over 8 frames for 0.1 to 0.2 ms. This cut render time by about 40 % **and** added long-distance shadows between clouds. Schneider calls it a rare optimisation that looked better.
- **Beer Shadow Map** (Hillaire 2020). Per shadow-map texel, store front depth z, mean extinction behind z, and maximum optical depth. Transmittance at depth d is exp(−min(maxOD, meanExt·max(0, d − z))). Compare the exponential shadow map (ESM), which is Beer's law with a single constant extinction for every texel and wrongly converges to black over long distances. The BSM is not coloured but covers enormous distances; secondary marches are sharp and coloured but short.
- **Transmittance LUT** for the sky (§4.4): the sun's transmittance through the atmosphere from any altitude and zenith angle is a single texture fetch.

### 3.4 Early exit, and the branch-divergence surprise

Stop when T < about 0.01 to 0.02: nothing behind can matter. But beware of "optimising" with branches. GPUs run threads in lockstep groups (*warps* or *wavefronts*), and if neighbouring pixels take different branches, both paths are paid for. Lawlor and Genetti found that **skipping** the aurora sample when far from a curtain was at least 18 % **slower** than sampling everywhere, and other attempts were up to seven times slower. **Measure before you branch.**

### 3.5 Jitter: turning banding into noise

**Why banding happens.** With a fixed start and fixed steps, neighbouring pixels sample the same depth slices. The volume is effectively cut into N parallel sheets, and you see their edges as contour lines, like tree rings, wherever density changes smoothly. This is *aliasing* along the ray.

**Jitter** offsets the first sample by u·Δ, with u ∈ [0, 1) different per pixel. Each pixel now samples a different set of depths. The error is still there but it is **decorrelated**: banding becomes fine noise.

**Audio analogy:** this is exactly dither before an analogue-to-digital converter. Quantisation distortion becomes a benign noise floor.

**The noise you jitter with matters:**

- **White noise** (`fract(sin(dot(...)))`): breaks the banding but clumps, so the noise is visibly ugly.
- **Blue noise** (a tiled precomputed texture, for example Christoph Peters' free textures): the energy is in high frequencies only, so it reads as fine even grain and blurs away well. Alan Wolfe's comparison with 16 steps shows blue noise is clearly better than white.
- **Interleaved Gradient Noise (IGN)** (Jorge Jimenez, Call of Duty: Advanced Warfare, 2014): IGN(x, y) = fract(52.9829189 · fract(0.06711056·x + 0.00583715·y)). It needs no texture, sits between dithered and random, and is designed for temporal accumulation.

**Static versus animated jitter: the house law.**
- If **nothing accumulates across frames**, jitter must be **static per pixel**. Per-frame jitter **is** crawling film grain. That rule is written into `shader-craft` and `aurora-shader.js:211-216`.
- If you **do** accumulate (TAA, an exponential moving average), animate the jitter so that each pixel visits a low-discrepancy sequence over time: add frame × golden-ratio-conjugate (0.618…) to a blue-noise value and take fract, or shift IGN by 5.588238 pixels per frame (Wolfe).
- Nubis Cubed does **both**: animated jitter within 250 m, where temporal data resolves it, and static jitter beyond, so distant clouds don't shimmer.

**The cost.** Toft et al. (2016) measured that per-pixel jitter raised draw time from 2.3 ms to 7.5 ms on a GTX 1080, because neighbouring pixels no longer fetch neighbouring texels (texture cache misses). The same offset for every pixel cost nothing extra but cannot be denoised.

### 3.6 Temporal reprojection and accumulation

Most real-time volumetrics are not computed in full each frame. The known approaches:

- **Schneider and Vos, 2015 (Nathan Vos's idea).** Render clouds into a **quarter-resolution** buffer. Each frame, update **1 of the 16 pixels** in every 4×4 block, in a Bayer order. Every other pixel is **reprojected** from the previous frame: you know where that sky direction was last frame. Where reprojection fails (screen edges), use a low-resolution fallback. Speedup about 10 times: a 20 ms effect became about 2 ms. The cost is up to 16 frames of latency, which shows when the camera moves fast. **Video analogy:** interlaced or rolling refresh.
- **Hillaire 2016 (Frostbite).** Each frame, randomly offset samples within their depth slice. Blend the new result with the reprojected history using a constant factor, an **exponential moving average** (EMA): history = lerp(history, current, α). The effective sample count is about 1/α. Fourteen samples per frame then look like many more.
- **Toft et al. 2016.** Use 8 steps (not 128), jittered, and let the engine's TAA (Playdead's open-source implementation from *Inside*, MIT licence) clean it up. Quarter-res, 8 steps, jitter and TAA cost 2.4 ms against 297.7 ms for full-res 128 steps.
- **Bauer 2019 (Red Dead Redemption 2), as Hillaire summarises it.** Quarter-res tracing with TAA upsampling: instant but softer, against Schneider's sharp but 16-frame-latent result.
- **Neighbourhood clamping** (Brian Karis, Unreal, 2014). Clamp the history colour into the min/max of the current frame's 3×3 neighbourhood (often in YCoCg colour space) before blending. This rejects stale history and is the main cure for ghosting.
- **Reprojecting a volume needs a depth.** Infinitely distant sky reprojects by direction alone. For clouds at finite distance, use a representative depth:
  - Hillaire's **transmittance-weighted mean depth**, Σ T(xₙ)·depth(xₙ) / Σ T(xₙ), skipping empty samples;
  - or the depth at which accumulated alpha crosses 0.5 (Schneider 2017).

  The same depth is used to look up the aerial perspective that is applied to the clouds afterwards (§4.7).

**Hardware analogy.** Temporal accumulation is signal averaging on a sampling oscilloscope. Each sweep is noisy, but averaging many sweeps that are locked to the same trigger (the reprojection) recovers the clean waveform. If the trigger is wrong you get ghosting: the reprojection is lying.

---

## 4. The sky and the atmosphere

### 4.1 Why the sky looks the way it does

- **Blue sky.** Air molecules are far smaller than light's wavelength, which gives Rayleigh scattering ∝ 1/λ⁴. Blue (440 nm) scatters about (680/440)⁴ ≈ 5.7 times more than red (680 nm). The standard coefficients show exactly that ratio: 33.1 against 5.802 (×10⁻⁶ m⁻¹).
- **Red sunsets.** Near the horizon, sunlight crosses tens of times more air. The blue is scattered out before it reaches you, and what is left to scatter toward you is orange and red.
- **White haze and the halo around the sun.** Aerosols (dust, water, pollution) are about the size of the wavelength. They give Mie scattering, which is almost colourless and strongly forward (g ≈ 0.76 to 0.8). That produces the bright glow around the sun and the whitening near the horizon.
- **Ozone.** It absorbs mostly in the green-red range (the Chappuis band) and scatters nothing. Without it, twilight skies come out too yellow and the zenith is not blue enough (Hillaire 2016, citing Adams, Plass and Kattawar, 1974).
- **Multiple scattering in the sky.** It matters most at sunset and in thick atmospheres. Without it, twilight is too dark and too saturated.

### 4.2 The standard Earth model (Hillaire, EGSR 2020; after Riley et al. and Bruneton and Neyret)

The atmosphere is modelled as a spherical shell:

- **Ground radius** 6360 km; **top** 6460 km (100 km thick); ground albedo 0.3.
- **Rayleigh:** σs = (5.802, 13.558, 33.1) × 10⁻⁶ m⁻¹ for RGB, no absorption, density e^(−h/8 km), phase 3/(16π)(1 + μ²).
- **Mie:** σs = 3.996 × 10⁻⁶ m⁻¹ and σa = 4.40 × 10⁻⁶ m⁻¹, density e^(−h/1.2 km), Cornette-Shanks phase with g = 0.8.
- **Ozone:** absorption only, σa = (0.650, 1.881, 0.085) × 10⁻⁶ m⁻¹. Its density is a **tent** peaking at 25 km and falling to zero at 10 and 40 km (30 km wide).

The RGB coefficients are sampled at single wavelengths, about 680, 550 and 440 nm. They are not integrated over the eye's response (Hillaire 2016, after discussion with Bruneton).

### 4.3 Brute force first: single scattering by nested marching (Nishita et al. 1993)

For each view sample p on the ray:

1. March from p toward the sun to the top of the atmosphere, accumulating the sun-path optical depth.
2. Combine it with the view-path optical depth so far.
3. Add σs_R·p_R(μ) + σs_M·p_M(μ), times transmittance, times sun illuminance.

GLtracy's sample does exactly this: 80 view steps by 8 light steps, a scaled planet, separate Rayleigh and Mie accumulators (`lslXDr/image.glsl:53-124`). Sean O'Neil's GPU Gems 2 chapter (2005) is the classic shader-friendly derivation. This approach is fine for a reference or a single still. It is too slow per pixel per frame at full resolution, and it has no multiple scattering.

### 4.4 The LUT architecture: how production skies really work

A **look-up table (LUT)** is a precomputed answer stored in a texture, read in one fetch. It is the GPU's version of a sine table in ROM. The atmosphere is spherically symmetric, which collapses most quantities to two or three dimensions.

**Bruneton and Neyret, 2008 (with Bruneton's documented 2017 rewrite, BSD licence).**
- A transmittance LUT (altitude by zenith angle), a 4D scattering LUT that already includes all orders of multiple scattering, and an irradiance LUT.
- The 2017 version adds ozone, custom density profiles, and spectral-to-luminance conversion.
- Accurate, but the 4D table is large, slow to rebuild (Hillaire quotes about 250 ms), and prone to horizon artifacts.

**Hillaire, EGSR 2020 (shipped in Unreal Engine; reference code MIT licensed).** He observed that the sky is *low frequency* except near the horizon and in shadows. Small LUTs therefore suffice, and all of them can be rebuilt every frame, so artists can change the atmosphere live:

1. **Transmittance LUT, 256×64.** Sun transmittance from any altitude and zenith angle, 40 samples per texel.
2. **Multiple-scattering LUT, 32×32.** Ψ_ms from §1.6(d), indexed by altitude and sun zenith; 20 samples by 64 directions.
3. **Sky-view LUT, about 200×100.** The distant sky in latitude-longitude around the camera, ray-marched with about 30 samples. The latitude mapping is **non-linear**: v = 0.5 + 0.5·sign(l)·√(|l|/(π/2)). That spends texels on the horizon, where colour changes fast; half of the upper half of the texture covers the first 22.5° above the horizon. Any number of suns can be baked in, and the sun disk is composited afterwards.
4. **Aerial perspective volume, 32×32×32** over 32 km: a *froxel* grid (frustum voxel; §5.2). RGB holds in-scattered light and A holds mean transmittance. It is applied to opaque and transparent surfaces alike, per pixel or per vertex.

Performance from the paper and the 2020 PBS slides:
- **GTX 1080 at 720p:** the LUT passes cost about 0.01 ms (transmittance), 0.05 ms (sky-view), 0.04 ms (aerial perspective) and 0.07 ms (multiple scattering). The whole sky and aerial perspective came to about 0.31 ms.
- **Phone-class GPU (iPhone 6s):** about 1 ms.
- **Views from space:** the sky is ray-marched per pixel instead, about 0.5 ms.

**Analytic sky models.** Preetham, Shirley and Smits (1999) is driven by "turbidity". Hosek and Wilkie (2012) is spectral. Both are cheap closed-form functions fitted to a reference, but they assume a viewer on the ground of an Earth-like planet. Use them for a quick, correct daylight dome. Use the LUT method when you need time of day, altitude, space views, alien atmospheres or artist control.

### 4.5 Sun, moon and stars (Hillaire 2016)

- Draw the sun as a disk of the correct angular size with **limb darkening** (the disk is darker toward its edge). A small gradient is enough.
- The moon is about 0.5° across.
- Stars can be coloured by temperature via Planck's law (Fabrice Neyret's approach, cited by Hillaire).

### 4.6 Fog of the atmosphere on things: aerial perspective

Distant objects pick up sky-coloured in-scatter and lose contrast:

  colour_final = colour_object · T_AP + L_AP

Both terms come from the aerial perspective volume, or from the analytic fog in §5.1.

### 4.7 Clouds inside the atmosphere (Hillaire 2016; Schneider 2017)

- **Aerial perspective on clouds.** Clouds are kilometres away, so they must be fogged. Without this, a visible seam appears at the horizon between clouds and terrain. To keep it cheap, compute one representative cloud depth (the weighted mean depth from §3.6) and apply the aerial perspective once to the integrated cloud colour and transmittance. Schneider stores an "atmosphere blend factor" channel computed at the alpha = 0.5 depth.
- **Clouds on the atmosphere.** A thick overcast blocks sunlight from scattering in the air below it: L_AP = L_AP × T_cloud + L_cloud (Hillaire 2016).
- **Per-step atmospheric transmittance in the cloud march.** Sunset light reaching high clouds is redder than light reaching low clouds. Hillaire (2020) shows this makes sunsets markedly more realistic.
- **Cloud shadows on the world.** Bake cloud transmittance into a 2D texture projected from the sun, or use a Beer Shadow Map. In Frostbite it also feeds global illumination.

---

## 5. Fog and god rays

### 5.1 Analytic fog, for every surface, almost free (Quilez's "better fog")

1. **Exponential fog:** fog = 1 − e^(−b·distance). Mix the surface toward the fog colour by that amount.
2. **Split extinction from in-scattering:** colour = surface · e^(−b_ext·d) + fogColour · (1 − e^(−b_in·d)). Use separate, even per-channel (RGB), coefficients. Blue-tinted distance and warm absorption are then independent controls.
3. **Sun-tinted fog:** fogColour = mix(away colour, toward colour, pow(max(dot(rd, toSun), 0), k)). This is a cheap stand-in for Mie forward scattering, the glow toward the sun.
4. **Height fog, solved analytically.** With density ρ(y) = a·e^(−b·y) and a ray o + s·d, the optical depth to distance t is

   τ(t) = ∫₀ᵗ a·e^(−b(o_y + s·d_y)) ds = (a/b) · e^(−b·o_y) · (1 − e^(−b·d_y·t)) / d_y

   When the ray is horizontal (d_y → 0) the formula is 0/0. Its limit is a·e^(−b·o_y)·t. A stable single expression is τ = a·e^(−b·o_y)·t·F(b·d_y·t), with F(k) = (1 − e^(−k))/k and a series for |k| small. This is the "fog that pools in valleys" every outdoor scene wants, at no march cost.

### 5.2 Volumetric fog with real shadows: froxels

**Bart Wronski (Assassin's Creed IV, SIGGRAPH 2014)** introduced the frustum-aligned 3D texture, or *froxel* grid (frustum + voxel):

1. A compute shader **injects** density and lighting (shadow maps, local lights) into each cell.
2. A second pass **integrates** front to back along depth.
3. Any surface or particle then looks up its fog with one 3D texture fetch at (screen uv, depth).

Depth slices are distributed exponentially, so they are finer near the camera.

**Hillaire (Frostbite, 2015)** made the froxel material physically based: scattering, absorption, phase g and emission as a "participating media material", with volumetric shadow maps and temporal jitter plus reprojection of the froxel samples.

**Hardware analogy:** a froxel grid is a framebuffer with depth slices, a cache of the fog that every consumer reads instead of marching on its own.

### 5.3 God rays (crepuscular rays)

The physical cause is in-scattering times **visibility** along the view ray: shafts are the parts of the medium that can see the sun. Four ways to get them:

1. **March the medium with a shadow test at each step.** This is the correct way, and it comes free with any volumetric march that has a light term. Alan Wolfe's demonstration is the clear version: count the fraction of the 16 steps that are lit, then blend fog colours. Blue-noise jitter makes 16 steps viable. The house light bed already exploits this principle: "simulate the cause, not three symptoms" (shader-craft).
2. **Screen-space radial blur** (Kenny Mitchell, GPU Gems 3, chapter 13, 2007).
   - First render an occlusion pass: occluders black, sky bright.
   - For each pixel, step N samples toward the sun's screen position. Each sample is weighted by weight × decay^i, the sum is scaled by exposure, and a "density" parameter sets sample spacing.
   - **Failure modes:** it breaks when the sun is off-screen, since rays flicker as occluders cross the edge. Shafts from behind an object are wrongly drawn **in front of** foreground objects. It degenerates when the sun is 90° to the view. With few samples it bands, which needs jitter or blur.
3. **Epipolar sampling** (Engelhardt and Dachsbacher, 2010; used in Intel's "Outdoor Light Scattering" sample). In-scatter changes fastest *across* lines radiating from the sun's screen position, so you sample sparsely along those lines and interpolate. (Not fetched for this report; named for completeness.)
4. **Schneider's hybrid** (Nubis, 2017). A radial-blur shaft buffer is used **as a mask on the Mie in-scatter term** of the atmosphere shader, not added on top. The colour therefore matches Mie scattering, shafts are never drawn over nearby scenery, and they connect seamlessly to other volumetrics.

---

## 6. A cloud renderer, end to end (the composite recipe)

This is what Nubis 2015/2017 and Frostbite 2016 have in common, in the order a frame runs:

1. **Bounds.** Intersect the view ray with the spherical cloud shell (Schneider used 1.5 to 4 km for the low clouds). Cull rays below the horizon and rays blocked by opaque depth. On PS4 these culls took 3.34 ms to 1.81 ms to 1.2 ms (Schneider 2017). Use a conservative (max) low-resolution depth so that thin moving occluders don't cause reprojection holes.
2. **Resolution and amortisation.** Quarter resolution, one-in-16 pixel updates plus reprojection; or half resolution with jitter, EMA and TAA.
3. **March.** About 54 to 128 potential steps (more toward the horizon). Cheap/expensive mode switching, with one step back on entering a cloud. Energy-conserving integration. Early exit at alpha ≈ 1.
4. **Density sampler.** Weather map (coverage, type, precipitation) → height profile → base noise → coverage remap → detail erosion with curl distortion, only where the base is above zero → wind offset and height skew.
5. **Lighting per non-zero sample:**
   - direct = sun × [Beer or two-Beer/octave multi-scatter of the cone-sampled optical depth] × phase (dual lobe or silver-lining max) × [powder or in-scatter probability, view-faded];
   - ambient = lerp(sky bottom colour, sky top colour, height fraction), or Nubis's (1 − profile)^0.5;
   - rain clouds get extra absorption.
6. **Composite.** Apply aerial perspective at the cloud's representative depth. Mask Mie god rays by sun visibility. Blend over the sky. Write cloud shadows for the world.
7. **Tonemap last.** All of the above is linear HDR. (House order: superlinear highlight, then the tanh shoulder.)

**Budgets that shipped:**

| Pipeline | Cost |
|---|---|
| Horizon Zero Dawn, PS4 | About 2 ms; about 1.2 ms after 2017 culling |
| Frostbite, Xbox One, worst case (16 samples, half resolution, two octaves) | 0.91 ms at 720p; 1.60 ms at 1080p |
| Nubis Cubed fly-through voxel clouds, PS5 | 2.2 to 4 ms at 960×540 |
| Toft et al., GTX 1080, 1080p, quarter resolution | 2.4 ms |

Schneider's warning applies throughout: carelessly built procedural systems are "excellent at generating ugly" (Schneider, 2017). Aim first for "80 % not ugly".

---

## 7. Aurora: how real aurora looks, and how shaders fake curtains

### 7.1 The real thing

- **What it is.** Electrons of roughly 1 to 20 keV come down along Earth's magnetic field lines and excite the thin upper atmosphere (Lawlor and Genetti 2011; NOAA SWPC aurora tutorial). The light is **emitted**, not scattered.
- **Geometry.** The currents are compressed into **sheets about 1 km thick** that run for **hundreds to thousands of km**. That 1 : 1000 aspect ratio is why curtains read as ribbons and draperies. The lower edge sits at about **90 to 100 km**; the curtain extends upward for 100 to 300+ km.
  - Electrons follow field lines, which at auroral latitudes dip steeply, so curtains hang nearly vertically, with fine **field-aligned rays**.
  - When a curtain passes overhead, those parallel rays converge in perspective toward the magnetic zenith, giving the **corona** form.
- **Motion** (NOAA).
  - Evening: a quiet arc, sometimes several parallel arcs.
  - Near midnight: ripples running along the curtain "like a hand along a curtain", folds and swirls, and a **westward travelling surge**.
  - Morning: diffuse patches that **pulse with roughly a 10-second period**.
  - Lawlor and Genetti describe substorms that start as smooth curtains, then fold and break into many overlapping fragments, then recover as dim pulsating aurora.
- **Colour by altitude and species:**
  - **Green, 557.7 nm**, atomic oxygen: the familiar body of the curtain, brightest around 100 to 150 km and fading above about 200 to 250 km. Its excited state lives well under a second, so the green **tracks the curtain's motion closely**.
  - **Red, 630.0 nm**, atomic oxygen: high, above about 200 km (NOAA's tutorial places the dominant red above about 300 km). Its excited state lives roughly **two minutes**, so in the denser air lower down it is quenched by collisions before it can emit. Because it lasts so long, the red **lags and blurs**: it is a slow afterglow of where the curtain has been. Lawlor and Genetti list "red slow-glow" as future work for exactly this reason.
  - **Blue and violet, 391.4 and 427.8 nm**, ionised molecular nitrogen, plus nitrogen's red bands: a **purple-pink fringe along the lower edge** during energetic displays. Sunlit tops of tall rays can also turn purple.
- **Eye versus camera.** At night the eye relies on rod vision, so naked-eye aurora is often a pale grey-green. Long-exposure photographs saturate the colours and integrate the slow red. Choose consciously which one you are rendering.

### 7.2 How shaders fake it: three families

**Family A: 2D stretched screen-space noise.** Domain-warped fBm, scaled anisotropically so its features stretch vertically, is coloured in bands by screen height: red top, green middle, cyan or blue low. The house sketch `design/vfx-sketches/daniil-curtains.frag:87-104` is this kind: separate red-top, green-middle and blue-bottom bands, each with its own stretched noise and height window. It is cheap and pretty, but it has no perspective or parallax, it cannot be flown through, and it reads as painted on the sky.

**Family B: a stack of horizontal sheets sampling one 2D footprint.** This is nimitz's 2017 technique (`XtGGRt/image.glsl:58-89`); `ffG3Rc/image.glsl:77-157` is a descendant of it.

- *Footprint.* An animated 2D field that looks like long bright bands with ragged, trail-like detail. nimitz builds it from a few octaves of rotated, warped triangle-wave functions, chosen because it is cheap enough to evaluate about 50 times per pixel (`XtGGRt/image.glsl:33-55`).
- *Extrusion.* Intersect the view ray with about 50 horizontal planes at increasing altitude and sample the **same** footprint on each. Because the pattern is identical layer to layer, it **extrudes vertically**, and the eye reads vertical rays and hanging curtains. **This is Lawlor's factorisation (footprint × vertical profile) achieved by sampling instead of by marching.**
- *Polynomial spacing.* Layer heights grow like i^1.4, so they are dense low down, where the curtain is bright and sharp, and sparse up in the faint rays (`:66`). nimitz notes this works because the upper trails are always fainter than the base.
- *Banding control.* A per-pixel jitter whose amplitude **ramps up with layer index** (`:65`), plus a **running average** across successive layers, a one-pole low-pass that smooths the stepping (`:73`).
- *Colour.* Each layer gets a hue from a cosine palette by its index, so hue changes with height. Each layer's weight decays exponentially with index after a short fade-in (`:74`), so the curtain is brightest at its lower edge and fades upward, just like the real thing. Fade near the horizon (`:78`).
- *Reflections.* For rays below the horizon, mirror the ray and reuse the same function, dimmed, to get the aurora on a lake (`:155-165`).
- *Limits.* It only looks right from below. Curtains cannot fold back on themselves in 3D, and grazing angles flatten.
- `ffG3Rc` adds explicit height-band colour weights, a 1D "ray flow" striation function along the screen x axis (`:70-75`), and a local rotational swirl for folds (`:113-124`).

**Family C: a true emissive volume.** This is Lawlor and Genetti (2011), and alro's MIT-licensed `ttScDc`.

- Emission(x, y, z) = footprint(x, z) × verticalProfile(altitude).
  - In Lawlor and Genetti's version the footprint is a 2D map of curtain splines along the planet, made complex with a 2D fluid simulation of a Kelvin-Helmholtz shear layer to produce the folds and curls. The vertical profile is a physical electron-energy deposition curve (the Lazarev model over the MSIS atmosphere, stored as a table). It rises sharply at about 100 km and decays slowly upward; higher-energy electrons peak lower.
  - alro's version uses a density that glows with distance to a noise-displaced vertical sheet inside a box, with colour lerped by normalised height and a blue-noise start offset (`ttScDc/image.glsl:158-241`).
- **Pure emission:** the integral is a plain sum, C += ε·Δ, with no transmittance. Stars show straight through, and everything is additive onto the night sky.
- **Acceleration.** A 2D distance field to the nearest curtain lets the march stride up to 1000 km through empty sky and slow to 2 km inside curtains. Built by *jump flooding* on the GPU, it gave about 3.5 times overall. And do not branch around samples (§3.4).
- **Display.** Lawlor and Genetti apply gamma to the colour **magnitude** only, colour · |colour|^(1/2.2 − 1), so the hue of thousands of summed dim samples survives the curve.

### 7.3 A physically motivated house recipe

1. **Footprint (2D, around the viewer).** A few long centre lines, each a low-frequency sine-sum polyline drifting slowly. Curtain intensity = exp(−(distance to line / width)²) with width ≈ 0.5 to 1 km at true scale. Add fold distortion with a domain warp or curl noise, and add **rays**: 1D noise *along* the curtain, stretched vertically, scrolling with the ripple speed.
2. **Vertical profile** as a function of altitude in km. A sharp rise from about 90 to 100 km to a peak near 110 to 120 km, then an exponential decay with a scale height of about 30 to 60 km. Its **lower edge height wiggles** along the curtain.
3. **Colour per altitude** (emission lines, linear RGB):
   - a purple-pink fringe below about 100 km, weighted by an "energetic" parameter;
   - 557.7 nm green as the body;
   - 630 nm red above about 200 km, driven by a **time-lagged** footprint (sample the footprint at an earlier time, or blur it), because the red is the slow afterglow.
4. **Integration.** An emission-only march through the 90 to 300 km shell, or a scaled box, with distance-field or polynomial striding and static jitter. Additive over the stars and sky; an optional mirrored second march for water.
5. **Motion vocabulary.** A slow drift of the arc; ripples travelling along curtains; occasional surges that brighten and fold; pulsating patches with a period of about 10 s for "morning".
6. **Exposure.** A "naked eye" mode (desaturated, green-grey, no red build-up) and a "camera" mode (saturated, red integrated over time).

---

## 8. Nebulae and space volumes

### 8.1 What real nebulae are

- **Emission nebulae.** Gas ionised by hot stars glows at specific emission lines: **H-alpha at 656.3 nm** (deep red, usually dominant), **[O III] at 495.9 and 500.7 nm** (teal-green), [S II] at 671.6 and 673.1 nm (red), and H-beta at 486.1 nm.
- **Reflection nebulae.** Dust scatters starlight, preferentially blue, so they look blue.
- **Dark nebulae.** Dense dust absorbs whatever is behind it. These are the lanes and pillars.
- **The "Hubble palette".** A false-colour mapping in which S II is shown as red, H-alpha as green and O III as blue. This is the source of the gold-and-teal look of the famous images.

### 8.2 How shaders build them

- **Model.** Emission plus absorption, with little or no scattering. Use the emissive integration from §1.4: glowing gas adds light, and dust lanes add extinction. Colour comes from line mixes, not from a sky-style phase function.
- **Density.** Ridged or "spiral" textureless noise gives filaments: sums of sin/cos with a small fixed rotation of the domain each octave and frequency growing by about 1.7 (otaviogood's spiral noise, as used by Duke, `MsVXWW/image.glsl:47-91`). Large-scale features come from a second, lower-frequency copy. Taking the absolute value of the combined field gives a distance-like quantity whose small values are the gas.
- **Embedded star as cause.** Add the star's inverse-square light **at every march step** (`MsVXWW/image.glsl:209-214`). The glow and bloom around it then come out of the integral itself instead of a post effect: the house principle of simulating the cause.
- **Bounds and steps.** March only inside a bounding sphere (`:120-131, 188`). Steps grow with distance from the camera and the light (`:249`). Jitter the step (`:243-246`, per frame there; static in the house).
- **Colour by accumulated density** (`:106-118`). Warm and dense to bright and thin, with a centre-to-edge tint. This gives an impression of internal occlusion without computing it.
- **Kali's "Star Nest"** (MIT licence, `XlfGRj`) is a different idea. A fractal fold iteration is sampled at about 20 depth slices, and its "activity" is accumulated with distance fading. It reads as an infinite volumetric star field for very little code.
- **Finish.** HDR accumulation, then a filmic tonemap. A star field behind is multiplied by the nebula's transmittance, so dust lanes hide stars.

---

## 9. Common mistakes and how to see them on screen

| What you see | Cause | Fix |
|---|---|---|
| Concentric contour lines or "tree rings" in fog and clouds | Fixed step positions (aliasing along the ray) | Static per-pixel jitter of the start (IGN or blue noise); fewer, jittered steps beat more unjittered ones |
| Fine grain that **crawls** frame to frame | Per-frame jitter with no temporal accumulation | Static jitter (house law); or add EMA/TAA and animate with the golden ratio |
| Brightness or thickness **changes when you change the step count**; dense regions glow too much | Naive integration ordering | Energy-conserving segment integral (§1.4) |
| Volume looks **too dark** and loses scattered light at low step counts | Transmittance updated before adding light | Same fix |
| Clouds look like **grey smoke** or "dirty cotton"; black cores; only rims lit | No multiple scattering; albedo too low; powder overdone | Octave multi-scatter (a ≤ b), ambient term, albedo ≈ 1, subtle powder or lower edge albedo |
| Clouds **dull and featureless with the sun behind you** | A single strong HG forward lobe (back value about 16 times below isotropic) | Dual-lobe HG with a back lobe, or the Jendersie-d'Eon fit |
| **No silver lining** toward the sun | g too low; clamping before tonemap; LDR buffer | g ≥ 0.6 forward lobe; HDR all the way; no clamp |
| Glow appears on the side **opposite** the sun | Phase cosine sign flipped | μ = dot(viewRayDir, dirToLight); positive g is forward |
| Phase brightness about 10 times off between implementations | Normalisation typo. The HG code printed on the 2017 Nubis slide ends "divide by 4, multiply by π", i.e. ×π/4 instead of ÷4π, a factor of π² ≈ 9.9 | Divide by (4π). Harmless when brightness is an art slider; wrong in a lux-calibrated pipeline |
| Dark-edged clouds even facing the sun; black sun-facing rims | Powder applied without view dependence | Fade powder to 1 as μ → 1 |
| **Banded self-shadows**; stair-stepped shadow terminators inside clouds | Too few light samples in a straight line | Cone sampling with growing spacing, a far sample, LOD; or a precomputed shadow grid or BSM |
| No shadows **between** clouds | Light march too short | A far cone sample (Schneider), a summed-density voxel grid (Nubis Cubed), or a Beer Shadow Map |
| Repeating pattern; identical cauliflowers marching across the sky | Tiling 3D noise visible at large scale | Low-frequency weather or coverage map; rotate and offset octaves; vary type with position |
| Hard flat tops and bottoms; clouds sliced by invisible planes | No height profile, so density is non-zero at the slab boundary | Height gradient going to 0 at both ends; wispy bottoms via remap |
| Clouds look **pasted on** at the horizon; seam against terrain | No aerial perspective applied to clouds | Fog clouds at a representative depth (§4.7) |
| Sunset sky too dark, overly saturated or yellow; zenith not blue at twilight | No multiple scattering in the sky; missing ozone | Multi-scattering LUT; ozone absorption layer |
| Sky smeared or blocky **near the horizon** | Linear latitude mapping in the sky LUT | Non-linear (square-root) latitude mapping |
| Noisy horizon, rings or jittering planet edge at Earth scale | float32 cancellation in ray-sphere tests | Kilometres; h(2R + h); stable quadratic (§3.1) |
| Fog wrong or black looking exactly horizontal | Height-fog formula 0/0 at d_y = 0 | Series fallback F(k) = (1 − e^(−k))/k |
| God rays **in front of** a nearby object; rays flicker as the sun nears the screen edge | Screen-space radial blur limitations | True shadowed in-scatter (march or froxels); or mask Mie in-scatter with the shaft buffer; fade when the sun is off-screen |
| **Ghost trails** behind moving clouds or the camera | Temporal history reused without validation | Neighbourhood clamp; reproject with a representative depth; reset on cuts |
| Colours muddy; additive glows look "flat" | Lighting computed in sRGB; tonemap before compositing | Linear HDR throughout; tonemap last |
| Aurora looks like a **painted backdrop** | Family A screen-space noise | Extrude a footprint (sheets) or march a volume; add rays and colour by altitude |
| Aurora colours in the wrong order (red at the bottom); curtain kilometres thick | No physical reference | Green body, red **top**, purple lower fringe; thin sheet (about 1 km) vs long extent |
| Nebula looks like **uniform fog** | Scattering model with a flat colour; no dust | Emission lines + absorption lanes + embedded star glow |
| "Optimised" branch made it **slower** | Warp divergence | Sample uniformly; measure (Lawlor: skipping was at least 18 % slower) |

---

## 10. Cost and budget cheat-sheet (numbers from the sources)

| Item | Number | Source |
|---|---|---|
| HZD clouds, unoptimised prototype | About 20 ms | Schneider and Vos 2015 |
| HZD clouds with quarter resolution, one-in-16 updates, reprojection | About 2 ms, 20 MB | Schneider and Vos 2015 |
| PS4 baseline + reprojection → adaptive step + LOD → light only non-zero → cull below horizon → depth cull | 22 → 8.1 → 3.34 → 1.81 → 1.2 ms | Schneider 2017 |
| Nubis Evolved, vertical profile clouds | 0.5 to 2.2 ms | Schneider 2022 (via the 2023 slides) |
| Envelope clouds with cone step mapping | 4.2 → 1.3 ms | Schneider 2022 (via the 2023 slides) |
| Nubis Cubed voxel clouds, 960×540, PS5 | 10 → 6.1 → 2.2 ms (ground view) | Schneider 2023 |
| Nubis Cubed, split resolution for 60 Hz | 4 → 2.1 ms | Schneider 2023 |
| Frostbite clouds, Xbox One, worst case | 0.91 ms at 720p, 1.60 ms at 1080p (half res, 16 samples, N = 2 octaves) | Hillaire 2016 |
| Toft et al. on GTX 1080, 1080p | 297.7 ms (full res, 128 steps) → 2.4 ms (quarter res, 8 steps, jitter, TAA) | Toft, Bowles, Zimmermann 2016 |
| Sky and aerial perspective (Hillaire 2020) | About 0.31 ms on a GTX 1080 at 720p; about 1 ms on an iPhone 6s | Hillaire 2020 |
| Bruneton 4D LUT rebuild | About 250 ms (cannot update per frame) | As quoted by Hillaire 2020 |
| Aurora volume (2010-era GPUs, 720p) | 23 to 60 fps; old CPU version 10 minutes per frame | Lawlor and Genetti 2011 |

**The house budget is different.** This host has an AMD display-driver crash history (TDR, timeout detection and recovery). The shader-craft floor sets the rules: small canvases, capped steps, undersample soft fields but never the subject, and never a second GPU context. In practice, every technique above that buys quality with *more samples* should instead buy it with *better samples*: energy-conserving integration, jitter, LUTs, distance fields and analytic integrals.

---

## 11. Reading the corpus (pointers, not code)

All files are under `state/arsenal/shaders/corpus/shaders/`. They are read-only references; re-derive any technique from the mathematics here.

| Shader | Author | Licence (as recorded) | What to look at |
|---|---|---|---|
| `XtGGRt` Auroras | nimitz | CC BY-NC-SA 3.0 | Sheet-stack aurora `:58-89`; triangle-noise footprint `:33-55`; index-ramped jitter `:65`; running average `:73`; reflection branch `:155-165` |
| `ffG3Rc` Chromatic Aurora Curtains | Valdex | Shadertoy default (CC BY-NC-SA 3.0) | Height-band colour weights `:132-146`; 1D ray striation `:70-75`; swirl folds `:113-124` |
| `ttScDc` AURORA | alro | **MIT** | True emissive volume in a box `:202-241`; blue-noise start offset `:223-224, :454`; colour by height `:158-160` |
| `XslGRr` Clouds | Inigo Quilez | **Meta says CC default, but the file header is Quilez's own all-rights-reserved educational licence** (`:1-12`): look, don't touch | Slab bounds `:128-150`; distance-proportional step `:160`; octave LOD `:166`; one-sample directional-derivative light `:175`; front-to-back compositing `:182-184`; dithered start `:153` |
| `XlBSRz` VolumetricIntegration | Sébastien Hillaire | Shadertoy default | The energy-conserving integration side by side with the naive one `:276-300`; the light march for volumetric shadow `:232-250`; the ordering toggle `:81-85` |
| `lslXDr` Atmospheric Scattering Sample | GLtracy | Shadertoy default | Nishita-style nested march `:53-124`; Cornette-Shanks-form Mie phase with negative g and flipped cosine `:22-37, :116-120` |
| `3l23Rh` Protean clouds | nimitz | CC BY-NC-SA 3.0 | Density-driven step `:88`; fog as a difference of integrals `:84-86`; cheap deformed-grid noise `:44-51`; two-sample derivative lighting `:79-80` |
| `MsVXWW` Dusty nebula 4 | Duke | CC BY-NC-SA 3.0 | Sphere-bounded march `:120-131, :188`; spiral noise `:47-91`; star glow per step `:209-214`; density-weighted colour `:106-118` |
| `DtdSz7` STELLAR CLOUDS | alro | **MIT** | Multi-buffer space volume (not studied in depth here) |
| `XlfGRj` Star Nest | Kali | **MIT** | Fractal-fold volumetric star field |
| `MdBfzR`, `MsjfRG` | albertelwin, Mattenii | Shadertoy default | Small 2D aurora fakes (Family A) |

---

## 12. House notes: findings in our own code (assessment only, nothing changed)

1. **The light bed's integration is the naive, non-energy-conserving ordering.**
   - `scripts/aurora-shader.js:256-259` adds `trans * a * lit` with `a = dens·MARCH_DT·SIGMA`, then multiplies `trans` by `exp(-a)`.
   - At full density, a = 0.64, so the slice is about **35 % too bright** relative to the exact integral, and the look depends on `STEPS` and `MARCH_DT`.
   - The exact form replaces the factor `a` with `(1 − exp(−a))`. That value is already half-computed on the next line, so the change is essentially free.
   - For sparse fog nothing changes visibly, since 1 − e^(−a) ≈ a when a is small. Dense banks would dim slightly and stop depending on step size.
   - This is a ceiling change (taste), so it goes through the bench and Daniel. I did not apply it.
2. **The light bed's jitter is static, which is correct by house law, but it is white noise.** `aurora-shader.js:217` uses a `fract(sin(dot))` hash. A static IGN, or a blue-noise tile, gives visibly finer, less clumpy grain at the same 26 steps, with no temporal machinery. This matches Nubis Cubed's "static far away" rule.
3. **A tracked chunk cites an all-rights-reserved source.** `design/vfx-chunks/value-noise-3d.glsl` gives its provenance as "IQ Rainforest 4ttSWf". The corpus records `4ttSWf` as all-rights-reserved. The function itself is textbook lattice value noise with a Hermite fade, so the remedy is a fresh write from the mathematics and a provenance line of "standard value noise, written fresh". (The primitive API below includes `noise_value3`.)
4. **The corpus licence detector misses Inigo Quilez's custom licence.**
   - 33 corpus shaders carry Quilez's "sole copyright owner … cannot use" header.
   - For 31 of them, `meta.json` records "CC-BY-NC-SA-3.0 (Shadertoy default)" with `explicit: false`. `XslGRr` (Clouds) is one; `4ttSWf` is correctly marked all-rights-reserved.
   - The licence line is therefore **stricter** than those meta files say. Detecting the header phrase would fix it.
5. **A verbatim external shader with no recorded author or licence sits in a tracked path.** `design/vfx-sketches/daniil-curtains.frag` says it is Daniil's find, "verbatim", but names no author or licence. It needs a provenance line, or a move under `state/`.
6. **MIT pieces relevant to this topic:** `ttScDc`, `DtdSz7`, `XlfGRj`. They are legally adaptable with their notice kept, but the house rule still says no corpus code in tracked files, so re-derive them.

---

## 13. Primitive API: the house volume library

### 13.1 Conventions (binding on every function below)

- **GLSL ES 3.00 with `precision highp float`.** Highp everywhere; `mediump` bands hashes.
- **Light directions.** `mu = dot(viewRayDir, dirToLight)`. Positive `g` means forward scattering, glowing around the light.
- **Units.** Clouds, fog and local volumes in **metres**. The atmosphere and aurora in **kilometres**, with coefficients converted (×1000) to km⁻¹.
- **Values.** Radiance is linear HDR. Transmittance is `vec3` per channel, or `float` when grey. Density is non-negative. Phase functions return sr⁻¹ and integrate to 1.
- **GLSL has no function pointers.** Marches that need a density callback come as **chunk templates** that require the including sketch to define a hook (`float vol_density(vec3 p)` or `float vol_densityCheap(vec3 p)`), or as macros taking the hook's name. They map to `kind: "source"` in the house chunk header. Pure functions map to `kind: "helper"`.
- **Categories** match the house `//! {"cat": …}` header: `volume`, `phase`, `scatter`, `cloud`, `noise`, `bounds`, `march`, `sampling`, `temporal`, `sky`, `fog`, `rays`, `aurora`, `nebula`.

### 13.2 Transmittance and integration (`volume`)

| Signature | Contract |
|---|---|
| `float vol_transmittance(float sigmaT, float dist)` | Beer-Lambert e^(−σt·d) for a homogeneous segment; returns a value in [0, 1]. |
| `vec3 vol_transmittance3(vec3 sigmaT, float dist)` | Per-channel Beer-Lambert for coloured extinction. |
| `float vol_opacityFactor(float x)` | Returns (1 − e^(−x))/x, stable as x → 0 (series below 1e-3); the shared kernel of every exact segment integral. |
| `struct VolAccum { vec3 L; vec3 T; }` / `VolAccum vol_accumInit()` | Front-to-back accumulator: L = 0, T = 1. |
| `void vol_stepScatter(inout VolAccum a, vec3 sigmaS, vec3 sigmaT, vec3 Lin, float dt)` | Energy-conserving segment integral: adds T·σs·Lin·Δ·F(σtΔ), multiplies T by e^(−σtΔ); brightness independent of dt. |
| `void vol_stepEmit(inout VolAccum a, vec3 emission, vec3 sigmaT, float dt)` | Exact emission-plus-absorption segment; for σt = 0 reduces to T·ε·Δ (aurora, nebula gas, fire). |
| `bool vol_saturated(VolAccum a, float eps)` | True when max(T) < eps; the early-exit test. |
| `vec3 vol_resolve(VolAccum a, vec3 background)` | L + T·background; the composite onto what lies behind. |
| `float vol_beerShadowMap(float d, vec3 bsm)` | Hillaire's BSM lookup: bsm = (front depth, mean σt, max optical depth); returns exp(−min(maxOD, σ̄t·max(0, d − z))). |

### 13.3 Phase functions (`phase`)

| Signature | Contract |
|---|---|
| `float phase_iso()` | 1/(4π). |
| `float phase_rayleigh(float mu)` | 3/(16π)·(1 + μ²); molecules, the blue sky. |
| `float phase_hg(float mu, float g)` | Henyey-Greenstein, normalised; mean cosine = g; g in (−1, 1). |
| `float phase_schlick(float mu, float g)` | Schlick's cheap HG stand-in with k = 1.55g − 0.55g³; error grows for \|g\| near 1. |
| `float phase_cornetteShanks(float mu, float g)` | Cornette-Shanks Mie-like lobe; the aerosol phase for the sky model (g ≈ 0.8). |
| `float phase_draine(float mu, float g, float alpha)` | Draine; alpha = 0 is HG, alpha = 1 is Cornette-Shanks. |
| `float phase_dualHG(float mu, float gFwd, float gBack, float w)` | lerp(HG(gFwd), HG(gBack), w); keeps detail with the sun behind the camera. |
| `float phase_silverLining(float mu, float g, float intensity, float spread)` | Schneider-style max(HG(g), intensity·HG(0.99 − spread)); an art control, **not** energy conserving. |
| `float phase_cloudMie(float mu, float diameterUm)` | Jendersie-d'Eon HG+Draine blend with parameters fitted from the droplet diameter; valid for 5 to 50 µm. |

### 13.4 Multiple scattering and cloud lighting (`scatter`, `cloud`)

| Signature | Contract |
|---|---|
| `vec3 scatter_octaves(float tauLight, float mu, float g, vec3 sigmaS, float a, float b, float c, int N)` | Wrenninge octave sum Σ aⁿ·σs·e^(−bⁿτ)·HG(μ, cⁿg); requires a ≤ b; N is 1 to 3; returns σs-weighted in-scatter per unit light. |
| `float scatter_twoBeer(float tau, float k2, float w2)` | max(e^(−τ), w2·e^(−k2·τ)); cheap multi-scatter (Schneider 2017 used about w2 = 0.7, k2 = 0.25). |
| `float cloud_powder(float tau, float k)` | In-scatter probability 1 − e^(−kτ) (k ≈ 2); the dark-edge term. |
| `float cloud_beerPowder(float tau)` | 2·e^(−τ)·(1 − e^(−2τ)); peak about 0.77 at τ ≈ 0.55. |
| `float cloud_powderView(float powder, float mu)` | Fades the powder term to 1 as you look toward the light; use it to apply powder. |
| `float cloud_inScatterProb(float lowDensity, float h01)` | Nubis 2017-style depth probability × vertical probability; darkens edges and bottoms; returns [0, 1]. |
| `float cloud_ambientProfile(float h01, float groundBias)` | Ambient weight ramp bottom to top, floor at groundBias for ground bounce. |
| `float cloud_ambientFromProfile(float profile, float skyOcclusionTau)` | (1 − profile)^0.5 · e^(−skyOcclusionTau); Nubis-style ambient with optional overhead occlusion. |
| `float cloud_edgeAlbedo(float density, float lo, float hi, float minAlbedo)` | Hillaire's physically based alternative to powder: lowers albedo where density is low. |

### 13.5 Density shaping (`cloud`, `noise`)

| Signature | Contract |
|---|---|
| `float remap(float v, float a, float b, float c, float d)` | Linear refit of [a, b] onto [c, d], **unclamped**; the Nubis carving tool. |
| `float remapSat(float v, float a, float b, float c, float d)` | Same, clamped to [min(c, d), max(c, d)]. |
| `float cloud_heightProfile(float h01, vec4 ramps)` | Rise over [ramps.x, ramps.y], fall over [ramps.z, ramps.w]; 0 at both ends. |
| `float cloud_typeProfile(float h01, float type)` | Blends stratus (0), stratocumulus (0.5) and cumulus (1) height profiles by type. |
| `float cloud_coverage(float base, float coverage)` | Coverage threshold remap; coverage 1 = overcast, 0 = clear; clouds inflate smoothly as coverage rises. |
| `float cloud_erode(float base, float detail, float strength)` | Remap-erodes edges only; preserves the dense core; returns 0 where base is 0. |
| `float cloud_profileErode(float profile, float noise)` | saturate(noise − (1 − profile)); Nubis Evolved-style up-rez of a coarse profile. |
| `vec3 cloud_windOffset(vec3 p, vec3 wind, float time, float h01, float skew)` | Advects the sample position and skews it with height. |
| `float cloud_anvil(float coverage, float h01, float anvilBias)` | Spreads coverage near the top of the layer (power < 1); anvil tops. |
| `float noise_value3(vec3 p)` | Lattice value noise with Hermite fade in [0, 1]; textureless (replaces the chunk with the questionable provenance). |
| `float noise_gradient3(vec3 p)` | Perlin-style gradient noise in about [−1, 1]. |
| `float noise_worley3(vec3 p, float period)` | Tileable cellular F1 distance, returned inverted (1 − F1) as billows in [0, 1]. |
| `float noise_perlinWorley(float perlin01, float worleyInv)` | Dilates Perlin by inverted Worley; connected masses with billows. |
| `float noise_fbm3(vec3 p, int octaves, float lacunarity, float gain)` | fBm with a fixed rotation between octaves; octaves may be lowered with distance for LOD. |
| `float noise_ridged3(vec3 p, int octaves)` | 1 − \|noise\| octaves; filaments for nebulae and lightning-lit edges. |
| `vec3 noise_curl3(vec3 p)` | Divergence-free curl of a noise potential; turbulent distortion without sources or sinks. |
| `float noise_fold2(float n01, float sharpness)` | Twice-folded noise: fakes one octave higher frequency without another fetch. |
| `float noise_spiral3(vec3 p, int octaves)` | Textureless sin/cos sum with a per-octave domain rotation; cheap nebula and cloud filaments. |
| `float dens_heightExp(float y, float rho0, float scaleH)` | ρ0·e^(−y/H); fog, haze and atmosphere layers. |
| `float dens_fromSDF(float sdf, float softness)` | clamp(−sdf/softness, 0, 1); turns any distance field into a volume. |

### 13.6 Bounds and marching (`bounds`, `march`)

| Signature | Contract |
|---|---|
| `vec2 ray_slab(float oy, float dy, float y0, float y1)` | Entry and exit t of a horizontal slab; returns (tNear, tFar) with tFar < tNear meaning a miss. |
| `vec2 ray_sphere(vec3 o, vec3 d, vec3 c, float r)` | Numerically stable ray-sphere (stable quadratic); returns (tNear, tFar) or a miss. |
| `vec2 ray_sphereAlt(float r0, float mu0, float R)` | Ray-sphere from radius and zenith cosine using h(2R + h); precise at planet scale (km). |
| `vec2 ray_shell(vec3 o, vec3 d, vec3 c, float rIn, float rOut)` | First segment of a ray inside a spherical shell (cloud layer or atmosphere); handles a camera inside, below or above. |
| `vec2 ray_box(vec3 o, vec3 d, vec3 bmin, vec3 bmax)` | Slab-method box intersection. |
| `float march_stepDistance(float t, float dtMin, float k)` | max(dtMin, k·t); matches pixel footprint growth. |
| `float march_stepOptical(float sigmaT, float tauTarget, float dtMin, float dtMax)` | Limits each step's optical depth to tauTarget (≈ 0.1 to 0.3). |
| `float march_stepSDF(float sdf, float adaptive)` | max(sdf, adaptive); leaps through empty space, adaptive inside (Nubis Cubed). |
| `float march_stepPoly(int i, float base, float scale, float power)` | Layer i at base + scale·i^power; polynomial stride for aurora sheets. |
| *Template* `VOL_MARCH_CHEAP_EXPENSIVE(densCheap, densFull, …)` | Big cheap steps until density > 0, one step back, full detail until N empty samples; requires both hooks. |
| *Template* `VOL_LIGHT_CONE(densFn, p, toLight, n, spacing, farDist)` | n cone samples toward the light with growing spacing plus one far sample; returns the light's optical depth. |
| `float light_dirDerivative(float densHere, float densTowardLight, float scale)` | One-sample lighting proxy clamp((ρ(p) − ρ(p + εL))/scale); non-physical, very cheap. |

### 13.7 Sampling and temporal (`sampling`, `temporal`)

| Signature | Contract |
|---|---|
| `float jitter_ign(vec2 pixel)` | Interleaved gradient noise in [0, 1); static per pixel; the house default jitter. |
| `float jitter_ignFrame(vec2 pixel, int frame)` | IGN shifted 5.588238 px per frame; **only** with temporal accumulation. |
| `float jitter_blue(sampler2D tile, ivec2 pixel)` | Static blue-noise value from a tiled texture. |
| `float jitter_blueFrame(sampler2D tile, ivec2 pixel, int frame)` | fract(blue + frame·0.6180339887); **only** with temporal accumulation. |
| `float march_jitterStart(float tStart, float dt, float u)` | tStart + u·dt; turns banding into noise. |
| `vec2 temporal_reprojectDir(vec3 worldDir, mat4 prevViewProj)` | Previous-frame UV of an infinitely distant direction (sky, far clouds). |
| `vec2 temporal_reprojectPos(vec3 worldPos, mat4 prevViewProj)` | Previous-frame UV of a world point (near volumes, with representative depth). |
| `void temporal_depthAccum(inout vec2 acc, float T, float t, float density)` | Accumulates Σ T·t and Σ T over non-empty samples; the mean depth for reprojection and aerial perspective. |
| `vec4 temporal_blend(vec4 history, vec4 current, vec4 nbMin, vec4 nbMax, float alpha)` | Neighbourhood-clamps history, then EMA lerp(history, current, alpha); effective samples about 1/alpha. |
| `bool temporal_bayerOwns(ivec2 pixel, int frame)` | True when this pixel is the one of 16 in its 4×4 block refreshed this frame (Schneider-style amortisation). |

### 13.8 Sky and atmosphere (`sky`)

| Signature | Contract |
|---|---|
| `struct Atmos { float Rg, Rt; vec3 rayS; float rayH; float mieS, mieA, mieH, mieG; vec3 ozA; float ozPeak, ozHalfWidth; vec3 groundAlbedo; }` | Planet atmosphere description (km, km⁻¹). |
| `Atmos atmos_earth()` | Hillaire 2020 Earth defaults (6360/6460 km; Rayleigh 5.802/13.558/33.1 e-3 km⁻¹, H 8 km; Mie 3.996 e-3 scattering + 4.40 e-3 absorption km⁻¹, H 1.2 km, g 0.8; ozone tent 25 ± 15 km). |
| `void atmos_medium(Atmos A, float altKm, out vec3 rayleighS, out float mieS, out vec3 sigmaT)` | Per-altitude coefficients: exponential Rayleigh and Mie, tent ozone. |
| `vec3 atmos_transmittance(Atmos A, float r, float muZenith, int steps)` | Reference march of the sun's transmittance to the top of the atmosphere (fills the transmittance LUT). |
| `vec2 atmos_transmittanceUV(Atmos A, float r, float mu)` / inverse | LUT parameterisation; precision concentrated near the horizon. |
| `vec2 atmos_skyViewUV(float latitude, float longitude)` / inverse | Non-linear latitude mapping v = 0.5 + 0.5·sign(l)·√(\|l\|/(π/2)). |
| `vec3 atmos_singleScatter(Atmos A, vec3 o, vec3 d, vec3 toSun, float tMax, int steps)` | Nishita-style reference with Rayleigh + Mie phases; uses the transmittance LUT or a light march. |
| `vec3 atmos_multiScatterPsi(vec3 L2, vec3 fms)` | Ψ_ms = L₂/(1 − f_ms); the closed form of the infinite scattering series. |
| `vec3 atmos_apply(vec3 surface, vec3 inscatter, vec3 transmittance)` | Aerial perspective: surface·T + inscatter. |
| `vec3 sky_sunDisk(vec3 rd, vec3 toSun, float angRadius, vec3 luminance)` | Sun disk with smooth limb darkening; composited after the sky LUT. |

### 13.9 Fog and rays (`fog`, `rays`)

| Signature | Contract |
|---|---|
| `vec3 fog_exp(vec3 col, vec3 fogCol, float dist, float b)` | Classic exponential fog. |
| `vec3 fog_split(vec3 col, vec3 inCol, vec3 bExt, vec3 bIn, float dist)` | Separate per-channel extinction and in-scatter; independent colour and haze. |
| `vec3 fog_sunTint(vec3 rd, vec3 toSun, vec3 awayCol, vec3 towardCol, float sharp)` | Fog colour warming toward the sun; Mie-glow stand-in. |
| `float fog_heightTau(vec3 o, vec3 d, float t, float a, float b)` | Analytic optical depth of a·e^(−b·y) along a ray; stable when d.y ≈ 0. |
| `vec3 rays_radial(sampler2D occlusion, vec2 uv, vec2 sunUV, int n, float density, float weight, float decay, float exposure, float u)` | Mitchell-style screen-space shafts with a jittered first sample; know its failure modes (§5.3). |
| `float rays_litFraction(…)` *template* | Fraction of jittered march steps that see the light; the true-god-ray mask. |

### 13.10 Aurora and nebula (`aurora`, `nebula`)

| Signature | Contract |
|---|---|
| `float aurora_profile(float altKm, float lowerEdgeKm, float scaleHKm)` | Emission vs altitude: sharp rise at the lower edge, exponential decay above. |
| `vec3 aurora_lineColor(float altKm, float energetic)` | Linear RGB of the emission mix by altitude: purple fringe low (×energetic), 557.7 nm green body, 630 nm red high. |
| `float aurora_footprint(vec2 xzKm, float time, float foldAmt)` | 2D curtain intensity: Gaussian around drifting folded centre lines; returns [0, 1]. |
| `float aurora_rays(float alongKm, float time)` | Field-aligned striation: 1D noise along the curtain, scrolling; multiplies the footprint. |
| `float aurora_redLag(vec2 xzKm, float time, float lagSec)` | Time-lagged and blurred footprint for the slow 630 nm afterglow. |
| `vec3 aurora_sheets(vec3 o, vec3 rd, int layers, float stridePow, float jitter)` | Family B: footprint sampled on polynomially spaced horizontal planes, running-averaged, colour by layer height. |
| `vec3 aurora_volume(vec3 o, vec3 rd, float tNear, float tFar, float jitter)` | Family C: emission-only march of footprint × profile × line colour, with a distance-field stride where available. |
| `vec3 display_hueSafeGamma(vec3 c, float gamma)` | Gamma on the magnitude only (c·\|c\|^(1/γ − 1)); keeps the hue of many summed dim emitters. |
| `vec3 nebula_lines(float hAlpha, float oIII, float sII, int palette)` | Emission-line mix: natural (H-alpha red, O III teal) or Hubble SHO false colour. |
| `vec3 nebula_starGlow(vec3 p, vec3 starPos, vec3 starCol, float k)` | Inverse-square light added per march step; the glow comes out of the integral. |
| `void nebula_step(inout VolAccum a, vec3 p, float gasDensity, float dustDensity, vec3 lineColor, float dt)` | One emission + absorption step: gas emits, dust extinguishes. |

---

## 14. A learning path (ten sketches for the bench)

Each step changes one thing. Render through the open tab per the shader-craft loop, with a number beside each image.

1. **A uniform fog slab** over a checkerboard. Compare naive and exact integration at 8 and 64 steps. The naive one changes; the exact one doesn't.
2. **Add banding, then kill it.** First no jitter, then static white noise, then static IGN. Watch the tree rings turn into grain, then finer grain.
3. **One point light in fog with HG.** Sweep g from −0.5 to 0.95 and watch the halo grow and the back side dim. Flip the cosine sign once to learn the trap.
4. **A noise cloud in a slab.** Height profile, coverage remap, detail erosion. Sweep coverage to confirm the polarity.
5. **Self-shadowing.** First a straight 6-sample light march (banded), then cone sampling with a far sample.
6. **Multiple scattering.** N = 1, 2 and 3 octaves (a = b = c = 0.5). Watch the core brighten and the cloud stop looking like smoke.
7. **Powder.** Add it, then add the view fade, then try edge albedo instead. Compare against the photographs in Schneider's 2015 talk.
8. **Sky.** A brute-force single-scattering sky (Rayleigh + Mie + ozone, km units) at low resolution. Sweep the sun from noon to sunset, then add a cheap multi-scatter term and compare twilight.
9. **Aurora.** First a sheet stack (Family B), then a true emissive volume (Family C) with colour by altitude and a red lag. Fly the camera under it to see the corona converge.
10. **Nebula.** Emission + dust absorption + embedded star glow inside a bounding sphere, finished with the house tonemap.

---

## 15. Sources

**Primary: clouds**
- Schneider and Vos, "The Real-time Volumetric Cloudscapes of Horizon: Zero Dawn", SIGGRAPH 2015 Advances. https://advances.realtimerendering.com/s2015/index.html. The original Nubis prototype: Perlin-Worley noise, height presets, Beer + HG + powder, 64 to 128 steps, cone light samples, one-in-16 reprojection, 2 ms.
- Schneider, "Nubis: Authoring Real-Time Volumetric Cloudscapes with the Decima Engine", SIGGRAPH 2017 Advances. https://advances.realtimerendering.com/s2017/Nubis%20-%20Authoring%20Realtime%20Volumetric%20Cloudscapes%20with%20the%20Decima%20Engine%20-%20Final%20.pdf. Remap modelling, weather maps, silver-lining max, two-Beer multi-scatter, in-scatter probability, PS4 optimisation timings, Mie-masked god rays.
- Schneider, "Nubis³: Methods (and madness) to model and render immersive real-time voxel-based clouds", SIGGRAPH 2023 Advances. https://d3d3g8mu99pzk9.cloudfront.net/AndrewSchneider/Nubis%20Cubed.pdf. NVDF voxel clouds, up-rez, SDF + adaptive + jitter stepping, precomputed light grid, split resolution; also recaps Nubis Evolved (2022).
- Guerrilla Games, Nubis³ page. https://www.guerrilla-games.com/read/nubis-cubed. Index of the 2023 talk and its downloads.
- Andrew Schneider's publications list. https://sites.google.com/view/vonschneidz/publications. All Nubis talks, including the 2018 "Nubis in a Nutshell" distillation.
- Toft, Bowles and Zimmermann, "Optimisations for Real-Time Volumetric Cloudscapes", 2016. https://arxiv.org/pdf/1609.05344. Analytic step integration plus 8 jittered steps plus TAA, with measured timings and the jitter cache-miss cost.

**Primary: sky, atmosphere, participating media**
- Hillaire, "Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite", SIGGRAPH 2016 PBS course notes. https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf. Participating-media primer, phase functions, ozone, energy-conserving integration, dual-lobe phase, octave multi-scatter, cloud and atmosphere interactions, Xbox One timings.
- Hillaire, "A Scalable and Production Ready Sky and Atmosphere Rendering Technique", EGSR 2020. https://sebh.github.io/publications/egsr2020.pdf. Transmittance, multi-scattering, sky-view and aerial-perspective LUTs, the L₂/(1 − f_ms) derivation, Earth constants, timings.
- Hillaire, "Physically Based and Scalable Atmospheres in Unreal Engine", SIGGRAPH 2020 PBS slides. https://blog.selfshadow.com/publications/s2020-shading-course/hillaire/s2020_pbs_hillaire_slides.pdf. Cloud multi-scatter choices, edge-albedo instead of powder, Beer Shadow Maps, linear-shadow integration, caveats.
- A readable mirror of the EGSR 2020 paper text. https://www.readkong.com/page/a-scalable-and-production-ready-sky-and-atmosphere-3211109. Used to read the paper's constants and equations when the primary PDF exceeded fetch limits.
- Hillaire's publication list. https://sebh.github.io/publications/. Index including the 2015 Frostbite unified volumetrics talk.
- Hillaire, UnrealEngineSkyAtmosphere (MIT). https://github.com/sebh/UnrealEngineSkyAtmosphere. Reference implementation and path tracer for the 2020 sky.
- Hillaire, TileableVolumeNoise (MIT). https://github.com/sebh/TileableVolumeNoise. Generator for tileable Perlin-Worley and Worley cloud noise.
- Bruneton, Precomputed Atmospheric Scattering, 2017 rewrite (BSD). https://ebruneton.github.io/precomputed_atmospheric_scattering/. The documented 4D-LUT reference with ozone and spectral handling.
- Bruneton's repository. https://github.com/ebruneton/precomputed_atmospheric_scattering. Source and licence of the above.
- Jendersie and d'Eon, "An Approximate Mie Scattering Function for Fog and Cloud Rendering", SIGGRAPH 2023 Talks. https://research.nvidia.com/labs/rtr/approximate-mie/publications/approximate-mie.pdf. The HG + Draine blend with diameter-fitted parameters.
- NVIDIA project page for the same talk. https://research.nvidia.com/labs/rtr/approximate-mie/. Supplemental material and code links.

**Fog, god rays, sampling, temporal**
- Inigo Quilez, "Better fog". https://iquilezles.org/articles/fog/. Exponential fog, the extinction/in-scatter split, sun-tinted fog, and analytic height fog with the horizontal-ray edge case.
- Kenny Mitchell, "Volumetric Light Scattering as a Post-Process", GPU Gems 3, chapter 13. https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process. Screen-space radial god rays, their parameters and failure modes.
- Alan Wolfe, "Ray Marching Fog With Blue Noise", 2020. https://blog.demofox.org/2020/05/10/ray-marching-fog-with-blue-noise/. No noise vs white vs blue jitter at 16 steps; golden-ratio animation; IGN's per-frame shift.
- Alan Wolfe, "Animating Noise For Integration Over Time", 2017. https://blog.demofox.org/2017/10/31/animating-noise-for-integration-over-time/. Why and how to animate blue noise for temporal accumulation.
- Jorge Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", 2014. https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/. Origin of Interleaved Gradient Noise.
- Playdead, temporal reprojection anti-aliasing for *Inside* (MIT). https://github.com/playdeadgames/temporal. Open TAA implementation used by Toft et al.; neighbourhood clamping credited to Karis.
- Jean-Philippe Grenier, "Volumetric Clouds", 2016. https://www.jpgrenier.org/clouds.html. An independent implementation: Bayer-matrix start offsets, a 16-frame Halton reconstruction, absorption-weighted motion vectors.

**Aurora and nebulae**
- Lawlor and Genetti, "Interactive Volume Rendering Aurora on the GPU", Journal of WSCG, 2011. https://www.cs.uaf.edu/~olawlor/papers/2010/aurora/lawlor_aurora_2010.pdf. Footprint × deposition factorisation, 1 km sheets, fluid-simulated folds, distance-field stepping, the branch-divergence finding, hue-preserving gamma.
- Lawlor and Genetti talk slides, 2011. https://www.cs.uaf.edu/~olawlor/2011/aurora_WSCG_2011.pdf. The compounding speedups and future work (red slow-glow).
- NOAA Space Weather Prediction Center, "Aurora Tutorial". https://www.spaceweather.gov/content/aurora-tutorial. What aurora looks like: arcs, rays, ripples, surges, pulsating patches, colours by altitude.
- Toni Sagristà, "Rendering volume aurorae and nebulae", 2024. https://tonisagrista.com/blog/2024/rendering-aurorae-nebulae/. A modern Lawlor-style implementation (cubemap footprint plus SDF), emission-only, and the inside-volume ghosting pitfall.
- Sky and Telescope, "Palettes of the Deep Sky". https://skyandtelescope.org/astronomy-resources/palettes-of-the-deep-sky/. Emission-line colours and the Hubble false-colour palette.

**Tutorials (for onboarding)**
- Maxime Heckel, "Real-time dreamy Cloudscapes with Volumetric Raymarching". https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/. SDF-shaped clouds, directional-derivative light, blue-noise jitter, half-resolution with upscaling.
- Maxime Heckel, "On Rendering the Sky, Sunsets, and Planets". https://blog.maximeheckel.com/posts/on-rendering-the-sky-sunsets-and-planets/. An approachable walk through atmospheric scattering.
- Chris Wallis, "Volumetric Rendering Part 2", 2020. https://wallisc.github.io/rendering/2020/05/02/Volumetric-Rendering-Part-2.html. A beginner-friendly Beer-Lambert light march and volume shadows on opaque objects.
- Sean O'Neil, "Accurate Atmospheric Scattering", GPU Gems 2, chapter 16. https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-16-accurate-atmospheric-scattering. The classic shader derivation of Nishita single scattering.

**Background references (cited, not fetched for this report)**
- Henyey and Greenstein, "Diffuse radiation in the Galaxy", Astrophysical Journal 93, 1941. https://ui.adsabs.harvard.edu/abs/1941ApJ....93...70H/abstract. Origin of the HG phase function.
- Fong, Wrenninge, Kulla and Habel, "Production Volume Rendering", SIGGRAPH 2017 course. https://graphics.pixar.com/library/ProductionVolumeRendering/. Film-grade volume rendering: delta and ratio tracking, the ground truth that real time approximates.
- Pharr, Jakob and Humphreys, Physically Based Rendering, 4th edition, "Volume Scattering". https://pbr-book.org/4ed/Volume_Scattering. Rigorous treatment of media, phase functions and the transport equation.
- Christoph Peters, "Free blue noise textures". https://momentsingraphics.de/BlueNoise.html. Ready-made blue-noise tiles for jitter.

Also named in the text but not linked: Wrenninge, Kulla and Lundqvist ("Oz", 2013, octave multi-scatter), Bouthors et al. (2008, cloud phase and collectors), Wronski (2014, froxel fog), Karis (2014, TAA neighbourhood clamp), Bauer (2019, Red Dead Redemption 2 atmospherics), Engelhardt and Dachsbacher (2010, epipolar sampling), Nishita et al. (1993), Preetham, Shirley and Smits (1999), Hosek and Wilkie (2012), Cornette and Shanks (1992), Draine (2003), Worley (1996), Bridson et al. (2007, curl noise), Baranoski et al. (2000, aurora), Hess, Koepke and Schult (1998, cloud optical properties).
