import { authConfig } from "~/config/auth";
import { getMetadata } from "~/lib/metadata";
import { Accounts } from "~/modules/user/settings/security/accounts";
import { EditPassword } from "~/modules/user/settings/security/edit-password";
import { Passkeys } from "~/modules/user/settings/security/passkeys";
import { Sessions } from "~/modules/user/settings/security/sessions";
import { TwoFactorAuthentication } from "~/modules/user/settings/security/two-factor/two-factor";

export const generateMetadata = getMetadata({
  title: "auth:account.settings.security.title",
  description: "auth:account.settings.security.description",
});

export default function SettingsPage() {
  return (
    <>
      <EditPassword />
      <Accounts />
      {authConfig.providers.passkey && <Passkeys />}
      <TwoFactorAuthentication />
      <Sessions />
    </>
  );
}
