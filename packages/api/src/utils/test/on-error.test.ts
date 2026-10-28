import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { onError } from "../on-error";

import type { Context } from "hono";

vi.mock("@akashic-labs/i18n/server", () => ({
  getTranslation: vi.fn().mockResolvedValue({
    t: (key: string) => key,
    i18n: {},
  }),
}));

vi.mock("@akashic-labs/i18n", () => ({
  isKey: vi.fn().mockReturnValue(true),
}));

vi.mock("@akashic-labs/shared/utils", () => ({
  getStatusCode: vi.fn().mockReturnValue(500),
}));

interface ErrorResponse {
  code: string;
  message: string;
  status: number;
  path: string;
  timestamp?: string;
}

describe("onError", () => {
  beforeEach(() => {
    vi.spyOn(console, "log").mockImplementation(() => {
      /* empty */
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return a formatted error response for valid error object", async () => {
    const error = {
      code: "ERROR_CODE",
      message: "Something went wrong",
    };

    const context = {
      req: { raw: { url: "http://localhost/api/test" } },
      var: { locale: "en" },
    } as Context<{
      Bindings: { NODE_ENV: string };
      Variables: { locale: string };
    }>;

    const response = await onError(error, context);

    const data = (await response.json()) as ErrorResponse;

    expect(data).toMatchObject({
      code: "ERROR_CODE",
      message: "Something went wrong",
      status: 500,
      path: "/api/test",
    });
    expect(data.timestamp).toBeDefined();
  });

  it("should translate error code if message is missing", async () => {
    const error = {
      code: "auth.error.invalid_credentials",
      message: "",
    };

    const context = {
      req: { raw: { url: "http://localhost/api/test" } },
      var: { locale: "en" },
    } as Context<{
      Bindings: { NODE_ENV: string };
      Variables: { locale: string };
    }>;

    const response = await onError(error, context);

    const data = (await response.json()) as ErrorResponse;

    expect(data.message).toBe("auth.error.invalid_credentials");
  });

  it("should fallback to general error if input is not a recognized error object", async () => {
    const error = "Just a string error";

    const context = {
      req: { raw: { url: "http://localhost/api/test" } },
      var: { locale: "en" },
    } as Context<{
      Bindings: { NODE_ENV: string };
      Variables: { locale: string };
    }>;

    const response = await onError(error, context);

    const data = (await response.json()) as ErrorResponse;

    expect(data).toMatchObject({
      code: "common:error.general",
      message: "common:error.general",
      status: 500,
      path: "/api/test",
    });
  });
});
