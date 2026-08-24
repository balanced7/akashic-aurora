// dsh-akashic-recall — the five-listener adapter (sealed fence t383-dsh-adapter).
// STILL UNWIRED: no cordis.patch.yml entry / profile dependency until the cold
// start (wiring rides the same fresh session as the T1 receipt).
//
// Listeners and their sealed tier mapping:
//   session/created        -> T2 trigger: boot whisper fetched, presence idle
//   system-prompt/assemble -> T2 injection (whisper as a SECTION, survives R1
//                             suppression) + T5 derived (plan recall as a CONTEXT)
//   session/event          -> T5 trigger (user/message) + R1 probe confirmation
//   tools/post-execute     -> T3 one-beat-late (recall contexts) + T4 DIRECT
//                             (isError => FAIL half, then retry recall; success
//                             => resolve; flip => nudge context)
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
import { appendFileSync, mkdirSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const BRIDGE = join(PLUGIN_DIR, '..', 'bridge.py')
const SESSION_KEY = 'dsh_agent'
const CAP_DIR = join(tmpdir(), 'akashic_recall', 'payloads_dsh')
const LOG = (...a) => console.log('[dsh-akashic-recall]', ...a)

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

export const name = 'dsh-akashic-recall'
// NO inject export: this cordis fork treats every declared inject as REQUIRED
// (_refresh goes INACTIVE on any missing key — no optional mechanism exists), and
// invariants/systemPrompt are not mounted in every profile. The R2 invariant check
// therefore registers via try/catch and logs 'skipped' where the service is absent;
// the WEB wiring gives R2 its real home (a config-level inject there, where
// dsh-invariants is mounted). Drilled 2026-08-24: with an inject export the plugin
// sat 'pending (waiting for service)' in headless and the whole tree refused to boot.

export function apply(ctx) {
  observeOnly = !!process.env.AKASHIC_AGENT_ID && process.env.AKASHIC_AGENT_ID !== SESSION_KEY
  if (observeOnly) {
    LOG(`OBSERVE-ONLY: AKASHIC_AGENT_ID=${process.env.AKASHIC_AGENT_ID} != ${SESSION_KEY}; injecting nothing, mis-attributing nothing`)
  }
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
      const { path, command } = extractTarget(exec && exec.arguments)
      if (!path && !command && !(result && result.isError)) return decision
      const sid = activeSid()
      const base = ['--session-key', SESSION_KEY, '--seen-key', sid]
      const target = [path, command].filter(Boolean).join(' | ') || 'unknown'
      if (result && result.isError) {
        const credit = await spawnBridge(['outcome-credit', ...base, '--target', target, '--success', '0'])
        const rec = path || command
          ? await spawnBridge(['action-recall', ...base, ...(path ? ['--path', path] : []), ...(command ? ['--command', command] : [])])
          : null
        return attachContext(decision, [rec && rec.text, credit && credit.text].filter(Boolean).join('\n'))
      }
      const credit = await spawnBridge(['outcome-credit', ...base, '--target', target, '--success', '1'])
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
}
