"use client";

import { Check, Paperclip, SendHorizontal, TriangleAlert } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { AgentAvatar } from "~/components/agent-avatar";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { FIDELITY_LABEL, type Fidelity, displayName } from "~/lib/bifrost";
import { rosterOf, useConsole } from "~/lib/store";
import { cn, postJson } from "~/lib/utils";

/** How long a broadcast stays armed after the first Enter (Daniil 2026-08-24: accidental broadcasts). */
const ARM_MS = 4000;

const FIDELITIES: { id: Fidelity; label: string; hint: string }[] = [
  { id: "inform", label: "Inform", hint: "adopted at the agent's next turn" },
  { id: "steer", label: "Steer", hint: "folded into the current task, no stop (one agent)" },
  { id: "interrupt", label: "Interrupt", hint: "drop the current task and switch (one agent)" },
];

type SendResult = { ok?: boolean; launched?: string[]; seat?: string; msg?: string };

export function Composer() {
  const status = useConsole((s) => s.status);
  const recipients = useConsole((s) => s.recipients);
  const fidelity = useConsole((s) => s.fidelity);
  const setFidelity = useConsole((s) => s.setFidelity);
  const [value, setValue] = useState("");
  const [armed, setArmed] = useState(false);
  const armTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const fileInput = useRef<HTMLInputElement>(null);

  const roster = rosterOf(status);
  const broadcast = recipients.length === 1 && recipients[0] === "all";
  const targets = broadcast ? roster : recipients;

  function disarm() {
    setArmed(false);
    clearTimeout(armTimer.current);
  }

  async function send() {
    const body = value.trim();
    if (!body) return;
    if (fidelity !== "inform" && (broadcast || targets.length !== 1)) {
      toast.warning(`Pick one agent to ${fidelity}; it targets a single seat.`);
      return;
    }
    setValue("");
    const sendTo = broadcast ? ["all"] : targets;
    try {
      const results = await Promise.all(
        sendTo.map((to) => postJson<SendResult>("/send", { text: body, to, fidelity, ns: useConsole.getState().room })),
      );
      const failed = results.some((r) => !r.ok);
      const launched = results.flatMap((r) => r.launched ?? []);
      const notes = results.map((r) => (fidelity === "steer" ? r.msg : r.seat)).filter(Boolean);
      const who = broadcast ? "everyone" : sendTo.map((id) => displayName(id, status?.residents)).join(", ");
      if (failed) toast.error(`Send to ${who} failed. Is the bus offline?`);
      else
        toast.success(`${capitalize(FIDELITY_LABEL[fidelity])}: ${who}`, {
          description: [launched.length ? `auto-launched ${launched.join(", ")}` : "", ...notes].filter(Boolean).join(" · ") || undefined,
        });
    } catch {
      toast.error("Send failed. Is the bus offline?");
      setValue(body);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Escape") return disarm();
    if (e.key !== "Enter" || e.shiftKey) {
      if (armed) disarm(); // typing drops the arm so a half-thought is never broadcast
      return;
    }
    e.preventDefault();
    if (broadcast && !armed && value.trim()) {
      setArmed(true);
      toast.warning(`Broadcast to ${roster.length} agent${roster.length === 1 ? "" : "s"}? Press Enter again to send.`, {
        duration: ARM_MS,
      });
      armTimer.current = setTimeout(() => setArmed(false), ARM_MS);
      return;
    }
    disarm();
    void send();
  }

  async function uploadFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) await uploadFile(file);
  }

  return (
    <div
      className="mx-3 mb-3 shrink-0 rounded-lg border border-glass-line bg-glass px-5 pt-3 pb-4 backdrop-blur-[26px]"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) void uploadFiles(e.dataTransfer.files);
      }}
    >
      <div className="mb-2 flex items-center gap-2">
        <div role="radiogroup" aria-label="Delivery" className="flex rounded-lg border border-border bg-panel/70 p-0.5">
          {FIDELITIES.map((f) => (
            <button
              key={f.id}
              type="button"
              role="radio"
              aria-checked={fidelity === f.id}
              title={f.hint}
              onClick={() => setFidelity(f.id)}
              className={cn(
                "cursor-pointer rounded-md px-2.5 py-1 text-xs font-semibold text-muted transition hover:text-text",
                fidelity === f.id && f.id === "inform" && "bg-ok/15 text-ok",
                fidelity === f.id && f.id === "steer" && "bg-accent/15 text-accent",
                fidelity === f.id && f.id === "interrupt" && "bg-danger/15 text-danger",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="truncate text-xs text-faint">{FIDELITIES.find((f) => f.id === fidelity)?.hint}</span>
      </div>
      <div className="flex items-end gap-2 rounded-2xl border border-border bg-panel/80 p-1.5 focus-within:border-accent/45">
        <RecipientPicker roster={roster} />
        <textarea
          rows={1}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={onKeyDown}
          onPaste={(e) => {
            const files = Array.from(e.clipboardData.files);
            if (files.length) {
              e.preventDefault();
              void uploadFiles(files);
            }
          }}
          placeholder="Message the agents… (Enter to send, Shift+Enter for a new line)"
          aria-label="Message"
          className="max-h-40 min-h-9 flex-1 resize-none bg-transparent px-1.5 py-1.5 text-[14.5px] outline-none placeholder:text-faint"
        />
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) void uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          title="Share a file into the project (or drop / paste it here)"
          className="grid size-9 shrink-0 cursor-pointer place-items-center rounded-xl text-muted hover:bg-white/5 hover:text-text"
        >
          <Paperclip className="size-4" />
          <span className="sr-only">Attach file</span>
        </button>
        <button
          type="button"
          onClick={() => {
            disarm();
            void send();
          }}
          disabled={!value.trim()}
          title={armed ? "Broadcast armed" : "Send"}
          className={cn(
            "grid size-9 shrink-0 cursor-pointer place-items-center rounded-xl bg-accent text-[#0b0c10] transition hover:brightness-110 disabled:cursor-default disabled:opacity-40",
            armed && "bg-amber",
          )}
        >
          {armed ? <TriangleAlert className="size-4" /> : <SendHorizontal className="size-4" />}
          <span className="sr-only">Send</span>
        </button>
      </div>
    </div>
  );
}

function RecipientPicker({ roster }: { roster: string[] }) {
  const recipients = useConsole((s) => s.recipients);
  const residents = useConsole((s) => s.status?.residents);
  const toggleRecipient = useConsole((s) => s.toggleRecipient);
  const broadcast = recipients.length === 1 && recipients[0] === "all";
  const shown = broadcast ? roster : recipients;
  const label = broadcast
    ? "Everyone"
    : shown.length === 1
      ? displayName(shown[0]!, residents)
      : `${shown.length} agents`;

  return (
    <Popover>
      <PopoverTrigger
        title="Who receives your message"
        aria-label={`Recipients: ${label}`}
        className="flex h-9 shrink-0 cursor-pointer items-center gap-2 rounded-xl px-2 hover:bg-white/5"
      >
        <span className="flex -space-x-1.5">
          {shown.slice(0, 4).map((id) => (
            <AgentAvatar key={id} id={id} className="size-6 rounded-lg text-[11px] ring-2 ring-panel" />
          ))}
        </span>
        <span className="max-w-36 truncate text-[13px] font-semibold">{label}</span>
      </PopoverTrigger>
      <PopoverContent className="w-64" onOpenAutoFocus={(e) => e.preventDefault()}>
        <RecipientRow selected={broadcast} onSelect={() => toggleRecipient("all", false)}>
          <div className="grid size-6 place-items-center rounded-lg bg-[linear-gradient(140deg,#7aa2f7,#48e6bf)] text-[11px] font-bold text-[#0b0c10]">
            *
          </div>
          Everyone
        </RecipientRow>
        {roster.map((id) => (
          <RecipientRow
            key={id}
            selected={!broadcast && recipients.includes(id)}
            onSelect={(additive) => toggleRecipient(id, additive)}
          >
            <AgentAvatar id={id} className="size-6 rounded-lg text-[11px]" />
            {displayName(id, residents)}
          </RecipientRow>
        ))}
        <p className="px-2 pt-1.5 pb-0.5 text-[11px] text-faint">Shift- or Ctrl-click to pick several.</p>
      </PopoverContent>
    </Popover>
  );
}

function RecipientRow({
  selected,
  onSelect,
  children,
}: {
  selected: boolean;
  onSelect: (additive: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={selected}
      onClick={(e) => onSelect(e.shiftKey || e.ctrlKey || e.metaKey)}
      className={cn(
        "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] hover:bg-white/5",
        selected && "bg-accent/10",
      )}
    >
      {children}
      {selected && <Check className="ml-auto size-3.5 text-accent" />}
    </button>
  );
}

async function uploadFile(file: File) {
  const content_b64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
  try {
    const res = await postJson<{ ok: boolean; path?: string; error?: string }>("/upload", {
      name: file.name || "pasted.png",
      content_b64,
    });
    if (res.ok) toast.success(`Shared ${res.path}`, { description: "Agents can read it with their tools." });
    else toast.error(`Upload failed: ${res.error ?? "unknown error"}`);
  } catch {
    toast.error("Upload failed. Is the console backend up?");
  }
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
