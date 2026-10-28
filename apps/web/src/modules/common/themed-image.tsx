"use client";

import Image from "next/image";
import { useTheme } from "next-themes";
import { preload } from "react-dom";

import type { ComponentProps } from "react";

export const ThemedImage = ({
  light,
  dark,
  ...props
}: Omit<ComponentProps<typeof Image>, "src"> & {
  light: string;
  dark: string;
}) => {
  preload(light, { as: "image" });
  preload(dark, { as: "image" });

  const { resolvedTheme } = useTheme();

  return <Image src={resolvedTheme === "dark" ? dark : light} {...props} />;
};
