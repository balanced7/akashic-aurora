# Gaming & modding — playbook and current state

Daniil wants to revisit gaming and modding. This is the durable record: what was done, what's
installed where, and the rules that transfer to the next game. Grow it in place; don't start a new
doc per game.

## Current state (2026-09-20)

- **OptiScaler v0.9.4** installed in **Crysis 3 Remastered** at
  `F:\SteamLibrary\steamapps\common\Crysis3Remastered\Bin64`.
- **FSR 4.1.1 confirmed working** (quality + performance difference reported large). Achieved via
  `Dx11Upscaler = fsr31_12` (the "FSR3.X/4 w/Dx12" dx11on12 interop, because the game is DX11) on an
  RX 9070 XT (RDNA4).
- **Backup** of the old v0.7.9 install: `Bin64\_OptiScaler_backup_20260920-150809` (rollback is one
  copy away).
- The stale **pre-FSR4 `amdxcffx64.dll`** was renamed to `amdxcffx64.dll.old` — it was the thing
  pinning the game to FSR 3.2 while FSR 4.1.1 was installed and running underneath.

## The playbook (reusable for any game / mod)

1. **Find the install fast.** Registry `HKLM\...\Uninstall\*\InstallLocation` beats guessing
   `steamapps\common`. (We found it there when the operator had forgotten where it was.)
2. **Back up before touching anything.** Copy the tool's proxy DLL + its config + any same-named
   runtime DLLs to a dated `_backup` folder. Modding is only fun when rollback is one command away.
3. **Know the render API — it decides the upscaler path.** FSR4 is DX12-only; on a DX11 title it
   works only through the "FSR3.X/4 w/Dx12" (dx11on12) interop; Vulkan is unsupported. DLSS in the
   game's own settings is what OptiScaler intercepts and swaps for FSR.
4. **Remove leftover same-named DLLs from older versions.** A stale runtime in the folder shadows the
   new one and silently pins the old backend — this is the single most common "upgrade didn't take".
5. **Verify the ACTIVE backend, never the label.** The overlay/version string lies (it showed "3.2"
   while 4.1.1 was running). Definitive checks: (a) the tool's own watermark flag
   (`Fsr4EnableWatermark = true`), and (b) inspect the running process's loaded DLLs
   (`(Get-Process <game>).Modules`).

## The rules that transfer beyond gaming

- **Measure / verify the active thing, not its label.** (Same law as the canvas, the vision model,
  the census — the string is never the ground truth.)
- **A stale versioned file shadows a new one** — generalized DLL-hell; check for leftovers before
  reinstalling anything.
- **Backup first, keep rollback one command away.**

## Halo: Campaign Evolved (2026-09-20)

- **Native FSR 4**, enabled automatically on RDNA4 (RX 9000). No OptiScaler needed — this is NOT the
  Crysis case (the game already ships FSR4).
- Shipped runtime was **`amd_fidelityfx_upscaler_dx12.dll` v4.0.3.604** at
  `Engine\Plugins\Halo.External\FSR4\Source\fidelityfx-sdk\Kits\FidelityFX\signedbin\`.
- **Upgraded to v4.1.1.2740** (OptiScaler's FFX DLL) by a direct DLL swap — the "replace a DLL" trick
  (igorslab: FSR 4.0 → 4.1.1 = replace the DLL). Original backed up as `…\amd_fidelityfx_upscaler_dx12.dll.v4.0.3.bak`.
- **What 4.1.1 buys over 4.0.3:** sharper upscaled detail, smoother camera motion (less
  shimmer/ghosting — the 4.1.1 build is specifically the anti-shimmer update), slightly higher FPS.
- **Caveat:** shipped UE5 builds may load the DLL from inside a `.pak` rather than the loose file —
  if the swap has no visible effect, that's the next thing to check. Rollback = restore the `.bak`.

## Revisit checklist

- [ ] Does the RX 9070 XT driver path need the Adrenalin "FSR4 Upscaling" global toggle for *other*
      (DX12) games, instead of per-game OptiScaler?
- [ ] Shimmer in Crysis 3: the documented fix is an `Engine.ini` line
      (`r.NGX.DLSS.DilateMotionVectors=0`) — only if it shows up in motion.
- [ ] Other titles to try: any DX11/12 game with FSR2/DLSS2/XeSS is a candidate (see OptiScaler's
      compatibility list; avoid Easy Anti-Cheat / BattlEye titles — the proxy DLL is refused).
