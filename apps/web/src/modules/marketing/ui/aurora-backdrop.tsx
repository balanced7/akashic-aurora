import { cn } from "@akashic-labs/ui";

/** Slow curtains of light behind hero sections. Pure CSS, no client JS. */
export const AuroraBackdrop = ({
  className,
  intensity = 1,
}: {
  className?: string;
  intensity?: number;
}) => (
  <div
    aria-hidden
    className={cn(
      "pointer-events-none absolute inset-0 overflow-hidden",
      className,
    )}
  >
    <div className="mk-grid-bg absolute inset-0 opacity-60" />
    <div
      className="animate-mk-aurora absolute -top-[30%] left-[10%] h-[70%] w-[80%] rounded-[50%] blur-[90px]"
      style={{
        opacity: 0.55 * intensity,
        background:
          "conic-gradient(from 200deg at 50% 50%, rgb(10 200 185 / 0.55), rgb(3 151 171 / 0.15), rgb(200 170 110 / 0.35), rgb(10 200 185 / 0.55))",
      }}
    />
    <div
      className="animate-mk-aurora absolute -top-[20%] right-[-10%] h-[50%] w-[45%] rounded-[50%] blur-[100px] [animation-delay:-9s]"
      style={{
        opacity: 0.4 * intensity,
        background:
          "radial-gradient(circle, rgb(120 90 220 / 0.45), transparent 70%)",
      }}
    />
    <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-b from-transparent to-black" />
  </div>
);
