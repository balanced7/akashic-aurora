import { Img, Link, Text } from "@react-email/components";

import { env } from "../../../env";

interface FooterProps {
  readonly origin: string;
}

export const Footer = ({ origin }: FooterProps) => {
  return (
    <>
      <Img
        src={`${origin}/images/logo.png`}
        alt="Akashic Labs Logo"
        height={45}
        className="mt-12"
      />
      <Text className="text-muted-foreground max-w-[250px] leading-normal">
        <Link
          href="https://akashiclabs.dev"
          className="text-muted-foreground"
          style={{ textDecoration: "underline" }}
        >
          {env.PRODUCT_NAME}
        </Link>
      </Text>
    </>
  );
};
