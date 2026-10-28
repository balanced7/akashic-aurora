"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import type { LinkProps } from "next/link";
import type { AnchorHTMLAttributes } from "react";

type TurboLinkProps = LinkProps &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof LinkProps> & {
    children?: React.ReactNode;
  };

export const TurboLink = (props: TurboLinkProps) => {
  const router = useRouter();
  const strHref = typeof props.href === "string" ? props.href : props.href.href;

  const conditionalPrefetch = () => {
    if (strHref) {
      void router.prefetch(strHref);
    }
  };

  return (
    <Link
      {...props}
      prefetch={false}
      onMouseEnter={(e) => {
        conditionalPrefetch();
        return props.onMouseEnter?.(e);
      }}
      onPointerEnter={(e) => {
        conditionalPrefetch();
        return props.onPointerEnter?.(e);
      }}
      onTouchStart={(e) => {
        conditionalPrefetch();
        return props.onTouchStart?.(e);
      }}
      onFocus={(e) => {
        conditionalPrefetch();
        return props.onFocus?.(e);
      }}
    >
      {props.children}
    </Link>
  );
};
