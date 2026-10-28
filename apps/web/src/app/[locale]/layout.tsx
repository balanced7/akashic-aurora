import { notFound } from "next/navigation";

import { config, isLocaleSupported, loadResources } from "@akashic-labs/i18n";

import { getMetadata } from "~/lib/metadata";
import { Providers } from "~/lib/providers/providers";
import { BaseLayout } from "~/modules/common/layout/base";
import { Toaster } from "~/modules/common/toast";

export function generateStaticParams() {
  return config.locales.map((locale) => ({ locale }));
}

export const generateMetadata = getMetadata();

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const locale = (await params).locale;

  if (!isLocaleSupported(locale)) {
    return notFound();
  }

  // Preloaded translations let client components render real content on the server.
  const resources = await loadResources(locale);

  return (
    <BaseLayout locale={locale}>
      <Providers locale={locale} resources={resources}>
        {children}
        <Toaster />
      </Providers>
    </BaseLayout>
  );
}
