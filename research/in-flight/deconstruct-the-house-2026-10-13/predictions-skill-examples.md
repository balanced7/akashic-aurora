<!-- Provenance: a verbatim copy of the prediction register for the worked examples in the deconstruct skill
     (.claude/skills/deconstruct/references/worked-examples.md) and its self-checks, moved out of the session scratch
     folder (scratchpad/deconstruct/predictions.md, written 2026-10-13 10:15-10:29 EDT) on 2026-10-13 after review
     defect D9. Nothing below this comment was edited. Results are recorded in the worked examples themselves. -->

# Predictions registered BEFORE each test (deconstruct skill authoring, 2026-10-13)

## Website: akashiclabs.io (our own public site)
Source read first: E:\akashiclabs-site\astro.config.mjs (Astro, site https://akashiclabs.io),
.github/workflows/deploy.yml (GitHub Pages via actions/deploy-pages@v4), public/CNAME = akashiclabs.io,
src/pages/index.astro (h1 "Akashic Labs", h2 "Forest Walks", walks from a content collection).
- W1 (C, the repo's claim "deploy to GitHub Pages"): response header `server: GitHub.com` (no CDN in front). Could fail: Cloudflare or another proxy in front.
- W2 (C, "static site"): the raw HTML, with no JavaScript run, already contains "Forest Walks" and at least 3 walk links. Could fail: client-side rendering.
  Negative control: a string that is not on the page returns 0 matches.
- W3 (G, my belief about Pages defaults): `cache-control: max-age=600`.
- W4 (C, HTTPS): http:// answers 301 to https://.

## API: GitHub REST, GET /repos/balanced7/akashic-aurora, unauthenticated, body discarded
- A1: `x-ratelimit-limit: 60`.
- A2: the response carries an `etag`; repeating with If-None-Match returns 304.
- A3: x-ratelimit-remaining drops by exactly 1 between two plain 200 calls. Could fail for the wrong reason: another process on this IP calling the API.
- A4 (deliberately the "first principle" many people hold): a 304 does NOT spend rate limit for an unauthenticated caller. I am unsure; GitHub's docs, as I remember them, scope the free 304 to authorized requests.

## Financial model (pure arithmetic, py)
- F1: Gordon terminal value, next-year FCF 100, r 9%, g 3% -> 4%: value rises MORE than 15%.
- F2: r 9% -> 10% at g 3% moves value LESS (in size) than F1's move.
- F3: 5-year explicit forecast (FCF 100 growing 5%), terminal growth 3% after, r 9%: terminal value is MORE than 60% of total present value.

## Game economy (Archero, public sources via the reverse-engineering skill's games reference)
- G1 (identity, cannot fail): 3:1 fusion over 5 steps needs 243 base copies.
- G2: DPS x EHP: +53% DPS for -20% HP = x1.224 (take); +50% DPS for -40% HP = x0.90 (refuse).
- G3: two "+1 arrow, -25% damage each" picks: +69% if the penalties multiply, +50% if they add.

## Aurora (a principle in nature)
- AU1: the source will put O(1D) (630.0 nm) lifetime at roughly 100+ s and O(1S) (557.7 nm) under 1 s.
- AU2: red emission altitude above ~200 km, green ~100-150 km in a published source.
- AU3: the 630.0/636.4 nm intensity ratio is about 3 (same upper level), computable from published A-values.

## Self-checks on the written skill (registered before running)
- S1 (G): every repo path cited in SKILL.md and references/teardown-card.md exists.
- S2 (G): the frontmatter parses; name == deconstruct; description <= 1024 characters. Could fail: my description is long.
- S3 (G): every house number quoted in SKILL.md appears in the-house-deconstructed.md.
- S4 (C, brief rule): reverse-engineering/SKILL.md still 09:32:21 and the v1 card still 09:16:56 (I edited neither).
