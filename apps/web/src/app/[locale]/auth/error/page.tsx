import { getTranslation } from "@akashic-labs/i18n/server";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";

const AuthError = async ({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) => {
  const { error } = await searchParams;
  const { t } = await getTranslation({ ns: ["common", "auth"] });

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <Icons.CircleX className="text-destructive size-24" strokeWidth={1.2} />
      <h1 className="text-center text-2xl font-semibold">
        {t("error.general")}
      </h1>

      {error && (
        <code className="bg-muted rounded-md px-2 py-0.5 font-mono">
          {error}
        </code>
      )}

      <TurboLink
        href={pathsConfig.auth.login}
        className="text-muted-foreground hover:text-primary mt-3 text-sm font-medium underline underline-offset-4"
      >
        {t("goToLogin")}
      </TurboLink>
    </div>
  );
};

export default AuthError;
