import { useMutation } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  BillingModel,
  PricingPlanType,
  calculatePriceDiscount,
  calculateRecurringDiscount,
  getPlanPrice,
  getHighestDiscountForPrice,
} from "@akashic-labs/billing";
import { useTranslation } from "@akashic-labs/i18n";

import { appConfig } from "~/config/app";
import { pathsConfig } from "~/config/paths";
import { billing } from "~/modules/billing/lib/api";
import { PLAN_FEATURES } from "~/modules/billing/pricing/constants/features";

import type { User } from "@akashic-labs/auth";
import type {
  Discount,
  PricingPlan,
  RecurringInterval,
} from "@akashic-labs/billing";

export const usePlan = (
  plan: PricingPlan,
  options: {
    model: BillingModel;
    interval: RecurringInterval;
    discounts: Discount[];
    currency?: string;
  },
) => {
  const { t } = useTranslation("billing");
  const router = useRouter();
  const checkout = useMutation({
    ...billing.mutations.checkout.create,
    onSuccess: (data) => {
      if (!data.url) {
        return toast.error(t("error.checkout"));
      }
      return router.push(data.url);
    },
  });

  const getPortal = useMutation({
    ...billing.mutations.portal.get,
    onSuccess: (data) => {
      if (!data.url) {
        return toast.error(t("error.portal"));
      }
      return router.push(data.url);
    },
  });

  const pathname = usePathname();
  const price = getPlanPrice(plan, options);

  const features = plan.id in PLAN_FEATURES ? PLAN_FEATURES[plan.id] : null;

  const discountForPrice = price
    ? getHighestDiscountForPrice(price, options.discounts)
    : null;

  const discount =
    price && discountForPrice
      ? calculatePriceDiscount(price, discountForPrice)
      : options.model === BillingModel.RECURRING
        ? calculateRecurringDiscount(plan, options.interval)
        : null;

  const handleCheckout = (user: User | null) => {
    if (!user) {
      const url = new URL(pathsConfig.auth.login);
      url.searchParams.set("redirectTo", pathsConfig.marketing.pricing);
      return router.push(url.toString());
    }

    if (!price) {
      return;
    }

    checkout.mutate({
      json: {
        price: {
          id: price.id,
        },
        redirect: {
          success: `${appConfig.url}${pathsConfig.dashboard.user.index}`,
          cancel: `${appConfig.url}${pathname}`,
        },
      },
    });
  };

  const handleOpenPortal = (user: User | null) => {
    if (!user) {
      const url = new URL(pathsConfig.auth.login);
      url.searchParams.set("redirectTo", pathsConfig.marketing.pricing);
      return router.push(url.toString());
    }

    getPortal.mutate({
      query: {
        redirectUrl: `${appConfig.url}${pathname}`,
      },
    });
  };

  const hasPlan = (customerPlan: string | null) => {
    if (!customerPlan) {
      return false;
    }

    const currentPlanIndex = Object.values(PricingPlanType).indexOf(plan.id);
    const customerCurrentPlanIndex = customerPlan
      ? Object.values(PricingPlanType).indexOf(customerPlan)
      : -1;

    return currentPlanIndex <= customerCurrentPlanIndex;
  };

  return {
    isPending: checkout.isPending || getPortal.isPending,
    price,
    features,
    discount,
    handleCheckout,
    handleOpenPortal,
    hasPlan,
  };
};
