# VFX system code map, 2026-09-12

This is a read-only pass over `E:\AI-Setup`, run by an Explore agent that claude (Vandor) sent out before tying a new project into the VFX bench. The report is kept verbatim. Claims marked "found by reading" were never executed. The intent and the sliced plan are in `vfx-studio-synthesis-and-plan-2026-08-02.md`, and the craft rules are in `.claude/skills/shader-craft/SKILL.md`. Line numbers were taken on 2026-09-12, when `scripts/bifrost_ui.py` carried Navi's uncommitted reasoning-stream edit, so expect them to drift.

---

The VFX system is a rendering bench bolted onto the Bifrost console, and it is dormant right now. Nothing is listening on 8787 and no `bifrost_ui` process is running. It was last used 2026-09-03 (commit 803f32b8, "orrery v5"). All paths below are under `E:\AI-Setup\`.

## 1. What it is

Every render runs in whichever `/vfx` browser tab holds a lease, and the server only brokers.
- **Server**, `scripts\bifrost_ui.py`: keeps a job queue (:187-201), a renderer lease (:216-266) and a feed (:298-355), all in memory.
- **Renderer**, `scripts\vfx.html`: a WebGL2 page that loads `/agent-avatar.js` (:375) and runs jobs in `runJob` (:1670-1828).
- **CLI**, `scripts\vfx_render.py`: standard-library client that prints the output PNG path to stdout.
- **Ingest**, `scripts\vfx_ingest.py`: converts Shadertoy source into the bench's shader format as plain text.
- **Recall**: `core\learning\vfx_chunk_lessons.py` turns chunk headers into Redis lessons. `core\learning\domains.py:32-65` and `core\recall\at_action.py:1381-1395` route those lessons to domain `vfx`.
- **Probes**, `scripts\vfx_probe_*.py`: offline image metrics, stdout only.

```
vfx_render.py ─POST /vfx/job─▶ _VFX_JOBS ◀─GET /vfx/job/next (900ms)─ vfx.html runJob
   └─poll GET /vfx/job/<id>       ▲  POST /vfx/snap {name,png} ◀─────┤ → design\vfx-snaps\*.png
                                  └─ POST /vfx/job/result ◀──────────┘
                                       └▶ _VFX_FEED ─GET /vfx/feed (700ms)▶ page thread
chat box ─POST /send▶ Bifrost bus     design\vfx-chunks\*.glsl ─adopt▶ Redis ─▶ recall-at
```

## 2. In / out

- **Job**: `POST /vfx/job {op,args}` returns `{id:"jN",op,args,state:"pending",result:null}`.
  - Poll `GET /vfx/job/jN`; state goes pending → running → done.
  - The result is `{ok,path,bytes}` or `{ok:false,error}`.
  - Ops are `state thumb sheet grid sketch script graph snap`; args mirror the CLI flags (`vfx_render.py:180-258`), plus an optional `say`.
  - `script.steps[]` entries are `{do: node|link|set|state|style|identity|clear|build|snap, ...}`.
  - `graph` is `{nodes[{id,chunk,x,y}], edges[{from,fromPort,to,toPort,type}]}`.
- **Lease**: `GET /vfx/job/next?worker=&visible=0|1` returns a job, `{}`, or `{viewer:true}`.
  - TTL is 6 s, renewed by polling. A visible tab beats a hidden one; an unnamed caller is `legacy` and yields only to an equal (:220-242).
  - `GET /vfx/renderer` returns `{attached,worker,visible,idle}`.
- **Feed**: `POST /vfx/feed {text≤2000, kind="say", label≤80, from≤32}`.
  - `GET /vfx/feed?since=N` returns `{entries,last}`; `since=0` gives the newest 30, and the feed caps at 300.
  - A render entry is `{id,ts,from,kind:"render",op,ok,text,label:"<op> <subject>",error,path,url}` (:328-340).
  - POSTed entries always get an empty `path`/`url` (:1265), so images reach the page only through job results.
- **Ingest**: `POST /vfx/ingest {name,src}` returns `{ok,name,bytes,kind:shadertoy|passthrough,notes[],warnings[],summary}`.
- **Uploads and stores**:
  - `POST /vfx/snap|thumb {name,png:dataURL}` and `/vfx/clip {name,webm}`.
  - `/vfx/sketch`, `/vfx/presets`, `/vfx/compositions`, `/vfx/groups`, `/vfx/graphs`.
  - `/vfx/bench` takes a merge-patch; `subject` must be `avatar` or `shader` (:656-696).
- **File formats**:
  - A chunk file's first line is `//! {"name","kind","from","note","order","cat","in","out"}`.
  - A sketch needs `#version 300 es`, `precision highp float;`, `uniform vec2  u_res;`, `uniform float u_time;`, `out vec4 outColor`.
- **CLI verbs**:
  - `vfx_render.py state|thumb|sheet|grid|sketch|script|graph|ingest|say`; exit 0 ok, 1 failed, 2 no console, 3 no renderer or timeout.
  - `agent_cli.py recall-at --gesture --subject --domain` (:7720-7731).
  - `py -m core.learning.vfx_chunk_lessons`.
