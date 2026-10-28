import { memo } from "react";

import { BillingModel, formatPrice } from "@akashic-labs/billing";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button, buttonVariants } from "@akashic-labs/ui-web/button";
import { Card } from "@akashic-labs/ui-web/card";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { useCustomer } from "~/modules/billing/hooks/use-customer";
import { TurboLink } from "~/modules/common/turbo-link";

import { usePlan } from "./hooks/use-plan";

import type { User } from "@akashic-labs/auth";
import type {
  Discount,
  PricingPlan,
  RecurringInterval,
} from "@akashic-labs/billing";

interface PlanProps {
  readonly plan: PricingPlan;
  readonly user: User | null;
  readonly interval: RecurringInterval;
  readonly model: BillingModel;
  readonly currency: string;
  readonly discounts: Discount[];
}

export const Plan = memo<PlanProps>(
  ({ plan, interval, user, model, currency, discounts }) => {
    const { data: customer } = useCustomer();
    const { t, i18n } = useTranslation(["common", "billing"]);
    const {
      features,
      price,
      discount,
      isPending,
      handleCheckout,
      handleOpenPortal,
      hasPlan,
    } = usePlan(plan, { model, interval, discounts, currency });

    if (!price) {
      return null;
    }

    return (
      <div className="grow basis-[350px] rounded-lg">
        <Card
          className={cn(
            "relative flex h-full flex-col gap-6 px-7 py-6 md:p-8",
            plan.badge && "border-primary",
          )}
        >
          {plan.badge && (
            <Badge className="hover:bg-primary absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 px-4 py-1.5 uppercase">
              {isKey(plan.badge, i18n, "billing") ? t(plan.badge) : plan.badge}
            </Badge>
          )}
          <div>
            <span className="text-lg font-semibold">
              {isKey(plan.name, i18n, "billing") ? t(plan.name) : plan.name}
            </span>
            <p className="relative flex items-end gap-1 py-2">
              {discount?.original &&
                "amount" in discount.original &&
                typeof discount.original.amount === "number" &&
                discount.percentage > 0 && (
                  <span className="text-muted-foreground mr-2 text-lg line-through md:text-xl">
                    {formatPrice(
                      {
                        amount: discount.original.amount,
                        currency,
                      },
                      i18n.language,
                    )}
                  </span>
                )}
              <span className="text-4xl font-bold tracking-tighter md:text-5xl">
                {price.custom
                  ? isKey(price.label, i18n, "billing")
                    ? t(price.label)
                    : price.label
                  : formatPrice(
                      {
                        amount:
                          discount?.discounted &&
                          "amount" in discount.discounted
                            ? discount.discounted.amount
                            : price.amount,
                        currency,
                      },
                      i18n.language,
                    )}
              </span>
              {!price.custom && (
                <span className="text-muted-foreground shrink-0 text-lg">
                  /{" "}
                  {price.type === BillingModel.RECURRING
                    ? t(`interval.${price.interval}`)
                    : t("interval.lifetime")}
                </span>
              )}
            </p>
            <span className="text-sm">
              {isKey(plan.description, i18n, "billing")
                ? t(plan.description)
                : plan.description}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            {features?.map((feature) => (
              <div
                key={feature.title}
                className={cn("flex items-center gap-3 py-1", {
                  "opacity-50": !feature.available,
                })}
              >
                <div
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-full",
                    feature.available ? "bg-primary" : "border-primary border",
                  )}
                >
                  {feature.available ? (
                    <Icons.CheckIcon className="text-primary-foreground w-3" />
                  ) : (
                    <Icons.X className="text-primary w-3" />
                  )}
                </div>
                <span className="text-md">
                  {isKey(feature.title, i18n, "billing")
                    ? t(feature.title)
                    : feature.title}
                  {"addon" in feature && (
                    <span className="ml-2 whitespace-nowrap">
                      &nbsp;{feature.addon}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-auto flex flex-col gap-2">
            {"trialDays" in price &&
              price.trialDays &&
              !hasPlan(customer?.plan ?? null) && (
                <Button
                  variant="outline"
                  onClick={() => handleCheckout(user)}
                  disabled={isPending}
                >
                  {isPending ? (
                    <Icons.Loader2 className="animate-spin" />
                  ) : (
                    t("trial.period", { period: price.trialDays })
                  )}
                </Button>
              )}
            {price.custom ? (
              <TurboLink href={price.href} className={buttonVariants()}>
                {hasPlan(customer?.plan ?? null)
                  ? t("manage.plan.title")
                  : t("getStarted")}
              </TurboLink>
            ) : price.amount === 0 ? (
              <TurboLink
                href={
                  user
                    ? pathsConfig.dashboard.user.index
                    : pathsConfig.auth.login
                }
                className={buttonVariants({ variant: "outline" })}
              >
                {user ? t("goToDashboard") : t("trial.cta")}
              </TurboLink>
            ) : (
              <Button
                onClick={() =>
                  model === BillingModel.RECURRING &&
                  hasPlan(customer?.plan ?? null)
                    ? handleOpenPortal(user)
                    : handleCheckout(user)
                }
                disabled={isPending}
              >
                {isPending ? (
                  <Icons.Loader2 className="animate-spin" />
                ) : model === BillingModel.RECURRING &&
                  hasPlan(customer?.plan ?? null) ? (
                  t("manage.plan.title")
                ) : model === BillingModel.RECURRING ? (
                  t("subscribe")
                ) : (
                  t("getLifetimeAccess")
                )}
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  },
);

Plan.displayName = "Plan";
