import { MDXContent } from "@content-collections/mdx/react";
import { Children, isValidElement } from "react";

import { slugify } from "./toc";

import type { ComponentProps, ReactNode } from "react";

/** The text a reader sees in a heading, for its anchor id. */
const textOf = (node: ReactNode): string =>
  Children.toArray(node)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") {
        return String(child);
      }
      if (isValidElement<{ children?: ReactNode }>(child)) {
        return textOf(child.props.children);
      }
      return "";
    })
    .join("");

const components = {
  h2: ({ children, ...props }: ComponentProps<"h2">) => (
    <h2 id={slugify(textOf(children))} {...props}>
      {children}
    </h2>
  ),
  table: (props: ComponentProps<"table">) => (
    <div className="overflow-x-auto" tabIndex={0} role="region">
      <table {...props} />
    </div>
  ),
};

/**
 * A walk's MDX body, set for long reading on the dark canvas: a ~68ch measure, generous
 * leading, tables that scroll instead of spilling, and a quieter reference list.
 */
export const WalkBody = ({ mdx }: { mdx: string }) => (
  <div
    data-testid="walk-body"
    className="prose prose-invert prose-lg prose-headings:font-semibold prose-headings:tracking-tight prose-headings:scroll-mt-28 prose-h2:mt-16 prose-h2:text-[28px] prose-h2:leading-tight prose-p:leading-[1.75] prose-li:leading-[1.7] prose-a:underline-offset-4 prose-a:decoration-white/30 hover:prose-a:decoration-white prose-strong:font-semibold prose-code:rounded-md prose-code:border prose-code:border-white/10 prose-code:bg-white/[0.06] prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[0.85em] prose-code:font-normal prose-code:before:content-none prose-code:after:content-none prose-pre:rounded-2xl prose-pre:border prose-pre:border-white/[0.08] prose-pre:bg-[#07080a] prose-blockquote:border-l-hud-gold prose-blockquote:font-normal prose-blockquote:not-italic prose-blockquote:text-white/85 prose-table:my-0 prose-table:text-[15px] prose-th:whitespace-nowrap prose-th:text-white prose-td:align-top max-w-[68ch] [--tw-prose-body:rgb(255_255_255/0.74)] [--tw-prose-bold:#fff] [--tw-prose-bullets:var(--color-hud-gold)] [--tw-prose-code:#fff] [--tw-prose-counters:rgb(255_255_255/0.45)] [--tw-prose-headings:#fff] [--tw-prose-links:#fff] [--tw-prose-quotes:#fff] [--tw-prose-td-borders:rgb(255_255_255/0.08)] [--tw-prose-th-borders:rgb(255_255_255/0.16)] [&_h2#references+ol]:text-[14px] [&_h2#references+ol]:leading-relaxed [&_h2#references+ol]:[overflow-wrap:anywhere] [&_h2#references+ol_li]:my-1.5 [&>div[role=region]]:my-8"
  >
    <MDXContent code={mdx} components={components} />
  </div>
);
