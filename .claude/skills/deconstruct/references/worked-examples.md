# Worked mini-examples: five targets, eight rows each (compressed)

Moved here from `../SKILL.md` on 2026-10-13 so the skill that always loads stays short. Each example shows one
kind of target. All checks ran on 2026-10-13 between about 10:15 and 10:25 EDT. Each prediction was registered
before its test; the register is kept with the calibration record, in
`research/in-flight/deconstruct-the-house-2026-10-13/predictions-skill-examples.md`.

## A website: akashiclabs.io (ours)

The site's code is not in this repo. It lives in its own repository, checked out locally at `E:\akashiclabs-site`;
the paths below that start with `akashiclabs-site/` are relative to that checkout.

| row | entry |
|---|---|
| 1 Purpose | Daniel's public lab site and its Forest Walks field notes **[observed** `akashiclabs-site/src/pages/index.astro:15-17`**]** |
| 2 Observables | `Server: GitHub.com`, `Cache-Control: max-age=600`, `Via: 1.1 varnish`, `X-Cache: MISS`; `http://` returns 301 to `https://`; the raw HTML holds "Forest Walks" once and 3 walk links; `Last-Modified: 2026-09-02 02:30:53 GMT` **[observed, curl]** |
| 3 Mechanism | Astro, a static site generator, builds the HTML from Markdown at build time. A GitHub Action deploys it to GitHub Pages, which serves it through a Varnish cache **[observed** in the site's repo: `akashiclabs-site/astro.config.mjs:6`, `akashiclabs-site/.github/workflows/deploy.yml:1-33`, `akashiclabs-site/public/CNAME`; the cache from the `Via` header**]** |
| Loops | Commit, build, deploy, visitor: **C** for publishing. Whether anything about readers flows back: **unknown** (I read 4 files, not the whole repo) |
| 4 Principles | HTTP is stateless request and response (**LAW**, RFC 9110). Caching is governed by headers (**LAW**, RFC 9111), so a change can take up to 10 minutes to reach a cached reader **[inferred** from `max-age=600`**]**. The content exists before any JavaScript runs (**DESIGN CHOICE**: static generation) |
| 5 Capabilities | Node 22 and Astro, a GitHub repository with Pages, control of the domain's DNS |
| 6 Steps | Domain and DNS, then the repository, the Astro scaffold, the content, the Action, Pages with the custom domain, and HTTPS enforcement. Critical path: DNS, then Pages, then HTTPS |
| 7 Invariants | The live page matches the newest commit. The newest commit, `06d990e`, is dated 02:30:19 GMT and `main` equals `origin/main`, so the live page is that commit's build **[inferred]**. How Pages sets `Last-Modified` only 34 seconds later is **unknown** |
| 8 Verification | W1 (C) `Server: GitHub.com`: **held**, but my side note "no CDN in front" **failed**, because `Via: 1.1 varnish` shows a cache layer the repo never mentions. W2 (C) the content is in the raw HTML: **held** ("Forest Walks" once, 3 walk links; the negative control returned 0). W3 (G) `max-age=600`: **held**. W4 (C) http redirects with a 301: **held** |

Trap seen: **the map is not the territory.** The site's repo is a complete map of what we built, and it is
silent about the cache layer that every reader goes through.

## An API: GitHub's public REST API

| row | entry |
|---|---|
| 1 Purpose | Programmatic access to GitHub data. For GitHub, serving it means rationing a shared server |
| 2 Observables | `X-RateLimit-Limit: 60`; Remaining 59, 58, 57, 56 and Used 1, 2, 3, 4 over four calls; `ETag: W/"d862…"`; `Cache-Control: public, max-age=60, s-maxage=60`; a 304 on `If-None-Match` **[observed, curl, body discarded]** |
| 3 Mechanism | A budget per caller, decremented on every request and reported back in headers. An ETag (a fingerprint of the response) lets a client ask "has this changed?" **[inferred** from Row 2**]** |
| Loops | Request, then budget spent, then a header reports what remains, then the client backs off: **P**. The API closes its half, and the reader is our client, which has to read the header |
| 4 Principles | GET is safe and idempotent: repeating it changes nothing (**LAW** in the standard's sense, RFC 9110). Conditional requests return 304 when nothing changed (**LAW**, RFC 9110). "A 304 is free": **SCOPED**, see A4 |
| 5 Capabilities | An HTTP client. A token raises the limit (documented; not tested here, so **unknown**) |
| 6 Steps | Read the docs, then authentication, pagination, conditional requests, back-off on Remaining, and retry on 403 and 429 |
| 7 Invariants | Used + Remaining = Limit: **held** 4 of 4 (1+59, 2+58, 3+57, 4+56). From outside, a break looks like a 403 or 429 with Remaining at 0 |
| 8 Verification | A1 limit 60: **held**. A2 an ETag, then a 304: **held**. A3 one unit per 200: **held** (this could have failed for the wrong reason if another process on the same address had called the API). **A4 a 304 costs nothing: FAILED** (58 to 57) |

Trap seen: **a false first principle.** "Conditional requests are free" is true at some doors and was
stated as true everywhere. The Great Sage report for this example is the voice example in `../SKILL.md`.

## A financial model: identities versus bets

Target: a generic discounted-cash-flow (DCF) model. It is a teaching template, not any company, and not
advice.

- **Mechanism.** Forecast free cash flow (FCF, the cash left after running and maintaining the business).
  Divide each year's FCF by (1 + r)^t, where r is the discount rate. Add a terminal value for every year
  after the forecast, using the Gordon formula FCF × (1 + g) / (r − g), where g is the growth rate forever.
  Then sum everything.
- **Row 4 splits every cell into two kinds.** **Identities** are true by construction (**LAW**): assets =
  liabilities + equity; the change in cash equals the sum of the cash-flow statement; the present value is
  the discounted sum of the given inputs; and a geometric series converges only when g < r. **Bets** are
  guesses about the future: growth, margins, the discount rate and the terminal assumptions. Each bet is
  **CONTINGENT** and carries its source and date. The identities are the gears and the bets are the fuel.
- **Row 7 invariants.** The balance sheet balances in every period *without a plug* (a number forced in to
  make it balance). A check cell that reads TRUE because a plug forces it is **quiet green**. g < r always
  holds. A circular reference, such as interest on average debt, either converges or it does not; find out
  which.
- **Row 8, run with py arithmetic:**

| id | dir | prediction | result | verdict |
|---|---|---|---|---|
| F1 | G | Next-year FCF 100 and r = 9%: raising g from 3% to 4% raises the terminal value by more than 15% | 1,666.7 to 2,000.0, **+20.0%** | held |
| F2 | G | Raising r from 9% to 10% moves it less than F1 does | **−14.3%** | held |
| F3 | G | A five-year forecast (FCF 100, growing 5%) plus a terminal value: the terminal value is more than 60% of the total | **76.1%**. In this model g from 3% to 4% gives +16.1%, and r from 9% to 10% gives −14.4% | held |
| F4 | G | Read backwards: a price of 2,000 on next-year FCF of 100 at r = 9% implies g = 4% | 4.0% (an identity, so it could not fail; labelled as such) | identity |

**Analysis.** Three quarters of this model's value is a bet about year six onward. So the honest output is
a range, together with the bets that move it most (a sensitivity or "tornado" table), not a single number.
**Reverse engineering a price** means solving for the bet the price implies (F4). That is this skill
applied to a market.

## A principle in nature: the aurora's red crown above its green body

| row | entry |
|---|---|
| 1 Purpose | The question: why is a tall aurora red on top and green below, when both colours come from the same atom? |
| 2 Observables | Green at 557.7 nm, mostly at 100 to 150 km; red at 630.0 nm (with 636.4 nm), mostly at 200 to 300 km **[observed in sources, read 2026-10-13 through a web-search summary, not the full papers:** Taguchi et al., JGR 2017, doi 10.1002/2016JA023115; arXiv 2112.09432; SWSC 2025 synthetic auroral spectra**]** |
| 3 Mechanism | Electrons falling along magnetic field lines excite atomic oxygen. The ¹S state drops to ¹D and emits green in about 0.7 s. The ¹D state drops to the ground state and emits red, but only after about 110 s on average. Every collision before then steals the energy (called quenching) **[observed in sources; the chain is inferred]** |
| 4 Principles | Energy levels are quantised (**LAW**). "Forbidden" transitions have long lifetimes (**LAW**, selection rules). Air density falls roughly exponentially with height (**LAW**, hydrostatic balance). The collision rate is proportional to density (**LAW**, kinetic theory). A photon is emitted only if radiative decay beats the next collision (**LAW**: two rates competing) |
| 5 and 6 | To observe it: a camera, a spectrometer, two sites for triangulation. Steps: identify the lines, then the species, then the lifetimes, then the altitude profile, then the rate race |
| 7 Invariants | In one arc, the red sits above the green. **A red at the bottom is a different mechanism** (nitrogen at about 90 km in strong storms). A colour is a lead, not a finding |
| 8 Verification | AU1: ¹D about 110 s and ¹S about 0.7 s: **held, but weak**. AU2: red above about 200 km, green at 100 to 150 km: **held, but weak**. Both are lookups in the same sources Row 2 used, so they could not fail for the right reason (labelled weak at review). AU3: 630.0 and 636.4 nm come in a ratio of about 3, because both leave the same upper level: **held** (2.997 ± 0.016 measured, J. Phys. Chem. A 2006, doi 10.1021/jp056163x; a source independent of Row 2). AU4, not run: in pulsating aurora (patches that switch on and off every few seconds), the green should pulse and the red should barely pulse. **unknown** until a study with a 630 nm channel is read |

Analysis: the same atom paints both colours, and altitude decides which one survives. The ~110-second
lifetime acts like a large RC time constant (a slow capacitor) across the signal line. Above about 200 km
the air is thin enough that an excited atom gets to wait out its two minutes. Lower down, collisions empty
the capacitor first. AU4 is the prediction the mechanism makes that nobody handed us: a 110-second memory
averages a few-second rhythm away.

## A game economy: Archero (public sources only)

Sources: `.claude/skills/reverse-engineering/references/games-design-teardown.md` and
`.claude/skills/reverse-engineering/references/archero-design-seed.md`, which draw on Deconstructor of Fun, Naavik
and Scott Fine (2019). We never open the client, because Habby's terms forbid it.

| row | entry |
|---|---|
| 1 Purpose | For the player: short runs inside a long progression. For the studio: progression that sells **[observed in sources]** |
| 3 Mechanism and loops | Run power (three-choice ability drafts, reset every run) multiplied by meta power (talents, and equipment fused 3:1 per tier). Drops and purchases flow in; fusion and talents flow out. The duplicate-copy sink was **P** in 2019 (copies were dead weight) and was patched later **[observed in sources]** |
| 4 Principles | Stock change = inflow − outflow (**LAW**, conservation). 3:1 fusion compounds geometrically (**LAW**, arithmetic). "Time to the next goal drives retention" (**DESIGN CHOICE**: an industry heuristic, not a law) |
| 7 Failure modes | Each tier takes about 3 times longer when inflow is flat. Each new top grade makes old investment worthless. Four independent teardowns, from 2019 to 2026, agree **[observed in sources]** |
| 8 Verification | G1: 3^5 = 243 base copies for one top-tier item (**identity**). G2: damage-per-second × effective hit points (DPS × EHP) gives +53% DPS for −20% HP = **×1.224**, take it; +50% DPS for −40% HP = **×0.90**, refuse (arithmetic). G3: two picks of "+1 arrow, −25% damage each" give **+68.8%** if the penalties multiply and **+50.0%** if they add. A wiki rarely says which. **The cheapest test is a recording of our own play with the on-screen damage numbers; not run (it needs a play session)** |

Traps to watch: **Goodhart** (DPS × EHP hides the difference between one target and a crowd) and **the map
is not the territory** (a 2019 wiki number describing the 2026 game).
