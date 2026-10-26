# Bifrost console (Next.js)

The live agent console rebuilt as a Next.js app. It is only a face: the Python console
(`scripts/bifrost_ui.py`, 127.0.0.1:8787) stays the bus bridge, and every API call plus the live
stream is proxied to it (`next.config.ts`, `app/events/route.ts`). Point it elsewhere with
`BIFROST_API`.

Runs on 127.0.0.1:8789 (`config.PORT_UI_NEXT`), localhost only like the original. Needs Node 22.

```sh
pnpm install
pnpm dev          # http://127.0.0.1:8789, hot reload
pnpm test         # unit tests (feed folding, markdown safety)
pnpm e2e          # Playwright against the live backend; sends are intercepted
pnpm build && systemctl --user restart aurora-bifrost-next   # update the running service
```

Ported so far: live message stream with trace folding and 1:1 threads, agent presence pills,
pause/resume, the composer (Inform/Steer/Interrupt, recipient picker, broadcast arm guard, file
drop/paste upload), code-block Copy/Run, and the aurora shader background (loaded from the
backend's `scripts/aurora-shader.js`).

Not yet ported from the 8787 console: launcher, episodes, presentation settings, slide deck/viz,
engine-room gauges, world/floor/resident lines, HUD and voice line, hero avatar, rooms, link
panel, report shelf, and the VFX lab.
