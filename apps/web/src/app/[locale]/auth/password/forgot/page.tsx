import { getTranslation } from "@akashic-labs/i18n/server";

import { getMetadata } from "~/lib/metadata";
import { ForgotPasswordForm } from "~/modules/auth/form/password/forgot";
import { AuthHeader } from "~/modules/auth/layout/header";

export const generateMetadata = getMetadata({
  title: "auth:account.password.forgot.title",
});

const ForgotPassword = async () => {
  const { t } = await getTranslation({ ns: "auth" });
  return (
    <>
      <AuthHeader
        title={t("account.password.forgot.header.title")}
        description={t("account.password.forgot.header.description")}
      />
      <ForgotPasswordForm />
    </>
  );
};

export default ForgotPassword;
