"use client";

import { useEffect } from "react";

import { Trans, useTranslation } from "@akashic-labs/i18n";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";

export default function Error({ error }: { error: Error }) {
  const { t } = useTranslation(["marketing", "common"]);

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex max-w-xl flex-1 items-center justify-center px-6">
      <div className="text-center">
        <h1 className="mt-4 text-4xl font-bold">{t("error.general")}</h1>
        <p className="text-center text-lg leading-tight text-pretty">
          <Trans
            i18nKey="editToReload"
            t={t}
            values={{
              file: "src/app/[locale]/error.tsx",
            }}
            components={{
              code: (
                <code className="bg-muted text-muted-foreground mt-4 inline-block rounded-sm px-1.5 text-sm" />
              ),
            }}
          />
        </p>
        <TurboLink
          href={pathsConfig.index}
          className="text-primary mt-6 inline-block underline underline-offset-4 hover:no-underline"
        >
          {t("goBackHome")}
        </TurboLink>
      </div>
    </main>
  );
}
