/// <reference types="../types.d.ts" />

import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { includeIgnoreFile } from "@eslint/compat";
import eslint from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import turboPlugin from "eslint-plugin-turbo";
import unusedImportsPlugin from "eslint-plugin-unused-imports";
import tseslint from "typescript-eslint";
import i18nextPlugin from "eslint-plugin-i18next";
import { defineConfig } from "eslint/config";

const restrictEnvAccess = defineConfig({
  files: ["**/*.js", "**/*.ts", "**/*.tsx"],
  ignores: ["**/env*.ts"],
  rules: {
    "no-restricted-properties": [
      "error",
      {
        object: "process",
        property: "env",
        message:
          "Use `import { env } from 'env.config'` instead to ensure validated types.",
      },
    ],
    "no-restricted-imports": [
      "error",
      {
        name: "process",
        importNames: ["env"],
        message:
          "Use `import { env } from 'env.config'` instead to ensure validated types.",
      },
    ],
  },
});

export default defineConfig(
  // Ignore files not tracked by VCS and any config files
  includeIgnoreFile(
    path.resolve(
      path.dirname(fileURLToPath(import.meta.url)),
      "../../../.gitignore",
    ),
  ),
  { ignores: ["**/*.config.*"] },
  {
    files: ["**/*.js", "**/*.ts", "**/*.tsx"],
    plugins: {
      import: importPlugin,
      "unused-imports": unusedImportsPlugin,
      turbo: turboPlugin,
    },
    extends: [
      eslint.configs.recommended,
      i18nextPlugin.configs["flat/recommended"],
      ...tseslint.configs.recommended,
      ...tseslint.configs.recommendedTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
    ],
    rules: {
      ...turboPlugin.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/consistent-type-imports": [
        "warn",
        { prefer: "type-imports", fixStyle: "separate-type-imports" },
      ],
      "@typescript-eslint/no-misused-promises": [
        2,
        { checksVoidReturn: { attributes: false } },
      ],
      "@typescript-eslint/no-unnecessary-condition": [
        "error",
        {
          allowConstantLoopConditions: true,
        },
      ],
      "import/consistent-type-specifier-style": ["error", "prefer-top-level"],
      "import/order": [
        "error",
        {
          alphabetize: {
            caseInsensitive: true,
            order: "asc",
          },
          pathGroups: [
            {
              pattern: "@akashic-labs/**",
              group: "internal",
              position: "before",
            },
            {
              pattern: "~/**",
              group: "internal",
              position: "before",
            },
          ],
          groups: [
            ["builtin", "external"],
            "internal",
            "parent",
            "sibling",
            "index",
            "object",
            "type",
          ],
          "newlines-between": "always",
          warnOnUnassignedImports: true,
          pathGroupsExcludedImportTypes: ["type"],
        },
      ],
      "unused-imports/no-unused-imports": "error",
      "unused-imports/no-unused-vars": [
        "warn",
        {
          vars: "all",
          varsIgnorePattern: "^_",
          args: "after-used",
          argsIgnorePattern: "^_",
        },
      ],
    },
  },
  {
    linterOptions: { reportUnusedDisableDirectives: true },
    languageOptions: { parserOptions: { projectService: true } },
  },
  restrictEnvAccess,
);
