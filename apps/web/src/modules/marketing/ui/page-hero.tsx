import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { AuroraBackdrop } from "~/modules/marketing/ui/aurora-backdrop";
import { AuroraShader } from "~/modules/marketing/ui/aurora-shader";
import { Container, Eyebrow } from "~/modules/marketing/ui/primitives";

import type { CSSProperties, ReactNode } from "react";

const rise = (delay: number) =>
  ({ "--rise-delay": `${delay}ms` }) as CSSProperties;

interface PageHeroProps {
  readonly eyebrow: ReactNode;
  readonly title: ReactNode;
  readonly description?: ReactNode;
  readonly actions?: ReactNode;
  readonly crumbs?: readonly { label: string; href: string }[];
  readonly aside?: ReactNode;
  readonly backdrop?: boolean;
  readonly className?: string;
  readonly children?: ReactNode;
}

export const PageHero = ({
  eyebrow,
  title,
  description,
  actions,
  crumbs,
  aside,
  backdrop = true,
  className,
  children,
}: PageHeroProps) => (
  <section
    className={cn(
      "relative overflow-hidden pt-32 pb-14 sm:pt-40 sm:pb-20",
      className,
    )}
  >
    {backdrop && <AuroraBackdrop intensity={0.35} />}
    {backdrop && <AuroraShader className="h-[640px]" intensity={0.6} />}
    <Container className="relative">
      {crumbs && crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-8">
          <ol className="text-mk-faint flex flex-wrap items-center gap-1.5 text-[13px]">
            <li>
              <Link href="/" className="hover:text-white">
                Home
              </Link>
            </li>
            {crumbs.map((crumb) => (
              <li key={crumb.href} className="flex items-center gap-1.5">
                <ChevronRight className="size-3.5" />
                <Link href={crumb.href} className="hover:text-white">
                  {crumb.label}
                </Link>
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div
        className={cn(
          "flex flex-col gap-10",
          aside && "lg:flex-row lg:items-end lg:justify-between",
        )}
      >
        <div className="flex max-w-4xl flex-col gap-6">
          <div className="mk-rise" style={rise(0)}>
            <Eyebrow>{eyebrow}</Eyebrow>
          </div>
          <h1
            data-testid="page-title"
            className="mk-display mk-rise-solid text-[2.6rem] sm:text-6xl lg:text-[4.2rem]"
            style={rise(60)}
          >
            {title}
          </h1>
          {description && (
            <p
              className="text-mk-muted mk-rise-solid max-w-2xl text-lg leading-relaxed text-pretty sm:text-xl"
              style={rise(160)}
            >
              {description}
            </p>
          )}
          {actions && (
            <div
              className="mk-rise mt-2 flex flex-wrap items-center gap-3"
              style={rise(260)}
            >
              {actions}
            </div>
          )}
        </div>
        {aside && (
          <div className="mk-rise" style={rise(220)}>
            {aside}
          </div>
        )}
      </div>
      {children && (
        <div className="mk-rise mt-14 sm:mt-16" style={rise(340)}>
          {children}
        </div>
      )}
    </Container>
  </section>
);
