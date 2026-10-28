import { MarketingShell } from "~/modules/marketing/layout/marketing-shell";

export default async function MarketingLayout(props: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await props.params;
  return <MarketingShell locale={locale}>{props.children}</MarketingShell>;
}
