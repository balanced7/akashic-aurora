import { appConfig } from "~/config/app";

import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api", "/dashboard", "/auth"],
    },
    sitemap: `${appConfig.url}/sitemap.xml`,
  };
}
