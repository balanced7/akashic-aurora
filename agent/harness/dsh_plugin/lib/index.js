// dsh-akashic-recall — the five-listener adapter (sealed fence t383-dsh-adapter).
// WIRED LIVE 2026-08-24: mount fixed via cordis.patch.yml insert form with a
// relative-file name (see tests/test_dsh_contract.py for the pinned contract).
//
// Listeners and their sealed tier mapping:
//   session/created        -> T2 trigger: boot whisper fetched, presence idle
//   system-prompt/assemble -> T2 injection (whisper as a SECTION, survives R1
//                             suppression) + T5 derived (plan recall as a CONTEXT)
//   session/event          -> T5 trigger (user/message) + R1 probe confirmation
//   tools/post-execute     -> T3 one-beat-late (recall contexts) + T4 DIRECT
//                             (isError => FAIL half, then retry recall; success
//                             => resolve; flip => nudge context) + draft keepalive
//                             (fire-and-forget refresh of last-session-draft.md)
//   session/flush+disposed -> T6 capture (where-we-are distiller) + presence offline
//
// Presence (Daniil, reconciliation PRESENCE section): every event fires a
// roster.heartbeat via bridge `presence`; the rich presence hash snippet is
// claude's backend item — this file only routes phase + session id.
//
// Identity: session_key is the explicit constant 'dsh_agent' (never env);
// seen-key is DSH_SESSION_ID. If AKASHIC_AGENT_ID resolves to anything else at
// load, the plugin pins itself observe-only (captures + presence still run).
// R1 static half: includeRuntimeContext === false => plan contexts skipped,
// loud log. R1 dynamic half: once-per-session marker probe, confirmed by
// scanning the session/event feed; silence = loud "context dropped".
// R2: dsh-invariants registration asserts the post-execute listener exists.
import { appendFileSync, mkdirSync, statSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineTool } from '@deepseek-ai/dsh-tools'

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const BRIDGE = join(PLUGIN_DIR, '..', 'bridge.py')
const SESSION_KEY = 'dsh_agent'
const CAP_DIR = join(tmpdir(), 'akashic_recall', 'payloads_dsh')
const LOG = (...a) => console.log('[dsh-akashic-recall]', ...a)

// GENERATION FRESHNESS (Vandor's ask + Rill's refinement, 2026-08-24): the ESM cache
// serves the module object loaded at FIRST import, while apply() RE-EXECUTES on entry
// restart -- so a module-scope stamp survives every reload and an apply-time re-stat
// exposes exactly the lie "I just applied a fix". No invariants service needed; the
// bug becomes its own detector.
const LOADED_MTIME = (() => {
  try { return statSync(fileURLToPath(import.meta.url)).mtimeMs } catch { return 0 }
})()

let listenerRegistered = false
let observeOnly = false
const sessions = new Map() // sid -> { whisperText, whisperInjected, planPending, lastPrompt, probe }

const activeSid = () => process.env.DSH_SESSION_ID || ''
const stateFor = (sid) => {
  if (!sid) return null
  if (!sessions.has(sid)) sessions.set(sid, { whisperText: '', whisperInjected: false, planPending: false, lastPrompt: '', probe: null })
  return sessions.get(sid)
}

function capture(record) {
  try {
    mkdirSync(CAP_DIR, { recursive: true })
    appendFileSync(join(CAP_DIR, 'captures.jsonl'), JSON.stringify(record) + '\n', 'utf8')
  } catch {}
}

function spawnBridge(args, { await_ = true, timeoutMs = 5000 } = {}) {
  const run = () => new Promise((resolve) => {
    const child = spawn('py', [BRIDGE, ...args], { windowsHide: true })
    let out = ''
    let done = false
    const finish = (v) => { if (!done) { done = true; resolve(v) } }
    const timer = setTimeout(() => { child.kill(); finish(null) }, timeoutMs)
    child.stdout.on('data', (d) => { out += d })
    child.on('error', () => { clearTimeout(timer); finish(null) })
    child.on('close', () => { clearTimeout(timer); try { finish(JSON.parse(out)) } catch { finish(null) } })
  })
  const p = run()
  p.catch(() => {})
  return await_ ? p : null
}

function firePresence(phase) {
  const sid = activeSid()
  if (sid) spawnBridge(['presence', '--phase', phase, '--session-id', sid], { await_: false })
}

function extractTarget(args) {
  if (!args || typeof args !== 'object') return { path: null, command: null }
  const path = typeof args.file_path === 'string' ? args.file_path : typeof args.path === 'string' ? args.path : null
  const command = typeof args.command === 'string' ? args.command : null
  return { path, command }
}

