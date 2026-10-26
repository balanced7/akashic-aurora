"use client";

import { ChevronRight } from "lucide-react";
import { memo, useLayoutEffect, useMemo, useRef, useState } from "react";

import { AgentAvatar } from "~/components/agent-avatar";
import {
  type BusMessage,
  type FeedItem,
  buildFeed,
  clockTime,
  displayName,
  epistemic,
  text,
  tone,
} from "~/lib/bifrost";
import { renderMarkdown } from "~/lib/markdown";
import { usePrefs } from "~/lib/prefs";
import { useConsole } from "~/lib/store";
import { cn, postJson } from "~/lib/utils";

/** Rows rendered at once; older history is one click away (the buffer holds the session). */
const WINDOW = 300;

const TONE_TEXT = {
  claude: "text-claude",
  deepseek: "text-deepseek",
  user: "text-user",
  system: "text-system",
} as const;

export function MessageLog() {
  const messages = useConsole((s) => s.messages);
  const thread = useConsole((s) => s.thread);
  const ready = useConsole((s) => s.ready);
  const bookkeeping = useConsole((s) => s.bookkeeping);
  const [limit, setLimit] = useState(WINDOW);
  const feed = useMemo(() => buildFeed(messages, thread), [messages, thread]);
  const visible = feed.slice(-limit);

  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [feed]);

  return (
    <div
      ref={scroller}
      onScroll={(e) => {
        const el = e.currentTarget;
        pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
      }}
      className="min-h-0 flex-1 overflow-y-auto px-5 py-4"
      aria-live="polite"
      aria-busy={!ready}
    >
      <div className="flex flex-col gap-3">
        {feed.length > visible.length && (
          <button
            type="button"
            onClick={() => setLimit((l) => l + WINDOW)}
            className="mx-auto cursor-pointer rounded-full border border-border bg-panel/70 px-3 py-1 text-xs text-muted hover:text-text"
          >
            Show {Math.min(WINDOW, feed.length - visible.length)} older
          </button>
        )}
        {!ready && feed.length === 0 && <p className="py-10 text-center text-sm text-faint">Connecting to the bus…</p>}
        {ready && feed.length === 0 && <p className="py-10 text-center text-sm text-faint">No messages yet.</p>}
        {visible.map((item) => (
          // the wrapper is the anchor the rail's chapters scroll to
          <div key={item.key} data-feed-key={item.key}>
            <FeedRow item={item} />
          </div>
        ))}
        {bookkeeping.count > 0 && (
          <p className="text-center text-[11px] text-faint" title={`latest: ${bookkeeping.last}`}>
            {bookkeeping.count} bookkeeping event{bookkeeping.count === 1 ? "" : "s"} hidden (triage, ack, stale)
          </p>
        )}
      </div>
    </div>
  );
}

const FeedRow = memo(function FeedRow({ item }: { item: FeedItem }) {
  switch (item.type) {
    case "traces":
      return <TraceCard agent={item.agent} traces={item.traces} />;
    case "system":
      return <SystemLine m={item.m} />;
    case "verdict":
      return <SystemLine m={item.m} prefix={`Round ${item.m.meta?.verdict ?? "amber"}: `} guard />;
    case "message":
      return <Message m={item.m} />;
  }
});

function SystemLine({ m, prefix = "", guard }: { m: BusMessage; prefix?: string; guard?: boolean }) {
  const body = text(m);
  const isGuard = guard || /loop-guard/i.test(body);
  const from = m.from && m.from !== "system" ? m.from : "";
  return (
    <div
      className={cn(
        "mx-auto max-w-[85%] rounded-lg px-3 py-1 text-center text-[12.5px] text-muted",
        isGuard && "border border-amber/30 bg-amber/10 text-amber",
      )}
    >
      {from && <span className="font-semibold">{displayName(from, useConsole.getState().status?.residents)}: </span>}
      {prefix}
      {body}
    </div>
  );
}

