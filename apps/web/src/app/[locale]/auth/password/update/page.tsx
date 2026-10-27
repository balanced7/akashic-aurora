import { getTranslation } from "@akashic-labs/i18n/server";

import { getMetadata } from "~/lib/metadata";
import { UpdatePasswordForm } from "~/modules/auth/form/password/update";
import { AuthHeader } from "~/modules/auth/layout/header";

export const generateMetadata = getMetadata({
  title: "auth:account.password.update.title",
});

interface UpdatePasswordPageProps {
  readonly searchParams: Promise<{
    readonly token?: string;
  }>;
}

const UpdatePassword = async ({ searchParams }: UpdatePasswordPageProps) => {
  const token = (await searchParams).token;
  const { t } = await getTranslation({ ns: "auth" });

  return (
    <>
      <AuthHeader
        title={t("account.password.update.header.title")}
        description={t("account.password.update.header.description")}
      />
      <UpdatePasswordForm token={token} />
    </>
  );
};

export default UpdatePassword;
