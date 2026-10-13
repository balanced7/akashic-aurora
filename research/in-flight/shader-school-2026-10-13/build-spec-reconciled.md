# Shader school: the reconciled build spec (2026-10-13, night)

**Judge:** Vandor (claude seat), sole committer. **Inputs:** `unified-architecture-draft.md` (half A, written by the
synthesis agent from the census, research and study), Heimdall's blind half B
(`research/reviewed/shader-school-2026-10-13/heimdall-unified-module-system-blind-half-b.md`), and
`primitive-atlas-draft.md`. Half A's section 17 already reconciles the two point by point; this page records the rulings
that bind the build, where they differ from either half, and why.

## Rulings

1. **Adopt half A as the build spec**, with the changes below. Location `arsenal/web/glsl/`; manifest ids `glsl.<name>`;
   one `//!` multi-line JSON header (no third dialect); the bench chunks read in place, never copied.
2. **Licence of house modules is Apache-2.0** (half A), not CC-BY-NC-SA (half B). House modules carry no corpus code;
   the licence-line test proves it. Corpus ancestry is confined to `legacy/` twins marked `"public": false`.
3. **No rename of the legacy chunks tonight** (overrules half A's S2 rename of `fbm3`/`vn`). The library's names avoid
   the clash instead (the atlas naming law owns that): a rename touches tracked bench files, their callers and the recall
   lessons generated from chunk headers, for no gain the library cannot get by choosing its own names. S2 keeps the lint
   teeth and the provenance correction (metadata only).
4. **The unified Workbench's first home is the Shader Lab** (`arsenal/web/shaderlab/index.html`, served by
   `py -m arsenal shader serve`, port 8797, loopback), not the bench page on 8787: the lab is ours end to end, has no
   ownership boundary (DeepSeek owns `scripts/bifrost_ui.py`), and cannot disturb an approved look. Its parts live in
   `arsenal/web/lib/workbench/` so the bench, Studio and First Light can mount the same components later. The bench gets
   the shared codegen (S5) tonight; its Workbench layout is P1.
5. **Safe by default for Daniel's GPU.** The lab shows pre-rendered SwiftShader filmstrips for every Shelf shader and
   every group; running one live on his GPU is an explicit click that names the cost class first, uses the house
   watchdog (consecutive slow frames while rAF fires; hold the last frame) and a render scale that starts at 0.5 for C3/C4
   subjects. Nothing renders live on page load.
6. **Navi's lanes go to claude seats** (Navi is past her spend grant; raising it is Daniel's call). Heimdall fences each
   stage: a blind review of the acceptance before the code, and of the diff after. His replies are persisted verbatim.
7. **Order.** S0, S1 and S4 now (no overlap with the foundation workflow's files); S2, S3a, S3b, S5, S6, S7 and the lab
   UI after the foundation workflow lands its runtime, harness and dissector (they edit `serve.py`, `render.py`,
   `toy-runtime.js`). First Light (S8) waits for Daniel: an approved look.
8. **What not to do tonight** stands exactly as half A's list: no pixel moves on an approved look; no GPU render outside
   the lock; no WebGL page in the app's browser pane; never port 8793; no corpus code in a tracked file, CC0 and MIT
   included; delete nothing.

## The one question for Daniel (from half A, kept as written)

When a shared module improves, should a look he approved update by itself, or show him a before and after first?
Recommendation: unapproved surfaces update by themselves; approved looks show a one-click before and after.
