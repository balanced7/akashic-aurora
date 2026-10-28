"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { config, PricingPlanType } from "@akashic-labs/billing";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { useCustomer } from "~/modules/billing/hooks/use-customer";
import { billing } from "~/modules/billing/lib/api";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";

export const ManagePlan = () => {
  const { t } = useTranslation("billing");
  const router = useRouter();
  const { data: customer } = useCustomer();

  const getPortal = useMutation({
    ...billing.mutations.portal.get,
    onSuccess: ({ url }) => {
      router.push(url);
    },
  });

  const plan = config.plans.find(
    (plan) => plan.id === (customer?.plan ?? PricingPlanType.FREE),
  );

  if (!plan) {
    return null;
  }

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("manage.billing.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("manage.billing.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardContent>
        <Button
          className="w-fit gap-1"
          disabled={getPortal.isPending}
          onClick={() =>
            getPortal.mutate({
              query: {
                redirectUrl: window.location.href,
              },
            })
          }
        >
          {t("manage.billing.visitPortal")}
          {getPortal.isPending ? (
            <Icons.Loader2 className="size-4 animate-spin" />
          ) : (
            <Icons.ArrowUpRight className="size-4" />
          )}
        </Button>
      </SettingsCardContent>
    </SettingsCard>
  );
};
