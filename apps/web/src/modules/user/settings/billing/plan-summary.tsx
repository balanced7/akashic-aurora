"use client";

import dayjs from "dayjs";

import {
  ACTIVE_BILLING_STATUSES,
  BillingStatus,
  config,
  PricingPlanType,
} from "@akashic-labs/billing";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Badge } from "@akashic-labs/ui-web/badge";
import { buttonVariants } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { useCustomer } from "~/modules/billing/hooks/use-customer";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { TurboLink } from "~/modules/common/turbo-link";

export const PlanSummary = () => {
  const { t, i18n } = useTranslation(["common", "billing"]);
  const { data: customer } = useCustomer();

  const plan = config.plans.find(
    (plan) => plan.id === (customer?.plan ?? PricingPlanType.FREE),
  );

  if (!plan) {
    return null;
  }

  const isHigherPlanAvailable =
    config.plans.findIndex((p) => p.id === plan.id) <
    config.plans.filter((p) => p.prices.some((price) => "amount" in price))
      .length -
      1;

  const status = customer?.status ?? BillingStatus.ACTIVE;

  const statusKey = `status.${status.toLowerCase().replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())}`;

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("manage.plan.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("manage.plan.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardContent className="-mt-2 border-t">
        <div className="flex flex-col gap-2 rounded-md pt-6">
          <div className="flex flex-wrap items-center justify-between gap-1">
            <div className="flex items-center gap-2">
              {ACTIVE_BILLING_STATUSES.includes(status) ? (
                <Icons.BadgeCheck className="size-5" />
              ) : (
                <Icons.BadgeX className="size-5" />
              )}
              <span className="text-lg font-bold capitalize">
                {isKey(plan.name, i18n, "billing") ? t(plan.name) : plan.name}
              </span>
              <Badge
                className={cn(
                  "bg-destructive/15 text-destructive hover:bg-destructive/25 ml-1 capitalize",
                  {
                    "bg-success/15 text-success hover:bg-success/25":
                      status === BillingStatus.ACTIVE,
                    "bg-muted text-muted-foreground hover:bg-muted/25":
                      status === BillingStatus.TRIALING,
                  },
                )}
              >
                {isKey(statusKey, i18n, "billing") ? t(statusKey) : statusKey}
              </Badge>
            </div>

            <span className="text-muted-foreground text-sm">
              {t("updatedAt")}{" "}
              {dayjs(customer?.updatedAt)
                .toDate()
                .toLocaleDateString(i18n.language)}
            </span>
          </div>

          <p className="text-muted-foreground text-sm">
            {isKey(plan.description, i18n, "billing")
              ? t(plan.description)
              : plan.description}{" "}
            <TurboLink
              href={pathsConfig.marketing.pricing}
              className="hover:text-primary font-medium underline underline-offset-4"
            >
              {t("learnMore")}
            </TurboLink>
          </p>

          {isHigherPlanAvailable && (
            <TurboLink
              href={pathsConfig.marketing.pricing}
              className={cn(buttonVariants(), "mt-2 w-fit gap-1")}
            >
              {t("upgrade")}
              <Icons.ArrowUpRight className="size-4" />
            </TurboLink>
          )}
        </div>
      </SettingsCardContent>
    </SettingsCard>
  );
};
