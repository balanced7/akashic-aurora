import i18next from "i18next";
import en from "zod/v4/locales/en.js";

import { config } from "../config";

import type { TFunction } from "i18next";
import type { $ZodIssue, $ZodIssueBase, $ZodRawIssue } from "zod/v4/core";

const defaultErrorMap = en().localeError;

const jsonStringifyReplacer = (_: string, value: unknown): unknown => {
  if (typeof value === "bigint") {
    return value.toString();
  }
  return value;
};

function joinValues<T extends unknown[]>(array: T, separator = " | "): string {
  return array
    .map((val) => (typeof val === "string" ? `'${val}'` : val))
    .join(separator);
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  if (typeof value !== "object" || value === null) return false;

  for (const key in value) {
    if (!Object.prototype.hasOwnProperty.call(value, key)) return false;
  }

  return true;
};

const getKeyAndValues = (
  param: unknown,
  defaultKey: string,
): {
  values: Record<string, unknown>;
  key: string;
} => {
  if (typeof param === "string") return { key: param, values: {} };

  if (isRecord(param)) {
    const key =
      "key" in param && typeof param.key === "string" ? param.key : defaultKey;
    const values =
      "values" in param && isRecord(param.values) ? param.values : {};
    return { key, values };
  }

  return { key: defaultKey, values: {} };
};

const parsedType = (data: unknown): string => {
  const t = typeof data;

  switch (t) {
    case "number": {
      return Number.isNaN(data) ? "NaN" : "number";
    }
    case "object": {
      if (Array.isArray(data)) {
        return "array";
      }
      if (data === null) {
        return "null";
      }

      if (
        Object.getPrototypeOf(data) !== Object.prototype &&
        data?.constructor
      ) {
        return data.constructor.name;
      }
    }
  }
  return t;
};

export type $ZodErrorMap<T extends $ZodIssueBase = $ZodIssue> = (
  issue: $ZodRawIssue<T>,
) => {
  message: string;
  code?: string;
};

export type MakeZodI18nMap = (options?: ZodI18nMapOptions) => $ZodErrorMap;

export interface ZodI18nMapOptions {
  t?: TFunction;
  handlePath?: HandlePathOption | false;
}

export interface HandlePathOption {
  context?: string;
  keyPrefix?: string;
}

const defaultNs = "validation";

export const makeZodI18nMap: MakeZodI18nMap = (options) => (issue) => {
  const { t, ns, handlePath } = {
    t: i18next.t,
    ns: defaultNs,
    ...options,
    handlePath:
      options?.handlePath !== false
        ? {
            context: "with_path",
            ns: config.namespaces,
            keyPrefix: undefined,
            ...options?.handlePath,
          }
        : null,
  } as const;

  const defaultResult = defaultErrorMap(issue);
  const defaultMessage =
    typeof defaultResult === "string"
      ? defaultResult
      : (defaultResult?.message ?? "");

  const path =
    issue.path && issue.path.length > 0 && !!handlePath
      ? {
          context: handlePath.context,
          path: t(
            [handlePath.keyPrefix, issue.path.join(".")]
              .filter(Boolean)
              .join("."),
            {
              ns: handlePath.ns,
              defaultValue: issue.path.join("."),
            },
          ),
        }
      : {};

  switch (issue.code) {
    case "invalid_type":
      if (issue.received === undefined || issue.received === null) {
        const code = `${ns}:error.undefined`;

        return {
          message: t(code, {
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      } else {
        const parsed = parsedType(issue.input).toLocaleLowerCase();
        const code = `${ns}:error.type`;

        return {
          message: t(code, {
            ns,
            expected: t(`type.${issue.expected}`, {
              defaultValue: issue.expected,
            }),
            received: t(`type.${parsed}`, {
              defaultValue: parsed,
            }),
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      }
    case "unrecognized_keys": {
      const code = `${ns}:error.unrecognizedKeys`;

      return {
        message: t(code, {
          keys: joinValues(issue.keys, ", "),
          count: issue.keys.length,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }
    case "invalid_union": {
      const code = `${ns}:error.union`;

      return {
        message: t(code, {
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }
    case "invalid_key": {
      const code = `${ns}:error.invalidKey`;

      return {
        message: t(code, {
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }

    case "invalid_element": {
      const code = `${ns}:error.invalidElement`;

      return {
        message: t(code, {
          origin: issue.origin,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }

    case "invalid_value": {
      const code = `${ns}:error.invalidValue`;

      return {
        message: t(code, {
          values: joinValues(issue.values, ", "),
          count: issue.values.length,
          expected: JSON.stringify(issue.values, jsonStringifyReplacer),
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }

    case "too_small": {
      const minimum =
        issue.origin === "date"
          ? new Date(issue.minimum as number)
          : issue.minimum;

      const code = `${ns}:error.tooSmall.${issue.origin}.${
        issue.exact ? "exact" : issue.inclusive ? "inclusive" : "notInclusive"
      }`;

      return {
        message: t(code, {
          minimum,
          count: typeof minimum === "number" ? minimum : undefined,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }
    case "too_big": {
      const maximum =
        issue.origin === "date"
          ? new Date(issue.maximum as number)
          : issue.maximum;

      const code = `${ns}:error.tooBig.${issue.origin}.${
        issue.exact ? "exact" : issue.inclusive ? "inclusive" : "notInclusive"
      }`;

      return {
        message: t(code, {
          maximum,
          count: typeof maximum === "number" ? maximum : undefined,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }

    case "invalid_format": {
      if (issue.format === "starts_with") {
        const code = `${ns}:error.string.startsWith`;

        return {
          message: t(code, {
            startsWith: issue.prefix,
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      } else if (issue.format === "ends_with") {
        const code = `${ns}:error.string.endsWith`;

        return {
          message: t(code, {
            endsWith: issue.suffix,
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      } else if (issue.format === "includes") {
        const code = `${ns}:error.string.includes`;

        return {
          message: t(code, {
            includes: issue.includes,
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
        };
      } else if (issue.format === "regex") {
        const code = `${ns}:error.string.regex`;

        return {
          message: t(code, {
            pattern: issue.pattern,
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      } else {
        const code = `${ns}:error.string.generic`;

        return {
          message: t(code, {
            format: issue.format,
            ns,
            defaultValue: defaultMessage,
            ...path,
          }),
          code,
        };
      }
    }

    case "custom": {
      const { key, values } = getKeyAndValues(
        issue.params?.i18n,
        "error.custom",
      );

      return {
        message: t(key, {
          ...values,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code: key,
      };
    }
    case "not_multiple_of": {
      const code = `${ns}:error.notMultipleOf`;

      return {
        message: t(code, {
          multipleOf: issue.multipleOf,
          ns,
          defaultValue: defaultMessage,
          ...path,
        }),
        code,
      };
    }
    default:
      return { message: defaultMessage, code: `${ns}:error.default` };
  }
};
