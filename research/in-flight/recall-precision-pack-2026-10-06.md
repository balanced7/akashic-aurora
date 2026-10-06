# RECALL PRECISION AUDIT -- blind labelling pack

For each SURFACED item, judge it against THE ACTION ACTUALLY TAKEN (not the query text):
  on   = this item was on-point for that action
  off  = it was not
  skip = you cannot tell (skip is NOT 'off' -- unlabelled is not negative)

Then, per case, name any lesson that SHOULD have surfaced and did not (the recall arm).
Reply as: <case>:<slot> on|off|skip   and   MISS <case> <source-id or description>

## case 1  [command]
ACTION: echo "=== doctor (read) ===" && timeout 115 py -u agent_cli.py doctor 2>&1 | tail -25; echo "exit=$?"
  1:a  learn:experiment:roster_sensor_wrong_about_the_seat_reading_it
  1:b  learn:experiment:ghost_page_survives_in_hook_whisper_after_doctor_clears
  1:c  learn:experiment:consume_limit_hides_backlog

## case 2  [command]
ACTION: py -m pytest -q tests/test_mcp_arg_defaults_parity.py 2>&1 | tail -3; py scripts/checkers/check_advertised_verbs.py 2>&1 | tail -4; py -c " import json;d=json.load(open(r'c:/users/l5/appdata/local/temp/claude/e--/428ba6c4-2217-4008-a2be-ecd9901cc3b2/scratchpad/disc.json',encoding='utf-8'));print(d[0].keys() if isinstance(d[0],dict) else d[0])"
  2:a  learn:experiment:live_key_census_before_changing_a_key_derivation
  2:b  learn:experiment:launcher_pin_via_setx_is_invisible_to_running_processes
  2:c  learn:experiment:claude_trace_parity_via_hook

## case 3  [command]
ACTION: $env:pythonioencoding='utf-8' echo "=== (a) did we ever build web/fetch tools? repo-side ===" py -c " import subprocess for pat in ['webfetch','web_fetch','fetch_url','urlfetch','read_url','websearch']: r = subprocess.run(['git','grep','-l','-i',pat], capture_output=true, text=true, encoding='utf-8', errors='replace') hits = [h for h in (r.stdout or '').splitlines() if h.strip()][:6] print('%-12s %s' % (pat, hits if hits else '(no tracked hits)')) " echo "--- scripts/local/websearch.py head ---" if (test-path -literalpath 'e:\ai-setup\scripts\local\websearch.py') { get-content -literalpath 'e:\ai-setup\scripts\local\websearch.py' -totalcount 12 } echo "" echo "=== (b) does the live piano path read the gpu back per frame? (a stall, not a cost) ===" select-string -path 'e:\ai-setup\arsenal\web\piano\*.js','e:\ai-setup\arsenal\web\piano\*.html' -pattern 'readpixels|getimagedata|todataurl|readrendertargetpixels' | select-object -first 14 | foreach-object { "{0}:{1}: {2}" -f $_.filename, $_.linenumber, $_.line.trim().substring(0, [math]::min(110, $_.line.trim().length)) }
  3:a  learn:experiment:search_the_right_plane_before_searching_harder
  3:b  learn:experiment:burn_down_measures_the_players_not_the_system

## case 4  [command]
ACTION: cd "e:/ai-setup" && sed -n '150,215p' core/comm/discord_rooms.py
  4:a  learn:experiment:a_pin_minted_a_live_thread_in_his_server

## case 5  [command]
ACTION: grep -rn "ack_pages\|pager.page(\|retract" --include=*.py agent_cli.py core/comm/pager.py | head -30
  5:a  learn:experiment:escalation_needs_retraction_not_just_emission

## case 6  [command]
ACTION: echo "=== dead-world read probe: akashic_world=alpha py agent_cli.py status (bounded 90s) ==="; start=$(date +%s); akashic_world=alpha timeout 90 py agent_cli.py status > /tmp/alpha_status.txt 2>&1; rc=$?; end=$(date +%s); echo "exit=$rc elapsed=$((end-start))s"; head -25 /tmp/alpha_status.txt
  6:a  learn:experiment:one_word_two_meanings_is_how_gauges_lie

## case 7  [command]
ACTION: cd "e:/ai-setup"; grep -n -i -e "a receipt|must carry a receipt|wish without|self-report|felt friction|measured friction|count(ing)? friction|friction rate|how much friction|tax(ed)? per session" docs/wishlist.md | cut -c1-260 | head -30
  7:a  learn:experiment:chrome_cdp_media_domain_names_the_real_video_decoder

