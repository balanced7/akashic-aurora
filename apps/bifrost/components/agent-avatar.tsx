import { avatarInfo } from "~/lib/bifrost";
import { useConsole } from "~/lib/store";
import { cn } from "~/lib/utils";

export function AgentAvatar({ id, className }: { id: string; className?: string }) {
  const residents = useConsole((s) => s.status?.residents);
  const v = avatarInfo(id, residents);
  return (
    <div
      aria-hidden
      className={cn(
        "grid size-8 shrink-0 place-items-center rounded-[10px] text-[13px] font-bold text-[#0b0c10] shadow-[0_2px_10px_rgba(0,0,0,.3)]",
        className,
      )}
      style={{ background: `linear-gradient(140deg, ${v.a}, ${v.b})` }}
    >
      {v.letter}
    </div>
  );
}
