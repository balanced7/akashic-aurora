# A0 brief: house-safe hardening of the arsenal server (alpha release, phase 0)

*For: Heimdall (build), fenced with Vandor (review and commit). Evidence: [census.md](census.md) sections 1c, 1d, 3d and 4. Plan: [plan.md](plan.md). Do not start until Vandor posts "final heat done" on the bus, because the bake-off harness imports `arsenal.serve` live.*

## Why

Daniel wants /piano packaged so strangers can run it with any MIDI keyboard ("a single click install"). Before anyone else runs the local server, it must not trust arbitrary web pages. The same fix protects Daniel's own machine today. Saved data must also be able to live outside the code folder, or every installer breaks.

## Scope (all behaviour for the house profile stays the same unless stated)

1. **Origin and Host checks.**
   - Every POST route and every GET route that returns private data needs a check: `/api/performance*`, `/api/library`, `/api/takes`, jam/deck reads, cues status.
   - **Host:** accept only `127.0.0.1:<port>`, `localhost:<port>` and `[::1]:<port>`. Everything else gets 421 or 403. This is the DNS-rebinding defence.
   - **Origin:** accept an absent Origin (CLIs and curl, which the cue route already allows at `serve.py:520-522`) or a same-origin `http://127.0.0.1:<port>` / `http://localhost:<port>`. Reject everything else with 403.
   - **JSON bodies:** require `Content-Type: application/json` on JSON POSTs (`_read_json`, `serve.py:204-209`), so a CORS-simple `text/plain` POST from a web page is refused.
   - **Code shape:** one helper and one table of which routes are private. Do not scatter ad-hoc checks.
2. **State root.**
   - `ARSENAL_STATE` (env) overrides the root for the practice log, takes, jam cards and runs, and every other `state/arsenal/...` path computed from the package location (`performance.py:32`, `take.py:22`, `jam/cards.py:33`; census section 1d lists the rest).
   - **Default in the house profile:** unchanged (repo `state/arsenal`).
   - **Default in the alpha profile:** the per-user data dir, `%LOCALAPPDATA%\PianoAlpha\state` on Windows and `~/Library/Application Support/PianoAlpha/state` on macOS.
   - **Code shape:** one resolver function, used everywhere.
3. **Recordings root.** `ARSENAL_LIBRARY` overrides `serve.py:38`. The alpha default is the user's Videos folder + `PianoAlpha`. The house default is unchanged.
4. **Profile flag.** `ARSENAL_PROFILE` = `house` (default) or `alpha`. Expose it read-only to the page, e.g. `GET /api/profile` returning `{profile, assistantName, userName}`, so later phases can hide house-only surfaces. In alpha, `/` redirects to `/piano`; in house, `/` stays as it is today.
5. **Static types.** Add `.woff2` (`font/woff2`) to `STATIC_TYPES` (`serve.py:41-45`).

## Out of scope

- Any piano.js UI change (that is A1).
- Vendoring downloads (A2 needs Daniel's OK).
- Deleting any route or feature.

## Tests (write them first, as red then green)

- Each private GET with `Host: evil.example:8793` returns 421 or 403. With `Host: 127.0.0.1:<port>` it returns 200.
- A POST to `/api/performance/...` with `Origin: https://evil.example`, and a POST with `Content-Type: text/plain`, are both refused. The same POST with no Origin and JSON succeeds.
- The cue POST still works from curl (no Origin).
- `ARSENAL_STATE=<tmp>` sends practice log, takes and jam writes under tmp. With it unset, paths are identical to today.
- With `ARSENAL_PROFILE=alpha`, `/` redirects to `/piano`. With house, `/` behaves as today.
- **House regression:**
  - the existing arsenal pytest set stays green;
  - the page's own fetches still work, because they are same-origin. Check the log, cues, deck and REC upload paths by grepping piano.js, log.js, deck.js and transport.js for `fetch(`, and confirm each sends JSON with a same-origin Origin.

## Rules

- Take advisory locks on the files you edit: `py agent_cli.py lock <seat> <path> --ttl 3600`.
- Edit only `arsenal/serve.py`, `arsenal/performance.py`, `arsenal/take.py`, `arsenal/jam/*.py` (path resolution only), a new `arsenal/paths.py` if useful, and new tests under `tests/`.
- Do NOT restart the running server on 8793. Vandor restarts it after review.
- No git state changes and no `scripts/mirror.py`. Vandor commits.
- Report back on the bus with: the diff paths, the test counts (red before, green after), and anything in census section 3d you could not close.