function extractEventText(event) {
  try {
    const blocks = event && event.data && Array.isArray(event.data.content) ? event.data.content : []
    return blocks.map((b) => (b && typeof b.text === 'string' ? b.text : '')).join('\n')
  } catch { return '' }
}

function eventHasToken(event, token) {
  return !!token && extractEventText(event).includes(token)
}

function attachContext(decision, text) {
  if (!decision || !text) return decision
  if (decision.kind === 'accept' || decision.kind === 'block') {
    const ctxMsg = {
      // Message contract (dsh-llm message.d.ts): id + role + content + source are
      // REQUIRED — an absent source crashes the ferry on source.kind (drilled
      // 2026-08-24). The source vocabulary has a first-class slot for us:
      // kind 'plugin' with form 'recall' ("material lifted out of another
      // session's log, possibly reduced on the way in").
      id: `akashic-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      role: 'user',
      content: [{ type: 'text', text }],
      source: { kind: 'plugin', plugin: 'dsh-akashic-recall', form: 'recall' },
    }
    return { ...decision, additionalContexts: [...(decision.additionalContexts ?? []), ctxMsg] }
  }
  return decision
}

const _probeToken = () => `akashic-probe-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

// ---------------------------------------------------------------------------
// MCP DOOR CLIENT -- the typed-tools finish (2026-08-24). One PERSISTENT child
// runs `py ai_setup_mcp.py` (the MCP twin of agent_cli.py); the plugin registers
// each curated door tool as a NATIVE cordis tool, so the seat stops shelling for
// every verb. Schemas come from tools/list at runtime -- the plugin never hardcodes
// the door's contract, so the two surfaces cannot drift. Fail-open throughout: if
// the door cannot start or a call fails, the tool reports the error shape; the
// recall listeners never depend on it.
// ---------------------------------------------------------------------------
const DOOR_TOOLS = [
  'boot', 'learn', 'recall', 'recall_at', 'recall_feedback', 'note', 'notes',
  'status', 'task', 'mailbox', 'stats', 'injections', 'graduate', 'log',
  'handoff', 'story', 'events', 'promoted', 'locks', 'lock', 'unlock',
  'bifrost_sync', 'bifrost_send', 'bifrost_inbox', 'bifrost_presence',
  'knowledge_map', 'friction', 'tag_anti_pattern',
  // T383 tranche 1 (2026-08-26): the read family -- eye surface + coordination reads
  'eye', 'find', 'freq', 'get', 'ingest', 'overview', 'standing', 'trace',
  'zoom', 'route', 'delta', 'roster', 'scout', 'timeline', 'compare',
  // T383 tranche 2a (2026-08-26): resident-ceremony READS + repeat (write moves stay CLI)
  'resident', 'roles', 'show', 'verdict_file', 'calibration', 'repeat',
]
const DOOR_PREFIX = 'akashic_'
const DOOR_TIMEOUT_MS = 60000

const door = { proc: null, nextId: 1, pending: new Map(), tools: new Map(), ready: false }

// DOOR SELF-HEAL (wired 2026-08-26): a long-lived child of a long-lived host must not
// take the seat's hands down with it. On exit, respawn with backoff up to RESPAWN_MAX
// attempts; a successful handshake resets the counter; exhaustion is LOUD (captured,
// greppable) -- a dead door that pretends it might answer is the silence class this
// file exists to retire.
let applyCtx = null
let respawnAttempts = 0
const RESPAWN_MAX = 3
const RESPAWN_BASE_MS = 2000

function scheduleDoorRespawn() {
  if (respawnAttempts >= RESPAWN_MAX) {
    capture({ at: Date.now(), kind: 'door-respawn-exhausted', attempts: respawnAttempts })
    return
  }
  if (!applyCtx) return
  respawnAttempts += 1
  const delay = RESPAWN_BASE_MS * Math.pow(2, respawnAttempts - 1)
  capture({ at: Date.now(), kind: 'door-respawn', attempt: respawnAttempts, delay })
  setTimeout(async () => {
    const ready = await doorHandshake()
    if (ready) {
      respawnAttempts = 0
      // Tool registrations are a ONE-TIME act at apply(); the harness persists them
      // and REFUSES a duplicate (drill receipt 2026-08-26: 'tool akashic_boot is
      // already registered'). doorCall reroutes to the fresh child automatically, so
      // the respawn is handshake-only -- nothing to re-register, nothing to lie about.
      LOG(`door respawned: ${door.tools.size} tools remain registered (child restarted)`)
      capture({ at: Date.now(), kind: 'door-respawn-ok', tools: door.tools.size })
    }
  }, delay)
}

function doorSpawn() {
  const repo = process.env.AKASHIC_REPO
  if (!repo) {
    LOG('MCP door NOT spawned: AKASHIC_REPO unset (the .env stamp is missing) -- typed tools unavailable, listeners unaffected')
    capture({ at: Date.now(), kind: 'door-unavailable', reason: 'no AKASHIC_REPO' })
    return null
  }
  try {
    const proc = spawn('py', ['ai_setup_mcp.py'], {
      cwd: repo, windowsHide: true,
      stdio: ['pipe', 'pipe', 'ignore'],
    })
    let buf = ''
    proc.stdout.on('data', (d) => {
      buf += d.toString('utf8')
      let nl
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl).trim()
        buf = buf.slice(nl + 1)
        if (!line) continue
        let msg
        try { msg = JSON.parse(line) } catch { continue }   // tolerate stray non-JSON lines
        const id = msg.id
        if (id !== undefined && door.pending.has(id)) {
          const { resolve, timer } = door.pending.get(id)
          door.pending.delete(id)
          clearTimeout(timer)
          resolve(msg)
        }
      }
    })
    proc.on('error', () => { door.ready = false; door.proc = null })
    proc.on('exit', () => {
      door.ready = false
      door.proc = null
      for (const { resolve, timer } of door.pending.values()) {
        clearTimeout(timer)
        resolve({ id: null, error: { message: 'door process exited' } })
      }
      door.pending.clear()
      capture({ at: Date.now(), kind: 'door-exit' })
      scheduleDoorRespawn()
    })
    door.proc = proc
    return proc
  } catch (e) {
    LOG('MCP door spawn failed:', e && e.message)
    capture({ at: Date.now(), kind: 'door-unavailable', reason: String(e && e.message) })
    return null
  }
}

function doorRpc(method, params, expectReply = true) {
  const proc = door.proc
  if (!proc || !proc.stdin.writable) return Promise.resolve(null)
  const id = door.nextId++
  const req = { jsonrpc: '2.0', method }
  if (params !== undefined) req.params = params
  if (expectReply) req.id = id
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      if (door.pending.has(id)) {
        door.pending.delete(id)
        resolve({ id, error: { message: `door timeout after ${DOOR_TIMEOUT_MS}ms` } })
      }
    }, DOOR_TIMEOUT_MS)
    if (expectReply) door.pending.set(id, { resolve, timer })
    try {
      proc.stdin.write(JSON.stringify(req) + '\n')
    } catch {
      if (expectReply) { door.pending.delete(id); clearTimeout(timer) }
      resolve(null)
    }
    if (!expectReply) resolve(null)   // notifications: fire and forget, nothing to wait for
  })
}

