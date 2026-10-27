"use client";

import { memo } from "react";

import {
  calculatePriceDiscount,
  formatPrice,
  BillingDiscountType,
} from "@akashic-labs/billing";
import { Trans } from "@akashic-labs/i18n";
import { Icons } from "@akashic-labs/ui-web/icons";

import type {
  Discount as DiscountType,
  PricingPlanPrice,
} from "@akashic-labs/billing";

interface DiscountProps {
  readonly currency: string;
  readonly priceWithDiscount?: PricingPlanPrice & {
    discount: DiscountType | undefined;
  };
}

export const Discount = memo<DiscountProps>(
  ({ priceWithDiscount, currency }) => {
    if (!priceWithDiscount?.discount) {
      return null;
    }

    const discount = calculatePriceDiscount(
      priceWithDiscount,
      priceWithDiscount.discount,
    );

    if (!discount) {
      return null;
    }

    return (
      <p className="sm mt-2 text-center md:text-lg">
        <Icons.Gift className="text-primary mr-1.5 mb-1.5 inline-block h-5 w-5" />
        <span className="text-primary">
          <Trans
            i18nKey="billing:discount.specialOffer"
            values={{
              discount:
                discount.type === BillingDiscountType.PERCENT
                  ? discount.percentage + "%"
                  : formatPrice({
                      amount:
                        discount.original.amount - discount.discounted.amount,
                      currency,
                    }),
            }}
            components={{
              bold: <span className="font-semibold" />,
            }}
          />
        </span>
      </p>
    );
  },
);

Discount.displayName = "Discount";