function TraceCard({ agent, traces }: { agent: string; traces: BusMessage[] }) {
  const residents = useConsole((s) => s.status?.residents);
  // null follows the Traces setting; a click pins this card open or shut
  const [pinned, setOpen] = useState<boolean | null>(null);
  const expanded = usePrefs((s) => s.tracesExpanded);
  const open = pinned ?? expanded;
  const last = text(traces[traces.length - 1] ?? {});
  return (
    <div className="ml-11 rounded-lg border border-border/70 bg-panel/40 text-[12.5px]">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-2 px-3 py-1.5 text-left text-muted hover:text-text"
      >
        <ChevronRight className={cn("size-3.5 shrink-0 transition-transform", open && "rotate-90")} />
        <span className={cn("shrink-0 font-semibold", TONE_TEXT[tone(agent)])}>{displayName(agent, residents)}</span>
        <span className="shrink-0">
          {traces.length} trace{traces.length === 1 ? "" : "s"}
        </span>
        {!open && <span className="truncate text-faint">{last}</span>}
      </button>
      {open && (
        <ol className="max-h-80 overflow-y-auto border-t border-border/70 px-3 py-2 font-mono text-[11.5px] leading-relaxed text-muted">
          {traces.map((t, i) => (
            <li key={i} className="flex gap-2">
              <span className="shrink-0 text-faint">{clockTime(t.ts)}</span>
              <span className="whitespace-pre-wrap">{text(t)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Message({ m }: { m: BusMessage }) {
  const residents = useConsole((s) => s.status?.residents);
  const setThread = useConsole((s) => s.setThread);
  const from = m.from ?? "system";
  const me = from === "user";
  const epi = epistemic(m);
  const html = useMemo(() => renderMarkdown(text(m)), [m]);
  const intent = m.meta?.intent;

  return (
    <div className={cn("flex gap-3", me && "flex-row-reverse")}>
      <AgentAvatar id={from} />
      <div
        className={cn(
          "min-w-0 max-w-[min(760px,85%)] rounded-2xl border px-3.5 py-2 shadow-[0_2px_14px_rgba(0,0,0,.18)]",
          me ? "rounded-tr-md border-user/25 bg-user/[.07]" : "rounded-tl-md border-glass-line bg-panel/75",
        )}
      >
        <div className="mb-0.5 flex flex-wrap items-center gap-x-2 text-xs">
          <button
            type="button"
            disabled={me}
            onClick={() => setThread(from)}
            title={me ? undefined : `Talk 1:1 with ${displayName(from, residents)}`}
            className={cn("font-semibold enabled:cursor-pointer enabled:hover:underline", TONE_TEXT[tone(from)])}
          >
            {displayName(from, residents)}
          </button>
          {m.to && m.to !== "all" && !me && <span className="text-faint">→ {displayName(m.to, residents)}</span>}
          {me && m.to && <span className="text-faint">→ {m.to === "all" ? "everyone" : displayName(m.to, residents)}</span>}
          <span className="text-faint">{clockTime(m.ts)}</span>
          <span className="text-faint" title={epi.tier === "unknown" ? "no currency stamp, status unknown" : epi.tier}>
            {epi.glyph}
          </span>
          {epi.marker && <span className="text-amber">{epi.marker}</span>}
          {intent && intent !== "chat" && (
            <span className="rounded border border-border px-1 text-[10.5px] uppercase tracking-wide text-muted" title={m.meta?.why}>
              {intent}
            </span>
          )}
          {!!m.meta?.hops && <span className="text-faint">hop {m.meta.hops}</span>}
          {m.meta?.source === "discord" && <span className="text-accent2">via Discord</span>}
        </div>
        <MessageBody html={html} />
      </div>
    </div>
  );
}

/** Markdown body; code blocks carry Copy and (for py/pytest commands) a safe Run via /lib/run. */
function MessageBody({ html }: { html: string }) {
  async function onClick(e: React.MouseEvent) {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-act]");
    const host = btn?.closest(".code-host");
    if (!btn || !host) return;
    const code = host.querySelector("pre code")?.textContent ?? "";
    if (btn.dataset.act === "copy") {
      await navigator.clipboard?.writeText(code);
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = "Copy"), 1400);
      return;
    }
    host.querySelector(".code-run-result")?.remove();
    btn.textContent = "Running…";
    const out = document.createElement("div");
    out.className = "code-run-result";
    try {
      const res = await postJson<{ ok: boolean; argv?: string[]; exit?: number; output?: string; refused?: string }>(
        "/lib/run",
        { command: code.trim().replace(/^>\s*/, "") },
      );
      if (res.ok) out.textContent = `$ ${(res.argv ?? []).join(" ")}\n[exit ${res.exit}]\n${res.output ?? ""}`;
      else {
        out.dataset.refused = "";
        out.textContent = `Refused: ${res.refused ?? "unknown reason"}`;
      }
    } catch (err) {
      out.dataset.refused = "";
      out.textContent = `Run failed: ${String(err)}`;
    }
    btn.textContent = "▶ Run";
    host.appendChild(out);
  }
  // renderMarkdown escapes all raw HTML and drops unsafe URLs (lib/markdown.ts).
  return <div className="prose-bus text-[14.5px]" onClick={onClick} dangerouslySetInnerHTML={{ __html: html }} />;
}
