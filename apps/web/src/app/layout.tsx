import "~/assets/styles/globals.css";
import { DEFAULT_VIEWPORT, DEFAULT_METADATA } from "~/lib/metadata";

export const viewport = DEFAULT_VIEWPORT;
export const metadata = DEFAULT_METADATA;

// Since we have a `not-found.tsx` page on the root, a layout file
// is required, even if it's just passing children through.
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
