import {
  Container,
  Font,
  Head,
  Html,
  Section,
  Tailwind,
} from "@react-email/components";

import { Footer } from "./footer";
import { Header } from "./header";

import type { PropsWithChildren } from "react";

export const Layout = ({
  children,
  origin,
  locale,
}: PropsWithChildren<{ origin?: string | null; locale?: string }>) => {
  return (
    <Html lang={locale}>
      <Head>
        <Font
          fontFamily="Geist"
          fallbackFontFamily="Arial"
          fontWeight={400}
          fontStyle="normal"
          webFont={{
            url: "https://fonts.gstatic.com/s/geist/v3/gyByhwUxId8gMEwYGFWNOITddY4.woff2",
            format: "woff2",
          }}
        />
      </Head>
      <Tailwind
        config={{
          theme: {
            extend: {
              colors: {
                background: "#ffffff",
                foreground: "#09090b",
                card: {
                  DEFAULT: "#ffffff",
                  foreground: "#09090b",
                },
                popover: {
                  DEFAULT: "#ffffff",
                  foreground: "#09090b",
                },
                primary: {
                  DEFAULT: "#f14704",
                  foreground: "#fff7ed",
                },
                secondary: {
                  DEFAULT: "#f4f4f5",
                  foreground: "#18181b",
                },
                muted: {
                  DEFAULT: "#f4f4f5",
                  foreground: "#71717b",
                },
                accent: {
                  DEFAULT: "#f4f4f5",
                  foreground: "#18181b",
                },
                success: {
                  DEFAULT: "#4ade80",
                  foreground: "#09090b",
                },
                destructive: {
                  DEFAULT: "#e7000b",
                  foreground: "#fff7ed",
                },
                border: "#e4e4e7",
                input: "#e4e4e7",
                ring: "#f14704",
              },
            },
          },
        }}
      >
        <Section className="p-1">
          <Container className="bg-card text-card-foreground rounded-lg p-6">
            {origin && <Header origin={origin} />}
            {children}
            {origin && <Footer origin={origin} />}
          </Container>
        </Section>
      </Tailwind>
    </Html>
  );
};
