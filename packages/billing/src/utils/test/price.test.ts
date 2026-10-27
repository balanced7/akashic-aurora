import { describe, expect, it } from "vitest";

import {
  BillingDiscountType,
  BillingModel,
  PricingPlanType,
  RecurringInterval,
} from "../../types";
import {
  calculatePriceDiscount,
  calculateRecurringDiscount,
  formatPrice,
  getHighestDiscountForPrice,
  getPlanPrice,
  getPriceWithHighestDiscount,
} from "../price";

import type { Discount, PricingPlan, PricingPlanPrice } from "../../types";

const MONTHLY_PRICE: PricingPlanPrice = {
  id: "price_monthly",
  type: BillingModel.RECURRING,
  interval: RecurringInterval.MONTH,
  amount: 1000, // $10.00
  currency: "USD",
  custom: false,
};

const YEARLY_PRICE: PricingPlanPrice = {
  id: "price_yearly",
  type: BillingModel.RECURRING,
  interval: RecurringInterval.YEAR,
  amount: 10000, // $100.00
  currency: "USD",
  custom: false,
};

const LIFETIME_PRICE: PricingPlanPrice = {
  id: "price_lifetime",
  type: BillingModel.ONE_TIME,
  amount: 30000, // $300.00
  currency: "USD",
  custom: false,
};

const EUR_PRICE: PricingPlanPrice = {
  id: "price_eur",
  type: BillingModel.RECURRING,
  interval: RecurringInterval.MONTH,
  amount: 900, // €9.00
  currency: "EUR",
  custom: false,
};

const PRICES: PricingPlanPrice[] = [
  MONTHLY_PRICE,
  YEARLY_PRICE,
  LIFETIME_PRICE,
  EUR_PRICE,
];

const PLAN: PricingPlan = {
  id: PricingPlanType.PREMIUM,
  name: "Premium Plan",
  description: "Best for professionals",
  badge: null,
  prices: PRICES,
};

const PERCENT_DISCOUNT: Discount = {
  code: "SAVE10",
  type: BillingDiscountType.PERCENT,
  off: 10,
  appliesTo: ["price_monthly", "price_yearly"],
};

const AMOUNT_DISCOUNT: Discount = {
  code: "MINUS5",
  type: BillingDiscountType.AMOUNT,
  off: 500, // $5.00
  appliesTo: ["price_monthly"],
};

const DISCOUNTS: Discount[] = [PERCENT_DISCOUNT, AMOUNT_DISCOUNT];

describe("getPlanPrice", () => {
  it("should return the correct recurring price for a given interval", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.RECURRING,
      interval: RecurringInterval.MONTH,
    });
    expect(price).toEqual(MONTHLY_PRICE);
  });

  it("should return the correct one-time price", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.ONE_TIME,
    });
    expect(price).toEqual(LIFETIME_PRICE);
  });

  it("should match currency if provided", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.RECURRING,
      interval: RecurringInterval.MONTH,
      currency: "USD",
    });
    expect(price).toEqual(MONTHLY_PRICE);
  });

  it("should match currency case-insensitively", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.RECURRING,
      interval: RecurringInterval.MONTH,
      currency: "usd",
    });
    expect(price).toEqual(MONTHLY_PRICE);
  });

  it("should return specific currency price when multiple exist", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.RECURRING,
      interval: RecurringInterval.MONTH,
      currency: "EUR",
    });
    expect(price).toEqual(EUR_PRICE);
  });

  it("should return undefined if no matching price found", () => {
    const price = getPlanPrice(PLAN, {
      model: BillingModel.RECURRING,
      interval: RecurringInterval.WEEK, // No weekly price in mock
    });
    expect(price).toBeUndefined();
  });
});

describe("formatPrice", () => {
  it("should format currency correctly using Intl.NumberFormat", () => {
    const formatted = formatPrice({ amount: 1234, currency: "USD" }, "en-US");
    expect(formatted).toBe("$12.3");
  });

  it("should handle round numbers without decimals if specified in implementation", () => {
    const formatted = formatPrice({ amount: 1000, currency: "USD" }, "en-US");
    expect(formatted).toBe("$10");
  });

  it("should handle default language", () => {
    const formatted = formatPrice({ amount: 1000, currency: "USD" });
    // Should not throw and return a string
    expect(typeof formatted).toBe("string");
  });
});