async function doorHandshake() {
  const proc = doorSpawn()
  if (!proc) return false
  const init = await doorRpc('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'dsh-akashic-recall', version: '0' },
  })
  if (!init || init.error) {
    LOG('MCP initialize failed:', init && init.error && init.error.message)
    capture({ at: Date.now(), kind: 'door-init-failed', reason: String(init && init.error && init.error.message) })
    return false
  }
  await doorRpc('notifications/initialized', undefined, false)
  const listed = await doorRpc('tools/list', {})
  const tools = listed && listed.result && listed.result.tools
  if (!Array.isArray(tools)) {
    LOG('MCP tools/list failed -- typed tools unavailable')
    capture({ at: Date.now(), kind: 'door-tools-list-failed', reason: String((listed && listed.error && listed.error.message) || 'no tools array') })
    return false
  }
  door.tools = new Map(tools.map((t) => [t.name, t]))
  door.ready = true
  LOG(`MCP door ready: ${tools.length} tools; registering ${DOOR_TOOLS.length} curated`)
  capture({ at: Date.now(), kind: 'door-ready', tools: tools.length })
  return true
}

async function doorCall(toolName, args) {
  if (!door.ready) {
    return { text: 'akashic door is not running (see console log); the recall listeners are unaffected', isError: true }
  }
  const resp = await doorRpc('tools/call', { name: toolName, arguments: args ?? {} })
  if (!resp || resp.error) {
    return { text: `door error: ${(resp && resp.error && resp.error.message) || 'no response'}`, isError: true }
  }
  const r = resp.result || {}
  const text = Array.isArray(r.content)
    ? r.content.map((b) => (b && typeof b.text === 'string' ? b.text : '')).join('\n')
    : JSON.stringify(r, null, 2)
  return { text, isError: !!r.isError }
}