## case 8  [command]
ACTION: ls scripts | grep -i -e 'start|launch|boot|daemon|gateway|discord|wake|seat|up\b|mem_watch|house' | head -40; echo "--- docs"; ls docs | grep -i -e 'runbook|start|launch|ops|recover|house|morning|services' | head; echo "--- bat/ps1"; ls *.bat *.ps1 *.cmd 2>/dev/null; ls scripts/*.bat scripts/*.ps1 scripts/*.cmd 2>/dev/null | head -20
  8:a  learn:experiment:subagent_reports_live_only_in_their_final_message
  8:b  learn:experiment:a_long_lived_process_holds_a_dead_connection_while_the_server_is_healthy
  8:c  learn:experiment:a3_runner_down_recount_is_one_outage_not_a_mid

## case 9  [command]
ACTION: echo "=== all hook commands in pr/39 .claude/settings.json ===" && git show pr/39:.claude/settings.json | grep -n '"command"' ; echo; echo "=== all hook commands in master .claude/settings.json ===" && git show master:.claude/settings.json | grep -n '"command"'
  9:a  learn:experiment:hook_move_copy_repoint_remove_bootstrap_depth

## case 10  [command]
ACTION: echo "=== a small verb's parser + dispatch, for the pattern ===" && grep -n '"locks"' agent_cli.py | head -4 && echo "---" && grep -n "def cmd_locks" agent_cli.py && sed -n "$(grep -n 'def cmd_locks' agent_cli.py | cut -d: -f1),+8p" agent_cli.py
  10:a  learn:experiment:check_wiring_function_gate_a5_string_dispatch_bypass

## case 11  [command]
ACTION: echo "=== boot doors"; grep -n -e 'def knowledge_boot|def cmd_boot|def boot\(' core/comm/toolbox.py agent_cli.py ai_setup_mcp.py core/comm/*.py 2>/dev/null | head; echo "=== who resolves identity"; grep -n -e 'def resolve|def sid8|def binding' core/comm/seat_identity.py | head; echo "=== what build_autoboot/knowledge_boot takes"; grep -n -e 'def build_autoboot_context|def render_boot|def boot_context' core/**/*.py agent_cli.py 2>/dev/null | head -5
  11:a  learn:experiment:collective_intelligence_is_routed_corrections_not_pooled_knowledge

## case 12  [command]
ACTION: py - <<'py' import pathlib p = pathlib.path("agent_cli.py"); s = p.read_text(encoding="utf-8") before = s cmd = '''def cmd_focus(args): """check in / out: which task this session's tool calls belong to. the missing primitive under t056. task_costs attributes to "the one task owned by this agent in in_progress or verifying" and refuses on 0 or >1 -- and measured 2026-09-27, nine tasks are active under `claude`, so it refused every time and 172 done tasks carry zero cost data. owner matching cannot disambiguate nine open tasks; a session saying which one it is on can. """ from core.coord import session_focus as sf sid = getattr(args, "session", "") or sf.this_session() if getattr(args, "health", false): print(json.dumps(sf.health(), indent=2)); return 0 if not sid: print("error: no session id (claude_code_session_id unset). pass --session <id>.") return 2 if getattr(args, "clear", false): out = sf.clear_focus(sid) if out.get("was"): print(f"# checked out of {out['was']} -- {out.get('calls',0)} tool call(s) attributed " f"({out.get('hits',0)} on its files, {out.get('misses',0)} elsewhere)") else: print("# this session had no focus") return 0 if getattr(args, "quiet", false): sf.quiet(sid); print("# drift notes silenced for this session; attribution continues"); return 0 if getattr(args, "set", ""): r = sf.set_focus(sid, args.set, agent=args.agent_id or "") if not r.get("ok"): print(f"error: {r.get('error')}"); return 2 print(f"# focused {r['task']} ({r.get('status')}) -- {r.get('title','')[:70]}") if r.get("files"): print(f"# drift watched against: {', '.join(r['files'][:4])}" f"{' ...' if len(r['files']) > 4 else ''}") if r.get("note"): print(f"# note: {r['note']}") return 0 st = sf.current(sid) if args.json: print(json.dumps(st or {}, indent=2)); return 0 if not st: print("# no focus. set one: py agent_cli.py focus --set t###"); return 0 print(f"# focus {st['task']}: {st.get('calls',0)} call(s) attributed " f"({st.get('hits',0)} on its files, {st.get('misses',0)} elsewhere, " f"streak {st.get('streak',0)})") if st.get("nudges"): print(f"# drift notes: {st['nudges']} sent, {st.get('dismissed',0)} dismissed") return 0 ''' anchor = "def cmd_locks(args):" assert anchor in s s = s.replace(anchor, cmd + anchor, 1) parser = ''' fcs = sub.add_parser("focus", help="check in/out: attribute this session's tool calls to a task") fcs.add_argument("agent_id", nargs="?", default="") fcs.add_argument("--set", default="", metavar="t###", help="check in: focus this task") fcs.add_argument("--clear", action="store_true", help="check out, and report what was attributed") fcs.add_argument("--quiet", action="store_true", help="silence drift notes here; keep attributing") fcs.add_argument("--health", action="store_true", help="is the drift nudge earning its keep?") fcs.add_argument("--session", default="", help="override the session id (default: this session)") fcs.add_argument("--json", action="store_true") fcs.set_defaults(fn=cmd_focus) ''' panchor = ' lks = sub.add_parser("locks", help="show who holds which advisory path-locks")' assert panchor in s s = s.replace(panchor, parser + panchor, 1) assert s != before p.write_text(s, encoding="utf-8", newline="\n") print("crlf:", p.read_bytes().count(b"\r\n")) py py agent_cli.py focus 2>&1 | head -3
  12:a  learn:experiment:d3_mojibake_guard_fenced
