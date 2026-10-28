import { getMetadata } from "~/lib/metadata";
import { LoginFlow } from "~/modules/auth/login";

export const generateMetadata = getMetadata({
  title: "auth:login.title",
});

const Login = async ({
  searchParams,
}: {
  searchParams: Promise<{
    redirectTo?: string;
    invitationId?: string;
    email?: string;
  }>;
}) => {
  const { redirectTo, invitationId, email } = await searchParams;

  return (
    <LoginFlow
      redirectTo={redirectTo}
      invitationId={invitationId}
      email={email}
    />
  );
};

export default Login;
