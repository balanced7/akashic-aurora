import { llms, loader, type LoaderPlugin } from 'fumadocs-core/source';
import { createElement } from 'react';
import { icons } from 'lucide-react';
import { AuroraIcon, isAuroraIcon } from '@/components/aurora-icon';
import { docsContentRoute, docsImageRoute, docsRoute } from './shared';
import { defineDocs } from 'fumadocs-mdx/macro';
import { metaSchema, pageSchema } from 'fumadocs-core/source/schema';
import { remarkMdxMermaid } from 'fumadocs-core/mdx-plugins/remark-mdx-mermaid';
import { applyMdxPreset } from 'fumadocs-mdx/config';

const docs = defineDocs({
  dir: 'content/docs',
  docs: {
    schema: pageSchema,
    // Setting mdxOptions drops the defaults, so apply the preset and add the plugin to it.
    mdxOptions: applyMdxPreset({
      remarkPlugins: (plugins) => [...plugins, remarkMdxMermaid],
    }),
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
  meta: {
    schema: metaSchema,
  },
});

type IconNode = { icon?: unknown };

// A meta.json `icon` names a section icon (see components/aurora-icon.tsx) or, failing that, a Lucide icon.
function iconsPlugin(): LoaderPlugin {
  function replaceIcon<T extends IconNode>(node: T): T {
    const name = node.icon;
    if (typeof name !== 'string') return node;
    if (isAuroraIcon(name)) {
      node.icon = createElement(AuroraIcon, { name, size: 16 });
    } else if (name in icons) {
      node.icon = createElement(icons[name as keyof typeof icons]);
    } else {
      console.warn(`[icons] Unknown icon: ${name}.`);
      node.icon = undefined;
    }
    return node;
  }
  return {
    name: 'aurora:icons',
    transformPageTree: { file: replaceIcon, folder: replaceIcon, separator: replaceIcon },
  };
}

// See https://fumadocs.dev/docs/headless/source-api for more info
export const source = loader({
  baseUrl: docsRoute,
  source: docs.toFumadocsSource(),
  plugins: [iconsPlugin()],
});

export const docsLlms = llms(source, {
  renderPage: async (page) => `# ${page.data.title} (${page.url})

${await page.data.getText('processed')}`,
});
