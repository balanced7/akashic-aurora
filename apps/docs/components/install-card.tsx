'use client';

import { useEffect, useState } from 'react';
import { CodeBlock, Pre } from 'fumadocs-ui/components/codeblock';
import { cn } from '@/lib/cn';

const RELEASES = 'https://github.com/balanced7/akashic-aurora/releases/latest/download';

type Method = {
  id: string;
  label: string;
  note: string;
  install: string;
  update: string;
};

// One line each, like the install pages of opencode and the Codex CLI. Keep in step with
// aurora-cli/install/ and the README's install table.
const methods: Method[] = [
  {
    id: 'unix',
    label: 'macOS / Linux',
    note: 'The install script. It installs uv if you need it, then aurora, then fetches Aurora itself.',
    install: `curl -fsSL ${RELEASES}/install.sh | sh`,
    update: `curl -fsSL ${RELEASES}/install.sh | sh`,
  },
  {
    id: 'windows',
    label: 'Windows',
    note: 'The PowerShell script. Run it from a new PowerShell window.',
    install: `powershell -ExecutionPolicy ByPass -c "irm ${RELEASES}/install.ps1 | iex"`,
    update: `powershell -ExecutionPolicy ByPass -c "irm ${RELEASES}/install.ps1 | iex"`,
  },
  {
    id: 'uv',
    label: 'uv',
    note: 'If you already use uv. Works on every OS.',
    install: 'uv tool install akashic-aurora-cli',
    update: 'uv tool upgrade akashic-aurora-cli',
  },
  {
    id: 'pipx',
    label: 'pipx',
    note: 'If you already use pipx. Works on every OS.',
    install: 'pipx install akashic-aurora-cli',
    update: 'pipx upgrade akashic-aurora-cli',
  },
];

const STORAGE_KEY = 'aurora-install-method';

function Command({ title, code }: { title: string; code: string }) {
  return (
    <CodeBlock title={title} className="my-0">
      {/* MDX code is pre-highlighted into padded lines; plain text needs the padding itself */}
      <Pre className="px-4">
        <code>{code}</code>
      </Pre>
    </CodeBlock>
  );
}

function StepHead({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-fd-primary text-sm font-semibold text-fd-primary-foreground">
        {n}
      </span>
      <h3 className="m-0 text-base font-semibold">{title}</h3>
    </div>
  );
}

// The quickstart card: install (pick your OS or package manager), set up, first task.
export function InstallCard() {
  const [active, setActive] = useState(methods[0].id);

  // Pick a starting tab after hydration, so the server and client render the same HTML.
  useEffect(() => {
    let saved: string | null = null;
    try {
      saved = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // storage can be blocked; the default tab is fine
    }
    if (saved && methods.some((m) => m.id === saved)) setActive(saved);
    else if (/windows/i.test(navigator.userAgent)) setActive('windows');
  }, []);

  const choose = (id: string) => {
    setActive(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // not remembered; nothing else depends on it
    }
  };

  const method = methods.find((m) => m.id === active) ?? methods[0];

  return (
    <section
      aria-label="Quickstart"
      className="not-prose my-6 flex flex-col gap-6 rounded-xl border bg-fd-card p-5 text-fd-card-foreground"
    >
      <div className="flex flex-col gap-3">
        <StepHead n={1} title="Install aurora" />
        <div
          role="radiogroup"
          aria-label="Install method"
          className="flex w-fit max-w-full flex-wrap gap-1 rounded-lg border bg-fd-muted p-1"
        >
          {methods.map((m) => (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={m.id === active}
              onClick={() => choose(m.id)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                m.id === active
                  ? 'bg-fd-background text-fd-foreground shadow-sm'
                  : 'text-fd-muted-foreground hover:text-fd-foreground',
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="m-0 text-sm text-fd-muted-foreground">{method.note}</p>
        <Command title="Install" code={method.install} />
        <Command title="Update" code={method.update} />
      </div>

      <div className="flex flex-col gap-3">
        <StepHead n={2} title="Set up your agents" />
        <p className="m-0 text-sm text-fd-muted-foreground">
          It wires the hooks, the MCP server and your agent id for Claude Code, Codex or Cursor. Each step shows
          the command that changes it later.
        </p>
        <Command title="Terminal" code="aurora setup" />
      </div>

      <div className="flex flex-col gap-3">
        <StepHead n={3} title="Start your first task" />
        <p className="m-0 text-sm text-fd-muted-foreground">
          Boot to load past lessons, learn to record one, recall to search them. Run these from any directory.
        </p>
        <Command
          title="Terminal"
          code={[
            'aurora boot me --task first-run',
            'aurora learn me --experiment first_try --tried installing --result booted',
            'aurora recall first_try',
          ].join('\n')}
        />
      </div>
    </section>
  );
}
