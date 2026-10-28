const ADMIN_PREFIX = "/admin";
const AUTH_PREFIX = "/auth";
const BLOG_PREFIX = "/blog";
const DASHBOARD_PREFIX = "/dashboard";
const LEGAL_PREFIX = "/legal";

const API_PREFIX = "/api";

const pathsConfig = {
  index: "/",
  admin: {
    index: ADMIN_PREFIX,
    users: {
      index: `${ADMIN_PREFIX}/users`,
      user: (id: string) => `${ADMIN_PREFIX}/users/${id}`,
    },
    organizations: {
      index: `${ADMIN_PREFIX}/organizations`,
      organization: (slug: string) => `${ADMIN_PREFIX}/organizations/${slug}`,
    },
    customers: {
      index: `${ADMIN_PREFIX}/customers`,
      customer: (id: string) => `${ADMIN_PREFIX}/customers/${id}`,
    },
  },
  marketing: {
    pricing: "/pricing",
    contact: "/contact",
    blog: {
      index: BLOG_PREFIX,
      post: (slug: string) => `${BLOG_PREFIX}/${slug}`,
    },
    legal: (slug: string) => `${LEGAL_PREFIX}/${slug}`,
  },
  auth: {
    login: `${AUTH_PREFIX}/login`,
    register: `${AUTH_PREFIX}/register`,
    join: `${AUTH_PREFIX}/join`,
    forgotPassword: `${AUTH_PREFIX}/password/forgot`,
    updatePassword: `${AUTH_PREFIX}/password/update`,
    error: `${AUTH_PREFIX}/error`,
  },
  dashboard: {
    user: {
      index: DASHBOARD_PREFIX,
      ai: `${DASHBOARD_PREFIX}/ai`,
      reports: `${DASHBOARD_PREFIX}/reports`,
      skillTrees: `${DASHBOARD_PREFIX}/skill-trees`,
      settings: {
        index: `${DASHBOARD_PREFIX}/settings`,
        security: `${DASHBOARD_PREFIX}/settings/security`,
        billing: `${DASHBOARD_PREFIX}/settings/billing`,
      },
    },
    organization: (slug: string) => ({
      index: `${DASHBOARD_PREFIX}/${slug}`,
      settings: {
        index: `${DASHBOARD_PREFIX}/${slug}/settings`,
      },
      members: `${DASHBOARD_PREFIX}/${slug}/members`,
    }),
  },
} as const;

export {
  pathsConfig,
  DASHBOARD_PREFIX,
  ADMIN_PREFIX,
  BLOG_PREFIX,
  AUTH_PREFIX,
  API_PREFIX,
  LEGAL_PREFIX,
};
