import { Plus } from "lucide-react";

import type { FaqItem } from "~/modules/marketing/content/faq";

/** Native <details> accordion: works without JavaScript and keeps answers crawlable. */
export const FaqList = ({ items }: { items: readonly FaqItem[] }) => (
  <div
    data-testid="faq"
    className="flex flex-col divide-y divide-white/[0.07] border-y border-white/[0.07]"
  >
    {items.map((item) => (
      <details key={item.question} className="group py-5">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-[17px] font-medium text-white [&::-webkit-details-marker]:hidden">
          {item.question}
          <Plus className="size-4 shrink-0 text-white/50 transition-transform duration-300 group-open:rotate-45" />
        </summary>
        <p className="text-mk-muted mt-3 max-w-3xl text-[15.5px] leading-relaxed">
          {item.answer}
        </p>
      </details>
    ))}
  </div>
);
