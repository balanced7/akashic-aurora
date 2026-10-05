// commitlint rules for Conventional Commits. Types and scopes come from changelog.config.js so
// the two never disagree.
//
// Check a message:   echo "feat(core): add x" | npx -p @commitlint/cli -p @commitlint/config-conventional commitlint
// Check the last N:  npx -p @commitlint/cli -p @commitlint/config-conventional commitlint --from HEAD~N
import type { UserConfig } from "@commitlint/types";

import changelog from "./changelog.config.js";

const config: UserConfig = {
  extends: ["@commitlint/config-conventional"],
  parserPreset: {
    parserOpts: {
      // config-conventional's header pattern, plus an optional leading emoji (`🎸feat(core): x`).
      headerPattern: /^(?:\p{Extended_Pictographic}️?\s?)?(\w*)(?:\(([\w$.\-*/ ]*)\))?!?: (.*)$/u,
      headerCorrespondence: ["type", "scope", "subject"],
    },
  },
  rules: {
    "type-enum": [2, "always", changelog.list],
    "scope-enum": [2, "always", changelog.scopes.filter(Boolean)],
    "header-max-length": [2, "always", changelog.maxMessageLength],
    "body-leading-blank": [2, "always"],
    "body-max-line-length": [2, "always", 100],
    "footer-max-line-length": [2, "always", 100],
  },
};

export default config;
