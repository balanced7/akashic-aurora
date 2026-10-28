import { PricingPlanType, FEATURES } from "@akashic-labs/billing";

interface PlanFeature {
  readonly id: string;
  readonly available: boolean;
  readonly title: string;
  readonly addon?: React.ReactNode;
}

export const PLAN_FEATURES: Record<PricingPlanType, PlanFeature[]> = {
  [PricingPlanType.FREE]: [
    {
      id: FEATURES[PricingPlanType.FREE].SYNC,
      available: true,
      title: "billing:plan.starter.features.sync",
    },
    {
      id: FEATURES[PricingPlanType.FREE].BASIC_SUPPORT,
      available: true,
      title: "billing:plan.starter.features.basicSupport",
    },
    {
      id: FEATURES[PricingPlanType.FREE].LIMITED_STORAGE,
      available: true,
      title: "billing:plan.starter.features.limitedStorage",
    },
    {
      id: FEATURES[PricingPlanType.FREE].EMAIL_NOTIFICATIONS,
      available: true,
      title: "billing:plan.starter.features.emailNotifications",
    },
    {
      id: FEATURES[PricingPlanType.FREE].BASIC_REPORTS,
      available: true,
      title: "billing:plan.starter.features.basicReports",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].ADVANCED_SYNC,
      available: false,
      title: "billing:plan.premium.features.advancedSync",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].PRIORITY_SUPPORT,
      available: false,
      title: "billing:plan.premium.features.prioritySupport",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].MORE_STORAGE,
      available: false,
      title: "billing:plan.premium.features.moreStorage",
    },
  ],
  [PricingPlanType.PREMIUM]: [
    {
      id: FEATURES[PricingPlanType.PREMIUM].ADVANCED_SYNC,
      available: true,
      title: "billing:plan.premium.features.advancedSync",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].PRIORITY_SUPPORT,
      available: true,
      title: "billing:plan.premium.features.prioritySupport",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].MORE_STORAGE,
      available: true,
      title: "billing:plan.premium.features.moreStorage",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].TEAM_COLLABORATION,
      available: true,
      title: "billing:plan.premium.features.teamCollaboration",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].SMS_NOTIFICATIONS,
      available: true,
      title: "billing:plan.premium.features.smsNotifications",
    },
    {
      id: FEATURES[PricingPlanType.PREMIUM].ADVANCED_REPORTS,
      available: true,
      title: "billing:plan.premium.features.advancedReports",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].UNLIMITED_STORAGE,
      available: false,
      title: "billing:plan.enterprise.features.unlimitedStorage",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].CUSTOM_BRANDING,
      available: false,
      title: "billing:plan.enterprise.features.customBranding",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].DEDICATED_SUPPORT,
      available: false,
      title: "billing:plan.enterprise.features.dedicatedSupport",
    },
  ],
  [PricingPlanType.ENTERPRISE]: [
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].UNLIMITED_STORAGE,
      available: true,
      title: "billing:plan.enterprise.features.unlimitedStorage",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].CUSTOM_BRANDING,
      available: true,
      title: "billing:plan.enterprise.features.customBranding",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].DEDICATED_SUPPORT,
      available: true,
      title: "billing:plan.enterprise.features.dedicatedSupport",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].API_ACCESS,
      available: true,
      title: "billing:plan.enterprise.features.apiAccess",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].USER_ROLES,
      available: true,
      title: "billing:plan.enterprise.features.userRoles",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].AUDIT_LOGS,
      available: true,
      title: "billing:plan.enterprise.features.auditLogs",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].SINGLE_SIGN_ON,
      available: true,
      title: "billing:plan.enterprise.features.singleSignOn",
    },
    {
      id: FEATURES[PricingPlanType.ENTERPRISE].ADVANCED_ANALYTICS,
      available: true,
      title: "billing:plan.enterprise.features.advancedAnalytics",
    },
  ],
};