- **Bus**: render traffic never touches Bifrost or Redis, by design (:1255-1258). Nothing watches files; everything is polled.
- **Out**:
  - `design\vfx-snaps\<name>.png` (≤8 MB)
  - `design\vfx-thumbs\<name>.png` (≤2 MB) and `.webm` (≤6 MB, via MediaRecorder)
  - `design\vfx-sketches\<name>.frag` and `design\vfx-*.json`
  - Redis keys `learn:experiment:vfx_chunk_<name>` and `learn:anti_patterns`

## 3. Runtime

- **Launch**: `py scripts\bifrost_ui.py` (defaults 127.0.0.1:8787, :1552-1553), then open `/vfx` in a tab that stays visible. No scheduled task starts either one.
- **Dependencies**: Python standard library plus a browser with WebGL2 and MediaRecorder. There is no ffmpeg, headless browser or moderngl; the design rejected them (`vfx_render.py:9-16`).
- **Git history**:
  - Built 2026-08-02 (d10c495f through 2ef87677; domains 4431a42f and c197ebce).
  - Probes tracked 09-02 (e2dee4d5).
  - Last used 09-03 (803f32b8): `design\vfx-bench.json` still points at the `orrery` sketch and 7 snapshots from that day are untracked.
  - shader-craft skill and pin landed 09-09 (4be20341, d3caa944).
- **`E:\Video Output E`**: nothing in the repo reads or writes it. It is OBS Studio's recording folder (`%APPDATA%\obs-studio\basic\profiles\Untitled\basic.ini` has `FilePath=E:/Video Output E`). It holds 89 mp4 files, 42 GB, dated 2026-03-29 to 09-06.

## 4. Pins

`tests\test_vfx_feed_and_lease.py` resets the module globals `_VFX_LEASE`, `_VFX_FEED`, `_VFX_FEED_SEQ`, `_VFX_JOBS` and `_VFX_SEQ` directly (:34-43), so those names can't change. It asserts:
- Exactly one tab gets a job; the other gets `{viewer:true}`.
- A visible tab displaces a hidden one, and a hidden tab never steals, even from a visible `legacy` tab (:108-120). The lease is released after the TTL.
- Both successes and failures post to the feed (`url` is `/vfx/snap/x.png` or `""`; `label` is `thumb swirl`).
- The since-cursor works, catch-up returns 30 entries, and the feed stays ≤300 with ids that keep increasing.
- Bench writes merge, an unknown subject is refused without a partial write, and a corrupt bench file doesn't stop the page opening.

`tests\test_shader_craft_skill_cites_live_surfaces.py` asserts:
- Every path the skill names exists (p1).
- 12 quoted lines (from `agent-avatar.js`, `aurora-shader.js`, `activity-line.js`, `fibshell.frag`) are in the source, the cookbook and HEAD (p2/p7).
- The modules still have their `isSupported`/`setState`/`start` entry points (p3).
- **Every `design\vfx-sketches\*.frag` uses the sketch format above (p4).**
- `vfx_render.py` keeps `thumb/sheet/grid/state/ingest` and `--file --t --say --frames --from --to` (p5).

`test_vfx_ingest.py` (13 tests) and `test_domain_recall_triggers.py` pin the ingest conversion and the recall routing.

## 5. Gaps and extension points

- **Plan slices S1–S7**: none of their defining pieces exist in code.
  - No render ledger, so jobs and the feed vanish on restart.
  - No take strip, no `--mode split`, no `probe` verb, no staleness hash.
  - Metrics exist only as the offline probes.
- **Ingest paste box ("next")**: not built. The page saves pasted shaders through `/vfx/sketch` (`vfx.html:1390`) without conversion. Texture inputs (`iChannel`), multi-pass and sound shaders are unsupported (`vfx_ingest.py:25-28`).
- **Likely bug** (found by reading, not run): the chat box posts `target:'claude'` (`vfx.html:2116`) but `_send` reads `to` (`bifrost_ui.py:1432`), so the message goes to every agent.
- **vfx recall is half-wired**: the `gesture`/`subject` trigger (`at_action.py:1389`) has no live caller because the page never calls recall-at. Chunk adoption only happens when run by hand; `MAP.md:211` marks it GAP.
- **Hardcoded limits**: `BASE` is fixed at 127.0.0.1:8787 (`vfx_render.py:42`), `subject` must be `avatar` or `shader`, and there is no mp4 export.
- **Where a new project plugs in**:
  - **New op**: one branch in `runJob` plus a CLI subparser (`--say` is added automatically, :264-266). The server accepts any op name and posts every result to the feed (:269-279).
  - **Shader**: `POST /vfx/ingest`, or drop a `.frag` in the sketch format.
  - **Narration**: `POST /vfx/feed` with your own `from`.
  - **Reusable piece**: a chunk `.glsl` with a `//!` header.
  - **Recall**: a new entry in `DOMAINS` / `_PATH_HINTS`.
  - **Metrics**: add fields to the job result.
