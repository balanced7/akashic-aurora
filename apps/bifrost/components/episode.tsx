"use client";

import { BookOpen, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { create } from "zustand";

import { Button } from "~/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { useNow } from "~/lib/use-now";
import { cn, postJson, single } from "~/lib/utils";

/** /episode/current: the titled stretch of this session in progress (session bookends, S4). */
type Suggestion = { title?: string; description?: string; why?: string; reason: string; confidence?: number };
type Chapter = {
  id: string;
  title: string;
  started: string;
  duration_seconds: number;
  beats_count: number;
  suggestion: Suggestion | null;
};
type Draft = { chapter_id: string; title?: string; description?: string; why?: string };

/** Episode state moves at human pace, so it polls slowly. */
const POLL_MS = 15_000;
const IGNORE_KEY = "bifrost_epi_ignore";

type EpisodeState = {
  chapter: Chapter | null;
  draft: Draft | null;
  /** Bumped when a suggestion is suppressed, so the banner re-reads localStorage. */
  suppressed: number;
};
const useEpisode = create<EpisodeState>(() => ({ chapter: null, draft: null, suppressed: 0 }));

const poll = single(async () => {
  try {
    const r = await fetch("/episode/current", { cache: "no-store" });
    const j = (await r.json()) as { current_chapter: Chapter | null };
    useEpisode.setState({ chapter: j.current_chapter ?? null });
  } catch {
    useEpisode.setState({ chapter: null });
  }
});

export function useEpisodePoll() {
  useEffect(() => {
    void poll();
    const t = setInterval(() => void poll(), POLL_MS);
    return () => clearInterval(t);
  }, []);
}

export function fmtDuration(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${Math.floor(s / 3600)}h${Math.round((s % 3600) / 60)}m`;
}

// The suggestion is advisory: Ignore hides this one suggestion for a day, Continue for ten minutes.
const ignoreKey = (c: Chapter, s: Suggestion) => `${c.id}|${s.reason}|${s.title ?? ""}`;
function ignoredUntil(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(IGNORE_KEY) ?? "{}") as Record<string, number>;
  } catch {
    return {};
  }
}
function suppress(c: Chapter, s: Suggestion, ms: number) {
  const m = ignoredUntil();
  m[ignoreKey(c, s)] = Date.now() + ms;
  localStorage.setItem(IGNORE_KEY, JSON.stringify(m));
  useEpisode.setState((st) => ({ suppressed: st.suppressed + 1 }));
}

async function endEpisode() {
  try {
    const r = await postJson<{ draft: Draft | null; error?: string }>("/episode/close");
    if (r.draft) useEpisode.setState({ draft: r.draft });
    else toast.error(r.error ?? "The episode layer returned no draft.");
  } catch {
    toast.error("Could not end the episode. Is the console backend offline?");
  }
  void poll();
}

/** Header chip: the current episode's title and age; opens the panel to end and title it. */
export function EpisodeChip() {
  const chapter = useEpisode((s) => s.chapter);
  const draft = useEpisode((s) => s.draft);
  const [open, setOpen] = useState(false);
  const title = chapter?.title || "untitled episode";
  return (
    <Popover
      open={open || !!draft}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) useEpisode.setState({ draft: null });
      }}
    >
      <PopoverTrigger asChild>
        <Button variant="ghost" title="Current episode: a titled stretch of this session" className="max-w-56">
          <BookOpen />
          <span className="truncate">{chapter ? title : "episode"}</span>
          {chapter && <span className="text-[11px] font-normal text-faint">{fmtDuration(chapter.duration_seconds)}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[400px]">
        <div className="mb-1 flex items-center gap-2">
          <b className="text-[13px]">Current episode</b>
          <span className="flex-1" />
          {chapter && !draft && (
            <Button size="sm" variant="warn" onClick={() => void endEpisode()}>
              <Square />
              End episode
            </Button>
          )}
        </div>
        <p className="text-xs text-faint">A titled, confined stretch of this session: what happened and why.</p>
        {chapter ? (
          <p className="mt-2 text-xs text-muted">
            started {new Date(chapter.started).toLocaleString([], { dateStyle: "short", timeStyle: "short" })} ·{" "}
            {fmtDuration(chapter.duration_seconds)} · {chapter.beats_count} beats
            {chapter.suggestion &&
              ` · suggestion: ${chapter.suggestion.reason} (${Math.round((chapter.suggestion.confidence ?? 0) * 100)}%)`}
          </p>
        ) : (
          <p className="mt-2 text-xs text-amber">No episode open, or the episode layer is unavailable.</p>
        )}
        {draft && <DraftForm key={draft.chapter_id} draft={draft} />}
      </PopoverContent>
    </Popover>
  );
}

const FIELD = "w-full rounded-lg border border-border bg-bg/60 px-2.5 py-1.5 text-[13px] text-text outline-none focus:border-accent/60";

function DraftForm({ draft }: { draft: Draft }) {
  const [title, setTitle] = useState(draft.title ?? "");
  const [description, setDescription] = useState(draft.description ?? "");
  const [why, setWhy] = useState(draft.why ?? "");
  async function accept() {
    try {
      const r = await postJson<{ error?: string }>("/episode/accept", { chapter_id: draft.chapter_id, title, description, why });
      if (r.error) toast.error(r.error);
      else toast.success(`Episode closed: ${title || "untitled"}`);
    } catch {
      toast.error("Could not accept the episode. Is the console backend offline?");
    }
    useEpisode.setState({ draft: null });
    void poll();
  }
  return (
    <form
      className="mt-3 space-y-2 border-t border-border pt-3"
      onSubmit={(e) => {
        e.preventDefault();
        void accept();
      }}
    >
      <label className="block text-[11px] font-semibold text-muted">
        Title
        <input className={cn(FIELD, "mt-1")} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="what this stretch was" />
      </label>
      <label className="block text-[11px] font-semibold text-muted">
        Description
        <textarea className={cn(FIELD, "mt-1 h-16 resize-y")} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="what happened" />
      </label>
      <label className="block text-[11px] font-semibold text-muted">
        Why
        <textarea className={cn(FIELD, "mt-1 h-14 resize-y")} value={why} onChange={(e) => setWhy(e.target.value)} placeholder="the intent behind it" />
      </label>
      <div className="flex items-center gap-1.5">
        <span className="mr-auto text-[11px] text-faint">Review the draft, edit any field, then accept.</span>
        <Button size="sm" variant="ghost" onClick={() => useEpisode.setState({ draft: null })}>
          Later
        </Button>
        <Button size="sm" variant="primary" type="submit">
          Accept
        </Button>
      </div>
    </form>
  );
}

/** The advisory "end this episode?" banner. Only Accept closes anything. */
export function EpisodeBanner() {
  const chapter = useEpisode((s) => s.chapter);
  const draft = useEpisode((s) => s.draft);
  useEpisode((s) => s.suppressed);
  const now = useNow(60_000);
  const s = chapter?.suggestion;
  if (!chapter || !s || draft) return null;
  if ((ignoredUntil()[ignoreKey(chapter, s)] ?? 0) > now) return null;
  async function accept() {
    try {
      // one shot: close with the suggested fields and finalize (the contract's agent path)
      await postJson("/episode/close", { title: s!.title, description: s!.description, why: s!.why, finalize: true });
      toast.success(`Episode closed: ${s!.title || "untitled"}`);
    } catch {
      toast.error("Could not close the episode.");
    }
    void poll();
  }
  return (
    <div role="status" className="mx-4 mt-2 flex items-center gap-2 rounded-xl border border-accent2/30 bg-accent2/10 px-3.5 py-2 text-[13px]">
      <BookOpen className="size-4 shrink-0 text-accent2" />
      <span className="min-w-0 truncate">
        Suggested: end this episode as <b>{s.title || "untitled"}</b>
        <span className="text-faint">
          {" "}
          · {s.reason} · {Math.round((s.confidence ?? 0) * 100)}%
        </span>
      </span>
      <span className="flex-1" />
      <Button size="sm" variant="primary" onClick={() => void accept()}>
        Accept
      </Button>
      <Button size="sm" variant="ghost" onClick={() => suppress(chapter, s, 24 * 3600_000)}>
        Ignore
      </Button>
      <Button size="sm" variant="ghost" onClick={() => suppress(chapter, s, 10 * 60_000)}>
        Continue
      </Button>
    </div>
  );
}
