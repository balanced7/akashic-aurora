import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { handle, isAPIError, withTimeout } from "../index";

describe("isAPIError", () => {
  it("should return true for valid API error object", () => {
    const error = {
      code: "ERROR_CODE",
      message: "Something went wrong",
      timestamp: new Date().toISOString(),
      path: "/api/test",
    };
    expect(isAPIError(error)).toBe(true);
  });

  it.each([
    [{}],
    [{ code: "ERROR_CODE" }],
    [{ message: "Something went wrong" }],
    [{ timestamp: new Date().toISOString() }],
    [{ path: "/api/test" }],
  ])("should return false for invalid object", (input) => {
    expect(isAPIError(input)).toBe(false);
  });

  it.each([[null], [undefined]])("should return false for %s", (input) => {
    expect(isAPIError(input)).toBe(false);
  });
});

describe("handle", () => {
  it("should return data on success", async () => {
    const mockFn = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });

    const handler = handle(mockFn);
    const result = await handler({});

    expect(result).toEqual({ success: true });
  });

  it("should throw error on failure if throwOnError is true (default)", async () => {
    const mockFn = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ message: "Failed" }),
    });

    const handler = handle(mockFn);
    await expect(handler({})).rejects.toThrow(Error);
  });

  it("should return null on failure if throwOnError is false", async () => {
    const mockFn = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ message: "Failed" }),
    });

    const handler = handle(mockFn, { throwOnError: false });
    const result = await handler({});

    expect(result).toBeNull();
  });

  it("should throw error if fetch throws and throwOnError is true", async () => {
    const mockFn = vi.fn().mockRejectedValue(new Error("Network Error"));
    const handler = handle(mockFn);
    await expect(handler({})).rejects.toThrow("Network Error");
  });

  it("should allow error propagation if fetch throws and throwOnError is false", async () => {
    const mockFn = vi.fn().mockRejectedValue(new Error("Network Error"));
    const handler = handle(mockFn, { throwOnError: false });

    // Expect it to throw because handle doesn't catch fn() errors
    await expect(handler({})).rejects.toThrow("Network Error");
  });

  it("should validate data with schema if provided", async () => {
    const schema = z.object({ id: z.number() });
    const mockFn = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 123 }),
    });

    const handler = handle(mockFn, { schema });
    const result = await handler({});

    expect(result).toEqual({ id: 123 });
  });

  it("should throw error if schema validation fails and throwOnError is true", async () => {
    const schema = z.object({ id: z.number() });
    const mockFn = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "invalid" }),
    });

    const handler = handle(mockFn, { schema });
    await expect(handler({})).rejects.toThrow();
  });

  it("should return null if schema validation fails and throwOnError is false", async () => {
    const schema = z.object({ id: z.number() });
    const mockFn = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "invalid" }),
    });

    const handler = handle(mockFn, { schema, throwOnError: false });
    const result = await handler({});

    expect(result).toBeNull();
  });
});

describe("withTimeout", () => {
  it("should resolve if promise finishes before timeout", async () => {
    const promise = new Promise((resolve) =>
      setTimeout(() => resolve("done"), 10),
    );
    const result = await withTimeout(promise, 100);
    expect(result).toBe("done");
  });

  it("should reject if timeout is reached", async () => {
    const promise = new Promise((resolve) =>
      setTimeout(() => resolve("done"), 100),
    );
    await expect(withTimeout(promise, 10)).rejects.toThrow(Error);
  });
});
