import { getTranslation } from "@akashic-labs/i18n/server";

import { authConfig } from "~/config/auth";
import { getMetadata } from "~/lib/metadata";
import { AnonymousLogin } from "~/modules/auth/form/anonymous";
import { LoginCta } from "~/modules/auth/form/login/form";
import { RegisterForm } from "~/modules/auth/form/register-form";
import { SocialProviders } from "~/modules/auth/form/social-providers";
import { AuthDivider } from "~/modules/auth/layout/divider";
import { AuthHeader } from "~/modules/auth/layout/header";
import { InvitationDisclaimer } from "~/modules/auth/layout/invitation-disclaimer";

export const generateMetadata = getMetadata({
  title: "auth:register.title",
});

const Register = async ({
  searchParams,
}: {
  searchParams: Promise<{
    redirectTo?: string;
    invitationId?: string;
    email?: string;
  }>;
}) => {
  const { redirectTo, invitationId, email } = await searchParams;
  const { t } = await getTranslation({ ns: "auth" });

  return (
    <>
      <AuthHeader
        title={t("register.header.title")}
        description={t("register.header.description")}
      />
      {invitationId && <InvitationDisclaimer />}
      <SocialProviders
        providers={authConfig.providers.oAuth}
        redirectTo={redirectTo}
      />
      {authConfig.providers.oAuth.length > 0 && <AuthDivider />}
      <div className="flex flex-col gap-2">
        <RegisterForm redirectTo={redirectTo} email={email} />
        {authConfig.providers.anonymous && <AnonymousLogin />}
      </div>
      <LoginCta />
    </>
  );
};

export default Register;