function translateSchema(schema) {
  const out = {}
  const props = (schema && schema.properties) || {}
  const required = (schema && schema.required) || []
  for (const [k, v] of Object.entries(props)) {
    if (!v || typeof v !== 'object') continue
    const param = {
      type: v.type === 'integer' ? 'number' : (v.type || 'string'),
      description: v.description || '',
    }
    if (required.includes(k)) param.required = true
    if (Array.isArray(v.enum)) param.enum = v.enum
    out[k] = param
  }
  return out
}

async function registerDoorTools(ctx) {
  if (!door.ready) return false
  try {
    for (const name of DOOR_TOOLS) {
      const t = door.tools.get(name)
      if (!t || !t.inputSchema) continue
      ctx.tools.register(defineTool({
        name: DOOR_PREFIX + name,
        description: `[Akashic door] ${t.description || name}`,
        parameters: translateSchema(t.inputSchema),
        output: {
          schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
              text: { type: 'string' },
              isError: { type: 'boolean' },
            },
          },
          render: (_args, value) => [{
            type: 'text',
            text: `${value.isError ? '[door error]\n' : ''}${value.text || '(no output)'}`,
          }],
        },
        async execute(args) {
          const result = await doorCall(name, args)
          if (result.isError) {
            // Report the door's error, never pretend it worked.
            return result
          }
          return result
        },
      }))
    }
    LOG(`registered ${DOOR_TOOLS.length} akashic_* door tools`)
    return true
  } catch (e) {
    LOG('tool registration failed:', e && e.message)
    capture({ at: Date.now(), kind: 'door-register-failed', reason: String(e && e.message) })
    return false
  }
}

export const name = 'dsh-akashic-recall'
export const inject = ['tools']   // REQUIRED by this fork: typed door tools. dsh-tools is
// mounted in the web profile's bundle (dump-config: id 'tools' -> @deepseek-ai/dsh-tools),
// so this inject is satisfiable; do NOT mount this plugin in a tools-less profile.