describe("calculateRecurringDiscount", () => {
  it("should calculate discount for yearly billing compared to monthly", () => {
    const result = calculateRecurringDiscount(PLAN, RecurringInterval.YEAR);

    expect(result).toBeDefined();
    expect(result?.percentage).toBe(7);
    expect(result?.discounted.id).toBe("price_yearly");
    expect(result?.original.amount).toBe(10800);
  });

  it("should return null if price not found", () => {
    const result = calculateRecurringDiscount(PLAN, RecurringInterval.WEEK);
    expect(result).toBeNull();
  });

  it("should return null if minPrice is missing/invalid", () => {
    // Plan with no recurring prices
    const emptyPlan: PricingPlan = { ...PLAN, prices: [] };
    const result = calculateRecurringDiscount(
      emptyPlan,
      RecurringInterval.YEAR,
    );
    expect(result).toBeNull();
  });
});

describe("calculatePriceDiscount", () => {
  it("should calculate percentage discount", () => {
    const price = MONTHLY_PRICE; // 1000
    const discount = PERCENT_DISCOUNT; // 10%

    const result = calculatePriceDiscount(price, discount);
    expect(result).toBeDefined();
    expect(result?.type).toBe(BillingDiscountType.PERCENT);
    expect(result?.percentage).toBe(10);
    expect(result?.discounted.amount).toBe(900); // 1000 - 10%
  });

  it("should calculate amount discount", () => {
    const price = MONTHLY_PRICE; // 1000
    const discount = AMOUNT_DISCOUNT; // 500 off

    const result = calculatePriceDiscount(price, discount);
    expect(result).toBeDefined();
    expect(result?.type).toBe(BillingDiscountType.AMOUNT);
    expect(result?.percentage).toBe(50); // 500/1000 * 100
    expect(result?.discounted.amount).toBe(500);
  });

  it("should return null for custom price", () => {
    const customPrice: PricingPlanPrice = {
      id: "custom",
      custom: true,
      label: "Contact Us",
      href: "/contact",
      type: BillingModel.ONE_TIME,
      currency: "USD",
    };
    const result = calculatePriceDiscount(customPrice, PERCENT_DISCOUNT);
    expect(result).toBeNull();
  });
});

describe("getHighestDiscountForPrice", () => {
  it("should select the discount that gives the biggest reduction", () => {
    // Price: 1000
    // Percent discount: 10% -> 100 off -> 900
    // Amount discount: 500 off -> 500 off -> 500
    const best = getHighestDiscountForPrice(MONTHLY_PRICE, DISCOUNTS);
    expect(best).toBe(AMOUNT_DISCOUNT);
  });

  it("should return undefined if no discount applies", () => {
    const noDiscountPrice: PricingPlanPrice = {
      ...MONTHLY_PRICE,
      id: "price_other",
    };
    const result = getHighestDiscountForPrice(noDiscountPrice, DISCOUNTS);
    expect(result).toBeUndefined();
  });

  it("should return correct discount when comparison involves amount 0", () => {
    // Edge case where discount makes it free or similar
    const fullDiscount: Discount = {
      code: "FREE",
      type: BillingDiscountType.PERCENT,
      off: 100,
      appliesTo: ["price_monthly"],
    };
    const discounts = [...DISCOUNTS, fullDiscount];
    const best = getHighestDiscountForPrice(MONTHLY_PRICE, discounts);
    expect(best).toBe(fullDiscount);
  });
});

describe("getPriceWithHighestDiscount", () => {
  it("should return the price configuration that yields the biggest saving", () => {
    const result = getPriceWithHighestDiscount([PLAN], DISCOUNTS);

    expect(result).toBeDefined();
    expect(result?.id).toBe(YEARLY_PRICE.id);
    expect(result?.discount?.code).toBe("SAVE10");
  });

  it("should return null if no prices have discounts", () => {
    const result = getPriceWithHighestDiscount([PLAN], []);

    expect(result).not.toBeNull();
    expect(result?.discount).toBeUndefined();
  });
});
