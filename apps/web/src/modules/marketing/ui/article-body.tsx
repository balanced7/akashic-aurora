import { MDXContent } from "@content-collections/mdx/react";

/** MDX body styled for the dark marketing canvas. */
export const ArticleBody = ({ mdx }: { mdx: string }) => (
  <div
    data-testid="article-body"
    className="prose prose-invert prose-lg prose-headings:font-semibold prose-headings:tracking-tight prose-h2:mt-14 prose-h2:text-[28px] prose-p:leading-relaxed prose-a:underline-offset-4 prose-code:rounded-md prose-code:border prose-code:border-white/10 prose-code:bg-white/[0.06] prose-code:px-1.5 prose-code:py-0.5 prose-code:font-normal prose-code:before:content-none prose-code:after:content-none prose-pre:rounded-2xl prose-pre:border prose-pre:border-white/[0.08] prose-pre:bg-[#07080a] max-w-none [--tw-prose-body:rgb(255_255_255/0.72)] [--tw-prose-bold:#fff] [--tw-prose-bullets:var(--color-hud-gold)] [--tw-prose-code:#fff] [--tw-prose-headings:#fff] [--tw-prose-links:#fff] [--tw-prose-quotes:#fff]"
  >
    <MDXContent code={mdx} />
  </div>
);