export async function apply(ctx) {
  applyCtx = ctx   // the self-heal path re-registers door tools after a respawn
  observeOnly = !!process.env.AKASHIC_AGENT_ID && process.env.AKASHIC_AGENT_ID !== SESSION_KEY
  if (observeOnly) {
    LOG(`OBSERVE-ONLY: AKASHIC_AGENT_ID=${process.env.AKASHIC_AGENT_ID} != ${SESSION_KEY}; injecting nothing, mis-attributing nothing`)
  }
  // Freshness probe -- fires at the exact moment someone believes they reloaded.
  try {
    const diskMtime = statSync(fileURLToPath(import.meta.url)).mtimeMs
    if (diskMtime > LOADED_MTIME) {
      LOG(`STALE GENERATION: module loaded at mtime ${LOADED_MTIME}, file on disk is newer (${diskMtime}) -- the running code is NOT the fixed code. REMEDY: restart the server (module code does not hot-reload; patch-row edits do)`)
      capture({ at: Date.now(), kind: 'freshness-drift', loadedMtime: LOADED_MTIME, diskMtime })
    }
  } catch {}
  // R1 static half
  let contextSuppressed = false
  try {
    const sp = ctx.systemPrompt
    if (sp && sp.config && sp.config.includeRuntimeContext === false) {
      contextSuppressed = true
      LOG('R1: includeRuntimeContext=false -- plan/recall contexts would be discarded; T5 contexts disabled')
    }
  } catch {}
  // R2: absence must be loud
  try {
    ctx.invariants.register('dsh-akashic-recall', {
      install(_, fail) {
        if (!listenerRegistered) fail('dsh-akashic-recall: tools/post-execute listener absent (R2)')
      },
    })
  } catch (e) {
    LOG('R2 invariant registration skipped:', e && e.message)
  }

  ctx.on('session/created', (session) => {
    firePresence('idle')
    const st = stateFor(session && session.id || activeSid())
    if (st && !st.whisperText) {
      spawnBridge(['boot-whisper', '--cwd', process.cwd() || '', '--agent-id', SESSION_KEY, '--session-id', session && session.id || activeSid()])
        .then((res) => { if (res && res.text) st.whisperText = res.text })
        .catch(() => {})
    }
  })

  ctx.on('session/event', (session, event) => {
    const sid = session && session.id || activeSid()
    const st = stateFor(sid)
    if (!st) return
    if (event && event.type === 'user/message') {
      st.lastPrompt = extractEventText(event)
      st.planPending = true
      firePresence('thinking')
    }
    if (st.probe && st.probe.pending) {
      st.probe.seen += 1
      if (eventHasToken(event, st.probe.token)) {
        st.probe = null // confirmed
      } else if (st.probe.seen > 3) {
        LOG(`R1: probe ${st.probe.token} not echoed in ${st.probe.seen} surface events -- CONTEXT DROPPED`)
        st.probe = null
      }
    }
    capture({ at: Date.now(), kind: 'session-event', type: event && event.type, sid })
  })

  ctx.on('tools/post-execute', async function (exec, result, next) {
    const decision = await next() // downstream settles first; we only enrich
    try {
      firePresence('tool-running')
      capture({
        at: Date.now(), kind: 'post-execute',
        tool: exec && typeof exec.name === 'string' ? exec.name : null,
        argKeys: exec && exec.arguments ? Object.keys(exec.arguments) : [],
        isError: !!(result && result.isError),
      })
      if (observeOnly) return decision
      // DRAFT KEEPALIVE (wired 2026-08-26): a hard-killed host must still leave a
      // fresh chronicles/last-session-draft.md. Fire-and-forget at every turn
      // boundary; the 600s throttle lives in the bridge (never blocks the tool
      // result, never raises into the listener). Kill switch AKASHIC_DRAFT_KEEPALIVE=0.
      spawnBridge(['draft-keepalive'], { await_: false })
      const { path, command } = extractTarget(exec && exec.arguments)
      if (!path && !command && !(result && result.isError)) return decision
      const sid = activeSid()
      const base = ['--session-key', SESSION_KEY, '--seen-key', sid]
      // V27 target-join law: outcome-credit gets the SAME --path/--command the
      // action-recall door got, so the bridge's normalize_target derivation matches
      // the surface impression byte-for-byte. NEVER pre-join a target here (the
      // 'path | command' join evaporated the impression join, pinned by
      // tests/test_dsh_contract.py).
      const targetArgs = [...(path ? ['--path', path] : []), ...(command ? ['--command', command] : [])]
      if (result && result.isError) {
        const credit = await spawnBridge(['outcome-credit', ...base, ...targetArgs, '--success', '0'])
        const rec = path || command
          ? await spawnBridge(['action-recall', ...base, ...(path ? ['--path', path] : []), ...(command ? ['--command', command] : [])])
          : null
        return attachContext(decision, [rec && rec.text, credit && credit.text].filter(Boolean).join('\n'))
      }
      const credit = await spawnBridge(['outcome-credit', ...base, ...targetArgs, '--success', '1'])
      if (credit && credit.text) return attachContext(decision, credit.text) // flip nudge wins the slot
      const rec = await spawnBridge(['action-recall', ...base, ...(path ? ['--path', path] : []), ...(command ? ['--command', command] : [])])
      return attachContext(decision, rec && rec.text)
    } catch {
      return decision // fail-open: recall must never alter a settled tool outcome
    }
  }, { prepend: true })

  ctx.on('system-prompt/assemble', async function (assembly, context, next) {
    const a = await next()
    try {
      if (observeOnly) return a
      const st = stateFor(activeSid())
      if (!st) return a
      if (!st.whisperInjected && st.whisperText) {
        a.sections = [...(a.sections ?? []), { name: 'akashic:whisper', text: st.whisperText }]
        st.whisperInjected = true
      }
      if (st.planPending && process.env.AKASHIC_PLAN_RECALL !== '0' && !contextSuppressed) {
        st.planPending = false
        const res = await spawnBridge(['plan-recall', '--session-key', SESSION_KEY, '--seen-key', activeSid(), '--prompt', st.lastPrompt || ''])
        if (res && res.text) {
          a.contexts = [...(a.contexts ?? []), { name: 'akashic:plan-recall', text: res.text }]
          st.probe = { pending: true, token: _probeToken(), seen: 0 }
        }
      }
      return a
    } catch {
      return a
    }
  }, { prepend: true })

  ctx.on('session/disposed', (session) => {
    firePresence('offline')
    spawnBridge(['session-end', '--session-id', session && session.id || activeSid()], { await_: false })
    const sid = session && session.id || activeSid()
    if (sid) sessions.delete(sid)
  })

  ctx.on('session/flush', () => {
    firePresence('offline')
  })

  listenerRegistered = true
  LOG('activated: five listeners registered; observeOnly =', observeOnly)

  // The typed door tools (fail-open: if the door cannot start, the listeners above
  // keep working and the seat simply lacks akashic_* tools until the next restart).
  try {
    const ready = await doorHandshake()
    if (ready) await registerDoorTools(ctx)
  } catch (e) {
    LOG('door bootstrap failed:', e && e.message)
    capture({ at: Date.now(), kind: 'door-bootstrap-failed', reason: String(e && e.message) })
  }
}
