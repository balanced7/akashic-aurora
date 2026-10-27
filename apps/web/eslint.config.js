import baseConfig from "@akashic-labs/eslint-config/base";
import nextConfig from "@akashic-labs/eslint-config/next";
import reactConfig from "@akashic-labs/eslint-config/react";

/** @type {import('typescript-eslint').Config} */
export default [
  {
    ignores: [".next/**", "e2e/.results/**", "e2e/.report/**"],
  },
  ...baseConfig,
  ...reactConfig,
  ...nextConfig,
  {
    // The marketing site is English-only by design. Its copy lives in typed content modules and
    // components, not in the i18n catalogs, so literal strings are expected here.
    files: [
      "src/modules/marketing/**",
      "src/app/\\[locale\\]/(marketing)/**",
      "src/app/llms.txt/**",
      "src/app/api/og/**",
      // English-only prototypes behind the dashboard, not yet wired to the i18n catalogs.
      "src/app/\\[locale\\]/dashboard/(user)/demo/**",
      "src/app/\\[locale\\]/dashboard/(user)/skill-trees/**",
      "src/modules/skill-tree/**",
    ],
    rules: {
      "i18next/no-literal-string": "off",
    },
  },
];
